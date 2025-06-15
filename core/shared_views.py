import discord
from discord import Interaction, TextStyle, ui
from core import factories
from core.rolling import RollFormula
from core.models import BaseCharacter
from core.utils import get_character, roll_formula
from data import repo

class PaginatedSelectView(ui.View):
    def __init__(self, options, select_callback, user_id, prompt="Select an option:", page=0, page_size=25):
        super().__init__(timeout=60)
        self.options = options
        self.select_callback = select_callback  # function(view, interaction, value)
        self.user_id = user_id
        self.prompt = prompt
        self.page = page
        self.page_size = page_size

        page_options = options[page*page_size:(page+1)*page_size]
        self.add_item(PaginatedSelect(page_options, self))

        if page > 0:
            self.add_item(PaginatedPrevButton(self))
        if (page+1)*page_size < len(options):
            self.add_item(PaginatedNextButton(self))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

class PaginatedSelect(ui.Select):
    def __init__(self, options, parent_view):
        super().__init__(placeholder="Select...", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        await self.parent_view.select_callback(self.parent_view, interaction, value)

class PaginatedPrevButton(ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="Previous", style=discord.ButtonStyle.secondary, row=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=self.parent_view.prompt,
            view=PaginatedSelectView(
                self.parent_view.options,
                self.parent_view.select_callback,
                self.parent_view.user_id,
                self.parent_view.prompt,
                page=self.parent_view.page - 1,
                page_size=self.parent_view.page_size
            )
        )

class PaginatedNextButton(ui.Button):
    def __init__(self, parent_view):
        super().__init__(label="Next", style=discord.ButtonStyle.secondary, row=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=self.parent_view.prompt,
            view=PaginatedSelectView(
                self.parent_view.options,
                self.parent_view.select_callback,
                self.parent_view.user_id,
                self.parent_view.prompt,
                page=self.parent_view.page + 1,
                page_size=self.parent_view.page_size
            )
        )

class SceneNotesEditView(discord.ui.View):
    def __init__(self, guild_id, is_gm):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.is_gm = is_gm
        if is_gm:
            self.add_item(SceneNotesButton(guild_id))

class SceneNotesButton(discord.ui.Button):
    def __init__(self, guild_id):
        super().__init__(label="Edit Scene Notes", style=discord.ButtonStyle.primary)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ Only GMs can edit scene notes.", ephemeral=True)
            return
        await interaction.response.send_modal(EditSceneNotesModal(self.guild_id))  # No need to pass interaction.message

class EditSceneNotesModal(discord.ui.Modal, title="Edit Scene Notes"):
    def __init__(self, guild_id):
        super().__init__()
        self.guild_id = guild_id
        current_notes = repo.get_scene_notes(guild_id) or ""
        self.notes = discord.ui.TextInput(
            label="Scene Notes",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=2000,
            default=current_notes
        )
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        repo.set_scene_notes(self.guild_id, self.notes.value)
        # Rebuild the scene embed and view
        system = repo.get_system(self.guild_id)
        sheet = factories.get_specific_sheet(system)
        npc_ids = repo.get_scene_npc_ids(self.guild_id)
        is_gm = repo.is_gm(self.guild_id, interaction.user.id)
        lines = []
        for npc_id in npc_ids:
            npc = repo.get_character(self.guild_id, npc_id)
            if npc:
                lines.append(sheet.format_npc_scene_entry(npc, is_gm))
        notes = repo.get_scene_notes(self.guild_id)
        description = ""
        if notes:
            description += f"**Notes:**\n{notes}\n\n"
        if lines:
            description += "\n\n".join(lines)
        else:
            description += "📭 No NPCs are currently in the scene."
        embed = discord.Embed(
            title="🎭 The Current Scene",
            description=description,
            color=discord.Color.purple()
        )
        view = SceneNotesEditView(self.guild_id, is_gm)
        await interaction.response.edit_message(embed=embed, view=view)

class EditNameModal(ui.Modal, title="Edit Character Name"):
    def __init__(self, char_id: str, current_name: str, system: str, make_view_embed):
        super().__init__()
        self.char_id = char_id
        self.system = system
        self.make_view_embed = make_view_embed
        self.name_input = ui.TextInput(
            label="New Name",
            default=current_name,
            max_length=100
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return
        new_name = self.name_input.value.strip()
        if not new_name:
            await interaction.response.send_message("❌ Name cannot be empty.", ephemeral=True)
            return
        character.name = new_name
        repo.set_character(interaction.guild.id, character, system=self.system)
        embed, view = self.make_view_embed(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Name updated.", embed=embed, view=view)

class EditNotesModal(ui.Modal, title="Edit Notes"):
    def __init__(self, char_id: str, notes: str, system: str, make_view_embed):
        super().__init__()
        self.char_id = char_id
        self.system = system
        self.make_view_embed = make_view_embed
        self.notes_field = ui.TextInput(
            label="Notes",
            style=TextStyle.paragraph,
            required=False,
            default=notes,
            max_length=2000
        )
        self.add_item(self.notes_field)

    async def on_submit(self, interaction: Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        character.notes = [line for line in self.notes_field.value.splitlines() if line.strip()]
        repo.set_character(interaction.guild.id, character, system=self.system)
        embed, view = self.make_view_embed(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Notes updated.", embed=embed, view=view)

class RequestRollView(ui.View):
    def __init__(self, chars, system, roll_parameters: str = None, difficulty: int = None):
        super().__init__(timeout=300)
        for char in chars:
            self.add_item(RequestRollButton(char.id, system, roll_parameters, difficulty))

class RequestRollButton(ui.Button):
    def __init__(self, char_id, system, roll_parameters: str = None, difficulty: int = None):
        super().__init__(label="Roll", style=discord.ButtonStyle.primary)
        self.char_id = char_id
        self.roll_parameters = roll_parameters
        self.difficulty = difficulty
        self.system = system

    async def callback(self, interaction: discord.Interaction):
        character = repo.get_character_by_id(interaction.guild.id, self.char_id)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return
        # Parse roll_parameters into kwargs
        kwargs = {}
        if self.roll_parameters:
            for param in self.roll_parameters.split(","):
                if ":" in param:
                    k, v = param.split(":", 1)
                    kwargs[k.strip()] = v.strip()
        await character.request_roll(interaction, roll_parameters=kwargs, difficulty=self.difficulty)

class RollFormulaView(ui.View):
    """
    Base class for system-specific RollFormulaViews.
    Provides shared variables and structure for roll input views.
    """
    def __init__(self, roll_formula_obj: RollFormula, character: BaseCharacter, original_interaction, difficulty: int = None):
        super().__init__(timeout=300)
        self.roll_formula_obj = roll_formula_obj  # The RollFormula object being edited
        self.character = character                # The character making the roll
        self.original_interaction = original_interaction  # The original Discord interaction
        self.difficulty = difficulty  
        
        self.modifier_inputs = {}

        # Create a text input for each key in the roll formula
        for key, value in self.roll_formula_obj.to_dict().items():
            input_box = discord.ui.TextInput(
                label=f"{key}",
                default=str(value),
                required=False,
                max_length=20
            )
            self.modifier_inputs[key] = input_box
            self.add_item(input_box)

        # Add a blank modifier input for adding new modifiers
        self.add_item(AddModifierButton(self))

    def add_modifier_input(self, label="modifier"):
        input_box = discord.ui.TextInput(
            label=label,
            required=True,
            default="0",
            max_length=20
        )
        self.modifier_inputs[label] = input_box
        self.add_item(input_box)            # Optional difficulty for the roll

class AddModifierButton(discord.ui.Button):
    def __init__(self, parent_view: RollFormulaView):
        super().__init__(label="Add Modifier", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Add a new modifier input with a unique label
        idx = 1
        while f"modifier{idx}" in self.parent_view.modifier_inputs:
            idx += 1
        label = f"modifier{idx}"
        self.parent_view.add_modifier_input(label=label)
        await interaction.response.edit_message(view=self.parent_view)