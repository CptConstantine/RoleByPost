-- Server settings
CREATE TABLE IF NOT EXISTS server_settings (
    guild_id TEXT PRIMARY KEY,
    system TEXT,
    gm_role_id TEXT,
    player_role_id TEXT
);

-- Remove any indexes that might exist for the characters table
DROP INDEX IF EXISTS idx_character_guild_name;
DROP INDEX IF EXISTS idx_character_guild_owner;

-- Drop the characters table
DROP TABLE IF EXISTS characters;

-- Active characters
CREATE TABLE IF NOT EXISTS active_characters (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    char_id TEXT NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

-- Default skills
CREATE TABLE IF NOT EXISTS default_skills (
    guild_id TEXT NOT NULL,
    system TEXT NOT NULL,
    skills_json JSONB NOT NULL,
    PRIMARY KEY (guild_id, system)
);

-- Last message times
CREATE TABLE IF NOT EXISTS last_message_times (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

-- Initiative tracking
CREATE TABLE IF NOT EXISTS initiative (
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    type TEXT NOT NULL,
    initiative_state JSONB NOT NULL,
    is_active BOOLEAN NOT NULL,
    message_id TEXT,
    PRIMARY KEY (guild_id, channel_id)
);

-- Server initiative defaults
CREATE TABLE IF NOT EXISTS server_initiative_defaults (
    guild_id TEXT PRIMARY KEY,
    default_type TEXT
);

-- Scenes
CREATE TABLE IF NOT EXISTS scenes (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    creation_time DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (guild_id, scene_id)
);

-- Scene notes
CREATE TABLE IF NOT EXISTS scene_notes (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL, 
    notes TEXT,
    PRIMARY KEY (guild_id, scene_id)
);

-- Scene NPCs
CREATE TABLE IF NOT EXISTS scene_npcs (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    npc_id TEXT NOT NULL,
    PRIMARY KEY (guild_id, scene_id, npc_id)
);

-- Reminders
CREATE TABLE IF NOT EXISTS reminders (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    timestamp DOUBLE PRECISION NOT NULL,
    PRIMARY KEY (guild_id, user_id)
);

-- Auto reminder settings
CREATE TABLE IF NOT EXISTS auto_reminder_settings (
    guild_id TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    delay_seconds INTEGER NOT NULL DEFAULT 86400
);

-- Auto reminder opt-outs
CREATE TABLE IF NOT EXISTS auto_reminder_optouts (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    opted_out BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (guild_id, user_id)
);

-- Auto recaps
CREATE TABLE IF NOT EXISTS auto_recaps (
    guild_id TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    channel_id TEXT,
    days_interval INTEGER NOT NULL DEFAULT 7,
    days_to_include INTEGER NOT NULL DEFAULT 7,
    last_recap_time DOUBLE PRECISION,
    paused BOOLEAN NOT NULL DEFAULT FALSE,
    check_activity BOOLEAN NOT NULL DEFAULT TRUE
);

-- API keys
CREATE TABLE IF NOT EXISTS api_keys (
    guild_id TEXT PRIMARY KEY,
    openai_key TEXT
);

-- Pinned scene messages
CREATE TABLE IF NOT EXISTS pinned_scene_messages (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    message_id TEXT NOT NULL,
    PRIMARY KEY (guild_id, scene_id, channel_id)
);

-- FATE scene aspects
CREATE TABLE IF NOT EXISTS fate_scene_aspects (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    aspects JSONB,
    PRIMARY KEY (guild_id, scene_id)
);

-- FATE scene zones
CREATE TABLE IF NOT EXISTS fate_scene_zones (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    zones JSONB,
    PRIMARY KEY (guild_id, scene_id)
);

-- MGT2E scene environment
CREATE TABLE IF NOT EXISTS mgt2e_scene_environment (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    environment JSONB,
    PRIMARY KEY (guild_id, scene_id)
);

-- Homebrew rules
CREATE TABLE IF NOT EXISTS homebrew_rules (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    rule_name TEXT NOT NULL,
    rule_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, rule_name)
);

CREATE TABLE IF NOT EXISTS channel_permissions (
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    channel_type TEXT NOT NULL CHECK (channel_type IN ('ic', 'ooc', 'gm')),
    PRIMARY KEY (guild_id, channel_id)
);

-- Game aspects (global and scene-specific)
CREATE TABLE IF NOT EXISTS game_aspects (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    aspect_name TEXT NOT NULL,
    aspect TEXT NOT NULL,  -- JSON serialized Aspect object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(guild_id, aspect_name)
);

-- Zone aspects
CREATE TABLE IF NOT EXISTS zone_aspects (
    id SERIAL PRIMARY KEY,
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    zone_name TEXT NOT NULL,
    aspect TEXT NOT NULL,  -- JSON serialized Aspect object
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    aspect_name TEXT NOT NULL,
    UNIQUE(guild_id, scene_id, zone_name, aspect_name)
);

-- Entities
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    system TEXT NOT NULL,
    system_specific_data JSONB DEFAULT '{}',
    notes JSONB DEFAULT '[]',
    avatar_url TEXT DEFAULT ''
);

-- Add relationships table
CREATE TABLE IF NOT EXISTS relationships (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    from_entity_id TEXT NOT NULL,
    to_entity_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (from_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (to_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    UNIQUE(guild_id, from_entity_id, to_entity_id, relationship_type)
);

-- Indexes for performance
/* CREATE INDEX IF NOT EXISTS idx_character_guild_name ON characters(guild_id, name);
CREATE INDEX IF NOT EXISTS idx_character_guild_owner ON characters(guild_id, owner_id); */
CREATE INDEX IF NOT EXISTS idx_scenes_guild_active ON scenes(guild_id, is_active);

CREATE INDEX IF NOT EXISTS idx_reminders_timestamp ON reminders(timestamp);

CREATE INDEX IF NOT EXISTS idx_initiative_active ON initiative(guild_id, is_active);

CREATE INDEX IF NOT EXISTS idx_pinned_scene_channel ON pinned_scene_messages(guild_id, channel_id);

CREATE INDEX IF NOT EXISTS idx_homebrew_rules_guild ON homebrew_rules(guild_id);

CREATE INDEX IF NOT EXISTS idx_channel_permissions_lookup ON channel_permissions (guild_id, channel_id);

CREATE INDEX IF NOT EXISTS idx_entities_guild_type ON entities(guild_id, entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_guild_system ON entities(guild_id, system);
CREATE INDEX IF NOT EXISTS idx_entities_owner ON entities(owner_id);
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(guild_id, name);

CREATE INDEX IF NOT EXISTS idx_relationships_guild ON relationships(guild_id);
CREATE INDEX IF NOT EXISTS idx_relationships_from ON relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON relationships(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);
CREATE INDEX IF NOT EXISTS idx_relationships_guild_from ON relationships(guild_id, from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_guild_to ON relationships(guild_id, to_entity_id);