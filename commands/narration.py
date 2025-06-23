import re
import discord
from core.models import BaseCharacter
from data import repo
import core.factories as factories

async def process_narration(message):
    """Process messages with special prefixes for character speech and GM narration."""
    if not message.guild:
        return  # Only process in guild channels
        
    content = message.content
    guild_id = message.guild.id
    user_id = message.author.id
    
    # Check for GM narration first
    if content.startswith("gm::"):
        # Make sure user is a GM
        if not repo.is_gm(guild_id, user_id):
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
        character = repo.get_active_character(guild_id, user_id)
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
        if not repo.is_gm(guild_id, user_id):
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
        character = repo.get_character(guild_id, npc_name)
        
        # Handle case where NPC doesn't exist - create a temporary character object
        if not character:
            # If we have an alias, we'll use the NPC name as a temporary character
            if not alias:
                alias = npc_name  # Use the NPC name as an alias if no alias was provided
            
            # Create a temporary character for display
            character = BaseCharacter.create_base_character(f"temp_{npc_name.lower().replace(' ', '_')}", npc_name, user_id, is_npc=True, notes=[])
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
    embed.set_thumbnail(url=character.avatar_url)
    await webhook.send(
        embeds=[embed],
        username=display_name,
        avatar_url=character.avatar_url,
        allowed_mentions=discord.AllowedMentions(everyone=False)
    )

def get_character_color(character):
    """Return a color for the character based on system and character type."""
    system = character.data.get("system", "generic") if hasattr(character, "data") else "generic"
    
    if system == "fate":
        return discord.Color.blue()
    elif system == "mgt2e":
        return discord.Color.dark_teal()
    elif hasattr(character, "is_npc") and character.is_npc:
        return discord.Color.dark_orange()
    else:
        return discord.Color.purple()

def get_default_avatar(character):
    """Return a default avatar URL based on character's system or type."""
    system = character.data.get("system", "generic") if hasattr(character, "data") else "generic"
    
    if system == "fate":
        return "https://i.imgur.com/JQ5kUTy.png"  # Fate dice icon
    elif system == "mgt2e":
        return "https://i.imgur.com/zsQlxz7.png"  # Traveller icon
    elif hasattr(character, "is_npc") and character.is_npc:
        return "https://i.imgur.com/ZLnfuEX.png"  # Generic NPC icon
    else:
        return "https://i.imgur.com/hVKYkR5.png"  # Generic PC icon