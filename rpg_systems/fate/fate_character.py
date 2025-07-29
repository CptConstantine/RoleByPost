from typing import Any, Dict, List, Union
import discord
from core.base_models import BaseCharacter, EntityDefaults, EntityType, EntityLinkType, SystemType
from rpg_systems.fate.aspect import Aspect
from rpg_systems.fate.fate_roll_formula import FateRollFormula
from rpg_systems.fate.fate_roll_views import FateRollFormulaView
from rpg_systems.fate.stress_track import StressTrack, StressBox
from rpg_systems.fate.consequence_track import ConsequenceTrack, Consequence

SYSTEM = SystemType.FATE

class FateCharacter(BaseCharacter):
    SUPPORTED_ENTITY_TYPES: List[EntityType] = [
        EntityType.PC,
        EntityType.NPC
    ]

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
        super().apply_defaults(entity_type, guild_id)
        # Get the appropriate defaults based on entity type
        system_defaults = self.ENTITY_DEFAULTS.get_defaults(entity_type)
        
        for key, value in system_defaults.items():
            if key == "skills":
                # Use per-guild default if available
                skills = None
                if guild_id:
                    from data.repositories.repository_factory import repositories
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
    
    async def edit_requested_roll(self, interaction: discord.Interaction, roll_formula_obj: "FateRollFormula", difficulty: int = None):
        """
        Opens a view for editing the roll parameters, prepopulated with any requested skill.
        """
        view = FateRollFormulaView(self, roll_formula_obj, difficulty)
        
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
        
    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: "FateRollFormula", difficulty: int = None):
        """
        Prints the roll result
        """
        result, total = roll_formula_obj.roll_formula(self, roll_formula_obj.roll_config.dice_formula)

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
    
    def get_sheet_edit_view(self, editor_id: int, is_gm: bool) -> discord.ui.View:
        from rpg_systems.fate.fate_sheet_edit_views import FateSheetEditView
        return FateSheetEditView(editor_id=editor_id, char_id=self.id)

    def format_full_sheet(self, guild_id: int, is_gm: bool = False) -> discord.Embed:
        """Format the character sheet for Fate system"""
        return self.get_sheet_embed(guild_id, display_all=True, is_gm=is_gm)

    def get_sheet_embed(self, guild_id, display_all, is_gm=False):
        embed = discord.Embed(title=f"{self.name}", color=discord.Color.purple())

        # --- Aspects ---
        aspects = self.aspects
        if aspects:
            aspect_lines = []
            for aspect in aspects:
                aspect_lines.append(aspect.get_short_aspect_string(is_owner=True))

            embed.add_field(name="__Aspects__", value="\n".join(aspect_lines), inline=False)
        elif display_all:
            embed.add_field(name="__Aspects__", value="None", inline=False)

        # --- Skills ---
        # Only display skills > 0
        if self.skills:
            skills = {k: v for k, v in self.skills.items() if v > 0}
            if skills:
                sorted_skills = sorted(skills.items(), key=lambda x: -x[1])
                skill_lines = [f"**{k}**: +{v}" for k, v in sorted_skills]
                embed.add_field(name="__Skills__", value="\n".join(skill_lines), inline=False)
            elif display_all:
                embed.add_field(name="__Skills__", value="None", inline=False)

        # --- Stress Tracks ---
        stress_tracks = self.stress_tracks
        if stress_tracks:
            stress_lines = []
            for track in stress_tracks:
                # Format boxes with their values
                box_display = []
                for box in track.boxes:
                    if box.is_filled:
                        box_display.append(f"[☒{box.value}]")
                    else:
                        box_display.append(f"[☐{box.value}]")
                
                stress_line = f"**{track.track_name}**: {' '.join(box_display)}"
                stress_lines.append(stress_line)

            embed.add_field(name="__Stress__", value="\n".join(stress_lines), inline=False)
        elif display_all:
            embed.add_field(name="__Stress__", value="None", inline=False)

        # --- Consequences ---
        consequence_tracks = self.consequence_tracks
        if consequence_tracks:
            consequence_lines = []
            for track in consequence_tracks:
                if track.name:
                    consequence_lines.append(f"**{track.name}**:")
                for consequence in track.consequences:
                    if consequence.aspect:
                        consequence_lines.append(f"{consequence.name} ({consequence.severity}): {consequence.aspect.name}")
                    else:
                        consequence_lines.append(f"{consequence.name} ({consequence.severity}):")
            
            embed.add_field(name="__Consequences__", value="\n".join(consequence_lines), inline=False)
        elif display_all:
            embed.add_field(name="__Consequences__", value="None", inline=False)

        # --- Fate Points / Refresh ---
        fp = self.fate_points
        if self.refresh > 0:
            refresh = self.refresh
            embed.add_field(name="__Fate Points__", value=f"{fp}/{refresh}", inline=True)
        elif display_all:
            embed.add_field(name="__Fate Points__", value="0/0", inline=True)

        # --- Stunts ---
        stunts = self.stunts
        if stunts:
            stunt_lines = [f"• {stunt_name}" for stunt_name in stunts.keys()]
            embed.add_field(name="__Stunts__", value="\n".join(stunt_lines), inline=False)
        elif display_all:
            embed.add_field(name="__Stunts__", value="None", inline=False)

        # --- Inventory ---
        # Fate inventories are all extras instead of just items
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
        elif display_all:
            embed.add_field(name="__Inventory__", value="None", inline=False)

        # --- Notes ---
        notes = self.notes
        if notes:
            notes_display = "\n".join(notes)
            embed.add_field(name="__Notes__", value=notes_display, inline=False)
        elif display_all:
            embed.add_field(name="__Notes__", value="None", inline=False)

        return embed

    def format_npc_scene_entry(self, is_gm: bool) -> str:
        """Format NPC entry for scene display"""
        # Get the character's aspects
        aspect_lines = []
        for aspect in self.aspects:
            # Use the Aspect.get_short_aspect_string method for consistent formatting
            aspect_str = aspect.get_short_aspect_string(is_gm=is_gm)
            if aspect_str:  # Skip empty strings (hidden aspects for non-GMs)
                aspect_lines.append(aspect_str)
                
        aspect_str = ", ".join(aspect_lines) if aspect_lines else "_No aspects set_"
        lines = [f"**{self.name}** - {aspect_str}"]
        
        # Add stress and consequences for GM view
        if is_gm:
            # Show stress tracks if any boxes are filled
            stress_tracks = self.stress_tracks
            filled_tracks = []
            for track in stress_tracks:
                filled_boxes = [box for box in track.boxes if box.is_filled]
                if filled_boxes:
                    box_display = ' '.join(f"[☒{box.value}]" for box in filled_boxes)
                    filled_tracks.append(f"**{track.track_name}**: {box_display}")
            
            if filled_tracks:
                lines.append(f"**Stress:** {', '.join(filled_tracks)}")
            
            # Show filled consequences
            consequence_tracks = self.consequence_tracks
            filled_consequences = []
            for track in consequence_tracks:
                for consequence in track.consequences:
                    if consequence.aspect:
                        filled_consequences.append(f"{consequence.name}: {consequence.aspect.name}")
            
            if filled_consequences:
                cons_display = ', '.join(filled_consequences)
                lines.append(f"**Consequences:** {cons_display}")
        
        if is_gm and self.notes:
            notes_display = "\n".join(self.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        
        # Add stunts to NPC scene entry when viewed by GM
        if is_gm and self.stunts:
            stunt_names = list(self.stunts.keys())
            if stunt_names:
                lines.append(f"**Stunts:** {', '.join(stunt_names)}")
        
        return "\n".join(lines)

def get_character(char_id) -> FateCharacter:
    from data.repositories.repository_factory import repositories
    character = repositories.entity.get_by_id(str(char_id))
    return character if character else None
