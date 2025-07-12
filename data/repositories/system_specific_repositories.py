from dataclasses import asdict
from typing import List, Optional, Dict, Any
from core.base_models import SystemType
from rpg_systems.fate.aspect import Aspect, AspectType
from .base_repository import BaseRepository
from data.models import FateSceneAspects, FateSceneZones, GameAspect, MGT2ESceneEnvironment, DefaultSkills, ZoneAspect
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
    
    def from_dict(self, data: dict) -> Optional[FateSceneAspects]:
        """Convert database row to FateSceneAspects entity"""
        if not data:
            return None
        
        aspects_data = data.get('aspects', [])
        
        # Handle both cases: JSON string and already parsed list
        if isinstance(aspects_data, str):
            aspects = json.loads(aspects_data)
        elif isinstance(aspects_data, list):
            aspects = aspects_data
        else:
            aspects = []
        
        return FateSceneAspects(
            guild_id=data.get('guild_id'),
            scene_id=data.get('scene_id'),
            aspects=aspects
        )
    
    def get_aspects(self, guild_id: str, scene_id: str) -> List[Aspect]:
        """Get aspects for a Fate scene"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND scene_id = %s"
        result = self.execute_query(query, (str(guild_id), str(scene_id)), fetch_one=True)
        
        # Convert dict data to Aspect objects
        scene_aspects = []
        if result and result.aspects:
            for aspect in result.aspects:
                scene_aspects.append(Aspect.from_dict(aspect))

        return scene_aspects
    
    def set_aspects(self, guild_id: str, scene_id: str, aspects: List[Aspect]) -> None:
        """Set aspects for a Fate scene"""
        fate_aspects = FateSceneAspects(
            guild_id=str(guild_id),
            scene_id=str(scene_id),
            aspects=[aspect.to_dict() for aspect in aspects]
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
        zones_data = data.get('zones', [])
        
        # Handle both cases: JSON string and already parsed list
        if isinstance(zones_data, str):
            zones = json.loads(zones_data)
        elif isinstance(zones_data, list):
            zones = zones_data
        else:
            zones = []
            
        return FateSceneZones(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            zones=zones
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
        environment_data = data.get('environment', {})
        
        # Handle both cases: JSON string and already parsed dict
        if isinstance(environment_data, str):
            environment = json.loads(environment_data)
        elif isinstance(environment_data, dict):
            environment = environment_data
        else:
            environment = {}
            
        return MGT2ESceneEnvironment(
            guild_id=data['guild_id'],
            scene_id=data['scene_id'],
            environment=environment
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
        skills_data = data.get('skills_json', {})
        
        # Handle both cases: JSON string and already parsed dict
        if isinstance(skills_data, str):
            skills_json = json.loads(skills_data)
        elif isinstance(skills_data, dict):
            skills_json = skills_data
        else:
            skills_json = {}
            
        return DefaultSkills(
            guild_id=data['guild_id'],
            system=data['system'],
            skills_json=skills_json
        )
    
    def get_default_skills(self, guild_id: str, system: SystemType) -> Optional[Dict[str, Any]]:
        """Get default skills for a guild and system"""
        query = f"SELECT * FROM {self.table_name} WHERE guild_id = %s AND system = %s"
        result = self.execute_query(query, (str(guild_id), system), fetch_one=True)
        return result.skills_json if result else None
    
    def set_default_skills(self, guild_id: str, system: SystemType, skills: Dict[str, Any]) -> None:
        """Set default skills for a guild and system"""
        default_skills = DefaultSkills(
            guild_id=str(guild_id),
            system=system.value,
            skills_json=skills
        )
        self.save(default_skills, conflict_columns=['guild_id', 'system'])

class FateGameAspectsRepository(BaseRepository[GameAspect]):
    def __init__(self):
        super().__init__('game_aspects')
        
    def to_dict(self, entity: GameAspect) -> dict:
        return {
            'guild_id': entity.guild_id,
            'aspect_name': entity.aspect_name,
            'aspect': json.dumps(entity.aspect) if isinstance(entity.aspect, dict) else entity.aspect
        }
    
    def from_dict(self, data: dict) -> Optional[GameAspect]:
        if not data:
            return None
        
        aspect_data = data.get('aspect', None)

        if isinstance(aspect_data, str):
            aspect_data = json.loads(aspect_data)
        
        return GameAspect(
            guild_id=data.get('guild_id'),
            aspect_name=data.get('aspect_name'),
            aspect=aspect_data
        )

    def get_game_aspects(self, guild_id: str) -> List[Aspect]:
        query = f"SELECT aspect_name, aspect FROM fate_game_aspects WHERE guild_id = %s"
        params = (str(guild_id),)

        rows = self.execute_query(query, params)
        return [Aspect.from_dict(row.aspect) for row in rows if row]

    def set_game_aspect(self, guild_id: str, aspect: Aspect):
        """Set game aspect, replacing existing one with same name."""
        aspect.aspect_type = AspectType.GAME
        game_aspect = GameAspect(
            guild_id=guild_id,
            aspect_name=aspect.name,
            aspect=aspect.to_dict()
        )
        self.save(game_aspect, conflict_columns=['guild_id', 'aspect_name'])
        
    def clear_game_aspects(self, guild_id: str):
        """Clear all game aspects for a guild."""
        self.delete(f"guild_id = %s", (str(guild_id),))

class FateZoneAspectsRepository(BaseRepository[ZoneAspect]):
    def __init__(self):
        super().__init__('zone_aspects')
    
    def to_dict(self, entity: ZoneAspect) -> dict:
        return {
            'guild_id': entity.guild_id,
            'scene_id': entity.scene_id,
            'zone_name': entity.zone_name,
            'aspect_name': entity.aspect_name,
            'aspect': json.dumps(entity.aspect) if isinstance(entity.aspect, dict) else entity.aspect
        }
    
    def from_dict(self, data: dict) -> Optional[ZoneAspect]:
        if not data:
            return None
        
        aspect_data = data.get('aspect', None)

        if isinstance(aspect_data, str):
            aspect_data = json.loads(aspect_data)
        
        return ZoneAspect(
            guild_id=data.get('guild_id'),
            scene_id=data.get('scene_id'),
            zone_name=data.get('zone_name'),
            aspect_name=data.get('aspect_name'),
            aspect=aspect_data
        )

    def get_zone_aspects(self, guild_id: str, scene_id: str, zone_name: str) -> List[Aspect]:
        """Get aspects for a specific zone."""
        query = f"SELECT aspect FROM fate_zone_aspects WHERE guild_id = %s AND scene_id = %s AND zone_name = %s"
        params = (str(guild_id), str(scene_id), str(zone_name))

        rows = self.execute_query(query, params)
        return [Aspect.from_dict(row.aspect) for row in rows if row]
    
    def set_zone_aspect(self, guild_id: str, scene_id: str, zone_name: str, aspect: Aspect):
        """Set aspect for a zone"""
        aspect.aspect_type = AspectType.ZONE
        zone_aspect = ZoneAspect(
            guild_id=guild_id,
            scene_id=scene_id,
            zone_name=zone_name,
            aspect_name=aspect.name,
            aspect=aspect.to_dict()  # Keep as dict for ZoneAspect model
        )
        self.save(zone_aspect, conflict_columns=['guild_id', 'scene_id', 'zone_name', 'aspect_name'])

    def get_all_zone_aspects_for_scene(self, guild_id: str, scene_id: str) -> Dict[str, List[Aspect]]:
        """Get all zone aspects for a scene, organized by zone name."""
        query = f"SELECT zone_name, aspect FROM fate_zone_aspects WHERE guild_id = %s AND scene_id = %s"
        params = (str(guild_id), str(scene_id))

        rows = self.execute_query(query, params)
        zone_aspects: Dict[str, List[Aspect]] = {}

        for row in rows:
            if row and hasattr(row, 'zone_name') and hasattr(row, 'aspect'):
                zone_name = row.zone_name
                aspect_data = row.aspect
                if isinstance(aspect_data, str):
                    aspect_data = json.loads(aspect_data)
                aspect = Aspect.from_dict(aspect_data)

                if zone_name not in zone_aspects:
                    zone_aspects[zone_name] = []
                zone_aspects[zone_name].append(aspect)

        return zone_aspects
    
    def clear_zone_aspects(self, guild_id: str, scene_id: str):
        """Clear all zone aspects for a specific scene."""
        query = f"DELETE FROM fate_zone_aspects WHERE guild_id = %s AND scene_id = %s"
        self.execute_query(query, (str(guild_id), str(scene_id)))