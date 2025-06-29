from typing import List, Optional, Dict, Any
from .base_repository import BaseRepository
from models import FateSceneAspects, FateSceneZones, MGT2ESceneEnvironment, DefaultSkills
import json

class FateSceneAspectsRepository(BaseRepository[FateSceneAspects]):
    def __init__(self):
        super().__init__('fate_scene_aspects')
    
    def to_dict(self, entity: FateSceneAspects) -> dict:
        return {
            'guild_id': entity.guild_id,
            'scene_id': entity.scene_id,
            'aspects': json.dumps(entity.aspects)
        }
    
    def from_dict(self, data: dict) -> FateSceneAspects:
        return FateSceneAspects(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            aspects=json.loads(data.get('aspects', '[]'))
        )
    
    def get_aspects(self, guild_id: str, scene_id: str) -> List[Dict[str, Any]]:
        """Get aspects for a Fate scene"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND scene_id = %s"
        result = self.execute_query(query, (str(guild_id), str(scene_id)), fetch_one=True)
        return result.aspects if result else []
    
    def set_aspects(self, guild_id: str, scene_id: str, aspects: List[Dict[str, Any]]) -> None:
        """Set aspects for a Fate scene"""
        fate_aspects = FateSceneAspects(
            guild_id=str(guild_id),
            scene_id=str(scene_id),
            aspects=aspects
        )
        self.save(fate_aspects, conflict_columns=['guild_id', 'scene_id'])

class FateSceneZonesRepository(BaseRepository[FateSceneZones]):
    def __init__(self):
        super().__init__('fate_scene_zones')
    
    def to_dict(self, entity: FateSceneZones) -> dict:
        return {
            'guild_id': entity.guild_id,
            'scene_id': entity.scene_id,
            'zones': json.dumps(entity.zones)
        }
    
    def from_dict(self, data: dict) -> FateSceneZones:
        return FateSceneZones(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            zones=json.loads(data.get('zones', '[]'))
        )
    
    def get_zones(self, guild_id: str, scene_id: str) -> List[str]:
        """Get zones for a Fate scene"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND scene_id = %s"
        result = self.execute_query(query, (str(guild_id), str(scene_id)), fetch_one=True)
        return result.zones if result else []
    
    def set_zones(self, guild_id: str, scene_id: str, zones: List[str]) -> None:
        """Set zones for a Fate scene"""
        fate_zones = FateSceneZones(
            guild_id=str(guild_id),
            scene_id=str(scene_id),
            zones=zones
        )
        self.save(fate_zones, conflict_columns=['guild_id', 'scene_id'])

class MGT2ESceneEnvironmentRepository(BaseRepository[MGT2ESceneEnvironment]):
    def __init__(self):
        super().__init__('mgt2e_scene_environment')
    
    def to_dict(self, entity: MGT2ESceneEnvironment) -> dict:
        return {
            'guild_id': entity.guild_id,
            'scene_id': entity.scene_id,
            'environment': json.dumps(entity.environment)
        }
    
    def from_dict(self, data: dict) -> MGT2ESceneEnvironment:
        return MGT2ESceneEnvironment(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            environment=json.loads(data.get('environment', '{}'))
        )
    
    def get_environment(self, guild_id: str, scene_id: str) -> Dict[str, str]:
        """Get environment for an MGT2E scene"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND scene_id = %s"
        result = self.execute_query(query, (str(guild_id), str(scene_id)), fetch_one=True)
        return result.environment if result else {}
    
    def set_environment(self, guild_id: str, scene_id: str, environment: Dict[str, str]) -> None:
        """Set environment for an MGT2E scene"""
        mgt2e_env = MGT2ESceneEnvironment(
            guild_id=str(guild_id),
            scene_id=str(scene_id),
            environment=environment
        )
        self.save(mgt2e_env, conflict_columns=['guild_id', 'scene_id'])

class DefaultSkillsRepository(BaseRepository[DefaultSkills]):
    def __init__(self):
        super().__init__('default_skills')
    
    def to_dict(self, entity: DefaultSkills) -> dict:
        return {
            'guild_id': entity.guild_id,
            'system': entity.system,
            'skills_json': json.dumps(entity.skills_json)
        }
    
    def from_dict(self, data: dict) -> DefaultSkills:
        return DefaultSkills(
            guild_id=data['guild_id'],
            system=data['system'],
            skills_json=json.loads(data['skills_json'])
        )
    
    def get_default_skills(self, guild_id: str, system: str) -> Optional[Dict[str, Any]]:
        """Get default skills for a guild and system"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND system = %s"
        result = self.execute_query(query, (str(guild_id), system), fetch_one=True)
        return result.skills_json if result else None
    
    def set_default_skills(self, guild_id: str, system: str, skills: Dict[str, Any]) -> None:
        """Set default skills for a guild and system"""
        default_skills = DefaultSkills(
            guild_id=str(guild_id),
            system=system,
            skills_json=skills
        )
        self.save(default_skills, conflict_columns=['guild_id', 'system'])