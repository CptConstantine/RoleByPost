import logging
from functools import wraps
from typing import List, Callable, Union
import discord
from data.repositories.repository_factory import repositories

def channel_restricted(allowed_types: List[str]):
    """
    Decorator to restrict commands to specific channel types.
    
    Args:
        allowed_types: List of allowed channel types ('ic', 'ooc', 'gm', 'unrestricted')
    
    Usage:
        @channel_restricted(['ic', 'unrestricted'])
        async def my_command(self, interaction: discord.Interaction):
            # Command implementation
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            # Get the channel type for this channel
            channel_type = repositories.channel_permissions.get_channel_type(
                str(interaction.guild.id), 
                str(interaction.channel.id)
            )
            
            # If no channel type is set, treat as unrestricted
            if channel_type is None:
                channel_type = 'unrestricted'
            
            # Check if the command is allowed in this channel type
            if channel_type not in allowed_types:
                # Create a friendly error message
                channel_type_names = {
                    'ic': 'In-Character (IC)',
                    'ooc': 'Out-of-Character (OOC)',
                    'gm': 'GM Only',
                    'unrestricted': 'Unrestricted'
                }
                
                allowed_names = [channel_type_names.get(t, t) for t in allowed_types]
                current_name = channel_type_names.get(channel_type, channel_type)
                
                await interaction.response.send_message(
                    f"❌ This command is not allowed in **{current_name}** channels.\n"
                    f"💡 This command can be used in: **{', '.join(allowed_names)}** channels.",
                    ephemeral=True
                )
                return
            
            # Channel type is allowed, proceed with the command
            return await func(self, interaction, *args, **kwargs)
        
        return wrapper
    return decorator

def gm_channel_only():
    """
    Decorator shortcut for commands that should only work in GM channels.
    """
    return channel_restricted(['gm', 'unrestricted'])

def ic_channel_only():
    """
    Decorator shortcut for commands that should only work in IC channels.
    """
    return channel_restricted(['ic', 'unrestricted'])

def ooc_channel_only():
    """
    Decorator shortcut for commands that should only work in OOC channels.
    """
    return channel_restricted(['ooc', 'unrestricted'])

def no_ic_channels():
    """
    Decorator shortcut for commands that should NOT work in IC channels.
    """
    return channel_restricted(['ooc', 'gm', 'unrestricted'])

def gm_role_required():
    """
    Decorator shortcut for commands that require GM role.
    Uses the server's configured GM role.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            # Check if user has GM permissions using existing system
            if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
                await interaction.response.send_message(
                    "❌ This command requires GM permissions.",
                    ephemeral=True
                )
                return
            
            return await func(self, interaction, *args, **kwargs)
        
        return wrapper
    return decorator

def admin_required():
    """
    Decorator shortcut for commands that require administrator permissions.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ This command requires administrator permissions.",
                    ephemeral=True
                )
                return
            
            return await func(self, interaction, *args, **kwargs)
        
        return wrapper
    return decorator

def player_or_gm_role_required():
    """
    Decorator shortcut for commands that require player role.
    Uses the server's configured player role.
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, interaction: discord.Interaction, *args, **kwargs):
            # Check if user has player permissions using existing system
            if not await repositories.server.has_player_or_gm_permission(str(interaction.guild.id), interaction.user):
                await interaction.response.send_message(
                    "❌ This command requires player or GM permissions.",
                    ephemeral=True
                )
                return
            
            return await func(self, interaction, *args, **kwargs)
        
        return wrapper
    return decorator