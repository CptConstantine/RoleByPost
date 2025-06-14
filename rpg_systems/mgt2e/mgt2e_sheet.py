import discord
from core.models import BaseSheet
from data import repo
from rpg_systems.mgt2e.mgt2e_character import MGT2ECharacter


class MGT2ESheet(BaseSheet):
    def format_full_sheet(self, character: MGT2ECharacter) -> discord.Embed:
        # Use the .name property instead of get_name()
        embed = discord.Embed(
            title=f"{character.name or 'Traveller'}",
            color=discord.Color.dark_teal()
        )

        # --- Attributes ---
        attributes = character.attributes  # Use property
        if attributes:
            attr_lines = [
                f"**STR**: {attributes.get('STR', 0)}   **DEX**: {attributes.get('DEX', 0)}   **END**: {attributes.get('END', 0)}",
                f"**INT**: {attributes.get('INT', 0)}   **EDU**: {attributes.get('EDU', 0)}   **SOC**: {attributes.get('SOC', 0)}"
            ]
            embed.add_field(name="Attributes", value="\n".join(attr_lines), inline=False)
        else:
            embed.add_field(name="Attributes", value="None", inline=False)

        # --- Skills ---
        skills = character.skills  # Use property
        trained_skills = character.get_trained_skills(skills)
        if trained_skills:
            sorted_skills = sorted(trained_skills.items(), key=lambda x: (x[0]))
            skill_lines = []
            for k, v in sorted_skills:
                skill_lines.append(f"**{k}**: {v}")
            chunk = ""
            count = 1
            for line in skill_lines:
                if len(chunk) + len(line) + 1 > 1024:
                    if count == 1:
                        embed.add_field(name=f"Skills", value=chunk.strip(), inline=False)
                    chunk = ""
                    count += 1
                chunk += line + "\n"
            if chunk:
                embed.add_field(name=f"Skills {count}", value=chunk.strip(), inline=False)
        else:
            embed.add_field(name="Skills", value="None", inline=False)

        # --- Notes ---
        notes = character.notes  # Use property, which is a list
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)

        return embed

    def format_npc_scene_entry(self, npc: MGT2ECharacter, is_gm: bool):
        # Use .name and .notes properties
        lines = [f"**{npc.name or 'NPC'}**"]
        if is_gm and npc.notes:
            notes_display = "\n".join(npc.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)

    def roll(self, character: MGT2ECharacter, *, skill=None, attribute=None, formula=None):
        import random, re

        if formula:
            arg = formula.replace(" ", "").lower()
            fudge_pattern = r'(\d*)d[fF]([+-]\d+)?'
            fudge_match = re.fullmatch(fudge_pattern, arg)
            if fudge_match:
                num_dice = int(fudge_match.group(1)) if fudge_match.group(1) else 4
                modifier = int(fudge_match.group(2)) if fudge_match.group(2) else 0
                rolls = [random.choice([-1, 0, 1]) for _ in range(num_dice)]
                symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
                total = sum(rolls) + modifier
                response = f'🎲 Fudge Rolls: `{" ".join(symbols)}`'
                if modifier:
                    response += f' {"+" if modifier > 0 else ""}{modifier}'
                response += f'\n🧮 Total: {total}'
                return response
            pattern = r'(\d*)d(\d+)([+-]\d+)?'
            match = re.fullmatch(pattern, arg)
            if match:
                num_dice = int(match.group(1)) if match.group(1) else 1
                die_size = int(match.group(2))
                modifier = int(match.group(3)) if match.group(3) else 0
                if num_dice > 100 or die_size > 1000:
                    return "😵 That's a lot of dice. Try fewer."
                rolls = [random.randint(1, die_size) for _ in range(num_dice)]
                total = sum(rolls) + modifier
                response = f'🎲 Rolled: {rolls}'
                if modifier:
                    response += f' {"+" if modifier > 0 else ""}{modifier}'
                response += f'\n🧮 Total: {total}'
                return response
            return "❌ Invalid formula. Use like `2d6+3` or `4df+1`."

        if not skill or not attribute:
            return "❌ Please specify both a skill and an attribute."
        skills = character.skills  # Use property
        skill_mod = character.get_skill_modifier(skills, skill)
        attr_val = character.attributes.get(attribute.upper(), 0)  # Use property
        attr_mod = character.get_attribute_modifier(attr_val)
        rolls = [random.randint(1, 6) for _ in range(2)]
        total = sum(rolls) + skill_mod + attr_mod
        response = (
            f'🎲 2d6: {rolls} + **{skill}** ({skill_mod}) + **{attribute.upper()}** mod ({attr_mod})\n'
            f'🧮 Total: {total}'
        )
        return response