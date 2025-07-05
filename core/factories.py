from typing import List
from core import initiative_types, initiative_views, scene_views
from core.models import BaseInitiative, EntityType, GenericCompanion, GenericCompanionSheetEditView, GenericEntity
from rpg_systems.fate import fate_character, fate_roll_modifiers, fate_roll_views, fate_scene_views, fate_sheet_edit_views
from rpg_systems.mgt2e import mgt2e_character, mgt2e_roll_modifiers, mgt2e_roll_views, mgt2e_scene_views, mgt2e_sheet_edit_views
from rpg_systems.generic import generic_character

def get_specific_character(system: str, entity_type: EntityType = None):
    # If entity_type is COMPANION, use companion-specific views
    if entity_type == EntityType.COMPANION:
        return get_specific_companion(system)
    
    if system == "fate":
        return fate_character.FateCharacter
    elif system == "mgt2e":
        return mgt2e_character.MGT2ECharacter
    elif system == "generic":
        return generic_character.GenericCharacter
    else:
        raise ValueError(f"Unknown system: {system}")
    
def get_specific_companion(system: str):
    """Get the appropriate companion class based on system"""
    # For now, only GenericCompanion is implemented
    return GenericCompanion

def get_specific_sheet_view(system: str, editor_id: str, char_id: str, entity_type: EntityType = None):
    """Get the appropriate sheet view based on system and entity type"""
    
    # If entity_type is COMPANION, use companion-specific views
    if entity_type == EntityType.COMPANION:
        return get_specific_companion_sheet_view(system, editor_id, char_id)
    
    # Original logic for PCs/NPCs
    if system == "fate":
        return fate_sheet_edit_views.FateSheetEditView(editor_id=editor_id, char_id=char_id)
    elif system == "mgt2e":
        return mgt2e_sheet_edit_views.MGT2ESheetEditView(editor_id=editor_id, char_id=char_id)
    elif system == "generic":
        return generic_character.GenericSheetEditView(editor_id=editor_id, char_id=char_id)
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_companion_sheet_view(system: str, editor_id: str, char_id: str):
    """Get companion sheet view for system, falling back to generic"""
    # Just Generic for now until system-specific implementations
    return GenericCompanionSheetEditView(editor_id=editor_id, char_id=char_id)

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
        return fate_roll_modifiers.FateRollModifiers(roll_parameters_dict)
    elif system == "mgt2e":
        return mgt2e_roll_modifiers.MGT2ERollModifiers(roll_parameters_dict)
    elif system == "generic":
        return generic_character.GenericRollModifiers(roll_parameters_dict)
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_roll_formula_view(system: str, roll_formula_obj, difficulty: int = None):
    if system == "fate":
        return fate_roll_views.FateRollModifiersView(roll_formula_obj, difficulty)
    elif system == "mgt2e":
        return mgt2e_roll_views.MGT2ERollModifiersView(roll_formula_obj, difficulty)
    elif system == "generic":
        return generic_character.GenericRollModifiersView(roll_formula_obj, difficulty)
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

def get_specific_entity(system: str, entity_type: str):
    """Get the appropriate entity class for the given system and entity type"""
    if system == "generic":
        # Generic system only supports generic entities
        return GenericEntity
    elif system == "fate":
        if entity_type == "generic":
            return GenericEntity
        elif entity_type == "pc" or entity_type == "npc":
            return fate_character.FateCharacter
        else:
            raise ValueError(f"Unknown entity type '{entity_type}' for Fate system")
    elif system == "mgt2e":
        if entity_type == "generic":
            return GenericEntity
        else:
            raise ValueError(f"Unknown entity type '{entity_type}' for MGT2E system")
    else:
        raise ValueError(f"Unknown system: {system}")

def get_system_entity_types(system: str) -> List[EntityType]:
    """Get the available entity types for the given system"""
    if system == "fate":
        return [EntityType.GENERIC, EntityType.PC, EntityType.NPC, EntityType.COMPANION]
    elif system == "mgt2e":
        return [EntityType.GENERIC, EntityType.PC, EntityType.NPC, EntityType.COMPANION]
    else:
        return [EntityType.GENERIC, EntityType.PC, EntityType.NPC, EntityType.COMPANION]
    
def get_specific_companion(system: str):
    """Get companion class for system, falling back to generic"""
    # Check if system has a specific companion class
    # Only GenericCompanion for now until system-specific companions are implemented
    return GenericCompanion