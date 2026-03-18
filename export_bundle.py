import os
import zipfile
from datetime import datetime


def export_zip(task_folder, validation_error=None):

    base_dir = "generated"
    zip_dir = "exports"

    os.makedirs(zip_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    zip_path = os.path.join(zip_dir, f"{task_folder}_{timestamp}.zip")

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:

        for root, dirs, files in os.walk(base_dir):

            for file in files:

                file_path = os.path.join(root, file)

                arcname = os.path.relpath(file_path, base_dir)

                zipf.write(file_path, arcname)

        # include validation error log
        if validation_error:

            zipf.writestr("validation_error.txt", validation_error)

    return zip_path