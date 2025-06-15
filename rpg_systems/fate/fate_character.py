import random
from typing import Any, Dict, List
import discord
from discord import ui, SelectOption
from core.models import BaseCharacter, BaseSheet
from core.rolling import RollModifiers
from core.shared_views import FinalizeRollButton, PaginatedSelectView, EditNameModal, EditNotesModal, RollModifiersView
from core.utils import get_character, roll_formula
from data import repo

SYSTEM = "fate"

class FateCharacter(BaseCharacter):
    DEFAULT_SKILLS = {
        "Athletics": 0,
        "Burglary": 0,
        "Contacts": 0,
        "Crafts": 0,
        "Deceive": 0,
        "Drive": 0,
        "Empathy": 0,
        "Fight": 0,
        "Investigate": 0,
        "Lore": 0,
        "Notice": 0,
        "Physique": 0,
        "Provoke": 0,
        "Rapport": 0,
        "Resources": 0,
        "Shoot": 0,
        "Stealth": 0,
        "Will": 0
    }
    SYSTEM_SPECIFIC_CHARACTER = {
        "fate_points": 3,
        "skills": {},
        "aspects": [],
        "hidden_aspects": [],
        "stress": {"physical": [False, False, False], "mental": [False, False]},
        "consequences": ["Mild: None", "Moderate: None", "Severe: None"]
    }
    SYSTEM_SPECIFIC_NPC = {
        "fate_points": 0,
        "skills": {},
        "aspects": [],
        "hidden_aspects": [],
        "stress": {"physical": [False, False, False], "mental": [False, False]},
        "consequences": ["Mild: None"]
    }

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FateCharacter":
        return cls(data)

    # Properties for system-specific fields

    @property
    def skills(self) -> Dict[str, int]:
        return self.data.get("skills", {})

    @skills.setter
    def skills(self, value: Dict[str, int]):
        self.data["skills"] = value

    @property
    def aspects(self) -> List[str]:
        return self.data.get("aspects", [])

    @aspects.setter
    def aspects(self, value: List[str]):
        self.data["aspects"] = value

    @property
    def hidden_aspects(self) -> List[int]:
        return self.data.get("hidden_aspects", [])

    @hidden_aspects.setter
    def hidden_aspects(self, value: List[int]):
        self.data["hidden_aspects"] = value

    @property
    def fate_points(self) -> int:
        return self.data.get("fate_points", 0)

    @fate_points.setter
    def fate_points(self, value: int):
        self.data["fate_points"] = value

    @property
    def stress(self) -> Dict[str, list]:
        return self.data.get("stress", {})

    @stress.setter
    def stress(self, value: Dict[str, list]):
        self.data["stress"] = value

    @property
    def consequences(self) -> list:
        return self.data.get("consequences", [])

    @consequences.setter
    def consequences(self, value: list):
        self.data["consequences"] = value

    # You can keep your old getter methods for backward compatibility if needed,
    # but you should now use the properties above in new code.

    def apply_defaults(self, is_npc=False, guild_id=None):
        """
        Apply system-specific default fields to a character dict.
        This method uses the @property accessors for all fields.
        """
        super().apply_defaults(is_npc=is_npc, guild_id=guild_id)
        system_defaults = self.SYSTEM_SPECIFIC_NPC if is_npc else self.SYSTEM_SPECIFIC_CHARACTER
        for key, value in system_defaults.items():
            if key == "skills":
                # Use per-guild default if available
                skills = None
                if guild_id:
                    skills = repo.get_default_skills(guild_id, "fate")
                default_skills = dict(skills) if skills else dict(self.DEFAULT_SKILLS)
                # Use the property setter for skills
                if not self.skills:
                    self.skills = default_skills
                else:
                    # Only add missing skills, don't overwrite existing ones
                    updated_skills = dict(self.skills)
                    for skill, val in default_skills.items():
                        if skill not in updated_skills:
                            updated_skills[skill] = val
                    self.skills = updated_skills
            else:
                # Use property setters for all other fields
                if not hasattr(self, key) or getattr(self, key) in (None, [], {}, 0, False):
                    setattr(self, key, value)
    
    async def request_roll(self, interaction: discord.Interaction, roll_parameters: dict, difficulty: int = None):
        roll_formula_obj = FateRollModifiers(roll_parameters_dict=roll_parameters)
        view = FateRollModifiersView(roll_formula_obj, self, interaction, difficulty)
        await interaction.response.send_message(
            content="Adjust your roll formula as needed, then finalize to roll.",
            view=view,
            ephemeral=True
        )
        
    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollModifiers, difficulty: int = None):
        """
        Rolls 4df with modifiers from the RollFormula object.
        """
        # Build the formula string from the RollFormula object
        # Example: "2d6+3-1"
        formula_parts = ["4df"]
        for key, value in roll_formula_obj.get_modifiers(self).items():
            try:
                mod = int(value)
                if mod >= 0:
                    formula_parts.append(f"+{mod}")
                else:
                    formula_parts.append(f"{mod}")
            except Exception:
                continue
        formula = "".join(formula_parts)
        result, total = roll_formula(formula)
        if total is not None and difficulty is not None:
            if total >= difficulty:
                result += f"\n✅ Success! (Needed {difficulty}) Shifts: {total - difficulty}"
            else:
                result += f"\n❌ Failure. (Needed {difficulty}) Shifts: {total - difficulty}"
        await interaction.response.send_message(result, ephemeral=False)

    @staticmethod
    def parse_and_validate_skills(skills_str):
        """
        Parse a skills string like 'Fight:2, Stealth:1' into a dict.
        This method is static and does not use properties, but you can use the result
        to assign to the .skills property of a FateCharacter instance.
        """
        skills_dict = {}
        for entry in skills_str.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        # Add Fate-specific validation here if needed (e.g., pyramid structure)
        return skills_dict

class FateRollModifiers(RollModifiers):
    """
    A roll formula specifically for the generic RPG system.
    It can handle any roll parameters as needed.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        super().__init__(roll_parameters_dict)
        self.skill = roll_parameters_dict.get("skill") if roll_parameters_dict else None

    def get_modifiers(self, character: FateCharacter) -> Dict[str, int]:
        modifiers = super().get_modifiers(character).items()
        if self.skill:
            skill_value = character.skills.get(self.skill, 0)
            modifiers = list(modifiers) + [(self.skill, skill_value)]
        return dict(modifiers)

class FateSheet(BaseSheet):
    def format_full_sheet(self, character: FateCharacter) -> discord.Embed:
        # Use the property .name instead of get_name()
        embed = discord.Embed(title=f"{character.name}", color=discord.Color.purple())

        # --- Aspects ---
        aspects = character.aspects
        hidden_aspects = character.hidden_aspects
        if aspects:
            aspect_lines = []
            for idx, aspect in enumerate(aspects):
                if idx in hidden_aspects:
                    aspect_lines.append(f"- *{aspect}*")
                else:
                    aspect_lines.append(f"- {aspect}")
            embed.add_field(name="Aspects", value="\n".join(aspect_lines), inline=False)
        else:
            embed.add_field(name="Aspects", value="None", inline=False)

        # --- Skills ---
        skills = character.skills
        if skills:
            sorted_skills = sorted(skills.items(), key=lambda x: -x[1])
            skill_lines = [f"**{k}**: +{v}" for k, v in sorted_skills]
            embed.add_field(name="Skills", value="\n".join(skill_lines), inline=False)
        else:
            embed.add_field(name="Skills", value="None", inline=False)

        # --- Stress Tracks ---
        stress = character.stress
        if stress:
            stress_lines = [
                f"**Physical**: {' '.join('[☒]' if x else '[☐]' for x in stress.get('physical', []))}",
                f"**Mental**: {' '.join('[☒]' if x else '[☐]' for x in stress.get('mental', []))}"
            ]
            embed.add_field(name="Stress", value="\n".join(stress_lines), inline=False)
        else:
            embed.add_field(name="Stress", value="None", inline=False)

        # --- Consequences ---
        consequences = character.consequences
        if consequences:
            embed.add_field(name="Consequences", value="\n".join(f"- {c}" for c in consequences), inline=False)
        else:
            embed.add_field(name="Consequences", value="None", inline=False)

        # --- Fate Points ---
        fp = character.fate_points
        embed.add_field(name="Fate Points", value=str(fp), inline=True)

        # --- Notes ---
        notes = character.notes
        # If notes is a list, join them for display
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)

        return embed

    def format_npc_scene_entry(self, npc: FateCharacter, is_gm: bool):
        aspects = npc.aspects
        hidden = npc.hidden_aspects
        aspect_lines = []
        for idx, aspect in enumerate(aspects):
            if idx in hidden:
                aspect_lines.append(f"*{aspect}*" if is_gm else "*hidden*")
            else:
                aspect_lines.append(aspect)
        aspect_str = "\n".join(aspect_lines) if aspect_lines else "_No aspects set_"
        lines = [f"**{npc.name}**\n{aspect_str}"]
        if is_gm and npc.notes:
            notes_display = "\n".join(npc.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)
    
    def roll(self, character: FateCharacter, *, skill=None, attribute=None):
        if not skill:
            return "❌ Please specify a skill."
        skill_val = character.skills.get(skill, 0)
        rolls = [random.choice([-1, 0, 1]) for _ in range(4)]
        symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
        total = sum(rolls) + skill_val
        response = f'🎲 4dF: `{" ".join(symbols)}` + **{skill}** ({skill_val})\n🧮 Total: {total}'
        return response

class FateSheetEditView(ui.View):
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

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=1)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        await interaction.response.send_modal(
            EditNameModal(
                self.char_id,
                character.name if character else "",
                SYSTEM,
                lambda editor_id, char_id: (FateSheet().format_full_sheet(get_character(interaction.guild.id, char_id)), FateSheetEditView(editor_id, char_id))
            )
        )

    @ui.button(label="Edit Aspects", style=discord.ButtonStyle.secondary, row=2)
    async def edit_aspects(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing aspects:", view=EditAspectsView(interaction.guild.id, self.editor_id, self.char_id))

    @ui.button(label="Edit Skills", style=discord.ButtonStyle.secondary, row=2)
    async def edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        skills = character.skills if character.skills else {}
        skill_options = [SelectOption(label=k, value=k) for k in sorted(skills.keys())]

        async def on_skill_selected(view, interaction2, skill):
            current_value = skills.get(skill, 0)
            await interaction2.response.send_modal(EditSkillValueModal(self.char_id, skill, current_value))

        await interaction.response.send_message(
            "Select a skill to edit:",
            view=PaginatedSelectView(skill_options, on_skill_selected, interaction.user.id, prompt="Select a skill to edit:"),
            ephemeral=True
        )

    @ui.button(label="Edit Stress", style=discord.ButtonStyle.primary, row=1)
    async def edit_stress(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditStressModal(self.char_id))

    @ui.button(label="Edit Consequences", style=discord.ButtonStyle.primary, row=1)
    async def edit_consequences(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing consequences:", view=EditConsequencesView(interaction.guild.id, self.editor_id, self.char_id))

    @ui.button(label="Edit Fate Points", style=discord.ButtonStyle.primary, row=1)
    async def edit_fp(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditFatePointsModal(self.char_id))

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=4)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        notes = "\n".join(character.notes) if character and character.notes else ""
        await interaction.response.send_modal(
            EditNotesModal(
                self.char_id,
                notes,
                SYSTEM,
                lambda editor_id, char_id: (FateSheet().format_full_sheet(get_character(interaction.guild.id, char_id)), FateSheetEditView(editor_id, char_id))
            )
        )

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
        self.char = get_character(self.guild_id, self.char_id)
        if not self.char:
            self.aspects = []
            self.hidden_aspects = []
        else:
            self.aspects = self.char.aspects
            self.hidden_aspects = self.char.hidden_aspects
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

            self.char = get_character(interaction.guild.id, self.char_id)
            self.aspects = self.char.aspects
            self.hidden_aspects = self.char.hidden_aspects

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
                self.char.aspects = self.aspects
                self.char.hidden_aspects = self.hidden_aspects
                repo.set_character(interaction.guild.id, self.char, system=SYSTEM)
                self.page = max(0, self.page - 1)
            elif cid == "toggle_hidden":
                if self.page in self.hidden_aspects:
                    self.hidden_aspects.remove(self.page)
                else:
                    self.hidden_aspects.append(self.page)
                self.char.hidden_aspects = self.hidden_aspects
                repo.set_character(interaction.guild.id, self.char, system=SYSTEM)
            elif cid == "add":
                await interaction.response.send_modal(AddAspectModal(self.char_id))
                return
            elif cid == "done":
                await interaction.response.edit_message(content="✅ Done editing aspects.", embed=FateSheet().format_full_sheet(self.char), view=FateSheetEditView(interaction.user.id, self.char_id))
                return

            repo.set_character(interaction.guild.id, self.char, system=SYSTEM)
            self.load_data()
            self.render()
            await interaction.response.edit_message(embed=FateSheet().format_full_sheet(self.char), view=self)
        return callback

class EditAspectModal(ui.Modal, title="Edit Aspect"):
    def __init__(self, char_id: str, index: int, current: str):
        super().__init__()
        self.char_id = char_id
        self.index = index
        self.add_item(ui.TextInput(label="Aspect", default=current, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        aspects = character.aspects
        if self.index >= len(aspects):
            await interaction.response.send_message("❌ Aspect not found.", ephemeral=True)
            return
        aspects[self.index] = self.children[0].value.strip()
        character.aspects = aspects
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Aspect updated.", embed=FateSheet().format_full_sheet(character), view=EditAspectsView(interaction.guild.id, interaction.user.id, self.char_id))

class AddAspectModal(ui.Modal, title="Add Aspect"):
    def __init__(self, char_id: str):
        super().__init__()
        self.char_id = char_id
        self.add_item(ui.TextInput(label="New Aspect", max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        aspects = character.aspects
        aspects.append(self.children[0].value.strip())
        character.aspects = aspects
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Aspect added.", embed=FateSheet().format_full_sheet(character), view=EditAspectsView(interaction.guild.id, interaction.user.id, self.char_id))

class EditStressModal(ui.Modal, title="Edit Stress"):
    physical = ui.TextInput(label="Physical Stress (e.g. 1 1 0)", required=False)
    mental = ui.TextInput(label="Mental Stress (e.g. 1 0)", required=False)

    def __init__(self, char_id):
        super().__init__()
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        stress = character.stress
        stress["physical"] = [bool(int(x)) for x in self.physical.value.split()]
        stress["mental"] = [bool(int(x)) for x in self.mental.value.split()]
        character.stress = stress
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Stress updated!", embed=FateSheet().format_full_sheet(character), view=FateSheetEditView(interaction.user.id, self.char_id))

class EditFatePointsModal(ui.Modal, title="Edit Fate Points"):
    fate_points = ui.TextInput(label="Fate Points", required=True)

    def __init__(self, char_id):
        super().__init__()
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        try:
            character.fate_points = int(self.fate_points.value)
        except ValueError:
            await interaction.response.send_message("❌ Invalid number.", ephemeral=True)
            return
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Fate Points updated.", embed=FateSheet().format_full_sheet(character), view=FateSheetEditView(interaction.user.id, self.char_id))

class EditConsequenceModal(ui.Modal, title="Edit Consequence"):
    def __init__(self, char_id: str, index: int, current: str):
        super().__init__()
        self.char_id = char_id
        self.index = index
        self.add_item(ui.TextInput(label="Consequence", default=current, max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        consequences = character.consequences
        if self.index >= len(consequences):
            await interaction.response.send_message("❌ Consequence not found.", ephemeral=True)
            return
        consequences[self.index] = self.children[0].value.strip()
        character.consequences = consequences
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Consequence updated.", view=EditConsequencesView(interaction.guild.id, interaction.user.id, self.char_id))

class AddConsequenceModal(ui.Modal, title="Add Consequence"):
    def __init__(self, char_id: str):
        super().__init__()
        self.char_id = char_id
        self.add_item(ui.TextInput(label="New Consequence", max_length=100))

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        consequences = character.consequences
        consequences.append(self.children[0].value.strip())
        character.consequences = consequences
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        await interaction.response.edit_message(content="✅ Consequence added.", view=EditConsequencesView(interaction.guild.id, interaction.user.id, self.char_id))

class EditConsequencesView(ui.View):
    def __init__(self, guild_id: int, user_id: int, char_id: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.page = 0

        self.char = get_character(self.guild_id, self.char_id)
        self.consequences = self.char.consequences if self.char else []
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

            self.char = get_character(interaction.guild.id, self.char_id)
            self.consequences = self.char.consequences if self.char else []

            if cid == "prev":
                self.page = max(0, self.page - 1)
            elif cid == "next":
                self.page = min(self.max_page, self.page + 1)
            elif cid == "edit":
                await interaction.response.send_modal(EditConsequenceModal(self.char_id, self.page, self.consequences[self.page]))
                return
            elif cid == "remove":
                del self.consequences[self.page]
                self.char.consequences = self.consequences
                repo.set_character(interaction.guild.id, self.char, system=SYSTEM)
                self.page = max(0, self.page - 1)
            elif cid == "add":
                await interaction.response.send_modal(AddConsequenceModal(self.char_id))
                return
            elif cid == "done":
                await interaction.response.edit_message(content="✅ Done editing consequences.", embed=FateSheet().format_full_sheet(self.char), view=FateSheetEditView(interaction.user.id, self.char_id))
                return

            repo.set_character(interaction.guild.id, self.char, system=SYSTEM)
            self.render()
            await interaction.response.edit_message(view=self)
        return callback

class RollButton(ui.Button):
    def __init__(self, char_id, editor_id):
        super().__init__(label="Roll", style=discord.ButtonStyle.primary, row=0)
        self.char_id = char_id
        self.editor_id = editor_id

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can’t roll for this character.", ephemeral=True)
            return
        character = get_character(interaction.guild.id, self.char_id)
        skills = character.skills if character else {}
        skill_options = [SelectOption(label=k, value=k) for k in sorted(skills.keys())]

        async def on_skill_selected(view, interaction2, skill):
            result = FateSheet().roll(character, skill=skill)
            await interaction2.response.send_message(result, ephemeral=True)

        await interaction.response.send_message(
            "Select a skill to roll:",
            view=PaginatedSelectView(skill_options, on_skill_selected, interaction.user.id, prompt="Select a skill to roll:"),
            ephemeral=True
        )

class EditSkillValueModal(ui.Modal, title="Edit Skill Value"):
    def __init__(self, char_id: str, skill: str, current_value: int = 0):
        super().__init__()
        self.char_id = char_id
        self.skill = skill
        label = f"Set value for {skill} (-3 to 6)"
        if len(label) > 45:
            label = label[:42] + "..."
        self.value_field = ui.TextInput(
            label=label,
            required=True,
            default=str(current_value),
            max_length=3
        )
        self.add_item(self.value_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        value = self.value_field.value.strip()
        try:
            value_int = int(value)
            if value_int < -3 or value_int > 6:
                raise ValueError
        except Exception:
            await interaction.response.send_message("❌ Please enter an integer from -3 to 6.", ephemeral=True)
            return
        skills = character.skills
        skills[self.skill] = value_int
        character.skills = skills
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        embed = FateSheet().format_full_sheet(character)
        view = FateSheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content=f"✅ {self.skill} updated.", embed=embed, view=view)

class FateRollModifiersView(RollModifiersView):
    def __init__(self, roll_formula_obj: RollModifiers, character, original_interaction, difficulty: int = None):
        super().__init__(roll_formula_obj, character, original_interaction, difficulty)
        self.add_item(FinalizeRollButton(self))

# class FateRollFormulaView(RollFormulaView):
#     """
#     A view for editing and finalizing Fate roll formulas.
#     This view allows users to adjust the roll formula and finalize it for rolling.
#     Provides a dropdown to select a different skill than the one from the roll_formula_obj.
#     """
#     def __init__(self, roll_formula_obj: FateRollFormula, character, original_interaction, difficulty: int = None):
#         super().__init__(roll_formula_obj, character, original_interaction, difficulty)
#         # Prepare skill options from the character's skills
#         skills = getattr(character, "skills", {})
#         skill_options = [
#             discord.SelectOption(label=skill, value=skill)
#             for skill in sorted(skills.keys())
#         ]
#         # Default to the skill in the roll_formula_obj if present, else first skill
#         default_skill = roll_formula_obj.skill if hasattr(roll_formula_obj, "properties") else None
#         if not default_skill and skill_options:
#             default_skill = skill_options[0].value

#         self.skill_select = discord.ui.Select(
#             placeholder=default_skill if default_skill else "Select a skill",
#             options=skill_options,
#             min_values=0,
#             max_values=1
#         )
#         self.add_item(self.skill_select)
#         self.add_item(FateFinalizeRollButton(self))

# class FateFinalizeRollButton(FinalizeRollButton):
#     def __init__(self, parent_view: "FateRollFormulaView"):
#         super().__init__(label="Finalize Roll", style=discord.ButtonStyle.success)
#         self.parent_view = parent_view

#     async def callback(self, interaction: discord.Interaction):
#         super().callback(interaction)
#         # Update the roll_formula_obj with the selected skill and any other modifiers
#         selected_skill = self.parent_view.skill_select.values[0] if self.parent_view.skill_select.values else None
#         if selected_skill:
#             self.parent_view.roll_formula_obj["skill"] = selected_skill

#         await self.parent_view.character.send_roll_message(
#             interaction,
#             self.parent_view.roll_formula_obj,
#             self.parent_view.difficulty
#         )
#         self.parent_view.stop()