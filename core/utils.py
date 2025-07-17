from typing import List
import discord
from core.base_models import BaseCharacter, BaseEntity, EntityLinkType, EntityType
from data.repositories.repository_factory import repositories

async def _can_user_view_character(guild_id: str, user: discord.User, character: BaseCharacter) -> bool:
        """Check if a user can view a specific character based on entity type and ownership"""
        is_gm = await repositories.server.has_gm_permission(guild_id, user)

        if character.entity_type == EntityType.NPC:
            return is_gm
        elif character.entity_type == EntityType.PC:
            return str(character.owner_id) == str(user.id) or is_gm
        elif character.entity_type == EntityType.COMPANION:
            if str(character.owner_id) == str(user.id) or is_gm:
                return True
            # Check if user owns any characters that control this companion
            return await _user_controls_companion(guild_id, user.id, character)
        return False

async def _can_user_edit_character(guild_id: str, user: discord.User, character: BaseCharacter) -> bool:
        """Check if a user can edit a specific character"""
        is_gm = await repositories.server.has_gm_permission(guild_id, user)
        
        if character.entity_type == EntityType.NPC:
            return is_gm
        elif character.entity_type in [EntityType.PC, EntityType.COMPANION]:
            return str(character.owner_id) == str(user.id) or is_gm
        return False
    
async def _user_controls_companion(guild_id: str, user_id: str, companion: BaseCharacter) -> bool:
    """Check if user owns any characters that control this companion"""
    controlling_chars = repositories.link.get_parents(
        guild_id,
        companion.id,
        EntityLinkType.CONTROLS.value
    )
    
    return any(
        str(controller.owner_id) == str(user_id) 
        for controller in controlling_chars
    )

async def _resolve_character(guild_id: str, user_id: str, char_name: str = None) -> BaseCharacter:
    """Resolve character from name or get active character if no name provided"""
    if char_name:
        character = repositories.character.get_character_by_name(guild_id, char_name)
        if not character:
            raise ValueError(f"Character '{char_name}' not found.")
        return character
    else:
        character = repositories.active_character.get_active_character(guild_id, user_id)
        if not character:
            raise ValueError("No active character set. Use `/char switch` to choose one.")
        return character
    
async def _get_owner_character(guild_id: str, user_id: str, owner_character: str = None) -> BaseCharacter:
    """Get the owner character for companion creation"""
    if owner_character:
        owner_char = repositories.character.get_character_by_name(guild_id, owner_character)
        if not owner_char:
            raise ValueError(f"Character '{owner_character}' not found.")
        
        # Check permissions
        is_gm = await repositories.server.has_gm_permission(guild_id, user_id)
        if not is_gm and str(owner_char.owner_id) != str(user_id):
            raise PermissionError("You can only create companions for characters you own.")
        
        return owner_char
    else:
        # Use active character
        owner_char = repositories.active_character.get_active_character(guild_id, user_id)
        if not owner_char:
            raise ValueError("No active character found. Use `/char switch` or specify an owner character.")
        return owner_char
    
async def _set_character_avatar(character: BaseCharacter, avatar_url: str, guild_id: str) -> discord.Embed:
    """Set character avatar and return preview embed"""
    character.avatar_url = avatar_url
    system = repositories.server.get_system(guild_id)
    repositories.entity.upsert_entity(guild_id, character, system=system)
    
    embed = discord.Embed(
        title="Avatar Updated",
        description=f"Avatar for **{character.name}** has been set.",
        color=discord.Color.green()
    )
    embed.set_image(url=avatar_url)
    return embed

def _check_character_possessions(guild_id: str, character: BaseCharacter, transfer_inventory: bool = False) -> List[BaseEntity]:
    """Check if character possesses entities and validate deletion"""
    possessed_entities = repositories.link.get_children(
        guild_id, 
        character.id, 
        EntityLinkType.POSSESSES.value
    )
    
    if possessed_entities and not transfer_inventory:
        entity_names = [entity.name for entity in possessed_entities]
        raise ValueError(
            f"Cannot delete **{character.name}** because it possesses other entities: {', '.join(entity_names)}.\n"
            f"Use `transfer_inventory: True` to release these items, transfer them manually, or use `/link remove` to remove the possession links."
        )
    
    return possessed_entities

def _release_possessed_entities(guild_id: str, character: BaseCharacter) -> None:
    """Remove all POSSESSES links for a character"""
    possessed_entities = repositories.link.get_children(
        guild_id,
        character.id,
        EntityLinkType.POSSESSES.value
    )
    
    for entity in possessed_entities:
        repositories.link.delete_links_by_entities(
            guild_id,
            character.id,
            entity.id,
            EntityLinkType.POSSESSES.value
        )

def _transfer_companion_control(guild_id: str, companion: BaseCharacter, new_controller: BaseCharacter, user_id: str) -> None:
    """Transfer control of companion to new character"""
    # Remove existing control links
    existing_controllers = repositories.link.get_parents(
        guild_id,
        companion.id,
        EntityLinkType.CONTROLS.value
    )
    
    for controller in existing_controllers:
        repositories.link.delete_links_by_entities(
            guild_id,
            controller.id,
            companion.id,
            EntityLinkType.CONTROLS.value
        )
    
    # Create new control link
    repositories.link.create_link(
        guild_id,
        new_controller.id,
        companion.id,
        EntityLinkType.CONTROLS.value,
        {"transferred_by": user_id}
    )