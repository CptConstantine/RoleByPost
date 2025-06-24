import sqlite3
import json
import uuid
import time
from core.models import BaseCharacter
import core.factories as factories


DB_FILE = 'data/bot.db'


def get_db():
    return sqlite3.connect(DB_FILE)


def is_gm(guild_id, user_id):
    with get_db() as conn:
        cur = conn.execute("SELECT 1 FROM gms WHERE guild_id = ? AND user_id = ?", (str(guild_id), str(user_id)))
        return cur.fetchone() is not None


def set_gm(guild_id, user_id):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO gms (guild_id, user_id) VALUES (?, ?)", (str(guild_id), str(user_id)))
        conn.commit()


def get_gm_ids(guild_id):
    with get_db() as conn:
        cur = conn.execute("SELECT user_id FROM gms WHERE guild_id = ?", (str(guild_id),))
        return [row[0] for row in cur.fetchall()]


def set_system(guild_id, system):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO server_settings (guild_id, system) VALUES (?, ?)",
            (str(guild_id), system)
        )
        conn.commit()


def get_system(guild_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT system FROM server_settings WHERE guild_id = ?",
            (str(guild_id),)
        )
        row = cur.fetchone()
        return row[0] if row else "fate"  # Default to "fate"


def set_character(guild_id, character: BaseCharacter, system=None):
    """
    Save a character to the database.
    character: An instance of a system-specific Character.
    """
    if system is None:
        system = get_system(guild_id)
    CharacterClass = factories.get_specific_character(system)

    # Use the system's defined fields
    if character.is_npc:
        system_fields = CharacterClass.SYSTEM_SPECIFIC_NPC
    else:
        system_fields = CharacterClass.SYSTEM_SPECIFIC_CHARACTER

    system_specific_data = {}
    for key in system_fields:
        system_specific_data[key] = character.data.get(key)

    notes = character.notes or []

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO characters
            (id, guild_id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(character.id),
            str(guild_id),
            system,
            character.name,
            str(character.owner_id),
            bool(character.is_npc),
            json.dumps(system_specific_data),
            json.dumps(notes),
            character.avatar_url
        ))
        conn.commit()


def get_character(guild_id, char_name):
    """
    Load a character from the database and return an instance of the system-specific Character class.
    """
    with get_db() as conn:
        cur = conn.execute("SELECT id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url FROM characters WHERE guild_id = ? AND name = ?", (str(guild_id), str(char_name)))
        row = cur.fetchone()
        if not row:
            return None
        id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url = row

        character = build_character(id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url)
        character
        return character

def get_character_by_id(guild_id, char_id):
    """
    Load a character from the database and return an instance of the system-specific Character class.
    """
    with get_db() as conn:
        cur = conn.execute("SELECT id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url FROM characters WHERE guild_id = ? AND id = ?", (str(guild_id), str(char_id)))
        row = cur.fetchone()
        if not row:
            return None
        id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url = row

        character = build_character(id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url)
        return character

def build_character(id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url):
    CharacterClass = factories.get_specific_character(system)
    system_fields = CharacterClass.SYSTEM_SPECIFIC_NPC if is_npc else CharacterClass.SYSTEM_SPECIFIC_CHARACTER
    system_specific = json.loads(system_specific_data)
    
    # Use the helper method
    character_dict = BaseCharacter.create_base_character(
        id=id,
        name=name,
        owner_id=owner_id,
        is_npc=is_npc,
        notes=json.loads(notes) or [],
        avatar_url=avatar_url
    )
    
    # Add system-specific fields
    for key in system_fields:
        character_dict[key] = system_specific.get(key, system_fields[key])
        
    return CharacterClass.from_dict(character_dict)


def get_all_characters(guild_id, system=None):
    """
    Load all characters for a guild (optionally filtered by system).
    Returns a list of system-specific Character class instances.
    """
    characters = []
    with get_db() as conn:
        if system:
            cur = conn.execute(
                "SELECT id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url FROM characters WHERE guild_id = ? AND system = ?",
                (str(guild_id), system)
            )
        else:
            cur = conn.execute(
                "SELECT id, system, name, owner_id, is_npc, system_specific_data, notes, avatar_url FROM characters WHERE guild_id = ?",
                (str(guild_id),)
            )
        rows = cur.fetchall()

        if not rows:
            return []
        for row in rows:
            id, system_val, name, owner_id, is_npc, system_specific_data, notes, avatar_url = row
            CharacterClass = factories.get_specific_character(system_val)
            system_fields = CharacterClass.SYSTEM_SPECIFIC_NPC if is_npc else CharacterClass.SYSTEM_SPECIFIC_CHARACTER
            system_specific = json.loads(system_specific_data)
            
            # Use the helper method
            character_dict = BaseCharacter.create_base_character(
                id=id,
                name=name,
                owner_id=owner_id,
                is_npc=is_npc,
                notes=json.loads(notes) or [],
                avatar_url=avatar_url
            )
            
            # Add system-specific fields
            for key in system_fields:
                character_dict[key] = system_specific.get(key, system_fields[key])
                
            characters.append(CharacterClass.from_dict(character_dict))
    return characters


def get_non_gm_active_characters(guild_id):
    """
    Returns a list of active character objects for users who are not GMs in the given guild.
    """
    with get_db() as conn:
        # Get all GM user_ids for this guild
        cur = conn.execute(
            "SELECT user_id FROM gms WHERE guild_id = ?",
            (str(guild_id),)
        )
        gm_ids = set(str(row[0]) for row in cur.fetchall())

        # Get all active characters where user_id is not a GM
        cur = conn.execute(
            "SELECT user_id, char_id FROM active_characters WHERE guild_id = ?",
            (str(guild_id),)
        )
        non_gm_active = [
            (str(row[0]), row[1]) for row in cur.fetchall() if str(row[0]) not in gm_ids
        ]

    # Return the character objects
    return [get_character_by_id(guild_id, char_id) for user_id, char_id in non_gm_active if get_character_by_id(guild_id, char_id) is not None]


def set_default_skills(guild_id, system, skills_dict):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO default_skills (guild_id, system, skills_json) VALUES (?, ?, ?)",
            (str(guild_id), system, json.dumps(skills_dict))
        )
        conn.commit()


def get_default_skills(guild_id, system):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT skills_json FROM default_skills WHERE guild_id = ? AND system = ?",
            (str(guild_id), system)
        )
        row = cur.fetchone()
        if row:
            return json.loads(row[0])
        return None


def create_scene(guild_id, name):
    """Create a new scene with the given name"""
    scene_id = str(uuid.uuid4())
    with get_db() as conn:
        # First, check if this is the first scene for the guild
        cur = conn.execute("SELECT COUNT(*) FROM scenes WHERE guild_id = ?", (str(guild_id),))
        is_first_scene = cur.fetchone()[0] == 0
        
        # Insert the new scene
        conn.execute(
            "INSERT INTO scenes (guild_id, scene_id, name, is_active, creation_time) VALUES (?, ?, ?, ?, ?)",
            (str(guild_id), scene_id, name, is_first_scene, time.time())
        )
        conn.commit()
        return scene_id

def get_scenes(guild_id):
    """Get all scenes for a guild"""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT scene_id, name, is_active FROM scenes WHERE guild_id = ? ORDER BY creation_time",
            (str(guild_id),)
        )
        return [{"id": row[0], "name": row[1], "is_active": bool(row[2])} for row in cur.fetchall()]

def get_scene_by_name(guild_id, name):
    """Get a scene by name"""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT scene_id, name, is_active FROM scenes WHERE guild_id = ? AND LOWER(name) = LOWER(?)",
            (str(guild_id), name.lower())
        )
        row = cur.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "is_active": bool(row[2])}
        return None

def get_active_scene(guild_id):
    """Get the active scene for a guild"""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT scene_id, name FROM scenes WHERE guild_id = ? AND is_active = 1",
            (str(guild_id),)
        )
        row = cur.fetchone()
        if row:
            return {"id": row[0], "name": row[1], "is_active": True}
        return None

def set_active_scene(guild_id, scene_id):
    """Set a scene as active and deactivate all others"""
    with get_db() as conn:
        # First deactivate all scenes
        conn.execute(
            "UPDATE scenes SET is_active = 0 WHERE guild_id = ?",
            (str(guild_id),)
        )
        # Then activate the specified scene
        conn.execute(
            "UPDATE scenes SET is_active = 1 WHERE guild_id = ? AND scene_id = ?",
            (str(guild_id), str(scene_id))
        )
        conn.commit()

def delete_scene(guild_id, scene_id):
    """Delete a scene and all associated data"""
    with get_db() as conn:
        # Delete the scene
        conn.execute(
            "DELETE FROM scenes WHERE guild_id = ? AND scene_id = ?",
            (str(guild_id), str(scene_id))
        )
        # Delete associated notes
        conn.execute(
            "DELETE FROM scene_notes WHERE guild_id = ? AND scene_id = ?",
            (str(guild_id), str(scene_id))
        )
        # Delete associated NPCs
        conn.execute(
            "DELETE FROM scene_npcs WHERE guild_id = ? AND scene_id = ?",
            (str(guild_id), str(scene_id))
        )
        conn.commit()
        
        # If the deleted scene was active, set another scene as active if available
        if conn.total_changes > 0:
            cur = conn.execute(
                "SELECT scene_id FROM scenes WHERE guild_id = ? ORDER BY creation_time LIMIT 1",
                (str(guild_id),)
            )
            row = cur.fetchone()
            if row:
                conn.execute(
                    "UPDATE scenes SET is_active = 1 WHERE guild_id = ? AND scene_id = ?",
                    (str(guild_id), row[0])
                )
                conn.commit()

def rename_scene(guild_id, scene_id, new_name):
    """Rename a scene"""
    with get_db() as conn:
        conn.execute(
            "UPDATE scenes SET name = ? WHERE guild_id = ? AND scene_id = ?",
            (new_name, str(guild_id), str(scene_id))
        )
        conn.commit()

# Modified scene notes functions

def set_scene_notes(guild_id, notes, scene_id=None):
    """Set notes for a scene"""
    if scene_id is None:
        scene = get_active_scene(guild_id)
        if not scene:
            return False
        scene_id = scene["id"]
        
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scene_notes (guild_id, scene_id, notes) VALUES (?, ?, ?)",
            (str(guild_id), str(scene_id), notes)
        )
        conn.commit()
        return True

def get_scene_notes(guild_id, scene_id=None):
    """Get notes for a scene"""
    if scene_id is None:
        scene = get_active_scene(guild_id)
        if not scene:
            return None
        scene_id = scene["id"]
        
    with get_db() as conn:
        cur = conn.execute(
            "SELECT notes FROM scene_notes WHERE guild_id = ? AND scene_id = ?",
            (str(guild_id), str(scene_id))
        )
        row = cur.fetchone()
        return row[0] if row else None

# Modified scene NPCs functions

def add_scene_npc(guild_id, npc_id, scene_id=None):
    """Add an NPC to a scene"""
    if scene_id is None:
        scene = get_active_scene(guild_id)
        if not scene:
            return False
        scene_id = scene["id"]
        
    with get_db() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO scene_npcs (guild_id, scene_id, npc_id) VALUES (?, ?, ?)",
            (str(guild_id), str(scene_id), str(npc_id))
        )
        conn.commit()
        return True

def remove_scene_npc(guild_id, npc_id, scene_id=None):
    """Remove an NPC from a scene"""
    if scene_id is None:
        scene = get_active_scene(guild_id)
        if not scene:
            return False
        scene_id = scene["id"]
        
    with get_db() as conn:
        conn.execute(
            "DELETE FROM scene_npcs WHERE guild_id = ? AND scene_id = ? AND npc_id = ?",
            (str(guild_id), str(scene_id), str(npc_id))
        )
        conn.commit()
        return True

def clear_scene_npcs(guild_id, scene_id=None):
    """Remove all NPCs from a scene"""
    if scene_id is None:
        scene = get_active_scene(guild_id)
        if not scene:
            return False
        scene_id = scene["id"]
        
    with get_db() as conn:
        conn.execute(
            "DELETE FROM scene_npcs WHERE guild_id = ? AND scene_id = ?",
            (str(guild_id), str(scene_id))
        )
        conn.commit()
        return True

def get_scene_npc_ids(guild_id, scene_id=None):
    """Get all NPCs in a scene"""
    if scene_id is None:
        scene = get_active_scene(guild_id)
        if not scene:
            return []
        scene_id = scene["id"]
        
    with get_db() as conn:
        cur = conn.execute(
            "SELECT npc_id FROM scene_npcs WHERE guild_id = ? AND scene_id = ?",
            (str(guild_id), str(scene_id))
        )
        return [row[0] for row in cur.fetchall()]

def get_scene_npcs(guild_id, scene_id=None):
    """Get all NPCs in a scene as character objects"""
    npc_ids = get_scene_npc_ids(guild_id, scene_id)
    return [get_character_by_id(guild_id, npc_id) for npc_id in npc_ids if get_character_by_id(guild_id, npc_id) is not None]


def set_active_character(guild_id, user_id, char_id):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO active_characters (guild_id, user_id, char_id) VALUES (?, ?, ?)",
            (str(guild_id), str(user_id), str(char_id))
        )
        conn.commit()


def get_active_character(guild_id, user_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT char_id FROM active_characters WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        row = cur.fetchone()
        return get_character_by_id(guild_id, row[0]) if row else None


def set_last_message_time(guild_id, user_id, timestamp):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO last_message_times (guild_id, user_id, timestamp) VALUES (?, ?, ?)",
            (str(guild_id), str(user_id), timestamp)
        )
        conn.commit()


def get_last_message_time(guild_id, user_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT timestamp FROM last_message_times WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        row = cur.fetchone()
        return float(row[0]) if row else None


def set_reminder_time(guild_id, user_id, timestamp):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO reminders (guild_id, user_id, timestamp) VALUES (?, ?, ?)",
            (str(guild_id), str(user_id), timestamp)
        )
        conn.commit()


def get_reminder_time(guild_id, user_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT timestamp FROM reminders WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        row = cur.fetchone()
        return float(row[0]) if row else None
    
def start_initiative(guild_id, channel_id, type, initiative_state):
    """
    Start or update initiative for a channel.
    """
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO initiative (guild_id, channel_id, type, initiative_state, is_active) VALUES (?, ?, ?, ?, ?)",
            (str(guild_id), str(channel_id), type, json.dumps(initiative_state), True)
        )
        conn.commit()

def get_initiative(guild_id, channel_id):
    """
    Retrieve the initiative state for a channel.
    """
    with get_db() as conn:
        cur = conn.execute(
            "SELECT type, initiative_state, is_active FROM initiative WHERE guild_id = ? AND channel_id = ?",
            (str(guild_id), str(channel_id))
        )
        row = cur.fetchone()
        if row:
            type, initiative_state, is_active = row
            return {
                "type": type,
                "initiative_state": json.loads(initiative_state),
                "is_active": bool(is_active)
            }
        return None

def update_initiative_state(guild_id, channel_id, initiative_state):
    """
    Update the initiative_state for a channel.
    """
    with get_db() as conn:
        conn.execute(
            "UPDATE initiative SET initiative_state = ? WHERE guild_id = ? AND channel_id = ?",
            (json.dumps(initiative_state), str(guild_id), str(channel_id))
        )
        conn.commit()

def set_initiative_message_id(guild_id, channel_id, message_id):
    """
    Store the message ID for the initiative message
    """
    with get_db() as conn:
        conn.execute(
            "UPDATE initiative SET message_id = ? WHERE guild_id = ? AND channel_id = ?",
            (str(message_id), str(guild_id), str(channel_id))
        )
        conn.commit()

def get_initiative_message_id(guild_id, channel_id):
    """
    Get the message ID for the initiative message
    """
    with get_db() as conn:
        cur = conn.execute(
            "SELECT message_id FROM initiative WHERE guild_id = ? AND channel_id = ?",
            (str(guild_id), str(channel_id))
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else None

def set_initiative_active(guild_id, channel_id, is_active):
    """
    Set whether initiative is active for a channel.
    """
    with get_db() as conn:
        conn.execute(
            "UPDATE initiative SET is_active = ? WHERE guild_id = ? AND channel_id = ?",
            (bool(is_active), str(guild_id), str(channel_id))
        )
        conn.commit()

def end_initiative(guild_id, channel_id):
    """
    Remove initiative for a channel (ends initiative).
    """
    with get_db() as conn:
        conn.execute(
            "DELETE FROM initiative WHERE guild_id = ? AND channel_id = ?",
            (str(guild_id), str(channel_id))
        )
        conn.commit()

def set_default_initiative_type(guild_id, default_type):
    """
    Set the default initiative type for a server.
    """
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO server_initiative_defaults (guild_id, default_type) VALUES (?, ?)",
            (str(guild_id), default_type)
        )
        conn.commit()

def get_default_initiative_type(guild_id):
    """
    Get the default initiative type for a server.
    Returns the type as a string, or None if not set.
    """
    with get_db() as conn:
        cur = conn.execute(
            "SELECT default_type FROM server_initiative_defaults WHERE guild_id = ?",
            (str(guild_id),)
        )
        row = cur.fetchone()
        return row[0] if row else None

# Add these functions to repo.py

def get_auto_reminder_settings(guild_id):
    """Get auto-reminder settings for a guild"""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT enabled, delay_seconds FROM auto_reminder_settings WHERE guild_id = ?",
            (str(guild_id),)
        )
        row = cur.fetchone()
        if row:
            return {"enabled": bool(row[0]), "delay_seconds": row[1]}
        else:
            # Default settings if not found
            return {"enabled": False, "delay_seconds": 86400}

def set_auto_reminder(guild_id, enabled, delay_seconds):
    """Enable or disable auto-reminders for a guild"""
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO auto_reminder_settings (guild_id, enabled, delay_seconds) "
            "VALUES (?, ?, ?)",
            (str(guild_id), int(enabled), delay_seconds)
        )
        conn.commit()

def is_user_opted_out(guild_id, user_id):
    """Check if a user has opted out of auto-reminders"""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT opted_out FROM auto_reminder_optouts WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        row = cur.fetchone()
        return bool(row[0]) if row else False

def set_user_optout(guild_id, user_id, opted_out):
    """Set whether a user has opted out of auto-reminders"""
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO auto_reminder_optouts (guild_id, user_id, opted_out) "
            "VALUES (?, ?, ?)",
            (str(guild_id), str(user_id), int(opted_out))
        )
        conn.commit()

def get_all_auto_reminder_users(guild_id):
    """Get all users who have been mentioned for auto-reminders"""
    with get_db() as conn:
        cur = conn.execute(
            "SELECT user_id FROM auto_reminder_optouts WHERE guild_id = ?",
            (str(guild_id),)
        )
        return [row[0] for row in cur.fetchall()]

def update_last_message_time(guild_id, user_id, timestamp):
    """Update the last message timestamp for a user in a guild"""
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO last_message_times (guild_id, user_id, timestamp) VALUES (?, ?, ?)",
            (str(guild_id), str(user_id), timestamp)
        )
        conn.commit()