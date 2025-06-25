import random
from typing import Any, Dict, List
import discord
from discord import ui, SelectOption
from core.models import BaseCharacter, BaseSheet, RollModifiers
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
        "stress": {"physical": [False, False], "mental": [False, False]},
        "consequences": ["Mild: None", "Moderate: None", "Severe: None"],
        "stunts": {}  # Added stunts as a dictionary: {name: description}
    }
    SYSTEM_SPECIFIC_NPC = {
        "fate_points": 0,
        "skills": {},
        "aspects": [],
        "hidden_aspects": [],
        "stress": {"physical": [False, False], "mental": [False, False]},
        "consequences": ["Mild: None"],
        "stunts": {}  # Added stunts for NPCs too
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

    # Add property getter and setter for stunts
    @property
    def stunts(self) -> Dict[str, str]:
        return self.data.get("stunts", {})
        
    @stunts.setter
    def stunts(self, value: Dict[str, str]):
        self.data["stunts"] = value

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
    
    async def edit_requested_roll(self, interaction: discord.Interaction, roll_formula_obj: "FateRollModifiers", difficulty: int = None):
        """
        Opens a view for editing the roll parameters, prepopulated with any requested skill.
        """
        view = FateRollModifiersView(roll_formula_obj, difficulty)
        
        # Create a message that shows what was initially requested
        content = "Adjust your roll formula as needed, then finalize to roll."
        if roll_formula_obj.skill:
            skill_value = self.skills.get(roll_formula_obj.skill, 0)
            content = f"Roll requested with skill: **{roll_formula_obj.skill}** (+{skill_value if skill_value >= 0 else skill_value})\n{content}"
        
        await interaction.response.send_message(
            content=content,
            view=view,
            ephemeral=True
        )
        
    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: "FateRollModifiers", difficulty: int = None):
        """
        Prints the roll result
        """
        result, total = roll_formula(self, "4df", roll_formula_obj)

        difficulty_shifts_str = ""
        if difficulty:
            shifts = total - difficulty
            difficulty_shifts_str = f" (Needed {difficulty}) Shifts: {shifts}"
            if total >= difficulty + 2:
                result += f"\n✅ Success *with style*!{difficulty_shifts_str}"
            elif total > difficulty:
                result += f"\n✅ Success.{difficulty_shifts_str}"
            elif total == difficulty:
                result += f"\n⚖️ Tie.{difficulty_shifts_str}"
            else:
                result += f"\n❌ Failure.{difficulty_shifts_str}"
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
    A roll formula specifically for the Fate RPG system.
    It can handle any roll parameters as needed.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        super().__init__(roll_parameters_dict)
        self.skill = roll_parameters_dict.get("skill") if roll_parameters_dict else None

    def get_modifiers(self, character: FateCharacter) -> Dict[str, str]:
        modifiers = super().get_modifiers(character).items()
        if self.skill:
            skill_value = character.skills.get(self.skill)
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
        # Only display skills > 0
        skills = {k: v for k, v in character.skills.items() if v > 0}
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

        # --- Stunts ---
        stunts = character.stunts
        if stunts:
            stunt_lines = [f"• {stunt_name}" for stunt_name in stunts.keys()]
            embed.add_field(name="Stunts", value="\n".join(stunt_lines), inline=False)
        else:
            embed.add_field(name="Stunts", value="None", inline=False)
            
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
        
        # Add stunts to NPC scene entry when viewed by GM
        if is_gm and npc.stunts:
            stunt_names = list(npc.stunts.keys())
            if stunt_names:
                lines.append(f"**Stunts:** {', '.join(stunt_names)}")
        
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

    @ui.button(label="Edit Stress", style=discord.ButtonStyle.primary, row=1)
    async def edit_stress(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditStressModal(self.char_id))

    @ui.button(label="Edit Consequences", style=discord.ButtonStyle.primary, row=1)
    async def edit_consequences(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing consequences:", view=EditConsequencesView(interaction.guild.id, self.editor_id, self.char_id))

    @ui.button(label="Edit Fate Points", style=discord.ButtonStyle.primary, row=1)
    async def edit_fp(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditFatePointsModal(self.char_id))

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=2)
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
        
        # Create a view with buttons for different skill operations
        view = SkillManagementView(character, self.editor_id, self.char_id)
        await interaction.response.send_message(
            "Choose how you want to manage skills:",
            view=view,
            ephemeral=True
        )

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=2)
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

    @ui.button(label="Edit Stunts", style=discord.ButtonStyle.secondary, row=3)
    async def edit_stunts(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing stunts:", view=EditStuntsView(interaction.guild.id, self.editor_id, self.char_id))

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
    """
    Fate-specific roll modifiers view that includes a button to select skills.
    """
    def __init__(self, roll_formula_obj: FateRollModifiers, difficulty: int = None):
        self.character = None
        super().__init__(roll_formula_obj, difficulty)
        # Add a button for skill selection
        self.add_item(FateSelectSkillButton(self, roll_formula_obj.skill))
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))
    
    # Override to ensure we get the character before building the view
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.character = repo.get_active_character(interaction.guild.id, interaction.user.id)
        if not self.character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return False
        return True

class FateSelectSkillButton(ui.Button):
    """Button that opens a skill selection menu when clicked"""
    def __init__(self, parent_view: FateRollModifiersView, selected_skill: str = None):
        super().__init__(
            label=selected_skill if selected_skill else "Select Skill",
            style=discord.ButtonStyle.primary,
            row=3
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        character = repo.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return
        
        skills = character.skills if hasattr(character, 'skills') else {}
        skill_options = [SelectOption(label=f"{k} (+{v})" if v >= 0 else f"{k} ({v})", 
                                      value=k) 
                         for k, v in sorted(skills.items(), key=lambda x: (-x[1], x[0]))]
        
        if not skill_options:
            await interaction.response.send_message("❌ Your character has no skills to select.", ephemeral=True)
            return
        
        async def on_skill_selected(view, interaction2, skill):
            # Update the roll formula with the selected skill
            self.label = skill
            self.parent_view.roll_formula_obj.skill = skill
            skill_value = character.skills.get(skill, 0)
            await interaction2.response.edit_message(
                content=f"Selected skill: **{skill}** (+{skill_value if skill_value >= 0 else skill_value})",
                view=self.parent_view
            )
        
        await interaction.response.send_message(
            "Select a skill for your roll:",
            view=PaginatedSelectView(skill_options, on_skill_selected, interaction.user.id, prompt="Select a skill:"),
            ephemeral=True
        )

class SkillManagementView(ui.View):
    def __init__(self, character, editor_id, char_id):
        super().__init__(timeout=120)
        self.character = character
        self.editor_id = editor_id
        self.char_id = char_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Existing Skill", style=discord.ButtonStyle.primary, row=0)
    async def edit_existing_skill(self, interaction: discord.Interaction, button: ui.Button):
        skills = self.character.skills if self.character.skills else {}
        if not skills:
            await interaction.response.edit_message(
                content="This character doesn't have any skills yet. Add some first!",
                view=None
            )
            return

        skill_options = [SelectOption(label=k, value=k) for k in sorted(skills.keys())]

        async def on_skill_selected(view, interaction2, skill):
            current_value = skills.get(skill, 0)
            await interaction2.response.send_modal(EditSkillValueModal(self.char_id, skill, current_value))

        await interaction.response.edit_message(
            content="Select a skill to edit:",
            view=PaginatedSelectView(
                skill_options, 
                on_skill_selected, 
                interaction.user.id, 
                prompt="Select a skill to edit:"
            )
        )

    @ui.button(label="Add New Skill", style=discord.ButtonStyle.success, row=0)
    async def add_new_skill(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AddSkillModal(self.char_id))

    @ui.button(label="Remove Skill", style=discord.ButtonStyle.danger, row=0)
    async def remove_skill(self, interaction: discord.Interaction, button: ui.Button):
        skills = self.character.skills if self.character.skills else {}
        if not skills:
            await interaction.response.edit_message(
                content="This character doesn't have any skills to remove.",
                view=None
            )
            return

        skill_options = [SelectOption(label=k, value=k) for k in sorted(skills.keys())]

        async def on_skill_selected(view, interaction2, skill):
            # Remove the selected skill
            skills = self.character.skills
            if skill in skills:
                del skills[skill]
                self.character.skills = skills
                repo.set_character(interaction2.guild.id, self.character, system=SYSTEM)
                embed = FateSheet().format_full_sheet(self.character)
                view = FateSheetEditView(interaction2.user.id, self.char_id)
                await interaction2.response.edit_message(
                    content=f"✅ Removed skill: **{skill}**",
                    embed=embed,
                    view=view
                )
            else:
                await interaction2.response.edit_message(
                    content=f"❌ Skill not found: {skill}",
                    view=None
                )

        await interaction.response.edit_message(
            content="Select a skill to remove:",
            view=PaginatedSelectView(
                skill_options, 
                on_skill_selected, 
                interaction.user.id, 
                prompt="Select a skill to remove:"
            )
        )

    @ui.button(label="Bulk Edit Skills", style=discord.ButtonStyle.secondary, row=1)
    async def bulk_edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BulkEditSkillsModal(self.char_id))

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        embed = FateSheet().format_full_sheet(character)
        view = FateSheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(
            content="Operation cancelled.",
            embed=embed,
            view=view
        )

class AddSkillModal(ui.Modal, title="Add New Skill"):
    skill_name = ui.TextInput(label="Skill Name", required=True, max_length=50)
    skill_value = ui.TextInput(label="Skill Value (-3 to 6)", required=True, default="0", max_length=2)

    def __init__(self, char_id: str):
        super().__init__()
        self.char_id = char_id

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        
        # Validate skill value
        try:
            value_int = int(self.skill_value.value.strip())
            if value_int < -3 or value_int > 6:
                await interaction.response.send_message("❌ Skill value must be between -3 and 6.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid integer for skill value.", ephemeral=True)
            return
        
        # Add the new skill
        skills = character.skills
        skill_name = self.skill_name.value.strip()
        
        if not skill_name:
            await interaction.response.send_message("❌ Skill name cannot be empty.", ephemeral=True)
            return
            
        if skill_name in skills:
            await interaction.response.send_message(f"❌ Skill '{skill_name}' already exists. Use edit instead.", ephemeral=True)
            return
            
        skills[skill_name] = value_int
        character.skills = skills
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        
        embed = FateSheet().format_full_sheet(character)
        view = FateSheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(
            content=f"✅ Added new skill: **{skill_name}** (+{value_int if value_int >= 0 else value_int})",
            embed=embed,
            view=view
        )

class BulkEditSkillsModal(ui.Modal, title="Bulk Edit Skills"):
    def __init__(self, char_id: str):
        super().__init__()
        self.char_id = char_id
        
        # Get current skills to show as default
        character = get_character(None, char_id)  # We don't have guild_id here, but we have char_id
        skills = character.skills if character and character.skills else {}
        
        self.skills_text = ui.TextInput(
            label="Skills (format: Skill1:2,Skill2:1,Skill3:-1)",
            style=discord.TextStyle.paragraph,
            required=False,
            default=", ".join(f"{k}:{v}" for k, v in skills.items()),
            max_length=1000
        )
        self.add_item(self.skills_text)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        skills_dict = FateCharacter.parse_and_validate_skills(self.skills_text.value)
        
        if not skills_dict:
            skills_dict = {}  # Allow clearing all skills

        # Replace all skills with the new set
        character.skills = skills_dict
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        
        embed = FateSheet().format_full_sheet(character)
        view = FateSheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(
            content="✅ Skills updated!",
            embed=embed,
            view=view
        )

class EditStuntsView(ui.View):
    def __init__(self, guild_id: int, user_id: int, char_id: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.page = 0

        self.char = None
        self.stunts = {}  # Dictionary of {name: description}
        self.stunt_names = []  # List of stunt names for pagination
        self.max_page = 0
        self.load_data()
        self.render()

    def load_data(self):
        self.char = get_character(self.guild_id, self.char_id)
        if not self.char:
            self.stunts = {}
            self.stunt_names = []
        else:
            self.stunts = self.char.stunts
            self.stunt_names = list(self.stunts.keys())
        self.max_page = max(0, len(self.stunt_names) - 1)

    def render(self):
        self.clear_items()
        if self.stunt_names:
            current_stunt = self.stunt_names[self.page]
            label = f"{self.page + 1}/{len(self.stunt_names)}: {current_stunt[:30]}"
            self.add_item(ui.Button(label=label, disabled=True, row=0))
            
            # Description button to view full description
            self.add_item(ui.Button(label="📖 View Description", style=discord.ButtonStyle.primary, row=0, custom_id="view_desc"))
            
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
                await interaction.response.send_message("You can't edit this character.", ephemeral=True)
                return

            self.char = get_character(interaction.guild.id, self.char_id)
            self.stunts = self.char.stunts
            self.stunt_names = list(self.stunts.keys())

            if cid == "prev":
                self.page = max(0, self.page - 1)
            elif cid == "next":
                self.page = min(self.max_page, self.page + 1)
            elif cid == "view_desc":
                current_stunt = self.stunt_names[self.page]
                description = self.stunts.get(current_stunt, "No description available")
                await interaction.response.send_message(
                    f"**{current_stunt}**\n{description}", 
                    ephemeral=True
                )
                return
            elif cid == "edit":
                current_stunt = self.stunt_names[self.page]
                description = self.stunts.get(current_stunt, "")
                await interaction.response.send_modal(
                    EditStuntModal(self.char_id, current_stunt, description)
                )
                return
            elif cid == "remove":
                current_stunt = self.stunt_names[self.page]
                del self.stunts[current_stunt]
                self.char.stunts = self.stunts
                repo.set_character(interaction.guild.id, self.char, system=SYSTEM)
                self.stunt_names.remove(current_stunt)
                self.max_page = max(0, len(self.stunt_names) - 1)
                self.page = min(self.page, self.max_page)
            elif cid == "add":
                await interaction.response.send_modal(AddStuntModal(self.char_id))
                return
            elif cid == "done":
                await interaction.response.edit_message(
                    content="✅ Done editing stunts.", 
                    embed=FateSheet().format_full_sheet(self.char), 
                    view=FateSheetEditView(interaction.user.id, self.char_id)
                )
                return

            # Save changes and update view
            repo.set_character(interaction.guild.id, self.char, system=SYSTEM)
            self.load_data()
            self.render()
            await interaction.response.edit_message(view=self)
            
        return callback
    
class EditStuntModal(ui.Modal, title="Edit Stunt"):
    def __init__(self, char_id: str, stunt_name: str, description: str):
        super().__init__()
        self.char_id = char_id
        self.original_name = stunt_name
        
        self.name_field = ui.TextInput(
            label="Stunt Name",
            default=stunt_name,
            max_length=100,
            required=True
        )
        self.add_item(self.name_field)
        
        self.description_field = ui.TextInput(
            label="Description",
            default=description,
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.description_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        stunts = character.stunts
        
        new_name = self.name_field.value.strip()
        description = self.description_field.value.strip()
        
        if not new_name:
            await interaction.response.send_message("❌ Stunt name cannot be empty.", ephemeral=True)
            return
        
        # If name changed, remove old stunt and add with new name
        if new_name != self.original_name:
            if new_name in stunts and new_name != self.original_name:
                await interaction.response.send_message(f"❌ A stunt with the name '{new_name}' already exists.", ephemeral=True)
                return
            
            del stunts[self.original_name]
            
        stunts[new_name] = description
        character.stunts = stunts
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        
        await interaction.response.edit_message(
            content=f"✅ Stunt '{new_name}' updated.",
            view=EditStuntsView(interaction.guild.id, interaction.user.id, self.char_id)
        )


class AddStuntModal(ui.Modal, title="Add New Stunt"):
    def __init__(self, char_id: str):
        super().__init__()
        self.char_id = char_id
        
        self.name_field = ui.TextInput(
            label="Stunt Name",
            max_length=100,
            required=True
        )
        self.add_item(self.name_field)
        
        self.description_field = ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.description_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(interaction.guild.id, self.char_id)
        stunts = character.stunts
        
        name = self.name_field.value.strip()
        description = self.description_field.value.strip()
        
        if not name:
            await interaction.response.send_message("❌ Stunt name cannot be empty.", ephemeral=True)
            return
            
        if name in stunts:
            await interaction.response.send_message(f"❌ A stunt with the name '{name}' already exists.", ephemeral=True)
            return
            
        stunts[name] = description
        character.stunts = stunts
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        
        await interaction.response.edit_message(
            content=f"✅ Added new stunt: '{name}'",
            view=EditStuntsView(interaction.guild.id, interaction.user.id, self.char_id)
        )