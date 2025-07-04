from typing import Any, Dict, List, Union
import discord
from core.models import BaseCharacter, EntityDefaults, EntityType
from core.utils import roll_formula
from data.repositories.repository_factory import repositories
from rpg_systems.fate.aspect import Aspect
from rpg_systems.fate.fate_roll_modifiers import FateRollModifiers
from rpg_systems.fate.fate_roll_views import FateRollModifiersView
from rpg_systems.fate.stress_track import StressTrack, StressBox
from rpg_systems.fate.consequence_track import ConsequenceTrack, Consequence

SYSTEM = "fate"

class FateCharacter(BaseCharacter):
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.PC: {
            "refresh": 3,  
            "fate_points": 3,
            "skills": {},
            "aspects": [],
            "stress_tracks": [
                {
                    "track_name": "Physical",
                    "boxes": [{"value": 1, "is_filled": False}, {"value": 2, "is_filled": False}],
                    "linked_skill": "Physique"
                },
                {
                    "track_name": "Mental",
                    "boxes": [{"value": 1, "is_filled": False}, {"value": 2, "is_filled": False}],
                    "linked_skill": "Will"
                }
            ],
            "consequence_tracks": [
                {
                    "name": "Consequences",
                    "consequences": [
                        {"name": "Mild", "severity": 2, "aspect": None},
                        {"name": "Moderate", "severity": 4, "aspect": None},
                        {"name": "Severe", "severity": 6, "aspect": None}
                    ]
                }
            ],
            "stunts": {}  # Added stunts as a dictionary: {name: description}
        },
        EntityType.NPC: {
            "refresh": 0,
            "fate_points": 0,
            "skills": {},
            "aspects": [],
            "stress_tracks": [
                {
                    "track_name": "Physical",
                    "boxes": [{"value": 1, "is_filled": False}, {"value": 2, "is_filled": False}],
                    "linked_skill": "Physique"
                },
                {
                    "track_name": "Mental",
                    "boxes": [{"value": 1, "is_filled": False}, {"value": 2, "is_filled": False}],
                    "linked_skill": "Will"
                }
            ],
            "consequence_tracks": [
                {
                    "name": "Consequences",
                    "consequences": [{"name": "Mild", "severity": 2, "aspect": None}]
                }
            ],
            "stunts": {}  # Added stunts for NPCs too
        }
    })

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

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FateCharacter":
        return cls(data)

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
    def stress_tracks(self) -> List[StressTrack]:
        """Get stress tracks as StressTrack objects"""
        tracks_data = self.data.get("stress_tracks", [])
        return [StressTrack.from_dict(track) for track in tracks_data]

    @stress_tracks.setter
    def stress_tracks(self, value: List[StressTrack]):
        """Set stress tracks from StressTrack objects"""
        self.data["stress_tracks"] = [track.to_dict() for track in value]

    @property
    def consequence_tracks(self) -> List[ConsequenceTrack]:
        """Get consequence track as a list of ConsequenceTrack objects"""
        tracks_data = self.data.get("consequence_tracks", [])
        return [ConsequenceTrack.from_dict(track) for track in tracks_data]

    @consequence_tracks.setter
    def consequence_tracks(self, value: List[ConsequenceTrack]):
        """Set consequence tracks from a list of ConsequenceTrack objects"""
        self.data["consequence_tracks"] = [track.to_dict() for track in value]

    # Legacy properties for backward compatibility during migration
    @property
    def stress(self) -> Dict[str, list]:
        """Legacy stress property - returns boolean lists for backward compatibility"""
        tracks = {}
        for track in self.stress_tracks:
            bool_list = [box.is_filled for box in track.boxes]
            linked_skill = track.linked_skill.lower() if track.linked_skill else None
            tracks[track.track_name.lower()] = bool_list
        return tracks

    @stress.setter
    def stress(self, value: Dict[str, list]):
        """Legacy stress setter - converts from boolean lists"""
        stress_tracks = []
        for track_name, bool_list in value.items():
            boxes = [StressBox(value=i + 1, is_filled=filled) for i, filled in enumerate(bool_list)]
            linked_skill = None
            if "physical" in track_name:
                linked_skill = "Physique"
            elif "mental" in track_name:
                linked_skill = "Will"
            stress_tracks.append(StressTrack(track_name=track_name.capitalize(), boxes=boxes, linked_skill=linked_skill))
        self.stress_tracks = stress_tracks

    # Add property getter and setter for stunts
    @property
    def stunts(self) -> Dict[str, str]:
        return self.data.get("stunts", {})
        
    @stunts.setter
    def stunts(self, value: Dict[str, str]):
        self.data["stunts"] = value

    def apply_defaults(self, entity_type: EntityType, guild_id=None):
        """
        Apply system-specific default fields to a character dict.
        This method uses the @property accessors for all fields.
        """
        super().apply_defaults(entity_type=entity_type, guild_id=guild_id)

        # Get the appropriate defaults based on entity type
        system_defaults = self.ENTITY_DEFAULTS.get_defaults(entity_type)
        
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
            elif key == "stress_tracks":
                # Handle stress tracks - convert dict format to StressTrack objects
                if not self.stress_tracks:
                    stress_tracks = []
                    for track_data in value:
                        stress_tracks.append(StressTrack.from_dict(track_data))
                    self.stress_tracks = stress_tracks
            elif key == "consequence_tracks":
                # Handle consequence tracks - convert dict format to ConsequenceTrack objects
                if not self.consequence_tracks:
                    consequence_tracks = []
                    for track_data in value:
                        consequence_tracks.append(ConsequenceTrack.from_dict(track_data))
                    self.consequence_tracks = consequence_tracks
            elif key == "aspects":
                # Handle aspects - convert dict format to Aspect objects
                if not self.aspects:
                    aspects = []
                    for aspect_data in value:
                        if isinstance(aspect_data, dict):
                            aspects.append(Aspect.from_dict(aspect_data))
                        else:
                            # Assume it's already an Aspect object
                            aspects.append(aspect_data)
                    self.aspects = aspects
            else:
                # Use property setters for all other fields
                current_value = getattr(self, key, None)
                if current_value in (None, [], {}, 0, False):
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
