from typing import Optional
from .base_repository import BaseRepository
from data.models import StickyNarration


class StickyNarrationRepository(BaseRepository[StickyNarration]):
    def __init__(self):
        super().__init__('sticky_narration')

    def to_dict(self, entity: StickyNarration) -> dict:
        return {
            'guild_id': entity.guild_id,
            'user_id': entity.user_id,
            'channel_id': entity.channel_id,
            'character_id': entity.character_id
        }

    def from_dict(self, data: dict) -> StickyNarration:
        return StickyNarration(
            guild_id=data['guild_id'],
            user_id=data['user_id'],
            channel_id=data['channel_id'],
            character_id=data['character_id']
        )

    def set_sticky_character(self, guild_id: str, user_id: str, channel_id: str, character_id: str) -> None:
        """Set or update sticky character for a user in a specific channel"""
        sticky_narration = StickyNarration(
            guild_id=str(guild_id),
            user_id=str(user_id),
            channel_id=str(channel_id),
            character_id=character_id
        )
        self.save(sticky_narration, conflict_columns=['guild_id', 'user_id', 'channel_id'])

    def clear_sticky_character(self, guild_id: str, user_id: str, channel_id: str) -> bool:
        """Clear sticky character for a user in a specific channel"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND user_id = %s AND channel_id = %s"
        deleted_count = self.execute_query(query, (str(guild_id), str(user_id), str(channel_id)))
        return deleted_count is not None

    def get_sticky_character(self, guild_id: str, user_id: str, channel_id: str) -> Optional[str]:
        """Get sticky character id for a user in a specific channel"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND user_id = %s AND channel_id = %s"
        result = self.execute_query(query, (str(guild_id), str(user_id), str(channel_id)), fetch_one=True)
        return result.character_id if result else None

    def get_all_sticky_characters_for_user(self, guild_id: str, user_id: str) -> list[StickyNarration]:
        """Get all sticky characters for a user across all channels in a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND user_id = %s"
        return self.execute_query(query, (str(guild_id), str(user_id)))

    def clear_all_sticky_characters_for_user(self, guild_id: str, user_id: str) -> bool:
        """Clear all sticky characters for a user in a guild"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND user_id = %s"
        deleted_count = self.execute_query(query, (str(guild_id), str(user_id)))
        return deleted_count is not None