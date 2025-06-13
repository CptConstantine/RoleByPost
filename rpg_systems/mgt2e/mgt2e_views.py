from discord import ui, SelectOption
import discord
from core.abstract_models import get_npc_id, get_pc_id
from data import repo
from rpg_systems.mgt2e.mgt2e_sheet import MGT2ESheet
from rpg_systems.mgt2e.mgt2e_character import MGT2ECharacter
from collections import defaultdict
from core.shared_views import PaginatedSelectView


SYSTEM = "mgt2e"
sheet = MGT2ESheet()


def get_mgt2e_character(guild_id, char_id):
    character = repo.get_character(guild_id, char_id)
    return character if character else None

def get_skill_categories(skills_dict):
    categories = defaultdict(list)
    for skill in skills_dict:
        if "(" in skill and ")" in skill:
            group = skill.split("(", 1)[0].strip()
            categories[group].append(skill)
        else:
            categories[skill].append(skill)
    return categories

class SheetEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id
        self.add_item(RollButton(char_id, editor_id))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Attributes", style=discord.ButtonStyle.secondary, row=1)
    async def edit_attributes(self, interaction: discord.Interaction, button: ui.Button):
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        attrs = character.attributes if character else {}
        await interaction.response.send_modal(EditAttributesModal(self.char_id, attrs))

    @ui.button(label="Edit Skills", style=discord.ButtonStyle.secondary, row=1)
    async def edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        skills = character.skills if character else {}
        categories = get_skill_categories(sheet.DEFAULT_SKILLS)
        category_options = [SelectOption(label=cat, value=cat) for cat in sorted(categories.keys())]

        async def on_category_selected(view, interaction, category):
            skills_in_cat = categories[category]
            skill_options = [SelectOption(label=skill, value=skill) for skill in sorted(skills_in_cat)]
            async def on_skill_selected(view2, interaction2, skill):
                await interaction2.response.send_modal(EditSkillValueModal(self.char_id, skill))
            await interaction.response.edit_message(
                content=f"Select a skill in {category}:",
                view=PaginatedSelectView(skill_options, on_skill_selected, interaction.user.id, prompt=f"Select a skill in {category}:")
            )

        await interaction.response.send_message(
            "Select a skill category:",
            view=PaginatedSelectView(category_options, on_category_selected, interaction.user.id, prompt="Select a skill category:"),
            ephemeral=True
        )

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=2)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        # Only allow owner or GM
        if (interaction.user.id != int(character.owner_id) and
            not repo.is_gm(interaction.guild.id, interaction.user.id)):
            await interaction.response.send_message("❌ Only the owner or a GM can edit notes.", ephemeral=True)
            return
        notes = "\n".join(character.notes) if character and character.notes else ""
        await interaction.response.send_modal(EditNotesModal(self.char_id, notes))

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=2)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        current_name = character.name if character else ""
        await interaction.response.send_modal(EditNameModal(self.char_id, current_name))

class RollButton(ui.Button):
    def __init__(self, char_id, editor_id):
        super().__init__(label="Roll", style=discord.ButtonStyle.primary, row=0)
        self.char_id = char_id
        self.editor_id = editor_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can’t roll for this character.", ephemeral=True)
            return
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        skills = character.get_skills() if character else {}
        categories = get_skill_categories(skills)
        category_options = [SelectOption(label=cat, value=cat) for cat in sorted(categories.keys())]

        async def on_category_selected(view, interaction, category):
            skills_in_cat = categories[category]
            skill_options = [SelectOption(label=skill, value=skill) for skill in sorted(skills_in_cat)]
            async def on_skill_selected(view2, interaction2, skill):
                attributes = character.get_attributes() if character else {}
                attr_options = [SelectOption(label=k, value=k) for k in sorted(attributes.keys())]
                async def on_attr_selected(view3, interaction3, attr):
                    result = sheet.roll(character, skill=skill, attribute=attr)
                    await interaction3.response.send_message(result, ephemeral=True)
                await interaction2.response.edit_message(
                    content=f"Select an attribute to roll with {skill}:",
                    view=PaginatedSelectView(attr_options, on_attr_selected, interaction.user.id, prompt=f"Select an attribute to roll with {skill}:")
                )
            await interaction.response.edit_message(
                content=f"Select a skill in {category} to roll:",
                view=PaginatedSelectView(skill_options, on_skill_selected, interaction.user.id, prompt=f"Select a skill in {category} to roll:")
            )

        await interaction.response.send_message(
            "Select a skill category to roll:",
            view=PaginatedSelectView(category_options, on_category_selected, interaction.user.id, prompt="Select a skill category to roll:"),
            ephemeral=True
        )

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
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return

        new_name = self.name_input.value.strip()
        if not new_name:
            await interaction.response.send_message("❌ Name cannot be empty.", ephemeral=True)
            return

        character.name = new_name
        repo.set_character(interaction.guild.id, character, system=SYSTEM)

        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Name updated.", embed=embed, view=view)

class EditAttributesModal(ui.Modal, title="Edit Attributes"):
    def __init__(self, char_id: str, attrs: dict):
        super().__init__()
        self.char_id = char_id
        default = f"{attrs.get('STR', 0)} {attrs.get('DEX', 0)} {attrs.get('END', 0)} {attrs.get('INT', 0)} {attrs.get('EDU', 0)} {attrs.get('SOC', 0)}"
        self.attr_field = ui.TextInput(
            label="STR DEX END INT EDU SOC (space-separated)",
            required=True,
            default=default,
            max_length=50
        )
        self.add_item(self.attr_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        try:
            values = [int(x) for x in self.attr_field.value.strip().split()]
            if len(values) != 6:
                raise ValueError
            character.attributes = {
                "STR": values[0],
                "DEX": values[1],
                "END": values[2],
                "INT": values[3],
                "EDU": values[4],
                "SOC": values[5],
            }  # Use property setter
        except Exception:
            await interaction.response.send_message("❌ Please enter 6 integers separated by spaces (e.g. `8 7 6 5 4 3`).", ephemeral=True)
            return
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
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
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        skills_dict = {}
        for entry in self.skills_field.value.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        character.skills = skills_dict  # Use property setter
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
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
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        # Notes are now a list, so split lines and assign
        character.notes = [line for line in self.notes_field.value.splitlines() if line.strip()]
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Notes updated.", embed=embed, view=view)

class EditSkillValueModal(ui.Modal, title="Edit Skill Value"):
    def __init__(self, char_id: str, skill: str):
        super().__init__()
        self.char_id = char_id
        self.skill = skill
        label = f"{skill} value (0 - 5 or 'untrained')"
        if len(label) > 45:
            label = label[:42] + "..."
        self.value_field = ui.TextInput(
            label=label,
            required=True,
            max_length=10
        )
        self.add_item(self.value_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_mgt2e_character(interaction.guild.id, self.char_id)
        value = self.value_field.value.strip()
        try:
            skills = character.skills  # Use property
            if value.lower() == "untrained":
                skills[self.skill] = -3
            else:
                skills[self.skill] = int(value)
            character.skills = skills  # Save back using property setter
        except Exception:
            await interaction.response.send_message("❌ Please enter a number or 'untrained'.", ephemeral=True)
            return
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        embed = sheet.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content=f"✅ {self.skill} updated.", embed=embed, view=view)