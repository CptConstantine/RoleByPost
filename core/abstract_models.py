from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import discord

def get_pc_id(name):
    """Generate a player character ID from a name."""
    return f"pc:{name.lower().replace(' ', '_')}"

def get_npc_id(name):
    """Generate an NPC ID from a name."""
    return f"npc:{name.lower().replace(' ', '_')}"

class NotesMixin:
    def add_note(self, note: str):
        if "notes" not in self.data or not isinstance(self.data["notes"], list):
            self.data["notes"] = []
        self.data["notes"].append(note)

    def get_notes(self) -> List[str]:
        return self.data.get("notes", [])

class BaseRpgObj(ABC, NotesMixin):
    """
    Abstract base class for a "thing".
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseRpgObj":
        """Deserialize an entity from a dict."""
        return cls(data)

    @property
    def id(self) -> str:
        return self.data.get("id")

    @id.setter
    def id(self, value: str):
        self.data["id"] = value

    @property
    def owner_id(self) -> Optional[str]:
        return self.data.get("owner_id")

    @owner_id.setter
    def owner_id(self, value: str):
        self.data["owner_id"] = value

    @property
    def notes(self) -> list:
        return self.data.get("notes", [])

    @notes.setter
    def notes(self, value: list):
        self.data["notes"] = value

class BaseCharacter(BaseRpgObj):
    """
    Abstract base class for a character (PC or NPC).
    System-specific character classes should inherit from this and implement all methods.
    """
    SYSTEM_SPECIFIC_CHARACTER = {}
    SYSTEM_SPECIFIC_NPC = {}

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        if not hasattr(self, 'SYSTEM_SPECIFIC_CHARACTER'):
            raise NotImplementedError("SYSTEM_SPECIFIC_CHARACTER must be defined in the subclass.")
        if not hasattr(self, 'SYSTEM_SPECIFIC_NPC'):
            raise NotImplementedError("SYSTEM_SPECIFIC_NPC must be defined in the subclass.")

    @property
    def name(self) -> str:
        return self.data.get("name")

    @name.setter
    def name(self, value: str):
        self.data["name"] = value
        self.id = get_pc_id(self.data["name"]) if self.is_npc else get_npc_id(self.data["name"])

    @property
    def is_npc(self) -> bool:
        return self.data.get("is_npc", False)

    @is_npc.setter
    def is_npc(self, value: bool):
        self.data["is_npc"] = value

    @abstractmethod
    def apply_defaults(self, is_npc=False, guild_id=None):
        """Apply system-specific default fields to a character dict."""
        pass

class BaseSheet(ABC):
    @abstractmethod
    def format_full_sheet(self, character: Dict[str, Any]) -> discord.Embed:
        """Return a Discord Embed representing the full character sheet."""
        pass

    @abstractmethod
    def format_npc_scene_entry(self, npc: Dict[str, Any], is_gm: bool) -> str:
        """Return a string for displaying an NPC in a scene summary."""
        pass

class BaseInitiative(ABC):
    """
    Abstract base class for initiative.
    System-specific initiative classes should inherit from this and implement all methods.
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseInitiative":
        """Deserialize an entity from a dict."""
        return cls(data)

    @property
    def type(self) -> str:
        return self.data.get("type")

    @type.setter
    def type(self, value: str):
        self.data["type"] = value

    @property
    def remaining_in_round(self) -> list:
        return self.data.get("remaining_in_round", [])

    @remaining_in_round.setter
    def remaining_in_round(self, value: list):
        self.data["remaining_in_round"] = value

    @property
    def round_number(self) -> int:
        # Pythonic: default to 1 if not set
        return self.data.get("round_number", 1)

    @round_number.setter
    def round_number(self, value: int):
        self.data["round_number"] = value

class BaseInitiativeView(ABC, discord.ui.View):
    """
    Abstract base class for initiative views.
    System-specific initiative views should inherit from this and implement all methods.
    """
    def __init__(self, guild_id, channel_id, initiative):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.initiative = initiative

    @abstractmethod
    async def update_view(self, interaction: discord.Interaction):
        """
        Update the initiative view (e.g., after a turn advances).
        Must be implemented by subclasses.
        """
        pass