import random
import discord
from core.abstract_models import BaseSheet
from rpg_systems.fate.fate_character import FateCharacter
from data import repo


class FateSheet(BaseSheet):
    def format_full_sheet(self, character: FateCharacter) -> discord.Embed:
        # Use the property .name instead of get_name()
        embed = discord.Embed(title=f"{character.name}", color=discord.Color.purple())

        # --- Aspects ---
        aspects = character.aspects
        hidden_aspects = character.hidden_aspects
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
        skills = character.skills
        if skills:
            sorted_skills = sorted(skills.items(), key=lambda x: -x[1])
            skill_lines = [f"**{k}**: +{v}" for k, v in sorted_skills]
            embed.add_field(name="Skills", value="\n".join(skill_lines), inline=False)
        else:
            embed.add_field(name="Skills", value="None", inline=False)

        # --- Stress Tracks ---
        stress = character.stress
        if stress:
            stress_lines = [
                f"**Physical**: {' '.join('[☒]' if x else '[☐]' for x in stress.get('physical', []))}",
                f"**Mental**: {' '.join('[☒]' if x else '[☐]' for x in stress.get('mental', []))}"
            ]
            embed.add_field(name="Stress", value="\n".join(stress_lines), inline=False)
        else:
            embed.add_field(name="Stress", value="None", inline=False)

        # --- Consequences ---
        consequences = character.consequences
        if consequences:
            embed.add_field(name="Consequences", value="\n".join(f"- {c}" for c in consequences), inline=False)
        else:
            embed.add_field(name="Consequences", value="None", inline=False)

        # --- Fate Points ---
        fp = character.fate_points
        embed.add_field(name="Fate Points", value=str(fp), inline=True)

        # --- Notes ---
        notes = character.notes
        # If notes is a list, join them for display
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)

        return embed

    def format_npc_scene_entry(self, npc: FateCharacter, is_gm: bool):
        aspects = npc.aspects
        hidden = npc.hidden_aspects
        aspect_lines = []
        for idx, aspect in enumerate(aspects):
            if idx in hidden:
                aspect_lines.append(f"*{aspect}*" if is_gm else "*hidden*")
            else:
                aspect_lines.append(aspect)
        aspect_str = "\n".join(aspect_lines) if aspect_lines else "_No aspects set_"
        lines = [f"**{npc.name}**\n{aspect_str}"]
        if is_gm and npc.notes:
            notes_display = "\n".join(npc.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)
    
    def roll(self, character: FateCharacter, *, skill=None, attribute=None):
        if not skill:
            return "❌ Please specify a skill."
        skill_val = character.skills.get(skill, 0)
        rolls = [random.choice([-1, 0, 1]) for _ in range(4)]
        symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
        total = sum(rolls) + skill_val
        response = f'🎲 4dF: `{" ".join(symbols)}` + **{skill}** ({skill_val})\n🧮 Total: {total}'
        return response