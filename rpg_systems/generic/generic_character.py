from typing import Any, Dict
import discord
from discord import ui
from core.models import BaseCharacter, BaseSheet, RollModifiers, EntityDefaults, EntityType
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

    def apply_defaults(self, entity_type: EntityType, guild_id=None):
        """
        Apply system-specific default fields to a character.
        Generic system has no specific fields beyond base character.
        """
        super().apply_defaults(entity_type=entity_type, guild_id=guild_id)

        # Get the appropriate defaults based on entity type
        system_defaults = self.ENTITY_DEFAULTS.get_defaults(entity_type)
        
        # Apply any system-specific defaults (none for generic system)
        for key, value in system_defaults.items():
            current_value = getattr(self, key, None)
            if current_value in (None, [], {}, 0, False):
                setattr(self, key, value)

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

class GenericSheet(BaseSheet):
    def format_full_sheet(self, character: BaseCharacter) -> discord.Embed:
        embed = discord.Embed(
            title=f"{character.name or 'Character'}",
            color=discord.Color.greyple()
        )
        notes = character.notes
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)
        return embed

    def format_npc_scene_entry(self, npc: BaseCharacter, is_gm: bool):
        lines = [f"**{npc.name or 'NPC'}**"]
        if is_gm and npc.notes:
            notes_display = "\n".join(npc.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)

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
        character = get_character(self.char_id)
        await interaction.response.send_modal(
            EditNameModal(
                self.char_id,
                character.name if character else "",
                SYSTEM,
                lambda editor_id, char_id: (GenericSheet().format_full_sheet(get_character(char_id)), GenericSheetEditView(editor_id, char_id))
            )
        )

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=0)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(self.char_id)
        notes = "\n".join(character.notes) if character and character.notes else ""
        await interaction.response.send_modal(
            EditNotesModal(
                self.char_id,
                notes,
                SYSTEM,
                lambda editor_id, char_id: (GenericSheet().format_full_sheet(get_character(char_id)), GenericSheetEditView(editor_id, char_id))
            )
        )

class GenericRollModifiersView(RollModifiersView):
    """
    Generic roll modifiers view with just the basic modifier functionality.
    """
    def __init__(self, roll_formula_obj: RollModifiers, difficulty: int = None):
        super().__init__(roll_formula_obj, difficulty)
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))