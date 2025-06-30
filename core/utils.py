import re, random
from core.models import BaseCharacter, RollModifiers
from data.repositories.repository_factory import repositories

def get_character(char_id) -> BaseCharacter:
    character = repositories.character.get_by_id(str(char_id))
    return character if character else None

def roll_parameters_to_dict(roll_parameters: str) -> dict:
    # Parse roll_parameters into roll_parameters_dict
    roll_parameters_dict = {}
    if roll_parameters:
        for param in roll_parameters.split(","):
            if ":" in param:
                k, v = param.split(":", 1)
                roll_parameters_dict[k.strip()] = v.strip()
    return roll_parameters_dict

# Helper to roll a dice formula string (e.g., "1d6+2")
def roll_dice_formula(formula: str):
    formula = formula.replace(" ", "").lower()
    pattern = r'(\d*)d(\d+)((?:[+-]\d+)*)'
    match = re.fullmatch(pattern, formula)
    if match:
        num_dice = int(match.group(1)) if match.group(1) else 1
        die_size = int(match.group(2))
        modifiers_str = match.group(3) or ""
        modifiers_list = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
        modifier = sum(modifiers_list)
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        subtotal = sum(rolls) + modifier
        return subtotal, f"{formula} [{subtotal}]"
    # Try to parse as a simple integer
    try:
        return int(formula), str(formula)
    except Exception:
        return 0, formula

def roll_formula(character: BaseCharacter, base_roll: str, modifiers: RollModifiers):
    """
    Parses and rolls a dice formula like '2d6+3-2', '1d20+5-1', '1d100', etc.
    Modifiers can now also be dice formulas (e.g., Athletics: 1d6, mod1: 1d12+9).
    Returns a tuple: (result_string, total)
    The result string breaks out the formula into its elements, e.g.:
    4df (+ - - 0) + Athletics (2) + mod1 (10)
    """
    modifier_descriptions = []
    total_mod = 0
    rolled_mods = {}

    # Gather all modifiers and their sources, supporting dice formulas
    for key, value in modifiers.get_modifiers(character).items():
        if isinstance(value, str) and re.match(r'^\d*d\d+', value.replace(" ", "")):
            mod, desc = roll_dice_formula(value)
            rolled_mods[key] = mod  # Store the rolled value for later use
            total_mod += mod
            # Extract the total from the roll_dice_formula result (mod)
            modifier_descriptions.append(f"{key} ({desc})")
        else:
            try:
                mod = int(value)
                rolled_mods[key] = mod
                total_mod += mod
                sign = "+" if mod >= 0 else ""
                modifier_descriptions.append(f"{key} ({sign}{mod})")
            except Exception:
                continue

    # Build the full formula string for rolling, using the already rolled modifiers
    formula = base_roll
    for key, mod in rolled_mods.items():
        if mod >= 0:
            formula += f"+{mod}"
        else:
            formula += f"{mod}"

    formula = formula.replace(" ", "").lower()
    fudge_pattern = r'(\d*)d[fF]((?:[+-]\d+)*)'
    fudge_match = re.fullmatch(fudge_pattern, formula)
    if fudge_match:
        num_dice = int(fudge_match.group(1)) if fudge_match.group(1) else 4
        modifiers_str = fudge_match.group(2) or ""
        modifiers_list = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
        modifier = sum(modifiers_list)
        rolls = [random.choice([-1, 0, 1]) for _ in range(num_dice)]
        symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
        total = sum(rolls) + modifier
        # Compose the detailed formula string
        formula_str = f"{base_roll} `{' '.join(symbols)}`"
        if modifier_descriptions:
            formula_str += " + " + " + ".join(modifier_descriptions)
        response = f'🎲 {formula_str}\n🧮 Total: {total}'
        return response, total

    # Accepts 1d20+3-2, 2d6+1-1, etc.
    pattern = r'(\d*)d(\d+)((?:[+-]\d+)*)'
    match = re.fullmatch(pattern, formula)
    if match:
        num_dice = int(match.group(1)) if match.group(1) else 1
        die_size = int(match.group(2))
        modifiers_str = match.group(3) or ""
        modifiers_list = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
        modifier = sum(modifiers_list)
        if num_dice > 100 or die_size > 1000:
            return "😵 That's a lot of dice. Try fewer.", None
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        total = sum(rolls) + modifier
        # Compose the detailed formula string
        formula_str = f"{base_roll} [{', '.join(str(r) for r in rolls)}]"
        if modifier_descriptions:
            formula_str += " + " + " + ".join(modifier_descriptions)
        response = f'🎲 {formula_str}\n🧮 Total: {total}'
        return response, total

    return "❌ Invalid format. Use like `2d6+3-2`, `1d20+5-1`, `1d100`, or `4df+1`.", None