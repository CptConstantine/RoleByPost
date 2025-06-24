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
CREATE TABLE IF NOT EXISTS characters (
    id TEXT PRIMARY KEY,
    guild_id TEXT NOT NULL,
    system TEXT,
    name TEXT,
    owner_id TEXT,
    is_npc BOOLEAN,
    system_specific_data TEXT,
    notes TEXT DEFAULT '[]',
    avatar_url TEXT DEFAULT '',
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
CREATE TABLE IF NOT EXISTS reminders (
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

conn.commit()
conn.close()
print("Database updated.")