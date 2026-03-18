def detect_task_type(task: str):

    creation_keywords = [
        "create",
        "provision",
        "deploy",
        "build",
        "setup"
    ]

    task_lower = task.lower()

    for word in creation_keywords:
        if word in task_lower:
            return "creation"

    return "existing"