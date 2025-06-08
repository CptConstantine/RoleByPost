import discord
from character_sheets.base_sheet import BaseSheet


class FateSheet(BaseSheet):
    SYSTEM_SPECIFIC_CHARACTER = {
        "fate_points": 3,
        "skills": {},
        "aspects": [],
        "hidden_aspects": [],
        "stress": {"physical": [False, False, False], "mental": [False, False]},
        "consequences": ["Mild: None", "Moderate: None", "Severe: None"]
    }

    SYSTEM_SPECIFIC_NPC = {
        "fate_points": 0,
        "skills": {},
        "aspects": [],
        "hidden_aspects": [],
        "stress": {"physical": [False, False, False], "mental": [False, False]},
        "consequences": ["Mild: None"]
    }


    def format_full_sheet(self, character: dict) -> discord.Embed:
        embed = discord.Embed(title=f"{character.get('name')}", color=discord.Color.purple())

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
                f"**Physical**: {' '.join('[☒]' if x else '[☐]' for x in stress.get('physical', []))}",
                f"**Mental**: {' '.join('[☒]' if x else '[☐]' for x in stress.get('mental', []))}"
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

        # --- Notes ---
        notes = character.get("notes", "")
        embed.add_field(name="Notes", value=notes if notes else "_No notes_", inline=False)

        return embed


    def format_npc_scene_entry(self, npc, is_gm):
        aspects = npc.get("aspects", [])
        hidden = npc.get("hidden_aspects", [])
        aspect_lines = []
        for idx, aspect in enumerate(aspects):
            if idx in hidden:
                aspect_lines.append(f"*{aspect}*" if is_gm else "*hidden*")
            else:
                aspect_lines.append(aspect)
        aspect_str = "\n".join(aspect_lines) if aspect_lines else "_No aspects set_"
        lines = [f"**{npc['name']}**\n{aspect_str}"]
        if is_gm and npc.get("notes"):
            lines.append(f"**Notes:** *{npc['notes']}*")
        return "\n".join(lines)