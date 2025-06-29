from typing import Optional
from .base_repository import BaseRepository
from models import Reminder, AutoReminderSettings, AutoReminderOptout, LastMessageTime

class ReminderRepository(BaseRepository[Reminder]):
    def __init__(self):
        super().__init__('reminders')
    
    def to_dict(self, entity: Reminder) -> dict:
        return {
            'guild_id': entity.guild_id,
            'user_id': entity.user_id,
            'timestamp': entity.timestamp
        }
    
    def from_dict(self, data: dict) -> Reminder:
        return Reminder(
            guild_id=data['guild_id'],
            user_id=data['user_id'],
            timestamp=data['timestamp']
        )
    
    def set_reminder_time(self, guild_id: str, user_id: str, timestamp: float) -> None:
        """Set reminder time for a user"""
        reminder = Reminder(
            guild_id=str(guild_id),
            user_id=str(user_id),
            timestamp=timestamp
        )
        self.save(reminder, conflict_columns=['guild_id', 'user_id'])

class AutoReminderSettingsRepository(BaseRepository[AutoReminderSettings]):
    def __init__(self):
        super().__init__('auto_reminder_settings')
    
    def to_dict(self, entity: AutoReminderSettings) -> dict:
        return {
            'guild_id': entity.guild_id,
            'enabled': entity.enabled,
            'delay_seconds': entity.delay_seconds
        }
    
    def from_dict(self, data: dict) -> AutoReminderSettings:
        return AutoReminderSettings(
            guild_id=data['guild_id'],
            enabled=bool(data['enabled']),
            delay_seconds=data['delay_seconds']
        )
    
    def get_settings(self, guild_id: str) -> AutoReminderSettings:
        """Get auto reminder settings for a guild"""
        settings = self.find_by_id('guild_id', str(guild_id))
        return settings if settings else AutoReminderSettings(guild_id=str(guild_id))
    
    def update_settings(self, guild_id: str, enabled: bool, delay_seconds: int) -> None:
        """Update auto reminder settings"""
        settings = AutoReminderSettings(
            guild_id=str(guild_id),
            enabled=enabled,
            delay_seconds=delay_seconds
        )
        self.save(settings, conflict_columns=['guild_id'])

class AutoReminderOptoutRepository(BaseRepository[AutoReminderOptout]):
    def __init__(self):
        super().__init__('auto_reminder_optouts')
    
    def to_dict(self, entity: AutoReminderOptout) -> dict:
        return {
            'guild_id': entity.guild_id,
            'user_id': entity.user_id,
            'opted_out': entity.opted_out
        }
    
    def from_dict(self, data: dict) -> AutoReminderOptout:
        return AutoReminderOptout(
            guild_id=data['guild_id'],
            user_id=data['user_id'],
            opted_out=bool(data['opted_out'])
        )
    
    def is_user_opted_out(self, guild_id: str, user_id: str) -> bool:
        """Check if user is opted out of auto reminders"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND user_id = %s"
        optout = self.execute_query(query, (str(guild_id), str(user_id)), fetch_one=True)
        return optout.opted_out if optout else False
    
    def set_user_optout(self, guild_id: str, user_id: str, opted_out: bool) -> None:
        """Set user optout status"""
        optout = AutoReminderOptout(
            guild_id=str(guild_id),
            user_id=str(user_id),
            opted_out=opted_out
        )
        self.save(optout, conflict_columns=['guild_id', 'user_id'])

class LastMessageTimeRepository(BaseRepository[LastMessageTime]):
    def __init__(self):
        super().__init__('last_message_times')
    
    def to_dict(self, entity: LastMessageTime) -> dict:
        return {
            'guild_id': entity.guild_id,
            'user_id': entity.user_id,
            'timestamp': entity.timestamp
        }
    
    def from_dict(self, data: dict) -> LastMessageTime:
        return LastMessageTime(
            guild_id=data['guild_id'],
            user_id=data['user_id'],
            timestamp=data['timestamp']
        )
    
    def update_last_message_time(self, guild_id: str, user_id: str, timestamp: float) -> None:
        """Update last message time for a user"""
        last_msg = LastMessageTime(
            guild_id=str(guild_id),
            user_id=str(user_id),
            timestamp=timestamp
        )
        self.save(last_msg, conflict_columns=['guild_id', 'user_id'])
    
    def get_last_message_time(self, guild_id: str, user_id: str) -> Optional[float]:
        """Get last message time for a user"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND user_id = %s"
        last_msg = self.execute_query(query, (str(guild_id), str(user_id)), fetch_one=True)
        return last_msg.timestamp if last_msg else None