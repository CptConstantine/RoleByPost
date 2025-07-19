import discord
from discord import app_commands
from discord.ext import commands
from commands.autocomplete import owned_character_npc_or_companion_autocomplete, owned_companion_autocomplete, all_pc_names_autocomplete, owned_player_character_names_autocomplete
from core.base_models import AccessType, BaseCharacter, EntityType, EntityLinkType
from core.command_decorators import gm_role_required, no_ic_channels, player_or_gm_role_required
from core.utils import _can_user_edit_character, _can_user_view_character, _check_character_possessions, _get_character_by_name_or_nickname, _resolve_character, _set_character_avatar
from data.repositories.repository_factory import repositories
import core.factories as factories

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
    @player_or_gm_role_required()
    @no_ic_channels()
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
        
        await interaction.followup.send(f'📝 Created {system.value.upper()} character: **{char_name}**.', ephemeral=True)

    @create_group.command(name="npc", description="GM: Create a new NPC with a required name")
    @app_commands.describe(
        npc_name="The name of the new NPC"
    )
    @gm_role_required()
    @no_ic_channels()
    async def create_npc(self, interaction: discord.Interaction, npc_name: str, owner: str = None):
        await interaction.response.defer(ephemeral=True)
        
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
    @player_or_gm_role_required()
    @no_ic_channels()
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
            # Show only user's characters and companions they control
            user_characters = []
            for char in characters:
                if char.owner_id == str(interaction.user.id):
                    user_characters.append(char)
                elif char.entity_type == EntityType.COMPANION:
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
                        user_characters.append(char)
            
            characters = user_characters
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
                
                info = f"**{char.name}** ({char.entity_type.value.upper()})"
                if controlled_by:
                    info += f"\n  *Controlled by: {', '.join([c.name for c in controlled_by])}*"
                if controls_entities:
                    info += f"\n  *Controls: {', '.join([e.name for e in controls_entities])}*"

                character_info.append(info)
            
            embed.description = "\n\n".join(character_info)
        else:
            # Simple list grouped by type
            pcs = [char for char in characters if char.entity_type == EntityType.PC]
            npcs = [char for char in characters if char.entity_type == EntityType.NPC]
            companions = [char for char in characters if char.entity_type == EntityType.COMPANION]
            
            if pcs:
                pc_lines = []
                for char in pcs:
                    pc_lines.append(f"• {char.name}")
                
                embed.add_field(
                    name=f"Player Characters ({len(pcs)})",
                    value="\n".join(pc_lines)[:1024],
                    inline=False
                )
            
            if companions:
                companion_lines = []
                for char in companions:
                    # Get who controls this companion
                    controlling_chars = repositories.link.get_parents(
                        str(interaction.guild.id),
                        char.id,
                        EntityLinkType.CONTROLS.value
                    )
                    
                    if controlling_chars:
                        controller_names = [c.name for c in controlling_chars]
                        companion_lines.append(f"• {char.name} (controlled by {', '.join(controller_names)})")
                    else:
                        companion_lines.append(f"• {char.name} (no controller)")

                embed.add_field(
                    name=f"Companions ({len(companions)})",
                    value="\n".join(companion_lines)[:1024],
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
    @app_commands.autocomplete(char_name=owned_character_npc_or_companion_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def delete_character(self, interaction: discord.Interaction, char_name: str, transfer_inventory: bool = False):
        character = repositories.character.get_character_by_name(interaction.guild.id, char_name)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return

        # Use utility method for permission checking
        if not await _can_user_edit_character(str(interaction.guild.id), interaction.user, character):
            await interaction.response.send_message("❌ You don't have permission to delete this character.", ephemeral=True)
            return

        # Check if this character possesses other entities (extract to utility method)
        possessed_entities = _check_character_possessions(str(interaction.guild.id), character, transfer_inventory)
        
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
    @app_commands.autocomplete(char_name=owned_character_npc_or_companion_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def sheet(self, interaction: discord.Interaction, char_name: str = None):
        try:
            character = await _resolve_character(str(interaction.guild.id), str(interaction.user.id), char_name)
            
            if not await _can_user_edit_character(str(interaction.guild.id), interaction.user, character):
                await interaction.response.send_message("❌ You don't have permission to edit this character.", ephemeral=True)
                return
            
            is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            sheet_view = character.get_sheet_edit_view(interaction.user.id, is_gm=is_gm)
            embed = character.format_full_sheet(interaction.guild.id)
            
            await interaction.response.send_message(embed=embed, view=sheet_view, ephemeral=True)
            
        except ValueError as e:
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
        except PermissionError as e:
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)

    @character_group.command(name="transfer", description="GM: Transfer a PC to another player")
    @app_commands.describe(
        char_name="Name of the character to transfer",
        new_owner="The user to transfer ownership to"
    )
    @app_commands.autocomplete(char_name=all_pc_names_autocomplete)
    @gm_role_required()
    @no_ic_channels()
    async def transfer(self, interaction: discord.Interaction, char_name: str, new_owner: discord.Member):
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
    @app_commands.autocomplete(char_name=owned_player_character_names_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
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

    @character_group.command(name="set-nickname", description="Set or remove a nickname for a character.")
    @app_commands.describe(
        full_char_name="The character to set the nickname for.",
        nickname="The nickname to add. Leave blank to remove all nicknames."
    )
    @app_commands.autocomplete(full_char_name=owned_character_npc_or_companion_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def set_nickname(self, interaction: discord.Interaction, full_char_name: str, nickname: str = None):
        """Add or remove nicknames for a character."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            character = await _resolve_character(str(interaction.guild.id), str(interaction.user.id), full_char_name)
            
            if not await _can_user_edit_character(str(interaction.guild.id), interaction.user, character):
                await interaction.followup.send("❌ You don't have permission to set this character's nickname.", ephemeral=True)
                return

            if nickname:
                nickname = nickname.strip()
                # Check for conflicts
                existing_char = await _get_character_by_name_or_nickname(str(interaction.guild.id), nickname)
                if existing_char and existing_char.id != character.id:
                    await interaction.followup.send(f"❌ The name or nickname `{nickname}` is already in use by **{existing_char.name}**.", ephemeral=True)
                    return

                repositories.character_nickname.add_nickname(str(interaction.guild.id), character.id, nickname)
                nicknames = repositories.character_nickname.get_all_for_character(str(interaction.guild.id), character.id)
                nicknames = [n.nickname for n in nicknames]
                await interaction.followup.send(f"✅ Set a nickname for **{character.name}** to `{nickname}`.\nNicknames for **{character.name}**: {', '.join(nicknames)}", ephemeral=True)
            else:
                # Remove nickname
                system = repositories.character_nickname.remove_all_for_character(str(interaction.guild.id), character.id)
                await interaction.followup.send(f"✅ Removed all nicknames for **{character.name}**.", ephemeral=True)

        except ValueError as e:
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
        except PermissionError as e:
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)

    @character_group.command(name="nickname-list", description="List all nicknames for a character.")
    @app_commands.describe(
        full_char_name="The character to list nicknames for."
    )
    @app_commands.autocomplete(full_char_name=owned_character_npc_or_companion_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def nickname_list(self, interaction: discord.Interaction, full_char_name: str):
        """List all nicknames for a character."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            character = await _resolve_character(str(interaction.guild.id), str(interaction.user.id), full_char_name)
            
            if not await _can_user_view_character(str(interaction.guild.id), interaction.user, character):
                await interaction.followup.send("❌ You don't have permission to view this character's nicknames.", ephemeral=True)
                return

            nicknames = repositories.character_nickname.get_all_for_character(str(interaction.guild.id), character.id)
            
            if not nicknames:
                await interaction.followup.send(f"**{character.name}** has no nicknames.", ephemeral=True)
                return
            
            nickname_list = [f"• `{n.nickname}`" for n in nicknames]
            
            embed = discord.Embed(
                title=f"📝 Nicknames for {character.name}",
                description="\n".join(nickname_list),
                color=discord.Color.blue()
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)
        except PermissionError as e:
            await interaction.followup.send(f"❌ {str(e)}", ephemeral=True)

    @character_group.command(name="set-avatar", description="Set a character's avatar via file upload or URL (Defaults to active character if no name given)")
    @app_commands.describe(
        char_name="Optional: Character/NPC name (defaults to your active character)",
        avatar_url="Optional: URL to an image for your character's avatar",
        file="Optional: Upload an image file instead of providing a URL"
    )
    @app_commands.autocomplete(char_name=owned_character_npc_or_companion_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def character_setavatar(self, interaction: discord.Interaction, char_name: str = None, avatar_url: str = None, file: discord.Attachment = None):
        """Set an avatar image for your character or an NPC (if GM)"""
        
        # Must provide either URL or file, but not both
        if (avatar_url and file) or (not avatar_url and not file):
            await interaction.response.send_message("❌ Please provide either an avatar URL or upload a file, but not both.", ephemeral=True)
            return
        
        try:
            character = await _resolve_character(str(interaction.guild.id), str(interaction.user.id), char_name)
            
            if not await _can_user_edit_character(str(interaction.guild.id), interaction.user, character):
                await interaction.response.send_message("❌ You don't have permission to set this character's avatar.", ephemeral=True)
                return
                
            if file:
                if not file.content_type or not file.content_type.startswith('image/'):
                    await interaction.response.send_message("❌ Please upload a valid image file.", ephemeral=True)
                    return
                final_avatar_url = file.url
            else:
                if not avatar_url.startswith(("http://", "https://")):
                    await interaction.response.send_message("❌ Please provide a valid image URL starting with http:// or https://", ephemeral=True)
                    return
                final_avatar_url = avatar_url
            
            embed = await _set_character_avatar(character, final_avatar_url, str(interaction.guild.id))
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except ValueError as e:
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
        except PermissionError as e:
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
    
    @create_group.command(name="companion", description="Create a companion for your character")
    @app_commands.describe(
        companion_name="The name of the companion",
        owner_character="The character that will control this companion (defaults to your active character)"
    )
    @app_commands.autocomplete(owner_character=owned_player_character_names_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def create_companion(self, interaction: discord.Interaction, companion_name: str, owner_character: str = None):
        """Create a companion controlled by a character"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Determine the owner character
            if owner_character:
                owner_char = _resolve_character(str(interaction.guild.id), str(interaction.user.id), owner_character)
                
                # Check if user owns this character or is GM
                if not _can_user_edit_character(str(interaction.guild.id), interaction.user, owner_char):
                    await interaction.followup.send("❌ You can only create companions for characters you own.", ephemeral=True)
                    return
            else:
                # Use active character
                owner_char = repositories.active_character.get_active_character(str(interaction.guild.id), str(interaction.user.id))
                if not owner_char:
                    await interaction.followup.send("❌ No active character found. Use `/char switch` or specify an owner character.", ephemeral=True)
                    return
            
            # Check if companion name already exists
            existing = repositories.character.get_character_by_name(str(interaction.guild.id), companion_name)
            if existing:
                await interaction.followup.send(f"❌ A character named '{companion_name}' already exists.", ephemeral=True)
                return
            
            system = repositories.server.get_system(str(interaction.guild.id))
            companion = factories.build_and_save_entity(
                system=system,
                entity_type=EntityType.COMPANION,
                name=companion_name,
                owner_id=str(owner_char.owner_id),
                guild_id=str(interaction.guild.id),
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
        except ValueError as e:
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)
        except PermissionError as e:
            await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)

    @companion_group.command(name="list", description="List companions controlled by your characters")
    @app_commands.describe(character_name="Optional: Show companions for a specific character")
    @app_commands.autocomplete(character_name=owned_player_character_names_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def list_companions(self, interaction: discord.Interaction, character_name: str = None):
        """List companions controlled by user's characters"""
        await interaction.response.defer(ephemeral=True)
        
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if character_name:
            # List companions for specific character
            character = repositories.character.get_character_by_name(str(interaction.guild.id), character_name)
            if not character:
                await interaction.followup.send(f"❌ Character '{character_name}' not found.", ephemeral=True)
                return
            
            # Check permissions
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
            user_chars = repositories.character.get_user_characters(str(interaction.guild.id), str(interaction.user.id), include_npcs=is_gm)
            
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
    @app_commands.autocomplete(companion_name=owned_companion_autocomplete)
    @app_commands.autocomplete(new_controller=owned_character_npc_or_companion_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
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
        new_owner_member = interaction.guild.get_member(int(new_controller_char.owner_id))
        new_owner_is_gm = False
        if new_owner_member:
            new_owner_is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), new_owner_member)
        if new_controller_char.entity_type == EntityType.PC and not new_owner_is_gm:
            companion.set_access_type(AccessType.PUBLIC)
            system = repositories.server.get_system(interaction.guild.id)
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