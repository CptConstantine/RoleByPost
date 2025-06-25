from collections import defaultdict
from typing import Any, Dict
import discord
from discord import SelectOption, ui
from core.models import BaseCharacter, BaseSheet, RollModifiers
from core.shared_views import EditNameModal, EditNotesModal, FinalizeRollButton, PaginatedSelectView, RollModifiersView
from core.utils import get_character, roll_formula
from data import repo

SYSTEM = "mgt2e"

class MGT2ECharacter(BaseCharacter):
    DEFAULT_SKILLS = {
        "Admin": -3,
        "Advocate": -3,
        "Animals (Handling)": -3,
        "Animals (Veterinary)": -3,
        "Animals (Training)": -3,
        "Art (Performer)": -3,
        "Art (Holography)": -3,
        "Art (Instrument)": -3,
        "Art (Visual Media)": -3,
        "Art (Write)": -3,
        "Astrogation": -3,
        "Athletics (Dexterity)": -3,
        "Athletics (Endurance)": -3,
        "Athletics (Strength)": -3,
        "Broker": -3,
        "Carouse": -3,
        "Deception": -3,
        "Diplomat": -3,
        "Drive (Hovercraft)": -3,
        "Drive (Mole)": -3,
        "Drive (Track)": -3,
        "Drive (Walker)": -3,
        "Drive (Wheel)": -3,
        "Electronics (Comms)": -3,
        "Electronics (Computers)": -3,
        "Electronics (Remote Ops)": -3,
        "Electronics (Sensors)": -3,
        "Engineer (M-drive)": -3,
        "Engineer (J-drive)": -3,
        "Engineer (Life Suport)": -3,
        "Engineer (Power)": -3,
        "Explosives": -3,
        "Flyer (Airship)": -3,
        "Flyer (Grav)": -3,
        "Flyer (Ornithopter)": -3,
        "Flyer (Rotor)": -3,
        "Flyer (Wing)": -3,
        "Gambler": -3,
        "Gunner (Turret)": -3,
        "Gunner (Ortillery)": -3,
        "Gunner (Screen)": -3,
        "Gunner (Capital)": -3,
        "Gun Combat (Archaic)": -3,
        "Gun Combat (Energy)": -3,
        "Gun Combat (Slug)": -3,
        "Heavy Weapons (Artillery)": -3,
        "Heavy Weapons (Portable)": -3,
        "Heavy Weapons (Vehicle)": -3,
        "Investigate": -3,
        "Jack of All Trades": 0,
        "Language (Galanglic)": -3,
        "Language (Vilany)": -3,
        "Language (Zdetl)": -3,
        "Language (Oynprith)": -3,
        "Language (Trokh)": -3,
        "Language (Gvegh)": -3,
        "Leadership": -3,
        "Mechanic": -3,
        "Medic": -3,
        "Melee (Unarmed)": -3,
        "Melee (Blade)": -3,
        "Melee (Bludgeon)": -3,
        "Melee (Natural)": -3,
        "Navigation": -3,
        "Persuade": -3,
        "Pilot (Small Craft)": -3,
        "Pilot (Spacecraft)": -3,
        "Pilot (Capital Ships)": -3,
        "Recon": -3,
        "Science (Archaeology)": -3,
        "Science (Astronomy)": -3,
        "Science (Biology)": -3,
        "Science (Chemistry)": -3,
        "Science (Cosmology)": -3,
        "Science (Cybernetics)": -3,
        "Science (Economics)": -3,
        "Science (Genetics)": -3,
        "Science (History)": -3,
        "Science (Linguistics)": -3,
        "Science (Philosophy)": -3,
        "Science (Physics)": -3,
        "Science (Planetology)": -3,
        "Science (Psionicology)": -3,
        "Science (Psychology)": -3,
        "Science (Robotics)": -3,
        "Science (Xenology)": -3,
        "Seafarer (Ocean Ships)": -3,
        "Seafarer (Personal)": -3,
        "Seafarer (Sail)": -3,
        "Seafarer (Submarine)": -3,
        "Stealth": -3,
        "Steward": -3,
        "Streetwise": -3,
        "Survival": -3,
        "Tactics (Military)": -3,
        "Tactics (Naval)": -3,
        "Vacc Suit": -3
    }
    SYSTEM_SPECIFIC_CHARACTER = {
        "attributes": {"STR": 0, "DEX": 0, "END": 0, "INT": 0, "EDU": 0, "SOC": 0},
        "skills": {}
    }
    SYSTEM_SPECIFIC_NPC = {
        "attributes": {"STR": 0, "DEX": 0, "END": 0, "INT": 0, "EDU": 0, "SOC": 0},
        "skills": {}
    }

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MGT2ECharacter":
        return cls(data)

    @property
    def attributes(self) -> Dict[str, int]:
        return self.data.get("attributes", {})

    @attributes.setter
    def attributes(self, value: Dict[str, int]):
        self.data["attributes"] = value

    @property
    def skills(self) -> Dict[str, int]:
        return self.data.get("skills", {})

    @skills.setter
    def skills(self, value: Dict[str, int]):
        self.data["skills"] = value

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
                    skills = repo.get_default_skills(guild_id, "mgt2e")
                default_skills = dict(skills) if skills else dict(self.DEFAULT_SKILLS)
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
    
    async def edit_requested_roll(self, interaction: discord.Interaction, roll_formula_obj: "MGT2ERollModifiers", difficulty: int = None):
        """
        Opens a view for editing the roll parameters, prepopulated with any requested skill and attribute.
        """
        view = MGT2ERollModifiersView(roll_formula_obj, difficulty)
        
        # Create a message that shows what was initially requested
        content = "Adjust your roll formula as needed, then finalize to roll."
        parts = []
        
        if roll_formula_obj.skill:
            skill_mod = self.get_skill_modifier(self.skills, roll_formula_obj.skill)
            parts.append(f"skill: **{roll_formula_obj.skill}** ({skill_mod})")
        
        if roll_formula_obj.attribute:
            attr_val = self.attributes.get(roll_formula_obj.attribute.upper(), 0)
            attr_mod = self.get_attribute_modifier(attr_val)
            parts.append(f"attribute: **{roll_formula_obj.attribute.upper()}** ({attr_val}, MOD: {attr_mod})")
        
        if parts:
            content = f"Roll requested with {', '.join(parts)}\n{content}"
        
        await interaction.response.send_message(
            content=content,
            view=view,
            ephemeral=True
        )

    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollModifiers, difficulty: int = None):
        """
        Prints the roll result
        """
        result, total = roll_formula(self, "2d6", roll_formula_obj)

        difficulty_shifts_str = ""
        if difficulty:
            shifts = total - difficulty
            difficulty_shifts_str = f" (Needed {difficulty}) Shifts: {shifts}"
            if total >= difficulty:
                result += f"\n✅ Success.{difficulty_shifts_str}"
            else:
                result += f"\n❌ Failure.{difficulty_shifts_str}"
        
        await interaction.response.send_message(result, ephemeral=False)

    @staticmethod
    def parse_and_validate_skills(skills_str):
        """
        Parse a skills string like 'Admin:0, Gun Combat:1' into a dict.
        This method is static and does not use properties, but you can use the result
        to assign to the .skills property of a MGT2ECharacter instance.
        """
        skills_dict = {}
        for entry in skills_str.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        # Add any MGT2E-specific validation here if needed
        return skills_dict

    def get_trained_skills(self, skills: dict) -> dict:
        trained_groups = set()
        for skill_name, value in skills.items():
            if skill_name == "Jack of All Trades" and value <= 0:
                continue
            if "(" in skill_name and ")" in skill_name and value >= 0:
                group = skill_name.split("(", 1)[0].strip()
                trained_groups.add(group)
        for skill_name, value in skills.items():
            if skill_name == "Jack of All Trades" and value <= 0:
                continue
            if "(" not in skill_name and value >= 0:
                trained_groups.add(skill_name.strip())

        trained_skills = {}
        for skill_name, value in skills.items():
            if skill_name == "Jack of All Trades" and value <= 0:
                continue
            if "(" in skill_name and ")" in skill_name:
                group = skill_name.split("(", 1)[0].strip()
                if group in trained_groups:
                    trained_skills[skill_name] = value
            elif skill_name in trained_groups:
                trained_skills[skill_name] = value
        return trained_skills

    def is_skill_trained(self, skills: dict, skill_name: str) -> bool:
        if skill_name == "Jack of All Trades":
            return False
        if "(" in skill_name and ")" in skill_name:
            group = skill_name.split("(", 1)[0].strip()
            for k, v in skills.items():
                if (k.startswith(group) and v >= 0) or (k == group and v >= 0):
                    return True
            return False
        else:
            if skills.get(skill_name, None) is not None and skills[skill_name] >= 0:
                return True
            for k, v in skills.items():
                if k.startswith(skill_name + " (") and v >= 0:
                    return True
            return False

    def get_skill_modifier(self, skills: dict, skill_name: str) -> int:
        if self.is_skill_trained(skills, skill_name):
            return skills.get(skill_name, 0)
        else:
            untrained = -3
            if skills.get("Jack of All Trades", None) is not None:
                untrained = untrained + skills["Jack of All Trades"]
            return untrained

    def get_attribute_modifier(self, attr_val) -> int:
        if attr_val <= 0:
            return -3
        elif attr_val <= 2:
            return -2
        elif attr_val <= 5:
            return -1
        elif attr_val <= 8:
            return 0
        elif attr_val <= 11:
            return 1
        elif attr_val <= 14:
            return 2
        else:
            return 3

class MGT2ERollModifiers(RollModifiers):
    """
    A roll formula specifically for the MGT2E RPG system.
    It can handle any roll parameters as needed.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        super().__init__(roll_parameters_dict)
        self.skill = roll_parameters_dict.get("skill") if roll_parameters_dict else None
        self.attribute = roll_parameters_dict.get("attribute") if roll_parameters_dict else None

    def get_modifiers(self, character: MGT2ECharacter) -> Dict[str, str]:
        modifiers = super().get_modifiers(character).items()
        if self.skill:
            skill_value = character.skills.get(self.skill, 0)
            modifiers = list(modifiers) + [(self.skill, skill_value)]
        if self.attribute:
            attribute_value = character.attributes.get(self.attribute, 0)
            modifiers = list(modifiers) + [(self.attribute, character.get_attribute_modifier(attribute_value))]
        return dict(modifiers)
        
class MGT2ESheet(BaseSheet):
    def format_full_sheet(self, character: MGT2ECharacter) -> discord.Embed:
        # Use the .name property instead of get_name()
        embed = discord.Embed(
            title=f"{character.name or 'Traveller'}",
            color=discord.Color.dark_teal()
        )

        # --- Attributes ---
        attributes = character.attributes  # Use property
        if attributes:
            attr_lines = [
                f"**STR**: {attributes.get('STR', 0)}   **DEX**: {attributes.get('DEX', 0)}   **END**: {attributes.get('END', 0)}",
                f"**INT**: {attributes.get('INT', 0)}   **EDU**: {attributes.get('EDU', 0)}   **SOC**: {attributes.get('SOC', 0)}"
            ]
            embed.add_field(name="Attributes", value="\n".join(attr_lines), inline=False)
        else:
            embed.add_field(name="Attributes", value="None", inline=False)

        # --- Skills ---
        skills = character.skills  # Use property
        trained_skills = character.get_trained_skills(skills)
        if trained_skills:
            sorted_skills = sorted(trained_skills.items(), key=lambda x: (x[0]))
            skill_lines = []
            for k, v in sorted_skills:
                skill_lines.append(f"**{k}**: {v}")
            chunk = ""
            count = 1
            for line in skill_lines:
                if len(chunk) + len(line) + 1 > 1024:
                    if count == 1:
                        embed.add_field(name=f"Skills", value=chunk.strip(), inline=False)
                    chunk = ""
                    count += 1
                chunk += line + "\n"
            if chunk:
                embed.add_field(name=f"Skills", value=chunk.strip(), inline=False)
        else:
            embed.add_field(name="Skills", value="None", inline=False)

        # --- Notes ---
        notes = character.notes  # Use property, which is a list
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)

        return embed

    def format_npc_scene_entry(self, npc: MGT2ECharacter, is_gm: bool):
        # Use .name and .notes properties
        lines = [f"**{npc.name or 'NPC'}**"]
        if is_gm and npc.notes:
            notes_display = "\n".join(npc.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)

    def roll(self, character: MGT2ECharacter, *, skill=None, attribute=None, formula=None):
        import random, re

        if formula:
            arg = formula.replace(" ", "").lower()
            fudge_pattern = r'(\d*)d[fF]([+-]\d+)?'
            fudge_match = re.fullmatch(fudge_pattern, arg)
            if fudge_match:
                num_dice = int(fudge_match.group(1)) if fudge_match.group(1) else 4
                modifier = int(fudge_match.group(2)) if fudge_match.group(2) else 0
                rolls = [random.choice([-1, 0, 1]) for _ in range(num_dice)]
                symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
                total = sum(rolls) + modifier
                response = f'🎲 Fudge Rolls: `{" ".join(symbols)}`'
                if modifier:
                    response += f' {"+" if modifier > 0 else ""}{modifier}'
                response += f'\n🧮 Total: {total}'
                return response
            pattern = r'(\d*)d(\d+)([+-]\d+)?'
            match = re.fullmatch(pattern, arg)
            if match:
                num_dice = int(match.group(1)) if match.group(1) else 1
                die_size = int(match.group(2))
                modifier = int(match.group(3)) if match.group(3) else 0
                if num_dice > 100 or die_size > 1000:
                    return "😵 That's a lot of dice. Try fewer."
                rolls = [random.randint(1, die_size) for _ in range(num_dice)]
                total = sum(rolls) + modifier
                response = f'🎲 Rolled: {rolls}'
                if modifier:
                    response += f' {"+" if modifier > 0 else ""}{modifier}'
                response += f'\n🧮 Total: {total}'
                return response
            return "❌ Invalid formula. Use like `2d6+3` or `4df+1`."

        if not skill or not attribute:
            return "❌ Please specify both a skill and an attribute."
        skills = character.skills  # Use property
        skill_mod = character.get_skill_modifier(skills, skill)
        attr_val = character.attributes.get(attribute.upper(), 0)  # Use property
        attr_mod = character.get_attribute_modifier(attr_val)
        rolls = [random.randint(1, 6) for _ in range(2)]
        total = sum(rolls) + skill_mod + attr_mod
        response = (
            f'🎲 2d6: {rolls} + **{skill}** ({skill_mod}) + **{attribute.upper()}** mod ({attr_mod})\n'
            f'🧮 Total: {total}'
        )
        return response

def get_skill_categories(skills_dict):
    categories = defaultdict(list)
    for skill in skills_dict:
        if "(" in skill and ")" in skill:
            group = skill.split("(", 1)[0].strip()
            categories[group].append(skill)
        else:
            categories[skill].append(skill)
    return categories

class MGT2ESheetEditView(ui.View):
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
        character = get_character(interaction.guild.id, self.char_id)
        attrs = character.attributes if character else {}
        await interaction.response.send_modal(EditAttributesModal(self.char_id, attrs))

    @ui.button(label="Edit Skills", style=discord.ButtonStyle.secondary, row=1)
    async def edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        skills = character.skills if character else {}
        categories = get_skill_categories(MGT2ECharacter.DEFAULT_SKILLS)
        category_options = [SelectOption(label=cat, value=cat) for cat in sorted(categories.keys())]

        async def on_category_selected(view, interaction, category):
            skills_in_cat = categories[category]
            
            # If there's only one skill in this category and it's the same as the category name,
            # it means this is a standalone skill with no specialties
            if len(skills_in_cat) == 1 and skills_in_cat[0] == category:
                # Skip the skill selection step and directly open the edit modal
                await interaction.response.send_modal(EditSkillValueModal(self.char_id, category))
            else:
                # Multiple skills or specialties, continue with skill selection
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

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=1)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        await interaction.response.send_modal(
            EditNameModal(
                self.char_id,
                character.name if character else "",
                SYSTEM,
                lambda editor_id, char_id: (MGT2ESheet().format_full_sheet(get_character(interaction.guild.id, char_id)), MGT2ESheetEditView(editor_id, char_id))
            )
        )

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=4)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(interaction.guild.id, self.char_id)
        # Only allow owner or GM
        if (interaction.user.id != int(character.owner_id) and not await repo.has_gm_permission(interaction.guild.id, interaction.user)):
            await interaction.response.send_message("❌ Only the owner or a GM can edit notes.", ephemeral=True)
            return
        notes = "\n".join(character.notes) if character and character.notes else ""
        await interaction.response.send_modal(
            EditNotesModal(
                self.char_id,
                notes,
                SYSTEM,
                lambda editor_id, char_id: (MGT2ESheet().format_full_sheet(get_character(interaction.guild.id, char_id)), MGT2ESheetEditView(editor_id, char_id))
            )
        )

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
        categories = get_skill_categories(skills)
        category_options = [SelectOption(label=cat, value=cat) for cat in sorted(categories.keys())]

        async def on_category_selected(view, interaction, category):
            skills_in_cat = categories[category]
            skill_options = [SelectOption(label=skill, value=skill) for skill in sorted(skills_in_cat)]
            async def on_skill_selected(view2, interaction2, skill):
                attributes = character.attributes if character else {}
                attr_options = [SelectOption(label=k, value=k) for k in sorted(attributes.keys())]
                async def on_attr_selected(view3, interaction3, attr):
                    result = MGT2ESheet().roll(character, skill=skill, attribute=attr)
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
        character = get_character(interaction.guild.id, self.char_id)
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
        embed = MGT2ESheet().format_full_sheet(character)
        view = MGT2ESheetEditView(interaction.user.id, self.char_id)
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
        character = get_character(interaction.guild.id, self.char_id)
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
        embed = MGT2ESheet().format_full_sheet(character)
        view = MGT2ESheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(content="✅ Skills updated!", embed=embed, view=view)

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
        character = get_character(interaction.guild.id, self.char_id)
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
            
        repo.set_character(interaction.guild.id, character, system=SYSTEM)
        embed = MGT2ESheet().format_full_sheet(character)
        view = MGT2ESheetEditView(interaction.user.id, self.char_id)
        
        # Create a more informative success message that mentions if other skills were updated
        content = f"✅ {self.skill} updated."
        if value.lower() == "untrained" and "(" in self.skill and ")" in self.skill:
            content += " Related skill specialties have also been set to untrained."
        elif value.lower() != "untrained" and int(value) >= 0 and "(" in self.skill and ")" in self.skill:
            content += " Related skill specialties have also been set to at least 0."
            
        await interaction.response.edit_message(content=content, embed=embed, view=view)

class MGT2ERollModifiersView(RollModifiersView):
    """
    MGT2E-specific roll modifiers view that includes buttons to select skills and attributes.
    """
    def __init__(self, roll_formula_obj: MGT2ERollModifiers, difficulty: int = None):
        self.character = None
        super().__init__(roll_formula_obj, difficulty)
        # Add buttons for skill and attribute selection
        self.add_item(MGT2ESelectSkillButton(self, roll_formula_obj.skill))
        self.add_item(MGT2ESelectAttributeButton(self, roll_formula_obj.attribute))
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))
    
    # Override to ensure we get the character before building the view
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.character = repo.get_active_character(interaction.guild.id, interaction.user.id)
        if not self.character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return False
        return True

class MGT2ESelectSkillButton(ui.Button):
    """Button that opens a skill category selection menu when clicked"""
    def __init__(self, parent_view: MGT2ERollModifiersView, selected_skill: str = None):
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
        categories = get_skill_categories(skills)
        category_options = [SelectOption(label=cat, value=cat) for cat in sorted(categories.keys())]
        
        if not category_options:
            await interaction.response.send_message("❌ Your character has no skill categories.", ephemeral=True)
            return
        
        async def on_category_selected(view, interaction, category):
            skills_in_cat = categories[category]
            
            # If there's only one skill in this category and it's the same as the category name,
            # it means this is a standalone skill with no specialties
            if len(skills_in_cat) == 1 and skills_in_cat[0] == category:
                # Skip the skill selection step and directly update the roll formula
                self.label = category
                self.parent_view.roll_formula_obj.skill = category
                skill_mod = character.get_skill_modifier(skills, category)
                await interaction.response.edit_message(
                    content=f"Selected skill: **{category}** ({skill_mod})",
                    view=self.parent_view
                )
            else:
                # Multiple skills or specialties, continue with skill selection
                skill_options = [SelectOption(label=f"{skill} ({skills.get(skill, -3)})", value=skill) 
                                for skill in sorted(skills_in_cat)]
                
                async def on_skill_selected(view2, interaction2, skill):
                    # Update the roll formula with the selected skill
                    self.label = skill
                    self.parent_view.roll_formula_obj.skill = skill
                    skill_mod = character.get_skill_modifier(skills, skill)
                    await interaction2.response.edit_message(
                        content=f"Selected skill: **{skill}** ({skill_mod})",
                        view=self.parent_view
                    )
                
                await interaction.response.edit_message(
                    content=f"Select a skill in {category}:",
                    view=PaginatedSelectView(
                        skill_options, 
                        on_skill_selected, 
                        interaction.user.id, 
                        prompt=f"Select a skill in {category}:"
                    )
                )
        
        await interaction.response.send_message(
            "Select a skill category:",
            view=PaginatedSelectView(
                category_options, 
                on_category_selected, 
                interaction.user.id, 
                prompt="Select a skill category:"
            ),
            ephemeral=True
        )

class MGT2ESelectAttributeButton(ui.Button):
    """Button that opens an attribute selection menu when clicked"""
    def __init__(self, parent_view: MGT2ERollModifiersView, selected_attribute: str = None):
        super().__init__(
            label=selected_attribute if selected_attribute else "Select Attribute",
            style=discord.ButtonStyle.secondary,
            row=3
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        character = repo.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return
        
        attributes = character.attributes if hasattr(character, 'attributes') else {}
        attr_options = []
        
        for k, v in sorted(attributes.items()):
            mod = character.get_attribute_modifier(v)
            attr_options.append(SelectOption(
                label=f"{k}: {v} (MOD: {mod})",
                value=k
            ))
        
        if not attr_options:
            await interaction.response.send_message("❌ Your character has no attributes.", ephemeral=True)
            return
        
        async def on_attr_selected(view, interaction2, attr):
            # Update the roll formula with the selected attribute
            self.label = attr
            self.parent_view.roll_formula_obj.attribute = attr
            attr_val = attributes.get(attr, 0)
            attr_mod = character.get_attribute_modifier(attr_val)
            await interaction2.response.edit_message(
                content=f"Selected attribute: **{attr}** ({attr_val}, MOD: {attr_mod})",
                view=self.parent_view
            )
        
        await interaction.response.send_message(
            "Select an attribute for your roll:",
            view=PaginatedSelectView(attr_options, on_attr_selected, interaction.user.id, prompt="Select an attribute:"),
            ephemeral=True
        )