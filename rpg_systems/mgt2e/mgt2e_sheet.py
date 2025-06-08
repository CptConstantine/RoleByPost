import discord
from character_sheets.base_sheet import BaseSheet


class MGT2ESheet(BaseSheet):
    SYSTEM_SPECIFIC_CHARACTER = {
        "attributes": {"STR": 0, "DEX": 0, "END": 0, "INT": 0, "EDU": 0, "SOC": 0},
        "skills": {}
    }
    SYSTEM_SPECIFIC_NPC = {
        "attributes": {"STR": 0, "DEX": 0, "END": 0, "INT": 0, "EDU": 0, "SOC": 0},
        "skills": {}
    }

    def format_full_sheet(self, character: dict) -> discord.Embed:
        embed = discord.Embed(
            title=f"{character.get('name', 'Traveller')}",
            color=discord.Color.dark_teal()
        )

        # --- Attributes ---
        attributes = character.get("attributes", {})
        if attributes:
            attr_lines = [
                f"**STR**: {attributes.get('STR', 0)}   **DEX**: {attributes.get('DEX', 0)}   **END**: {attributes.get('END', 0)}",
                f"**INT**: {attributes.get('INT', 0)}   **EDU**: {attributes.get('EDU', 0)}   **SOC**: {attributes.get('SOC', 0)}"
            ]
            embed.add_field(name="Attributes", value="\n".join(attr_lines), inline=False)
        else:
            embed.add_field(name="Attributes", value="None", inline=False)

        # --- Skills ---
        skills = character.get("skills", {})
        if skills:
            sorted_skills = sorted(skills.items(), key=lambda x: (-x[1], x[0]))
            skill_lines = [f"**{k}**: {v}" for k, v in sorted_skills]
            embed.add_field(name="Skills", value="\n".join(skill_lines), inline=False)
        else:
            embed.add_field(name="Skills", value="None", inline=False)

        # --- Notes ---
        notes = character.get("notes", "")
        embed.add_field(name="Notes", value=notes if notes else "_No notes_", inline=False)

        return embed

    def format_npc_scene_entry(self, npc, is_gm):
        lines = [f"**{npc.get('name', 'NPC')}**"]
        if is_gm and npc.get("notes"):
            lines.append(f"**Notes:** *{npc['notes']}*")
        return "\n".join(lines)