from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from data.models import Entity
from core.base_models import BaseEntity, EntityType, EntityJSONEncoder
import json
import uuid
import time
import core.factories as factories

class EntityRepository(BaseRepository[Entity]):
    def __init__(self):
        super().__init__('entities')
    
    def to_dict(self, entity: Entity) -> dict:
        return {
            'id': entity.id,
            'guild_id': entity.guild_id,
            'name': entity.name,
            'owner_id': entity.owner_id,
            'entity_type': entity.entity_type,
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
        
        return Entity(
            id=data['id'],
            guild_id=data['guild_id'],
            name=data['name'],
            owner_id=data['owner_id'],
            entity_type=data['entity_type'],
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
        EntityClass = factories.get_specific_entity(entity.system, EntityType(entity.entity_type))
        
        # Create the entity dict using the helper method
        entity_dict = BaseEntity.build_entity_dict(
            id=entity.id,
            name=entity.name,
            owner_id=entity.owner_id,
            system=entity.system,
            entity_type=EntityType(entity.entity_type),
            notes=entity.notes,
            avatar_url=entity.avatar_url,
            system_specific_fields=entity.system_specific_data
        )
        
        # Add access_control if it doesn't exist (migration)
        if "access_control" not in entity_dict:
            entity_dict["access_control"] = {
                "access_type": "specific_users",
                "allowed_user_ids": []
            }
        
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
    
    def get_all_by_owner(self, guild_id: str, owner_id: str) -> List[BaseEntity]:
        """Get all entities owned by a user"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND owner_id = %s ORDER BY name"
        entities = self.execute_query(query, (str(guild_id), str(owner_id)))
        return self._convert_list_to_base_entities(entities)
    
    def get_all_accessible(self, guild_id: str, user_id: str, is_gm: bool = False) -> List[BaseEntity]:
        """
        Get all entities a user can access through:
        1. Direct ownership (owner_id)
        2. Control links (entities they control)
        3. Access control permissions (public/specific_users)
        """
        if is_gm:
            # GMs can access everything
            return self.get_all_by_guild(guild_id)
        
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        # Complex query to get all accessible entities
        query = f"""
        SELECT DISTINCT e.* FROM {self.table_name} e
        WHERE e.guild_id = %s AND (
            -- Direct ownership
            e.owner_id = %s
            OR
            -- Public access
            (e.system_specific_data->>'access_control' IS NULL 
             OR (e.system_specific_data->'access_control'->>'access_type') = 'public')
            OR
            -- Specific user access
            (
                (e.system_specific_data->'access_control'->>'access_type') = 'specific_users'
                AND (
                    e.system_specific_data->'access_control'->'allowed_user_ids' ? %s
                    OR e.system_specific_data->'access_control'->>'allowed_user_ids' LIKE %s
                )
            )
            OR
            -- Entities controlled by user's entities
            e.id IN (
                SELECT el.to_entity_id 
                FROM entity_links el
                JOIN {self.table_name} owner_entity ON owner_entity.id = el.from_entity_id
                WHERE el.guild_id = %s 
                AND el.link_type = 'controls'
                AND owner_entity.owner_id = %s
            )
        )
        ORDER BY e.name
        """
        
        # Parameters for the query
        # %s for user_id in JSON search (for exact match and LIKE pattern)
        like_pattern = f'%"{user_id}"%'
        
        entities = self.execute_query(
            query, 
            (guild_id, user_id, user_id, like_pattern, guild_id, user_id)
        )
        
        return self._convert_list_to_base_entities(entities)
    
    def get_entities_controlled_by_user(self, guild_id: str, user_id: str) -> List[BaseEntity]:
        """Get entities that are controlled by entities owned by the user"""
        user_id = str(user_id)
        guild_id = str(guild_id)
        
        query = f"""
        SELECT DISTINCT controlled.* 
        FROM {self.table_name} controlled
        JOIN entity_links el ON controlled.id = el.to_entity_id
        JOIN {self.table_name} controller ON controller.id = el.from_entity_id
        WHERE el.guild_id = %s 
        AND el.link_type = 'controls'
        AND controller.owner_id = %s
        ORDER BY controlled.name
        """
        
        entities = self.execute_query(query, (guild_id, user_id))
        return self._convert_list_to_base_entities(entities)
    
    def upsert_entity(self, guild_id: str, entity: BaseEntity, system: str) -> None:
        """Save or update a BaseEntity by converting it to Entity first"""
        # Get system-specific fields
        EntityClass = factories.get_specific_entity(system, entity.entity_type)
        system_fields = EntityClass.ENTITY_DEFAULTS.get_defaults(entity.entity_type)

        system_specific_data = {}
        for key in system_fields:
            system_specific_data[key] = entity.data.get(key)

        # Include access_control in system_specific_data for storage
        if "access_control" in entity.data:
            system_specific_data["access_control"] = entity.data["access_control"]

        notes = entity.notes or []
        
        # Create Entity from BaseEntity
        storage_entity = Entity(
            id=entity.id,
            guild_id=str(guild_id),
            name=entity.name,
            owner_id=entity.owner_id,
            entity_type=entity.entity_type.value,
            system=system,
            system_specific_data=system_specific_data,
            notes=notes,
            avatar_url=entity.avatar_url
        )
        
        self.save(storage_entity, conflict_columns=['id'])
    
    def delete_entity(self, guild_id: str, entity_id: str) -> None:
        """Delete an entity and all its links"""
        entity = self.get_by_id(entity_id)
        if entity:
            # Delete all links involving this entity
            from .repository_factory import repositories
            repositories.link.delete_all_links_for_entity(
                guild_id,
                entity_id
            )
            
            # Delete the entity itself
            query = f"DELETE FROM {self.table_name} WHERE id = %s"
            self.execute_query(query, (entity_id,))
    
    def rename_entity(self, entity_id: str, new_name: str) -> bool:
        """Rename an entity"""
        query = f"UPDATE {self.table_name} SET name = %s WHERE id = %s"
        self.execute_query(query, (new_name, entity_id))
        return True