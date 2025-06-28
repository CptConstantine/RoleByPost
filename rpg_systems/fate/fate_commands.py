import discord
from discord.ext import commands
from discord import app_commands
from data import repo
from rpg_systems.fate.fate_scene_view import FateSceneView, EditSceneAspectsModal

class FateCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    fate_group = app_commands.Group(
        name="fate",
        description="Fate-specific commands"
    )
    
    fate_scene_group = app_commands.Group(
        name="scene", 
        description="Fate scene commands",
        parent=fate_group
    )

    @fate_scene_group.command(name="aspects", description="Show detailed aspects in the current scene")
    async def fate_scene_aspects(self, interaction: discord.Interaction):
        """Show all aspects in the current scene and their descriptions"""
        # Check if server is using Fate
        system = repo.get_system(interaction.guild.id)
        if system != "fate":
            await interaction.response.send_message("⚠️ This command is only available for Fate games.", ephemeral=True)
            return

        # Get active scene
        active_scene = repo.get_active_scene(interaction.guild.id)
        if not active_scene:
            await interaction.response.send_message("⚠️ No active scene found. Create one with `/scene create` first.", ephemeral=True)
            return
            
        # Check if user is a GM 
        is_gm = await repo.has_gm_permission(interaction.guild.id, interaction.user)
        
        # Start building our response
        embed = discord.Embed(
            title=f"🎭 Aspects in Scene: {active_scene['name']}",
            color=discord.Color.gold()
        )
        
        # 1. Get scene aspects
        scene_aspects = repo.get_fate_scene_aspects(interaction.guild.id, active_scene['id']) or []
        aspect_lines = []
        
        # Check format and convert if necessary
        scene_aspect_list = []
        for aspect in scene_aspects:
            if isinstance(aspect, str):
                # Legacy format
                scene_aspect_list.append({
                    "name": aspect,
                    "description": "",
                    "is_hidden": False
                })
            else:
                scene_aspect_list.append(aspect)
        
        # Add scene aspects to the list
        for aspect in scene_aspect_list:
            name = aspect.get("name", "")
            description = aspect.get("description", "")
            is_hidden = aspect.get("is_hidden", False)
            
            # Skip hidden aspects for non-GMs
            if is_hidden and not is_gm:
                continue
                
            line = f"**{name}**"
            if is_hidden:
                line = f"*{line} (hidden)*"
                
            if description:
                line += f": {description}"
                
            aspect_lines.append(line)
        
        if aspect_lines:
            embed.add_field(
                name="Scene Aspects",
                value="\n".join(aspect_lines),
                inline=False
            )
            
        # 2. Get zone aspects (if zones implementation supports aspects)
        zone_aspects = []
        scene_zones = repo.get_fate_scene_zones(interaction.guild.id, active_scene['id']) or []
        
        # In this example, we're assuming zones don't yet have aspects
        # This is where you'd add zone aspect handling if implemented
        
        # 3. Get character aspects from NPCs in the scene
        npc_aspects_by_character = {}
        npc_ids = repo.get_scene_npc_ids(interaction.guild.id, active_scene['id'])
        
        for npc_id in npc_ids:
            npc = repo.get_character_by_id(interaction.guild.id, npc_id)
            if not npc:
                continue
                
            # Get aspect data for this NPC
            character_aspects = []
            if hasattr(npc, 'aspects') and npc.aspects:
                for aspect in npc.aspects:
                    name = aspect.get("name", "")
                    description = aspect.get("description", "")
                    is_hidden = aspect.get("is_hidden", False)
                    
                    # Skip hidden aspects for non-GMs
                    if is_hidden and not is_gm:
                        continue
                    
                    aspect_text = name
                    if is_hidden:
                        aspect_text = f"*{aspect_text} (hidden)*"
                        
                    if description:
                        aspect_text += f": {description}"
                        
                    character_aspects.append(aspect_text)
                    
            if character_aspects:
                npc_aspects_by_character[npc.name] = character_aspects
        
        # Add NPC aspects to embed
        for npc_name, aspects in npc_aspects_by_character.items():
            if aspects:
                embed.add_field(
                    name=f"{npc_name}'s Aspects",
                    value="\n".join(f"• {a}" for a in aspects),
                    inline=False
                )
        
        # 4. Get player character aspects
        # Get all active PCs in the guild
        pc_aspects_by_character = {}
        
        # Get all characters for the guild that aren't NPCs
        all_characters = repo.get_pcs_by_guild(interaction.guild.id)
        for character in all_characters:
            # Get aspect data for this PC
            character_aspects = []
            if hasattr(character, 'aspects') and character.aspects:
                for aspect in character.aspects:
                    name = aspect.get("name", "")
                    description = aspect.get("description", "")
                    is_hidden = aspect.get("is_hidden", False)
                    
                    # Skip hidden aspects for non-GMs if this isn't the PC's owner
                    is_owner = character.owner_id == interaction.user.id
                    
                    if is_hidden and not (is_gm or is_owner):
                        continue
                    
                    aspect_text = name
                    if is_hidden:
                        # Mark as hidden only in the display
                        aspect_text = f"*{aspect_text} (hidden)*"
                        
                    if description:
                        aspect_text += f": {description}"
                        
                    character_aspects.append(aspect_text)
                    
            if character_aspects:
                pc_aspects_by_character[character.name] = character_aspects
        
        # Add PC aspects to embed - these come after NPC aspects
        for pc_name, aspects in pc_aspects_by_character.items():
            if aspects:
                embed.add_field(
                    name=f"{pc_name}'s Aspects",
                    value="\n".join(f"• {a}" for a in aspects),
                    inline=False
                )

        # If no aspects were found anywhere
        if not embed.fields:
            embed.description = "No aspects found in this scene."
            
        # Add footer note for GMs
        if is_gm:
            embed.set_footer(text="As GM, you can see all aspects including hidden ones.")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup_fate_commands(bot):
    await bot.add_cog(FateCommands(bot))