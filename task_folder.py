import re


def task_to_folder(task):

    task = task.lower()

    task = re.sub(r'[^a-z0-9 ]', '', task)

    return task.replace(" ", "-")