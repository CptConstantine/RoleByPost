from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid
from core.base_models import AccessType, EntityType, SystemType, BaseEntity

if TYPE_CHECKING:
    from core.base_models import BaseInitiative

def build_entity(
    system: SystemType,
    entity_type: EntityType,
    name: str,
    owner_id: str,
    guild_id: Optional[str] = None,
    notes: Optional[list] = None,
    avatar_url: Optional[str] = None,
    access_type: AccessType = AccessType.PUBLIC,
    system_specific_fields: Optional[Dict[str, Any]] = None
) -> "BaseEntity":
    """
    Factory method to create any entity with the given parameters.
    
    Args:
        system: The RPG system
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
    
    # Build the entity dictionary
    entity_dict = BaseEntity.build_entity_dict(
        id=entity_id,
        name=name,
        owner_id=owner_id,
        system=system,
        entity_type=entity_type,
        notes=notes,
        avatar_url=avatar_url,
        access_type=access_type,
        system_specific_fields=system_specific_fields
    )
    
    # Get the system-specific entity class
    EntityClass = get_specific_entity(system, entity_type)
    
    # Create and apply defaults
    entity = EntityClass.from_dict(entity_dict)
    entity.apply_defaults(entity_type, guild_id)
    
    return entity

def build_and_save_entity(
    system: SystemType,
    entity_type: EntityType,
    name: str,
    owner_id: str,
    guild_id: str,
    notes: Optional[list] = None,
    avatar_url: Optional[str] = None,
    access_type: AccessType = AccessType.PUBLIC,
    system_specific_fields: Optional[Dict[str, Any]] = None
) -> "BaseEntity":
    """
    Factory method to create and save any entity with the given parameters.
    
    Args:
        system: The RPG system
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
        access_type=access_type,
        system_specific_fields=system_specific_fields
    )
    
    # Save the entity
    repositories.entity.upsert_entity(guild_id, entity, system=system)
    
    return entity

def get_specific_character(system: SystemType, entity_type: EntityType = None):
    # If entity_type is COMPANION, use companion-specific views
    from rpg_systems.fate import fate_character
    from rpg_systems.mgt2e import mgt2e_character
    from core import generic_entities

    if entity_type == EntityType.COMPANION:
        return get_specific_companion(system)

    if system == SystemType.FATE:
        return fate_character.FateCharacter
    elif system == SystemType.MGT2E:
        return mgt2e_character.MGT2ECharacter
    elif system == SystemType.GENERIC:
        return generic_entities.GenericCharacter
    else:
        raise ValueError(f"Unknown system: {system}")
    
def get_specific_companion(system: SystemType):
    """Get the appropriate companion class based on system"""
    from rpg_systems.fate import fate_extra
    from core import generic_entities

    if system == SystemType.FATE:
        return fate_extra.FateExtra
    else:
        return generic_entities.GenericCompanion

def get_specific_entity(system: SystemType, entity_type: EntityType):
    """Get the appropriate entity class for the given system and entity type"""
    from rpg_systems.fate import fate_character, fate_extra
    from rpg_systems.mgt2e import mgt2e_character
    from core import generic_entities

    if system == SystemType.GENERIC:
        if entity_type == EntityType.PC or entity_type == EntityType.NPC:
            return generic_entities.GenericCharacter
        elif entity_type == EntityType.COMPANION:
            return generic_entities.GenericCompanion
        elif entity_type == EntityType.CONTAINER:
            return generic_entities.GenericContainer
        else:
            return generic_entities.GenericEntity
    elif system == SystemType.FATE:
        if entity_type == EntityType.PC or entity_type == EntityType.NPC:
            return fate_character.FateCharacter
        elif entity_type == EntityType.CONTAINER:
            return generic_entities.GenericContainer
        else:
            return fate_extra.FateExtra
    elif system == SystemType.MGT2E:
        if entity_type == EntityType.PC or entity_type == EntityType.NPC:
            return mgt2e_character.MGT2ECharacter
        elif entity_type == EntityType.COMPANION:
            return generic_entities.GenericCompanion
        elif entity_type == EntityType.OTHER or entity_type == EntityType.ITEM:
            return generic_entities.GenericEntity
        elif entity_type == EntityType.CONTAINER:
            return generic_entities.GenericContainer
        else:
            raise ValueError(f"Unknown entity type '{entity_type}' for MGT2E system")
    else:
        raise ValueError(f"Unknown system: {system}")

def get_system_entity_types(system: SystemType) -> List[EntityType]:
    """Get the available entity types for the given system"""
    if system == SystemType.FATE:
        return [
            EntityType.OTHER,
            EntityType.ITEM,
            EntityType.COMPANION,
            EntityType.CONTAINER
        ]
    elif system == SystemType.MGT2E:
        return [
            EntityType.OTHER,
            EntityType.ITEM,
            EntityType.COMPANION,
            EntityType.CONTAINER
        ]
    else:
        return [
        EntityType.OTHER,
        EntityType.ITEM,
        EntityType.COMPANION,
        EntityType.CONTAINER
    ]

def get_specific_initiative(initiative_type: str):
    """Get the appropriate initiative class based on type"""
    from core import initiative_types
    if initiative_type == "popcorn":
        return initiative_types.PopcornInitiative
    elif initiative_type == "generic":
        return initiative_types.GenericInitiative
    else:
        raise ValueError(f"Unknown initiative type: {initiative_type}")

def get_specific_initiative_view(guild_id: str, channel_id: str, initiative: "BaseInitiative", message_id=None):
    """Get the appropriate initiative view for the given initiative type"""
    from core import initiative_views
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

def get_specific_roll_formula(system: SystemType, roll_parameters_dict: dict = None):
    """Get the appropriate roll formula class for the given system"""
    from rpg_systems.fate import fate_roll_formula
    from rpg_systems.mgt2e import mgt2e_roll_formula
    from core import generic_entities

    if system == SystemType.FATE:
        return fate_roll_formula.FateRollFormula(roll_parameters_dict)
    elif system == SystemType.MGT2E:
        return mgt2e_roll_formula.MGT2ERollFormula(roll_parameters_dict)
    elif system == SystemType.GENERIC:
        return generic_entities.GenericRollFormula(roll_parameters_dict)
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_roll_formula_view(system: SystemType, roll_formula_obj, difficulty: int = None):
    """Get the appropriate roll formula view for the given system"""
    from rpg_systems.fate import fate_roll_views
    from rpg_systems.mgt2e import mgt2e_roll_views
    from core import generic_entities

    if system == SystemType.FATE:
        return fate_roll_views.FateRollFormulaView(roll_formula_obj, difficulty)
    elif system == SystemType.MGT2E:
        return mgt2e_roll_views.MGT2ERollFormulaView(roll_formula_obj, difficulty)
    elif system == SystemType.GENERIC:
        return generic_entities.GenericRollFormulaView(roll_formula_obj, difficulty)
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_scene_view(system: SystemType, guild_id=None, channel_id=None, scene_id=None, message_id=None):
    """Get the appropriate scene view for the given system"""
    from rpg_systems.fate import fate_scene_views
    from rpg_systems.mgt2e import mgt2e_scene_views
    from core import scene_views
    
    if system == SystemType.FATE:
        return fate_scene_views.FateSceneView(guild_id, channel_id, scene_id, message_id)
    elif system == SystemType.MGT2E:
        return mgt2e_scene_views.MGT2ESceneView(guild_id, channel_id, scene_id, message_id)
    else:
        return scene_views.GenericSceneView(guild_id, channel_id, scene_id, message_id)