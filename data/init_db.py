import sqlite3

conn = sqlite3.connect('data/bot.db')
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS gms (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    PRIMARY KEY (guild_id, user_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS server_settings (
    guild_id TEXT PRIMARY KEY,
    system TEXT
)
""")

cur.execute("""
CREATE TABLE characters (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    system TEXT,
    name TEXT,
    owner_id TEXT,
    entity_type TEXT NOT NULL,
    system_specific_data TEXT,
    notes TEXT DEFAULT '[]',
    avatar_url TEXT DEFAULT ''
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS active_characters (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    char_id TEXT NOT NULL,
    PRIMARY KEY (guild_id, user_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS default_skills (
    guild_id TEXT NOT NULL,
    system TEXT NOT NULL,
    skills_json TEXT NOT NULL,
    PRIMARY KEY (guild_id, system)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS last_message_times (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    PRIMARY KEY (guild_id, user_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS initiative (
    guild_id TEXT NOT NULL,
    channel_id TEXT NOT NULL,
    type TEXT NOT NULL,
    initiative_state TEXT NOT NULL,
    is_active BOOLEAN NOT NULL,
    message_id TEXT,
    PRIMARY KEY (guild_id, channel_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS server_initiative_defaults (
    guild_id TEXT PRIMARY KEY,
    default_type TEXT
)
""")

# New table for scenes
cur.execute("""
CREATE TABLE IF NOT EXISTS scenes (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    name TEXT NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT 0,
    creation_time REAL NOT NULL,
    PRIMARY KEY (guild_id, scene_id)
)
""")

# Modified scene_notes table with scene_id
cur.execute("""
CREATE TABLE IF NOT EXISTS scene_notes (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL, 
    notes TEXT,
    PRIMARY KEY (guild_id, scene_id)
)
""")

# Modified scene_npcs table with scene_id
cur.execute("""
CREATE TABLE IF NOT EXISTS scene_npcs (
    guild_id TEXT NOT NULL,
    scene_id TEXT NOT NULL,
    npc_id TEXT NOT NULL,
    PRIMARY KEY (guild_id, scene_id, npc_id)
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    PRIMARY KEY (guild_id, user_id)
)
""")

# Table for server auto-reminder settings
cur.execute("""
CREATE TABLE IF NOT EXISTS auto_reminder_settings (
    guild_id TEXT PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT 0,
    delay_seconds INTEGER NOT NULL DEFAULT 86400
)
""")

# Table for user-specific auto-reminder opt-outs
cur.execute("""
CREATE TABLE IF NOT EXISTS auto_reminder_optouts (
    guild_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    opted_out BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (guild_id, user_id)
)
""")

# Index for characters table - fast lookup by guild_id and name
cur.execute("CREATE INDEX IF NOT EXISTS idx_character_guild_name ON characters(guild_id, name)")

# Index for characters table - fast lookup by guild_id and owner_id
cur.execute("CREATE INDEX IF NOT EXISTS idx_character_guild_owner ON characters(guild_id, owner_id)")

# Index for scene lookup
cur.execute("CREATE INDEX IF NOT EXISTS idx_scenes_guild_active ON scenes(guild_id, is_active)")

# Index for fast reminders lookup
cur.execute("CREATE INDEX IF NOT EXISTS idx_reminders_timestamp ON reminders(timestamp)")

# Index for initiative lookup
cur.execute("CREATE INDEX IF NOT EXISTS idx_initiative_active ON initiative(guild_id, is_active)")

conn.commit()
conn.close()
print("Database updated.")