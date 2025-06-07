import sqlite3
import json


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

        
def set_character(guild_id, char_id, character, system="fate"):
    with get_db() as conn:
        system_specific_data = {
            "fate_points": character.get("fate_points"),
            "skills": character.get("skills", {}),
            "aspects": character.get("aspects", []),
            "hidden_aspects": character.get("hidden_aspects", []),
            "stress": character.get("stress", {}),
            "consequences": character.get("consequences", []),
        }
        conn.execute("""
            INSERT OR REPLACE INTO characters
            (id, guild_id, system, name, owner_id, is_npc, system_specific_data)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(char_id),
            str(guild_id),
            system,
            character.get("name"),
            str(character.get("owner_id")),
            bool(character.get("is_npc")),
            json.dumps(system_specific_data)
        ))
        conn.commit()


def get_character(guild_id, char_id):
    with get_db() as conn:
        cur = conn.execute("SELECT name, owner_id, is_npc, system_specific_data FROM characters WHERE guild_id = ? AND id = ?", (str(guild_id), str(char_id)))
        row = cur.fetchone()
        if not row:
            return None
        name, owner_id, is_npc, system_specific_data = row
        system_specific = json.loads(system_specific_data)
        character = {
            "name": name,
            "owner_id": owner_id,
            "is_npc": is_npc,
            "fate_points": system_specific.get("fate_points", 0),
            "skills": system_specific.get("skills", {}),
            "aspects": system_specific.get("aspects", []),
            "hidden_aspects": system_specific.get("hidden_aspects", []),
            "stress": system_specific.get("stress", {}),
            "consequences": system_specific.get("consequences", []),
        }
        return character
    

def get_all_characters(guild_id):
    """Retrieve all characters for a guild."""
    characters = []
    with get_db() as conn:
        cur = conn.execute(
            "SELECT name, owner_id, is_npc, system_specific_data FROM characters WHERE guild_id = ?",
            (str(guild_id),)
        )
        rows = cur.fetchall()
        if not rows:
            return []
        for row in rows:
            name, owner_id, is_npc, system_specific_data = row
            system_specific = json.loads(system_specific_data)
            character = {
                "name": name,
                "owner_id": owner_id,
                "is_npc": is_npc,
                "fate_points": system_specific.get("fate_points", 0),
                "skills": system_specific.get("skills", {}),
                "aspects": system_specific.get("aspects", []),
                "hidden_aspects": system_specific.get("hidden_aspects", []),
                "stress": system_specific.get("stress", {}),
                "consequences": system_specific.get("consequences", []),
            }
            characters.append(character)
    return characters


def set_npc(guild_id, npc_id, npc, system="fate"):
    set_character(guild_id, npc_id, npc, system)


def add_scene_npc(guild_id, npc_id):
    with get_db() as conn:
        conn.execute("INSERT OR IGNORE INTO scenes (guild_id, npc_id) VALUES (?, ?)", (str(guild_id), str(npc_id)))
        conn.commit()


def remove_scene_npc(guild_id, npc_id):
    with get_db() as conn:
        conn.execute("DELETE FROM scenes WHERE guild_id = ? AND npc_id = ?", (str(guild_id), str(npc_id)))
        conn.commit()


def clear_scenes(guild_id):
    with get_db() as conn:
        conn.execute("DELETE FROM scenes WHERE guild_id = ?", (str(guild_id),))
        conn.commit()


def get_scenes(guild_id):
    with get_db() as conn:
        cur = conn.execute("SELECT npc_id FROM scenes WHERE guild_id = ?", (str(guild_id),))
        return [row[0] for row in cur.fetchall()]