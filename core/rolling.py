from abc import ABC
from typing import TYPE_CHECKING, Dict

if TYPE_CHECKING:
    from core.models import BaseCharacter  # Only for type hints, not at runtime

class RollModifiers(ABC):
    """
    A flexible container for roll parameters (e.g., skill, attribute, modifiers).
    Non-modifier properties (like skill, attribute) are stored in a separate dictionary.
    Modifiers are stored in self.modifiers.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        self.modifiers = {}  # Store direct numeric modifiers (e.g., mod1, mod2)
        if roll_parameters_dict:
            for key, modifier in roll_parameters_dict.items():
                try:
                    value = int(modifier)
                    self.modifiers[key] = value
                except (ValueError, TypeError):
                    continue

    def __getitem__(self, key):
        return self.modifiers.get(key)

    def __setitem__(self, key, value):
        self.modifiers[key] = value

    def to_dict(self):
        return dict(self.modifiers)

    def get_modifiers(self, character: "BaseCharacter") -> Dict[str, int]:
        """
        Returns a dictionary of all modifiers
        """
        return dict(self.modifiers)

    def __repr__(self):
        return f"RollFormula(properties={self.properties}, modifiers={self.modifiers})"