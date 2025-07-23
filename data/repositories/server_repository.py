from typing import Optional
import json

from core.base_models import SystemType
from .base_repository import BaseRepository
from data.models import ServerSettings
import discord

class ServerRepository(BaseRepository[ServerSettings]):
    def __init__(self):
        super().__init__('server_settings')
    
    def to_dict(self, entity: ServerSettings) -> dict:
        return {
            'guild_id': entity.guild_id,
            'system': entity.system,
            'gm_role_id': entity.gm_role_id,
            'player_role_id': entity.player_role_id,
            'generic_base_roll': entity.generic_base_roll,
            'core_roll_mechanic': json.dumps(entity.core_roll_mechanic) if entity.core_roll_mechanic else None
        }
    
    def from_dict(self, data: dict) -> ServerSettings:
        core_roll_mechanic = None
        if data.get('core_roll_mechanic'):
            if isinstance(data['core_roll_mechanic'], str):
                core_roll_mechanic = json.loads(data['core_roll_mechanic'])
            else:
                core_roll_mechanic = data['core_roll_mechanic']
        
        return ServerSettings(
            guild_id=data['guild_id'],
            system=data.get('system', 'generic'),
            gm_role_id=data.get('gm_role_id'),
            player_role_id=data.get('player_role_id'),
            generic_base_roll=data.get('generic_base_roll'),
            core_roll_mechanic=core_roll_mechanic
        )
    
    def get_by_guild_id(self, guild_id: str) -> Optional[ServerSettings]:
        """Get server settings by guild ID"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s"
        return self.execute_query(query, (str(guild_id),), fetch_one=True)
    
    def get_system(self, guild_id: int) -> SystemType:
        """Get the RPG system for a guild"""
        server = self.get_by_guild_id(str(guild_id))
        return SystemType(server.system) if server and server.system else SystemType.GENERIC

    async def has_gm_permission(self, guild_id: int, user: discord.Member) -> bool:
        """Check if user has GM permissions"""
        server_settings = self.get_by_guild_id(str(guild_id))
        if server_settings and server_settings.gm_role_id:
            gm_role = user.guild.get_role(int(server_settings.gm_role_id))
            if gm_role and gm_role in user.roles:
                return True
        
        return False
    
    async def has_player_or_gm_permission(self, guild_id: int, user: discord.Member) -> bool:
        """Check if user has player or GM permissions"""
        server_settings = self.get_by_guild_id(str(guild_id))
        if server_settings:
            player_role = user.guild.get_role(int(server_settings.player_role_id)) if server_settings.player_role_id else None
            gm_role = user.guild.get_role(int(server_settings.gm_role_id)) if server_settings.gm_role_id else None
            
            if (player_role and player_role in user.roles) or (gm_role and gm_role in user.roles):
                return True
        
        return False
    
    def set_system(self, guild_id: str, system: SystemType) -> None:
        """Set the RPG system for a server"""
        server = self.get_by_guild_id(guild_id)
        if server:
            server.system = system.value
        else:
            server = ServerSettings(guild_id=guild_id, system=system.value)
        self.save(server, conflict_columns=['guild_id'])
    
    def get_gm_role_id(self, guild_id: int) -> Optional[str]:
        """Get GM role ID for a guild"""
        server = self.get_by_guild_id(str(guild_id))
        return server.gm_role_id if server else None
    
    def set_gm_role(self, guild_id: int, role_id: int) -> None:
        """Set GM role for a guild"""
        server = self.get_by_guild_id(str(guild_id)) or ServerSettings(guild_id=str(guild_id))
        server.gm_role_id = str(role_id)
        self.save(server, conflict_columns=['guild_id'])
    
    def get_player_role_id(self, guild_id: int) -> Optional[str]:
        """Get player role ID for a guild"""
        server = self.get_by_guild_id(str(guild_id))
        return server.player_role_id if server else None
    
    def set_player_role(self, guild_id: int, role_id: int) -> None:
        """Set player role for a guild"""
        server = self.get_by_guild_id(str(guild_id)) or ServerSettings(guild_id=str(guild_id))
        server.player_role_id = str(role_id)
        self.save(server, conflict_columns=['guild_id'])

    def get_generic_base_roll(self, guild_id: int) -> Optional[int]:
        """Get the generic base roll for a guild"""
        server = self.get_by_guild_id(str(guild_id))
        return server.generic_base_roll if server else None
    
    def set_generic_base_roll(self, guild_id: int, base_roll: str) -> None:
        """Set the generic base roll for a guild"""
        server = self.get_by_guild_id(str(guild_id)) or ServerSettings(guild_id=str(guild_id))
        server.generic_base_roll = base_roll
        self.save(server, conflict_columns=['guild_id'])

    def get_core_roll_mechanic(self, guild_id: str) -> Optional[dict]:
        """Get the core roll mechanic configuration for a guild"""
        server = self.get_by_guild_id(guild_id)
        return server.core_roll_mechanic if server else None
    
    def set_core_roll_mechanic(self, guild_id: str, config: dict) -> None:
        """Set the core roll mechanic configuration for a guild"""
        # Get existing server settings or create defaults
        server = self.get_by_guild_id(guild_id)
        if not server:
            server = ServerSettings(
                guild_id=guild_id,
                system='generic',
                gm_role_id=None,
                player_role_id=None,
                generic_base_roll=None,
                core_roll_mechanic=config
            )
        else:
            server.core_roll_mechanic = config
        
        # Save with conflict resolution on guild_id
        self.save(server, conflict_columns=['guild_id'])