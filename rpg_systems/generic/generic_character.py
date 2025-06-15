from typing import Any, Dict
import discord
from discord import ui
from core.models import BaseCharacter, BaseSheet, RollFormula
from core.shared_views import EditNameModal, EditNotesModal, RollFormulaView
from core.utils import get_character, roll_formula
from core.rolling import RollFormula

SYSTEM = "generic"

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
        roll_formula_obj = GenericRollFormula(roll_parameters_dict=roll_parameters)
        view = GenericRollFormulaView(roll_formula_obj, self, interaction, difficulty)
        await interaction.response.send_message(
            content="Adjust your roll formula as needed, then finalize to roll.",
            view=view,
            ephemeral=True
        )

    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollFormula, difficulty: int = None):
        # Build the formula string from the RollFormula object
        # Example: "1d20+3+2-1"
        formula_parts = []
        formula_parts.append("1d20") # Change this to allow user to enter it
        for k, v in roll_formula_obj.get_modifiers(self).items():
            try:
                mod = int(v)
                if mod >= 0:
                    formula_parts.append(f"+{mod}")
                else:
                    formula_parts.append(f"{mod}")
            except Exception:
                continue
        formula = "".join(formula_parts)
        result, total = roll_formula(formula) # Send the formula string to be rolled
        if total is not None and difficulty is not None:
            if total >= difficulty:
                result += f"\n✅ Success! (Needed {difficulty})"
            else:
                result += f"\n❌ Failure. (Needed {difficulty})"
        await interaction.response.send_message(result, ephemeral=False)

class GenericRollFormula(RollFormula):
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
        #self.add_item(EditNameButton(self))
        #self.add_item(EditNotesButton(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=0)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        await interaction.response.send_modal(
            EditNameModal(
                self.char_id,
                character.name if character else "",
                SYSTEM,
                lambda editor_id, char_id: (GenericSheet().format_full_sheet(get_character(interaction.guild.id, char_id)), GenericSheetEditView(editor_id, char_id))
            )
        )

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=0)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        notes = "\n".join(character.notes) if character and character.notes else ""
        await interaction.response.send_modal(
            EditNotesModal(
                self.char_id,
                notes,
                SYSTEM,
                lambda editor_id, char_id: (GenericSheet().format_full_sheet(get_character(interaction.guild.id, char_id)), GenericSheetEditView(editor_id, char_id))
            )
        )

class GenericRollFormulaView(RollFormulaView):
    def __init__(self, roll_formula_obj: RollFormula, character, original_interaction, difficulty: int = None):
        super().__init__(roll_formula_obj, character, original_interaction, difficulty)
        self.add_item(FinalizeRollButton(self))

class FinalizeRollButton(discord.ui.Button):
    def __init__(self, parent_view: RollFormulaView):
        super().__init__(label="Finalize Roll", style=discord.ButtonStyle.success)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Update the roll_formula_obj with the latest values from the inputs
        for key, input_box in self.parent_view.modifier_inputs.items():
            value = input_box.value
            if value is not None and value != "":
                self.parent_view.roll_formula_obj[key] = value
        # Call the character's finalize_roll method
        await self.parent_view.character.send_roll_message(
            interaction,
            self.parent_view.roll_formula_obj,
            self.parent_view.difficulty
        )
        self.parent_view.stop()