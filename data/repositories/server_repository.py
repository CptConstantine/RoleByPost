from typing import Optional
from .base_repository import BaseRepository
from models import ServerSettings

class ServerRepository(BaseRepository[ServerSettings]):
    def __init__(self):
        super().__init__('server_settings')
    
    def to_dict(self, entity: ServerSettings) -> dict:
        return {
            'guild_id': entity.guild_id,
            'system': entity.system,
            'gm_role_id': entity.gm_role_id,
            'player_role_id': entity.player_role_id
        }
    
    def from_dict(self, data: dict) -> ServerSettings:
        return ServerSettings(
            guild_id=data['guild_id'],
            system=data.get('system'),
            gm_role_id=data.get('gm_role_id'),
            player_role_id=data.get('player_role_id')
        )
    
    def get_by_guild_id(self, guild_id: str) -> Optional[ServerSettings]:
        return self.find_by_id('guild_id', str(guild_id))
    
    def upsert(self, settings: ServerSettings) -> None:
        self.save(settings, conflict_columns=['guild_id'])
    
    def set_system(self, guild_id: str, system: str) -> None:
        # Get existing settings or create new
        settings = self.get_by_guild_id(guild_id) or ServerSettings(guild_id=str(guild_id))
        settings.system = system
        self.upsert(settings)
    
    def set_gm_role(self, guild_id: str, role_id: str) -> None:
        settings = self.get_by_guild_id(guild_id) or ServerSettings(guild_id=str(guild_id))
        settings.gm_role_id = str(role_id)
        self.upsert(settings)
    
    def set_player_role(self, guild_id: str, role_id: str) -> None:
        settings = self.get_by_guild_id(guild_id) or ServerSettings(guild_id=str(guild_id))
        settings.player_role_id = str(role_id)
        self.upsert(settings)