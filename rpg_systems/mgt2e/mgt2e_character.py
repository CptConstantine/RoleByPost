from collections import defaultdict
from typing import Any, Dict
import discord
from core.base_models import BaseCharacter, EntityType, EntityDefaults, EntityLinkType, RollFormula, SystemType
from core.roll_formula import RollFormula
from rpg_systems.mgt2e.mgt2e_roll_formula import MGT2ERollFormula
from rpg_systems.mgt2e.mgt2e_roll_views import MGT2ERollFormulaView
from data.repositories.repository_factory import repositories

SYSTEM = SystemType.MGT2E

class MGT2ECharacter(BaseCharacter):
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.PC: {
            "attributes": {"STR": 0, "DEX": 0, "END": 0, "INT": 0, "EDU": 0, "SOC": 0},
            "skills": {}
        },
        EntityType.NPC: {
            "attributes": {"STR": 0, "DEX": 0, "END": 0, "INT": 0, "EDU": 0, "SOC": 0},
            "skills": {}
        }
    })

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

    def apply_defaults(self, entity_type: EntityType, guild_id=None):
        """
        Apply system-specific default fields to a character.
        This method uses the @property accessors for all fields.
        """
        super().apply_defaults(entity_type, guild_id)

        # Get the appropriate defaults based on entity type
        system_defaults = self.ENTITY_DEFAULTS.get_defaults(entity_type)
        
        for key, value in system_defaults.items():
            if key == "skills":
                # Use per-guild default if available
                skills = None
                if guild_id:
                    skills = repositories.default_skills.get_default_skills(str(guild_id), SYSTEM)
                default_skills = dict(skills) if skills else dict(self.DEFAULT_SKILLS)
                # Only add missing skills, don't overwrite existing ones
                updated_skills = dict(self.skills)
                for skill, val in default_skills.items():
                    if skill not in updated_skills:
                        updated_skills[skill] = val
                self.skills = updated_skills
            else:
                # Use property setters for all other fields
                current_value = getattr(self, key, None)
                if current_value in (None, [], {}, 0, False):
                    setattr(self, key, value)
    
    def get_sheet_edit_view(self, editor_id: int, is_gm: bool) -> discord.ui.View:
        from rpg_systems.mgt2e.mgt2e_sheet_edit_views import MGT2ESheetEditView
        return MGT2ESheetEditView(editor_id=editor_id, char_id=self.id)
    
    async def edit_requested_roll(self, interaction: discord.Interaction, roll_formula_obj: MGT2ERollFormula, difficulty: int = None):
        """
        Opens a view for editing the roll parameters, prepopulated with any requested skill and attribute.
        """
        view = MGT2ERollFormulaView(roll_formula_obj, difficulty)
        
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

    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollFormula, difficulty: int = None):
        """
        Prints the roll result
        """
        result, total = roll_formula_obj.roll_formula(self, "2d6")

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
                    value = v.strip()
                    # Set default value of 0 if value is None or empty
                    if value.lower() == 'none' or value == '':
                        skills_dict[k.strip()] = -3
                    else:
                        skills_dict[k.strip()] = int(value)
                except ValueError:
                    # Set default value of 0 if conversion fails
                    skills_dict[k.strip()] = 0
        # Add Fate-specific validation here if needed (e.g., pyramid structure)
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

    def format_full_sheet(self, guild_id: int, is_gm: bool = False) -> discord.Embed:
        """Format the character sheet for MGT2E system"""
        # Use the .name property instead of get_name()
        embed = discord.Embed(
            title=f"{self.name or 'Traveller'}",
            color=discord.Color.dark_teal()
        )

        # --- Attributes ---
        attributes = self.attributes  # Use property
        if attributes:
            attr_lines = [
                f"**STR**: {attributes.get('STR', 0)}   **DEX**: {attributes.get('DEX', 0)}   **END**: {attributes.get('END', 0)}",
                f"**INT**: {attributes.get('INT', 0)}   **EDU**: {attributes.get('EDU', 0)}   **SOC**: {attributes.get('SOC', 0)}"
            ]
            embed.add_field(name="Attributes", value="\n".join(attr_lines), inline=False)
        else:
            embed.add_field(name="Attributes", value="None", inline=False)

        # --- Skills ---
        skills = self.skills  # Use property
        trained_skills = self.get_trained_skills(skills)
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

        # --- Inventory ---
        items = self.get_children(guild_id=guild_id, link_type=EntityLinkType.POSSESSES)
        if items:
            # Group items by entity type and count them
            item_counts = {}
            for item in items:
                entity_type = item.entity_type
                if entity_type in item_counts:
                    item_counts[entity_type] += 1
                else:
                    item_counts[entity_type] = 1
            
            # Format the display
            item_lines = [f"• {entity_type.value}(s): {count}" for entity_type, count in item_counts.items()]
            embed.add_field(name="__Inventory__", value="\n".join(item_lines), inline=False)
        else:
            embed.add_field(name="__Inventory__", value="None", inline=False)

        # --- Notes ---
        notes = self.notes  # Use property, which is a list
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)

        return embed

    def format_npc_scene_entry(self, is_gm: bool) -> str:
        """Format NPC entry for scene display"""
        # Use .name and .notes properties
        lines = [f"**{self.name or 'NPC'}**"]
        if is_gm and self.notes:
            notes_display = "\n".join(self.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)

def get_character(char_id) -> MGT2ECharacter:
    character = repositories.entity.get_by_id(str(char_id))
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
