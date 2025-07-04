from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from data.models import Entity
from core.models import BaseEntity, EntityType, EntityJSONEncoder
import json
import uuid
import time
import core.factories as factories

class EntityRepository(BaseRepository[Entity]):
    def __init__(self):
        super().__init__('entities')
    
    def to_dict(self, entity: Entity) -> dict:
        # Convert empty string parent_entity_id to None for proper foreign key handling
        parent_entity_id = entity.parent_entity_id
        if parent_entity_id == '':
            parent_entity_id = None

        return {
            'id': entity.id,
            'guild_id': entity.guild_id,
            'name': entity.name,
            'owner_id': entity.owner_id,
            'entity_type': entity.entity_type,
            'parent_entity_id': parent_entity_id,
            'system': entity.system,
            'system_specific_data': json.dumps(entity.system_specific_data, cls=EntityJSONEncoder),
            'notes': json.dumps(entity.notes),
            'avatar_url': entity.avatar_url
        }
    
    def from_dict(self, data: dict) -> Entity:
        # Handle system_specific_data - it might already be parsed or still be a string
        system_specific_data = data.get('system_specific_data', '{}')
        if isinstance(system_specific_data, str):
            system_specific_data = json.loads(system_specific_data)
        elif system_specific_data is None:
            system_specific_data = {}
        
        # Handle notes - it might already be parsed or still be a string
        notes = data.get('notes', '[]')
        if isinstance(notes, str):
            notes = json.loads(notes)
        elif notes is None:
            notes = []
        
        # Handle parent_entity_id - convert None to empty string for consistency
        parent_entity_id = data.get('parent_entity_id')
        if parent_entity_id is None:
            parent_entity_id = ''
        
        return Entity(
            id=data['id'],
            guild_id=data['guild_id'],
            name=data['name'],
            owner_id=data['owner_id'],
            entity_type=data['entity_type'],
            parent_entity_id=parent_entity_id,
            system=data['system'],
            system_specific_data=system_specific_data,
            notes=notes,
            avatar_url=data.get('avatar_url', '')
        )
    
    def _convert_to_base_entity(self, entity: Entity) -> BaseEntity:
        """Convert an Entity to a system-specific BaseEntity"""
        if not entity:
            return None
            
        # Get the system-specific entity class
        EntityClass = factories.get_specific_entity(entity.system, entity.entity_type)
        
        # Create the entity dict using the helper method
        entity_dict = BaseEntity.build_entity_dict(
            id=entity.id,
            name=entity.name,
            owner_id=entity.owner_id,
            entity_type=EntityType(entity.entity_type),
            parent_entity_id=entity.parent_entity_id if entity.parent_entity_id else None,
            notes=entity.notes,
            avatar_url=entity.avatar_url,
            system_specific_fields=entity.system_specific_data
        )
        
        return EntityClass.from_dict(entity_dict)
    
    def _convert_list_to_base_entities(self, entities: List[Entity]) -> List[BaseEntity]:
        """Convert a list of Entity objects to BaseEntity objects"""
        return [self._convert_to_base_entity(entity) for entity in entities if entity]
    
    def get_by_id(self, entity_id: str) -> Optional[BaseEntity]:
        """Get entity by ID"""
        entity = self.find_by_id('id', entity_id)
        return self._convert_to_base_entity(entity)
    
    def get_by_name(self, guild_id: str, name: str) -> Optional[BaseEntity]:
        """Get entity by name within a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND name = %s"
        entity = self.execute_query(query, (str(guild_id), name), fetch_one=True)
        return self._convert_to_base_entity(entity)
    
    def get_all_by_guild(self, guild_id: str, entity_type: str = None) -> List[BaseEntity]:
        """Get all entities for a guild, optionally filtered by type"""
        if entity_type:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND entity_type = %s ORDER BY name"
            entities = self.execute_query(query, (str(guild_id), entity_type))
        else:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s ORDER BY name"
            entities = self.execute_query(query, (str(guild_id),))
        
        return self._convert_list_to_base_entities(entities)
    
    def get_all_by_parent(self, guild_id: str, parent_entity_id: str) -> List[BaseEntity]:
        """Get all entities owned by a parent entity"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND parent_entity_id = %s ORDER BY name"
        entities = self.execute_query(query, (str(guild_id), parent_entity_id))
        return self._convert_list_to_base_entities(entities)
    
    def get_all_by_owner(self, guild_id: str, owner_id: str) -> List[BaseEntity]:
        """Get all entities owned by a user"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND owner_id = %s ORDER BY name"
        entities = self.execute_query(query, (str(guild_id), str(owner_id)))
        return self._convert_list_to_base_entities(entities)
    
    def get_top_level_entities(self, guild_id: str, entity_type: str = None) -> List[BaseEntity]:
        """Get entities that have no parent (top-level entities)"""
        if entity_type:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND entity_type = %s AND (parent_entity_id IS NULL OR parent_entity_id = '') ORDER BY name"
            entities = self.execute_query(query, (str(guild_id), entity_type))
        else:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND (parent_entity_id IS NULL OR parent_entity_id = '') ORDER BY name"
            entities = self.execute_query(query, (str(guild_id),))
        
        return self._convert_list_to_base_entities(entities)
    
    def upsert_entity(self, guild_id: str, entity: BaseEntity, system: str) -> None:
        """Save or update a BaseEntity by converting it to Entity first"""
        # Get system-specific fields
        EntityClass = factories.get_specific_entity(system, entity.entity_type.value)
        system_fields = EntityClass.ENTITY_DEFAULTS.get_defaults(entity.entity_type)

        system_specific_data = {}
        for key in system_fields:
            system_specific_data[key] = entity.data.get(key)

        notes = entity.notes or []
        
        # Handle parent_entity_id - convert empty string to None for proper foreign key handling
        parent_entity_id = entity.parent_entity_id
        if parent_entity_id == '':
            parent_entity_id = None
        
        # Create Entity from BaseEntity
        storage_entity = Entity(
            id=entity.id,
            guild_id=str(guild_id),
            name=entity.name,
            owner_id=entity.owner_id,
            entity_type=entity.entity_type.value,
            parent_entity_id=parent_entity_id,
            system=system,
            system_specific_data=system_specific_data,
            notes=notes,
            avatar_url=entity.avatar_url
        )
        
        self.save(storage_entity, conflict_columns=['id'])
    
    def delete_entity(self, entity_id: str) -> bool:
        """Delete an entity by ID"""
        deleted_count = self.delete("id = %s", (entity_id,))
        return deleted_count > 0
    
    def transfer_entity(self, entity_id: str, new_parent_id: str = None) -> bool:
        """Transfer an entity to a new parent (or make it top-level if new_parent_id is None)"""
        # Convert empty string to None for proper foreign key handling
        if new_parent_id == '':
            new_parent_id = None

        query = f"UPDATE {self.table_name} SET parent_entity_id = %s WHERE id = %s"
        self.execute_query(query, (new_parent_id, entity_id))
        return True
    
    def rename_entity(self, entity_id: str, new_name: str) -> bool:
        """Rename an entity"""
        query = f"UPDATE {self.table_name} SET name = %s WHERE id = %s"
        self.execute_query(query, (new_name, entity_id))
        return True