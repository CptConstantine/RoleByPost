import discord
from core.abstract_models import BaseSheet
from rpg_systems.generic.generic_character import GenericCharacter

class GenericSheet(BaseSheet):
    def format_full_sheet(self, character: GenericCharacter) -> discord.Embed:
        embed = discord.Embed(
            title=f"{character.name or 'Character'}",
            color=discord.Color.greyple()
        )
        notes = character.notes
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)
        return embed

    def format_npc_scene_entry(self, npc: GenericCharacter, is_gm: bool):
        lines = [f"**{npc.name or 'NPC'}**"]
        if is_gm and npc.notes:
            notes_display = "\n".join(npc.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)