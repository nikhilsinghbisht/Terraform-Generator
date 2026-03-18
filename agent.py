import os
import requests
import subprocess
import re
import time
import sys

# ✅ UTF-8 FIX (prevents emoji crash on Windows)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

from export_bundle import export_zip
from config import DEEPSEEK_API_KEY, MODEL, MAX_TOKENS
from task_classifier import detect_task_type
from schema_provider import get_resource_schema
from prompt_builder import build_prompt
from task_folder import task_to_folder


# --------------------------------------------------
# Extract azurerm resource
# --------------------------------------------------

def extract_resource_name(task):
    match = re.search(r"azurerm_[a-zA-Z0-9_]+", task)
    return match.group(0) if match else ""


# --------------------------------------------------
# LLM Call
# --------------------------------------------------

def generate_code(prompt, retries=3):

    url = "https://api.deepseek.com/v1/chat/completions"

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are an expert Terraform Azure engineer."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": MAX_TOKENS,
        "temperature": 0.1
    }

    for attempt in range(retries):

        print(f"\nLLM request attempt {attempt+1}/{retries}")

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=300)

            if response.status_code != 200:
                print("API Error:", response.text)
                time.sleep(2)
                continue

            return response.json()["choices"][0]["message"]["content"]

        except Exception as e:
            print("Request failed:", str(e))
            time.sleep(2)

    raise Exception("LLM request failed")


# --------------------------------------------------
# Sanitize file path
# --------------------------------------------------

def sanitize_filepath(path):
    path = re.sub(r'[<>:"|?*]', '', path)
    path = path.replace("`", "").strip().rstrip(".")
    return path


# --------------------------------------------------
# Terraform Cleaner
# --------------------------------------------------

def is_valid_line(line):

    if re.match(r"\s*\w+\s*=\s*$", line):
        return False

    if len(line) > 200:
        return False

    if "=" in line:
        parts = line.split("=", 1)
        key = parts[0].strip()
        val = parts[1].strip()

        if val == "":
            return False

        if len(key) > 80:
            return False

    return True


def clean_terraform_code(content):

    cleaned = []

    for line in content.split("\n"):
        if is_valid_line(line):
            cleaned.append(line)

    return "\n".join(cleaned)


# --------------------------------------------------
# Save files
# --------------------------------------------------

def save_output(code):

    base_dir = "generated"
    os.makedirs(base_dir, exist_ok=True)

    pattern = r"FILE:\s*(.*?)\n([\s\S]*?)(?=\nFILE:|\Z)"
    matches = re.findall(pattern, code)

    print("\nDetected FILE blocks:", len(matches))

    if len(matches) < 6:
        print("Warning: Incomplete output from LLM")

    for file_path, content in matches:

        file_path = sanitize_filepath(file_path)

        content = content.replace("```terraform", "").replace("```", "")
        content = clean_terraform_code(content)

        full_path = os.path.join(base_dir, file_path)

        try:
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content.strip())

            print("Created:", full_path)

        except Exception as e:
            print("Failed writing:", full_path, "| Error:", str(e))


# --------------------------------------------------
# Required files check (FIXED)
# --------------------------------------------------

def ensure_required_files(task_folder, task_type):

    example_dir = os.path.join("generated", "Examples", task_folder)
    module_base_dir = os.path.join("generated", "Modules", task_folder)

    example_files = [
        "provider.tf", "versions.tf", "variables.tf",
        "main.tf", "outputs.tf", "terraform.tfvars"
    ]

    module_files = [
        "main.tf", "locals.tf", "variables.tf", "outputs.tf"
    ]

    if task_type == "existing":
        example_files.append("import.tf")
        module_files.append("data.tf")

    missing = []

    # ✅ Check example files
    for f in example_files:
        if not os.path.exists(os.path.join(example_dir, f)):
            missing.append(f"Examples/{task_folder}/{f}")

    # ✅ FIX: dynamic resource folder detection
    if not os.path.exists(module_base_dir):
        missing.append(f"Modules/{task_folder} missing")
        return missing

    resource_dirs = [
        d for d in os.listdir(module_base_dir)
        if os.path.isdir(os.path.join(module_base_dir, d))
    ]

    if not resource_dirs:
        missing.append(f"Modules/{task_folder}/<resource> folder missing")
        return missing

    module_dir = os.path.join(module_base_dir, resource_dirs[0])

    # ✅ Check inside resource folder
    for f in module_files:
        if not os.path.exists(os.path.join(module_dir, f)):
            missing.append(f"Modules/{task_folder}/{resource_dirs[0]}/{f}")

    return missing


# --------------------------------------------------
# Terraform validation (RAILWAY SAFE)
# --------------------------------------------------

def validate_terraform(example_dir):

    # ✅ Skip validation on Railway
    if os.getenv("PORT"):
        print("⚠️ Skipping Terraform validation in Railway")
        return True, ""

    try:
        subprocess.run(["terraform", "version"], capture_output=True)
    except:
        print("⚠️ Terraform not installed, skipping validation")
        return True, ""

    subprocess.run(["terraform", "fmt", "-recursive"], cwd=example_dir)
    subprocess.run(["terraform", "init", "-backend=false"], cwd=example_dir)

    result = subprocess.run(
        ["terraform", "validate"],
        cwd=example_dir,
        capture_output=True,
        text=True
    )

    return result.returncode == 0, result.stderr


# --------------------------------------------------
# MAIN
# --------------------------------------------------

def main():

    # ✅ Required folders for cloud
    os.makedirs("generated", exist_ok=True)
    os.makedirs("exports", exist_ok=True)

    print("\nTerraform Azure Agent\n")

    if len(sys.argv) >= 2:
        task = sys.argv[1]
        description = sys.argv[2] if len(sys.argv) > 2 else ""
    else:
        task = input("Enter Terraform task:\n")
        description = input("Description:\n")

    if not description:
        description = "No description provided"

    print("\nTask:", task)

    task_type = detect_task_type(task)
    task_folder = task_to_folder(task)

    resource = extract_resource_name(task)
    schema_doc = ""

    if resource:
        print("\nFetching schema...")
        schema = get_resource_schema(resource)
        if schema:
            schema_doc = str(schema)

    prompt = build_prompt(task, description, task_type, schema_doc, task_folder)

    print("\nGenerating Terraform code...\n")

    code = generate_code(prompt)
    save_output(code)

    missing = ensure_required_files(task_folder, task_type)

    if missing:
        print("\nMissing files:", missing)

        fix_prompt = f"""
Missing files:
{missing}

Return FULL Terraform code with ALL files.
"""
        code = generate_code(fix_prompt)
        save_output(code)

    example_dir = os.path.join("generated", "Examples", task_folder)

    for attempt in range(2):

        valid, error = validate_terraform(example_dir)

        if valid:
            print("\nTerraform validated successfully")
            break

        print(f"\nFixing Terraform errors (attempt {attempt+1})")

        fix_prompt = f"""
Terraform validation failed:

{error}

Fix ALL issues and return FULL Terraform code with FILE blocks.
Do not generate invalid or empty attributes.
"""
        code = generate_code(fix_prompt)
        save_output(code)

    zip_path = export_zip(task_folder)
    print(f"\nBundle exported: {zip_path}")


if __name__ == "__main__":
    main()