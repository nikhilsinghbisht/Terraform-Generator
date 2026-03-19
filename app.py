import os
import subprocess
import uuid
import threading
import time
from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse

app = FastAPI()

jobs = {}

EXPORTS_DIR = "exports"


# --------------------------------------------------
# Ensure exports dir exists
# --------------------------------------------------
if not os.path.exists(EXPORTS_DIR):
    os.makedirs(EXPORTS_DIR)


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
        ["python3", "agent.py", task, description, job_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    for line in process.stdout:
        jobs[job_id]["logs"] += line

    process.wait()

    try:
        zip_file = None

        # wait until zip is created
        for _ in range(15):
            files = [f for f in os.listdir(EXPORTS_DIR) if f.endswith(".zip")]

            if files:
                # get latest zip file
                files.sort(
                    key=lambda x: os.path.getmtime(os.path.join(EXPORTS_DIR, x)),
                    reverse=True
                )

                zip_file = files[0]
                full_path = os.path.join(EXPORTS_DIR, zip_file)

                if os.path.getsize(full_path) > 0:
                    break

            time.sleep(1)

        if not zip_file:
            raise Exception("Zip file not created")

        jobs[job_id]["file"] = zip_file
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