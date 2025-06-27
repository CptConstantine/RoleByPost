import discord
from discord import ui
from data import repo
from core.scene_views import BasePinnedSceneView, SceneNotesButton
from core import factories

SYSTEM = "fate"

class FateSceneView(BasePinnedSceneView):
    """Fate-specific scene view with aspects and zones"""
    
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
        sheet = factories.get_specific_sheet(SYSTEM)
        
        # Get NPCs in scene
        npc_ids = repo.get_scene_npc_ids(self.guild_id, self.scene_id)
        
        # Format scene content - standard part
        lines = []
        for npc_id in npc_ids:
            npc = repo.get_character_by_id(self.guild_id, npc_id)
            if npc:
                lines.append(sheet.format_npc_scene_entry(npc, is_gm=False))
                
        # Get scene notes
        notes = repo.get_scene_notes(self.guild_id, self.scene_id)
        
        # Get Fate-specific scene data
        scene_aspects = repo.get_fate_scene_aspects(self.guild_id, self.scene_id) or []
        scene_zones = repo.get_fate_scene_zones(self.guild_id, self.scene_id) or []
        
        # Create embed
        embed = discord.Embed(
            title=f"🎭 Current Scene: {scene['name']}",
            color=discord.Color.purple()
        )
        
        description = ""
        if notes:
            description += f"**Notes:**\n{notes}\n\n"
            
        # Add Fate-specific sections
        if scene_aspects:
            description += "**Scene Aspects:**\n"
            for aspect in scene_aspects:
                description += f"• {aspect}\n"
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
        embed.set_footer(text="Scene view is pinned and will update automatically when the scene changes.")
        
        content = "🎭 **CURRENT SCENE** 🎭"
        
        return embed, content
        
    def build_view_components(self):
        if self.is_gm:
            self.add_item(SceneNotesButton(self))
            self.add_item(EditSceneAspectsButton(self))
            self.add_item(EditZonesButton(self))
            self.add_item(ManageNPCsButton(self))


class EditSceneAspectsButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Edit Aspects", style=discord.ButtonStyle.secondary, custom_id="edit_scene_aspects", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit scene aspects.", ephemeral=True)
            return
            
        # Open modal for editing aspects
        await interaction.response.send_modal(EditSceneAspectsModal(self.parent_view))


class EditZonesButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Edit Zones", style=discord.ButtonStyle.secondary, custom_id="edit_scene_zones", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit scene zones.", ephemeral=True)
            return
            
        # Open modal for editing zones
        await interaction.response.send_modal(EditZonesModal(self.parent_view))


class ManageNPCsButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Manage NPCs", style=discord.ButtonStyle.primary, custom_id="manage_npcs", row=1)
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage NPCs.", ephemeral=True)
            return
        
        # Get available NPCs
        npcs = repo.get_npcs_by_guild(interaction.guild.id)
        
        # Get NPCs currently in the scene
        scene_npc_ids = repo.get_scene_npc_ids(interaction.guild.id, self.parent_view.scene_id)
        
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
        scene_npc_ids = repo.get_scene_npc_ids(interaction.guild.id, self.parent_view.scene_id)
        
        # NPCs to add (selected but not in scene)
        to_add = [npc_id for npc_id in self.values if npc_id not in scene_npc_ids]
        
        # NPCs to remove (in scene but not selected)
        to_remove = [npc_id for npc_id in scene_npc_ids if npc_id not in self.values]
        
        # Perform the updates
        for npc_id in to_add:
            repo.add_scene_npc(interaction.guild.id, npc_id, self.parent_view.scene_id)
            
        for npc_id in to_remove:
            repo.remove_scene_npc(interaction.guild.id, npc_id, self.parent_view.scene_id)
        
        # Update the parent view
        await self.parent_view.update_view(interaction)
        
        # Respond with a confirmation
        added = len(to_add)
        removed = len(to_remove)
        message = []
        if added:
            message.append(f"Added {added} NPC{'s' if added > 1 else ''}")
        if removed:
            message.append(f"Removed {removed} NPC{'s' if removed > 1 else ''}")
        
        await interaction.response.send_message(
            f"✅ {' and '.join(message)} from the scene.",
            ephemeral=True
        )


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
        current_aspects = repo.get_fate_scene_aspects(parent_view.guild_id, parent_view.scene_id) or []
        current_text = "\n".join(current_aspects)
        
        self.aspects = discord.ui.TextInput(
            label="Scene Aspects (one per line)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=current_text
        )
        self.add_item(self.aspects)

    async def on_submit(self, interaction: discord.Interaction):
        # Split by newlines and filter out empty lines
        aspects = [aspect.strip() for aspect in self.aspects.value.splitlines()]
        aspects = [aspect for aspect in aspects if aspect]
        
        # Update aspects in DB
        repo.set_fate_scene_aspects(self.parent_view.guild_id, self.parent_view.scene_id, aspects)
        
        # Update the pinned message
        await self.parent_view.update_view(interaction)


class EditZonesModal(discord.ui.Modal, title="Edit Scene Zones"):
    def __init__(self, parent_view: FateSceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current zones
        current_zones = repo.get_fate_scene_zones(parent_view.guild_id, parent_view.scene_id) or []
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
        zones = [zone.strip() for zone in self.zones.value.splitlines()]
        zones = [zone for zone in zones if zone]
        
        # Update zones in DB
        repo.set_fate_scene_zones(self.parent_view.guild_id, self.parent_view.scene_id, zones)
        
        # Update the pinned message
        await self.parent_view.update_view(interaction)