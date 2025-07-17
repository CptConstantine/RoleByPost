import re
import discord
from core.base_models import BaseCharacter, BaseEntity, EntityType, SystemType
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
        await message.channel.send(
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
    if content.lower().startswith("gm::"):
        # Make sure user is a GM
        if not await repositories.server.has_gm_permission(guild_id, message.author):
            await message.channel.send("❌ Only GMs can use GM narration.", delete_after=10)
            try:
                await message.delete()
            except:
                pass
            return
            
        narration_content = content[4:].strip()
        await process_gm_narration(message, narration_content)
        return
    
    # Extract type and content from message format for PC/NPC speech
    if content.lower().startswith("pc::"):
        # Check if this is a companion speech (pc::Companion Name::message)
        match = re.match(r"pc::([^:]+)::(.*)", content, re.IGNORECASE | re.DOTALL)
        if match:
            # Format: pc::Character Name::Message content
            character_name = match.group(1).strip()
            speech_content = match.group(2).strip()
            
            # Try to find the named character
            character = repositories.character.get_character_by_name(guild_id, character_name)
            
            if not character:
                await message.channel.send(f"❌ Character '{character_name}' not found.", delete_after=10)
                try:
                    await message.delete()
                except:
                    pass
                return
            
            # Check if user can speak as this character
            if not await can_user_speak_as_character(guild_id, user_id, character):
                await message.channel.send(f"❌ You cannot speak as '{character_name}'. You can only speak as your own characters or companions controlled by your characters.", delete_after=10)
                try:
                    await message.delete()
                except:
                    pass
                return
            
            alias = None  # No alias for direct character speech
            
        else:
            # Standard format: pc::message (use active character)
            character = repositories.active_character.get_active_character(guild_id, user_id)
            if not character:
                await message.channel.send("❌ You don't have an active character set. Use `/char switch` first or specify a character name with `pc::Character Name::message`.", delete_after=10)
                try:
                    await message.delete()
                except:
                    pass
                return
            
            # Extract the actual message
            speech_content = content[4:].strip()
            alias = None  # No alias for PC speech
            
    elif content.lower().startswith("npc::"):
        # Make sure user is a GM
        if not await repositories.server.has_gm_permission(guild_id, message.author):
            await message.channel.send("❌ Only GMs can speak as NPCs.", delete_after=10)
            try:
                await message.delete()
            except:
                pass
            return
        
        # Parse format: npc::Character Name::Message content
        # Or extended format: npc::Character Name::Alias::Message content
        match = re.match(r"npc::([^:]+)::([^:]+)::(.*)", content, re.IGNORECASE | re.DOTALL)
        if match:
            # Extended format with alias
            npc_name = match.group(1).strip()
            alias = match.group(2).strip()
            speech_content = match.group(3).strip()
        else:
            # Standard format without alias
            match = re.match(r"npc::([^:]+)::(.*)", content, re.IGNORECASE | re.DOTALL)
            if not match:
                await message.channel.send("❌ Format for NPC speech is: `npc::Character Name::Message content` or `npc::Character Name::Alias::Message content`", delete_after=10)
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
            
            character = factories.build_entity(
                name=npc_name,
                owner_id=str(message.author.id),
                system=SystemType.GENERIC,  # Use generic system for temporary NPCs
                entity_type=EntityType.NPC
            )
    else:
        return  # Not a narration command
    
    # Try to send the character message
    try:
        # Send using webhook to have proper avatar/username
        await send_narration_webhook(message, character, speech_content, alias)

        # Delete the original message if we have permission
        try:
            await message.delete()
        except:
            pass
    except discord.Forbidden:
        await message.channel.send("❌ I need 'Manage Webhooks' permission to send character messages.", delete_after=10)
    except Exception as e:
        await message.channel.send(f"❌ Error editing narration message: {str(e)}", delete_after=10)

async def can_user_speak_as_character(guild_id: int, user_id: int, character: BaseCharacter) -> bool:
    """Check if a user can speak as a character (PC or companion)."""
    
    # User owns the character directly
    if str(character.owner_id) == str(user_id):
        return True
    
    # If it's a companion, check if user owns any characters that control this companion
    if character.entity_type == EntityType.COMPANION:
        from core.base_models import EntityLinkType
        controlling_chars = repositories.link.get_parents(
            str(guild_id),
            character.id,
            EntityLinkType.CONTROLS.value
        )
        
        for controller in controlling_chars:
            if str(controller.owner_id) == str(user_id):
                return True
    
    return False

async def process_gm_narration(message: discord.Message, narration_content: str):
    """Process GM narration messages."""
    target_channel = message.channel
    
    # Check permissions first
    me = target_channel.guild.me
    if not target_channel.permissions_for(me).manage_webhooks:
        await message.channel.send("❌ I need 'Manage Webhooks' permission to send GM narration.", delete_after=10)
        return
    
    # Get or create the webhook
    webhook = next((wh for wh in await target_channel.webhooks() if wh.name == "RoleByPostCharacters"), None) or await target_channel.create_webhook(name="RoleByPostCharacters")
    
    # Create GM narration embed
    embed = discord.Embed(
        description=narration_content,
        color=discord.Color.dark_purple()  # Different color for GM narration
    )
    
    embed.set_author(
        name="GM",
        icon_url=message.author.display_avatar.url  # Use the GM's avatar
    )
    
    # Disable ALL mentions - users, roles, everyone, here
    allowed_mentions = discord.AllowedMentions(
        users=False,
        roles=False,
        everyone=False
    )
    
    # Send the GM narration using webhook
    try:
        await webhook.send(
            embeds=[embed],
            username="GM",
            avatar_url=message.author.display_avatar.url,
            allowed_mentions=allowed_mentions
        )
        try:
            await message.delete()
        except:
            pass
    except Exception as e:
        await message.channel.send(f"❌ Error sending GM narration: {str(e)}", delete_after=10)

async def send_narration_webhook(message: discord.Message, character: BaseCharacter, content, alias=None):
    """Edit a message using a webhook to make it appear as the character with their avatar."""

    # Check permissions first
    me = message.guild.me
    if not message.channel.permissions_for(me).manage_webhooks:
        raise discord.Forbidden("Bot doesn't have manage_webhooks permission")
    
    # Determine display name (use alias if provided)
    display_name = alias if alias else character.name
    
    # Get or create the first webhook with the name "RoleByPostCharacters"
    webhook = next((wh for wh in await message.channel.webhooks() if wh.name == "RoleByPostCharacters"), None) or await message.channel.create_webhook(name="RoleByPostCharacters")
    embed = discord.Embed(
        description=content,
        color=get_character_color(character)
    )

    # Disable ALL mentions - users, roles, everyone, here
    allowed_mentions = discord.AllowedMentions(
        users=False,
        roles=False,
        everyone=False
    )

    if character.avatar_url:
        embed.set_thumbnail(url=character.avatar_url)
        await webhook.send(
            embeds=[embed],
            username=display_name,
            avatar_url=character.avatar_url,
            allowed_mentions=allowed_mentions
        )
    else:
        await webhook.send(
            embeds=[embed],
            username=display_name,
            allowed_mentions=allowed_mentions
        )

def get_character_color(character):
    """Return a color for the character based on system and character type."""
    if character.entity_type == EntityType.NPC:
        return discord.Color.orange()
    elif character.entity_type == EntityType.COMPANION:
        return discord.Color.blue()
    else:
        return discord.Color.green()