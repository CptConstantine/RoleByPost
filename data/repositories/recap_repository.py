from typing import Optional, List
from .base_repository import BaseRepository
from data.models import AutoRecapSettings, ApiKey

class AutoRecapRepository(BaseRepository[AutoRecapSettings]):
    def __init__(self):
        super().__init__('auto_recaps')
    
    def to_dict(self, entity: AutoRecapSettings) -> dict:
        return {
            'guild_id': entity.guild_id,
            'enabled': entity.enabled,
            'channel_id': entity.channel_id,
            'days_interval': entity.days_interval,
            'days_to_include': entity.days_to_include,
            'last_recap_time': entity.last_recap_time,
            'paused': entity.paused,
            'check_activity': entity.check_activity
        }
    
    def from_dict(self, data: dict) -> AutoRecapSettings:
        return AutoRecapSettings(
            guild_id=data['guild_id'],
            enabled=bool(data['enabled']),
            channel_id=data.get('channel_id'),
            days_interval=data['days_interval'],
            days_to_include=data['days_to_include'],
            last_recap_time=data.get('last_recap_time'),
            paused=bool(data.get('paused', False)),
            check_activity=bool(data.get('check_activity', True))
        )
    
    def get_settings(self, guild_id: str) -> AutoRecapSettings:
        """Get auto recap settings for a guild"""
        settings = self.find_by_id('guild_id', str(guild_id))
        return settings if settings else AutoRecapSettings(guild_id=str(guild_id))
    
    def update_settings(self, guild_id: str, enabled: bool, channel_id: str = None, 
                       days_interval: int = 7, days_to_include: int = 7) -> None:
        """Update auto recap settings"""
        settings = self.get_settings(guild_id)
        settings.enabled = enabled
        if channel_id:
            settings.channel_id = channel_id
        settings.days_interval = days_interval
        settings.days_to_include = days_to_include
        
        self.save(settings, conflict_columns=['guild_id'])
    
    def update_last_recap_time(self, guild_id: str, timestamp: float) -> None:
        """Update last recap time"""
        query = f"UPDATE {self.table_name} SET last_recap_time = %s WHERE guild_id = %s"
        self.execute_query(query, (timestamp, str(guild_id)))
    
    def update_pause_state(self, guild_id: str, paused: bool) -> None:
        """Update pause state"""
        query = f"UPDATE {self.table_name} SET paused = %s WHERE guild_id = %s"
        self.execute_query(query, (paused, str(guild_id)))
    
    def get_all_enabled_guilds(self) -> List[str]:
        """Get all guild IDs with auto recap enabled"""
        query = f"SELECT * FROM {self.table_name} WHERE enabled = true"
        results = self.execute_query(query)
        return [result.guild_id for result in results]

class ApiKeyRepository(BaseRepository[ApiKey]):
    def __init__(self):
        super().__init__('api_keys')
    
    def to_dict(self, entity: ApiKey) -> dict:
        return {
            'guild_id': entity.guild_id,
            'openai_key': entity.openai_key
        }
    
    def from_dict(self, data: dict) -> ApiKey:
        return ApiKey(
            guild_id=data['guild_id'],
            openai_key=data.get('openai_key')
        )
    
    def get_openai_key(self, guild_id: str) -> Optional[str]:
        """Get OpenAI API key for a guild"""
        api_key = self.find_by_id('guild_id', str(guild_id))
        return api_key.openai_key if api_key else None
    
    def set_openai_key(self, guild_id: str, api_key: str) -> None:
        """Set OpenAI API key for a guild"""
        key_entity = ApiKey(
            guild_id=str(guild_id),
            openai_key=api_key
        )
        self.save(key_entity, conflict_columns=['guild_id'])
    
    def remove_openai_key(self, guild_id: str) -> None:
        """Remove OpenAI API key for a guild"""
        self.delete(F"guild_id = %s", (str(guild_id),))