from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import discord

def get_pc_id(name):
    """Generate a player character ID from a name."""
    return f"pc:{name.lower().replace(' ', '_')}"

def get_npc_id(name):
    """Generate an NPC ID from a name."""
    return f"npc:{name.lower().replace(' ', '_')}"

class BaseCharacter(ABC):
    """
    Abstract base class for a character (PC or NPC).
    System-specific character classes should inherit from this and implement all methods.
    """
    SYSTEM_SPECIFIC_CHARACTER = {}
    SYSTEM_SPECIFIC_NPC = {}

    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseCharacter":
        """Deserialize a character from a dict."""
        return cls(data)

    def get_id(self) -> str:
        return self.data.get("id")

    def get_name(self) -> str:
        return self.data.get("name")

    def get_owner_id(self) -> Optional[str]:
        return self.data.get("owner_id")

    def is_npc(self) -> bool:
        return self.data.get("is_npc", False)

    def get_notes(self) -> str:
        return self.data.get("notes", "")

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.data)

    @abstractmethod
    def apply_defaults(self, is_npc=False, guild_id=None):
        """Apply system-specific default fields to a character dict."""
        pass

class BaseSheet(ABC):
    SYSTEM_SPECIFIC_CHARACTER = {}
    SYSTEM_SPECIFIC_NPC = {}

    @abstractmethod
    def format_full_sheet(self, character: Dict[str, Any]) -> discord.Embed:
        """Return a Discord Embed representing the full character sheet."""
        pass

    @abstractmethod
    def format_npc_scene_entry(self, npc: Dict[str, Any], is_gm: bool) -> str:
        """Return a string for displaying an NPC in a scene summary."""
        pass