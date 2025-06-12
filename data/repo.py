import sqlite3
import json
from core.abstract_models import BaseCharacter
import core.system_factory as system_factory


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
    CharacterClass = system_factory.get_specific_character(system)

    # Use the system's defined fields
    if character.is_npc:
        system_fields = CharacterClass.SYSTEM_SPECIFIC_NPC
    else:
        system_fields = CharacterClass.SYSTEM_SPECIFIC_CHARACTER

    system_specific_data = {}
    for key in system_fields:
        system_specific_data[key] = character.data.get(key)

    notes = character.notes or ""

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO characters
            (id, guild_id, system, name, owner_id, is_npc, system_specific_data, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(character.id),
            str(guild_id),
            system,
            character.name,
            str(character.owner_id),
            bool(character.is_npc),
            json.dumps(system_specific_data),
            notes
        ))
        conn.commit()


def get_character(guild_id, char_id):
    """
    Load a character from the database and return an instance of the system-specific Character class.
    """
    with get_db() as conn:
        try:
            cur = conn.execute("SELECT system, name, owner_id, is_npc, system_specific_data, notes FROM characters WHERE guild_id = ? AND id = ?", (str(guild_id), str(char_id)))
            row = cur.fetchone()
            if not row:
                return None
            system, name, owner_id, is_npc, system_specific_data, notes = row
        except sqlite3.OperationalError:
            cur = conn.execute("SELECT system, name, owner_id, is_npc, system_specific_data FROM characters WHERE guild_id = ? AND id = ?", (str(guild_id), str(char_id)))
            row = cur.fetchone()
            if not row:
                return None
            system, name, owner_id, is_npc, system_specific_data = row
            notes = ""

        CharacterClass = system_factory.get_specific_character(system)
        system_fields = CharacterClass.SYSTEM_SPECIFIC_NPC if is_npc else CharacterClass.SYSTEM_SPECIFIC_CHARACTER
        system_specific = json.loads(system_specific_data)
        character = {
            "name": name,
            "owner_id": owner_id,
            "is_npc": is_npc,
            "notes": notes or "",
        }
        for key in system_fields:
            character[key] = system_specific.get(key, system_fields[key])
        return CharacterClass.from_dict(character)


def get_all_characters(guild_id, system=None):
    """
    Load all characters for a guild (optionally filtered by system).
    Returns a list of system-specific Character class instances.
    """
    characters = []
    with get_db() as conn:
        try:
            if system:
                cur = conn.execute(
                    "SELECT system, name, owner_id, is_npc, system_specific_data, notes FROM characters WHERE guild_id = ? AND system = ?",
                    (str(guild_id), system)
                )
            else:
                cur = conn.execute(
                    "SELECT system, name, owner_id, is_npc, system_specific_data, notes FROM characters WHERE guild_id = ?",
                    (str(guild_id),)
                )
            rows = cur.fetchall()
        except sqlite3.OperationalError:
            if system:
                cur = conn.execute(
                    "SELECT system, name, owner_id, is_npc, system_specific_data FROM characters WHERE guild_id = ? AND system = ?",
                    (str(guild_id), system)
                )
            else:
                cur = conn.execute(
                    "SELECT system, name, owner_id, is_npc, system_specific_data FROM characters WHERE guild_id = ?",
                    (str(guild_id),)
                )
            rows = cur.fetchall()
            rows = [row + ("",) for row in rows]

        if not rows:
            return []
        for row in rows:
            system_val, name, owner_id, is_npc, system_specific_data, notes = row
            CharacterClass = system_factory.get_specific_character(system_val)
            system_fields = CharacterClass.SYSTEM_SPECIFIC_NPC if is_npc else CharacterClass.SYSTEM_SPECIFIC_CHARACTER
            system_specific = json.loads(system_specific_data)
            character = {
                "name": name,
                "owner_id": owner_id,
                "is_npc": is_npc,
                "notes": notes or "",
            }
            for key in system_fields:
                character[key] = system_specific.get(key, system_fields[key])
            characters.append(CharacterClass.from_dict(character))
    return characters


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


def add_scene_npc(guild_id, npc_id):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO scene_npcs (guild_id, npc_id) VALUES (?, ?)", (str(guild_id), str(npc_id)))
        conn.commit()


def remove_scene_npc(guild_id, npc_id):
    with get_db() as conn:
        conn.execute("DELETE FROM scene_npcs WHERE guild_id = ? AND npc_id = ?", (str(guild_id), str(npc_id)))
        conn.commit()


def clear_scenes(guild_id):
    with get_db() as conn:
        conn.execute("DELETE FROM scene_npcs WHERE guild_id = ?", (str(guild_id),))
        conn.commit()
        conn.execute("DELETE FROM scene_notes WHERE guild_id = ?", (str(guild_id),))
        conn.commit()


def get_scene_npcs(guild_id):
    with get_db() as conn:
        cur = conn.execute("SELECT npc_id FROM scene_npcs WHERE guild_id = ?", (str(guild_id),))
        return [row[0] for row in cur.fetchall()]
    

def set_scene_notes(guild_id, notes):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO scene_notes (guild_id, notes) VALUES (?, ?)",
            (str(guild_id), notes)
        )
        conn.commit()


def get_scene_notes(guild_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT notes FROM scene_notes WHERE guild_id = ?",
            (str(guild_id),)
        )
        row = cur.fetchone()
        return row[0] if row else None


def set_active_character(guild_id, user_id, char_id):
    with get_db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO active_characters (guild_id, user_id, char_id) VALUES (?, ?, ?)",
            (str(guild_id), str(user_id), str(char_id))
        )
        conn.commit()


def get_active_character_id(guild_id, user_id):
    with get_db() as conn:
        cur = conn.execute(
            "SELECT char_id FROM active_characters WHERE guild_id = ? AND user_id = ?",
            (str(guild_id), str(user_id))
        )
        row = cur.fetchone()
        return row[0] if row else None


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