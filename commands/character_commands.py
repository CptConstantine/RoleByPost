from typing import List
import uuid
import discord
from discord import app_commands
from discord.ext import commands
from core.base_models import AccessType, BaseCharacter, BaseEntity, EntityType, EntityLinkType
from data.repositories.repository_factory import repositories
import core.factories as factories
import json

async def pc_switch_name_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repositories.character.get_all_by_guild(interaction.guild.id)
    pcs = [
        c for c in all_chars
        if not c.is_npc and str(c.owner_id) == str(interaction.user.id)
    ]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def pc_name_gm_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repositories.character.get_all_by_guild(interaction.guild.id)
    pcs = [c for c in all_chars if not c.is_npc]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def character_or_npc_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for commands that can target PCs, NPCs, and companions"""
    all_chars = repositories.character.get_all_by_guild(interaction.guild.id)
    
    # Check if user is GM
    is_gm = await repositories.server.has_gm_permission(interaction.guild.id, interaction.user)
    
    # Filter characters based on permissions
    options = []
    for c in all_chars:
        if c.entity_type == EntityType.NPC and is_gm:
            # GMs can see all NPCs
            options.append(c.name)
        elif c.entity_type == EntityType.PC and (str(c.owner_id) == str(interaction.user.id) or is_gm):
            # Users can see their own PCs, GMs can see all PCs
            options.append(c.name)
        elif c.entity_type == EntityType.COMPANION:
            # Users can see companions they own or that are controlled by their characters
            if str(c.owner_id) == str(interaction.user.id) or is_gm:
                options.append(c.name)
            else:
                # Check if user owns any characters that control this companion
                controlling_chars = repositories.link.get_parents(
                    str(interaction.guild.id),
                    c.id,
                    EntityLinkType.CONTROLS.value
                )
                
                user_controls_companion = any(
                    str(controller.owner_id) == str(interaction.user.id) 
                    for controller in controlling_chars
                )
                
                if user_controls_companion:
                    options.append(c.name)
    
    # Filter by current input
    filtered_options = [name for name in options if current.lower() in name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in filtered_options[:25]]

async def companion_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete specifically for companion entities"""
    all_chars = repositories.character.get_all_by_guild(interaction.guild.id)
    
    # Check if user is GM
    is_gm = await repositories.server.has_gm_permission(interaction.guild.id, interaction.user)
    
    # Filter for companions only
    options = []
    for c in all_chars:
        if c.entity_type == EntityType.COMPANION:
            # Users can see companions they own or that are controlled by their characters
            if str(c.owner_id) == str(interaction.user.id) or is_gm:
                options.append(c.name)
            else:
                # Check if user owns any characters that control this companion
                controlling_chars = repositories.link.get_parents(
                    str(interaction.guild.id),
                    c.id,
                    EntityLinkType.CONTROLS.value
                )
                
                user_controls_companion = any(
                    str(controller.owner_id) == str(interaction.user.id) 
                    for controller in controlling_chars
                )
                
                if user_controls_companion:
                    options.append(c.name)
    
    # Filter by current input
    filtered_options = [name for name in options if current.lower() in name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in filtered_options[:25]]

async def owner_characters_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for entities that can own other entities"""
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    
    if is_gm:
        # GMs can see all entities as potential owners
        characters = repositories.character.get_all_by_guild(str(interaction.guild.id))
    else:
        # Users can only use their own entities as owners
        characters = repositories.character.get_user_characters(str(interaction.guild.id), str(interaction.user.id))
    
    # Filter by current input
    filtered_entities = [
        char for char in characters 
        if current.lower() in char.name.lower()
    ]
    
    return [
        app_commands.Choice(name=f"{char.name} ({char.entity_type.value})", value=char.name)
        for char in filtered_entities[:25]
    ]

async def multi_character_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Enhanced autocomplete that handles comma-separated character names"""
    # Parse what's already been typed
    parts = current.split(',')
    current_typing = parts[-1].strip() if parts else current
    already_selected = [part.strip() for part in parts[:-1]] if len(parts) > 1 else []
    
    # Get available characters (excluding already selected)
    all_chars = repositories.character.get_all_by_guild(str(interaction.guild.id))
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    
    available_chars = []
    for char in all_chars:
        # Skip if already selected
        if char.name in already_selected:
            continue
            
        # Check if current typing matches
        if current_typing and current_typing.lower() not in char.name.lower():
            continue
            
        # Check permissions
        if char.entity_type == EntityType.NPC and is_gm:
            available_chars.append(char.name)
        elif char.entity_type == EntityType.PC and (str(char.owner_id) == str(interaction.user.id) or is_gm):
            available_chars.append(char.name)
        elif char.entity_type == EntityType.COMPANION:
            if str(char.owner_id) == str(interaction.user.id) or is_gm:
                available_chars.append(char.name)
            else:
                # Check if user owns any characters that control this companion
                controlling_chars = repositories.link.get_parents(
                    str(interaction.guild.id),
                    char.id,
                    EntityLinkType.CONTROLS.value
                )
                
                user_controls_companion = any(
                    str(controller.owner_id) == str(interaction.user.id) 
                    for controller in controlling_chars
                )
                
                if user_controls_companion:
                    available_chars.append(char.name)
    
    # Build the choice values (preserve what's already typed + add new selection)
    prefix = ', '.join(already_selected)
    if prefix:
        prefix += ', '
    
    choices = []
    
    # If nothing is being typed and we have selected characters, show a summary
    if not current_typing and already_selected:
        summary_text = f"Selected: {', '.join(already_selected)} (continue typing...)"
        choices.append(app_commands.Choice(name=summary_text, value=current))
    
    # Add available characters
    for char_name in available_chars[:24]:  # Leave room for summary if needed
        full_value = prefix + char_name
        
        # Create display name showing context
        if already_selected:
            display_name = f"{', '.join(already_selected)}, {char_name}"
        else:
            display_name = char_name
            
        # Truncate display name if too long (Discord limit is 100 chars)
        if len(display_name) > 97:
            display_name = display_name[:94] + "..."
            
        choices.append(app_commands.Choice(name=display_name, value=full_value))
    
    return choices

class CharacterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    character_group = app_commands.Group(name="char", description="Character management commands")

    companion_group = app_commands.Group(name="companion", description="Companion management commands", parent=character_group)
    
    create_group = app_commands.Group(name="create", description="Create characters and NPCs", parent=character_group)
    
    @create_group.command(name="pc", description="Create a new player character (PC) with a required name")
    @app_commands.describe(
        char_name="The name of your new character"
    )
    async def create_pc(self, interaction: discord.Interaction, char_name: str):
        await interaction.response.defer(ephemeral=True)
        
        existing = repositories.character.get_character_by_name(interaction.guild.id, char_name)
        if existing:
            await interaction.followup.send(f"❌ A character named `{char_name}` already exists.", ephemeral=True)
            return
        
        is_gm = await repositories.server.has_gm_permission(interaction.guild.id, interaction.user)

        system = repositories.server.get_system(interaction.guild.id)
        character = factories.build_and_save_entity(
            system=system,
            entity_type=EntityType.PC,
            name=char_name,
            owner_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            access_type=AccessType.PUBLIC if not is_gm else AccessType.GM_ONLY
        )
        
        # Set as active if no active character exists
        if not repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id):
            repositories.active_character.set_active_character(str(interaction.guild.id), str(interaction.user.id), character.id)
        
        await interaction.followup.send(f'📝 Created {system.upper()} character: **{char_name}**.', ephemeral=True)

    @create_group.command(name="npc", description="GM: Create a new NPC with a required name")
    @app_commands.describe(
        npc_name="The name of the new NPC"
    )
    async def create_npc(self, interaction: discord.Interaction, npc_name: str, owner: str = None):
        await interaction.response.defer(ephemeral=True)
        if not await repositories.server.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.followup.send("❌ Only GMs can create NPCs.", ephemeral=True)
            return
        
        existing = repositories.character.get_character_by_name(interaction.guild.id, npc_name)
        if existing:
            await interaction.followup.send(f"❌ An NPC named `{npc_name}` already exists.", ephemeral=True)
            return
    
        system = repositories.server.get_system(interaction.guild.id)
        character = factories.build_and_save_entity(
            system=system,
            entity_type=EntityType.NPC,
            name=npc_name,
            owner_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            access_type=AccessType.GM_ONLY
        )
        
        await interaction.followup.send(f"🤖 Created NPC: **{npc_name}**", ephemeral=True)

    @character_group.command(name="list", description="List characters and NPCs")
    @app_commands.describe(
        show_npcs="Show NPCs (GM only)",
        show_links="Show ownership links"
    )
    async def list_characters(self, interaction: discord.Interaction, show_npcs: bool = False, show_links: bool = False):
        await interaction.response.defer(ephemeral=True)
        
        system = repositories.server.get_system(interaction.guild.id)
        
        # Get characters based on filters
        characters = repositories.character.get_all_by_guild(interaction.guild.id, system)
        title = "Characters"
        
        # Filter by user's permissions
        if not await repositories.server.has_gm_permission(interaction.guild.id, interaction.user):
            if show_npcs:
                await interaction.followup.send("❌ Only GMs can view NPCs.", ephemeral=True)
                return
            # Show only user's characters
            characters = [char for char in characters if char.owner_id == str(interaction.user.id)]
        else:
            # GM can see all, but filter NPCs if requested
            if not show_npcs:
                characters = [char for char in characters if not char.is_npc]
            
            if show_npcs:
                title += " (NPCs included)"

        if not characters:
            await interaction.followup.send("No characters found.", ephemeral=True)
            return

        # Create embed
        embed = discord.Embed(title=title, color=discord.Color.blue())
        
        if show_links:
            # Show detailed information for CONTROLS links
            character_info = []
            for char in characters:
                controlled_by = repositories.link.get_parents(
                    str(interaction.guild.id), 
                    char.id, 
                    EntityLinkType.CONTROLS.value
                )
                
                controls_entities = repositories.link.get_children(
                    str(interaction.guild.id),
                    char.id,
                    EntityLinkType.CONTROLS.value
                )
                
                info = f"**{char.name}** ({'NPC' if char.is_npc else 'PC'})"
                if controlled_by:
                    info += f"\n  *Controlled by: {', '.join([c.name for c in controlled_by])}*"
                if controls_entities:
                    info += f"\n  *Controls: {', '.join([e.name for e in controls_entities])}*"

                character_info.append(info)
            
            embed.description = "\n\n".join(character_info)
        else:
            # Simple list grouped by type
            pcs = [char for char in characters if not char.is_npc]
            npcs = [char for char in characters if char.is_npc]
            
            if pcs:
                pc_lines = []
                for char in pcs:
                    pc_lines.append(f"• {char.name}")
                
                embed.add_field(
                    name=f"Player Characters ({len(pcs)})",
                    value="\n".join(pc_lines)[:1024],
                    inline=False
                )
            
            if npcs:
                npc_lines = []
                for char in npcs:
                    npc_lines.append(f"• {char.name}")

                embed.add_field(
                    name=f"NPCs ({len(npcs)})",
                    value="\n".join(npc_lines)[:1024],
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @character_group.command(name="delete", description="Delete a character or NPC")
    @app_commands.describe(
        char_name="Name of the character/NPC to delete",
        transfer_inventory="If true, releases possessed items instead of blocking deletion"
    )
    @app_commands.autocomplete(char_name=character_or_npc_autocomplete)
    async def delete_character(self, interaction: discord.Interaction, char_name: str, transfer_inventory: bool = False):
        character = repositories.character.get_character_by_name(interaction.guild.id, char_name)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return

        # Check permissions
        if character.is_npc and not await repositories.server.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can delete NPCs.", ephemeral=True)
            return
        
        if not character.is_npc and character.owner_id != str(interaction.user.id):
            if not await repositories.server.has_gm_permission(interaction.guild.id, interaction.user):
                await interaction.response.send_message("❌ You can only delete your own characters.", ephemeral=True)
                return

        # Check if this character possesses other entities
        possessed_entities = repositories.link.get_children(
            str(interaction.guild.id), 
            character.id, 
            EntityLinkType.POSSESSES.value
        )
        
        if possessed_entities and not transfer_inventory:
            entity_names = [entity.name for entity in possessed_entities]
            await interaction.response.send_message(
                f"❌ Cannot delete **{char_name}** because it possesses other entities: {', '.join(entity_names)}.\n"
                f"Use `transfer_inventory: True` to release these items, transfer them manually, or use `/link remove` to remove the possession links.",
                ephemeral=True
            )
            return

        # Show confirmation
        view = ConfirmDeleteCharacterView(character, transfer_inventory)
        
        confirmation_msg = f"⚠️ Are you sure you want to delete **{char_name}** ({'NPC' if character.is_npc else 'PC'})?\n"
        
        if possessed_entities and transfer_inventory:
            entity_names = [entity.name for entity in possessed_entities]
            confirmation_msg += f"\n**This will also release the following possessed items:**\n{', '.join(entity_names)}\n"
        
        confirmation_msg += "\nThis action cannot be undone."
        
        await interaction.response.send_message(
            confirmation_msg,
            view=view,
            ephemeral=True
        )

    @character_group.command(name="sheet", description="View a character, NPC, or companion's full sheet")
    @app_commands.describe(char_name="Leave blank to view your active character, or enter a character/NPC/companion name")
    @app_commands.autocomplete(char_name=character_or_npc_autocomplete)
    async def sheet(self, interaction: discord.Interaction, char_name: str = None):
        character = None
        if not char_name:
            character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
            if not character:
                await interaction.response.send_message("❌ No active character set. Use `/character switch` to choose one.", ephemeral=True)
                return
        else:
            character = repositories.character.get_character_by_name(interaction.guild.id, char_name)
            if not character:
                await interaction.response.send_message("❌ Character not found.", ephemeral=True)
                return

        # Check permissions based on entity type
        is_gm = await repositories.server.has_gm_permission(interaction.guild.id, interaction.user)
        
        if character.entity_type == EntityType.NPC:
            # NPCs can only be viewed by GMs
            if not is_gm:
                await interaction.response.send_message("❌ Only the GM can view NPCs.", ephemeral=True)
                return
        elif character.entity_type == EntityType.COMPANION:
            # Companions can be viewed by their owner or by the owner of characters that control them
            if str(character.owner_id) != str(interaction.user.id) and not is_gm:
                # Check if user owns any characters that control this companion
                controlling_chars = repositories.link.get_parents(
                    str(interaction.guild.id),
                    character.id,
                    EntityLinkType.CONTROLS.value
                )
                
                user_controls_companion = any(
                    str(controller.owner_id) == str(interaction.user.id) 
                    for controller in controlling_chars
                )
                
                if not user_controls_companion:
                    await interaction.response.send_message(
                        "❌ You can only view companions you own or that are controlled by your characters.", 
                        ephemeral=True
                    )
                    return
        elif character.entity_type == EntityType.PC:
            # PCs can be viewed by their owner or GM
            if str(character.owner_id) != str(interaction.user.id) and not is_gm:
                await interaction.response.send_message("❌ You can only view your own characters.", ephemeral=True)
                return

        # Get appropriate sheet view based on entity type
        sheet_view = character.get_sheet_edit_view(interaction.user.id, is_gm=is_gm)
        
        embed = character.format_full_sheet(interaction.guild.id)
        await interaction.response.send_message(embed=embed, view=sheet_view, ephemeral=True)

    @character_group.command(name="transfer", description="GM: Transfer a PC to another player")
    @app_commands.describe(
        char_name="Name of the character to transfer",
        new_owner="The user to transfer ownership to"
    )
    @app_commands.autocomplete(char_name=pc_name_gm_autocomplete)
    async def transfer(self, interaction: discord.Interaction, char_name: str, new_owner: discord.Member):
        if not await repositories.server.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can transfer characters.", ephemeral=True)
            return
            
        character = repositories.character.get_character_by_name(interaction.guild.id, char_name)
        if not character or character.is_npc:
            await interaction.response.send_message("❌ PC not found.", ephemeral=True)
            return
            
        character.owner_id = new_owner.id
        
        # Set access to public when transferring to a player
        is_gm = await repositories.server.has_gm_permission(interaction.guild.id, new_owner)
        if not is_gm:
            character.set_access_type(AccessType.PUBLIC)
        
        system = repositories.server.get_system(interaction.guild.id)
        repositories.entity.upsert_entity(interaction.guild.id, character, system=system)
        await interaction.response.send_message(
            f"✅ Ownership of `{char_name}` transferred to {new_owner.display_name} and set to public access.", 
            ephemeral=True
        )

    @character_group.command(name="switch", description="Set your active character (PC) for this server")
    @app_commands.describe(char_name="The name of your character to set as active")
    @app_commands.autocomplete(char_name=pc_switch_name_autocomplete)
    async def switch(self, interaction: discord.Interaction, char_name: str):
        user_chars = repositories.character.get_user_characters(interaction.guild.id, interaction.user.id)
        character = next(
            (c for c in user_chars if c.name.lower() == char_name.lower()),
            None
        )
        if not character:
            await interaction.response.send_message(f"❌ You don't have a character named `{char_name}`.", ephemeral=True)
            return
            
        repositories.active_character.set_active_character(str(interaction.guild.id), str(interaction.user.id), character.id)
        await interaction.response.send_message(f"✅ `{char_name}` is now your active character.", ephemeral=True)

    @character_group.command(name="setavatar", description="Set your character's avatar image")
    @app_commands.describe(
        avatar_url="URL to an image for your character's avatar",
        char_name="Optional: Character/NPC name (defaults to your active character)"
    )
    @app_commands.autocomplete(char_name=character_or_npc_autocomplete)
    async def character_setavatar(self, interaction: discord.Interaction, avatar_url: str, char_name: str = None):
        """Set an avatar image URL for your character or an NPC (if GM)"""
        
        # Determine which character to set avatar for
        character = None
        if char_name:
            # User specified a character name
            character = repositories.character.get_character_by_name(interaction.guild.id, char_name)
            if not character:
                await interaction.response.send_message(f"❌ Character '{char_name}' not found.", ephemeral=True)
                return
                
            # Check permissions
            if character.is_npc:
                # Only GMs can set NPC avatars
                if not await repositories.server.has_gm_permission(interaction.guild.id, interaction.user):
                    await interaction.response.send_message("❌ Only GMs can set NPC avatars.", ephemeral=True)
                    return
            else:
                # Only the owner can set PC avatars (unless GM)
                is_gm = await repositories.server.has_gm_permission(interaction.guild.id, interaction.user)
                if str(character.owner_id) != str(interaction.user.id) and not is_gm:
                    await interaction.response.send_message("❌ You can only set avatars for your own characters.", ephemeral=True)
                    return
        else:
            # No character specified, use active character
            character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
            if not character:
                await interaction.response.send_message("❌ You don't have an active character set. Use `/character switch` to choose one or specify a character name.", ephemeral=True)
                return
        
        # Basic URL validation
        if not avatar_url.startswith(("http://", "https://")):
            await interaction.response.send_message("❌ Please provide a valid image URL starting with http:// or https://", ephemeral=True)
            return
        
        # Save the avatar URL to the character
        character.avatar_url = avatar_url
        system = repositories.server.get_system(interaction.guild.id)
        repositories.entity.upsert_entity(interaction.guild.id, character, system=system)

        # Show a preview
        embed = discord.Embed(
            title="Avatar Updated",
            description=f"Avatar for **{character.name}** has been set.",
            color=discord.Color.green()
        )
        embed.set_image(url=avatar_url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @character_group.command(name="narration", description="Get help with character narration formatting")
    async def character_narration_help(self, interaction: discord.Interaction):
        """Display help information about speaking as characters and GM narration"""
        
        embed = discord.Embed(
            title="📢 Character Narration Guide",
            description="How to speak as characters or narrate as a GM in play-by-post games",
            color=discord.Color.blue()
        )

        # Check if there are any channel restrictions set up
        channel_permissions = repositories.channel_permissions.get_all_channel_permissions(str(interaction.guild.id))
        has_restrictions = len(channel_permissions) > 0
        
        embed.add_field(
            name="Speaking as Your Character",
            value=(
                "**Basic Format:** `pc::Your character's message here`\n"
                "Uses your currently active character. Set with `/character switch`.\n\n"
                "**Speaking as a Specific Character/Companion:**\n"
                "`pc::Character Name::Message content`\n"
                "Example: `pc::Fluffy::*growls menacingly at the stranger*`\n\n"
                "You can speak as:\n"
                "• Your own player characters\n"
                "• Companions you own\n"
                "• Companions controlled by your characters"
            ),
            inline=False
        )
        
        embed.add_field(
            name="For GMs: Speaking as NPCs",
            value=(
                "**Basic Format**\n"
                "`npc::Character Name::Message content`\n"
                "Example: `npc::Bartender::What'll it be, stranger?`\n\n"
                "**With Custom Display Name**\n"
                "`npc::Character Name::Display Name::Message content`\n"
                "Example: `npc::Mysterious Figure::Hooded Stranger::Keep your voice down!`\n\n"
                "**On-the-fly NPCs**\n"
                "If you use a name that doesn't exist in the database, the bot will still create a temporary character to display the message."
            ),
            inline=False
        )
        
        embed.add_field(
            name="GM Narration",
            value=(
                "As a GM, you can narrate scenes with a distinctive format:\n"
                "`gm::Your narration text here`\n"
                "Example: `gm::The ground trembles as thunder rumbles overhead. The storm is getting closer.`\n\n"
                "GM narration appears with a purple embed and your avatar as the GM."
            ),
            inline=False
        )

        # Add channel restrictions info if they exist
        if has_restrictions:
            embed.add_field(
                name="⚠️ Channel Restrictions",
                value=(
                    "Narration commands (`pc::`, `npc::`, `gm::`) are **not allowed** in **Out-of-Character (OOC)** channels.\n"
                    "Use these commands in **In-Character (IC)** or **Unrestricted** channels to maintain immersion.\n\n"
                    "GMs can configure channel types with `/setup channel type`."
                ),
                inline=False
            )
        
        embed.add_field(
            name="Text Formatting",
            value=(
                "You can use Discord's standard formatting in your messages:\n"
                "• *Italics*: `*text*` or `_text_`\n"
                "• **Bold**: `**text**`\n"
                "• __Underline__: `__text__`\n"
                "• ~~Strikethrough~~: `~~text~~`\n"
                "• `Code`: `` `text` ``\n"
                "• ```Block quotes```: \\```text\\```"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Character Avatars",
            value=(
                "Set your character's avatar with the command:\n"
                "`/character setavatar [url]`\n\n"
                "This avatar will appear with your character's messages."
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @create_group.command(name="companion", description="Create a companion for your character")
    @app_commands.describe(
        companion_name="The name of the companion",
        owner_character="The character that will control this companion (defaults to your active character)"
    )
    @app_commands.autocomplete(owner_character=pc_switch_name_autocomplete)
    async def create_companion(self, interaction: discord.Interaction, companion_name: str, owner_character: str = None):
        """Create a companion controlled by a character"""
        await interaction.response.defer(ephemeral=True)
        
        # Determine the owner character
        if owner_character:
            owner_char = repositories.character.get_character_by_name(str(interaction.guild.id), owner_character)
            if not owner_char:
                await interaction.followup.send(f"❌ Character '{owner_character}' not found.", ephemeral=True)
                return
            
            # Check if user owns this character or is GM
            is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            if not is_gm and str(owner_char.owner_id) != str(interaction.user.id):
                await interaction.followup.send("❌ You can only create companions for characters you own.", ephemeral=True)
                return
        else:
            # Use active character
            owner_char = repositories.active_character.get_active_character(str(interaction.guild.id), str(interaction.user.id))
            if not owner_char:
                await interaction.followup.send("❌ No active character found. Use `/character switch` or specify an owner character.", ephemeral=True)
                return
        
        # Check if companion name already exists
        existing = repositories.character.get_character_by_name(str(interaction.guild.id), companion_name)
        if existing:
            await interaction.followup.send(f"❌ A character named '{companion_name}' already exists.", ephemeral=True)
            return
        
        # Get system and companion class
        system = repositories.server.get_system(str(interaction.guild.id))
        companion = factories.build_and_save_entity(
            system=system,
            entity_type=EntityType.COMPANION,
            name=companion_name,
            owner_id=str(owner_char.owner_id)
        )

        # Create CONTROLS link
        repositories.link.create_link(
            str(interaction.guild.id),
            owner_char.id,
            companion.id,
            EntityLinkType.CONTROLS.value,
            {"created_by": str(interaction.user.id)}
        )
        
        await interaction.followup.send(
            f"🐾 Created companion: **{companion_name}** controlled by **{owner_char.name}**",
            ephemeral=True
        )

    @companion_group.command(name="list", description="List companions controlled by your characters")
    @app_commands.describe(character_name="Optional: Show companions for a specific character")
    @app_commands.autocomplete(character_name=pc_switch_name_autocomplete)
    async def list_companions(self, interaction: discord.Interaction, character_name: str = None):
        """List companions controlled by user's characters"""
        await interaction.response.defer(ephemeral=True)
        
        if character_name:
            # List companions for specific character
            character = repositories.character.get_character_by_name(str(interaction.guild.id), character_name)
            if not character:
                await interaction.followup.send(f"❌ Character '{character_name}' not found.", ephemeral=True)
                return
            
            # Check permissions
            is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            if not is_gm and str(character.owner_id) != str(interaction.user.id):
                await interaction.followup.send("❌ You can only view companions for characters you own.", ephemeral=True)
                return
            
            companions = repositories.link.get_children(
                str(interaction.guild.id),
                character.id,
                EntityLinkType.CONTROLS.value
            )
            companions = [c for c in companions if c.entity_type == EntityType.COMPANION]
            
            if not companions:
                await interaction.followup.send(f"**{character.name}** has no companions.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"🐾 Companions controlled by {character.name}",
                color=discord.Color.blue()
            )
            
            companion_list = [f"• {comp.name}" for comp in companions]
            embed.description = "\n".join(companion_list)
            
        else:
            # List all companions controlled by user's characters
            user_chars = repositories.character.get_user_characters(str(interaction.guild.id), str(interaction.user.id))
            
            all_companions = []
            for char in user_chars:
                companions = repositories.link.get_children(
                    str(interaction.guild.id),
                    char.id,
                    EntityLinkType.CONTROLS.value
                )
                companions = [c for c in companions if c.entity_type == EntityType.COMPANION]
                
                for comp in companions:
                    all_companions.append((char.name, comp.name))
            
            if not all_companions:
                await interaction.followup.send("You have no companions.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title="🐾 Your Companions",
                color=discord.Color.blue()
            )
            
            # Group by controlling character
            by_character = {}
            for char_name, comp_name in all_companions:
                if char_name not in by_character:
                    by_character[char_name] = []
                by_character[char_name].append(comp_name)
            
            for char_name, comp_names in by_character.items():
                embed.add_field(
                    name=f"Controlled by {char_name}",
                    value="\n".join([f"• {name}" for name in comp_names]),
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @companion_group.command(name="transfer", description="Transfer control of a companion to another character")
    @app_commands.describe(
        companion_name="The companion to transfer",
        new_controller="The character that will control the companion"
    )
    @app_commands.autocomplete(companion_name=companion_autocomplete)
    @app_commands.autocomplete(new_controller=character_or_npc_autocomplete)
    async def transfer_companion(self, interaction: discord.Interaction, companion_name: str, new_controller: str):
        """Transfer control of a companion to another character"""
        await interaction.response.defer(ephemeral=True)
        
        # Get companion
        companion = repositories.character.get_character_by_name(str(interaction.guild.id), companion_name)
        if not companion or companion.entity_type != EntityType.COMPANION:
            await interaction.followup.send(f"❌ Companion '{companion_name}' not found.", ephemeral=True)
            return
        
        # Get new controller
        new_controller_char = repositories.character.get_character_by_name(str(interaction.guild.id), new_controller)
        if not new_controller_char:
            await interaction.followup.send(f"❌ Character '{new_controller}' not found.", ephemeral=True)
            return
        
        # Check permissions
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm and str(companion.owner_id) != str(interaction.user.id):
            await interaction.followup.send("❌ You can only transfer companions you own.", ephemeral=True)
            return
        
        # Remove existing control links
        existing_controllers = repositories.link.get_parents(
            str(interaction.guild.id),
            companion.id,
            EntityLinkType.CONTROLS.value
        )
        
        for controller in existing_controllers:
            repositories.link.delete_links_by_entities(
                str(interaction.guild.id),
                controller.id,
                companion.id,
                EntityLinkType.CONTROLS.value
            )
        
        # Create new control link
        repositories.link.create_link(
            str(interaction.guild.id),
            new_controller_char.id,
            companion.id,
            EntityLinkType.CONTROLS.value,
            {"transferred_by": str(interaction.user.id)}
        )
        
        # Set access to public if transferring to a PC (player character)
        new_owner_is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), new_controller_char.owner_id)
        if new_controller_char.entity_type == EntityType.PC and not new_owner_is_gm:
            companion.set_access_type(AccessType.PUBLIC)
            system = repositories.server.get_system(str(interaction.guild.id))
            repositories.entity.upsert_entity(str(interaction.guild.id), companion, system)
            
            await interaction.followup.send(
                f"✅ **{new_controller}** now controls **{companion_name}** and companion access set to public.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"✅ **{new_controller}** now controls **{companion_name}**",
                ephemeral=True
            )

class ConfirmDeleteCharacterView(discord.ui.View):
    def __init__(self, character: BaseCharacter, transfer_inventory: bool = False):
        super().__init__(timeout=60)
        self.character = character
        self.transfer_inventory = transfer_inventory

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.transfer_inventory:
            # Remove all POSSESSES links for this character
            possessed_entities = repositories.link.get_children(
                str(interaction.guild.id),
                self.character.id,
                EntityLinkType.POSSESSES.value
            )
            
            for entity in possessed_entities:
                repositories.link.delete_links_by_entities(
                    str(interaction.guild.id),
                    self.character.id,
                    entity.id,
                    EntityLinkType.POSSESSES.value
                )
        
        # Delete the character (this will also delete all remaining links)
        repositories.character.delete_character(interaction.guild.id, self.character.id)
        
        delete_msg = f"✅ Deleted character **{self.character.name}**."
        if self.transfer_inventory:
            delete_msg += " Released all possessed items."
        
        await interaction.response.edit_message(
            content=delete_msg,
            view=None
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="❌ Deletion cancelled.",
            view=None
        )

async def setup_character_commands(bot: commands.Bot):
    await bot.add_cog(CharacterCommands(bot))