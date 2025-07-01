from typing import Optional
from .base_repository import BaseRepository
from data.models import ChannelPermission

class ChannelPermissionRepository(BaseRepository[ChannelPermission]):
    def __init__(self):
        super().__init__("channel_permissions")
    
    def to_dict(self, entity: ChannelPermission) -> dict:
        return {
            "guild_id": entity.guild_id,
            "channel_id": entity.channel_id,
            "channel_type": entity.channel_type
        }
    
    def from_dict(self, data: dict) -> ChannelPermission:
        return ChannelPermission(
            guild_id=data["guild_id"],
            channel_id=data["channel_id"],
            channel_type=data["channel_type"]
        )
    
    def set_channel_type(self, guild_id: str, channel_id: str, channel_type: str) -> None:
        """Set the channel type for a specific channel"""
        permission = ChannelPermission(
            guild_id=str(guild_id),
            channel_id=str(channel_id),
            channel_type=channel_type
        )
        self.save(permission, conflict_columns=['guild_id', 'channel_id'])
    
    def get_channel_type(self, guild_id: str, channel_id: str) -> Optional[str]:
        """Get the channel type for a specific channel"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND channel_id = %s"
        result = self.execute_query(query, (str(guild_id), str(channel_id)), fetch_one=True)
        return result.channel_type if result else None

    def remove_channel_permission(self, guild_id: str, channel_id: str) -> None:
        """Remove channel permission (set to unrestricted)"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND channel_id = %s"
        self.execute_query(query, (str(guild_id), str(channel_id)))
    
    def get_all_channel_permissions(self, guild_id: str) -> list[ChannelPermission]:
        """Get all channel permissions for a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s"
        return self.execute_query(query, (str(guild_id),))