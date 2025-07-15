from typing import List, Optional
from .base_repository import BaseRepository
from data.models import Character, ActiveCharacter
from core.base_models import AccessType, BaseCharacter, BaseEntity, EntityJSONEncoder, EntityType, SystemType
import json
import core.factories as factories

class CharacterRepository(BaseRepository[Character]):
    def __init__(self):
        super().__init__('entities')  # Use entities table instead of characters
    
    def to_dict(self, entity: Character) -> dict:
        return {
            'id': entity.id,
            'guild_id': entity.guild_id,
            'name': entity.name,
            'owner_id': entity.owner_id,
            'entity_type': entity.entity_type,
            'system': entity.system,
            'system_specific_data': json.dumps(entity.system_specific_data, cls=EntityJSONEncoder),
            'notes': json.dumps(entity.notes),
            'avatar_url': entity.avatar_url,
            'access_type': entity.access_type
        }

    def from_dict(self, data: dict) -> Character:
        # Handle system_specific_data - it might already be parsed or still be a string
        system_specific_data = data.get('system_specific_data', '{}')
        if isinstance(system_specific_data, str):
            system_specific_data = json.loads(system_specific_data)
        elif system_specific_data is None:
            system_specific_data = {}
        
        # Handle notes - it might already be parsed or still be a string
        notes = data.get('notes', '[]')
        if isinstance(notes, str):
            notes = json.loads(notes)
        elif notes is None:
            notes = []
        
        return Character(
            id=data['id'],
            guild_id=data['guild_id'],
            name=data['name'],
            owner_id=data['owner_id'],
            entity_type=data['entity_type'],
            system=data.get('system'),
            system_specific_data=system_specific_data,
            notes=notes,
            access_type=data.get('access_type', 'public'),
            avatar_url=data.get('avatar_url', '')
        )

    def _convert_to_base_character(self, character: Character) -> BaseCharacter:
        """Convert a Character entity to a system-specific BaseCharacter"""
        if not character:
            return None
            
        # Get the system-specific character class
        CharacterClass = factories.get_specific_character(SystemType(character.system), EntityType(character.entity_type))

        # Create the character dict using the helper method
        character_dict = BaseEntity.build_entity_dict(
            id=character.id,
            name=character.name,
            owner_id=character.owner_id,
            system=SystemType(character.system),
            entity_type=EntityType(character.entity_type),
            notes=character.notes,
            avatar_url=character.avatar_url,
            access_type=AccessType(character.access_type),
            system_specific_fields=character.system_specific_data
        )
        
        return CharacterClass.from_dict(character_dict)

    def _convert_list_to_base_characters(self, characters: List[Character]) -> List[BaseCharacter]:
        """Convert a list of Character entities to BaseCharacter objects"""
        return [self._convert_to_base_character(char) for char in characters if char]

    def get_by_id(self, id: str) -> Optional[BaseCharacter]:
        """Get character by ID"""
        query = f"SELECT * FROM {self.table_name} WHERE id = %s"
        character = self.execute_query(query, (str(id),), fetch_one=True)
        return self._convert_to_base_character(character)

    def get_by_name(self, guild_id: str, name: str) -> Optional[BaseCharacter]:
        """Get character by name within a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND name = %s"
        character = self.execute_query(query, (str(guild_id), name), fetch_one=True)
        return self._convert_to_base_character(character)

    def get_all_by_guild(self, guild_id: str, system: SystemType = None) -> List[BaseCharacter]:
        """Get all characters for a guild, optionally filtered by system"""
        if system:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND system = %s AND entity_type in ('pc', 'npc') ORDER BY name"
            characters = self.execute_query(query, (str(guild_id), system.value))
        else:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND entity_type in ('pc', 'npc') ORDER BY name"
            characters = self.execute_query(query, (str(guild_id),))
        return self._convert_list_to_base_characters(characters)

    def get_user_characters(self, guild_id: int, user_id: int, include_npcs: bool = False) -> List[BaseCharacter]:
        """Get all characters owned by a user"""
        if include_npcs:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND owner_id = %s AND entity_type in ('pc', 'npc', 'companion') ORDER BY name"
        else:
            query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND owner_id = %s AND entity_type in ('pc', 'companion') ORDER BY name"
        
        characters = self.execute_query(query, (str(guild_id), str(user_id)))
        return self._convert_list_to_base_characters(characters)
    
    def get_accessible_characters(self, guild_id: int, user_id: int) -> List[BaseCharacter]:
        """Get all characters accessible to a user, including public and owned characters"""
        # Get all characters and companions that are public or in the scene
        all_chars = self.get_all_by_guild(str(guild_id))
        public_chars = [char for char in all_chars if char.access_type == AccessType.PUBLIC]

        # Get user's own characters
        user_chars = self.get_user_characters(guild_id, user_id, include_npcs=True)
        
        # Combine and remove duplicates
        accessible_chars = {char.id: char for char in public_chars + user_chars}
        
        return list(accessible_chars.values())

    def get_npcs(self, guild_id: int) -> List[BaseCharacter]:
        """Get all NPCs in a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND entity_type = 'npc' ORDER BY name"
        characters = self.execute_query(query, (str(guild_id),))
        return self._convert_list_to_base_characters(characters)

    def upsert_character(self, guild_id, character: BaseCharacter, system: SystemType) -> None:
        """Save or update a BaseCharacter by converting it to Character first"""
        CharacterClass = factories.get_specific_character(system, character.entity_type)

        # Use the system's defined fields
        system_fields = CharacterClass.ENTITY_DEFAULTS.get_defaults(character.entity_type)

        system_specific_data = {}
        for key in system_fields:
            system_specific_data[key] = character.data.get(key)

        notes = character.notes or []
        
        # Create Character entity from BaseCharacter
        storage_character = Character(
            id=character.id,
            guild_id=str(guild_id),
            name=character.name,
            owner_id=character.owner_id,
            entity_type='npc' if character.is_npc else 'pc',
            system=system,
            system_specific_data=system_specific_data,
            notes=notes,
            avatar_url=character.avatar_url
        )
        
        self.save(storage_character, conflict_columns=['id'])

    def delete_character(self, guild_id: str, character_id: str) -> None:
        """Delete a character and all its links"""
        # Get the character to find its guild_id
        character = self.get_by_id(character_id)
        if character:
            # Delete all links involving this character
            from .repository_factory import repositories
            repositories.link.delete_all_links_for_entity(str(guild_id), character_id)
            
        # Delete the character itself
        query = f"DELETE FROM {self.table_name} WHERE id = %s"
        self.execute_query(query, (character_id,))

    def get_character_by_name(self, guild_id: int, name: str) -> Optional[BaseCharacter]:
        """Alias for get_by_name for backward compatibility"""
        return self.get_by_name(str(guild_id), name)

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

    def _convert_to_base_character(self, character: Character) -> BaseCharacter:
        """Convert a Character entity to a system-specific BaseCharacter"""
        if not character:
            return None
            
        # Get the system-specific character class
        CharacterClass = factories.get_specific_character(SystemType(character.system), EntityType(character.entity_type))

        # Create the character dict using the helper method
        character_dict = BaseEntity.build_entity_dict(
            id=character.id,
            name=character.name,
            owner_id=character.owner_id,
            system=SystemType(character.system),
            entity_type=EntityType.get_type_from_str(character.entity_type),
            notes=character.notes,
            avatar_url=character.avatar_url,
            access_type=AccessType(character.access_type),
            system_specific_fields=character.system_specific_data
        )
        
        return CharacterClass.from_dict(character_dict)
    
    def get_active_character_record(self, guild_id: int, user_id: int) -> Optional[ActiveCharacter]:
        """Get active character record for a user"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND user_id = %s"
        return self.execute_query(query, (str(guild_id), str(user_id)), fetch_one=True)
    
    def get_active_character(self, guild_id: int, user_id: int) -> Optional[BaseCharacter]:
        """Get user's active character object as BaseCharacter"""
        from .repository_factory import repositories
        
        active_record = self.get_active_character_record(guild_id, user_id)
        if active_record:
            # Use find_all_by_column to get Character, then convert
            return repositories.entity.get_by_id(active_record.char_id)
        return None
    
    def get_all_active_characters(self, guild_id: int) -> List[BaseCharacter]:
        """Get all active characters in a guild"""
        from .repository_factory import repositories
        
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s"
        active_records = self.execute_query(query, (str(guild_id),))
        
        active_characters = []
        for record in active_records:
            character = repositories.entity.get_by_id(record.char_id)
            if character:
                active_characters.append(character)
        
        return active_characters
    
    def set_active_character(self, guild_id: str, user_id: str, character_id: str) -> None:
        """Set a user's active character"""
        active_char = ActiveCharacter(
            guild_id=guild_id,
            user_id=user_id,
            char_id=character_id
        )
        self.save(active_char, conflict_columns=['guild_id', 'user_id'])
    
    def clear_active_character(self, guild_id: int, user_id: int) -> None:
        """Clear a user's active character"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND user_id = %s"
        self.execute_query(query, (str(guild_id), str(user_id)))