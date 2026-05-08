import subprocess
import tempfile
import os
import sys

def run_opentrons_simulation(protocol_code: str, output_filename: str = None) -> dict:
    """
    Takes a string of Opentrons protocol code, saves it temporarily,
    runs the simulator, returns the logs, and optionally saves them to a .txt file.
    """

    # Resolve opentrons_simulate from the same environment as this Python interpreter
    venv_bin = os.path.dirname(sys.executable)
    opentrons_simulate = os.path.join(venv_bin, 'opentrons_simulate')

    if not os.path.exists(opentrons_simulate):
        return {
            "status": "error",
            "logs": (
                f"Could not find 'opentrons_simulate' in '{venv_bin}'.\n"
                "Make sure the opentrons package is installed in this environment:\n"
                "  pip install opentrons"
            ),
            "file_saved": "No file requested"
        }

    # Create a temporary .py file with the protocol code
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(protocol_code)
        temp_file_path = temp_file.name

    try:
        # Run the simulator, capturing both stdout and stderr separately
        result = subprocess.run(
            [opentrons_simulate, temp_file_path],
            capture_output=True,
            text=True
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        # Combine both streams so nothing is lost
        combined_logs = ""
        if stdout:
            combined_logs += stdout
        if stderr:
            combined_logs += ("\n\n--- STDERR ---\n" if stdout else "") + stderr

        # opentrons_simulate can return non-zero even on warnings, so
        # treat it as success if stdout has content and stderr has no
        # traceback/error keywords
        error_keywords = ("Traceback", "Error", "error", "failed", "exception")
        stderr_has_error = any(kw in stderr for kw in error_keywords)

        if result.returncode == 0 or (stdout and not stderr_has_error):
            status = "success"
            logs = combined_logs
        else:
            status = "error"
            logs = combined_logs or "No output captured. The simulator may have failed silently."

        # Save logs to file
        if output_filename:
            with open(output_filename, 'w') as f:
                f.write(logs)

        return {
            "status": status,
            "logs": logs,
            "file_saved": output_filename if output_filename else "No file requested"
        }

    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
