from abc import ABC, abstractmethod
import logging
import discord
from discord import ui
from data import repo
from core import factories

class BasePinnedSceneView(ABC, discord.ui.View):
    """
    Base class for scene views that use a single pinned message.
    Handles common functionality for pinning and updating messages.
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
            self.add_item(EmptySceneButton("edit_scene_notes"))
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
            scene_info = repo.get_scene_message_info(interaction.guild.id, interaction.channel.id)
            if not scene_info:
                return False
                
            self.guild_id = str(interaction.guild.id)
            self.channel_id = str(interaction.channel.id)
            self.scene_id = scene_info["scene_id"]  
            self.message_id = str(interaction.message.id)
            self.is_initialized = True
            
            # Check if user is GM
            self.is_gm = await repo.has_gm_permission(interaction.guild.id, interaction.user)
            
            # Build the view components
            self.build_view_components()
            return True
        return False
    
    async def get_scene_message(self, interaction):
        """Get the scene message if it exists in the database or create a new one"""
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
            
            # Send and pin the new message
            message = await channel.send(content=content, embed=embed, view=self)
            await message.pin()
            self.message_id = str(message.id)
            
            # Store the message ID in the database
            repo.set_scene_message_id(self.guild_id, self.scene_id, self.channel_id, message.id)
            
            # Send a temporary message indicating the scene has been pinned
            temp_msg = await channel.send("📌 Scene view has been pinned. You can always find the current scene at the top of the channel.")
            
            # Delete the pin notification sent by Discord
            async for msg in channel.history(limit=10):
                if msg.type == discord.MessageType.pins_add:
                    await msg.delete()
                    break
                    
            # Delete our own temporary message after a delay
            await temp_msg.delete(delay=8.0)
            
            return message
        except discord.Forbidden:
            await interaction.response.send_message(
                "⚠️ I don't have permission to pin messages. Scene view won't be pinned.",
                ephemeral=True
            )
            return None
        except Exception as e:
            logging.error(f"Error creating scene message: {e}")
            await interaction.response.send_message(
                "❌ Failed to create pinned scene view.",
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
            
    async def update_scene_message(self, interaction, content=None, embed=None, view=None):
        """Update the scene message instead of sending a new one"""
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
        """Update the scene view with current state"""
        embed, content = await self.create_scene_content()
        
        # Create a new view of the appropriate type
        system = repo.get_system(self.guild_id)
        new_view = factories.get_specific_scene_view(
            system,
            guild_id=self.guild_id, 
            channel_id=self.channel_id, 
            scene_id=self.scene_id,
            message_id=self.message_id
        )
        
        # Check if user is GM for the new view
        new_view.is_gm = await repo.has_gm_permission(interaction.guild.id, interaction.user)
        
        # Rebuild the view components
        new_view.build_view_components()
        
        # Update the message
        await self.update_scene_message(interaction, content=content, embed=embed, view=new_view)
        
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
        self.is_gm = await repo.has_gm_permission(interaction.guild.id, interaction.user)
                
        # For the scene notes button, only GMs can use it
        component_id = interaction.data.get("custom_id", "")
        if component_id == "edit_scene_notes" and not self.is_gm:
            await interaction.response.send_message("❌ Only GMs can edit scene notes.", ephemeral=True)
            return False
                
        return True


class EmptySceneButton(discord.ui.Button):
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
        await interaction.response.defer()


class GenericSceneView(BasePinnedSceneView):
    """Generic implementation of pinned scene view"""
    
    async def create_scene_content(self):
        # Get scene info
        scene = repo.get_scene_by_id(self.guild_id, self.scene_id)
        if not scene:
            return discord.Embed(
                title="❌ Scene Not Found",
                description="This scene no longer exists.",
                color=discord.Color.red()
            ), "❌ **SCENE ERROR** ❌"
            
        # Get system and sheet for formatting
        system = repo.get_system(self.guild_id)
        sheet = factories.get_specific_sheet(system)
        
        # Get NPCs in scene
        npc_ids = repo.get_scene_npc_ids(self.guild_id, self.scene_id)
        
        # Format scene content
        lines = []
        for npc_id in npc_ids:
            npc = repo.get_character_by_id(self.guild_id, npc_id)
            if npc:
                # Show NPC details for everyone
                lines.append(sheet.format_npc_scene_entry(npc, is_gm=False))
                
        # Get scene notes
        notes = repo.get_scene_notes(self.guild_id, self.scene_id)
        
        # Create embed
        embed = discord.Embed(
            title=f"🎭 Current Scene: {scene['name']}",
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
        
        return embed, content
        
    def build_view_components(self):
        if self.is_gm:
            self.add_item(SceneNotesButton(self))


class SceneNotesButton(ui.Button):
    def __init__(self, parent_view: BasePinnedSceneView):
        super().__init__(label="Edit Scene Notes", style=discord.ButtonStyle.primary, custom_id="edit_scene_notes", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit scene notes.", ephemeral=True)
            return
            
        # Open modal for editing notes
        await interaction.response.send_modal(SceneNotesModal(self.parent_view))


class SceneNotesModal(discord.ui.Modal, title="Edit Scene Notes"):
    def __init__(self, parent_view: BasePinnedSceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current notes
        current_notes = repo.get_scene_notes(parent_view.guild_id, parent_view.scene_id) or ""
        
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
        repo.set_scene_notes(self.parent_view.guild_id, self.notes.value, self.parent_view.scene_id)
        
        # Update the pinned message
        await self.parent_view.update_view(interaction)
        
        # Send confirmation
        await interaction.response.send_message("✅ Scene notes updated.", ephemeral=True)