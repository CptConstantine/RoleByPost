import discord
from discord import app_commands
from discord.ext import commands
from data.repositories.repository_factory import repositories

@app_commands.context_menu(name="View Character Sheet")
async def view_character_sheet_from_user_context(interaction: discord.Interaction, user: discord.User):
    """Context menu command to view a character sheet from a user."""
    character = repositories.active_character.get_active_character(interaction.guild.id, user.id)
    if not character:
        await interaction.response.send_message("❌ No active character set for this user.", ephemeral=True)
        return
    
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    view = character.get_sheet_edit_view(interaction.user.id, is_gm=is_gm, guild_id=str(interaction.guild.id))
    if isinstance(view, discord.ui.LayoutView):
        await interaction.response.send_message(view=view, ephemeral=True)
    else:
        embed = character.format_full_sheet(interaction.guild.id, is_gm=is_gm)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    return

async def setup_user_context_menu_commands(bot: commands.Bot):
    # Add context menus to the command tree
    bot.tree.add_command(view_character_sheet_from_user_context)