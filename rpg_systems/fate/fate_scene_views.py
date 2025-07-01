import logging
import discord
from discord import ui
from discord.ext import commands
from core.scene_views import BasePinnableSceneView, PlaceholderPersistentButton, SceneNotesButton
from core import factories
from rpg_systems.fate.aspect import Aspect
from data.repositories.repository_factory import repositories

SYSTEM = "fate"

class FateSceneView(BasePinnableSceneView):
    """Fate-specific scene view with aspects and zones"""
    
    def __init__(self, guild_id: int = None, scene_id: int = None, is_gm: bool = False, message_id: int = None):
        super().__init__(guild_id, scene_id, is_gm, message_id)
        
        if not self.is_initialized:
            # For persistent view registration, add placeholder buttons with the correct custom_ids
            self.add_item(PlaceholderPersistentButton("edit_aspects"))
            self.add_item(PlaceholderPersistentButton("edit_zones"))
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
        
        # Get Fate-specific scene data
        scene_aspects = repositories.fate_aspects.get_aspects(str(self.guild_id), str(self.scene_id)) or []
        scene_zones = repositories.fate_zones.get_zones(str(self.guild_id), str(self.scene_id)) or []
        
        # Create embed
        embed = discord.Embed(
            title=f"🎭 {('Current' if scene.is_active else 'Inactive')} Scene: {scene.name}",
            color=discord.Color.purple() if scene.is_active else discord.Color.dark_grey()
        )
        
        description = ""
        if notes:
            description += f"**Notes:**\n{notes}\n\n"
            
        # Add Fate-specific sections
        if scene_aspects:
            description += "**Scene Aspects:**\n"
            hidden_aspect_count = 0
            
            for aspect in scene_aspects:
                aspect_str = aspect.get_short_aspect_string(is_gm=self.is_gm)
                if aspect_str:
                    description += f"• {aspect_str}\n"
                else:
                    # This is a hidden aspect that non-GMs can't see
                    hidden_aspect_count += 1
            
            # After listing visible aspects, add a generic note about hidden aspects if any exist
            if hidden_aspect_count > 0 and not self.is_gm:
                description += f"• *{hidden_aspect_count} hidden aspect{'s' if hidden_aspect_count > 1 else ''}*\n"
                
            description += "\n"
        
        if scene_zones:
            description += "**Zones:**\n"
            for zone in scene_zones:
                description += f"• {zone}\n"
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
        self.clear_items()
        self.add_item(SceneNotesButton(self))
        self.add_item(EditSceneAspectsButton(self))
        self.add_item(EditZonesButton(self))
        self.add_item(ManageNPCsButton(self))


class EditSceneAspectsButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Edit Aspects", style=discord.ButtonStyle.secondary, custom_id="edit_aspects", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit aspects.", ephemeral=True)
            return
            
        # Open modal for editing aspects
        await interaction.response.send_modal(EditSceneAspectsModal(self.parent_view))


class EditZonesButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Edit Zones", style=discord.ButtonStyle.secondary, custom_id="edit_zones", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit zones.", ephemeral=True)
            return
            
        # Open modal for editing zones
        await interaction.response.send_modal(EditZonesModal(self.parent_view))


class ManageNPCsButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Manage NPCs", style=discord.ButtonStyle.primary, custom_id="manage_npcs", row=1)
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
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
    def __init__(self, parent_view: FateSceneView, options):
        super().__init__(timeout=300)  # 5 minute timeout
        self.parent_view = parent_view
        self.add_item(ManageNPCsSelect(parent_view, options))
        self.add_item(DoneButton(parent_view))


class ManageNPCsSelect(discord.ui.Select):
    def __init__(self, parent_view: FateSceneView, options):
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
    
        await self.parent_view.update_view(interaction)


class DoneButton(discord.ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Done", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="✅ NPC management complete.", view=None)


class EditSceneAspectsModal(discord.ui.Modal, title="Edit Scene Aspects"):
    def __init__(self, parent_view: FateSceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current aspects
        current_aspects = repositories.fate_aspects.get_aspects(str(parent_view.guild_id), str(parent_view.scene_id)) or []
        
        # Convert aspects to format suitable for editing in text field
        aspect_lines = []
        for aspect in current_aspects:
            # Format for editing in text area
            if aspect.is_hidden:
                aspect_lines.append(f"*{aspect.name}*")
            else:
                aspect_lines.append(aspect.name)
                
            # If we have free invokes, add them in a bracket
            if aspect.free_invokes > 0:
                aspect_lines[-1] += f" [{aspect.free_invokes}]"
        
        current_text = "\n".join(aspect_lines)
        
        self.aspects = discord.ui.TextInput(
            label="Aspects (* for hidden, [#] for invokes)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=current_text,
            placeholder="High Concept\n*A Secret Aspect*\nTrapped in Darkness [2]"
        )
        self.add_item(self.aspects)

    async def on_submit(self, interaction: discord.Interaction):
        # Split by newlines and filter out empty lines
        aspect_lines = [line.strip() for line in self.aspects.value.splitlines()]
        aspect_lines = [line for line in aspect_lines if line]
        
        # Convert to Aspect objects
        aspects = []
        for line in aspect_lines:
            # Check if this aspect has free invokes
            free_invokes = 0
            invoke_match = line.strip().split('[')
            if len(invoke_match) > 1 and invoke_match[1].endswith(']'):
                try:
                    # Extract the number from [#]
                    invoke_str = invoke_match[1].rstrip(']')
                    free_invokes = int(invoke_str)
                    # Remove the [#] part from the line
                    line = invoke_match[0].strip()
                except ValueError:
                    # If we can't parse the number, assume it's part of the name
                    pass
            
            # Check if this aspect is marked as hidden (with asterisks)
            if line.startswith("*") and line.endswith("*"):
                name = line[1:-1].strip()
                aspects.append(Aspect(
                    name=name,
                    description="",
                    is_hidden=True,
                    free_invokes=free_invokes
                ))
            else:
                aspects.append(Aspect(
                    name=line,
                    description="",
                    is_hidden=False,
                    free_invokes=free_invokes
                ))
        
        # Update aspects in DB
        repositories.fate_aspects.set_aspects(str(self.parent_view.guild_id), str(self.parent_view.scene_id), aspects)
        
        # Update the view - this will now update both pinned and ephemeral messages
        await self.parent_view.update_view(interaction)


class EditZonesModal(discord.ui.Modal, title="Edit Scene Zones"):
    def __init__(self, parent_view: FateSceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current zones
        current_zones = repositories.fate_zones.get_zones(str(parent_view.guild_id), str(parent_view.scene_id)) or []
        current_text = "\n".join(current_zones)
        
        self.zones = discord.ui.TextInput(
            label="Scene Zones (one per line)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=current_text
        )
        self.add_item(self.zones)

    async def on_submit(self, interaction: discord.Interaction):
        # Split by newlines and filter out empty lines
        zone_lines = [line.strip() for line in self.zones.value.splitlines()]
        zone_lines = [line for line in zone_lines if line]
        
        # Update zones in DB
        repositories.fate_zones.set_zones(str(self.parent_view.guild_id), str(self.parent_view.scene_id), zone_lines)
        
        # Update the view - this will now update both pinned and ephemeral messages
        await self.parent_view.update_view(interaction)