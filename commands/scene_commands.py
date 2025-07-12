import logging
import discord
from discord.ext import commands
from discord import app_commands
from core import shared_views
from data.repositories.repository_factory import repositories

import core.factories as factories

async def npc_name_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repositories.character.get_all_by_guild(str(interaction.guild.id))
    active_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
    
    if not active_scene:
        return []

    scene_npcs = set(repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), str(active_scene.scene_id)))
    npcs = [
        c for c in all_chars
        if c.is_npc and c.id not in scene_npcs and current.lower() in c.name.lower()
    ]
    options = [c.name for c in npcs]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def npcs_in_scene_autocomplete(interaction: discord.Interaction, current: str):
    active_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
    if not active_scene:
        return []
    all_chars = repositories.scene_npc.get_scene_npcs(str(interaction.guild.id), active_scene.scene_id)
    
    npcs = [c for c in all_chars]
    options = [c.name for c in npcs]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def scene_name_autocomplete(interaction: discord.Interaction, current: str):
    scenes = repositories.scene.get_all_scenes(str(interaction.guild.id))
    return [
        app_commands.Choice(name=f"{s.name}{'✓' if s.is_active else ''}", value=s.name)
        for s in scenes
        if current.lower() in s.name.lower()
    ][:25]

class SceneCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    scene_group = app_commands.Group(name="scene", description="Scene management commands")

    @scene_group.command(name="create", description="Create a new scene")
    @app_commands.describe(name="Name for the new scene")
    async def scene_create(self, interaction: discord.Interaction, name: str):
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can create scenes.", ephemeral=True)
            return
            
        if len(name) > 100:
            await interaction.response.send_message("❌ Scene name must be 100 characters or less.", ephemeral=True)
            return
            
        # Check if scene with this name already exists
        existing_scene = repositories.scene.get_by_name(str(interaction.guild.id), name)
        if existing_scene:
            await interaction.response.send_message(f"❌ A scene named '{name}' already exists.", ephemeral=True)
            return
            
        scene_id = repositories.scene.create_scene(str(interaction.guild.id), name)
        await interaction.response.send_message(f"✅ Created new scene: **{name}**", ephemeral=True)

    @scene_group.command(name="switch", description="Switch to a different scene")
    @app_commands.describe(scene_name="Name of the scene to switch to")
    @app_commands.autocomplete(scene_name=scene_name_autocomplete)
    async def scene_switch(self, interaction: discord.Interaction, scene_name: str):
        """Switch to a different scene"""
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can switch scenes.", ephemeral=True)
            return
            
        scene = repositories.scene.get_by_name(str(interaction.guild.id), scene_name)
        if not scene:
            await interaction.response.send_message(f"❌ Scene '{scene_name}' not found.", ephemeral=True)
            return
            
        # Get the previously active scene
        old_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
        
        # Set the new scene as active
        repositories.scene.set_active_scene(str(interaction.guild.id), scene.scene_id)
        
        # Use defer to prevent the interaction from timing out
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Step 1: Unpin any existing pinned scene messages
        pinned_messages = repositories.pinned_scene.get_all_pinned_messages(str(interaction.guild.id))
        
        for pinned_msg in pinned_messages:
            try:
                # Get the channel
                channel = interaction.guild.get_channel(int(pinned_msg.channel_id))
                if not channel:
                    continue
                    
                # Get the message
                try:
                    message = await channel.fetch_message(int(pinned_msg.message_id))
                    if message:
                        # Unpin the message
                        await message.unpin()
                        
                        # Update the message to show it's no longer the active scene
                        await message.edit(
                            content="⚠️ **SCENE CHANGED** ⚠️",
                            embed=discord.Embed(
                                title=f"Scene Changed to: {scene_name}",
                                description=f"This scene is no longer active. The active scene is now **{scene_name}**.",
                                color=discord.Color.dark_gold()
                            ),
                            view=None
                        )
                except discord.NotFound:
                    pass  # Message was deleted, just continue
                except Exception as e:
                    logging.error(f"Error updating old scene message: {e}")
            except Exception as e:
                logging.error(f"Error handling old scene message: {e}")
        
        # Clear all existing pins from the database
        repositories.pinned_scene.clear_all_pins(str(interaction.guild.id))
        
        # Step 2: Pin the new active scene in the current channel
        system = repositories.server.get_system(str(interaction.guild.id))
        
        # Create a new scene view for the active scene
        view = factories.get_specific_scene_view(
            system=system,
            guild_id=str(interaction.guild.id),
            channel_id=str(interaction.channel.id),
            scene_id=scene.scene_id
        )
        
        # Set is_gm to False for the pinned message to ensure hidden aspects remain hidden
        view.is_gm = False
        view.build_view_components()
        
        # Create and pin the message
        message = await view.pin_message(interaction)
        
        # Create response message based on old scene
        response = f"🔄 Switched to scene: **{scene_name}**"
        if old_scene:
            response += f" (from **{old_scene.name}**)"
        if message:
            response += "\n✅ The scene has been pinned to this channel."
        
        await interaction.followup.send(response, ephemeral=True)

    @scene_group.command(name="list", description="List all scenes")
    async def scene_list(self, interaction: discord.Interaction):
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm:
            await interaction.response.send_message("This command is only available to GMs.", ephemeral=True)
            return
        
        scenes = repositories.scene.get_all_scenes(str(interaction.guild.id))

        if not scenes:
            message = "No scenes have been created yet."
            if is_gm:
                message += " Create one with `/scene create`!"
            await interaction.response.send_message(message, ephemeral=True)
            return
            
        embed = discord.Embed(
            title="📋 Scene List",
            color=discord.Color.purple()
        )
        
        scene_lines = []
        for scene in scenes:
            active_marker = "✓ " if scene.is_active else ""
            scene_lines.append(f"{active_marker}**{scene.name}**")
            
        embed.description = "\n".join(scene_lines)
        
        if is_gm:
            embed.set_footer(text="Use /scene switch to change the active scene")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @scene_group.command(name="delete", description="Delete a scene")
    @app_commands.describe(scene_name="Name of the scene to delete")
    @app_commands.autocomplete(scene_name=scene_name_autocomplete)
    async def scene_delete(self, interaction: discord.Interaction, scene_name: str):
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can delete scenes.", ephemeral=True)
            return
            
        scene = repositories.scene.get_by_name(str(interaction.guild.id), scene_name)
        if not scene:
            await interaction.response.send_message(f"❌ Scene '{scene_name}' not found.", ephemeral=True)
            return
            
        # Create confirmation view
        view = ConfirmDeleteView(interaction.guild.id, scene, self)
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to delete scene **{scene_name}**? This action cannot be undone.",
            view=view,
            ephemeral=True
        )

    @scene_group.command(name="rename", description="Rename a scene")
    @app_commands.describe(
        current_name="Current name of the scene",
        new_name="New name for the scene"
    )
    @app_commands.autocomplete(current_name=scene_name_autocomplete)
    async def scene_rename(self, interaction: discord.Interaction, current_name: str, new_name: str):
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can rename scenes.", ephemeral=True)
            return
            
        if len(new_name) > 100:
            await interaction.response.send_message("❌ Scene name must be 100 characters or less.", ephemeral=True)
            return
            
        # Check if scene with the new name already exists
        existing_scene = repositories.scene.get_by_name(str(interaction.guild.id), new_name)
        if existing_scene:
            await interaction.response.send_message(f"❌ A scene named '{new_name}' already exists.", ephemeral=True)
            return
            
        scene = repositories.scene.get_by_name(str(interaction.guild.id), current_name)
        if not scene:
            await interaction.response.send_message(f"❌ Scene '{current_name}' not found.", ephemeral=True)
            return
            
        repositories.scene.rename_scene(str(interaction.guild.id), scene.scene_id, new_name)
        
        # Update all pinned scene messages for this scene
        if scene.is_active:
            await self._update_all_pinned_scenes(interaction.guild, scene.scene_id)
        
        await interaction.response.send_message(
            f"✅ Renamed scene from **{current_name}** to **{new_name}**", 
            ephemeral=True
        )

    @scene_group.command(name="add-npc", description="Add an NPC to a scene")
    @app_commands.describe(
        npc_name="The name of the NPC to add to the scene",
        scene_name="Optional: Name of the scene to add to (defaults to active scene)"
    )
    @app_commands.autocomplete(
        npc_name=npc_name_autocomplete,
        scene_name=scene_name_autocomplete
    )
    async def scene_add_npc(self, interaction: discord.Interaction, npc_name: str, scene_name: str = None):
        """
        Add an NPC to a scene
        
        Parameters:
        -----------
        npc_name: The name of the NPC to add
        scene_name: Optional name of the scene to add to. If not provided, adds to the active scene.
        """
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage scenes.", ephemeral=True)
            return
            
        # Determine which scene to use
        scene = None
        if scene_name:
            scene = repositories.scene.get_by_name(str(interaction.guild.id), scene_name)
            if not scene:
                await interaction.response.send_message(f"❌ Scene '{scene_name}' not found.", ephemeral=True)
                return
        else:
            scene = repositories.scene.get_active_scene(str(interaction.guild.id))
            if not scene:
                await interaction.response.send_message("❌ No active scene. Create one with `/scene create` first or specify a scene name.", ephemeral=True)
                return
        
        # Get the NPC
        npc = repositories.character.get_character_by_name(str(interaction.guild.id), npc_name)
        if not npc:
            await interaction.response.send_message("❌ NPC not found. Did you create it with `/character create npc`?", ephemeral=True)
            return
            
        # Check if the NPC is already in the scene
        scene_npcs = repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), scene.scene_id)
        if npc.id in scene_npcs:
            await interaction.response.send_message(f"⚠️ {npc_name} is already in scene '{scene.name}'.", ephemeral=True)
            return
            
        # Add the NPC to the scene
        repositories.scene_npc.add_npc_to_scene(str(interaction.guild.id), scene.scene_id, npc.id)
        
        # Only update pinned messages if the scene is active
        if scene.is_active:
            await self._update_all_pinned_scenes(interaction.guild, scene.scene_id)
        
        await interaction.response.send_message(
            f"✅ **{npc_name}** added to scene **{scene.name}**.", 
            ephemeral=True
        )

    @scene_group.command(name="remove-npc", description="Remove an NPC from a scene")
    @app_commands.describe(
        npc_name="The name of the NPC to remove from the scene",
        scene_name="Optional: Name of the scene to remove from (defaults to active scene)"
    )
    @app_commands.autocomplete(
        npc_name=npcs_in_scene_autocomplete,
        scene_name=scene_name_autocomplete
    )
    async def scene_removenpc(self, interaction: discord.Interaction, npc_name: str, scene_name: str = None):
        """
        Remove an NPC from a scene
        
        Parameters:
        -----------
        npc_name: The name of the NPC to remove
        scene_name: Optional name of the scene to remove from. If not provided, removes from the active scene.
        """
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage scenes.", ephemeral=True)
            return
            
        # Determine which scene to use
        scene = None
        if scene_name:
            scene = repositories.scene.get_by_name(str(interaction.guild.id), scene_name)
            if not scene:
                await interaction.response.send_message(f"❌ Scene '{scene_name}' not found.", ephemeral=True)
                return
        else:
            scene = repositories.scene.get_active_scene(str(interaction.guild.id))
            if not scene:
                await interaction.response.send_message("❌ No active scene. Create one with `/scene create` first or specify a scene name.", ephemeral=True)
                return
    
        # Get the NPC
        npc = repositories.character.get_character_by_name(str(interaction.guild.id), npc_name)
        if not npc:
            await interaction.response.send_message("❌ NPC not found.", ephemeral=True)
            return
            
        # Check if the NPC is in the scene
        scene_npcs = repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), scene.scene_id)
        if npc.id not in scene_npcs:
            await interaction.response.send_message(f"❌ {npc_name} isn't in scene '{scene.name}'.", ephemeral=True)
            return
            
        # Remove the NPC from the scene
        repositories.scene_npc.remove_npc_from_scene(str(interaction.guild.id), scene.scene_id, npc.id)
        
        # Only update pinned messages if the scene is active
        if scene.is_active:
            await self._update_all_pinned_scenes(interaction.guild, scene.scene_id)
        
        await interaction.response.send_message(
            f"🗑️ **{npc_name}** removed from scene **{scene.name}**.", 
            ephemeral=True
        )

    @scene_group.command(name="clear-npcs", description="Clear all NPCs from the current scene.")
    async def scene_clear_npcs(self, interaction: discord.Interaction):
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage the scene.", ephemeral=True)
            return
            
        active_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
        if not active_scene:
            await interaction.response.send_message("❌ No active scene. Create one with `/scene create` first.", ephemeral=True)
            return
            
        repositories.scene_npc.clear_scene_npcs(str(interaction.guild.id), active_scene.scene_id)
        
        # Update all pinned scene messages
        await self._update_all_pinned_scenes(interaction.guild, active_scene.scene_id)
        
        await interaction.response.send_message(
            f"🧹 All NPCs cleared from scene **{active_scene.name}**.", 
            ephemeral=True
        )

    @scene_group.command(name="view", description="View a scene (defaults to current scene if not specified)")
    @app_commands.describe(scene_name="Optional: Name of the scene to view (defaults to active scene)")
    @app_commands.autocomplete(scene_name=scene_name_autocomplete)
    async def scene_view(self, interaction: discord.Interaction, scene_name: str = None):
        """
        View a scene - can specify a specific scene or view the current active scene
        
        Parameters:
        -----------
        scene_name: Optional name of the scene to view. If not provided, shows the active scene.
        """
        # If scene_name is provided, get that specific scene
        # Otherwise, get the active scene
        scene = None
        
        if scene_name:
            scene = repositories.scene.get_by_name(str(interaction.guild.id), scene_name)
            if not scene:
                await interaction.response.send_message(f"❌ Scene '{scene_name}' not found.", ephemeral=True)
                return
        else:
            scene = repositories.scene.get_active_scene(str(interaction.guild.id))
            if not scene:
                # For GMs, suggest creating a scene. For players, just inform them there's no scene.
                if await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
                    await interaction.response.send_message(
                        "❌ No active scene. Create one with `/scene create` first or specify a scene name.", 
                        ephemeral=True
                    )
                else:
                    await interaction.response.send_message("No active scene has been set up by the GM.", ephemeral=True)
                return
        
        # Create a system-specific scene view
        system = repositories.server.get_system(str(interaction.guild.id))
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Check if the active scene is pinned in this channel
        pinned_msg = None
        if scene.is_active:  # Only check for pins if viewing the active scene
            pinned_msg = repositories.pinned_scene.get_scene_message_info(str(interaction.guild.id), str(interaction.channel.id))
        
        # Create a system-specific scene view with the proper components
        view = factories.get_specific_scene_view(
            system=system,
            guild_id=str(interaction.guild.id),
            channel_id=str(interaction.channel.id),
            scene_id=scene.scene_id,
            message_id=pinned_msg.message_id if pinned_msg else None
        )
        
        # Set the GM flag based on the user's permission
        # This allows GMs to see hidden aspects in their personal view
        view.is_gm = is_gm
        view.build_view_components()
        
        # Get the embed and content
        embed, content = await view.create_scene_content()
        
        # Add footer content
        if scene.is_active:
            # For active scene, mention if it's pinned
            if pinned_msg:
                if is_gm:
                    embed.set_footer(text="This scene is also pinned at the top of the channel.")
                else:
                    embed.set_footer(text="This scene is also pinned at the top of the channel for easy reference.")
        else:
            # For non-active scene, add a note
            if is_gm:
                embed.set_footer(text=f"This is not the active scene. Use `/scene switch \"{scene.name}\"` to make it active.")
            else:
                embed.set_footer(text="This is not the currently active scene.")
        
        # Send the message with our view - IMPORTANT: Using ephemeral=True here
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @scene_group.command(name="pin", description="Pin the current scene to this channel")
    async def scene_pin(self, interaction: discord.Interaction):
        """Pin the current scene to the current channel"""
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can pin scenes.", ephemeral=True)
            return
            
        active_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
        if not active_scene:
            await interaction.response.send_message("❌ No active scene. Create one with `/scene create` first.", ephemeral=True)
            return
        
        # Active scene is guaranteed to be active, but add an explicit check for clarity
        if not active_scene.is_active:
            await interaction.response.send_message("❌ Only the active scene can be pinned.", ephemeral=True)
            return
        
        # Use defer to prevent the interaction from timing out
        await interaction.response.defer(ephemeral=True, thinking=True)

        # Get the system for this guild
        system = repositories.server.get_system(str(interaction.guild.id))
        
        # Create the scene view
        view = factories.get_specific_scene_view(
            system=system,
            guild_id=interaction.guild.id, 
            channel_id=interaction.channel.id,
            scene_id=active_scene.scene_id
        )
        
        # IMPORTANT: Since pinned messages are always visible to all channel members,
        # we set is_gm to False regardless of who creates it, to ensure hidden aspects are hidden
        view.is_gm = False
        view.build_view_components()
        
        # Pin the message
        message = await view.pin_message(interaction)
        
        # Use followup instead of the original response
        if message:
            await interaction.followup.send("✅ Scene pinned to this channel.")
        else:
            await interaction.followup.send("❌ Failed to pin the scene. Check bot permissions.")

    @scene_group.command(name="unpin", description="Unpin pinned scenes and clear all pins")
    async def scene_unpin(self, interaction: discord.Interaction):
        """Unpin pinned scenes and clear all pins"""
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can unpin scenes.", ephemeral=True)
            return
            
        # Get all pinned messages for this guild
        pinned_messages = repositories.pinned_scene.get_all_pinned_messages(str(interaction.guild.id))
        
        # Track successful/failed unpins
        successful = 0
        failed = 0
        
        # Unpin all messages
        for pinned_msg in pinned_messages:
            try:
                # Get the channel
                channel = interaction.guild.get_channel(int(pinned_msg.channel_id))
                if not channel:
                    continue
                    
                # Get the message
                message = await channel.fetch_message(int(pinned_msg.message_id))
                if message:
                    # Unpin the message
                    await message.unpin()
                    # Update message content to show it's no longer active
                    await message.edit(
                        content="🛑 **SCENE TRACKING DISABLED** 🛑",
                        embed=discord.Embed(
                            title="Scene Tracking Disabled",
                            description="Scene tracking has been turned off. This message is no longer being updated.",
                            color=discord.Color.darker_grey()
                        ),
                        view=None
                    )
                    successful += 1
            except Exception as e:
                logging.error(f"Failed to unpin scene message: {e}")
                failed += 1
        
        # Clear the pinned messages from the database
        repositories.pinned_scene.clear_all_pins(str(interaction.guild.id))
        
        # Inform the user
        await interaction.response.send_message(
            f"✅ Scene tracking disabled. Successfully unpinned {successful} messages." +
            (f" Failed to unpin {failed} messages." if failed > 0 else ""),
            ephemeral=True
        )

    @scene_group.command(name="set-image", description="Set the image/map for a scene")
    @app_commands.describe(
        scene_name="Name of the scene to set image for (defaults to active scene)",
        image_url="Optional: URL to an image for the scene",
        file="Optional: Upload an image file for the scene"
    )
    @app_commands.autocomplete(scene_name=scene_name_autocomplete)
    async def scene_set_image(self, interaction: discord.Interaction, scene_name: str = None, image_url: str = None, file: discord.Attachment = None):
        """Set an image for a scene using either a URL or uploaded file"""

        # Only GMs can set scene images
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can set scene images.", ephemeral=True)
            return
        
        # Must provide either URL or file, but not both
        if (image_url and file) or (not image_url and not file):
            await interaction.response.send_message("❌ Please provide either an image URL or upload a file, but not both.", ephemeral=True)
            return

        # Determine which scene to set image for
        scene = None
        if scene_name:
            scene = repositories.scene.get_by_name(str(interaction.guild.id), scene_name)
            if not scene:
                await interaction.response.send_message(f"❌ Scene '{scene_name}' not found.", ephemeral=True)
                return
        else:
            scene = repositories.scene.get_active_scene(str(interaction.guild.id))
            if not scene:
                await interaction.response.send_message("❌ No active scene. Create one with `/scene create` first or specify a scene name.", ephemeral=True)
                return
        
        # Handle file upload
        if file:
            # Validate file type
            if not file.content_type or not file.content_type.startswith('image/'):
                await interaction.response.send_message("❌ Please upload a valid image file.", ephemeral=True)
                return
            
            # Use the Discord CDN URL of the uploaded file
            final_image_url = file.url
        else:
            # Handle URL input
            if not image_url.startswith(("http://", "https://")):
                await interaction.response.send_message("❌ Please provide a valid image URL starting with http:// or https://", ephemeral=True)
                return
            final_image_url = image_url

        # Save the image URL to the scene
        repositories.scene.set_scene_image(str(interaction.guild.id), scene.scene_id, final_image_url)

        # Update all pinned scenes if this is the active scene
        if scene.is_active:
            await self._update_all_pinned_scenes(interaction.guild, scene.scene_id)
        
        # Show a preview
        embed = discord.Embed(
            title="Scene Image Updated",
            description=f"Image for scene **{scene.name}** has been set.",
            color=discord.Color.green()
        )
        embed.set_image(url=final_image_url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Helper method to update all pinned scenes after a change
    async def _update_all_pinned_scenes(self, guild, scene_id=None):
        """
        Update all pinned scene messages for a specific scene or for all scenes if scene_id is None
        
        Args:
            guild: The Discord guild object
            scene_id: Optional scene ID to update. If None, updates all active scenes
        """
        try:
            # Get all pinned messages for this guild
            pinned_messages = repositories.pinned_scene.get_all_pinned_messages(str(guild.id))
            if not pinned_messages:
                return  # No pinned messages to update
                
            # Get the system for this guild
            system = repositories.server.get_system(str(guild.id))
            
            # If scene_id is None, get active scene
            if scene_id is None:
                active_scene = repositories.scene.get_active_scene(str(guild.id))
                if active_scene:
                    scene_id = active_scene.scene_id
                else:
                    return  # No active scene to update
        
            # Update all relevant pinned messages
            for pinned_msg in pinned_messages:
                if scene_id and pinned_msg.scene_id != str(scene_id):
                    continue  # Only update messages for this scene
                
                try:
                    # Get the channel
                    channel = guild.get_channel(int(pinned_msg.channel_id))
                    if not channel:
                        continue
                        
                    # Create a new view for the scene
                    view = factories.get_specific_scene_view(
                        system=system,
                        guild_id=str(guild.id), 
                        channel_id=pinned_msg.channel_id,
                        scene_id=pinned_msg.scene_id,
                        message_id=pinned_msg.message_id
                    )
                    
                    # IMPORTANT: Always set is_gm to False for pinned scene updates
                    # This ensures that hidden aspects are always hidden in public pinned messages
                    view.is_gm = False
                    view.build_view_components()
                    
                    # Get the embed and content
                    embed, content = await view.create_scene_content()
                    
                    # Get the message
                    message = await channel.fetch_message(int(pinned_msg.message_id))
                    if message:
                        # Update the message
                        await message.edit(content=content, embed=embed, view=view)
                except Exception as e:
                    logging.error(f"Failed to update pinned scene message: {e}")
        except Exception as e:
            logging.error(f"Error in _update_all_pinned_scenes: {e}")

class ConfirmDeleteView(discord.ui.View):
    def __init__(self, guild_id, scene, cog):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.scene = scene
        self.cog = cog
        
    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Before deleting, unpin and update any pinned messages for this scene
        try:
            # Get all pinned messages for this scene
            pinned_messages = repositories.pinned_scene.get_all_pinned_messages(str(interaction.guild.id))
            
            for pinned_msg in pinned_messages:
                if pinned_msg.scene_id == self.scene.scene_id:
                    try:
                        # Get the channel
                        channel = interaction.guild.get_channel(int(pinned_msg.channel_id))
                        if not channel:
                            continue
                            
                        # Get the message
                        message = await channel.fetch_message(int(pinned_msg.message_id))
                        if message:
                            # Unpin the message
                            await message.unpin()
                            # Update message content to show the scene is deleted
                            await message.edit(
                                content="🗑️ **SCENE DELETED** 🗑️",
                                embed=discord.Embed(
                                    title="Scene Deleted",
                                    description=f"Scene **{self.scene.name}** has been deleted.",
                                    color=discord.Color.red()
                                ),
                                view=None
                            )
                    except Exception as e:
                        logging.error(f"Failed to update pinned message for deleted scene: {e}")
        except Exception as e:
            logging.error(f"Error handling scene deletion cleanup: {e}")
            
        # Now delete the scene
        repositories.scene.delete_scene(str(self.guild_id), self.scene.scene_id)
        
        await interaction.response.edit_message(
            content=f"✅ Scene **{self.scene.name}** has been deleted.",
            view=None
        )
        
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(
            content="Scene deletion cancelled.",
            view=None
        )

async def setup_scene_commands(bot: commands.Bot):
    await bot.add_cog(SceneCommands(bot))