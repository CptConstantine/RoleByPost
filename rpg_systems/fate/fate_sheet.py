import random
import discord
from character_sheets.base_sheet import BaseSheet
from data import repo


class FateSheet(BaseSheet):
    DEFAULT_SKILLS = {
        "Athletics": 0,
        "Burglary": 0,
        "Contacts": 0,
        "Crafts": 0,
        "Deceive": 0,
        "Drive": 0,
        "Empathy": 0,
        "Fight": 0,
        "Investigate": 0,
        "Lore": 0,
        "Notice": 0,
        "Physique": 0,
        "Provoke": 0,
        "Rapport": 0,
        "Resources": 0,
        "Shoot": 0,
        "Stealth": 0,
        "Will": 0
    }
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

    def apply_defaults(self, character_dict, is_npc=False, guild_id=None):
        system_defaults = self.SYSTEM_SPECIFIC_NPC if is_npc else self.SYSTEM_SPECIFIC_CHARACTER
        for key, value in system_defaults.items():
            if key == "skills":
                # Use per-guild default if available
                skills = None
                if guild_id:
                    skills = repo.get_default_skills(guild_id, "fate")
                default_skills = dict(skills) if skills else dict(self.DEFAULT_SKILLS)
                character_dict.setdefault("skills", {})
                for skill, val in default_skills.items():
                    if skill not in character_dict["skills"]:
                        character_dict["skills"][skill] = val
            else:
                if key not in character_dict:
                    character_dict[key] = value


    @staticmethod
    def parse_and_validate_skills(skills_str):
        """Parse a skills string like 'Fight:2, Stealth:1' into a dict. Add Fate-specific validation here."""
        skills_dict = {}
        for entry in skills_str.split(","):
            if ":" in entry:
                k, v = entry.split(":", 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    continue
        # Add Fate-specific validation here if needed (e.g., pyramid structure)
        return skills_dict


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
    
    def roll(self, character, *, skill=None, attribute=None):
        if not skill:
            return "❌ Please specify a skill."
        skill_val = character.get("skills", {}).get(skill, 0)
        rolls = [random.choice([-1, 0, 1]) for _ in range(4)]
        symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
        total = sum(rolls) + skill_val
        response = f'🎲 4dF: `{" ".join(symbols)}` + **{skill}** ({skill_val})\n🧮 Total: {total}'
        return response