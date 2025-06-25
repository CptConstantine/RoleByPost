import discord
from discord.ext import commands
from discord import app_commands
from core import shared_views
from data import repo
import core.factories as factories

async def npc_name_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repo.get_all_characters(interaction.guild.id)
    active_scene = repo.get_active_scene(interaction.guild.id)
    
    if not active_scene:
        return []
        
    scene_npcs = set(repo.get_scene_npc_ids(interaction.guild.id))
    npcs = [
        c for c in all_chars
        if c.is_npc and c.id not in scene_npcs and current.lower() in c.name.lower()
    ]
    options = [c.name for c in npcs]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def npcs_in_scene_autocomplete(interaction: discord.Interaction, current: str):
    active_scene = repo.get_active_scene(interaction.guild.id)
    if not active_scene:
        return []
    all_chars = repo.get_scene_npcs(interaction.guild.id, active_scene['id'])
    
    npcs = [c for c in all_chars]
    options = [c.name for c in npcs]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def scene_name_autocomplete(interaction: discord.Interaction, current: str):
    scenes = repo.get_scenes(interaction.guild.id)
    return [
        app_commands.Choice(name=f"{s['name']}{'✓' if s['is_active'] else ''}", value=s['name'])
        for s in scenes
        if current.lower() in s['name'].lower()
    ][:25]

class SceneCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    scene_group = app_commands.Group(name="scene", description="Scene management commands")

    @scene_group.command(name="create", description="Create a new scene")
    @app_commands.describe(name="Name for the new scene")
    async def scene_create(self, interaction: discord.Interaction, name: str):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can create scenes.", ephemeral=True)
            return
            
        if len(name) > 100:
            await interaction.response.send_message("❌ Scene name must be 100 characters or less.", ephemeral=True)
            return
            
        # Check if scene with this name already exists
        existing_scene = repo.get_scene_by_name(interaction.guild.id, name)
        if existing_scene:
            await interaction.response.send_message(f"❌ A scene named '{name}' already exists.", ephemeral=True)
            return
            
        scene_id = repo.create_scene(interaction.guild.id, name)
        await interaction.response.send_message(f"✅ Created new scene: **{name}**", ephemeral=True)

    @scene_group.command(name="switch", description="Switch to a different scene")
    @app_commands.describe(scene_name="Name of the scene to switch to")
    @app_commands.autocomplete(scene_name=scene_name_autocomplete)
    async def scene_switch(self, interaction: discord.Interaction, scene_name: str):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can switch scenes.", ephemeral=True)
            return
            
        scene = repo.get_scene_by_name(interaction.guild.id, scene_name)
        if not scene:
            await interaction.response.send_message(f"❌ Scene '{scene_name}' not found.", ephemeral=True)
            return
            
        repo.set_active_scene(interaction.guild.id, scene["id"])
        await interaction.response.send_message(f"🔄 Switched to scene: **{scene_name}**", ephemeral=True)

    @scene_group.command(name="list", description="List all scenes")
    async def scene_list(self, interaction: discord.Interaction):
        scenes = repo.get_scenes(interaction.guild.id)
        is_gm = await repo.has_gm_permission(interaction.guild.id, interaction.user)
        
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
            active_marker = "✓ " if scene["is_active"] else ""
            scene_lines.append(f"{active_marker}**{scene['name']}**")
            
        embed.description = "\n".join(scene_lines)
        
        if is_gm:
            embed.set_footer(text="Use /scene switch to change the active scene")
            
        await interaction.response.send_message(embed=embed, ephemeral=False)

    @scene_group.command(name="delete", description="Delete a scene")
    @app_commands.describe(scene_name="Name of the scene to delete")
    @app_commands.autocomplete(scene_name=scene_name_autocomplete)
    async def scene_delete(self, interaction: discord.Interaction, scene_name: str):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can delete scenes.", ephemeral=True)
            return
            
        scene = repo.get_scene_by_name(interaction.guild.id, scene_name)
        if not scene:
            await interaction.response.send_message(f"❌ Scene '{scene_name}' not found.", ephemeral=True)
            return
            
        # Create confirmation view
        view = ConfirmDeleteView(interaction.guild.id, scene)
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
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can rename scenes.", ephemeral=True)
            return
            
        if len(new_name) > 100:
            await interaction.response.send_message("❌ Scene name must be 100 characters or less.", ephemeral=True)
            return
            
        # Check if scene with the new name already exists
        existing_scene = repo.get_scene_by_name(interaction.guild.id, new_name)
        if existing_scene:
            await interaction.response.send_message(f"❌ A scene named '{new_name}' already exists.", ephemeral=True)
            return
            
        scene = repo.get_scene_by_name(interaction.guild.id, current_name)
        if not scene:
            await interaction.response.send_message(f"❌ Scene '{current_name}' not found.", ephemeral=True)
            return
            
        repo.rename_scene(interaction.guild.id, scene["id"], new_name)
        await interaction.response.send_message(
            f"✅ Renamed scene from **{current_name}** to **{new_name}**", 
            ephemeral=True
        )

    @scene_group.command(name="add", description="Add an NPC to the current scene.")
    @app_commands.describe(npc_name="The name of the NPC to add to the scene")
    @app_commands.autocomplete(npc_name=npc_name_autocomplete)
    async def scene_add(self, interaction: discord.Interaction, npc_name: str):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage the scene.", ephemeral=True)
            return
            
        active_scene = repo.get_active_scene(interaction.guild.id)
        if not active_scene:
            await interaction.response.send_message("❌ No active scene. Create one with `/scene create` first.", ephemeral=True)
            return
            
        npc = repo.get_character(interaction.guild.id, npc_name)
        if not npc:
            await interaction.response.send_message("❌ NPC not found. Did you create it with `/character create npc`?", ephemeral=True)
            return
            
        scene_npcs = repo.get_scene_npc_ids(interaction.guild.id)
        if npc.id in scene_npcs:
            await interaction.response.send_message("⚠️ That NPC is already in the scene.", ephemeral=True)
            return
            
        repo.add_scene_npc(interaction.guild.id, npc.id)
        await interaction.response.send_message(
            f"✅ **{npc_name}** added to scene **{active_scene['name']}**.", 
            ephemeral=True
        )

    @scene_group.command(name="remove", description="Remove an NPC from the current scene.")
    @app_commands.describe(npc_name="The name of the NPC to remove from the scene")
    @app_commands.autocomplete(npc_name=npcs_in_scene_autocomplete)
    async def scene_remove(self, interaction: discord.Interaction, npc_name: str):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage the scene.", ephemeral=True)
            return
            
        active_scene = repo.get_active_scene(interaction.guild.id)
        if not active_scene:
            await interaction.response.send_message("❌ No active scene. Create one with `/scene create` first.", ephemeral=True)
            return
            
        scene_npcs = repo.get_scene_npc_ids(interaction.guild.id)
        npc = repo.get_character(interaction.guild.id, npc_name)
        
        if not npc:
            await interaction.response.send_message("❌ NPC not found.", ephemeral=True)
            return
            
        if npc.id not in scene_npcs:
            await interaction.response.send_message("❌ That NPC isn't in the current scene.", ephemeral=True)
            return
            
        repo.remove_scene_npc(interaction.guild.id, npc.id)
        await interaction.response.send_message(
            f"🗑️ **{npc_name}** removed from scene **{active_scene['name']}**.", 
            ephemeral=True
        )

    @scene_group.command(name="clear", description="Clear all NPCs from the current scene.")
    async def scene_clear(self, interaction: discord.Interaction):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage the scene.", ephemeral=True)
            return
            
        active_scene = repo.get_active_scene(interaction.guild.id)
        if not active_scene:
            await interaction.response.send_message("❌ No active scene. Create one with `/scene create` first.", ephemeral=True)
            return
            
        repo.clear_scene_npcs(interaction.guild.id)
        await interaction.response.send_message(
            f"🧹 All NPCs cleared from scene **{active_scene['name']}**.", 
            ephemeral=True
        )

    @scene_group.command(name="view", description="View the current scene.")
    async def scene_view(self, interaction: discord.Interaction):
        active_scene = repo.get_active_scene(interaction.guild.id)
        if not active_scene:
            # For GMs, suggest creating a scene. For players, just inform them there's no scene.
            if await repo.has_gm_permission(interaction.guild.id, interaction.user):
                await interaction.response.send_message(
                    "❌ No active scene. Create one with `/scene create` first.", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message("No active scene has been set up by the GM.", ephemeral=True)
            return
        
        system = repo.get_system(interaction.guild.id)
        sheet = factories.get_specific_sheet(system)
        npc_ids = repo.get_scene_npc_ids(interaction.guild.id)
        is_gm = await repo.has_gm_permission(interaction.guild.id, interaction.user)
        
        lines = []
        for npc_id in npc_ids:
            npc = repo.get_character_by_id(interaction.guild.id, npc_id)
            if npc:
                lines.append(sheet.format_npc_scene_entry(npc, is_gm))
                
        notes = repo.get_scene_notes(interaction.guild.id)
        description = ""
        if notes:
            description += f"**Notes:**\n{notes}\n\n"
            
        if lines:
            description += "\n\n".join(lines)
        else:
            description += "📭 No NPCs are currently in this scene."
            
        embed = discord.Embed(
            title=f"🎭 Scene: {active_scene['name']}",
            description=description,
            color=discord.Color.purple()
        )
        
        view = shared_views.SceneNotesEditView(interaction.guild.id, is_gm)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=False)


class ConfirmDeleteView(discord.ui.View):
    def __init__(self, guild_id, scene):
        super().__init__(timeout=60)
        self.guild_id = guild_id
        self.scene = scene
        
    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        repo.delete_scene(self.guild_id, self.scene["id"])
        await interaction.response.edit_message(
            content=f"✅ Scene **{self.scene['name']}** has been deleted.",
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