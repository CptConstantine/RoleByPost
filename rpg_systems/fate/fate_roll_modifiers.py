from typing import Dict
from core.models import RollModifiers
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rpg_systems.fate.fate_character import FateCharacter

class FateRollModifiers(RollModifiers):
    """
    A roll formula specifically for the Fate RPG system.
    It can handle any roll parameters as needed.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        super().__init__(roll_parameters_dict)
        self.skill = roll_parameters_dict.get("skill") if roll_parameters_dict else None

    def get_modifiers(self, character: "FateCharacter") -> Dict[str, str]:
        modifiers = super().get_modifiers(character).items()
        if self.skill:
            skill_value = character.skills.get(self.skill)
            modifiers = list(modifiers) + [(self.skill, skill_value)]
        return dict(modifiers)