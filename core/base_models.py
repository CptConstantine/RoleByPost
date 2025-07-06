from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
import json
from typing import Any, ClassVar, Dict, List, Optional
import discord
import discord.ui as ui
from data.models import Relationship

class BaseRpgObj(ABC):
    """
    Abstract base class for a "thing".
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data

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
        return self.data.get("owner_id")

    @owner_id.setter
    def owner_id(self, value: str):
        self.data["owner_id"] = value

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

class RollModifiers(ABC):
    """
    A flexible container for roll parameters (e.g., skill, attribute, modifiers).
    Non-modifier properties (like skill, attribute) are stored in a separate dictionary.
    Modifiers are stored in self.modifiers.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        self.modifiers = {}  # Store direct numeric modifiers (e.g., mod1, mod2)
        if roll_parameters_dict:
            for key, modifier in roll_parameters_dict.items():
                self.modifiers[key] = modifier

    def __getitem__(self, key):
        return self.modifiers.get(key)

    def __setitem__(self, key, value):
        self.modifiers[key] = value

    def to_dict(self):
        return dict(self.modifiers)

    def get_modifiers(self, character: "BaseCharacter") -> Dict[str, str]:
        """
        Returns a dictionary of all modifiers
        """
        return dict(self.modifiers)

    def __repr__(self):
        return f"RollModifiers(modifiers={self.modifiers})"

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

    def format_full_sheet(self) -> discord.Embed:
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

        """ if self.ENTITY_DEFAULTS:
            defaults = self.ENTITY_DEFAULTS.get_defaults(entity_type)
            for key, value in defaults.items():
                self._apply_default_field(key, value, guild_id) """
    
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
        entity_type: EntityType,
        notes: List[str] = None, 
        avatar_url: str = None, 
        system_specific_fields: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Helper method to create a standardized entity dictionary."""
        entity = {
            "id": str(id),
            "name": name,
            "owner_id": str(owner_id),
            "entity_type": entity_type.value,
            "notes": notes or [],
            "avatar_url": avatar_url or '',
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
    
    def get_owner(self) -> Optional['BaseEntity']:
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
    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollModifiers, difficulty: int = None):
        """
        Abstract method to handle a roll request for this character.
        Should return a discord.ui.View or send a message with the result.
        """
        pass