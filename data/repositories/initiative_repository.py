from typing import Optional

from core import factories
from core.base_models import BaseInitiative
from .base_repository import BaseRepository
from data.models import InitiativeTracker, ServerInitiativeDefaults
import json

class InitiativeRepository(BaseRepository[InitiativeTracker]):
    def __init__(self):
        super().__init__('initiative')
    
    def to_dict(self, entity: InitiativeTracker) -> dict:
        return {
            'guild_id': entity.guild_id,
            'channel_id': entity.channel_id,
            'type': entity.type,
            'initiative_state': json.dumps(entity.initiative_state) if entity.initiative_state else '{}',
            'is_active': entity.is_active,
            'message_id': entity.message_id
        }
    
    def from_dict(self, data: dict) -> InitiativeTracker:
        initiative_state_data = data.get('initiative_state', '{}')
        
        # Parse JSON string to dict for the entity
        if isinstance(initiative_state_data, str):
            try:
                initiative_state = json.loads(initiative_state_data)
            except (json.JSONDecodeError, TypeError):
                initiative_state = {}
        elif isinstance(initiative_state_data, dict):
            initiative_state = initiative_state_data
        else:
            initiative_state = {}
        
        return InitiativeTracker(
            guild_id=data['guild_id'],
            channel_id=data['channel_id'],
            type=data['type'],
            initiative_state=initiative_state,  # Now a dict
            is_active=bool(data['is_active']),
            message_id=data.get('message_id')
        )
    
    def _get_initiative_tracker(self, guild_id: str, channel_id: str) -> Optional[InitiativeTracker]:
        """Get initiative tracker for a channel"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND channel_id = %s AND is_active = true"
        return self.execute_query(query, (str(guild_id), str(channel_id)), fetch_one=True)

    def get_active_initiative(self, guild_id: str, channel_id: str) -> Optional[BaseInitiative]:
        """Get initiative for a channel"""
        initiative_tracker = self._get_initiative_tracker(guild_id, channel_id)
        if initiative_tracker:
            InitiativeClass = factories.get_specific_initiative(initiative_tracker.type)
            return InitiativeClass.from_dict(initiative_tracker.initiative_state)
        return None

    def get_initiative_message_id(self, guild_id: str, channel_id: str) -> Optional[str]:
        """Get the message ID for the initiative message"""
        initiative_tracker = self._get_initiative_tracker(guild_id, channel_id)
        return initiative_tracker.message_id if initiative_tracker else None

    def start_initiative(self, guild_id: str, channel_id: str, init_type: str, state: dict, message_id: str = None) -> None:
        """Start initiative in a channel"""
        initiative = InitiativeTracker(
            guild_id=str(guild_id),
            channel_id=str(channel_id),
            type=init_type,
            initiative_state=state,  # Now stored as dict
            is_active=True,
            message_id=str(message_id) if message_id else None
        )
        self.save(initiative, conflict_columns=['guild_id', 'channel_id'])

    def update_initiative_state(self, guild_id: str, channel_id: str, initiative: BaseInitiative) -> None:
        """Update initiative state"""
        query = f"UPDATE {self.table_name} SET initiative_state = %s WHERE guild_id = %s AND channel_id = %s"
        self.execute_query(query, (json.dumps(initiative.to_dict()), str(guild_id), str(channel_id)))
    
    def end_initiative(self, guild_id: str, channel_id: str) -> None:
        """End initiative in a channel"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND channel_id = %s"
        self.execute_query(query, (str(guild_id), str(channel_id)))

    def set_initiative_message_id(self, guild_id: str, channel_id: str, message_id: str) -> None:
        """Store the message ID for the initiative message"""
        query = f"UPDATE {self.table_name} SET message_id = %s WHERE guild_id = %s AND channel_id = %s"
        self.execute_query(query, (str(message_id), str(guild_id), str(channel_id)))

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