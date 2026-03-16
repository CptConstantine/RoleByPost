import discord
import discord.ui as ui
from core.base_models import SystemType
from core.inventory_views import EditInventoryView, EditInventoryViewV2
from core.shared_views import EditNameModal, EditNotesModal, PaginatedSelectView, PaginatedSelectViewV2, embed_to_text
from rpg_systems.mgt2e.mgt2e_character import MGT2ECharacter, get_character, get_skill_categories
from data.repositories.repository_factory import repositories

SYSTEM = SystemType.MGT2E


def _truncate_text(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _add_action_button(action_row: ui.ActionRow, label: str, style: discord.ButtonStyle, callback):
    button = ui.Button(label=label, style=style)
    button.callback = callback
    action_row.add_item(button)
    return button

class MGT2ESheetEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=1)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(self.char_id)
        await interaction.response.send_modal(EditNameModal(self.char_id, SYSTEM))

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=1)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(self.char_id)
        # Only allow owner or GM
        if (interaction.user.id != int(character.owner_id) and not await repositories.server.has_gm_permission(interaction.guild.id, interaction.user)):
            await interaction.response.send_message("❌ Only the owner or a GM can edit notes.", ephemeral=True)
            return
        notes = "\n".join(character.notes) if character and character.notes else ""
        await interaction.response.send_modal(EditNotesModal(self.char_id, SYSTEM))

    @ui.button(label="Edit Attributes", style=discord.ButtonStyle.secondary, row=1)
    async def edit_attributes(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(self.char_id)
        attrs = character.attributes if character else {}
        await interaction.response.send_modal(EditAttributesModal(self.char_id, attrs))

    @ui.button(label="Edit Skills", style=discord.ButtonStyle.secondary, row=1)
    async def edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(self.char_id)
        skills = character.skills if character else {}
        categories = get_skill_categories(MGT2ECharacter.DEFAULT_SKILLS)
        category_options = [discord.SelectOption(label=cat, value=cat) for cat in sorted(categories.keys())]

        async def on_category_selected(view, interaction: discord.Interaction, category):
            skills_in_cat = categories[category]
            
            # If there's only one skill in this category and it's the same as the category name,
            # it means this is a standalone skill with no specialties
            if len(skills_in_cat) == 1 and skills_in_cat[0] == category:
                # Skip the skill selection step and directly open the edit modal
                await interaction.response.send_modal(EditSkillValueModal(self.char_id, category))
            else:
                # Multiple skills or specialties, continue with skill selection
                skill_options = [discord.SelectOption(label=skill, value=skill) for skill in sorted(skills_in_cat)]
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
    
    @ui.button(label="Inventory", style=discord.ButtonStyle.secondary, row=3)
    async def edit_inventory(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing inventory:", view=EditInventoryView(interaction.guild.id, self.editor_id, self.char_id))

class EditAttributesModal(ui.Modal, title="Edit Attributes"):
    def __init__(self, char_id: str, attrs: dict, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id
        default = f"{attrs.get('STR', 0)} {attrs.get('DEX', 0)} {attrs.get('END', 0)} {attrs.get('INT', 0)} {attrs.get('EDU', 0)} {attrs.get('SOC', 0)}"
        self.attr_field = ui.TextInput(
            label="STR DEX END INT EDU SOC (space-separated)",
            required=True,
            default=default,
            max_length=50
        )
        self.add_item(self.attr_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
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
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=MGT2ESheetEditViewV2(
                    editor_id=interaction.user.id,
                    char_id=self.char_id,
                    guild_id=self.guild_id,
                    status_message="✅ Attributes updated."
                )
            )
        else:
            embed = character.format_full_sheet(interaction.guild.id)
            view = MGT2ESheetEditView(interaction.user.id, self.char_id)
            await interaction.response.edit_message(content="✅ Attributes updated.", embed=embed, view=view)

class EditSkillsModal(ui.Modal, title="Edit Skills"):
    def __init__(self, char_id: str, skills: dict, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id
        self.skills_field = ui.TextInput(
            label="Skills (format: Skill1:2,Skill2:1)",
            required=False,
            default=", ".join(f"{k}:{v}" for k, v in skills.items())
        )
        self.add_item(self.skills_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        skills_dict = {}
        for entry in self.skills_field.value.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        character.skills = skills_dict  # Use property setter
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=MGT2ESheetEditViewV2(
                    editor_id=interaction.user.id,
                    char_id=self.char_id,
                    guild_id=self.guild_id,
                    status_message="✅ Skills updated!"
                )
            )
        else:
            embed = character.format_full_sheet(interaction.guild.id)
            view = MGT2ESheetEditView(interaction.user.id, self.char_id)
            await interaction.response.edit_message(content="✅ Skills updated!", embed=embed, view=view)

class EditSkillValueModal(ui.Modal, title="Edit Skill Value"):
    def __init__(self, char_id: str, skill: str, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.skill = skill
        self.guild_id = guild_id
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
        character = get_character(self.char_id)
        value = self.value_field.value.strip()
        try:
            skills = character.skills  # Use property
            if value.lower() == "untrained":
                skills[self.skill] = -3
                
                # If this skill is a specialty (has parentheses), 
                # we should update other specialties in the same category to untrained as well
                if "(" in self.skill and ")" in self.skill:
                    category = self.skill.split("(", 1)[0].strip()
                    
                    # Get skill categories
                    categories = get_skill_categories(skills)
                    specialties = categories.get(category, [])
                    
                    # Set all specialties in this category to untrained
                    for specialty in specialties:
                        # Skip the current skill
                        if specialty == self.skill:
                            continue
                        
                        # Set specialty to untrained (-3)
                        skills[specialty] = -3
                
            else:
                new_value = int(value)
                skills[self.skill] = new_value
                
                # If this skill is a specialty (has parentheses) and is being set to >= 0,
                # we should update other specialties in the same category to be at least 0
                if new_value >= 0 and "(" in self.skill and ")" in self.skill:
                    category = self.skill.split("(", 1)[0].strip()
                    
                    # Get skill categories
                    categories = get_skill_categories(skills)
                    specialties = categories.get(category, [])
                    
                    # Update all related specialties in the same category
                    for specialty in specialties:
                        # Skip the current skill
                        if specialty == self.skill:
                            continue
                            
                        # If the specialty is untrained, set it to 0
                        if skills.get(specialty, -3) < 0:
                            skills[specialty] = 0
                
            character.skills = skills  # Save back using property setter
        except Exception as e:
            await interaction.response.send_message(f"❌ Please enter a number or 'untrained'. Error: {str(e)}", ephemeral=True)
            return
            
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        # Create a more informative success message that mentions if other skills were updated
        content = f"✅ {self.skill} updated."
        if value.lower() == "untrained" and "(" in self.skill and ")" in self.skill:
            content += " Related skill specialties have also been set to untrained."
        elif value.lower() != "untrained" and int(value) >= 0 and "(" in self.skill and ")" in self.skill:
            content += " Related skill specialties have also been set to at least 0."

        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=MGT2ESheetEditViewV2(
                    editor_id=interaction.user.id,
                    char_id=self.char_id,
                    guild_id=self.guild_id,
                    status_message=content
                )
            )
        else:
            embed = character.format_full_sheet(interaction.guild.id)
            view = MGT2ESheetEditView(interaction.user.id, self.char_id)
            await interaction.response.edit_message(content=content, embed=embed, view=view)


class MGT2ESheetEditViewV2(ui.LayoutView):
    def __init__(self, editor_id: int, char_id: str, guild_id: int, status_message: str = None):
        super().__init__(timeout=86400)
        self.editor_id = editor_id
        self.char_id = char_id
        self.guild_id = guild_id
        self.status_message = status_message
        self._build_layout()

    def _build_layout(self):
        character = get_character(self.char_id)
        if not character:
            container = ui.Container(accent_colour=discord.Colour.red())
            container.add_item(ui.TextDisplay("❌ Character not found."))
            self.add_item(container)
            return

        if self.status_message:
            status = ui.Container(accent_colour=discord.Colour.green())
            status.add_item(ui.TextDisplay(_truncate_text(self.status_message)))
            self.add_item(status)

        content = ui.Container(accent_colour=discord.Colour.dark_teal())
        content.add_item(ui.TextDisplay(_truncate_text(embed_to_text(character.format_full_sheet(self.guild_id, is_gm=True)))))
        self.add_item(content)
        self.add_item(ui.Separator())

        edit_row = ui.ActionRow()
        _add_action_button(edit_row, "Edit Name", discord.ButtonStyle.secondary, self.edit_name)
        _add_action_button(edit_row, "Edit Notes", discord.ButtonStyle.secondary, self.edit_notes)
        _add_action_button(edit_row, "Edit Attributes", discord.ButtonStyle.secondary, self.edit_attributes)
        _add_action_button(edit_row, "Edit Skills", discord.ButtonStyle.secondary, self.edit_skills)
        self.add_item(edit_row)

        inventory_row = ui.ActionRow()
        _add_action_button(inventory_row, "📦 Inventory", discord.ButtonStyle.secondary, self.edit_inventory)
        self.add_item(inventory_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    async def edit_name(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditNameModal(self.char_id, SYSTEM))

    async def edit_notes(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        if interaction.user.id != int(character.owner_id) and not await repositories.server.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only the owner or a GM can edit notes.", ephemeral=True)
            return
        await interaction.response.send_modal(EditNotesModal(self.char_id, SYSTEM))

    async def edit_attributes(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        attrs = character.attributes if character else {}
        await interaction.response.send_modal(EditAttributesModal(self.char_id, attrs, guild_id=self.guild_id))

    async def edit_skills(self, interaction: discord.Interaction):
        categories = get_skill_categories(MGT2ECharacter.DEFAULT_SKILLS)
        category_options = [discord.SelectOption(label=cat, value=cat) for cat in sorted(categories.keys())]

        async def on_category_selected(_view, interaction2: discord.Interaction, category):
            skills_in_cat = categories[category]
            if len(skills_in_cat) == 1 and skills_in_cat[0] == category:
                await interaction2.response.send_modal(EditSkillValueModal(self.char_id, category, guild_id=self.guild_id))
            else:
                skill_options = [discord.SelectOption(label=skill, value=skill) for skill in sorted(skills_in_cat)]

                async def on_skill_selected(_view2, interaction3, skill):
                    await interaction3.response.send_modal(EditSkillValueModal(self.char_id, skill, guild_id=self.guild_id))

                await interaction2.response.edit_message(
                    content=None,
                    embed=None,
                    view=PaginatedSelectViewV2(
                        skill_options,
                        on_skill_selected,
                        interaction.user.id,
                        prompt=f"Select a skill in {category}:",
                        title=f"## Select a skill in {category}"
                    )
                )

        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=PaginatedSelectViewV2(
                category_options,
                on_category_selected,
                interaction.user.id,
                prompt="Select a skill category:",
                title="## Select a skill category"
            )
        )

    async def edit_inventory(self, interaction: discord.Interaction):
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditInventoryViewV2(interaction.guild.id, self.editor_id, self.char_id, is_gm=is_gm)
        )
