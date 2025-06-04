
import json
import os
import discord


DATA_FILE = 'data/characters.json'

def load_data():
    if not os.path.exists(DATA_FILE):
        return {
            "gm_ids": [],
            "characters": {},
            "current_scene": {
                "npc_ids": []
            }
        }
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def is_gm(user_id):
    data = load_data()
    return str(user_id) in map(str, data["gm_ids"])

def set_gm(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data["gm_ids"]:
        data["gm_ids"].append(uid)
        save_data(data)

def get_character(char_id):
    data = load_data()
    return data["characters"].get(str(char_id)) or data.get("npcs", {}).get(char_id)

def set_character(char_id, character):
    data = load_data()
    data["characters"][str(char_id)] = character
    save_data(data)

def set_npc(char_id, npc):
    data = load_data()
    data["npcs"][str(char_id)] = npc
    save_data(data)


def format_full_sheet(name: str, character: dict) -> discord.Embed:
    embed = discord.Embed(title=f"{name}'s Character Sheet", color=discord.Color.purple())

    # --- Aspects ---
    aspects = character.get("aspects", {})
    embed.add_field(name="High Concept", value=aspects.get("high_concept", "Not set"), inline=False)
    embed.add_field(name="Trouble", value=aspects.get("trouble", "Not set"), inline=False)

    free_aspects = aspects.get("free", [])
    if free_aspects:
        for idx, a in enumerate(free_aspects, 1):
            embed.add_field(name=f"Free Aspect {idx}", value=a, inline=False)
    else:
        embed.add_field(name="Free Aspects", value="None", inline=False)

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


