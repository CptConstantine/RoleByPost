

import discord


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

    return embed