from discord import ui
import discord
from data import repo
from rpg_systems.mgt2e.mgt2e_sheet import MGT2ESheet

SYSTEM = "mgt2e"
sheet = MGT2ESheet()

class SheetEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=1)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        character = repo.get_character(interaction.guild.id, self.char_id)
        current_name = character.get("name")
        await interaction.response.send_modal(EditNameModal(self.char_id, current_name))

    @ui.button(label="Edit Attributes", style=discord.ButtonStyle.secondary, row=1)
    async def edit_attributes(self, interaction: discord.Interaction, button: ui.Button):
        character = repo.get_character(interaction.guild.id, self.char_id)
        attrs = character.get("attributes", {})
        await interaction.response.send_modal(EditAttributesModal(self.char_id, attrs))

    @ui.button(label="Edit Skills", style=discord.ButtonStyle.secondary, row=1)
    async def edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        character = repo.get_character(interaction.guild.id, self.char_id)
        skills = character.get("skills", {})
        await interaction.response.send_modal(EditSkillsModal(self.char_id, skills))

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=2)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        character = repo.get_character(interaction.guild.id, self.char_id)
        # Only allow owner or GM
        if (interaction.user.id != int(character.get("owner_id")) and
            not repo.is_gm(interaction.guild.id, interaction.user.id)):
            await interaction.response.send_message("❌ Only the owner or a GM can edit notes.", ephemeral=True)
            return
        notes = character.get("notes", "")
        await interaction.response.send_modal(EditNotesModal(self.char_id, notes))


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
        character = repo.get_character(interaction.guild.id, self.char_id)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return

        new_name = self.name_input.value.strip()
        if not new_name:
            await interaction.response.send_message("❌ Name cannot be empty.", ephemeral=True)
            return

        character["name"] = new_name
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)

        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Name updated.", embed=embed, view=view)


class EditAttributesModal(ui.Modal, title="Edit Attributes"):
    def __init__(self, char_id: str, attrs: dict):
        super().__init__()
        self.char_id = char_id
        # Combine all attributes into one field for user input
        default = f"{attrs.get('STR', 0)} {attrs.get('DEX', 0)} {attrs.get('END', 0)} {attrs.get('INT', 0)} {attrs.get('EDU', 0)} {attrs.get('SOC', 0)}"
        self.attr_field = ui.TextInput(
            label="STR DEX END INT EDU SOC (space-separated)",
            required=True,
            default=default,
            max_length=50
        )
        self.add_item(self.attr_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        try:
            values = [int(x) for x in self.attr_field.value.strip().split()]
            if len(values) != 6:
                raise ValueError
            character["attributes"] = {
                "STR": values[0],
                "DEX": values[1],
                "END": values[2],
                "INT": values[3],
                "EDU": values[4],
                "SOC": values[5],
            }
        except Exception:
            await interaction.response.send_message("❌ Please enter 6 integers separated by spaces (e.g. `8 7 6 5 4 3`).", ephemeral=True)
            return
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Attributes updated.", embed=embed, view=view)


class EditSkillsModal(ui.Modal, title="Edit Skills"):
    def __init__(self, char_id: str, skills: dict):
        super().__init__()
        self.char_id = char_id
        self.skills_field = ui.TextInput(
            label="Skills (format: Skill1:2,Skill2:1)",
            required=False,
            default=", ".join(f"{k}:{v}" for k, v in skills.items())
        )
        self.add_item(self.skills_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        skills_dict = {}
        for entry in self.skills_field.value.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        character["skills"] = skills_dict
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Skills updated!", embed=embed, view=view)


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
        character = repo.get_character(interaction.guild.id, self.char_id)
        character["notes"] = self.notes_field.value
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Notes updated.", embed=embed, view=view)