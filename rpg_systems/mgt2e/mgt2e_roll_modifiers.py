from typing import Dict
from core.models import RollModifiers
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rpg_systems.mgt2e.mgt2e_character import MGT2ECharacter

class MGT2ERollModifiers(RollModifiers):
    """
    A roll formula specifically for the MGT2E RPG system.
    It can handle any roll parameters as needed.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        super().__init__(roll_parameters_dict)
        self.skill = roll_parameters_dict.get("skill") if roll_parameters_dict else None
        self.attribute = roll_parameters_dict.get("attribute") if roll_parameters_dict else None

    def get_modifiers(self, character: "MGT2ECharacter") -> Dict[str, str]:
        modifiers = super().get_modifiers(character).items()
        if self.skill:
            skill_value = character.skills.get(self.skill, 0)
            modifiers = list(modifiers) + [(self.skill, skill_value)]
        if self.attribute:
            attribute_value = character.attributes.get(self.attribute, 0)
            modifiers = list(modifiers) + [(self.attribute, character.get_attribute_modifier(attribute_value))]
        return dict(modifiers)
