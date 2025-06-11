from core.abstract_models import BaseCharacter
from typing import Any, Dict, List

from data import repo

class FateCharacter(BaseCharacter):
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FateCharacter":
        return cls(data)

    def get_skills(self) -> Dict[str, int]:
        return self.data.get("skills", {})
    
    def get_aspects(self) -> List[str]:
        return self.data.get("aspects", [])

    def get_hidden_aspects(self) -> List[int]:
        return self.data.get("hidden_aspects", [])

    def get_fate_points(self) -> int:
        return self.data.get("fate_points", 0)

    def get_stress(self) -> Dict[str, list]:
        return self.data.get("stress", {})

    def get_consequences(self) -> list:
        return self.data.get("consequences", [])
    
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

    def apply_defaults(self, is_npc=False, guild_id=None):
        super().apply_defaults(is_npc=is_npc, guild_id=guild_id)
        system_defaults = self.SYSTEM_SPECIFIC_NPC if is_npc else self.SYSTEM_SPECIFIC_CHARACTER
        for key, value in system_defaults.items():
            if key == "skills":
                # Use per-guild default if available
                skills = None
                if guild_id:
                    skills = repo.get_default_skills(guild_id, "fate")
                default_skills = dict(skills) if skills else dict(self.DEFAULT_SKILLS)
                self.data.setdefault("skills", {})
                for skill, val in default_skills.items():
                    if skill not in self.data["skills"]:
                        self.data["skills"][skill] = val
            else:
                if key not in self.data:
                    self.data[key] = value

    @staticmethod
    def parse_and_validate_skills(skills_str):
        """Parse a skills string like 'Fight:2, Stealth:1' into a dict. Add Fate-specific validation here."""
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