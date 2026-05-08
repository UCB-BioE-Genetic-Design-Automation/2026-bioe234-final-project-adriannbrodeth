"""
OT-2 simulation engine (Adriann Brodeth).

Runs a protocol string through the opentrons_simulate CLI and returns
structured logs. The simulator must be installed in its own isolated venv
due to pydantic/anyio conflicts with FastMCP — see README for setup.
"""

import subprocess
import tempfile
import os
import sys


def run_opentrons_simulation(
    protocol_code: str,
    sim_path: str = None,
    output_filename: str = None,
) -> dict:
    """
    Takes a string of Opentrons protocol code, saves it temporarily,
    runs the simulator, and returns the logs.

    Parameters
    ----------
    protocol_code   : full text of a valid Opentrons API v2 Python script
    sim_path        : explicit path to the opentrons_simulate executable;
                      if None, looks next to sys.executable
    output_filename : optional path to save the raw log text

    Returns
    -------
    dict with keys: status ("success" | "error"), logs (str),
                    file_saved (str), step_count (int)
    """
    if sim_path is None:
        venv_bin = os.path.dirname(sys.executable)
        suffix = ".exe" if sys.platform == "win32" else ""
        sim_path = os.path.join(venv_bin, f"opentrons_simulate{suffix}")
        if not os.path.exists(sim_path):
            sim_path = os.path.join(venv_bin, "opentrons_simulate")

    if not os.path.exists(sim_path):
        return {
            "status": "error",
            "logs": (
                f"Could not find 'opentrons_simulate' at '{sim_path}'.\n"
                "Set OT_VENV_PYTHON in your .env file to point to the Python "
                "executable in a venv where opentrons is installed.\n"
                "See README.md — Setup: Opentrons venv."
            ),
            "file_saved": "No file requested",
            "step_count": 0,
        }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
        tmp.write(protocol_code)
        tmp_path = tmp.name

    try:
        result = subprocess.run(
            [sim_path, tmp_path],
            capture_output=True,
            text=True,
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        combined = ""
        if stdout:
            combined += stdout
        if stderr:
            combined += ("\n\n--- STDERR ---\n" if stdout else "") + stderr

        error_keywords = ("Traceback", "Error", "error", "failed", "exception")
        stderr_has_error = any(kw in stderr for kw in error_keywords)

        if result.returncode == 0 or (stdout and not stderr_has_error):
            status = "success"
            logs = combined
        else:
            status = "error"
            logs = combined or "No output captured. The simulator may have failed silently."

        step_count = sum(
            1 for line in logs.splitlines()
            if any(
                line.strip().startswith(kw)
                for kw in ("Aspirating", "Dispensing", "Picking up", "Dropping")
            )
        )

        if output_filename:
            with open(output_filename, "w") as f:
                f.write(logs)

        return {
            "status": status,
            "logs": logs,
            "file_saved": output_filename or "No file requested",
            "step_count": step_count,
        }

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
