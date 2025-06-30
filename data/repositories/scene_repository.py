from typing import List, Optional
from .base_repository import BaseRepository
from data.models import Scene, SceneNPC, PinnedSceneMessage, SceneNotes
import time
import uuid

class SceneRepository(BaseRepository[Scene]):
    def __init__(self):
        super().__init__('scenes')
    
    def to_dict(self, entity: Scene) -> dict:
        return {
            'guild_id': entity.guild_id,
            'scene_id': entity.scene_id,
            'name': entity.name,
            'is_active': entity.is_active,
            'creation_time': entity.creation_time
        }
    
    def from_dict(self, data: dict) -> Scene:
        return Scene(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            name=data['name'],
            is_active=bool(data['is_active']),
            creation_time=data['creation_time']
        )
    
    def create_scene(self, guild_id: str, name: str) -> str:
        """Create a new scene and return its ID"""
        scene_id = str(uuid.uuid4())
        
        # Check if this is the first scene for the guild
        existing_scenes = self.find_all_by_column('guild_id', str(guild_id))
        is_first_scene = len(existing_scenes) == 0
        
        scene = Scene(
            guild_id=str(guild_id),
            scene_id=scene_id,
            name=name,
            is_active=is_first_scene,
            creation_time=time.time()
        )
        
        self.save(scene)
        return scene_id
    
    def get_all_scenes(self, guild_id: str) -> List[Scene]:
        """Get all scenes for a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s ORDER BY creation_time DESC"
        return self.execute_query(query, (str(guild_id),), fetch_all=True)
    
    def get_by_name(self, guild_id: str, name: str) -> Optional[Scene]:
        """Get scene by name within a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND name = %s"
        return self.execute_query(query, (str(guild_id), name), fetch_one=True)
    
    def get_active_scene(self, guild_id: str) -> Optional[Scene]:
        """Get the active scene for a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND is_active = true"
        return self.execute_query(query, (str(guild_id),), fetch_one=True)
    
    def set_active_scene(self, guild_id: str, scene_id: str) -> None:
        """Set a scene as active and deactivate all others"""
        with self.db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                # Deactivate all scenes in guild
                cur.execute(
                    f"UPDATE {self.table_name} SET is_active = false WHERE guild_id = %s",
                    (str(guild_id),)
                )
                # Activate the specified scene
                cur.execute(
                    f"UPDATE {self.table_name} SET is_active = true WHERE guild_id = %s AND scene_id = %s",
                    (str(guild_id), str(scene_id))
                )
    
    def rename_scene(self, guild_id: str, scene_id: str, new_name: str) -> None:
        """Rename a scene"""
        query = f"UPDATE {self.table_name} SET name = %s WHERE guild_id = %s AND scene_id = %s"
        self.execute_query(query, (new_name, str(guild_id), str(scene_id)))
    
    def delete_scene(self, guild_id: str, scene_id: str) -> bool:
        """Delete a scene and return True if successful"""
        deleted_count = self.delete(
            "guild_id = %s AND scene_id = %s",
            (str(guild_id), str(scene_id))
        )
        return deleted_count > 0

class SceneNPCRepository(BaseRepository[SceneNPC]):
    def __init__(self):
        super().__init__('scene_npcs')
    
    def to_dict(self, entity: SceneNPC) -> dict:
        return {
            'guild_id': entity.guild_id,
            'scene_id': entity.scene_id,
            'npc_id': entity.npc_id
        }
    
    def from_dict(self, data: dict) -> SceneNPC:
        return SceneNPC(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            npc_id=data['npc_id']
        )
    
    def get_scene_npc_ids(self, guild_id: str, scene_id: str) -> List[str]:
        """Get all NPC IDs in a scene"""
        scene_npcs = self.find_all_by_column('guild_id', str(guild_id))
        return [snpc.npc_id for snpc in scene_npcs if snpc.scene_id == scene_id]
    
    def add_npc_to_scene(self, guild_id: str, scene_id: str, npc_id: str) -> None:
        """Add an NPC to a scene"""
        scene_npc = SceneNPC(
            guild_id=str(guild_id),
            scene_id=str(scene_id),
            npc_id=str(npc_id)
        )
        self.save(scene_npc, conflict_columns=['guild_id', 'scene_id', 'npc_id'])
    
    def remove_npc_from_scene(self, guild_id: str, scene_id: str, npc_id: str) -> bool:
        """Remove an NPC from a scene"""
        deleted_count = self.delete(
            "guild_id = %s AND scene_id = %s AND npc_id = %s",
            (str(guild_id), str(scene_id), str(npc_id))
        )
        return deleted_count > 0
    
    def get_scene_npcs(self, guild_id: str, scene_name: str = None) -> List[dict]:
        """Get NPCs for a scene - helper method for initiative commands"""
        from .repository_factory import repositories
        
        if scene_name:
            # Get specific scene
            scenes = repositories.scene.find_all_by_column('guild_id', str(guild_id))
            scene = next((s for s in scenes if s.name.lower() == scene_name.lower()), None)
            if not scene:
                return []
            
            # Get NPCs for this scene
            scene_npcs = self.find_all_by_column('scene_id', scene.scene_id)
            npc_ids = [sn.npc_id for sn in scene_npcs]
            
            # Get the actual NPC character objects
            all_chars = repositories.character.find_all_by_column('guild_id', str(guild_id))
            return [c for c in all_chars if c.is_npc and c.id in npc_ids]
        else:
            # Get active scene NPCs
            active_scene = repositories.scene.get_active_scene(str(guild_id))
            if not active_scene:
                return []
            
            scene_npcs = self.find_all_by_column('scene_id', active_scene.scene_id)
            npc_ids = [sn.npc_id for sn in scene_npcs]
            
            all_chars = repositories.character.find_all_by_column('guild_id', str(guild_id))
            return [c for c in all_chars if c.is_npc and c.id in npc_ids]

class PinnedSceneMessageRepository(BaseRepository[PinnedSceneMessage]):
    def __init__(self):
        super().__init__('pinned_scene_messages')
    
    def to_dict(self, entity: PinnedSceneMessage) -> dict:
        return {
            'guild_id': entity.guild_id,
            'scene_id': entity.scene_id,
            'channel_id': entity.channel_id,
            'message_id': entity.message_id
        }
    
    def from_dict(self, data: dict) -> PinnedSceneMessage:
        return PinnedSceneMessage(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            channel_id=data['channel_id'],
            message_id=data['message_id']
        )
    
    def set_pinned_message(self, guild_id: str, scene_id: str, channel_id: str, message_id: str) -> None:
        """Set pinned message for a scene in a channel"""
        pinned_msg = PinnedSceneMessage(
            guild_id=str(guild_id),
            scene_id=str(scene_id),
            channel_id=str(channel_id),
            message_id=str(message_id)
        )
        self.save(pinned_msg, conflict_columns=['guild_id', 'scene_id', 'channel_id'])
    
    def get_scene_message_info(self, guild_id: str, channel_id: str) -> Optional[PinnedSceneMessage]:
        """Get scene message info for a channel"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND channel_id = %s"
        return self.execute_query(query, (str(guild_id), str(channel_id)), fetch_one=True)
    
    def get_all_pinned_messages(self, guild_id: str) -> List[PinnedSceneMessage]:
        """Get all pinned scene messages for a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s ORDER BY scene_id"
        return self.execute_query(query, (str(guild_id),), fetch_all=True)
    
    def clear_all_pins(self, guild_id: str) -> None:
        """Clear all pinned messages for a guild"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s"
        self.execute_query(query, (str(guild_id),))
    
class SceneNotesRepository(BaseRepository[SceneNotes]):
    def __init__(self):
        super().__init__('scene_notes')
    
    def to_dict(self, entity: SceneNotes) -> dict:
        return {
            'guild_id': entity.guild_id,
            'scene_id': entity.scene_id,
            'notes': entity.notes
        }
    
    def from_dict(self, data: dict) -> SceneNotes:
        return SceneNotes(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            notes=data.get('notes', '')
        )
    
    def get_scene_notes(self, guild_id: str, scene_id: str) -> Optional[str]:
        """Get notes for a specific scene"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND scene_id = %s"
        result = self.execute_query(query, (str(guild_id), str(scene_id)), fetch_one=True)
        return result.notes if result else None
    
    def set_scene_notes(self, guild_id: str, scene_id: str, notes: str) -> None:
        """Set or update notes for a scene"""
        scene_notes = SceneNotes(
            guild_id=str(guild_id),
            scene_id=str(scene_id),
            notes=notes
        )
        self.save(scene_notes, conflict_columns=['guild_id', 'scene_id'])
    
    def delete_scene_notes(self, guild_id: str, scene_id: str) -> None:
        """Delete notes for a scene"""
        query = f"DELETE FROM {self.table_name} WHERE guild_id = %s AND scene_id = %s"
        self.execute_query(query, (str(guild_id), str(scene_id)))
    
    def get_all_scene_notes_for_guild(self, guild_id: str) -> list[SceneNotes]:
        """Get all scene notes for a guild"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s ORDER BY scene_id"
        return self.execute_query(query, (str(guild_id),), fetch_all=True)