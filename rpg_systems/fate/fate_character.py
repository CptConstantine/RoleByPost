from typing import Any, Dict, List, Union
import discord
from core.models import BaseCharacter
from core.utils import roll_formula
from data.repositories.repository_factory import repositories
from rpg_systems.fate.aspect import Aspect
from rpg_systems.fate.fate_roll_modifiers import FateRollModifiers
from rpg_systems.fate.fate_roll_views import FateRollModifiersView

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
        "refresh": 3,  
        "fate_points": 3,
        "skills": {},
        "aspects": [],  # This will now hold objects, not strings
        "stress": {"physical": [False, False], "mental": [False, False]},
        "consequences": ["Mild: None", "Moderate: None", "Severe: None"],
        "stunts": {}  # Added stunts as a dictionary: {name: description}
    }
    SYSTEM_SPECIFIC_NPC = {
        "refresh": 0,
        "fate_points": 0,
        "skills": {},
        "aspects": [],  # This will now hold objects, not strings
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
    def aspects(self) -> List[Aspect]:
        """Get aspects as list of Aspect objects"""
        aspect_dicts = self.data.get("aspects", [])
        return [Aspect.from_dict(aspect_dict) for aspect_dict in aspect_dicts]

    @aspects.setter
    def aspects(self, value: List[Union[Aspect, Dict[str, Any]]]):
        """Set aspects from a list of Aspect objects or dictionaries"""
        aspect_dicts = []
        for item in value:
            if isinstance(item, Aspect):
                aspect_dicts.append(item.to_dict())
            else:
                # Assume it's already a dictionary
                aspect_dicts.append(item)
        self.data["aspects"] = aspect_dicts

    @property
    def fate_points(self) -> int:
        return self.data.get("fate_points", 0)

    @fate_points.setter
    def fate_points(self, value: int):
        self.data["fate_points"] = value

    @property
    def refresh(self) -> int:
        return self.data.get("refresh", 0)

    @refresh.setter
    def refresh(self, value: int):
        self.data["refresh"] = value

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
                    skills = repositories.default_skills.get_default_skills(guild_id, SYSTEM)
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
                    value = v.strip()
                    # Set default value of 0 if value is None or empty
                    if value.lower() == 'none' or value == '':
                        skills_dict[k.strip()] = 0
                    else:
                        skills_dict[k.strip()] = int(value)
                except ValueError:
                    # Set default value of 0 if conversion fails
                    skills_dict[k.strip()] = 0
        # Add Fate-specific validation here if needed (e.g., pyramid structure)
        return skills_dict

def get_character(char_id) -> FateCharacter:
    character = repositories.character.get_by_id(str(char_id))
    return character if character else None
