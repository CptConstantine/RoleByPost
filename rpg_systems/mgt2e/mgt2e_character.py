from core.abstract_models import BaseCharacter
from typing import Any, Dict

from data import repo

class MGT2ECharacter(BaseCharacter):
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MGT2ECharacter":
        return cls(data)
    
    def get_attributes(self) -> Dict[str, int]:
        return self.data.get("attributes", {})

    def get_skills(self) -> Dict[str, int]:
        return self.data.get("skills", {})
    
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
        "Jack of All Trades": -3,
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

    def apply_defaults(self, is_npc=False, guild_id=None):
        super().apply_defaults(is_npc=is_npc, guild_id=guild_id)
        system_defaults = self.SYSTEM_SPECIFIC_NPC if is_npc else self.SYSTEM_SPECIFIC_CHARACTER
        for key, value in system_defaults.items():
            if key == "skills":
                # Use per-guild default if available
                skills = None
                if guild_id:
                    skills = repo.get_default_skills(guild_id, "mgt2e")
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
        """Parse a skills string like 'Admin:0, Gun Combat:1' into a dict. Add MGT2E-specific validation here."""
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
            if "(" in skill_name and ")" in skill_name and value >= 0:
                group = skill_name.split("(", 1)[0].strip()
                trained_groups.add(group)
        for skill_name, value in skills.items():
            if "(" not in skill_name and value >= 0:
                trained_groups.add(skill_name.strip())

        trained_skills = {}
        for skill_name, value in skills.items():
            if "(" in skill_name and ")" in skill_name:
                group = skill_name.split("(", 1)[0].strip()
                if group in trained_groups:
                    trained_skills[skill_name] = value
            elif skill_name in trained_groups:
                trained_skills[skill_name] = value
        return trained_skills

    def is_skill_trained(self, skills: dict, skill_name: str) -> bool:
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
            return -3

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