from typing import Any, Dict, List, Optional
import uuid
from core import initiative_types, initiative_views, scene_views
from core.base_models import BaseEntity, BaseInitiative, EntityType
from rpg_systems.fate import fate_character, fate_extra, fate_roll_formula, fate_roll_views, fate_scene_views, fate_sheet_edit_views
from rpg_systems.mgt2e import mgt2e_character, mgt2e_roll_formula, mgt2e_roll_views, mgt2e_scene_views, mgt2e_sheet_edit_views
from core import generic_entities

def build_entity(
    system: str,
    entity_type: EntityType,
    name: str,
    owner_id: str,
    guild_id: Optional[str] = None,
    notes: Optional[list] = None,
    avatar_url: Optional[str] = None,
    system_specific_fields: Optional[Dict[str, Any]] = None
) -> BaseEntity:
    """
    Factory method to create any entity with the given parameters.
    
    Args:
        system: The RPG system ("fate", "mgt2e", "generic")
        entity_type: The type of entity to create
        name: Name of the entity
        owner_id: ID of the user who owns this entity
        guild_id: Optional guild ID for applying defaults
        notes: Optional list of notes
        avatar_url: Optional avatar URL
        system_specific_fields: Optional dict of system-specific field values
    
    Returns:
        BaseEntity: A fully configured entity instance ready for saving
    
    Raises:
        ValueError: If the system/entity_type combination is invalid
    """
    # Generate a unique ID
    entity_id = str(uuid.uuid4())
    
    # Get the appropriate entity class
    EntityClass = get_specific_entity(system, entity_type)
    
    # Build the entity dictionary
    entity_dict = BaseEntity.build_entity_dict(
        id=entity_id,
        name=name,
        owner_id=owner_id,
        entity_type=entity_type,
        notes=notes,
        avatar_url=avatar_url,
        system_specific_fields=system_specific_fields
    )
    
    # Create the entity instance
    entity = EntityClass(entity_dict)
    
    # Apply defaults if guild_id is provided
    if guild_id:
        entity.apply_defaults(entity_type, guild_id=guild_id)
    else:
        entity.apply_defaults(entity_type)
    
    return entity

def build_and_save_entity(
    system: str,
    entity_type: EntityType,
    name: str,
    owner_id: str,
    guild_id: str,
    notes: Optional[list] = None,
    avatar_url: Optional[str] = None,
    system_specific_fields: Optional[Dict[str, Any]] = None
) -> BaseEntity:
    """
    Factory method to create and save any entity with the given parameters.
    
    Args:
        system: The RPG system ("fate", "mgt2e", "generic")
        entity_type: The type of entity to create
        name: Name of the entity
        owner_id: ID of the user who owns this entity
        guild_id: Guild ID where the entity will be saved
        notes: Optional list of notes
        avatar_url: Optional avatar URL
        system_specific_fields: Optional dict of system-specific field values
    
    Returns:
        BaseEntity: A fully configured and saved entity instance
    
    Raises:
        ValueError: If the system/entity_type combination is invalid
    """
    from data.repositories.repository_factory import repositories
    
    # Create the entity
    entity = build_entity(
        system=system,
        entity_type=entity_type,
        name=name,
        owner_id=owner_id,
        guild_id=guild_id,
        notes=notes,
        avatar_url=avatar_url,
        system_specific_fields=system_specific_fields
    )
    
    # Save the entity
    repositories.entity.upsert_entity(guild_id, entity, system=system)
    
    return entity

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
        return fate_extra.FateExtra
    else:
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
            EntityType.GENERIC,
            EntityType.ITEM,
            EntityType.COMPANION
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