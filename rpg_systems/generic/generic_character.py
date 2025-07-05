from typing import Any, Dict
import discord
from discord import ui
from core.models import BaseCharacter, RollModifiers, EntityDefaults, EntityType
from core.shared_views import EditNameModal, EditNotesModal, FinalizeRollButton, RollModifiersView
from core.utils import get_character, roll_formula

SYSTEM = "generic"

class GenericCharacter(BaseCharacter):
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.PC: { },
        EntityType.NPC: { }
    })

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericCharacter":
        return cls(data)
    
    def apply_defaults(self, entity_type = None, guild_id = None):
        super().apply_defaults(entity_type, guild_id)

        if self.ENTITY_DEFAULTS:
            defaults = self.ENTITY_DEFAULTS.get_defaults(entity_type)
            for key, value in defaults.items():
                self._apply_default_field(key, value, guild_id) 

    def format_full_sheet(self) -> discord.Embed:
        """Format the character sheet for generic system"""
        embed = discord.Embed(
            title=f"{self.name or 'Character'}",
            color=discord.Color.greyple()
        )
        notes = self.notes
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)
        return embed

    def format_npc_scene_entry(self, is_gm: bool) -> str:
        """Format NPC entry for scene display"""
        lines = [f"**{self.name or 'NPC'}**"]
        if is_gm and self.notes:
            notes_display = "\n".join(self.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)

    async def edit_requested_roll(self, interaction: discord.Interaction, roll_formula_obj: "GenericRollModifiers", difficulty: int = None):
        """
        Opens a view for editing the roll parameters.
        Generic version doesn't have skill selection but does allow modifier adjustment.
        """
        view = GenericRollModifiersView(roll_formula_obj, difficulty)
        await interaction.response.send_message(
            content="Adjust your roll formula as needed, then finalize to roll.",
            view=view,
            ephemeral=True
        )

    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollModifiers, difficulty: int = None):
        """
        Prints the roll result
        """
        result, total = roll_formula(self, "1d20", roll_formula_obj)

        difficulty_str = ""
        if difficulty:
            difficulty_str = f" (Needed {difficulty})"
            if total >= difficulty:
                result += f"\n✅ Success.{difficulty_str}"
            else:
                result += f"\n❌ Failure.{difficulty_str}"
        
        await interaction.response.send_message(result, ephemeral=False)

class GenericRollModifiers(RollModifiers):
    """
    A roll formula specifically for the generic RPG system.
    It can handle any roll parameters as needed.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        super().__init__(roll_parameters_dict)

class GenericSheetEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=0)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNameModal(self.char_id, SYSTEM))

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=0)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNotesModal(self.char_id, SYSTEM))

class GenericRollModifiersView(RollModifiersView):
    """
    Generic roll modifiers view with just the basic modifier functionality.
    """
    def __init__(self, roll_formula_obj: RollModifiers, difficulty: int = None):
        super().__init__(roll_formula_obj, difficulty)
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))