from abc import ABC, abstractmethod
import logging
import discord
from discord import ui
from discord.ext import commands
from core import factories
from data.repositories.repository_factory import repositories

class BasePinnableSceneView(ABC, discord.ui.View):
    """
    Base class for scene views that can be pinned.
    Handles common functionality for creating, pinning, updating, and unpinning messages.
    """
    def __init__(self, guild_id=None, channel_id=None, scene_id=None, message_id=None):
        # Always use timeout=None for persistent views
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.scene_id = scene_id
        self.message_id = message_id
        self.is_initialized = guild_id is not None and channel_id is not None and scene_id is not None
        
        # Skip adding buttons during persistent view registration
        if not self.is_initialized:
            # For persistent view registration, add a placeholder button with the correct custom_id
            self.add_item(PlaceholderPersistentButton("edit_scene_notes"))
            return
            
        # Build the view components according to the specific system
        self.is_gm = False  # Will be set during interaction
        self.build_view_components()
    
    @abstractmethod
    def build_view_components(self):
        """
        Build UI components for the view based on system-specific requirements.
        Should be implemented by subclasses.
        """
        pass
    
    async def initialize_if_needed(self, interaction):
        """Initialize the view if it was loaded as a persistent view"""
        if not self.is_initialized:
            # Get scene ID from the database for this channel
            scene_info = repositories.pinned_scene.get_scene_message_info(str(interaction.guild.id), str(interaction.channel.id))
            if not scene_info:
                return False
                
            self.guild_id = str(interaction.guild.id)
            self.channel_id = str(interaction.channel.id)
            self.scene_id = scene_info.scene_id
            self.message_id = str(interaction.message.id)
            self.is_initialized = True
            
            # Check if user is GM
            self.is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            
            # Build the view components
            self.build_view_components()
            return True
        return False
    
    async def get_scene_message(self, interaction):
        """
        Get the scene message if it exists or create a new one without pinning.
        This is the base method for displaying scene content.
        """
        try:
            # Check if we have a stored message ID
            if self.message_id:
                try:
                    # Try to fetch the existing message
                    channel = interaction.guild.get_channel(int(self.channel_id))
                    if not channel:
                        channel = await interaction.guild.fetch_channel(int(self.channel_id))
                        
                    message = await channel.fetch_message(int(self.message_id))
                    return message
                except discord.NotFound:
                    # Message was deleted, we'll create a new one
                    pass
                except Exception as e:
                    logging.error(f"Error fetching scene message: {e}")
                    
            # Create a new message if we don't have one or couldn't fetch it
            channel = interaction.channel
            self.channel_id = str(channel.id)
            
            # Create the initial content
            embed, content = await self.create_scene_content()
            
            # Send the message without pinning
            message = await channel.send(content=content, embed=embed, view=self)
            self.message_id = str(message.id)
            
            # Store the message ID in the database - this doesn't mean it's pinned,
            # just that we're tracking this message for this scene in this channel
            #repositories.pinned_scene.set_pinned_message(self.guild_id, self.scene_id, self.channel_id, message.id)
            
            return message
        except Exception as e:
            logging.error(f"Error creating scene message: {e}")
            await interaction.response.send_message(
                "❌ Failed to create scene view.",
                ephemeral=True
            )
            return None
    
    async def pin_message(self, interaction):
        """
        Pin the scene message to the channel.
        This should only be called from /scene pin command for active scenes.
        """
        try:
            # Check if the scene is active - only active scenes can be pinned
            scene = repositories.scene.find_by_id('scene_id', self.scene_id)
            if not scene or not scene.is_active:
                await interaction.followup.send(
                    "❌ Only the active scene can be pinned.",
                    ephemeral=True
                )
                return None
            
            # Get or create the scene message
            message = await self.get_scene_message(interaction)
            if not message:
                return None
                
            # Pin the message
            await message.pin()
            
            # Store the message ID in the pinned messages database
            repositories.pinned_scene.set_pinned_message(str(self.guild_id), str(self.scene_id), str(self.channel_id), str(message.id))
            
            # Send a temporary message indicating the scene has been pinned
            temp_msg = await interaction.channel.send("📌 Scene view has been pinned. You can always find the current scene at the top of the channel.")
            
            # Delete the pin notification sent by Discord
            async for msg in interaction.channel.history(limit=10):
                if msg.type == discord.MessageType.pins_add:
                    await msg.delete()
                    break
                    
            # Delete our own temporary message after a delay
            await temp_msg.delete(delay=8.0)
            
            return message
        except discord.Forbidden:
            await interaction.followup.send(
                "⚠️ I don't have permission to pin messages. Scene view won't be pinned.",
                ephemeral=True
            )
            return None
        except Exception as e:
            logging.error(f"Error pinning scene message: {e}")
            await interaction.followup.send(
                "❌ Failed to pin scene view.",
                ephemeral=True
            )
            return None
            
    @abstractmethod
    async def create_scene_content(self):
        """
        Create the content for a scene view.
        Should be implemented by subclasses to format system-specific data.
        
        Returns:
            tuple: (embed, content) where embed is a discord.Embed and content is a string
        """
        pass
            
    async def update_pinned_message(self, interaction, content=None, embed=None, view=None):
        """
        Update a pinned scene message if it exists.
        This should be called when scene content changes and there's a pinned message.
        """
        message = await self.get_scene_message(interaction)
        if not message:
            return None
            
        try:
            # Always use message.edit rather than interaction.response.edit_message
            # This ensures we're updating the pinned message, not responding to the interaction
            await message.edit(content=content, embed=embed, view=view)
            
            # If the interaction hasn't been responded to yet, send a deferred message update
            # or acknowledge the interaction to prevent "interaction failed" errors
            if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=False)
                
            return message
        except Exception as e:
            logging.error(f"Error updating scene message: {e}")
            # If the interaction hasn't been responded to yet, send an error message
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "⚠️ Failed to update the scene message. The previous scene message may have been deleted.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "⚠️ Failed to update the scene message. The previous scene message may have been deleted.",
                    ephemeral=True
                )
            return None
            
    async def update_view(self, interaction):
        """
        Update both the ephemeral view and pinned message (if active scene).
        Both should always be updated for active scenes.
        """
        # Check if this scene is active
        scene = repositories.scene.find_by_id('scene_id', self.scene_id)
        is_active = scene and scene.is_active
        
        # Get the current content
        #embed, content = await self.create_scene_content()
        
        # For active scenes, update all pinned messages through the scene commands cog
        if is_active:
            # Find any SceneCommands cog instance to use its update method
            scene_cog = None
            for cog in interaction.client.cogs.values():
                if isinstance(cog, commands.Cog) and hasattr(cog, "_update_all_pinned_scenes"):
                    scene_cog = cog
                    break
            
            # Update all pinned scenes with this scene ID
            if scene_cog:
                await scene_cog._update_all_pinned_scenes(interaction.guild, self.scene_id)
        
        # Always update the ephemeral view for the current user
        # Create a view with proper GM permissions for the ephemeral message
        system = repositories.server.get_system(str(self.guild_id))
        ephemeral_view = factories.get_specific_scene_view(
            system=system,
            guild_id=self.guild_id, 
            channel_id=self.channel_id, 
            scene_id=self.scene_id,
            message_id=self.message_id
        )
        ephemeral_view.is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        ephemeral_view.build_view_components()
        
        # Create embed with scene content for the ephemeral response
        ephemeral_embed, ephemeral_content = await ephemeral_view.create_scene_content()
        
        # Update the ephemeral message for the current user
        if not interaction.response.is_done():
            await interaction.response.edit_message(
                content=ephemeral_content, 
                embed=ephemeral_embed, 
                view=ephemeral_view
            )
    
    async def unpin_message(self, interaction):
        """
        Unpin the scene message from the channel.
        This should be called from /scene off or when switching active scenes.
        """
        try:
            message = await self.get_scene_message(interaction)
            if not message:
                return False
                
            # Unpin the message
            await message.unpin()
            
            # Update the message to show it's no longer active
            await message.edit(
                content="🛑 **SCENE TRACKING DISABLED** 🛑",
                embed=discord.Embed(
                    title="Scene Tracking Disabled",
                    description="Scene tracking has been turned off. This message is no longer being updated.",
                    color=discord.Color.darker_grey()
                ),
                view=None
            )
            
            # Remove the message from the pinned messages database
            repositories.pinned_scene.clear_all_pins(str(self.guild_id))
            
            return True
        except Exception as e:
            logging.error(f"Error unpinning scene message: {e}")
            return False
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Allow the bot itself
        if interaction.user.id == interaction.client.user.id:
            return True
            
        # Initialize if needed
        if not self.is_initialized:
            success = await self.initialize_if_needed(interaction)
            if not success:
                await interaction.response.send_message("⚠️ Error: Scene view is not properly initialized.", ephemeral=True)
                return False
                
        # Update the is_gm flag
        self.is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            
        # For GM-only buttons, check permissions
        component_id = interaction.data.get("custom_id", "")
        
        # List of GM-only buttons - add any other GM-only buttons here
        gm_only_buttons = ["edit_scene_notes", "edit_aspects", "edit_zones", "manage_npcs", "edit_environment"]
        
        if component_id in gm_only_buttons and not self.is_gm:
            await interaction.response.send_message("❌ Only GMs can use this feature.", ephemeral=True)
            return False
            
        return True


class PlaceholderPersistentButton(discord.ui.Button):
    """Empty button for persistent view registration"""
    def __init__(self, custom_id):
        super().__init__(label="...", custom_id=custom_id, style=discord.ButtonStyle.secondary)
        
    async def callback(self, interaction: discord.Interaction):
        """Reinitialize the view when this button is clicked after bot restart"""
        # This is called when a button from a persistent view is used after bot restart
        if not self.view.is_initialized:
            success = await self.view.initialize_if_needed(interaction)
            if not success:
                await interaction.response.send_message(
                    "⚠️ This scene view is outdated. Please use `/scene view` to see the current scene.",
                    ephemeral=True
                )
                return
                
        # Update the view with a newly initialized one
        await self.view.update_view(interaction)


class GenericSceneView(BasePinnableSceneView):
    """Generic implementation of pinned scene view"""
    
    async def create_scene_content(self):
        # Get scene info
        scene = repositories.scene.find_by_id('scene_id', self.scene_id)
        if not scene:
            return discord.Embed(
                title="❌ Scene Not Found",
                description="This scene no longer exists.",
                color=discord.Color.red()
            ), "❌ **SCENE ERROR** ❌"
        
        # Get NPCs in scene
        npc_ids = repositories.scene_npc.get_scene_npc_ids(str(self.guild_id), str(self.scene_id))
        
        # Format scene content
        lines = []
        for npc_id in npc_ids:
            npc = repositories.entity.get_by_id(str(npc_id))
            if npc:
                # Show NPC details for everyone
                lines.append(npc.format_npc_scene_entry(is_gm=False))
                
        # Get scene notes
        notes = repositories.scene_notes.get_scene_notes(str(self.guild_id), str(self.scene_id))
        
        # Create embed
        embed = discord.Embed(
            title=f"🎭 Current Scene: {scene.name}",
            color=discord.Color.purple()
        )
        
        description = ""
        if notes:
            description += f"**Notes:**\n{notes}\n\n"
            
        if lines:
            description += "\n\n".join(lines)
        else:
            description += "📭 No NPCs are currently in this scene."
            
        embed.description = description
        embed.set_footer(text="Scene view is pinned and will update automatically when the scene changes.")
        
        content = "🎭 **CURRENT SCENE** 🎭"

        if scene.image_url:
            embed.set_thumbnail(url=scene.image_url)

        return embed, content
        
    def build_view_components(self):
        if self.is_gm:
            self.add_item(SceneNotesButton(self))


class SceneNotesButton(ui.Button):
    def __init__(self, parent_view: BasePinnableSceneView):
        super().__init__(label="Edit Scene Notes", style=discord.ButtonStyle.primary, custom_id="edit_scene_notes", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit scene notes.", ephemeral=True)
            return
            
        # Open modal for editing notes
        await interaction.response.send_modal(SceneNotesModal(self.parent_view))


class SceneNotesModal(discord.ui.Modal, title="Edit Scene Notes"):
    def __init__(self, parent_view: BasePinnableSceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current notes
        current_notes = repositories.scene_notes.get_scene_notes(str(parent_view.guild_id), str(parent_view.scene_id)) or ""
        
        self.notes = discord.ui.TextInput(
            label="Scene Notes",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=2000,
            default=current_notes
        )
        self.add_item(self.notes)

    async def on_submit(self, interaction: discord.Interaction):
        # Update notes in DB
        repositories.scene_notes.set_scene_notes(str(self.parent_view.guild_id), str(self.parent_view.scene_id), self.notes.value)
        
        # Find any SceneCommands cog instance to use its update method
        scene_cog = None
        for cog in interaction.client.cogs.values():
            if isinstance(cog, commands.Cog) and hasattr(cog, "_update_all_pinned_scenes"):
                scene_cog = cog
                break
        
        # Update all pinned scenes with this scene ID - ensures hidden aspects stay hidden
        if scene_cog:
            await scene_cog._update_all_pinned_scenes(interaction.guild, self.parent_view.scene_id)
        else:
            # Fallback to the basic update if we can't find the cog
            await self.parent_view.update_view(interaction)
        
        # Send confirmation
        await interaction.response.send_message("✅ Scene notes updated.", ephemeral=True)