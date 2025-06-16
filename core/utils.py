import re, random
from core.models import BaseCharacter, RollModifiers
from data import repo


def get_character(guild_id, char_id) -> BaseCharacter:
    character = repo.get_character_by_id(guild_id, char_id)
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

def roll_formula(character: BaseCharacter, base_roll: str, modifiers: RollModifiers):
    """
    Parses and rolls a dice formula like '2d6+3-2', '1d20+5-1', '1d100', etc.
    Returns a tuple: (result_string, total)
    The result string breaks out the formula into its elements, e.g.:
    4df (+ - - 0) + Athletics (2) + mod1 (2)
    """
    modifier_descriptions = []
    total_mod = 0

    # Gather all modifiers and their sources
    for key, value in modifiers.get_modifiers(character).items():
        try:
            mod = int(value)
            total_mod += mod
            sign = "+" if mod >= 0 else ""
            modifier_descriptions.append(f"{key} ({sign}{mod})")
        except Exception:
            continue

    # Build the full formula string for rolling
    formula = base_roll
    for key, value in modifiers.get_modifiers(character).items():
        try:
            mod = int(value)
            if mod >= 0:
                formula += f"+{mod}"
            else:
                formula += f"{mod}"
        except Exception:
            continue

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
        formula_str = f"{base_roll} ({', '.join(str(r) for r in rolls)})"
        if modifier_descriptions:
            formula_str += " + " + " + ".join(modifier_descriptions)
        response = f'🎲 {formula_str}\n🧮 Total: {total}'
        return response, total

    return "❌ Invalid format. Use like `2d6+3-2`, `1d20+5-1`, `1d100`, or `4df+1`.", None