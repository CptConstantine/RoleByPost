import json
from typing import Optional
from data.models import EntityDetails
from data.repositories.base_repository import BaseRepository


class EntityDetailsRepository(BaseRepository[EntityDetails]):
    def __init__(self):
        super().__init__('vw_entity_details')

    def to_dict(self, entity: EntityDetails) -> dict:
        return {
            'id': entity.id,
            'guild_id': entity.guild_id,
            'name': entity.name,
            'owner_id': entity.owner_id,
            'entity_type': entity.entity_type,
            'system': entity.system,
            'avatar_url': entity.avatar_url,
            'access_type': entity.access_type,
            'possessed_items': json.dumps(entity.possessed_items) if entity.possessed_items else None,
            'possessed_by': json.dumps(entity.possessed_by) if entity.possessed_by else None,
            'controls': json.dumps(entity.controls) if entity.controls else None,
            'controlled_by': json.dumps(entity.controlled_by) if entity.controlled_by else None
        }

    def from_dict(self, data: dict) -> EntityDetails:
        return EntityDetails(
            id=data['id'],
            guild_id=data['guild_id'],
            name=data['name'],
            owner_id=data['owner_id'],
            entity_type=data['entity_type'],
            system=data['system'],
            avatar_url=data['avatar_url'],
            access_type=data['access_type'],
            possessed_items=data['possessed_items'],
            possessed_by=data['possessed_by'],
            controls=data['controls'],
            controlled_by=data['controlled_by']
        )
    
    def get_by_id(self, entity_id: str) -> Optional[EntityDetails]:
        return self.find_by_id('id', entity_id)