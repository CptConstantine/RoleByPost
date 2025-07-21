import discord
from discord import app_commands
from data.repositories.repository_factory import repositories

async def active_player_characters_plus_fate_points_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for active player characters in the current guild with fate points"""
    active_chars = repositories.active_character.get_all_active_characters(interaction.guild.id)
    
    # Filter characters based on permissions and add fate points
    options = list[str]()
    for c in active_chars:
        fate_points = getattr(c, 'fate_points', 0)
        display_name = f"{c.name} ({fate_points} FP)"
        options.append(display_name)
    
    # Filter by current input
    filtered_options = [n for n in options if current.lower() in n.lower()]
    return [app_commands.Choice(name=name, value=name) for name in filtered_options[:25]]