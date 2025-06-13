import discord
from discord import ui
from core.abstract_models import get_npc_id, get_pc_id
from data import repo
from rpg_systems.generic.generic_sheet import GenericSheet
from rpg_systems.generic.generic_character import GenericCharacter

sheet = GenericSheet()

def get_generic_character(guild_id, char_id):
    character = repo.get_character(guild_id, char_id)
    return character if character else None

class SheetEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id
        self.add_item(EditNameButton(self))
        self.add_item(EditNotesButton(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
            return False
        return True

class EditNameButton(ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="Edit Name", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        character = get_generic_character(interaction.guild.id, self.parent_view.char_id)
        current_name = character.name if character else ""
        await interaction.response.send_modal(EditNameModal(self.parent_view.char_id, current_name))

class EditNotesButton(ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="Edit Notes", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        character = get_generic_character(interaction.guild.id, self.parent_view.char_id)
        notes = "\n".join(character.notes) if character.notes else "_No notes_"
        await interaction.response.send_modal(EditNotesModal(self.parent_view.char_id, notes))

class EditNameModal(ui.Modal, title="Edit Character Name"):
    def __init__(self, char_id: str, current_name: str):
        super().__init__()
        self.char_id = char_id
        self.name_input = ui.TextInput(
            label="New Name",
            default=current_name,
            max_length=100
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_generic_character(interaction.guild.id, self.char_id)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return
        new_name = self.name_input.value.strip()
        if not new_name:
            await interaction.response.send_message("❌ Name cannot be empty.", ephemeral=True)
            return
        character.name = new_name
        repo.set_character(interaction.guild.id, character, system="generic")
        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Name updated.", embed=embed, view=view)

class EditNotesModal(ui.Modal, title="Edit Notes"):
    def __init__(self, char_id: str, notes: str):
        super().__init__()
        self.char_id = char_id
        self.notes_field = ui.TextInput(
            label="Notes",
            style=discord.TextStyle.paragraph,
            required=False,
            default=notes,
            max_length=2000
        )
        self.add_item(self.notes_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_generic_character(interaction.guild.id, self.char_id)
        character.notes = [line for line in self.notes_field.value.splitlines() if line.strip()]
        repo.set_character(interaction.guild.id, character, system="generic")
        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Notes updated.", embed=embed, view=view)