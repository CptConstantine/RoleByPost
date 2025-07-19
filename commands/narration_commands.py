import discord
from discord import app_commands
from discord.ext import commands
from commands.character_commands import owner_characters_autocomplete
from commands.narration import can_user_speak_as_character
from core.command_decorators import player_or_gm_role_required
from core.utils import _get_character_by_name_or_nickname
from data.repositories.repository_factory import repositories


async def ic_channels_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for IC channels in the current guild"""
    if not interaction.guild:
        return []
    
    # Get all IC channels for this guild
    all_channels = repositories.channel_permissions.get_all_channel_permissions(str(interaction.guild.id))
    if not all_channels:
        return []
    ic_channel_ids = [channel.channel_id for channel in all_channels if channel.channel_type == 'ic']

    # Filter channels the user can see and match current input
    choices = []
    for channel_id in ic_channel_ids:
        channel = interaction.guild.get_channel(int(channel_id))
        if channel and channel.permissions_for(interaction.user).view_channel:
            channel_name = channel.name
            if current.lower() in channel_name.lower():
                choices.append(app_commands.Choice(
                    name=f"#{channel_name}",
                    value=str(channel.id)
                ))
    
    return choices[:25]  # Discord limit


class NarrationCommands(commands.Cog):
    """Command to set or clear a sticky character for narration."""
    
    def __init__(self, bot):
        self.bot = bot

    narration_group = app_commands.Group(
        name="narration",
        description="Commands related to narration"
    )

    @narration_group.command(name="sticky", description="Set or clear sticky character for a specific channel")
    @app_commands.describe(
        character="Character name to stick, or 'off' to disable",
        channel="IC channel to set sticky character for (defaults to current channel)"
    )
    @app_commands.autocomplete(character=owner_characters_autocomplete, channel=ic_channels_autocomplete)
    @player_or_gm_role_required()
    async def narration_sticky(self, interaction: discord.Interaction, character: str = None, channel: str = None):
        # Determine target channel
        if channel:
            target_channel = interaction.guild.get_channel(int(channel))
            if not target_channel:
                await interaction.response.send_message("❌ Channel not found.", ephemeral=True)
                return
            
            # Verify it's an IC channel
            channel_type = repositories.channel_permissions.get_channel_type(
                str(interaction.guild.id), 
                str(target_channel.id)
            )
            if channel_type != 'ic':
                await interaction.response.send_message("❌ Sticky narration can only be set for IC channels.", ephemeral=True)
                return
                
            target_channel_id = str(target_channel.id)
            channel_mention = target_channel.mention
        else:
            # Default to current channel, but verify it's IC
            channel_type = repositories.channel_permissions.get_channel_type(
                str(interaction.guild.id), 
                str(interaction.channel.id)
            )
            if channel_type != 'ic':
                await interaction.response.send_message("❌ Current channel is not an IC channel. Please specify an IC channel.", ephemeral=True)
                return
                
            target_channel_id = str(interaction.channel.id)
            channel_mention = interaction.channel.mention

        if character is None:
            # Show current status
            current = repositories.sticky_narration.get_sticky_character(
                str(interaction.guild.id),
                str(interaction.user.id),
                target_channel_id
            )
            if current:
                await interaction.response.send_message(
                    f"🔒 Sticky character in {channel_mention}: **{current}**", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"No sticky character set in {channel_mention}.", 
                    ephemeral=True
                )
            return
        
        if character.lower() == "off":
            success = repositories.sticky_narration.clear_sticky_character(
                str(interaction.guild.id),
                str(interaction.user.id),
                target_channel_id
            )
            if success:
                await interaction.response.send_message(
                    f"✅ Sticky character disabled in {channel_mention}.", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"No sticky character was set in {channel_mention}.", 
                    ephemeral=True
                )
        else:
            # Validate character exists and user can speak as them
            char = await _get_character_by_name_or_nickname(str(interaction.guild.id), character)
            if not char or not await can_user_speak_as_character(str(interaction.guild.id), interaction.user.id, char):
                await interaction.response.send_message("❌ Character not found or you can't speak as them.", ephemeral=True)
                return
                
            repositories.sticky_narration.set_sticky_character(
                str(interaction.guild.id),
                str(interaction.user.id),
                target_channel_id,
                char.id
            )
            await interaction.response.send_message(
                f"🔒 Sticky character set to **{character}** in {channel_mention}.", 
                ephemeral=True
            )

async def setup_narration_commands(bot: commands.Bot):
    await bot.add_cog(NarrationCommands(bot))