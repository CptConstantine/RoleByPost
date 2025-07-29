from typing import Dict
from core.base_models import RollFormula
from typing import TYPE_CHECKING

from core.generic_roll_mechanics import CoreRollMechanicType, RollMechanicConfig, SuccessCriteria

if TYPE_CHECKING:
    from rpg_systems.fate.fate_character import FateCharacter

class FateRollFormula(RollFormula):
    """
    A roll formula specifically for the Fate RPG system.
    It can handle any roll parameters as needed.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        roll_config = RollMechanicConfig(
            mechanic_type=CoreRollMechanicType.ROLL_AND_SUM,
            dice_formula="4dF",  # Default Fate roll
            success_criteria=SuccessCriteria.GREATER_EQUAL
        )
        super().__init__(roll_config, roll_parameters_dict)
        self.skill = roll_parameters_dict.get("skill") if roll_parameters_dict else None

    def get_modifiers(self, character: "FateCharacter") -> Dict[str, str]:
        modifiers = super().get_modifiers(character).items()
        if self.skill:
            skill_value = character.skills.get(self.skill)
            modifiers = list(modifiers) + [(self.skill, skill_value)]
        return dict(modifiers)
    
    def get_total_dice_formula(self):
        formula = super().get_total_dice_formula()
        # Get the skill value and append it to the formula
        if self.skill:
            formula += f"+{self.skill}"
        return formula