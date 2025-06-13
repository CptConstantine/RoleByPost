from core.abstract_models import BaseCharacter
from typing import Any, Dict

class GenericCharacter(BaseCharacter):
    SYSTEM_SPECIFIC_CHARACTER = {}
    SYSTEM_SPECIFIC_NPC = {}

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericCharacter":
        return cls(data)

    def apply_defaults(self, is_npc=False, guild_id=None):
        # No system-specific fields for generic
        pass