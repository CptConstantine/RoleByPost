from core.models import BaseCharacter
from typing import Any, Dict, List

from data import repo

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