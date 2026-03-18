import os
import subprocess
import uuid
import threading
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

app = FastAPI()

jobs = {}

EXPORTS_DIR = "exports"


# --------------------------------------------------
# Serve UI
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()


# --------------------------------------------------
# Run Agent
# --------------------------------------------------

def run_agent(job_id, task, description):

    jobs[job_id]["status"] = "running"
    jobs[job_id]["logs"] = ""

    process = subprocess.Popen(
        ["python3", "agent.py", task, description],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        jobs[job_id]["logs"] += line

    process.wait()

    try:
        if not os.path.exists(EXPORTS_DIR):
            raise Exception("exports folder not found")

        # ✅ get full paths
        files = [
            os.path.join(EXPORTS_DIR, f)
            for f in os.listdir(EXPORTS_DIR)
            if f.endswith(".zip")
        ]

        if not files:
            raise Exception("No zip generated")

        # 🔥 pick latest by modification time (CRITICAL FIX)
        latest_file = max(files, key=os.path.getmtime)

        latest_zip = os.path.basename(latest_file)

        if not os.path.exists(latest_file):
            raise Exception("Zip file missing")

        # ✅ SUCCESS
        jobs[job_id]["file"] = latest_zip
        jobs[job_id]["status"] = "finished"

    except Exception as e:
        jobs[job_id]["logs"] += f"\n❌ ZIP generation failed: {str(e)}\n"
        jobs[job_id]["status"] = "error"

# --------------------------------------------------
# Generate API
# --------------------------------------------------

@app.post("/generate")
def generate(task: str = Form(...), description: str = Form("")):

    job_id = str(uuid.uuid4())[:8]

    jobs[job_id] = {
        "status": "starting",
        "logs": "",
        "file": None
    }

    thread = threading.Thread(
        target=run_agent,
        args=(job_id, task, description)
    )

    thread.start()

    return {"job_id": job_id}


# --------------------------------------------------
# Status API
# --------------------------------------------------

@app.get("/status/{job_id}")
def job_status(job_id: str):

    if job_id not in jobs:
        return JSONResponse({"status": "unknown"})

    return JSONResponse(jobs[job_id])


# --------------------------------------------------
# Download API
# --------------------------------------------------

@app.get("/download/{job_id}")
def download(job_id: str):

    if job_id not in jobs:
        return JSONResponse({"error": "invalid job id"})

    file = jobs[job_id]["file"]

    if not file:
        return JSONResponse({"error": "file not ready"})

    path = os.path.join(EXPORTS_DIR, file)

    if not os.path.exists(path):
        return JSONResponse({"error": "file missing on server"})

    return FileResponse(
        path,
        filename=file,
        media_type="application/zip"
    )