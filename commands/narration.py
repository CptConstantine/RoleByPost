import re
import discord
from core.models import BaseCharacter
import core.factories as factories
from data.repositories.repository_factory import repositories

async def process_narration(message: discord.Message):
    """Process messages with special prefixes for character speech and GM narration."""
    if not message.guild:
        return  # Only process in guild channels
    
    # Check channel restrictions for narration
    channel_type = repositories.channel_permissions.get_channel_type(
        str(message.guild.id), 
        str(message.channel.id)
    )
    
    # If channel is set to OOC, don't allow narration prefixes
    if channel_type == 'ooc':
        await message.reply(
            "❌ Character narration (`pc::`, `npc::`, `gm::`) is not allowed in **Out-of-Character (OOC)** channels.\n"
            "💡 Use these commands in **In-Character (IC)** or **Unrestricted** channels.",
            delete_after=10
        )
        # Don't delete the original message in this case - let the user see the error and handle it
        return
        
    content = message.content
    guild_id = message.guild.id
    user_id = message.author.id
    
    # Check for GM narration first
    if content.startswith("gm::"):
        # Make sure user is a GM
        if not await repositories.server.has_gm_permission(guild_id, message.author):
            await message.reply("❌ Only GMs can use GM narration.", delete_after=10)
            try:
                await message.delete()
            except:
                pass
            return
            
        narration_content = content[4:].strip()
        await process_gm_narration(message, narration_content)
        return
    
    # Extract type and content from message format for PC/NPC speech
    if content.startswith("pc::"):
        # Get user's active character
        character = repositories.active_character.get_active_character(guild_id, user_id)
        if not character:
            await message.reply("❌ You don't have an active character set. Use `/character switch` first.", delete_after=10)
            try:
                await message.delete()
            except:
                pass
            return
        
        # Extract the actual message
        speech_content = content[4:].strip()
        alias = None  # No alias for PC speech
        
    elif content.startswith("npc::"):
        # Make sure user is a GM
        if not await repositories.server.has_gm_permission(guild_id, message.author):
            await message.reply("❌ Only GMs can speak as NPCs.", delete_after=10)
            try:
                await message.delete()
            except:
                pass
            return
        
        # Parse format: npc::Character Name::Message content
        # Or extended format: npc::Character Name::Alias::Message content
        match = re.match(r"npc::([^:]+)::([^:]+)::(.*)", content)
        if match:
            # Extended format with alias
            npc_name = match.group(1).strip()
            alias = match.group(2).strip()
            speech_content = match.group(3).strip()
        else:
            # Standard format without alias
            match = re.match(r"npc::([^:]+)::(.*)", content)
            if not match:
                await message.reply("❌ Format for NPC speech is: `npc::Character Name::Message content` or `npc::Character Name::Alias::Message content`", delete_after=10)
                try:
                    await message.delete()
                except:
                    pass
                return
                
            npc_name = match.group(1).strip()
            speech_content = match.group(2).strip()
            alias = None
        
        # Find the NPC
        character = repositories.character.get_character_by_name(guild_id, npc_name)
        
        # Handle case where NPC doesn't exist - create a temporary character object
        if not character:
            # If we have an alias, we'll use the NPC name as a temporary character
            if not alias:
                alias = npc_name  # Use the NPC name as an alias if no alias was provided
            
            # Create a temporary character for display
            character_dict = BaseCharacter.build_entity_dict(f"temp_{npc_name.lower().replace(' ', '_')}", npc_name, user_id, is_npc=True, notes=[])
            CharacterClass = factories.get_specific_character(repositories.server.get_system(guild_id))
            character = CharacterClass.from_dict(character_dict)
    else:
        return  # Not a narration command
    
    target_channel = message.channel
    
    # Try to send the character message
    try:
        # Send using webhook to have proper avatar/username
        await send_character_webhook(target_channel, character, speech_content, alias)
        
        # Delete the original message if we have permission
        try:
            await message.delete()
        except:
            pass
    except discord.Forbidden:
        await message.reply("❌ I need 'Manage Webhooks' permission to send character messages.", delete_after=10)
    except Exception as e:
        await message.reply(f"❌ Error sending message: {str(e)}", delete_after=10)

async def process_gm_narration(message, narration_content):
    """Process GM narration messages."""
    target_channel = message.channel
    
    # Create GM narration embed
    embed = discord.Embed(
        description=narration_content,
        color=discord.Color.dark_purple()  # Different color for GM narration
    )
    
    embed.set_author(
        name="GM",
        icon_url=message.author.display_avatar.url  # Use the GM's avatar
    )
    
    # Send the GM narration
    try:
        await target_channel.send(embed=embed)
        try:
            await message.delete()
        except:
            pass
    except Exception as e:
        await message.reply(f"❌ Error sending GM narration: {str(e)}", delete_after=10)

async def send_character_webhook(channel, character: BaseCharacter, content, alias=None):
    """Send a message using a webhook to make it appear as the character with their avatar."""
    
    # Check permissions first
    me = channel.guild.me
    if not channel.permissions_for(me).manage_webhooks:
        raise discord.Forbidden("Bot doesn't have manage_webhooks permission")
    
    # Determine display name (use alias if provided)
    display_name = alias if alias else character.name
    
    # Get or create the first webhook with the name "PlayByPostBotCharacters"
    webhook = next((wh for wh in await channel.webhooks() if wh.name == "PlayByPostBotCharacters"), None) or await channel.create_webhook(name="PlayByPostBotCharacters")
    embed = discord.Embed(
        description=content,
        color=get_character_color(character)
    )
    if character.avatar_url:
        embed.set_thumbnail(url=character.avatar_url)
        await webhook.send(
            embeds=[embed],
            username=display_name,
            avatar_url=character.avatar_url,
            allowed_mentions=discord.AllowedMentions(everyone=False)
        )
    else:
        # Use a default avatar if character has no avatar
        #url=get_default_avatar(character)
        #embed.set_thumbnail(url=url)
        await webhook.send(
            embeds=[embed],
            username=display_name,
            #avatar_url=url,
            allowed_mentions=discord.AllowedMentions(everyone=False)
        )

def get_character_color(character):
    """Return a color for the character based on system and character type."""
    if character.is_npc:
        return discord.Color.orange()  # NPCs get orange
    else:
        return discord.Color.green()   # PCs get green

def get_default_avatar(character):
    """Return a default avatar URL based on character's system or type."""
    # This could be expanded to return different default avatars
    # based on character system, type, etc.
    return "https://cdn.discordapp.com/embed/avatars/0.png"