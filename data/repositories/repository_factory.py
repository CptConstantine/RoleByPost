from data.repositories.entity_repository import EntityRepository
from data.repositories.entity_link_repository import EntityLinkRepository
from data.repositories.vw_entity_details_repository import EntityDetailsRepository
from .channel_permission_repository import ChannelPermissionRepository
from .server_repository import ServerRepository
from .homebrew_repository import HomebrewRepository
from .character_repository import CharacterRepository, ActiveCharacterRepository
from .scene_repository import SceneNotesRepository, SceneRepository, SceneNPCRepository, PinnedSceneMessageRepository
from .initiative_repository import InitiativeRepository, ServerInitiativeDefaultsRepository
from .reminder_repository import (
    ReminderRepository, AutoReminderSettingsRepository, 
    AutoReminderOptoutRepository, LastMessageTimeRepository
)
from .recap_repository import AutoRecapRepository, ApiKeyRepository
from .system_specific_repositories import (
    FateSceneAspectsRepository, FateSceneZonesRepository, FateGameAspectsRepository, 
    MGT2ESceneEnvironmentRepository, DefaultSkillsRepository, FateZoneAspectsRepository
)

class RepositoryFactory:
    def __init__(self):
        # Core repositories
        self._server_repo = None
        self._homebrew_repo = None
        
        # Character repositories
        self._character_repo = None
        self._active_character_repo = None
        
        # Scene repositories
        self._scene_repo = None
        self._scene_npc_repo = None
        self._scene_notes_repo = None
        self._pinned_scene_repo = None
        
        # Initiative repositories
        self._initiative_repo = None
        self._server_initiative_defaults_repo = None
        
        # Reminder repositories
        self._reminder_repo = None
        self._auto_reminder_settings_repo = None
        self._auto_reminder_optout_repo = None
        self._last_message_time_repo = None
        
        # Recap repositories
        self._auto_recap_repo = None
        self._api_key_repo = None
        
        # System-specific repositories
        self._fate_aspects_repo = None
        self._fate_zones_repo = None
        self._mgt2e_environment_repo = None
        self._default_skills_repo = None
        self._fate_game_aspects_repo = None
        self._fate_zone_aspects_repo = None

        # Channel permission repositories
        self._channel_permissions_repo = None

        # Entity repository
        self._entity_repo = None
        
        # EntityLink repository
        self._link_repo = None

        # Entity details view repository
        self._entity_details_repo = None

    # Core repositories
    @property
    def server(self) -> "ServerRepository":
        if self._server_repo is None:
            self._server_repo = ServerRepository()
        return self._server_repo
    
    @property
    def homebrew(self) -> "HomebrewRepository":
        if self._homebrew_repo is None:
            self._homebrew_repo = HomebrewRepository()
        return self._homebrew_repo
    
    # Character repositories
    @property
    def character(self) -> "CharacterRepository":
        if self._character_repo is None:
            self._character_repo = CharacterRepository()
        return self._character_repo
    
    @property
    def active_character(self) -> "ActiveCharacterRepository":
        if self._active_character_repo is None:
            self._active_character_repo = ActiveCharacterRepository()
        return self._active_character_repo
    
    # Scene repositories
    @property
    def scene(self) -> "SceneRepository":
        if self._scene_repo is None:
            self._scene_repo = SceneRepository()
        return self._scene_repo
    
    @property
    def scene_npc(self) -> "SceneNPCRepository":
        if self._scene_npc_repo is None:
            self._scene_npc_repo = SceneNPCRepository()
        return self._scene_npc_repo
    
    @property
    def scene_notes(self) -> "SceneNotesRepository":
        if self._scene_notes_repo is None:
            self._scene_notes_repo = SceneNotesRepository()
        return self._scene_notes_repo
    
    @property
    def pinned_scene(self) -> "PinnedSceneMessageRepository":
        if self._pinned_scene_repo is None:
            self._pinned_scene_repo = PinnedSceneMessageRepository()
        return self._pinned_scene_repo
    
    # Initiative repositories
    @property
    def initiative(self) -> "InitiativeRepository":
        if self._initiative_repo is None:
            self._initiative_repo = InitiativeRepository()
        return self._initiative_repo
    
    @property
    def server_initiative_defaults(self) -> "ServerInitiativeDefaultsRepository":
        if self._server_initiative_defaults_repo is None:
            self._server_initiative_defaults_repo = ServerInitiativeDefaultsRepository()
        return self._server_initiative_defaults_repo
    
    # Reminder repositories
    @property
    def reminder(self) -> "ReminderRepository":
        if self._reminder_repo is None:
            self._reminder_repo = ReminderRepository()
        return self._reminder_repo
    
    @property
    def auto_reminder_settings(self) -> "AutoReminderSettingsRepository":
        if self._auto_reminder_settings_repo is None:
            self._auto_reminder_settings_repo = AutoReminderSettingsRepository()
        return self._auto_reminder_settings_repo
    
    @property
    def auto_reminder_optout(self) -> "AutoReminderOptoutRepository":
        if self._auto_reminder_optout_repo is None:
            self._auto_reminder_optout_repo = AutoReminderOptoutRepository()
        return self._auto_reminder_optout_repo
    
    @property
    def last_message_time(self) -> "LastMessageTimeRepository":
        if self._last_message_time_repo is None:
            self._last_message_time_repo = LastMessageTimeRepository()
        return self._last_message_time_repo
    
    # Recap repositories
    @property
    def auto_recap(self) -> "AutoRecapRepository":
        if self._auto_recap_repo is None:
            self._auto_recap_repo = AutoRecapRepository()
        return self._auto_recap_repo
    
    @property
    def api_key(self) -> "ApiKeyRepository":
        if self._api_key_repo is None:
            self._api_key_repo = ApiKeyRepository()
        return self._api_key_repo
    
    # System-specific repositories
    @property
    def fate_aspects(self) -> "FateSceneAspectsRepository":
        if self._fate_aspects_repo is None:
            self._fate_aspects_repo = FateSceneAspectsRepository()
        return self._fate_aspects_repo
    
    @property
    def fate_zones(self) -> "FateSceneZonesRepository":
        if self._fate_zones_repo is None:
            self._fate_zones_repo = FateSceneZonesRepository()
        return self._fate_zones_repo
    
    @property
    def mgt2e_environment(self) -> "MGT2ESceneEnvironmentRepository":
        if self._mgt2e_environment_repo is None:
            self._mgt2e_environment_repo = MGT2ESceneEnvironmentRepository()
        return self._mgt2e_environment_repo
    
    @property
    def default_skills(self) -> "DefaultSkillsRepository":
        if self._default_skills_repo is None:
            self._default_skills_repo = DefaultSkillsRepository()
        return self._default_skills_repo
    
    @property
    def fate_game_aspects(self) -> "FateGameAspectsRepository":
        if self._fate_game_aspects_repo is None:
            self._fate_game_aspects_repo = FateGameAspectsRepository()
        return self._fate_game_aspects_repo
    
    @property
    def fate_zone_aspects(self) -> "FateZoneAspectsRepository":
        if self._fate_zone_aspects_repo is None:
            self._fate_zone_aspects_repo = FateZoneAspectsRepository()
        return self._fate_zone_aspects_repo
    
    # Channel permission repositories
    @property
    def channel_permissions(self) -> "ChannelPermissionRepository":
        if self._channel_permissions_repo is None:
            self._channel_permissions_repo = ChannelPermissionRepository()
        return self._channel_permissions_repo
    
    # Entity repository
    @property
    def entity(self) -> "EntityRepository":
        if self._entity_repo is None:
            self._entity_repo = EntityRepository()
        return self._entity_repo
    
    # EntityLink repository
    @property
    def link(self) -> "EntityLinkRepository":
        if self._link_repo is None:
            self._link_repo = EntityLinkRepository()
        return self._link_repo

    # EntityDetails repository
    @property
    def entity_details(self) -> "EntityDetailsRepository":
        if self._entity_details_repo is None:
            self._entity_details_repo = EntityDetailsRepository()
        return self._entity_details_repo

# Global repository factory instance
repositories = RepositoryFactory()