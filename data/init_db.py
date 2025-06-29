import os
import sqlite3

DB_FILE = 'data/db/bot.db'

def init_database():
    """Initialize the database - can be called multiple times safely"""
    # Ensure data directory exists
    os.makedirs('data', exist_ok=True)
    
    conn = sqlite3.connect(DB_FILE)

    # All your existing CREATE TABLE statements...
    # (keep all the existing table creation code)
    
    conn.commit()
    conn.close()
    print("Database initialized successfully.")

def create_tables():
    conn = sqlite3.connect(DB_FILE)
    cur = conn.cursor()

    # Existing tables
    cur.execute("""
    CREATE TABLE IF NOT EXISTS server_settings (
        guild_id TEXT PRIMARY KEY,
        system TEXT,
        gm_role_id TEXT,
        player_role_id TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS characters (
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

    # Scenes tables
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

    cur.execute("""
    CREATE TABLE IF NOT EXISTS scene_notes (
        guild_id TEXT NOT NULL,
        scene_id TEXT NOT NULL, 
        notes TEXT,
        PRIMARY KEY (guild_id, scene_id)
    )
    """)

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

    # Table for automatic recaps
    cur.execute("""
    CREATE TABLE IF NOT EXISTS auto_recaps (
        guild_id TEXT PRIMARY KEY,
        enabled BOOLEAN NOT NULL DEFAULT 0,
        channel_id TEXT,
        days_interval INTEGER NOT NULL DEFAULT 7,
        days_to_include INTEGER NOT NULL DEFAULT 7,
        last_recap_time REAL,
        paused BOOLEAN NOT NULL DEFAULT 0,
        check_activity BOOLEAN NOT NULL DEFAULT 1
    )
    """)

    # Table for OpenAI API keys
    cur.execute("""
    CREATE TABLE IF NOT EXISTS api_keys (
        guild_id TEXT PRIMARY KEY,
        openai_key TEXT
    )
    """)

    # NEW TABLES FOR PINNED SCENE VIEWS

    # Table for pinned scene messages
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pinned_scene_messages (
        guild_id TEXT NOT NULL,
        scene_id TEXT NOT NULL,
        channel_id TEXT NOT NULL,
        message_id TEXT NOT NULL,
        PRIMARY KEY (guild_id, scene_id, channel_id)
    )
    """)

    # Table for FATE-specific scene aspects
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fate_scene_aspects (
        guild_id TEXT NOT NULL,
        scene_id TEXT NOT NULL,
        aspects TEXT,
        PRIMARY KEY (guild_id, scene_id)
    )
    """)

    # Table for FATE-specific scene zones
    cur.execute("""
    CREATE TABLE IF NOT EXISTS fate_scene_zones (
        guild_id TEXT NOT NULL,
        scene_id TEXT NOT NULL,
        zones TEXT,
        PRIMARY KEY (guild_id, scene_id)
    )
    """)

    # Table for MGT2E-specific scene environment
    cur.execute("""
    CREATE TABLE IF NOT EXISTS mgt2e_scene_environment (
        guild_id TEXT NOT NULL,
        scene_id TEXT NOT NULL,
        environment TEXT,
        PRIMARY KEY (guild_id, scene_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS homebrew_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id TEXT NOT NULL,
        rule_name TEXT NOT NULL,
        rule_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(guild_id, rule_name)
    )
    """)

    # Indexes for performance
    cur.execute("CREATE INDEX IF NOT EXISTS idx_character_guild_name ON characters(guild_id, name)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_character_guild_owner ON characters(guild_id, owner_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_scenes_guild_active ON scenes(guild_id, is_active)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_reminders_timestamp ON reminders(timestamp)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_initiative_active ON initiative(guild_id, is_active)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pinned_scene_channel ON pinned_scene_messages(guild_id, channel_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_homebrew_rules_guild ON homebrew_rules(guild_id)")

    conn.commit()
    conn.close()
    print("Database created.")