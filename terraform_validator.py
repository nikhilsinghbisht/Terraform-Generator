import subprocess
import os


def run_command(command, path):
    try:
        result = subprocess.run(
            command,
            cwd=path,
            capture_output=True,
            text=True,
            shell=True
        )

        return result.returncode, result.stdout + result.stderr

    except Exception as e:
        return 1, str(e)


def validate_terraform(directory):
    """
    Runs terraform init, fmt and validate
    """

    print("\nRunning Terraform validation...\n")

    commands = [
        "terraform init -backend=false",
        "terraform fmt -recursive",
        "terraform validate"
    ]

    for cmd in commands:

        code, output = run_command(cmd, directory)

        print(f"\nCommand: {cmd}\n")
        print(output)

        if code != 0:
            print("\nTerraform validation failed\n")
            return False

    print("\nTerraform validation successful\n")

    return True