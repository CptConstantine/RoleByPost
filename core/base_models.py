from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
import json
from typing import Any, ClassVar, Dict, List, Optional
import discord
import discord.ui as ui
from core.roll_formula import RollFormula
from data.models import Relationship

@dataclass
class AccessLevel:
    """Container access control configuration"""
    access_type: str  # 'public', 'gm_only', 'specific_users'
    allowed_user_ids: List[str] = None
    
    def __post_init__(self):
        if self.allowed_user_ids is None:
            self.allowed_user_ids = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "access_type": self.access_type,
            "allowed_user_ids": self.allowed_user_ids
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessLevel":
        """Create from dictionary"""
        return cls(
            access_type=data.get("access_type", "public"),
            allowed_user_ids=data.get("allowed_user_ids", [])
        )
    
    def can_access(self, user_id: str, is_gm: bool = False) -> bool:
        """Check if a user can access the container"""
        if self.access_type == "public":
            return True
        elif self.access_type == "gm_only":
            return is_gm
        elif self.access_type == "specific_users":
            return is_gm or str(user_id) in self.allowed_user_ids
        
        return False
    
    def add_user(self, user_id: str) -> None:
        """Add a user to the allowed list"""
        user_id = str(user_id)
        if user_id not in self.allowed_user_ids:
            self.allowed_user_ids.append(user_id)
    
    def remove_user(self, user_id: str) -> bool:
        """Remove a user from the allowed list. Returns True if user was removed."""
        user_id = str(user_id)
        if user_id in self.allowed_user_ids:
            self.allowed_user_ids.remove(user_id)
            return True
        return False

class BaseRpgObj(ABC):
    """
    Abstract base class for a "thing".
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        # Ensure access_control exists for all entities
        self._ensure_access_control()

    def _ensure_access_control(self):
        """Ensure access_control field exists with proper defaults"""
        if "access_control" not in self.data:
            self.data["access_control"] = {
                "access_type": "specific_users",
                "allowed_user_ids": []
            }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseRpgObj":
        """Deserialize an entity from a dict."""
        return cls(data)

    @property
    def id(self) -> str:
        return self.data.get("id")

    @id.setter
    def id(self, value: str):
        self.data["id"] = value

    @property
    def owner_id(self) -> Optional[str]:
        """Primary owner - maintains existing behavior for simple ownership checks"""
        return self.data.get("owner_id")

    @owner_id.setter
    def owner_id(self, value: str):
        """Set the primary owner - maintains existing behavior"""
        self.data["owner_id"] = value

    @property
    def access_control(self) -> AccessLevel:
        """Get additional access control configuration"""
        # Ensure field exists
        self._ensure_access_control()
        access_data = self.data.get("access_control", {"access_type": "specific_users", "allowed_user_ids": []})
        return AccessLevel.from_dict(access_data)

    @access_control.setter
    def access_control(self, value: AccessLevel):
        """Set additional access control configuration"""
        self.data["access_control"] = value.to_dict()

    def can_access(self, user_id: str, is_gm: bool = False) -> bool:
        """
        Hybrid access checking: combines owner_id with access_control
        
        Args:
            user_id: Discord user ID to check
            is_gm: Whether the user has GM permissions
            
        Returns:
            True if user can access this entity
        """
        user_id = str(user_id)
        
        # Primary owner always has access (maintains existing behavior)
        if self.owner_id == user_id:
            return True
        
        # GMs always have access
        if is_gm:
            return True
        
        # Check additional access control rules
        return self.access_control.can_access(user_id, is_gm)

    def add_allowed_user(self, user_id: str) -> None:
        """Add a user to the additional access list (beyond primary owner)"""
        access_control = self.access_control
        access_control.add_user(user_id)
        self.access_control = access_control

    def remove_allowed_user(self, user_id: str) -> bool:
        """Remove a user from the additional access list"""
        access_control = self.access_control
        result = access_control.remove_user(user_id)
        self.access_control = access_control
        return result

    def set_access_type(self, access_type: str) -> None:
        """Set the access type for additional access control"""
        valid_types = ["public", "gm_only", "specific_users"]
        if access_type not in valid_types:
            raise ValueError(f"Invalid access type. Must be one of: {valid_types}")
        
        access_control = self.access_control
        access_control.access_type = access_type
        self.access_control = access_control

    def get_all_allowed_users(self) -> List[str]:
        """Get all users who can access this entity (owner + additional users)"""
        allowed_users = []
        
        # Add primary owner
        if self.owner_id:
            allowed_users.append(self.owner_id)
        
        # Add additional users from access control
        access_control = self.access_control
        if access_control.access_type == "specific_users":
            for user_id in access_control.allowed_user_ids:
                if user_id not in allowed_users:
                    allowed_users.append(user_id)
        
        return allowed_users

    def is_owned_by(self, user_id: str) -> bool:
        """Check if user is the primary owner (for strict ownership checks)"""
        return self.owner_id == str(user_id)

    @property
    def system(self) -> str:
        return self.data.get("system")

    @system.setter
    def system(self, value: str):
        self.data["system"] = value

    @property
    def notes(self) -> list:
        return self.data.get("notes", [])

    @notes.setter
    def notes(self, value: list):
        self.data["notes"] = value

@dataclass
class InitiativeParticipant:
    id: str
    name: str
    owner_id: str
    is_npc: bool

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return InitiativeParticipant(**data)
    
class BaseInitiative(ABC):
    """
    Abstract base class for initiative.
    System-specific initiative classes should inherit from this and implement all methods.
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseInitiative":
        """Deserialize an entity from a dict."""
        return cls(data)
    
    def to_dict(self):
        data = self.data.copy()
        data["participants"] = [p.to_dict() if isinstance(p, InitiativeParticipant) else p for p in self.participants]
        return data

    @property
    def type(self) -> str:
        return self.data.get("type")

    @type.setter
    def type(self, value: str):
        self.data["type"] = value

    @property
    def remaining_in_round(self) -> list:
        return self.data.get("remaining_in_round", [])

    @remaining_in_round.setter
    def remaining_in_round(self, value: list):
        self.data["remaining_in_round"] = value

    @property
    def round_number(self) -> int:
        # Pythonic: default to 1 if not set
        return self.data.get("round_number", 1)

    @round_number.setter
    def round_number(self, value: int):
        self.data["round_number"] = value

    @property
    def participants(self):
        # Always return as dataclasses
        return [InitiativeParticipant.from_dict(p) if isinstance(p, dict) else p for p in self.data["participants"]]

    @participants.setter
    def participants(self, value):
        # Accepts a list of InitiativeParticipant or dicts
        self.data["participants"] = [p.to_dict() if isinstance(p, InitiativeParticipant) else p for p in value]

    def add_participant(self, participant: InitiativeParticipant):
        """
        Add a participant to the initiative.
        If the participant already exists, it will not be added again.
        """
        if not any(p.id == participant.id for p in self.participants):
            self.participants.append(participant)

    def remove_participant(self, participant_id: str):
        """
        Remove a participant by their ID.
        If the participant does not exist, nothing happens.
        """
        self.participants = [p for p in self.participants if p.id != participant_id]

    def get_participant_name(self, user_id):
        for p in self.participants:
            if p.id == user_id:
                return p.name
        return "Unknown"

class EntityJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'to_dict'):
            return obj.to_dict()
        return super().default(obj)

class EntityType(Enum):
    """Standard entity types across all systems"""
    GENERIC = "generic"
    PC = "pc"
    NPC = "npc"
    COMPANION = "companion"  # A character that is not a PC but is controlled by a player
    ITEM = "item"  # Generic item, can be used in inventory
    CONTAINER = "container"  # A container that can hold items, like a backpack or chest or any loot container
    
    def __str__(self):
        return self.value
    
    @staticmethod
    def get_type_from_str(entity_type_str: str) -> 'EntityType':
        """Get the EntityType enum member from a string."""
        try:
            return EntityType(entity_type_str.lower())
        except ValueError:
            raise ValueError(f"Unknown entity type: {entity_type_str}")
    
class RelationshipType(Enum):
    """Types of relationships between entities"""
    POSSESSES = "possesses" # For Inventory
    CONTROLS = "controls"   # Can speak as this entity
    
    def __str__(self):
        return self.value
    
    @staticmethod
    def get_all_dict() -> Dict[str, 'RelationshipType']:
        return {name: member for name, member in RelationshipType.__members__.items()}
    
    @staticmethod
    def get_relationships_str(guild_id: str, entity: 'BaseEntity') -> List[str]:
        """Get a list of relationship strings for the entity."""
        relationships_dict = RelationshipType.get_relationships_dict(guild_id, entity)
        return [f"{key}: {value}" for key, value in relationships_dict.items()]

    @staticmethod
    def get_relationships_dict(guild_id: str, entity: 'BaseEntity') -> Dict[str, str]:
        """Get a dictionary of relationship types and their string representations."""
        from data.repositories.repository_factory import repositories
        relationships_dict = {}
        
        # Entities this entity owns
        possessed_entities = repositories.relationship.get_children(
            guild_id, 
            entity.id, 
            RelationshipType.POSSESSES.value
        )
        if possessed_entities:
            possessed_names = [e.name for e in possessed_entities[:5]]  # Show first 5
            possessed_text = ", ".join(possessed_names)
            if len(possessed_entities) > 5:
                possessed_text += f" (+{len(possessed_entities) - 5} more)"
            relationships_dict[f"📦 Possesses ({len(possessed_entities)})"] = possessed_text
        
        # Entities that own this entity
        possessors = repositories.relationship.get_parents(
            guild_id,
            entity.id, 
            RelationshipType.POSSESSES.value
        )
        if possessors:
            possessor_names = [e.name for e in possessors]
            relationships_dict["📦 Possessed By"] = ", ".join(possessor_names)

        # Control relationships
        controlled_entities = repositories.relationship.get_children(
            guild_id, 
            entity.id, 
            RelationshipType.CONTROLS.value
        )
        if controlled_entities:
            controlled_names = [e.name for e in controlled_entities]
            relationships_dict["🎮 Controls"] = ", ".join(controlled_names)
        
        controllers = repositories.relationship.get_parents(
            guild_id, 
            entity.id, 
            RelationshipType.CONTROLS.value
        )
        if controllers:
            controller_names = [e.name for e in controllers]
            relationships_dict["🎮 Controlled By"] = ", ".join(controller_names)
        
        # Get all other relationships
        all_relationships = repositories.relationship.get_relationships_for_entity(
            guild_id, 
            entity.id
        )
        
        # Filter out POSSESSES and CONTROLS relationships (already shown above)
        other_relationships = [
            rel for rel in all_relationships 
            if rel.relationship_type not in [RelationshipType.POSSESSES.value, RelationshipType.CONTROLS.value]
        ]
        
        if other_relationships:
            rel_lines = []
            for rel in other_relationships[:3]:  # Show first 3 other relationships
                if rel.from_entity_id == entity.id:
                    # This entity has a relationship TO another entity
                    target_entity = repositories.entity.get_by_id(rel.to_entity_id)
                    if target_entity:
                        rel_name = rel.relationship_type.replace("_", " ").title()
                        rel_lines.append(f"• {rel_name} **{target_entity.name}**")
                else:
                    # Another entity has a relationship TO this entity
                    source_entity = repositories.entity.get_by_id(rel.from_entity_id)
                    if source_entity:
                        rel_name = rel.relationship_type.replace("_", " ").title()
                        rel_lines.append(f"• **{source_entity.name}** {rel_name.lower()} this entity")
            
            if rel_lines:
                rel_text = "\n".join(rel_lines)
                if len(other_relationships) > 3:
                    rel_text += f"\n(+{len(other_relationships) - 3} more relationships)"
                relationships_dict["🔗 Other Relationships"] = rel_text
        
        return relationships_dict

@dataclass
class EntityDefaults:
    """Configuration for entity defaults by type"""
    defaults_by_type: Dict[EntityType, Dict[str, Any]]
    
    def get_defaults(self, entity_type: EntityType) -> Dict[str, Any]:
        return self.defaults_by_type.get(entity_type, {})

class BaseEntity(BaseRpgObj):
    """
    Abstract base class for a "thing".
    """
    # Override in subclasses
    ENTITY_DEFAULTS: ClassVar[Optional[EntityDefaults]] = None
    SUPPORTED_ENTITY_TYPES: ClassVar[List[EntityType]] = [EntityType.GENERIC]

    def __init__(self, data: Dict[str, Any]):
        self.data = data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaseRpgObj":
        """Deserialize an entity from a dict."""
        return cls(data)

    @property
    def entity_type(self) -> EntityType:
        entity_type_str = self.data.get("entity_type", "generic")
        return EntityType(entity_type_str)

    @entity_type.setter
    def entity_type(self, value: EntityType):
        self.data["entity_type"] = value.value

    @property
    def name(self) -> str:
        return self.data.get("name")

    @name.setter
    def name(self, value: str):
        self.data["name"] = value
    
    @property
    def avatar_url(self):
        return self.data.get("avatar_url", '')
    
    @avatar_url.setter
    def avatar_url(self, url):
        self.data["avatar_url"] = url
    
    def get_sheet_edit_view(self, editor_id: int) -> ui.View:
        """Get the appropriate sheet edit view for this entity type"""
        raise NotImplementedError("Subclasses must implement get_sheet_edit_view")

    def format_full_sheet(self, guild_id: int) -> discord.Embed:
        """Return a Discord Embed representing the full entity sheet. Override in subclasses."""
        embed = discord.Embed(
            title=f"{self.name or 'Entity'}",
            color=discord.Color.greyple()
        )
        notes = self.notes
        if notes:
            notes_display = "\n".join(notes) if notes else "_No notes_"
            embed.add_field(name="Notes", value=notes_display, inline=False)
        return embed

    def apply_defaults(self, entity_type: EntityType = None, guild_id: str = None):
        """Apply system-specific default fields to an entity."""
        if entity_type is None:
            entity_type = self.entity_type
    
    def _apply_default_field(self, key: str, value: Any, guild_id: str = None):
        """Apply a single default field. Override in subclasses for custom logic."""
        current_value = getattr(self, key, None)
        if current_value in (None, [], {}, 0, False):
            setattr(self, key, value)

    @staticmethod
    def build_entity_dict(
        id: str, 
        name: str, 
        owner_id: str, 
        system: str,
        entity_type: EntityType,
        notes: List[str] = None, 
        avatar_url: str = None, 
        system_specific_fields: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Helper method to create a standardized entity dictionary."""
        entity = {
            "id": id,
            "name": name,
            "owner_id": owner_id,
            "system": system,
            "entity_type": entity_type.value,
            "notes": notes or [],
            "avatar_url": avatar_url or '',
            "access_control": {
                "access_type": "specific_users",
                "allowed_user_ids": [owner_id]
            }
        }
        
        # Add system-specific fields
        if system_specific_fields:
            for key, value in system_specific_fields.items():
                entity[key] = value
        
        return entity

    def get_children(self, guild_id: str, relationship_type: RelationshipType = None) -> List['BaseEntity']:
        """Get entities this entity has relationships to"""
        from data.repositories.repository_factory import repositories
        return repositories.relationship.get_children(guild_id, self.id, relationship_type.value if relationship_type else None)

    def get_parents(self, guild_id: str, relationship_type: RelationshipType = None) -> List['BaseEntity']:
        """Get entities that have relationships to this entity"""
        from data.repositories.repository_factory import repositories
        return repositories.relationship.get_parents(guild_id, self.id, relationship_type.value if relationship_type else None)
    
    def get_possesser(self) -> Optional['BaseEntity']:
        """Get the entity that owns this entity (if any)"""
        owners = self.get_parents(RelationshipType.POSSESSES.value)
        return owners[0] if owners else None
    
    def get_controlled_entities(self) -> List['BaseEntity']:
        """Get entities that this entity controls"""
        return self.get_children(RelationshipType.CONTROLS.value)
    
    def can_be_controlled_by(self, user_id: str) -> bool:
        """Check if a user can control this entity"""
        # User can control their own entities
        if self.owner_id == str(user_id):
            return True
        
        # Check if user owns any entities that control this entity
        controlling_entities = self.get_parents(RelationshipType.CONTROLS.value)
        for entity in controlling_entities:
            if entity.owner_id == str(user_id):
                return True
        
        return False

    def add_relationship(self, guild_id: str, target_entity: 'BaseEntity', relationship_type: RelationshipType, metadata: Dict[str, Any] = None) -> 'Relationship':
        """Add a relationship to another entity"""
        from data.repositories.repository_factory import repositories
        return repositories.relationship.create_relationship(
            guild_id, 
            self.id, 
            target_entity.id, 
            relationship_type.value, 
            metadata
        )

    def remove_relationship(self, guild_id: str, target_entity: 'BaseEntity', relationship_type: RelationshipType = None) -> bool:
        """Remove a relationship to another entity"""
        from data.repositories.repository_factory import repositories
        return repositories.relationship.delete_relationships_by_entities(
            guild_id, 
            self.id, 
            target_entity.id, 
            relationship_type.value if relationship_type else None
        )
    
    def get_inventory(self, guild_id: str) -> List['BaseEntity']:
        """Get all items in this entity's inventory"""
        possessed_entities = self.get_children(guild_id, RelationshipType.POSSESSES)
        return [entity for entity in possessed_entities if entity.entity_type == EntityType.ITEM]
    
    def add_to_inventory(self, guild_id: str, item: 'BaseEntity') -> 'Relationship':
        """Add an item to this entity's inventory"""
        if item.entity_type != EntityType.ITEM:
            raise ValueError("Only ITEM entities can be added to inventory")
        return self.add_relationship(guild_id, item, RelationshipType.POSSESSES)
    
    def remove_from_inventory(self, guild_id: str, item: 'BaseEntity') -> bool:
        """Remove an item from this entity's inventory"""
        if item.entity_type != EntityType.ITEM:
            raise ValueError("Only ITEM entities can be removed from inventory")
        return self.remove_relationship(guild_id, item, RelationshipType.POSSESSES)

class BaseCharacter(BaseEntity):
    """
    Abstract base class for a character (PC or NPC).
    System-specific character classes should inherit from this and implement all methods.
    """
    SUPPORTED_ENTITY_TYPES: ClassVar[List[EntityType]] = [EntityType.PC, EntityType.NPC]

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @property
    def is_npc(self) -> bool:
        return self.data.get("entity_type") == "npc"

    @is_npc.setter
    def is_npc(self, value: bool):
        self.data["entity_type"] = "npc" if value else "pc"

    def format_npc_scene_entry(self, is_gm: bool) -> str:
        """Return a string for displaying this character in a scene summary. Override in subclasses."""
        lines = [f"**{self.name or 'NPC'}**"]
        if is_gm and self.notes:
            notes_display = "\n".join(self.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)

    @abstractmethod
    async def edit_requested_roll(self, interaction: discord.Interaction, roll_parameters: dict, difficulty: int = None):
        """
        Abstract method to handle a roll request for this character.
        Should return a discord.ui.View or send a message with the result.
        """
        pass

    @abstractmethod
    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollFormula, difficulty: int = None):
        """
        Abstract method to handle a roll request for this character.
        Should return a discord.ui.View or send a message with the result.
        """
        pass