import re
from typing import TYPE_CHECKING
import discord
from discord import Interaction, TextStyle, ui
from core.base_models import BaseCharacter, RollFormula, SystemType
from data.repositories.repository_factory import repositories


# ─── Components v2 base classes ───────────────────────────────────────────────

class ConfirmDialogV2(ui.LayoutView):
    """Base Components v2 confirmation dialog with confirm/cancel buttons.

    Subclasses must implement ``on_confirm(interaction)``.
    Override ``on_cancel(interaction)`` for custom cancel behaviour.

    The *message* is rendered as a ``TextDisplay`` inside a ``Container``
    with a red accent colour (configurable).  Below the container an
    ``ActionRow`` holds the confirm (danger) and cancel (secondary) buttons.
    """

    def __init__(
        self,
        *,
        message: str,
        confirm_label: str = "Confirm",
        cancel_label: str = "Cancel",
        accent_colour: discord.Colour = None,
        timeout: float = 60,
    ):
        super().__init__(timeout=timeout)
        self._warning_message = message
        self._confirm_label = confirm_label
        self._cancel_label = cancel_label
        self._accent_colour = accent_colour or discord.Colour.red()
        self._build_layout()

    def _build_layout(self):
        """Construct the LayoutView hierarchy."""
        container = ui.Container(
            ui.TextDisplay(self._warning_message),
            accent_colour=self._accent_colour,
        )
        self.add_item(container)

        action_row = ui.ActionRow()

        confirm_btn = ui.Button(
            label=self._confirm_label,
            style=discord.ButtonStyle.danger,
        )
        confirm_btn.callback = self._on_confirm
        action_row.add_item(confirm_btn)

        cancel_btn = ui.Button(
            label=self._cancel_label,
            style=discord.ButtonStyle.secondary,
        )
        cancel_btn.callback = self._on_cancel
        action_row.add_item(cancel_btn)

        self.add_item(action_row)

    async def _on_confirm(self, interaction: discord.Interaction):
        await self.on_confirm(interaction)

    async def _on_cancel(self, interaction: discord.Interaction):
        await self.on_cancel(interaction)

    # ── Subclass hooks ──────────────────────────────────────────────────

    async def on_confirm(self, interaction: discord.Interaction):
        """Handle confirmation.  Must respond to the interaction."""
        raise NotImplementedError

    async def on_cancel(self, interaction: discord.Interaction):
        """Default cancel: dismiss with a short message."""
        await interaction.response.edit_message(
            content="❌ Cancelled.",
            view=None,
        )


def embed_to_text(embed: discord.Embed) -> str:
    """Convert a discord.Embed to markdown text for TextDisplay in Components v2."""
    lines = []
    if embed.title:
        lines.append(f"## {embed.title}")
    if embed.description:
        lines.append(embed.description)
    for field in embed.fields:
        lines.append(f"\n**{field.name}**")
        lines.append(field.value)
    if embed.footer and embed.footer.text:
        lines.append(f"\n*{embed.footer.text}*")
    return "\n".join(lines)


# ─── Legacy (v1) shared views ────────────────────────────────────────────────

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
    def __init__(self, options, parent_view: PaginatedSelectView):
        super().__init__(placeholder="Select...", min_values=1, max_values=1, options=options)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        await self.parent_view.select_callback(self.parent_view, interaction, value)

class PaginatedPrevButton(ui.Button):
    def __init__(self, parent_view: PaginatedSelectView):
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
    def __init__(self, parent_view: PaginatedSelectView):
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


class PaginatedSelectViewV2(ui.LayoutView):
    def __init__(self, options, select_callback, user_id, prompt="Select an option:", page=0, page_size=25, status_message: str = None, title: str = None):
        super().__init__(timeout=60)
        self.options = options
        self.select_callback = select_callback
        self.user_id = user_id
        self.prompt = prompt
        self.page = page
        self.page_size = page_size
        self.status_message = status_message
        self.title = title or "## Selection"
        self._build_layout()

    def _build_layout(self):
        if self.status_message:
            self.add_item(
                ui.Container(
                    ui.TextDisplay(self.status_message),
                    accent_colour=discord.Colour.green(),
                )
            )

        total_pages = max(1, ((len(self.options) - 1) // self.page_size) + 1) if self.options else 1
        page_options = self.options[self.page * self.page_size:(self.page + 1) * self.page_size]
        summary_lines = [
            self.title,
            self.prompt,
            f"**Page:** {self.page + 1}/{total_pages}",
            f"**Options:** {len(self.options)} total",
        ]
        if not page_options:
            summary_lines.extend(["", "*No options available.*"])

        self.add_item(
            ui.Container(
                ui.TextDisplay("\n".join(summary_lines)),
                accent_colour=discord.Colour.greyple(),
            )
        )

        if page_options:
            select_row = ui.ActionRow()
            select = ui.Select(
                placeholder="Select...",
                min_values=1,
                max_values=1,
                options=page_options,
            )
            select.callback = self._on_select
            select_row.add_item(select)
            self.add_item(select_row)

        if self.page > 0 or (self.page + 1) * self.page_size < len(self.options):
            nav_row = ui.ActionRow()
            if self.page > 0:
                prev_btn = ui.Button(label="Previous", style=discord.ButtonStyle.secondary)
                prev_btn.callback = self._previous_page
                nav_row.add_item(prev_btn)
            if (self.page + 1) * self.page_size < len(self.options):
                next_btn = ui.Button(label="Next", style=discord.ButtonStyle.secondary)
                next_btn.callback = self._next_page
                nav_row.add_item(next_btn)
            self.add_item(nav_row)

    def _clone(self, *, page: int = None, status_message: str = None):
        return PaginatedSelectViewV2(
            self.options,
            self.select_callback,
            self.user_id,
            prompt=self.prompt,
            page=self.page if page is None else page,
            page_size=self.page_size,
            status_message=status_message,
            title=self.title,
        )

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this selection menu.", ephemeral=True)
            return False
        return True

    async def _on_select(self, interaction: discord.Interaction):
        value = interaction.data["values"][0]
        await self.select_callback(self, interaction, value)

    async def _previous_page(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=None, embed=None, view=self._clone(page=self.page - 1))

    async def _next_page(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=None, embed=None, view=self._clone(page=self.page + 1))


def _get_scene_notes_text(guild_id, scene_id, is_gm: bool) -> str:
    active_scene = repositories.scene.get_active_scene(str(guild_id))
    scene_name = active_scene.name if active_scene else f"Scene {scene_id}"

    lines = [f"## 🎭 Scene: {scene_name}"]

    notes = repositories.scene_notes.get_scene_notes(str(guild_id), str(scene_id))
    if notes:
        lines.extend(["", "**Notes**", notes])

    npc_ids = repositories.scene_npc.get_scene_npc_ids(str(guild_id), str(scene_id))
    npc_lines = []
    for npc_id in npc_ids:
        npc = repositories.entity.get_by_id(str(npc_id))
        if npc:
            npc_lines.append(npc.format_npc_scene_entry(is_gm))

    lines.extend(["", "**Scene Entities**"])
    if npc_lines:
        lines.extend(npc_lines)
    else:
        lines.append("📭 No NPCs are currently in this scene.")

    return "\n".join(lines)

class SceneNotesButton(discord.ui.Button):
    def __init__(self, guild_id):
        super().__init__(label="Edit Scene Notes", style=discord.ButtonStyle.primary)
        self.guild_id = guild_id

    async def callback(self, interaction: discord.Interaction):
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit scene notes.", ephemeral=True)
            return
            
        # Get the active scene
        active_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
        if not active_scene:
            await interaction.response.send_message("❌ No active scene available.", ephemeral=True)
            return
            
        await interaction.response.send_modal(EditSceneNotesModal(interaction.guild.id, active_scene.scene_id))


class EditSceneNotesModal(discord.ui.Modal, title="Edit Scene Notes"):
    def __init__(self, guild_id, scene_id):
        super().__init__()
        self.guild_id = guild_id
        self.scene_id = scene_id
        current_notes = repositories.scene_notes.get_scene_notes(str(guild_id), str(scene_id)) or ""
        self.notes = discord.ui.TextInput(
            label="Scene Notes",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=2000,
            default=current_notes
        )
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        repositories.scene_notes.set_scene_notes(str(self.guild_id), str(self.scene_id), self.notes.value)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        view = SceneNotesEditViewV2(self.guild_id, self.scene_id, is_gm=is_gm, status_message="✅ Scene notes updated.")
        await interaction.response.edit_message(content=None, embed=None, view=view)

class SceneNotesEditView(discord.ui.View):
    def __init__(self, guild_id, is_gm=False):
        super().__init__()
        if is_gm:
            self.add_item(SceneNotesButton(guild_id))


class SceneNotesEditViewV2(ui.LayoutView):
    def __init__(self, guild_id, scene_id, is_gm: bool = False, status_message: str = None):
        super().__init__(timeout=60 * 60)
        self.guild_id = guild_id
        self.scene_id = scene_id
        self.is_gm = is_gm
        self.status_message = status_message
        self._build_layout()

    def _build_layout(self):
        if self.status_message:
            self.add_item(
                ui.Container(
                    ui.TextDisplay(self.status_message),
                    accent_colour=discord.Colour.green(),
                )
            )

        self.add_item(
            ui.Container(
                ui.TextDisplay(_get_scene_notes_text(self.guild_id, self.scene_id, self.is_gm)),
                accent_colour=discord.Colour.purple(),
            )
        )

        if self.is_gm:
            self.add_item(ui.Separator())
            action_row = ui.ActionRow()
            action_row.add_item(SceneNotesButton(self.guild_id))
            self.add_item(action_row)

class EditNameModal(ui.Modal, title="Edit Character Name"):
    def __init__(self, entity_id: str, system: SystemType):
        super().__init__()
        self.entity = repositories.entity.get_by_id(str(entity_id))
        self.system = system
        self.name_input = ui.TextInput(
            label="New Name",
            default=self.entity.name if self.entity.name else "",
            max_length=100
        )
        self.add_item(self.name_input)

    async def on_submit(self, interaction: Interaction):
        if not self.entity:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return
        new_name = self.name_input.value.strip()
        if not new_name:
            await interaction.response.send_message("❌ Name cannot be empty.", ephemeral=True)
            return
        self.entity.name = new_name
        repositories.entity.upsert_entity(interaction.guild.id, self.entity, self.system)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        view = self.entity.get_sheet_edit_view(interaction.user.id, is_gm=is_gm, guild_id=str(interaction.guild.id))
        if isinstance(view, ui.LayoutView):
            await interaction.response.edit_message(view=view, content=None, embed=None)
        else:
            embed = self.entity.format_full_sheet(interaction.guild.id)
            await interaction.response.edit_message(content="✅ Name updated.", embed=embed, view=view)

class EditNotesModal(ui.Modal, title="Edit Notes"):
    def __init__(self, entity_id: str, system: SystemType):
        super().__init__()
        self.entity = repositories.entity.get_by_id(str(entity_id))
        self.system = system
        self.notes_field = ui.TextInput(
            label="Notes",
            style=TextStyle.paragraph,
            required=False,
            default="\n".join(self.entity.notes) if self.entity.notes else "",
            max_length=2000
        )
        self.add_item(self.notes_field)

    async def on_submit(self, interaction: Interaction):
        self.entity.notes = [line for line in self.notes_field.value.splitlines() if line.strip()]
        repositories.entity.upsert_entity(interaction.guild.id, self.entity, self.system)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        view = self.entity.get_sheet_edit_view(interaction.user.id, is_gm=is_gm, guild_id=str(interaction.guild.id))
        if isinstance(view, ui.LayoutView):
            await interaction.response.edit_message(view=view, content=None, embed=None)
        else:
            embed = self.entity.format_full_sheet(interaction.guild.id)
            await interaction.response.edit_message(content="✅ Notes updated.", embed=embed, view=view)

class RequestRollView(ui.View):
    def __init__(self, users_requested: list[int], roll_formula: RollFormula = None, difficulty: int = None):
        super().__init__(timeout=60*60*24*7) # 1 week timeout
        self.users_requested = users_requested
        self.roll_formula_obj = roll_formula
        self.difficulty = difficulty
        self.add_item(EditRequestedRollButton(roll_formula, difficulty))
        self.add_item(FinalizeRollButton(roll_formula, difficulty))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Ensure the user was someone whose roll was requested
        if interaction.user.id not in self.users_requested:
            await interaction.response.send_message(
                "❌ You were not included in this roll request. Use `/roll check` or `/roll custom` to roll separately.",
                ephemeral=True
            )
            return False
        return await super().interaction_check(interaction)


class RequestRollViewV2(ui.LayoutView):
    def __init__(self, users_requested: list[int], roll_formula: RollFormula = None, difficulty: int = None, request_message: str = None):
        super().__init__(timeout=60 * 60 * 24 * 7)
        self.users_requested = users_requested
        self.roll_formula_obj = roll_formula
        self.difficulty = difficulty
        self.request_message = request_message or "A roll has been requested."
        self._build_layout()

    def _build_layout(self):
        lines = [
            "## 🎲 Roll Request",
            self.request_message,
            "",
            f"**Formula:** `{self.roll_formula_obj.get_total_dice_formula()}`",
        ]
        if self.difficulty is not None:
            lines.append(f"**Difficulty:** {self.difficulty}")

        self.add_item(
            ui.Container(
                ui.TextDisplay("\n".join(lines)),
                accent_colour=discord.Colour.gold(),
            )
        )
        self.add_item(ui.Separator())

        action_row = ui.ActionRow()
        action_row.add_item(EditRequestedRollButton(self.roll_formula_obj, self.difficulty))
        action_row.add_item(FinalizeRollButton(self.roll_formula_obj, self.difficulty))
        self.add_item(action_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id not in self.users_requested:
            await interaction.response.send_message(
                "❌ You were not included in this roll request. Use `/roll check` or `/roll custom` to roll separately.",
                ephemeral=True
            )
            return False
        return True

class EditRequestedRollButton(ui.Button):
    def __init__(self, roll_formula: RollFormula = None, difficulty: int = None):
        super().__init__(label="Modify Roll", style=discord.ButtonStyle.primary)
        self.roll_formula_obj = roll_formula
        self.difficulty = difficulty

    async def callback(self, interaction: discord.Interaction):
        character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.response.send_message("❌ Active character not found. Use /setactive to set your active character.", ephemeral=True)
            return
        await character.edit_requested_roll(interaction, self.roll_formula_obj, difficulty=self.difficulty)

class RollFormulaView(ui.View):
    """
    Base class for system-specific RollFormulaViews.
    Provides shared variables and structure for roll input views.
    Each modifier/property is shown as a button; clicking it opens a modal to edit its value.
    """
    def __init__(self, roll_formula_obj: RollFormula, character: BaseCharacter, difficulty: int = None):
        super().__init__(timeout=60*60*24) # 1 day timeout
        self.roll_formula_obj = roll_formula_obj
        self.character = character
        self.difficulty = difficulty  

        self.modifier_buttons = {}

        # Create a button for each key in the roll formula
        dice_pattern = re.compile(r"^\s*\d*d\d+([+-]\d+)?\s*$", re.IGNORECASE)
        for key, value in self.roll_formula_obj.modifiers.items():
            is_numeric = False
            if not isinstance(value, bool):
                try:
                    int(value)
                    is_numeric = True
                except (ValueError, TypeError):
                    pass
            if is_numeric or dice_pattern.match(str(value)):
                button = EditModifierButton(key, str(value), self)
                self.modifier_buttons[key] = button
                self.add_item(button)

        # Add a button to add new modifiers
        self.add_item(AddModifierButton(self))

    def add_modifier_button(self, label="modifier", value="0"):
        button = EditModifierButton(label, value, self)
        self.modifier_buttons[label] = button
        self.add_item(button)

    async def update_modifier(self, interaction: discord.Interaction, key: str, value: str):
        # Update the RollFormula object and button label
        self.roll_formula_obj[key] = value
        button = self.modifier_buttons[key]
        button.label = f"{key}: {value}"
        await interaction.response.edit_message(view=self)


class RollFormulaViewV2(ui.LayoutView):
    """Components v2 base class for interactive roll builders."""

    def __init__(self, character: BaseCharacter, roll_formula_obj: RollFormula, difficulty: int = None, status_message: str = None):
        super().__init__(timeout=60 * 60 * 24)
        self.character = character
        self.roll_formula_obj = roll_formula_obj
        self.difficulty = difficulty
        self.status_message = status_message
        self._build_layout()

    def _build_layout(self):
        if self.status_message:
            self.add_item(
                ui.Container(
                    ui.TextDisplay(self._truncate_text(self.status_message)),
                    accent_colour=discord.Colour.green(),
                )
            )

        self.add_item(
            ui.Container(
                ui.TextDisplay(self._truncate_text(self._get_summary_text())),
                accent_colour=self._get_content_colour(),
            )
        )

        extra_rows = self._build_extra_action_rows()
        modifier_rows = self._build_modifier_action_rows()
        footer_row = self._build_footer_row()

        if extra_rows or modifier_rows or footer_row:
            self.add_item(ui.Separator())

        for row in extra_rows:
            self.add_item(row)
        for row in modifier_rows:
            self.add_item(row)
        if footer_row is not None:
            self.add_item(footer_row)

    def _truncate_text(self, text: str, limit: int = 4000) -> str:
        if len(text) <= limit:
            return text
        return text[: limit - 1] + "…"

    def _truncate_button_label(self, label: str, limit: int = 80) -> str:
        if len(label) <= limit:
            return label
        return label[: limit - 1] + "…"

    def _make_button(self, label: str, style: discord.ButtonStyle, callback):
        button = ui.Button(label=self._truncate_button_label(label), style=style)
        button.callback = callback
        return button

    def _get_content_colour(self) -> discord.Colour:
        return discord.Colour.blurple()

    def _get_instruction_text(self) -> str:
        return "Adjust your roll formula as needed, then finalize to roll."

    def _get_specific_summary_lines(self) -> list[str]:
        return []

    def _build_extra_action_rows(self) -> list[ui.ActionRow]:
        return []

    def _clone(self, status_message: str = None):
        return self.__class__(
            character=self.character,
            roll_formula_obj=self.roll_formula_obj,
            difficulty=self.difficulty,
            status_message=status_message,
        )

    def _get_summary_text(self) -> str:
        lines = [
            "## 🎲 Roll Builder",
            f"**Character:** {self.character.name if self.character else 'Unknown'}",
            f"**Formula:** `{self.roll_formula_obj.get_total_dice_formula()}`",
        ]

        if self.difficulty is not None:
            lines.append(f"**Difficulty:** {self.difficulty}")

        specific_lines = self._get_specific_summary_lines()
        if specific_lines:
            lines.append("")
            lines.extend(specific_lines)

        modifiers = self.roll_formula_obj.modifiers if hasattr(self.roll_formula_obj, "modifiers") else {}
        if modifiers:
            lines.append("")
            lines.append("**Modifiers**")
            for key, value in modifiers.items():
                lines.append(f"- {key}: {value}")

        lines.append("")
        lines.append(self._get_instruction_text())
        return "\n".join(lines)

    def _get_modifier_button_defs(self) -> list[tuple[str, discord.ButtonStyle, str, str]]:
        defs = []
        dice_pattern = re.compile(r"^\s*\d*d\d+([+-]\d+)?\s*$", re.IGNORECASE)
        for key, value in self.roll_formula_obj.modifiers.items():
            is_numeric = False
            if not isinstance(value, bool):
                try:
                    int(value)
                    is_numeric = True
                except (ValueError, TypeError):
                    pass
            if is_numeric or dice_pattern.match(str(value)):
                defs.append((f"{key}: {value}", discord.ButtonStyle.secondary, key, str(value)))
        return defs

    def _build_modifier_action_rows(self) -> list[ui.ActionRow]:
        button_defs = self._get_modifier_button_defs()
        rows: list[ui.ActionRow] = []
        current_row = None

        for index, (label, style, key, value) in enumerate(button_defs):
            if index % 5 == 0:
                current_row = ui.ActionRow()
                rows.append(current_row)

            current_row.add_item(self._make_button(label, style, self._make_modifier_callback(key, value)))

        return rows

    def _build_footer_row(self) -> ui.ActionRow:
        row = ui.ActionRow()
        row.add_item(self._make_button("Add Modifier", discord.ButtonStyle.primary, self.add_modifier_prompt))
        row.add_item(self._make_button(f"Roll {self.roll_formula_obj.get_total_dice_formula()}", discord.ButtonStyle.success, self.finalize_roll))
        return row

    def _make_modifier_callback(self, key: str, value: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_modal(EditModifierModal(key, value, self, interaction))

        return callback

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        active_character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not active_character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return False
        self.character = active_character
        return True

    async def refresh_view(self, interaction: discord.Interaction, status_message: str = None):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=self._clone(status_message=status_message),
        )

    async def update_modifier(self, interaction: discord.Interaction, key: str, value: str):
        self.roll_formula_obj[key] = value
        await self.refresh_view(interaction, status_message=f"✅ Updated **{key}** to `{value}`.")

    async def add_modifier(self, interaction: discord.Interaction, key: str, value: str):
        self.roll_formula_obj.modifiers[key] = value
        await self.refresh_view(interaction, status_message=f"✅ Added modifier **{key}** = `{value}`.")

    async def add_modifier_prompt(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddModifierModal(self, interaction))

    async def finalize_roll(self, interaction: discord.Interaction):
        character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id) or self.character
        if not character:
            await interaction.response.send_message("❌ Active character not found. Use /setactive to set your active character.", ephemeral=True)
            return
        await character.send_roll_message(interaction, self.roll_formula_obj, self.difficulty)

class EditModifierButton(discord.ui.Button):
    def __init__(self, key: str, value: str, parent_view: RollFormulaView):
        super().__init__(label=f"{key}: {value}", row=1, style=discord.ButtonStyle.secondary)
        self.key = key
        self.value = value
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditModifierModal(self.key, self.value, self.parent_view, interaction))

class EditModifierModal(discord.ui.Modal, title="Edit Modifier"):
    def __init__(self, key: str, value: str, parent_view: RollFormulaView, original_interaction: discord.Interaction):
        super().__init__()
        self.key = key
        self.parent_view = parent_view
        self.original_interaction = original_interaction
        self.value_input = discord.ui.TextInput(
            label=f"Value for {key}",
            default=value,
            required=True,
            max_length=20
        )
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        await self.parent_view.update_modifier(interaction, self.key, self.value_input.value)

class AddModifierButton(discord.ui.Button):
    def __init__(self, parent_view: RollFormulaView):
        super().__init__(label="Add Modifier", row=0, style=discord.ButtonStyle.primary)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Open a modal to ask for new modifier key and value
        await interaction.response.send_modal(AddModifierModal(self.parent_view, interaction))

class AddModifierModal(discord.ui.Modal, title="Add Modifier"):
    def __init__(self, parent_view: RollFormulaView, original_interaction: discord.Interaction):
        super().__init__()
        self.parent_view = parent_view
        self.original_interaction = original_interaction
        self.key_input = discord.ui.TextInput(
            label="Modifier Name",
            placeholder="e.g. bonus, penalty, situational",
            required=True,
            max_length=30
        )
        self.value_input = discord.ui.TextInput(
            label="Modifier Value",
            placeholder="e.g. +2, -1, 0",
            required=True,
            max_length=10
        )
        self.add_item(self.key_input)
        self.add_item(self.value_input)

    async def on_submit(self, interaction: discord.Interaction):
        key = self.key_input.value.strip()
        value = self.value_input.value.strip()
        if hasattr(self.parent_view, "add_modifier"):
            await self.parent_view.add_modifier(interaction, key, value)
            return

        self.parent_view.roll_formula_obj.modifiers[key] = value
        self.parent_view.add_modifier_button(label=key, value=value)
        
        for item in self.parent_view.children:
            if isinstance(item, FinalizeRollButton):
                item.label = f"Roll {self.parent_view.roll_formula_obj.get_total_dice_formula()}"
                break
                
        await interaction.response.edit_message(view=self.parent_view)

class FinalizeRollButton(discord.ui.Button):
    def __init__(self, roll_formula_obj: RollFormula = None, difficulty: int = None):
        super().__init__(label=f"Roll {roll_formula_obj.get_total_dice_formula()}", style=discord.ButtonStyle.success)
        self.roll_formula_obj = roll_formula_obj
        self.difficulty = difficulty

    async def callback(self, interaction: discord.Interaction):
        character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        await character.send_roll_message(
            interaction,
            self.roll_formula_obj,
            self.difficulty
        )