import json
import os
import discord


CHARACTERS_FILE = 'data/characters.json'
SERVER_FILE = 'data/server.json'
SCENES_FILE = 'data/scenes.json'

def load_character_data():
    default_character_data = {
        "characters": {},
        "npcs": {}
    }
    if not os.path.exists(CHARACTERS_FILE):
        # Ensure the data directory exists
        os.makedirs(os.path.dirname(CHARACTERS_FILE), exist_ok=True)
        # Save the default structure
        with open(CHARACTERS_FILE, 'w') as f:
            json.dump(default_character_data, f, indent=2)
        return default_character_data
    with open(CHARACTERS_FILE, 'r') as f:
        return json.load(f)

def load_server_data():
    default_server_data = {
        "gm_ids": []
    }
    if not os.path.exists(SERVER_FILE):
        os.makedirs(os.path.dirname(SERVER_FILE), exist_ok=True)
        with open(SERVER_FILE, 'w') as f:
            json.dump(default_server_data, f, indent=2)
        return default_server_data
    with open(SERVER_FILE, 'r') as f:
        return json.load(f)
    
def load_scene_data():
    default_scene_data = {
        "current_scene": {
            "npc_ids": []
        }
    }
    if not os.path.exists(SCENES_FILE):
        os.makedirs(os.path.dirname(SCENES_FILE), exist_ok=True)
        with open(SCENES_FILE, 'w') as f:
            json.dump(default_scene_data, f, indent=2)
        return default_scene_data
    with open(SCENES_FILE, 'r') as f:
        return json.load(f)

def save_character_data(data):
    with open(CHARACTERS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def save_server_data(server_data):
    with open(SERVER_FILE, 'w') as f:
        json.dump(server_data, f, indent=2)

def save_scene_data(scene_data):
    with open(SCENES_FILE, 'w') as f:
        json.dump(scene_data, f, indent=2)

def is_gm(user_id):
    server_data = load_server_data()
    return str(user_id) in map(str, server_data["gm_ids"])

def set_gm(user_id):
    data = load_server_data()
    uid = str(user_id)
    if uid not in data["gm_ids"]:
        data["gm_ids"].append(uid)
        save_server_data(data)

def get_character(char_id):
    data = load_character_data()
    return data["characters"].get(str(char_id)) or data.get("npcs", {}).get(char_id)

def set_character(char_id, character):
    data = load_character_data()
    data["characters"][str(char_id)] = character
    save_character_data(data)

def set_npc(char_id, npc):
    data = load_character_data()
    data["npcs"][str(char_id)] = npc
    save_character_data(data)


def format_full_sheet(name: str, character: dict) -> discord.Embed:
    embed = discord.Embed(title=f"{name}'s Character Sheet", color=discord.Color.purple())

    # --- Aspects ---
    aspects = character.get("aspects", [])
    hidden_aspects = character.get("hidden_aspects", [])
    if aspects:
        aspect_lines = []
        for idx, aspect in enumerate(aspects):
            if idx in hidden_aspects:
                aspect_lines.append(f"- *{aspect}*")
            else:
                aspect_lines.append(f"- {aspect}")
        embed.add_field(name="Aspects", value="\n".join(aspect_lines), inline=False)
    else:
        embed.add_field(name="Aspects", value="None", inline=False)

    # --- Skills ---
    skills = character.get("skills", {})
    if skills:
        sorted_skills = sorted(skills.items(), key=lambda x: -x[1])
        skill_lines = [f"**{k}**: +{v}" for k, v in sorted_skills]
        embed.add_field(name="Skills", value="\n".join(skill_lines), inline=False)
    else:
        embed.add_field(name="Skills", value="None", inline=False)

    # --- Stress Tracks ---
    stress = character.get("stress", {})
    if stress:
        stress_lines = [
            f"**Physical**: {' '.join('[☒]' if x else '[☐]' for x in stress['physical'])}",
            f"**Mental**: {' '.join('[☒]' if x else '[☐]' for x in stress['mental'])}"
        ]
        embed.add_field(name="Stress", value="\n".join(stress_lines), inline=False)
    else:
        embed.add_field(name="Stress", value="None", inline=False)

    # --- Consequences ---
    consequences = character.get("consequences", [])
    if consequences:
        embed.add_field(name="Consequences", value="\n".join(f"- {c}" for c in consequences), inline=False)
    else:
        embed.add_field(name="Consequences", value="None", inline=False)

    # --- Fate Points ---
    fp = character.get("fate_points", 0)
    embed.add_field(name="Fate Points", value=str(fp), inline=True)

    return embed


