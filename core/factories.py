from typing import List
from core import initiative_types, initiative_views, scene_views
from core.base_models import BaseInitiative, EntityType
from rpg_systems.fate import fate_character, fate_extra, fate_roll_formula, fate_roll_views, fate_scene_views, fate_sheet_edit_views
from rpg_systems.mgt2e import mgt2e_character, mgt2e_roll_formula, mgt2e_roll_views, mgt2e_scene_views, mgt2e_sheet_edit_views
from core import generic_entities

def get_specific_character(system: str, entity_type: EntityType = None):
    # If entity_type is COMPANION, use companion-specific views
    if entity_type == EntityType.COMPANION:
        return get_specific_companion(system)
    
    if system == "fate":
        return fate_character.FateCharacter
    elif system == "mgt2e":
        return mgt2e_character.MGT2ECharacter
    elif system == "generic":
        return generic_entities.GenericCharacter
    else:
        raise ValueError(f"Unknown system: {system}")
    
def get_specific_companion(system: str):
    """Get the appropriate companion class based on system"""
    if system == "fate":
        # Use FateExtra for Fate companions
        from rpg_systems.fate import fate_extra
        return fate_extra.FateExtra
    else:
        # Fall back to generic companion for other systems
        return generic_entities.GenericCompanion

def get_specific_entity(system: str, entity_type: EntityType):
    """Get the appropriate entity class for the given system and entity type"""
    if system == "generic":
        if entity_type == EntityType.PC or entity_type == EntityType.NPC:
            return generic_entities.GenericCharacter
        elif entity_type == EntityType.COMPANION:
            return generic_entities.GenericCompanion
        else:
            return generic_entities.GenericEntity
    elif system == "fate":
        if entity_type == EntityType.PC or entity_type == EntityType.NPC:
            return fate_character.FateCharacter
        else:
            return fate_extra.FateExtra
    elif system == "mgt2e":
        if entity_type == EntityType.PC or entity_type == EntityType.NPC:
            return mgt2e_character.MGT2ECharacter
        elif entity_type == EntityType.COMPANION:
            return generic_entities.GenericCompanion
        elif entity_type == EntityType.GENERIC or entity_type == EntityType.ITEM:
            return generic_entities.GenericEntity
        else:
            raise ValueError(f"Unknown entity type '{entity_type}' for MGT2E system")
    else:
        raise ValueError(f"Unknown system: {system}")

def get_system_entity_types(system: str) -> List[EntityType]:
    """Get the available entity types for the given system"""
    if system == "fate":
        return [
            EntityType.FATE_EXTRA
        ]
    elif system == "mgt2e":
        return [
            EntityType.GENERIC,
            EntityType.ITEM,
            EntityType.COMPANION
        ]
    else:
        return [
        EntityType.GENERIC,
        EntityType.ITEM,
        EntityType.COMPANION
    ]

def get_specific_initiative(initiative_type: str):
    if initiative_type == "popcorn":
        return initiative_types.PopcornInitiative
    elif initiative_type == "generic":
        return initiative_types.GenericInitiative
    else:
        raise ValueError(f"Unknown initiative type: {initiative_type}")

def get_specific_initiative_view(guild_id: str, channel_id: str, initiative: BaseInitiative, message_id=None):
    if initiative.type == "popcorn":
        return initiative_views.PopcornInitiativeView(
            guild_id=guild_id, 
            channel_id=channel_id, 
            initiative=initiative,
            message_id=message_id
        )
    elif initiative.type == "generic":
        return initiative_views.GenericInitiativeView(
            guild_id=guild_id, 
            channel_id=channel_id, 
            initiative=initiative,
            message_id=message_id
        )
    else:
        raise ValueError(f"Unknown initiative type: {initiative.type}")

def get_specific_roll_formula(system: str, roll_parameters_dict: dict = None):
    if system == "fate":
        return fate_roll_formula.FateRollFormula(roll_parameters_dict)
    elif system == "mgt2e":
        return mgt2e_roll_formula.MGT2ERollFormula(roll_parameters_dict)
    elif system == "generic":
        return generic_entities.GenericRollFormula(roll_parameters_dict)
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_roll_formula_view(system: str, roll_formula_obj, difficulty: int = None):
    if system == "fate":
        return fate_roll_views.FateRollFormulaView(roll_formula_obj, difficulty)
    elif system == "mgt2e":
        return mgt2e_roll_views.MGT2ERollFormulaView(roll_formula_obj, difficulty)
    elif system == "generic":
        return generic_entities.GenericRollFormulaView(roll_formula_obj, difficulty)
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_scene_view(system, guild_id=None, channel_id=None, scene_id=None, message_id=None):
    """Get the appropriate scene view for the given system"""
    if system == "fate":
        return fate_scene_views.FateSceneView(guild_id, channel_id, scene_id, message_id)
    elif system == "mgt2e":
        return mgt2e_scene_views.MGT2ESceneView(guild_id, channel_id, scene_id, message_id)
    else:
        return scene_views.GenericSceneView(guild_id, channel_id, scene_id, message_id)