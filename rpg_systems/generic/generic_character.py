import discord
from core.models import BaseCharacter
from typing import Any, Dict
from core.shared_views import RollFormulaModal

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

    async def request_roll(self, interaction: discord.Interaction, roll_parameters: dict = None, difficulty: int = None):
        # Ask for a roll formula
        await interaction.response.send_modal(RollFormulaModal(difficulty=difficulty))