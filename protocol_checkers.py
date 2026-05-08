import ast
import re

def syntax_check(protocol_code: str) -> list:
    """
    Checks for the bare-minimum structural requirements of an Opentrons protocol.
    """
    feedback = []
    
    try:
        tree = ast.parse(protocol_code)
    except SyntaxError as e:
        return [f"❌ Code Error: There is a typo in your Python code on line {e.lineno}. Check for missing parentheses or quotes."]

    # Look for metadata and run()
    has_api = "apiLevel" in protocol_code
    has_run = any(isinstance(node, ast.FunctionDef) and node.name == 'run' for node in tree.body)

    if not has_api:
        feedback.append("🛠️ Missing Metadata: Opentrons needs to know which version of their software to use. Add `metadata = {'apiLevel': '2.14'}` to the top.")
    
    if not has_run:
        feedback.append("🛠️ Missing Main Function: The robot doesn't know where to start! Make sure all your steps are inside a `def run(protocol):` block.")

    return feedback

def hardware_match_check(protocol_code: str) -> list:
    """
    Ensures the pipettes loaded physically match the tipracks loaded.
    Checks a variety of common Opentrons pipette sizes.
    """
    feedback = []
    
    # 1. Find all loaded pipettes and labware using regex
    pipettes = re.findall(r"load_instrument\(['\"](.*?)['\"]", protocol_code)
    labware = re.findall(r"load_labware\(['\"](.*?)['\"]", protocol_code)
    
    # Convert lists to single lowercase strings for easy searching
    pipettes_str = " ".join(pipettes).lower()
    
    # Filter labware to only look at ones that mention "tiprack"
    tipracks = [lw.lower() for lw in labware if "tiprack" in lw.lower()]
    tipracks_str = " ".join(tipracks)

    # 2. Define our rules: { "pipette_type": ["acceptable", "tip", "sizes"] }
    pipette_tip_map = {
        "p10": ["10", "20"],       # P10 can often use 10ul or 20ul tips
        "p20": ["20"],
        "p50": ["50", "200"],      # P50 can use 50ul or 200ul tips
        "p200": ["200", "300"],
        "p300": ["300", "200"],    # P300 can use 300ul or 200ul tips
        "p1000": ["1000"]
    }

    # 3. Check what the user loaded against our rules
    for pip_size, acceptable_tips in pipette_tip_map.items():
        if pip_size in pipettes_str:
            # Check if ANY of the acceptable tip sizes are in the loaded tipracks string
            has_matching_tip = any(tip_size in tipracks_str for tip_size in acceptable_tips)
            
            if not has_matching_tip:
                tip_suggestions = "µL or ".join(acceptable_tips) + "µL"
                feedback.append(
                    f"⚠️ Hardware Mismatch: You loaded a {pip_size.upper()} pipette, "
                    f"but didn't load a matching tip rack. Please load a {tip_suggestions} tip rack."
                )

    # 4. Edge Case: Did they load a pipette but NO tipracks at all?
    if pipettes and not tipracks:
        feedback.append("🚨 Missing Tip Racks: You loaded a pipette, but forgot to load any tip racks!")

    return feedback

def simulation_safety_check(simulation_logs: str) -> list:
    """
    Scans the simulation logs/traceback for common runtime errors and warnings.
    Translates cryptic Opentrons errors into plain English.
    """
    feedback = []
    logs_lower = simulation_logs.lower()

    # 1. Check for Out of Tips Error
    if "outoftipserror" in logs_lower or "out of tips" in logs_lower:
        feedback.append(
            "❌ Out of Tips: The robot tried to pick up a tip, but all your loaded tip racks are empty! "
            "You need to either load more tip racks or drop tips back into the rack to reuse them."
        )

    # 2. Check for Tip Already Attached Error
    if "tipattachederror" in logs_lower:
        feedback.append(
            "❌ Tip Already Attached: The robot tried to pick up a tip, but it already has one on the pipette! "
            "Make sure you call `pipette.drop_tip()` before trying to pick up a new one."
        )

    # 3. Check for Out of Bounds / Collision
    if "pointerror" in logs_lower or "out of bounds" in logs_lower:
        feedback.append(
            "🚨 Collision Warning: The robot attempted to move outside its physical limits. "
            "Check your well coordinates or check if you are reaching into an empty slot."
        )

    # 4. Check for Pipette Liquid / Volume Errors
    if "pipetteliquiderror" in logs_lower or "cannot aspirate more than" in logs_lower:
        feedback.append(
            "💧 Volume Error: You tried to aspirate more liquid than the pipette can hold, "
            "or you tried to dispense liquid when the pipette was empty."
        )

    return feedback

def optimization_resource_check(simulation_logs: str) -> list:
    """
    Analyzes a successful simulation log to find opportunities to save time and plastic.
    Returns a list of plain-English optimization suggestions.
    """
    feedback = []
    
    # 1. Tip Waste Analysis
    # The Opentrons simulator always outputs "Picking up tip" when a tip is grabbed
    pickups = simulation_logs.count("Picking up tip")
    
    if pickups > 12:
        feedback.append(
            f"💡 Eco/Time Tip: Your protocol uses {pickups} tips. "
            "If you are transferring the exact same harmless liquid (like water, buffer, or a master mix) "
            "to multiple wells, you don't need a new tip every time! Try adding `new_tip='once'` "
            "to your `transfer()` command to reuse a single tip and save plastic."
        )

    # 2. Deck Movement / Travel Time Analysis
    # If a user puts labware on opposite corners of the deck, the robot wastes time traveling.
    if "on 1\n" in simulation_logs and ("on 11\n" in simulation_logs or "on 9\n" in simulation_logs):
        feedback.append(
            "⏱️ Speed Tip: You have labware placed on opposite sides of the deck (e.g., Slot 1 and Slot 9/11). "
            "The robot will have to travel a long distance back and forth. "
            "To speed up your protocol, try grouping your active labware close together (like Slots 1, 2, and 3)."
        )

    return feedback

def extract_actionable_steps(simulation_logs: str) -> list:
    """
    Extracts physical actions from the Opentrons logs to create a readable checklist.
    """
    steps = []
    
    # Changed these to all lowercase
    action_verbs = [
        "picking up", "dropping", "aspirating", "dispensing", 
        "transferring", "pausing", "resetting", "loading", 
        "mixing", "consolidating", "distributing", "moving"
    ]
    
    for line in simulation_logs.split('\n'):
        clean_line = line.strip()
        # Check against lowercase version to make it bulletproof
        if any(clean_line.lower().startswith(verb) for verb in action_verbs):
            steps.append(clean_line) # We append the original line to keep formatting nice
            
    return steps