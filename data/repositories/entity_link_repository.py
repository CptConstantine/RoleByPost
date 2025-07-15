from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from data.models import EntityLink
from core.base_models import BaseEntity
import json
import uuid
from datetime import datetime

class EntityLinkRepository(BaseRepository[EntityLink]):
    def __init__(self):
        super().__init__('entity_links')
    
    def to_dict(self, entity: EntityLink) -> dict:
        return {
            'id': entity.id,
            'guild_id': entity.guild_id,
            'from_entity_id': entity.from_entity_id,
            'to_entity_id': entity.to_entity_id,
            'link_type': entity.link_type,
            'metadata': json.dumps(entity.metadata),
            'created_at': entity.created_at.isoformat() if entity.created_at else None
        }

    def from_dict(self, data: dict) -> EntityLink:
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
        
        return EntityLink(
            id=data['id'],
            guild_id=data['guild_id'],
            from_entity_id=data['from_entity_id'],
            to_entity_id=data['to_entity_id'],
            link_type=data['link_type'],
            metadata=metadata,
            created_at=created_at
        )

    def get_children(self, guild_id: str, entity_id: str, link_type: str = None) -> List[BaseEntity]:
        """Get entities that this entity has links TO (children)"""
        from data.repositories.repository_factory import repositories
        
        params = [str(guild_id), str(entity_id)]
        link_type_clause = ""
        if link_type:
            link_type_clause = "AND el.link_type = %s"
            params.append(link_type)

        query = f"""
            SELECT e.* 
            FROM entities e
            JOIN entity_links el ON e.id = el.to_entity_id
            WHERE el.guild_id = %s AND el.from_entity_id = %s {link_type_clause}
            ORDER BY e.name
        """
        
        # Use the entity repository's methods to handle conversion from dict to BaseEntity
        child_entity_dicts = repositories.entity.execute_query(query, tuple(params))
        return repositories.entity._convert_list_to_base_entities(child_entity_dicts)

    def get_parents(self, guild_id: str, entity_id: str, link_type: str = None) -> List[BaseEntity]:
        """Get entities that have links TO this entity (parents)"""
        from data.repositories.repository_factory import repositories
        
        params = [str(guild_id), str(entity_id)]
        link_type_clause = ""
        if link_type:
            link_type_clause = "AND el.link_type = %s"
            params.append(link_type)

        query = f"""
            SELECT e.* 
            FROM entities e
            JOIN entity_links el ON e.id = el.from_entity_id
            WHERE el.guild_id = %s AND el.to_entity_id = %s {link_type_clause}
            ORDER BY e.name
        """
        
        # Use the entity repository's methods to handle conversion from dict to BaseEntity
        parent_entity_dicts = repositories.entity.execute_query(query, tuple(params))
        return repositories.entity._convert_list_to_base_entities(parent_entity_dicts)

    def get_links_for_entity(self, guild_id: str, entity_id: str) -> List[EntityLink]:
        """Get all links involving this entity (both directions)"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND (from_entity_id = %s OR to_entity_id = %s)"
        return self.execute_query(query, (str(guild_id), str(entity_id), str(entity_id)))

    def create_link(self, guild_id: str, from_entity_id: str, to_entity_id: str, link_type: str, metadata: Dict[str, Any] = None) -> EntityLink:
        """Create a new link"""
        link = EntityLink(
            id=str(uuid.uuid4()),
            guild_id=str(guild_id),
            from_entity_id=str(from_entity_id),
            to_entity_id=str(to_entity_id),
            link_type=link_type,
            metadata=metadata or {},
            created_at=datetime.now()
        )
        
        self.save(link, conflict_columns=['guild_id', 'from_entity_id', 'to_entity_id', 'link_type'])
        return link

    def delete_link(self, link_id: str) -> bool:
        """Delete a link by ID"""
        query = f"DELETE FROM {self.table_name} WHERE id = %s"
        result = self.execute_query(query, (link_id,))
        return result is not None

    def delete_links_by_entities(self, guild_id: str, from_entity_id: str, to_entity_id: str, link_type: str = None) -> bool:
        """Delete links between two entities"""
        if link_type:
            query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s AND link_type = %s"
            self.execute_query(query, (str(guild_id), str(from_entity_id), str(to_entity_id), link_type))
        else:
            query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s"
            self.execute_query(query, (str(guild_id), str(from_entity_id), str(to_entity_id)))
        return True

    def get_link_by_entities(self, guild_id: str, from_entity_id: str, to_entity_id: str, link_type: str = None) -> Optional[EntityLink]:
        """Get a specific link between two entities"""
        if link_type:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s AND link_type = %s"
            return self.execute_query(query, (str(guild_id), str(from_entity_id), str(to_entity_id), link_type), fetch_one=True)
        else:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s"
            return self.execute_query(query, (str(guild_id), str(from_entity_id), str(to_entity_id)), fetch_one=True)

    def delete_all_links_for_entity(self, guild_id: str, entity_id: str) -> bool:
        """Delete all links involving an entity (used when deleting entities)"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND (from_entity_id = %s OR to_entity_id = %s)"
        self.execute_query(query, (str(guild_id), str(entity_id), str(entity_id)))
        return True
    
    def get_possessed_quantity(self, guild_id: str, parent_id: str, item_id: str) -> int:
        """Get the quantity of a specific item possessed by an entity"""
        # Grab the quantity from the metadata if it exists. Default to 1
        query = f"""
            SELECT * 
            FROM {self.table_name} 
            WHERE guild_id = %s AND from_entity_id = %s AND to_entity_id = %s AND link_type = 'possesses'
        """
        link = self.execute_query(query, (str(guild_id), str(parent_id), str(item_id)), fetch_one=True)
        return link.metadata.get('quantity', 1) if link else 1
    
    def update_metadata(self, link: EntityLink) -> EntityLink:
        """Update the metadata of an existing link"""
        query = f"""
            UPDATE {self.table_name} 
            SET metadata = %s 
            WHERE id = %s
        """
        self.execute_query(query, (json.dumps(link.metadata), link.id))
        return link