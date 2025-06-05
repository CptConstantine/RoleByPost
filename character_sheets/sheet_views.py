from discord import ui
import discord
import character_sheets.sheet_utils as sheet_utils
import json


class SheetEditView(ui.View):
    def __init__(self, editor_id: int, char_type: str, char_id: str, display_name: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id  # Who's editing
        self.char_type = char_type  # "characters" or "npcs"
        self.char_id = char_id
        self.display_name = display_name

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Stress", style=discord.ButtonStyle.primary, row=1)
    async def edit_stress(self, interaction: discord.Interaction, button: ui.Button):
        # Show a modal for editing stress
        await interaction.response.send_modal(EditStressModal(self.char_type, self.char_id))
    
    @ui.button(label="Edit Consequences", style=discord.ButtonStyle.primary, row=1)
    async def edit_consequences(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing consequences:", view=EditConsequencesView(self.editor_id, self.char_type, self.char_id))

    @ui.button(label="Edit Fate Points", style=discord.ButtonStyle.primary, row=1)
    async def edit_fp(self, interaction: discord.Interaction, button: ui.Button):
        # Show a modal for editing fate points
        await interaction.response.send_modal(EditFatePointsModal(self.char_type, self.char_id))

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=2)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        data = sheet_utils.load_character_data()
        entry = data[self.char_type].get(self.char_id)
        current_name = entry.get("name", self.display_name)
        await interaction.response.send_modal(EditNameModal(self.char_type, self.char_id, current_name))

    @ui.button(label="Edit Aspects", style=discord.ButtonStyle.secondary, row=2)
    async def edit_aspects(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing aspects:", view=EditAspectsView(self.editor_id, self.char_type, self.char_id))
    
    @ui.button(label="Edit Skills", style=discord.ButtonStyle.secondary, row=2)
    async def edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        # Show a modal for editing skills
        await interaction.response.send_modal(EditSkillsModal(self.char_type, self.char_id))


class EditNameModal(ui.Modal, title="Edit Character Name"):
    def __init__(self, char_type: str, char_id: str, current_name: str):
        super().__init__()
        self.char_type = char_type  # "characters" or "npcs"
        self.char_id = char_id

        self.name_input = ui.TextInput(
            label="New Name",
            default=current_name,
            max_length=100
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: discord.Interaction):
        data = sheet_utils.load_character_data()
        entry = data[self.char_type].get(self.char_id)
        if not entry:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return

        new_name = self.name_input.value.strip()
        if not new_name:
            await interaction.response.send_message("❌ Name cannot be empty.", ephemeral=True)
            return

        entry["name"] = new_name
        sheet_utils.save_character_data(data)

        embed = sheet_utils.format_full_sheet(new_name, entry)
        view = SheetEditView(interaction.user.id, self.char_type, self.char_id, new_name)
        await interaction.response.edit_message(content="✅ Name updated.", embed=embed, view=view)


    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=1)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        data = sheet_utils.load_character_data()
        entry = data[self.char_type].get(self.char_id)
        current_name = entry.get("name", self.display_name)
        await interaction.response.send_modal(EditNameModal(self.char_type, self.char_id, current_name))


class EditAspectsView(ui.View):
    def __init__(self, user_id: int, char_type: str, char_id: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.char_type = char_type
        self.char_id = char_id
        self.page = 0

        self.data = sheet_utils.load_character_data()
        self.char = self.data[char_type].get(char_id, {})
        self.aspects = self.char.get("aspects", [])
        self.hidden_aspects = self.char.setdefault("hidden_aspects", [])

        self.max_page = max(0, len(self.aspects) - 1)
        self.render()

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

        # Re-attach callbacks manually
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id:
                item.callback = self.make_callback(item.custom_id)

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
                return

            if cid == "prev":
                self.page = max(0, self.page - 1)
            elif cid == "next":
                self.page = min(self.max_page, self.page + 1)
            elif cid == "edit":
                await interaction.response.send_modal(EditAspectModal(self.char_type, self.char_id, self.page, self.aspects[self.page]))
                return
            elif cid == "remove":
                if self.page in self.hidden_aspects:
                    self.hidden_aspects.remove(self.page)
                del self.aspects[self.page]
                # Adjust hidden_aspects indices after removal
                self.hidden_aspects = [i-1 if i > self.page else i for i in self.hidden_aspects if i != self.page]
                self.char["aspects"] = self.aspects
                self.char["hidden_aspects"] = self.hidden_aspects
                sheet_utils.save_character_data(self.data)
                self.page = max(0, self.page - 1)
            elif cid == "toggle_hidden":
                if self.page in self.hidden_aspects:
                    self.hidden_aspects.remove(self.page)
                else:
                    self.hidden_aspects.append(self.page)
                self.char["hidden_aspects"] = self.hidden_aspects
                sheet_utils.save_character_data(self.data)
            elif cid == "add":
                await interaction.response.send_modal(AddAspectModal(self.char_type, self.char_id))
                return
            elif cid == "done":
                await interaction.response.edit_message(content="✅ Done editing aspects.", embed=sheet_utils.format_full_sheet(self.char["name"], self.char), view=None)
                return

            sheet_utils.save_character_data(self.data)
            self.char = self.data[self.char_type].get(self.char_id, {})
            self.aspects = self.char.get("aspects", [])
            self.hidden_aspects = self.char.setdefault("hidden_aspects", [])
            self.max_page = max(0, len(self.aspects) - 1)
            self.render()
            await interaction.response.edit_message(embed=sheet_utils.format_full_sheet(self.char["name"], self.char), view=self)

        return callback


class EditAspectModal(ui.Modal, title="Edit Aspects"):
    def __init__(self, char_type: str, char_id: str, index: int, current: str):
        super().__init__()
        self.char_type = char_type
        self.char_id = char_id
        self.index = index
        self.add_item(ui.TextInput(label="Aspect", default=current, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        data = sheet_utils.load_character_data()
        entry = data[self.char_type].get(self.char_id)
        aspects = entry.get("aspects", [])
        if self.index >= len(aspects):
            await interaction.response.send_message("❌ Aspect not found.", ephemeral=True)
            return

        aspects[self.index] = self.children[0].value.strip()
        entry["aspects"] = aspects
        sheet_utils.save_character_data(data)

        await interaction.response.edit_message(content="✅ Aspect updated.", view=EditAspectsView(interaction.user.id, self.char_type, self.char_id))


class AddAspectModal(ui.Modal, title="Add Aspect"):
    def __init__(self, char_type: str, char_id: str):
        super().__init__()
        self.char_type = char_type
        self.char_id = char_id
        self.add_item(ui.TextInput(label="New Aspect", max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        data = sheet_utils.load_character_data()
        entry = data[self.char_type].get(self.char_id)
        aspects = entry.get("aspects", [])
        aspects.append(self.children[0].value.strip())
        sheet_utils.save_character_data(data)

        await interaction.response.edit_message(content="✅ Aspect added.", view=EditAspectsView(interaction.user.id, self.char_type, self.char_id))


class EditSkillsModal(ui.Modal, title="Edit Skills"):
    skills = ui.TextInput(label="Skills (format: Skill1:2,Skill2:1)", required=False)

    def __init__(self, char_type, char_id):
        super().__init__()
        self.char_type = char_type
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        data = sheet_utils.load_character_data()
        char = data[self.char_type][self.char_id]
        skills_dict = {}
        for entry in self.skills.value.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        char["skills"] = skills_dict
        sheet_utils.save_character_data(data)
        await interaction.response.send_message("✅ Skills updated!", ephemeral=True)


class EditStressModal(ui.Modal, title="Edit Stress"):
    physical = ui.TextInput(label="Physical Stress (e.g. 0 1 0)", required=False)
    mental = ui.TextInput(label="Mental Stress (e.g. 1 0)", required=False)

    def __init__(self, char_type, char_id):
        super().__init__()
        self.char_type = char_type
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        data = sheet_utils.load_character_data()
        char = data[self.char_type][self.char_id]
        char["stress"]["physical"] = [bool(int(x)) for x in self.physical.value.split()]
        char["stress"]["mental"] = [bool(int(x)) for x in self.mental.value.split()]
        sheet_utils.save_character_data(data)
        await interaction.response.send_message("✅ Stress updated!", ephemeral=True)


class EditFatePointsModal(ui.Modal, title="Edit Fate Points"):
    fate_points = ui.TextInput(label="Fate Points", required=True)

    def __init__(self, char_type, char_id):
        super().__init__()
        self.char_type = char_type
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        data = sheet_utils.load_character_data()
        char = data[self.char_type][self.char_id]
        try:
            char["fate_points"] = int(self.fate_points.value)
        except ValueError:
            await interaction.response.send_message("❌ Invalid number.", ephemeral=True)
            return
        sheet_utils.save_character_data(data)
        await interaction.response.send_message("✅ Fate Points updated!", ephemeral=True)


class EditConsequenceModal(ui.Modal, title="Edit Consequence"):
    def __init__(self, char_type: str, char_id: str, index: int, current: str):
        super().__init__()
        self.char_type = char_type
        self.char_id = char_id
        self.index = index
        self.add_item(ui.TextInput(label="Consequence", default=current, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        data = sheet_utils.load_character_data()
        entry = data[self.char_type].get(self.char_id)
        consequences = entry.get("consequences", [])
        if self.index >= len(consequences):
            await interaction.response.send_message("❌ Consequence not found.", ephemeral=True)
            return

        consequences[self.index] = self.children[0].value.strip()
        entry["consequences"] = consequences
        sheet_utils.save_character_data(data)

        await interaction.response.edit_message(content="✅ Consequence updated.", view=EditConsequencesView(interaction.user.id, self.char_type, self.char_id))


class AddConsequenceModal(ui.Modal, title="Add Consequence"):
    def __init__(self, char_type: str, char_id: str):
        super().__init__()
        self.char_type = char_type
        self.char_id = char_id
        self.add_item(ui.TextInput(label="New Consequence", max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        data = sheet_utils.load_character_data()
        entry = data[self.char_type].get(self.char_id)
        consequences = entry.setdefault("consequences", [])
        consequences.append(self.children[0].value.strip())
        sheet_utils.save_character_data(data)

        await interaction.response.edit_message(content="✅ Consequence added.", view=EditConsequencesView(interaction.user.id, self.char_type, self.char_id))


class EditConsequencesView(ui.View):
    def __init__(self, user_id: int, char_type: str, char_id: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.char_type = char_type
        self.char_id = char_id
        self.page = 0

        self.data = sheet_utils.load_character_data()
        self.char = self.data[char_type].get(char_id, {})
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

        # Re-attach callbacks manually
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id:
                item.callback = self.make_callback(item.custom_id)

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can’t edit this character.", ephemeral=True)
                return

            if cid == "prev":
                self.page = max(0, self.page - 1)
            elif cid == "next":
                self.page = min(self.max_page, self.page + 1)
            elif cid == "edit":
                await interaction.response.send_modal(EditConsequenceModal(self.char_type, self.char_id, self.page, self.consequences[self.page]))
                return
            elif cid == "remove":
                del self.consequences[self.page]
                self.char["consequences"] = self.consequences
                sheet_utils.save_character_data(self.data)
                self.page = max(0, self.page - 1)
            elif cid == "add":
                await interaction.response.send_modal(AddConsequenceModal(self.char_type, self.char_id))
                return
            elif cid == "done":
                await interaction.response.edit_message(content="✅ Done editing consequences.", view=None)
                return

            sheet_utils.save_character_data(self.data)
            self.char = self.data[self.char_type].get(self.char_id, {})
            self.consequences = self.char.get("consequences", [])
            self.max_page = max(0, len(self.consequences) - 1)
            self.render()
            await interaction.response.edit_message(view=self)

        return callback