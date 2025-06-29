from typing import List, Optional
from .base_repository import BaseRepository
from models import Character, ActiveCharacter
import json
import uuid

class CharacterRepository(BaseRepository[Character]):
    def __init__(self):
        super().__init__('characters')
    
    def to_dict(self, entity: Character) -> dict:
        return {
            'id': entity.id,
            'guild_id': entity.guild_id,
            'name': entity.name,
            'owner_id': entity.owner_id,
            'entity_type': entity.entity_type,
            'system': entity.system,
            'system_specific_data': json.dumps(entity.system_specific_data),
            'notes': json.dumps(entity.notes),
            'avatar_url': entity.avatar_url
        }
    
    def from_dict(self, data: dict) -> Character:
        return Character(
            id=data['id'],
            guild_id=data['guild_id'],
            name=data['name'],
            owner_id=data['owner_id'],
            entity_type=data['entity_type'],
            system=data.get('system'),
            system_specific_data=json.loads(data.get('system_specific_data', '{}')),
            notes=json.loads(data.get('notes', '[]')),
            avatar_url=data.get('avatar_url', '')
        )
    
    def get_by_name(self, guild_id: str, name: str) -> Optional[Character]:
        """Get character by name within a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND name = %s"
        return self.execute_query(query, (str(guild_id), name), fetch_one=True)
    
    def get_all_by_guild(self, guild_id: str, system: str = None) -> List[Character]:
        """Get all characters for a guild, optionally filtered by system"""
        if system:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND system = %s"
            return self.execute_query(query, (str(guild_id), system), fetch_all=True)
        else:
            return self.find_all_by_column('guild_id', str(guild_id))
    
    def get_npcs_by_guild(self, guild_id: str) -> List[Character]:
        """Get all NPCs for a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND entity_type = 'npc'"
        return self.execute_query(query, (str(guild_id),), fetch_all=True)
    
    def get_pcs_by_guild(self, guild_id: str) -> List[Character]:
        """Get all PCs for a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND entity_type = 'pc'"
        return self.execute_query(query, (str(guild_id),), fetch_all=True)
    
    def get_non_gm_active_characters(self, guild_id: str) -> List[Character]:
        """Get active characters excluding GM-owned characters"""
        query = f"""
            SELECT c.* FROM {self.table_name} c
            INNER JOIN active_characters ac ON c.id = ac.char_id
            WHERE c.guild_id = %s AND c.entity_type = 'pc'
        """
        return self.execute_query(query, (str(guild_id),), fetch_all=True)
    
    def upsert_character(self, character: Character) -> None:
        """Save or update a character"""
        self.save(character, conflict_columns=['id'])

class ActiveCharacterRepository(BaseRepository[ActiveCharacter]):
    def __init__(self):
        super().__init__('active_characters')
    
    def to_dict(self, entity: ActiveCharacter) -> dict:
        return {
            'guild_id': entity.guild_id,
            'user_id': entity.user_id,
            'char_id': entity.char_id
        }
    
    def from_dict(self, data: dict) -> ActiveCharacter:
        return ActiveCharacter(
            guild_id=data['guild_id'],
            user_id=data['user_id'],
            char_id=data['char_id']
        )
    
    def get_active_character(self, guild_id: str, user_id: str) -> Optional[ActiveCharacter]:
        """Get active character for a user in a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND user_id = %s"
        return self.execute_query(query, (str(guild_id), str(user_id)), fetch_one=True)
    
    def set_active_character(self, guild_id: str, user_id: str, char_id: str) -> None:
        """Set active character for a user"""
        active_char = ActiveCharacter(
            guild_id=str(guild_id),
            user_id=str(user_id),
            char_id=str(char_id)
        )
        self.save(active_char, conflict_columns=['guild_id', 'user_id'])