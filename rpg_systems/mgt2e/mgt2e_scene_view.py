import discord
from discord import ui
from discord.ext import commands
from core import factories
from core.scene_views import BasePinnableSceneView, PlaceholderPersistentButton, SceneNotesButton
from data.repositories.repository_factory import repositories

SYSTEM = "mgt2e"

class MGT2ESceneView(BasePinnableSceneView):
    """Mongoose Traveller 2E scene view with environmental details"""
    def __init__(self, guild_id: int = None, scene_id: int = None, is_gm: bool = False, message_id: int = None):
        super().__init__(guild_id, scene_id, is_gm, message_id)
        
        if not self.is_initialized:
            # For persistent view registration, add placeholder buttons with the correct custom_ids
            self.add_item(PlaceholderPersistentButton("edit_scene_notes"))
            self.add_item(PlaceholderPersistentButton("edit_environment"))
            self.add_item(PlaceholderPersistentButton("manage_npcs"))
            return
    
    async def create_scene_content(self):
        # Get scene info
        scene = repositories.scene.find_by_id('scene_id', self.scene_id)
        if not scene:
            return discord.Embed(
                title="❌ Scene Not Found",
                description="This scene no longer exists.",
                color=discord.Color.red()
            ), "❌ **SCENE ERROR** ❌"
            
        # Get system and sheet for formatting
        sheet = factories.get_specific_sheet(SYSTEM)
        
        # Get NPCs in scene
        npc_ids = repositories.scene_npc.get_scene_npc_ids(str(self.guild_id), str(self.scene_id))
        
        # Format scene content - standard part
        lines = []
        for npc_id in npc_ids:
            npc = repositories.character.get_by_id(str(npc_id))
            if npc:
                lines.append(sheet.format_npc_scene_entry(npc, is_gm=self.is_gm))
                
        # Get scene notes
        notes = repositories.scene_notes.get_scene_notes(str(self.guild_id), str(self.scene_id))
        
        # Get MGT2E-specific scene data
        environment = repositories.mgt2e_environment.get_environment(str(self.guild_id), str(self.scene_id)) or {}
        
        # Create embed
        embed = discord.Embed(
            title=f"🎭 {('Current' if scene.is_active else 'Inactive')} Scene: {scene.name}",
            color=discord.Color.purple() if scene.is_active else discord.Color.dark_grey()
        )
        
        description = ""
        if notes:
            description += f"**Notes:**\n{notes}\n\n"
            
        # Add MGT2E-specific sections
        if environment:
            description += "**Environment:**\n"
            for key, value in environment.items():
                if value:  # Only show non-empty values
                    description += f"• **{key}:** {value}\n"
            description += "\n"
            
        if lines:
            description += "**NPCs:**\n"
            description += "\n\n".join(lines)
        else:
            description += "📭 No NPCs are currently in this scene."
            
        embed.description = description
        
        # Add appropriate footer based on scene active status
        if scene.is_active:
            embed.set_footer(text="Scene view will update automatically when the scene changes.")
            content = "🎭 **CURRENT SCENE** 🎭"
        else:
            embed.set_footer(text="This is not the active scene. Use /scene switch to make it active.")
            content = "🎭 **INACTIVE SCENE** 🎭"
        
        return embed, content
        
    def build_view_components(self):
        # Add all buttons regardless of GM status - the interaction_check will handle permissions
        self.clear_items()  # Clear any existing buttons
        self.add_item(SceneNotesButton(self))
        self.add_item(EditEnvironmentButton(self))
        self.add_item(ManageNPCsButton(self))


class EditEnvironmentButton(ui.Button):
    def __init__(self, parent_view: MGT2ESceneView):
        super().__init__(label="Edit Environment", style=discord.ButtonStyle.secondary, custom_id="edit_environment", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role - this is handled by interaction_check in base class,
        # but we add an additional check here for safety
        if not repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit environment details.", ephemeral=True)
            return
            
        # Open modal for editing environment
        await interaction.response.send_modal(EditEnvironmentModal(self.parent_view))


class ManageNPCsButton(ui.Button):
    def __init__(self, parent_view: MGT2ESceneView):
        super().__init__(label="Manage NPCs", style=discord.ButtonStyle.primary, custom_id="manage_npcs", row=1)
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role - this is handled by interaction_check in base class,
        # but we add an additional check here for safety
        if not repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage NPCs.", ephemeral=True)
            return
        
        # Get available NPCs
        npcs = repositories.character.get_npcs_by_guild(str(interaction.guild.id))
        
        # Get NPCs currently in the scene
        scene_npc_ids = repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), str(self.parent_view.scene_id))
        
        # Create selection options for NPCs
        options = []
        
        # First, add NPCs already in the scene so they appear at the top
        for npc in npcs:
            if npc.id in scene_npc_ids:
                options.append(discord.SelectOption(
                    label=f"✓ {npc.name}",
                    value=npc.id,
                    description=f"Remove from scene",
                    default=True
                ))
        
        # Then add NPCs not in the scene
        for npc in npcs:
            if npc.id not in scene_npc_ids:
                options.append(discord.SelectOption(
                    label=npc.name,
                    value=npc.id,
                    description=f"Add to scene"
                ))
        
        # Send a message with the menu
        if options:
            view = ManageNPCsView(self.parent_view, options)
            await interaction.response.send_message(
                "Select NPCs to add/remove from the scene:", 
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ No NPCs found. Create some with `/character create npc`.", 
                ephemeral=True
            )


class ManageNPCsView(discord.ui.View):
    def __init__(self, parent_view: MGT2ESceneView, options):
        super().__init__(timeout=300)  # 5 minute timeout
        self.parent_view = parent_view
        self.add_item(ManageNPCsSelect(parent_view, options))
        self.add_item(DoneButton(parent_view))


class ManageNPCsSelect(discord.ui.Select):
    def __init__(self, parent_view: MGT2ESceneView, options):
        super().__init__(
            placeholder="Select NPCs to add/remove...",
            min_values=0,
            max_values=len(options),
            options=options
        )
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        # Get current NPCs in scene
        scene_npc_ids = repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), str(self.parent_view.scene_id))
        
        # NPCs to add (selected but not in scene)
        to_add = [npc_id for npc_id in self.values if npc_id not in scene_npc_ids]
        
        # NPCs to remove (in scene but not selected)
        to_remove = [npc_id for npc_id in scene_npc_ids if npc_id not in self.values]
        
        # Perform the updates
        for npc_id in to_add:
            repositories.scene_npc.add_npc_to_scene(str(interaction.guild.id), str(self.parent_view.scene_id), npc_id)
            
        for npc_id in to_remove:
            repositories.scene_npc.remove_npc_from_scene(str(interaction.guild.id), str(self.parent_view.scene_id), npc_id)
    
        # Check if this is the active scene before updating pins
        scene = repositories.scene.find_by_id('scene_id', self.parent_view.scene_id)
    
        # Only update all pinned instances if this is the active scene
        if scene and scene.is_active:
            # Find any SceneCommands cog instance to use its update method
            scene_cog = None
            for cog in interaction.client.cogs.values():
                if isinstance(cog, commands.Cog) and hasattr(cog, "_update_all_pinned_scenes"):
                    scene_cog = cog
                    break
        
            # Update all pinned scenes with this scene ID
            if scene_cog:
                await scene_cog._update_all_pinned_scenes(interaction.guild, self.parent_view.scene_id)
    
        # Always update the current ephemeral view for the user
        await self.parent_view.update_view(interaction)


class DoneButton(discord.ui.Button):
    def __init__(self, parent_view: MGT2ESceneView):
        super().__init__(label="Done", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="✅ NPC management complete.", view=None)


class EditEnvironmentModal(discord.ui.Modal, title="Edit Scene Environment"):
    def __init__(self, parent_view: MGT2ESceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current environment
        current_env = repositories.mgt2e_environment.get_environment(str(parent_view.guild_id), str(parent_view.scene_id)) or {}
        
        # Add input fields for each environmental factor
        self.description = ui.TextInput(
            label="Description", 
            default=current_env.get("description", ""),
            required=False,
            max_length=100,
            style=discord.TextStyle.paragraph
        )
        self.gravity = ui.TextInput(
            label="Gravity", 
            default=current_env.get("gravity", ""),
            required=False,
            max_length=100
        )
        self.atmosphere = ui.TextInput(
            label="Atmosphere", 
            default=current_env.get("atmosphere", ""),
            required=False,
            max_length=100
        )
        self.temperature = ui.TextInput(
            label="Temperature", 
            default=current_env.get("temperature", ""),
            required=False,
            max_length=100
        )
        
        self.add_item(self.description)
        self.add_item(self.gravity)
        self.add_item(self.atmosphere)
        self.add_item(self.temperature)

    async def on_submit(self, interaction: discord.Interaction):
        # Update environment data in DB
        repositories.mgt2e_environment.set_environment(str(self.parent_view.guild_id), str(self.parent_view.scene_id), {
            "description": self.description.value,
            "gravity": self.gravity.value,
            "atmosphere": self.atmosphere.value,
            "temperature": self.temperature.value
        })
        
        # Check if this is the active scene before updating pins
        scene = repositories.scene.find_by_id('scene_id', self.parent_view.scene_id)
        
        # Only update pinned scenes if this is the active scene
        if scene and scene.is_active:
            # Find any SceneCommands cog instance to use its update method
            scene_cog = None
            for cog in interaction.client.cogs.values():
                if isinstance(cog, commands.Cog) and hasattr(cog, "_update_all_pinned_scenes"):
                    scene_cog = cog
                    break
            
            # Update all pinned scenes with this scene ID
            if scene_cog:
                await scene_cog._update_all_pinned_scenes(interaction.guild, self.parent_view.scene_id)
        
        # Always update the user's ephemeral view with GM permissions intact
        is_gm = repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Create a new scene view with the updated environment data
        temp_view = factories.get_specific_scene_view(
            system=repositories.server.get_system(str(interaction.guild.id)),
            guild_id=str(interaction.guild.id),
            channel_id=str(interaction.channel.id),
            scene_id=self.parent_view.scene_id
        )
        temp_view.is_gm = is_gm
        temp_view.build_view_components()
        
        # Create embed with scene content for the response
        embed, content = await temp_view.create_scene_content()
        
        # If this scene is active AND there's a pinned message for it, add the footer
        pinned_msg = None
        if scene and scene.is_active:
            pinned_msg = repositories.pinned_scene.get_scene_message_info(str(interaction.guild.id), str(interaction.channel.id))
            if pinned_msg and pinned_msg.scene_id == self.parent_view.scene_id:
                embed.set_footer(text="This scene is also pinned at the top of the channel.")
        
        # Update the user's view
        await interaction.response.edit_message(embed=embed, view=temp_view)