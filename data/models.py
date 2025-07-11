from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from datetime import datetime

@dataclass
class ServerSettings:
    guild_id: str
    system: Optional[str] = None
    gm_role_id: Optional[str] = None
    player_role_id: Optional[str] = None
    generic_base_roll: Optional[str] = None

@dataclass
class Character:
    id: str
    guild_id: str
    name: str
    owner_id: str
    entity_type: str
    access_type: str
    system: Optional[str] = None
    system_specific_data: Optional[Dict[str, Any]] = None
    notes: List[str] = None
    avatar_url: str = ""
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []
        if self.system_specific_data is None:
            self.system_specific_data = {}
    
    @property
    def is_npc(self) -> bool:
        return self.entity_type == "npc"

@dataclass
class ActiveCharacter:
    guild_id: str
    user_id: str
    char_id: str

@dataclass
class DefaultSkills:
    guild_id: str
    system: str
    skills_json: Dict[str, Any]

@dataclass
class LastMessageTime:
    guild_id: str
    user_id: str
    timestamp: float

@dataclass
class InitiativeTracker:
    guild_id: str
    channel_id: str
    type: str
    initiative_state: Dict[str, Any]
    is_active: bool
    message_id: Optional[str] = None

@dataclass
class ServerInitiativeDefaults:
    guild_id: str
    default_type: str

@dataclass
class Scene:
    guild_id: str
    scene_id: str
    name: str
    is_active: bool
    creation_time: float
    notes: Optional[str] = None

@dataclass
class SceneNPC:
    guild_id: str
    scene_id: str
    npc_id: str

@dataclass
class SceneNotes:
    guild_id: str
    scene_id: str
    notes: str

@dataclass
class Reminder:
    guild_id: str
    user_id: str
    timestamp: float

@dataclass
class AutoReminderSettings:
    guild_id: str
    enabled: bool = False
    delay_seconds: int = 86400

@dataclass
class AutoReminderOptout:
    guild_id: str
    user_id: str
    opted_out: bool = False

@dataclass
class AutoRecapSettings:
    guild_id: str
    enabled: bool = False
    channel_id: Optional[str] = None
    days_interval: int = 7
    days_to_include: int = 7
    last_recap_time: Optional[float] = None
    paused: bool = False
    check_activity: bool = True

@dataclass
class ApiKey:
    guild_id: str
    openai_key: Optional[str] = None

@dataclass
class PinnedSceneMessage:
    guild_id: str
    scene_id: str
    channel_id: str
    message_id: str

@dataclass
class FateSceneAspects:
    guild_id: str
    scene_id: str
    aspects: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.aspects is None:
            self.aspects = []

@dataclass
class FateSceneZones:
    guild_id: str
    scene_id: str
    zones: List[str] = None
    
    def __post_init__(self):
        if self.zones is None:
            self.zones = []

@dataclass
class MGT2ESceneEnvironment:
    guild_id: str
    scene_id: str
    environment: Dict[str, str] = None
    
    def __post_init__(self):
        if self.environment is None:
            self.environment = {}

@dataclass
class HomebrewRule:
    guild_id: str
    rule_name: str
    rule_text: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class ChannelPermission:
    guild_id: str
    channel_id: str
    channel_type: str  # 'ic', 'ooc', 'gm', 'unrestricted'

@dataclass
class GameAspect:
    guild_id: str
    aspect_name: str
    aspect: Dict[str, Any]

@dataclass  
class ZoneAspect:
    guild_id: str
    scene_id: str
    zone_name: str
    aspect_name: str
    aspect: Dict[str, Any]

@dataclass
class Entity:
    id: str
    guild_id: str
    name: str
    owner_id: str
    entity_type: str
    system: str
    system_specific_data: Dict[str, Any]
    notes: List[str]
    avatar_url: str
    access_type: str

@dataclass
class EntityLink:
    id: str
    guild_id: str
    from_entity_id: str
    to_entity_id: str
    link_type: str
    metadata: Dict[str, Any] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now()