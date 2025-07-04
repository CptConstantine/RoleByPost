from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from data.models import Relationship
from core.models import BaseEntity
import json
import uuid
from datetime import datetime

class RelationshipRepository(BaseRepository[Relationship]):
    def __init__(self):
        super().__init__('relationships')
    
    def to_dict(self, entity: Relationship) -> dict:
        return {
            'id': entity.id,
            'guild_id': entity.guild_id,
            'from_entity_id': entity.from_entity_id,
            'to_entity_id': entity.to_entity_id,
            'relationship_type': entity.relationship_type,
            'metadata': json.dumps(entity.metadata),
            'created_at': entity.created_at.isoformat() if entity.created_at else None
        }

    def from_dict(self, data: dict) -> Relationship:
        # Handle metadata - it might already be parsed or still be a string
        metadata = data.get('metadata', '{}')
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        elif metadata is None:
            metadata = {}
        
        # Handle created_at
        created_at = data.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return Relationship(
            id=data['id'],
            guild_id=data['guild_id'],
            from_entity_id=data['from_entity_id'],
            to_entity_id=data['to_entity_id'],
            relationship_type=data['relationship_type'],
            metadata=metadata,
            created_at=created_at
        )

    def get_children(self, guild_id: str, entity_id: str, relationship_type: str = None) -> List[BaseEntity]:
        """Get entities that this entity has relationships TO (children)"""
        from data.repositories.repository_factory import repositories
        if relationship_type:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND relationship_type = %s"
            relationships = self.execute_query(query, (str(guild_id), str(entity_id), relationship_type))
        else:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s"
            relationships = self.execute_query(query, (str(guild_id), str(entity_id)))
        
        # Get the actual entities
        child_entities = []
        for relationship in relationships:
            entity = repositories.entity.get_by_id(relationship.to_entity_id)
            if entity:
                child_entities.append(entity)
        
        return child_entities

    def get_parents(self, guild_id: str, entity_id: str, relationship_type: str = None) -> List[BaseEntity]:
        """Get entities that have relationships TO this entity (parents)"""
        from data.repositories.repository_factory import repositories
        if relationship_type:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND to_entity_id = %s AND relationship_type = %s"
            relationships = self.execute_query(query, (str(guild_id), str(entity_id), relationship_type))
        else:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND to_entity_id = %s"
            relationships = self.execute_query(query, (str(guild_id), str(entity_id)))
        
        # Get the actual entities
        parent_entities = []
        for relationship in relationships:
            entity = repositories.entity.get_by_id(relationship.from_entity_id)
            if entity:
                parent_entities.append(entity)
        
        return parent_entities

    def get_relationships_for_entity(self, guild_id: str, entity_id: str) -> List[Relationship]:
        """Get all relationships involving this entity (both directions)"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND (from_entity_id = %s OR to_entity_id = %s)"
        return self.execute_query(query, (str(guild_id), str(entity_id), str(entity_id)))

    def create_relationship(self, guild_id: str, from_entity_id: str, to_entity_id: str, relationship_type: str, metadata: Dict[str, Any] = None) -> Relationship:
        """Create a new relationship"""
        relationship = Relationship(
            id=str(uuid.uuid4()),
            guild_id=str(guild_id),
            from_entity_id=str(from_entity_id),
            to_entity_id=str(to_entity_id),
            relationship_type=relationship_type,
            metadata=metadata or {},
            created_at=datetime.now()
        )
        
        self.save(relationship, conflict_columns=['guild_id', 'from_entity_id', 'to_entity_id', 'relationship_type'])
        return relationship

    def delete_relationship(self, relationship_id: str) -> bool:
        """Delete a relationship by ID"""
        query = f"DELETE FROM {self.table_name} WHERE id = %s"
        result = self.execute_query(query, (relationship_id,))
        return result is not None

    def delete_relationships_by_entities(self, guild_id: str, from_entity_id: str, to_entity_id: str, relationship_type: str = None) -> bool:
        """Delete relationships between two entities"""
        if relationship_type:
            query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s AND relationship_type = %s"
            self.execute_query(query, (str(guild_id), str(from_entity_id), str(to_entity_id), relationship_type))
        else:
            query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s"
            self.execute_query(query, (str(guild_id), str(from_entity_id), str(to_entity_id)))
        return True

    def get_relationship_by_entities(self, guild_id: str, from_entity_id: str, to_entity_id: str, relationship_type: str = None) -> Optional[Relationship]:
        """Get a specific relationship between two entities"""
        if relationship_type:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s AND relationship_type = %s"
            return self.execute_query(query, (str(guild_id), str(from_entity_id), str(to_entity_id), relationship_type), fetch_one=True)
        else:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s"
            return self.execute_query(query, (str(guild_id), str(from_entity_id), str(to_entity_id)), fetch_one=True)

    def delete_all_relationships_for_entity(self, guild_id: str, entity_id: str) -> bool:
        """Delete all relationships involving an entity (used when deleting entities)"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND (from_entity_id = %s OR to_entity_id = %s)"
        self.execute_query(query, (str(guild_id), str(entity_id), str(entity_id)))
        return True