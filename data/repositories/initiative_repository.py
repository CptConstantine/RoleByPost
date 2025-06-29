from typing import Optional
from .base_repository import BaseRepository
from models import InitiativeTracker, ServerInitiativeDefaults
import json

class InitiativeRepository(BaseRepository[InitiativeTracker]):
    def __init__(self):
        super().__init__('initiative')
    
    def to_dict(self, entity: InitiativeTracker) -> dict:
        return {
            'guild_id': entity.guild_id,
            'channel_id': entity.channel_id,
            'type': entity.type,
            'initiative_state': entity.initiative_state,
            'is_active': entity.is_active,
            'message_id': entity.message_id
        }
    
    def from_dict(self, data: dict) -> InitiativeTracker:
        return InitiativeTracker(
            guild_id=data['guild_id'],
            channel_id=data['channel_id'],
            type=data['type'],
            initiative_state=data['initiative_state'],
            is_active=bool(data['is_active']),
            message_id=data.get('message_id')
        )
    
    def get_initiative(self, guild_id: str, channel_id: str) -> Optional[InitiativeTracker]:
        """Get initiative tracker for a channel"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND channel_id = %s"
        return self.execute_query(query, (str(guild_id), str(channel_id)), fetch_one=True)
    
    def start_initiative(self, guild_id: str, channel_id: str, init_type: str, state: dict, message_id: str = None) -> None:
        """Start initiative in a channel"""
        initiative = InitiativeTracker(
            guild_id=str(guild_id),
            channel_id=str(channel_id),
            type=init_type,
            initiative_state=json.dumps(state),
            is_active=True,
            message_id=str(message_id) if message_id else None
        )
        self.save(initiative, conflict_columns=['guild_id', 'channel_id'])
    
    def update_initiative_state(self, guild_id: str, channel_id: str, state: dict) -> None:
        """Update initiative state"""
        query = f"UPDATE {self.table_name} SET initiative_state = %s WHERE guild_id = %s AND channel_id = %s"
        self.execute_query(query, (json.dumps(state), str(guild_id), str(channel_id)))
    
    def end_initiative(self, guild_id: str, channel_id: str) -> None:
        """End initiative in a channel"""
        query = f"UPDATE {self.table_name} SET is_active = false WHERE guild_id = %s AND channel_id = %s"
        self.execute_query(query, (str(guild_id), str(channel_id)))

class ServerInitiativeDefaultsRepository(BaseRepository[ServerInitiativeDefaults]):
    def __init__(self):
        super().__init__('server_initiative_defaults')
    
    def to_dict(self, entity: ServerInitiativeDefaults) -> dict:
        return {
            'guild_id': entity.guild_id,
            'default_type': entity.default_type
        }
    
    def from_dict(self, data: dict) -> ServerInitiativeDefaults:
        return ServerInitiativeDefaults(
            guild_id=data['guild_id'],
            default_type=data['default_type']
        )
    
    def get_default_type(self, guild_id: str) -> Optional[str]:
        """Get default initiative type for a guild"""
        defaults = self.find_by_id('guild_id', str(guild_id))
        return defaults.default_type if defaults else None
    
    def set_default_type(self, guild_id: str, default_type: str) -> None:
        """Set default initiative type for a guild"""
        defaults = ServerInitiativeDefaults(
            guild_id=str(guild_id),
            default_type=default_type
        )
        self.save(defaults, conflict_columns=['guild_id'])