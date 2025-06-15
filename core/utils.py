import random
import re
from data import repo


def get_character(guild_id, char_id):
    character = repo.get_character_by_id(guild_id, char_id)
    return character if character else None

def roll_formula(formula: str):
    """
    Parses and rolls a dice formula like '2d6+3-2', '1d20+5-1', '1d100', etc.
    Returns a tuple: (result_string, total)
    """
    import re, random

    formula = formula.replace(" ", "").lower()
    fudge_pattern = r'(\d*)d[fF]((?:[+-]\d+)*)'
    fudge_match = re.fullmatch(fudge_pattern, formula)
    if fudge_match:
        num_dice = int(fudge_match.group(1)) if fudge_match.group(1) else 4
        modifiers_str = fudge_match.group(2) or ""
        modifiers = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
        modifier = sum(modifiers)
        rolls = [random.choice([-1, 0, 1]) for _ in range(num_dice)]
        symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
        total = sum(rolls) + modifier
        response = f'🎲 Fudge Rolls: `{" ".join(symbols)}`'
        if modifier:
            response += f' {"+" if modifier > 0 else ""}{modifier}'
        response += f'\n🧮 Total: {total}'
        return response, total

    # Accepts 1d20+3-2, 2d6+1-1, etc.
    pattern = r'(\d*)d(\d+)((?:[+-]\d+)*)'
    match = re.fullmatch(pattern, formula)
    if match:
        num_dice = int(match.group(1)) if match.group(1) else 1
        die_size = int(match.group(2))
        modifiers_str = match.group(3) or ""
        modifiers = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
        modifier = sum(modifiers)
        if num_dice > 100 or die_size > 1000:
            return "😵 That's a lot of dice. Try fewer.", None
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        total = sum(rolls) + modifier
        response = f'🎲 Rolled: {rolls}'
        if modifier:
            response += f' {"+" if modifier > 0 else ""}{modifier}'
        response += f'\n🧮 Total: {total}'
        return response, total

    return "❌ Invalid format. Use like `2d6+3-2`, `1d20+5-1`, `1d100`, or `4df+1`.", None