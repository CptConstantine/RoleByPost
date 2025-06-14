import discord
from discord import ui
from core.shared_views import EditNameModal, EditNotesModal, get_character
from data import repo
from rpg_systems.generic.generic_sheet import GenericSheet
from rpg_systems.generic.generic_character import GenericCharacter

SYSTEM = "generic"
sheet = GenericSheet()

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
                lambda editor_id, char_id: (sheet.format_full_sheet(get_character(interaction.guild.id, char_id)), GenericSheetEditView(editor_id, char_id))
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
                lambda editor_id, char_id: (sheet.format_full_sheet(get_character(interaction.guild.id, char_id)), GenericSheetEditView(editor_id, char_id))
            )
        )