from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from enum import Enum
import json
from typing import Any, ClassVar, Dict, List, Optional
import discord
import discord.ui as ui
from core.roll_formula import RollFormula
from data.models import EntityLink

class AccessType(Enum):
    """Simple access control for entities"""
    PUBLIC = "public"  # Anyone can access
    GM_ONLY = "gm_only"  # Only GMs can access

@dataclass
class AccessLevel:
    """Simplified access control configuration"""
    access_type: AccessType = AccessType.PUBLIC
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "access_type": self.access_type.value
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessLevel":
        """Create from dictionary"""
        access_type_str = data.get("access_type", "public")
        try:
            access_type = AccessType(access_type_str)
        except ValueError:
            access_type = AccessType.PUBLIC
        return cls(access_type=access_type)
    
    def can_access(self, user_id: str, is_gm: bool = False) -> bool:
        """Check if a user can access the entity"""
        if self.access_type == AccessType.PUBLIC:
            return True
        elif self.access_type == AccessType.GM_ONLY:
            return is_gm
        return False

class BaseRpgObj(ABC):
    """
    Abstract base class for a "thing".
    """
    def __init__(self, data: Dict[str, Any]):
        self.data = data
        # Ensure access_type exists for all entities
        self._ensure_access_type()

    def _ensure_access_type(self):
        """Ensure access_type field exists with proper defaults"""
        if "access_type" not in self.data:
            self.data["access_type"] = AccessType.PUBLIC.value

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
    def access_type(self) -> AccessType:
        """Get access type"""
        access_type_str = self.data.get("access_type", "public")
        try:
            return AccessType(access_type_str)
        except ValueError:
            return AccessType.PUBLIC

    @access_type.setter
    def access_type(self, value: AccessType):
        """Set access type"""
        self.data["access_type"] = value.value

    def can_be_accessed_by(self, user_id: str, is_gm: bool = False) -> bool:
        """
        Check if a user can access the entity
        
        Args:
            user_id: Discord user ID to check
            is_gm: Whether the user has GM permissions
            owner_id: The owner ID of the entity (optional)
            
        Returns:
            True if user can access this entity
        """
        user_id = str(user_id)
        
        # GMs always have access
        if is_gm:
            return True
        
        # Check access type
        if self.access_type == AccessType.PUBLIC:
            return True
        
        return False

    def set_access_type(self, access_type: AccessType) -> None:
        """Set the access type"""
        self.access_type = access_type

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
    
class EntityLinkType(Enum):
    """Types of links between entities"""
    POSSESSES = "possesses" # For Inventory
    CONTROLS = "controls"   # Can speak as this entity
    
    def __str__(self):
        return self.value
    
    @staticmethod
    def get_all_dict() -> Dict[str, 'EntityLinkType']:
        return {name: member for name, member in EntityLinkType.__members__.items()}
    
    @staticmethod
    def get_links_str(guild_id: str, entity: 'BaseEntity') -> List[str]:
        """Get a list of link strings for the entity."""
        links_dict = EntityLinkType.get_links_dict(guild_id, entity)
        return [f"{key}: {value}" for key, value in links_dict.items()]

    @staticmethod
    def get_links_dict(guild_id: str, entity: 'BaseEntity') -> Dict[str, str]:
        """Get a dictionary of link types and their string representations."""
        from data.repositories.repository_factory import repositories
        links_dict = {}
        
        # Entities this entity owns
        possessed_entities = repositories.link.get_children(
            guild_id, 
            entity.id, 
            EntityLinkType.POSSESSES.value
        )
        if possessed_entities:
            possessed_names = [e.name for e in possessed_entities[:5]]  # Show first 5
            possessed_text = ", ".join(possessed_names)
            if len(possessed_entities) > 5:
                possessed_text += f" (+{len(possessed_entities) - 5} more)"
            links_dict[f"📦 Possesses ({len(possessed_entities)})"] = possessed_text
        
        # Entities that own this entity
        possessors = repositories.link.get_parents(
            guild_id,
            entity.id, 
            EntityLinkType.POSSESSES.value
        )
        if possessors:
            possessor_names = [e.name for e in possessors]
            links_dict["📦 Possessed By"] = ", ".join(possessor_names)

        # Control links
        controlled_entities = repositories.link.get_children(
            guild_id, 
            entity.id, 
            EntityLinkType.CONTROLS.value
        )
        if controlled_entities:
            controlled_names = [e.name for e in controlled_entities]
            links_dict["🎮 Controls"] = ", ".join(controlled_names)
        
        controllers = repositories.link.get_parents(
            guild_id, 
            entity.id, 
            EntityLinkType.CONTROLS.value
        )
        if controllers:
            controller_names = [e.name for e in controllers]
            links_dict["🎮 Controlled By"] = ", ".join(controller_names)
        
        # Get all other links
        all_links = repositories.link.get_links_for_entity(
            guild_id, 
            entity.id
        )
        
        # Filter out POSSESSES and CONTROLS links (already shown above)
        other_links = [
            rel for rel in all_links 
            if rel.link_type not in [EntityLinkType.POSSESSES.value, EntityLinkType.CONTROLS.value]
        ]
        
        if other_links:
            rel_lines = []
            for rel in other_links[:3]:  # Show first 3 other links
                if rel.from_entity_id == entity.id:
                    # This entity has a link TO another entity
                    target_entity = repositories.entity.get_by_id(rel.to_entity_id)
                    if target_entity:
                        rel_name = rel.link_type.replace("_", " ").title()
                        rel_lines.append(f"• {rel_name} **{target_entity.name}**")
                else:
                    # Another entity has a link TO this entity
                    source_entity = repositories.entity.get_by_id(rel.from_entity_id)
                    if source_entity:
                        rel_name = rel.link_type.replace("_", " ").title()
                        rel_lines.append(f"• **{source_entity.name}** {rel_name.lower()} this entity")
            
            if rel_lines:
                rel_text = "\n".join(rel_lines)
                if len(other_links) > 3:
                    rel_text += f"\n(+{len(other_links) - 3} more links)"
                links_dict["🔗 Other Links"] = rel_text
        
        return links_dict

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

    def get_sheet_edit_view(self, editor_id: int, is_gm: bool) -> ui.View:
        """Get the appropriate sheet edit view for this entity type"""
        raise NotImplementedError("Subclasses must implement get_sheet_edit_view")

    def format_full_sheet(self, guild_id: int, is_gm: bool = False) -> discord.Embed:
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
        access_type: AccessType = AccessType.PUBLIC,
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
            "access_type": access_type.value
        }
        
        # Add system-specific fields
        if system_specific_fields:
            for key, value in system_specific_fields.items():
                entity[key] = value
        
        return entity
    
    def get_item_quantity(self, guild_id: str, item_name: str) -> int:
        """Get the total quantity of an item in the container"""
        total_quantity = 0
        for contained_item in self.get_contained_items(guild_id):
            if contained_item.name == item_name:
                links = self.get_links_to_entity(guild_id, contained_item.id, EntityLinkType.POSSESSES)
                if links:
                    total_quantity += links[0].metadata.get("quantity", 1)
        return total_quantity
    
    def can_take_item(self, guild_id: str, item_name: str, quantity: int = 1) -> bool:
        """Check if we can take the specified quantity of an item"""
        available_quantity = self.get_item_quantity(guild_id, item_name)
        return available_quantity >= quantity
    
    def take_item(self, guild_id: str, item_name: str, quantity: int = 1) -> 'BaseEntity':
        """Take items from container, returns the item entity for adding to inventory"""
        if not self.can_take_item(guild_id, item_name, quantity):
            return None
        
        # Find the item
        target_item = None
        for contained_item in self.get_contained_items(guild_id):
            if contained_item.name == item_name:
                target_item = contained_item
                break
        
        if not target_item:
            return None
        
        # Remove the quantity
        self.remove_item(guild_id, target_item, quantity)
        
        return target_item
    
    def get_links_to_entity(self, guild_id: str, entity_id: str, link_type: EntityLinkType) -> List[EntityLink]:
        """Helper method to get links to a specific entity"""
        from data.repositories.repository_factory import repositories
        all_links = repositories.link.get_links_for_entity(guild_id, self.id)
        return [rel for rel in all_links 
                if rel.from_entity_id == self.id and rel.to_entity_id == entity_id 
                and rel.link_type == link_type.value]

    def get_children(self, guild_id: str, link_type: EntityLinkType = None) -> List['BaseEntity']:
        """Get entities this entity has links to"""
        from data.repositories.repository_factory import repositories
        return repositories.link.get_children(guild_id, self.id, link_type.value if link_type else None)
    
    def get_contained_items(self, guild_id: str) -> List['BaseEntity']:
        """Get all items contained in this container"""
        return [item for item in self.get_children(guild_id, EntityLinkType.POSSESSES) if item.entity_type == EntityType.ITEM]

    def get_parents(self, guild_id: str, link_type: EntityLinkType = None) -> List['BaseEntity']:
        """Get entities that have links to this entity"""
        from data.repositories.repository_factory import repositories
        return repositories.link.get_parents(guild_id, self.id, link_type.value if link_type else None)
    
    def get_possesser(self) -> Optional['BaseEntity']:
        """Get the entity that owns this entity (if any)"""
        owners = self.get_parents(EntityLinkType.POSSESSES.value)
        return owners[0] if owners else None
    
    def get_controlled_entities(self) -> List['BaseEntity']:
        """Get entities that this entity controls"""
        return self.get_children(EntityLinkType.CONTROLS.value)
    
    def can_be_controlled_by(self, user_id: str) -> bool:
        """Check if a user can control this entity"""
        # User can control their own entities
        if self.owner_id == str(user_id):
            return True
        
        # Check if user owns any entities that control this entity
        controlling_entities = self.get_parents(EntityLinkType.CONTROLS.value)
        for entity in controlling_entities:
            if entity.owner_id == str(user_id):
                return True
        
        return False

    def add_link(self, guild_id: str, target_entity: 'BaseEntity', link_type: EntityLinkType, metadata: Dict[str, Any] = None) -> 'EntityLink':
        """Add a link to another entity"""
        from data.repositories.repository_factory import repositories
        return repositories.link.create_link(
            guild_id, 
            self.id, 
            target_entity.id, 
            link_type.value, 
            metadata
        )

    def remove_link(self, guild_id: str, target_entity: 'BaseEntity', link_type: EntityLinkType = None) -> bool:
        """Remove a link to another entity"""
        from data.repositories.repository_factory import repositories
        return repositories.link.delete_links_by_entities(
            guild_id, 
            self.id, 
            target_entity.id, 
            link_type.value if link_type else None
        )
    
    def get_inventory(self, guild_id: str) -> List['BaseEntity']:
        """Get all items in this entity's inventory"""
        possessed_entities = self.get_children(guild_id, EntityLinkType.POSSESSES)
        return [entity for entity in possessed_entities if entity.entity_type == EntityType.ITEM]
    
    def add_to_inventory(self, guild_id: str, item: 'BaseEntity') -> 'EntityLink':
        """Add an item to this entity's inventory"""
        if item.entity_type != EntityType.ITEM:
            raise ValueError("Only ITEM entities can be added to inventory")
        return self.add_link(guild_id, item, EntityLinkType.POSSESSES)
    
    def add_item(self, guild_id: str, item: 'BaseEntity', quantity: int = 1) -> bool:
        """Add an item to the container with specified quantity, stacking if same item exists"""
        if item.entity_type != EntityType.ITEM:
            return False
        
        # Check if we already have this item (by name for stacking)
        existing_links = []
        for contained_item in self.get_contained_items(guild_id):
            if contained_item.name == item.name:
                links = self.get_links_to_entity(guild_id, contained_item.id, EntityLinkType.POSSESSES)
                if links:
                    existing_links.extend(links)
        
        if existing_links:
            # Stack with existing item
            link = existing_links[0]
            current_quantity = link.metadata.get("quantity", 1)
            link.metadata["quantity"] = current_quantity + quantity
            
            from data.repositories.repository_factory import repositories
            repositories.link.save(link)
            return True
        else:
            # Check if container has space for new unique item
            max_items = self.data.get("max_items", 0)
            if max_items > 0:
                unique_items = len(self.get_contained_items(guild_id))
                if unique_items >= max_items:
                    return False
            
            # Create new link with quantity metadata
            metadata = {"quantity": quantity}
            self.add_link(guild_id, item, EntityLinkType.POSSESSES, metadata)
            return True
    
    def remove_from_inventory(self, guild_id: str, item: 'BaseEntity') -> bool:
        """Remove an item from this entity's inventory"""
        if item.entity_type != EntityType.ITEM:
            raise ValueError("Only ITEM entities can be removed from inventory")
        return self.remove_link(guild_id, item, EntityLinkType.POSSESSES)
    
    def remove_item(self, guild_id: str, item: 'BaseEntity', quantity: int = None) -> bool:
        """Remove an item from the container"""
        if item.entity_type != EntityType.ITEM:
            return False
        
        # If no quantity specified, remove all
        if quantity is None:
            return self.remove_link(guild_id, item, EntityLinkType.POSSESSES)
        
        # Get current link to check quantity
        links = self.get_links_to_entity(guild_id, item.id, EntityLinkType.POSSESSES)
        if not links:
            return False
        
        link = links[0]
        current_quantity = link.metadata.get("quantity", 1)
        
        if quantity >= current_quantity:
            # Remove completely
            return self.remove_link(guild_id, item, EntityLinkType.POSSESSES)
        else:
            # Update quantity
            from data.repositories.repository_factory import repositories
            link.metadata["quantity"] = current_quantity - quantity
            repositories.link.save(link)
            return True

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