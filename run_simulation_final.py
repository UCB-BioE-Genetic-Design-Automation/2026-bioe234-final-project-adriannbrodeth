import os
import sys
from simulation_engine_2 import run_opentrons_simulation
from protocol_checkers import (
    syntax_check,
    hardware_match_check,
    simulation_safety_check,
    optimization_resource_check,
    extract_actionable_steps
)

def main():
    # 1. Configuration: Anchor paths to the script's actual directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # 2. Accept a file argument from the command line, or fall back to default
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
        if not os.path.isabs(input_file):
            input_file = os.path.join(script_dir, input_file)
    else:
        input_file = os.path.join(script_dir, 'test_protocol.py')

    # 3. Validate file extension
    _, ext = os.path.splitext(input_file)
    if ext not in ('.py', '.txt'):
        print(f"Error: Unsupported file type '{ext}'. Only .py and .txt files are accepted.")
        sys.exit(1)

    # 4. Force output file to ALWAYS save in the same folder as the input file
    input_dir = os.path.dirname(os.path.abspath(input_file))
    base_name = os.path.splitext(os.path.basename(input_file))[0]
    output_log = os.path.join(input_dir, f'{base_name}_simulation_results.txt')

    print(f"Reading {input_file}...")

    try:
        with open(input_file, 'r') as file:
            protocol_content = file.read()

        # ==========================================
        # PIPELINE STEP 1: PRE-FLIGHT SYNTAX CHECK
        # ==========================================
        print("Running Pre-flight Syntax Check...")
        syntax_errors = syntax_check(protocol_content)
        
        if syntax_errors:
            print("\n🚨 SYNTAX CHECK FAILED! Fix these issues before simulating:")
            for error in syntax_errors:
                print(f"  {error}")
            
            print(f"\nSimulation aborted. Please fix '{input_file}' and try again.")
            sys.exit(1) # Stop the script immediately
        else:
            print("✅ Syntax check passed!\n")
        # ==========================================

        # ==========================================
        # PIPELINE STEP 2: HARDWARE CHECK
        # ==========================================
        print("Running Logic & Hardware Match Check...")
        logic_errors = hardware_match_check(protocol_content)
        
        if logic_errors:
            print("\n🚨 LOGIC CHECK FAILED! Fix these physical hardware mismatches:")
            for error in logic_errors:
                print(f"  {error}")
            print(f"\nSimulation aborted. Continuing could crash the robot.")
            sys.exit(1)
        else:
            print("✅ Hardware logic passed!\n")

# ==========================================
        # PIPELINE STEP 3: SIMULATION
        # ==========================================
        print("Starting Opentrons simulation (this may take a few seconds)...")
        results = run_opentrons_simulation(protocol_content, output_filename=output_log)

        # ==========================================
        # PIPELINE STEP 4: POST-SIMULATION ANALYSIS
        # ==========================================
        print("Analyzing Simulation Logs...")
        
        safety_warnings = simulation_safety_check(results["logs"])
        optimizations = optimization_resource_check(results["logs"])
        checklist_steps = extract_actionable_steps(results["logs"])

        # 1. Output Warnings (ALWAYS RUNS)
        if safety_warnings:
            print("\n🚨 HUMAN-READABLE WARNINGS & ERRORS:")
            for warning in safety_warnings:
                print(f"  {warning}")

        # 2. Output Optimizations (ALWAYS RUNS)
        if optimizations:
            print("\n✨ OPTIMIZATION SUGGESTIONS:")
            for opt in optimizations:
                print(f"  {opt}")
        elif not safety_warnings and results["status"] == "success":
            print("\n✨ Protocol looks highly optimized already! Great job.")

        # 3. Output the Prep Checklist (ALWAYS RUNS)
        print("\n📋 ROBOT ACTION CHECKLIST (What the robot actually did):")
        if checklist_steps:
            for i, step in enumerate(checklist_steps, 1):
                # Visually highlight moments where the robot pauses for the human
                if "Pausing" in step or "Resetting" in step:
                    print(f"  {i}. 🛑 HUMAN REQUIRED: {step.upper()}") 
                else:
                    print(f"  {i}. {step}")
            
            # If the protocol crashed, show them EXACTLY where it died on the timeline
            if results["status"] != "success":
                print(f"  {len(checklist_steps) + 1}. 💥 [SIMULATION CRASHED HERE]")
        else:
            print("  (No physical steps were completed. Check your code logic.)")

        # 4. Final System Status
        if results["status"] != "success":
            print(f"\n❌ FINAL STATUS: Simulation Failed. Full Traceback saved to: {output_log}")
        else:
            print(f"\n✅ FINAL STATUS: Success! Log saved to: {output_log}")

        # Confirm the file actually exists after writing
        if os.path.exists(output_log):
            print(f"✅ Confirmed: file exists at {output_log} ({os.path.getsize(output_log)} bytes)")

    except FileNotFoundError:
        print(f"Error: Could not find '{input_file}'. Make sure the file exists.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()