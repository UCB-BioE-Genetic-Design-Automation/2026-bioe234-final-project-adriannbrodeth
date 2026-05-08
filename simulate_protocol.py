"""
tools/simulate_protocol.py
===========================
Run an OT-2 protocol script through opentrons_simulate and return the log text.
Uses OT_VENV_PYTHON from .env to locate a separate venv that has opentrons installed.
"""

import json
import os
import sys
import matplotlib
matplotlib.use("Agg")

from .._lib.simulation_engine import run_opentrons_simulation


class SimulateProtocol:
    def initiate(self) -> None:
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass
        python_path = os.environ.get("OT_VENV_PYTHON") or sys.executable
        venv_bin = os.path.dirname(python_path)
        suffix = ".exe" if sys.platform == "win32" else ""
        self._sim_path = os.path.join(venv_bin, f"opentrons_simulate{suffix}")

    def run(self, protocol_code: str, output_filename: str = "simulation_output.txt") -> str:
        try:
            result = run_opentrons_simulation(
                protocol_code=protocol_code,
                sim_path=self._sim_path,
                output_filename=output_filename,
            )
        except Exception as exc:  # noqa: BLE001
            return json.dumps({"error": f"Simulation failed: {exc}"})

        return json.dumps(result)


_instance = SimulateProtocol()
_instance.initiate()
simulate_protocol = _instance.run
