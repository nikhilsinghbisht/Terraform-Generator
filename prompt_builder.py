def build_prompt(task, description, task_type, registry_doc, task_folder):

    if task_type == "creation":
        with open("prompts/creation_prompt.txt", "r", encoding="utf-8") as f:
            template = f.read()
    else:
        with open("prompts/existing_prompt.txt", "r", encoding="utf-8") as f:
            template = f.read()

    # 🔥 Escape ALL Terraform braces
    template = template.replace("{", "{{").replace("}", "}}")

    # ✅ restore only placeholders
    template = template.replace("{{TASK}}", "{TASK}")
    template = template.replace("{{DESCRIPTION}}", "{DESCRIPTION}")
    template = template.replace("{{TASK_TYPE}}", "{TASK_TYPE}")
    template = template.replace("{{REGISTRY_DOC}}", "{REGISTRY_DOC}")
    template = template.replace("{{TASK_FOLDER}}", "{TASK_FOLDER}")

    return template.format(
        TASK=task,
        DESCRIPTION=description,
        TASK_TYPE=task_type,
        REGISTRY_DOC=registry_doc,
        TASK_FOLDER=task_folder
    )