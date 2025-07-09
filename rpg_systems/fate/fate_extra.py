from typing import Any, Dict, List
import discord
from core.base_models import EntityDefaults, EntityType
from rpg_systems.fate.fate_character import FateCharacter


class FateExtra(FateCharacter):
    """
    A Fate Extra - can represent any entity type in the Fate system.
    This includes items, locations, organizations, vehicles, or any other
    entity that might have aspects, skills, or stress tracks.
    """
    SUPPORTED_ENTITY_TYPES: List[EntityType] = [
        EntityType.GENERIC,
        EntityType.ITEM,
        EntityType.COMPANION
    ]
    
    # Define defaults for all entity types
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.GENERIC: {
            "refresh": 0,
            "fate_points": 0,
            "skills": {},
            "aspects": [],
            "stress_tracks": [],
            "consequence_tracks": [],
            "stunts": {}
        },
        EntityType.ITEM: {
            "refresh": 0,
            "fate_points": 0,
            "skills": {},
            "aspects": [],
            "stress_tracks": [],
            "consequence_tracks": [],
            "stunts": {}
        },
        EntityType.COMPANION: {
            "refresh": 0,
            "fate_points": 0,
            "skills": {},
            "aspects": [],
            "stress_tracks": [],
            "consequence_tracks": [],
            "stunts": {}
        }
    })

    DEFAULT_SKILLS = {}
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FateExtra":
        """Create a FateExtra from a dictionary"""
        return cls(data)
    
    def apply_defaults(self, entity_type: EntityType, guild_id=None):
        """Apply defaults for the Fate Extra entity type"""
        super().apply_defaults(entity_type, guild_id)
        
        # Ensure skills are empty by default for extras
        self.skills = self.DEFAULT_SKILLS.copy()
    
    def get_sheet_edit_view(self, editor_id: int, is_gm: bool) -> discord.ui.View:
        # For most entity types, use the full Fate sheet view
        from rpg_systems.fate.fate_sheet_edit_views import FateSheetEditView
        return FateSheetEditView(editor_id=editor_id, char_id=self.id)

    def format_full_sheet(self, guild_id: int, is_gm: bool = False) -> discord.Embed:
        """Format the extra's sheet - use parent implementation but adjust title"""
        return self.get_sheet_embed(guild_id, display_all=False, is_gm=is_gm)

    def format_npc_scene_entry(self, is_gm: bool) -> str:
        """Format extra entry for scene display"""
        embed = super().format_npc_scene_entry(is_gm)

        return embed