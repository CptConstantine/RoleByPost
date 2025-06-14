import random
import re
from data import repo


def get_character(guild_id, char_id):
    character = repo.get_character_by_id(guild_id, char_id)
    return character if character else None

def roll_formula(formula: str):
    """
    Parses and rolls a dice formula like '2d6+3' or 'd20-1'.
    Returns a tuple: (result_string, total)
    """
    formula = formula.replace(" ", "").lower()
    fudge_pattern = r'(\d*)d[fF]([+-]\d+)?'
    fudge_match = re.fullmatch(fudge_pattern, formula)
    if fudge_match:
        num_dice = int(fudge_match.group(1)) if fudge_match.group(1) else 4
        modifier = int(fudge_match.group(2)) if fudge_match.group(2) else 0
        rolls = [random.choice([-1, 0, 1]) for _ in range(num_dice)]
        symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
        total = sum(rolls) + modifier
        response = f'🎲 Fudge Rolls: `{" ".join(symbols)}`'
        if modifier:
            response += f' {"+" if modifier > 0 else ""}{modifier}'
        response += f'\n🧮 Total: {total}'
        return response, total

    pattern = r'(\d*)d(\d+)([+-]\d+)?'
    match = re.fullmatch(pattern, formula)
    if match:
        num_dice = int(match.group(1)) if match.group(1) else 1
        die_size = int(match.group(2))
        modifier = int(match.group(3)) if match.group(3) else 0
        if num_dice > 100 or die_size > 1000:
            return "😵 That's a lot of dice. Try fewer.", None
        rolls = [random.randint(1, die_size) for _ in range(num_dice)]
        total = sum(rolls) + modifier
        response = f'🎲 Rolled: {rolls}'
        if modifier:
            response += f' {"+" if modifier > 0 else ""}{modifier}'
        response += f'\n🧮 Total: {total}'
        return response, total

    return "❌ Invalid format. Use like `2d6+3` or `4df+1`.", None