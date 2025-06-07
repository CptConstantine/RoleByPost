from discord import ui
import discord
from data import repo
import rpg_systems.fate.sheet_utils as sheet_utils

SYSTEM = "fate"

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

    @ui.button(label="Edit Aspects", style=discord.ButtonStyle.secondary, row=2)
    async def edit_aspects(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing aspects:", view=EditAspectsView(interaction.guild.id, self.editor_id, self.char_id))

    @ui.button(label="Edit Skills", style=discord.ButtonStyle.secondary, row=2)
    async def edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditSkillsModal(self.char_id))

    @ui.button(label="Edit Stress", style=discord.ButtonStyle.primary, row=1)
    async def edit_stress(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditStressModal(self.char_id))

    @ui.button(label="Edit Consequences", style=discord.ButtonStyle.primary, row=1)
    async def edit_consequences(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing consequences:", view=EditConsequencesView(interaction.guild.id, self.editor_id, self.char_id))

    @ui.button(label="Edit Fate Points", style=discord.ButtonStyle.primary, row=1)
    async def edit_fp(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditFatePointsModal(self.char_id))


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

        embed = sheet_utils.format_full_sheet(character)
        view = SheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Name updated.", embed=embed, view=view)


class EditAspectsView(ui.View):
    def __init__(self, guild_id: int, user_id: int, char_id: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.page = 0

        self.char = None
        self.aspects = []
        self.hidden_aspects = []
        self.max_page = 0
        self.load_data()
        self.render()

    def load_data(self):
        # This should be called whenever data might have changed
        self.char = repo.get_character(self.guild_id, self.char_id)
        if not self.char:
            self.aspects = []
            self.hidden_aspects = []
        else:
            self.aspects = self.char.get("aspects", [])
            self.hidden_aspects = self.char.setdefault("hidden_aspects", [])
        self.max_page = max(0, len(self.aspects) - 1)

    def render(self):
        self.clear_items()
        if self.aspects:
            label = f"{self.page + 1}/{len(self.aspects)}: {self.aspects[self.page][:30]}"
            self.add_item(ui.Button(label=label, disabled=True, row=0))
            if self.page > 0:
                self.add_item(ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, row=1, custom_id="prev"))
            if self.page < self.max_page:
                self.add_item(ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, row=1, custom_id="next"))
            self.add_item(ui.Button(label="✏️ Edit", style=discord.ButtonStyle.primary, row=2, custom_id="edit"))
            self.add_item(ui.Button(label="🗑 Remove", style=discord.ButtonStyle.danger, row=2, custom_id="remove"))
            is_hidden = self.page in self.hidden_aspects
            toggle_label = "🙈 Hide" if not is_hidden else "👁 Unhide"
            toggle_style = discord.ButtonStyle.secondary if not is_hidden else discord.ButtonStyle.success
            self.add_item(ui.Button(label=toggle_label, style=toggle_style, row=2, custom_id="toggle_hidden"))
        self.add_item(ui.Button(label="➕ Add New", style=discord.ButtonStyle.success, row=3, custom_id="add"))
        self.add_item(ui.Button(label="✅ Done", style=discord.ButtonStyle.secondary, row=3, custom_id="done"))
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id:
                item.callback = self.make_callback(item.custom_id)

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
                return

            self.char = repo.get_character(interaction.guild.id, self.char_id)
            self.aspects = self.char.get("aspects", [])
            self.hidden_aspects = self.char.setdefault("hidden_aspects", [])

            if cid == "prev":
                self.page = max(0, self.page - 1)
            elif cid == "next":
                self.page = min(self.max_page, self.page + 1)
            elif cid == "edit":
                await interaction.response.send_modal(EditAspectModal(self.char_id, self.page, self.aspects[self.page]))
                return
            elif cid == "remove":
                if self.page in self.hidden_aspects:
                    self.hidden_aspects.remove(self.page)
                del self.aspects[self.page]
                self.char["aspects"] = self.aspects
                self.char["hidden_aspects"] = self.hidden_aspects
                repo.set_character(interaction.guild.id, self.char_id, self.char, system=SYSTEM)
                self.page = max(0, self.page - 1)
            elif cid == "toggle_hidden":
                if self.page in self.hidden_aspects:
                    self.hidden_aspects.remove(self.page)
                else:
                    self.hidden_aspects.append(self.page)
                self.char["hidden_aspects"] = self.hidden_aspects
                repo.set_character(interaction.guild.id, self.char_id, self.char, system=SYSTEM)
            elif cid == "add":
                await interaction.response.send_modal(AddAspectModal(self.char_id))
                return
            elif cid == "done":
                await interaction.response.edit_message(content="✅ Done editing aspects.", embed=sheet_utils.format_full_sheet(self.char), view=SheetEditView(interaction.user.id, self.char_id))
                return

            repo.set_character(interaction.guild.id, self.char_id, self.char, system=SYSTEM)
            self.load_data()
            self.render()
            await interaction.response.edit_message(embed=sheet_utils.format_full_sheet(self.char), view=self)
        return callback

class EditAspectModal(ui.Modal, title="Edit Aspect"):
    def __init__(self, char_id: str, index: int, current: str):
        super().__init__()
        self.char_id = char_id
        self.index = index
        self.add_item(ui.TextInput(label="Aspect", default=current, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        aspects = character.get("aspects", [])
        if self.index >= len(aspects):
            await interaction.response.send_message("❌ Aspect not found.", ephemeral=True)
            return
        aspects[self.index] = self.children[0].value.strip()
        character["aspects"] = aspects
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Aspect updated.", embed=sheet_utils.format_full_sheet(character), view=EditAspectsView(interaction.guild.id, interaction.user.id, self.char_id))

class AddAspectModal(ui.Modal, title="Add Aspect"):
    def __init__(self, char_id: str):
        super().__init__()
        self.char_id = char_id
        self.add_item(ui.TextInput(label="New Aspect", max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        aspects = character.get("aspects", [])
        aspects.append(self.children[0].value.strip())
        character["aspects"] = aspects
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Aspect added.", embed=sheet_utils.format_full_sheet(character), view=EditAspectsView(interaction.guild.id, interaction.user.id, self.char_id))

class EditSkillsModal(ui.Modal, title="Edit Skills"):
    skills = ui.TextInput(label="Skills (format: Skill1:2,Skill2:1)", required=False)

    def __init__(self, char_id):
        super().__init__()
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        skills_dict = {}
        for entry in self.skills.value.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        character["skills"] = skills_dict or []
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Skills updated!", embed=sheet_utils.format_full_sheet(character), view=SheetEditView(interaction.user.id, self.char_id))

class EditStressModal(ui.Modal, title="Edit Stress"):
    physical = ui.TextInput(label="Physical Stress (e.g. 1 1 0)", required=False)
    mental = ui.TextInput(label="Mental Stress (e.g. 1 0)", required=False)

    def __init__(self, char_id):
        super().__init__()
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        character["stress"]["physical"] = [bool(int(x)) for x in self.physical.value.split()]
        character["stress"]["mental"] = [bool(int(x)) for x in self.mental.value.split()]
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Stress updated!", embed=sheet_utils.format_full_sheet(character), view=SheetEditView(interaction.user.id, self.char_id))

class EditFatePointsModal(ui.Modal, title="Edit Fate Points"):
    fate_points = ui.TextInput(label="Fate Points", required=True)

    def __init__(self, char_id):
        super().__init__()
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        try:
            character["fate_points"] = int(self.fate_points.value)
        except ValueError:
            await interaction.response.send_message("❌ Invalid number.", ephemeral=True)
            return
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Fate Points updated.", embed=sheet_utils.format_full_sheet(character), view=SheetEditView(interaction.user.id, self.char_id))

class EditConsequenceModal(ui.Modal, title="Edit Consequence"):
    def __init__(self, char_id: str, index: int, current: str):
        super().__init__()
        self.char_id = char_id
        self.index = index
        self.add_item(ui.TextInput(label="Consequence", default=current, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        consequences = character.get("consequences", [])
        if self.index >= len(consequences):
            await interaction.response.send_message("❌ Consequence not found.", ephemeral=True)
            return
        consequences[self.index] = self.children[0].value.strip()
        character["consequences"] = consequences
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Consequence updated.", view=EditConsequencesView(interaction.guild.id, interaction.user.id, self.char_id))

class AddConsequenceModal(ui.Modal, title="Add Consequence"):
    def __init__(self, char_id: str):
        super().__init__()
        self.char_id = char_id
        self.add_item(ui.TextInput(label="New Consequence", max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        character = repo.get_character(interaction.guild.id, self.char_id)
        consequences = character.setdefault("consequences", [])
        consequences.append(self.children[0].value.strip())
        character["consequences"] = consequences
        repo.set_character(interaction.guild.id, self.char_id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Consequence added.", view=EditConsequencesView(interaction.guild.id, interaction.user.id, self.char_id))

class EditConsequencesView(ui.View):
    def __init__(self, guild_id: int, user_id: int, char_id: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.page = 0

        self.char = repo.get_character(self.guild_id, self.char_id)
        self.consequences = self.char.get("consequences", [])
        self.max_page = max(0, len(self.consequences) - 1)
        self.render()

    def render(self):
        self.clear_items()
        if self.consequences:
            label = f"{self.page + 1}/{len(self.consequences)}: {self.consequences[self.page][:30]}"
            self.add_item(ui.Button(label=label, disabled=True, row=0))
            if self.page > 0:
                self.add_item(ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, row=1, custom_id="prev"))
            if self.page < self.max_page:
                self.add_item(ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, row=1, custom_id="next"))
            self.add_item(ui.Button(label="✏️ Edit", style=discord.ButtonStyle.primary, row=2, custom_id="edit"))
            self.add_item(ui.Button(label="🗑 Remove", style=discord.ButtonStyle.danger, row=2, custom_id="remove"))
        self.add_item(ui.Button(label="➕ Add New", style=discord.ButtonStyle.success, row=3, custom_id="add"))
        self.add_item(ui.Button(label="✅ Done", style=discord.ButtonStyle.secondary, row=3, custom_id="done"))
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id:
                item.callback = self.make_callback(item.custom_id)

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
                return

            self.char = repo.get_character(interaction.guild.id, self.char_id)
            self.consequences = self.char.get("consequences", []) if self.char else []

            if cid == "prev":
                self.page = max(0, self.page - 1)
            elif cid == "next":
                self.page = min(self.max_page, self.page + 1)
            elif cid == "edit":
                await interaction.response.send_modal(EditConsequenceModal(self.char_id, self.page, self.consequences[self.page]))
                return
            elif cid == "remove":
                del self.consequences[self.page]
                self.char["consequences"] = self.consequences
                repo.set_character(interaction.guild.id, self.char_id, self.char, system=SYSTEM)
                self.page = max(0, self.page - 1)
            elif cid == "add":
                await interaction.response.send_modal(AddConsequenceModal(self.char_id))
                return
            elif cid == "done":
                await interaction.response.edit_message(content="✅ Done editing consequences.", embed=sheet_utils.format_full_sheet(self.char), view=SheetEditView(interaction.user.id, self.char_id))
                return

            repo.set_character(interaction.guild.id, self.char_id, self.char, system=SYSTEM)
            self.render()
            await interaction.response.edit_message(view=self)
        return callback