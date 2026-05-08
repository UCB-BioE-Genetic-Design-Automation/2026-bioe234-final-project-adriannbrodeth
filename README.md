# Opentrons OT-2 Simulation Engine & Validation Pipeline
**BIOE 234 Final Project · Spring 2026**

> This repository highlights my specific contributions (**Adriann Brodeth**) to a larger group project: *LLM-Driven Optimization and Visualization of Opentrons OT-2 Protocols*.
>
> While the broader project provides an end-to-end conversational AI interface for describing, generating, and visualizing lab protocols, my role was to build the **Simulation Engine** and the **Protocol Checkers**. My component acts as the critical bridge in the pipeline — taking the AI-generated Python script, validating it for physical and structural logic, and safely running it through a dry-run simulator to produce structured logs for downstream heuristic analysis and visualization.

---

## 🏗️ Architecture & How It Fits

The simulation engine sits squarely in the middle of the project's data flow:

```
  OT-2 Python script  (Taylor's Module)
          ↓
[ simulation_engine.py + protocol_checkers.py ]  ←─── Adriann's Component
          ↓
  simulation log (plain text)
          ↓
  heuristic analysis  (Alex's Module)
  log parsing + visualization  (Christian's Module)
```

### The Two-Venv Architecture

One of the core technical challenges I solved was a **dependency collision**. The Opentrons package conflicts with the FastMCP server dependencies (specifically `pydantic` and `anyio`). To solve this, I designed a two-venv architecture:

- **`.venv`** — Handles the main app, Streamlit, Gemini SDK, and visualizer dependencies.
- **`venv_ot`** — An isolated environment strictly for Opentrons.

Instead of directly importing `opentrons` into the main process (which would break FastMCP), my code securely spans this boundary by invoking the `venv_ot` executable as an external subprocess.

---

## 🛠️ Key Technical Features

### 1. The Simulation Engine (`simulation_engine_final.py`)

This is the core execution wrapper that safely dry-runs the protocol:

- **Subprocess & Temp Files** — The engine writes the protocol string to a temporary `.py` file, as `opentrons_simulate` requires a file path rather than standard input. It then runs it using Python's `subprocess.run`.
- **Robust Log Capturing** — Captures and combines both `stdout` (step-by-step logs) and `stderr` (Opentrons calibration warnings), successfully navigating silent failures to output clean, consolidated logs.
- **Structured Outputs & Step Extraction** — Instead of raising exceptions, it returns a structured dictionary containing `"status"`, `"logs"`, and `"step_count"`. The step count is extracted by parsing the log for recognized pipetting actions (`aspirate`, `dispense`, `pick-up`, `drop`), which is then surfaced in the Streamlit UI metrics.

### 2. Pre-Flight Validation (`protocol_checkers_final.py`)

Before passing any AI-generated code to the Opentrons simulator, this suite runs safety checks to prevent crashes:

- **Syntax Checking** — Uses Python's built-in `ast` module to parse the protocol code, catching typos, missing `apiLevel` metadata, and ensuring the required `run()` function is present.
- **Hardware Match Logic** — Uses regular expressions to parse `load_instrument` and `load_labware` commands, ensuring that the loaded pipettes (e.g., P20, P300) physically match the volume of the loaded tip racks.

### 3. Post-Simulation Analysis (`protocol_checkers_final.py`)

After a simulation runs, the module parses the raw logs to provide immediate, human-readable feedback:

- **Safety Translation** — Translates cryptic Opentrons exceptions (like `OutOfTipsError` or `PointError`) into plain-English warnings about empty tip racks, attached tips, or physical bounds collisions.
- **Resource Optimization** — Analyzes successful logs to find time and plastic savings, such as recommending `new_tip='once'` if a tip is picked up more than 12 times, or flagging inefficient deck movements across opposite slots.
- **Actionable Checklists** — Extracts physical verbs from the logs to generate a clean, step-by-step checklist of what the robot actually did (e.g., highlighting when human pauses are required).

---

## 🚀 Execution & Integration

These core functions are wrapped into two distinct execution paths to support both the group's web application and standard CLI usage:

- **MCP Tool Integration** (`simulate_protocol.py` / `.json`) — The engine is exposed to the Gemini model as an MCP tool using the Function Object pattern, with a JSON schema declaring the tool's inputs, outputs, and descriptions.
- **Command Line Pipeline** (`run_simulation_final.py`) — A standalone script that sequences the syntax check, hardware check, simulation engine, and post-analysis. It handles file validation and aborts immediately if pre-flight checks fail, saving compute time and preventing robot crashes.

---

## 📄 Example Outputs

The engine reliably handles standard template protocols and custom freeform generations. Examples of raw simulation logs are available in the `examples/` directory:

| File | Description |
|------|-------------|
| `serial_dilution_log.txt` | ~32 actions for 180 µL plate-to-plate transfers |
| `pcr_setup_log.txt` | 74 actions handling 5–15 µL transfers of samples and master mix |
| `reagent_addition_log.txt` | 192 actions dispensing 50 µL from a reservoir into 48 wells |

> **Note:** The `--- STDERR ---` section at the bottom of these logs contains expected calibration warnings from the Opentrons runtime and does not indicate a pipeline failure.

---

## 🔭 Future Work

| Area / Feature | Current Limitation | Planned Expansion |
|---|---|---|
| **Execution Environment** | Relies on `opentrons_simulate` (dry-run only). Cannot check physical liquid levels or account for real-world factors like jammed tips. | Connect to a live robot via the Opentrons HTTP API, enabling actual execution and real-time sensing after a successful dry-run. |
| **Hardware Compatibility** | Pre-flight checks are hard-coded for the OT-2 (API level 2.15). The newer Flex (OT-3) uses a vastly different API and deck layout. | Build a robot-model selector and create separate, dynamically loaded hardware validation rules to fully support the Opentrons Flex. |
| **LLM Hallucinations** | Custom protocols with hallucinated labware names pass structural checks but crash the simulator or confuse downstream visualizers. | Implement an auto-updating JSON catalog of the official Opentrons labware repository to intercept and reject fake labware before booting the simulator. |
| **Pipette Loadouts** | Hardware matching rules assume basic, single-pipette loadouts. Complex dual-pipette workflows complicate tip-rack assignment validation. | Refactor the regex parser to distinctly map `pipette_left` and `pipette_right` to specific tip racks, ensuring proper hardware matching for dual mounts. |
