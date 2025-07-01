import discord
from discord.ext import commands
from discord import app_commands
from data.repositories.repository_factory import repositories

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
        system = repositories.server.get_system(str(interaction.guild.id))
        if system != "fate":
            await interaction.response.send_message("⚠️ This command is only available for Fate games.", ephemeral=True)
            return

        # Get active scene
        active_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
        if not active_scene:
            await interaction.response.send_message("⚠️ No active scene found. Create one with `/scene create` first.", ephemeral=True)
            return
            
        # Check if user is a GM 
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Start building our response
        embed = discord.Embed(
            title=f"🎭 Aspects in Scene: {active_scene.name}",
            color=discord.Color.gold()
        )
        
        # 1. Get scene aspects
        scene_aspects = repositories.fate_aspects.get_aspects(str(interaction.guild.id), str(active_scene.scene_id)) or []
        
        # Format aspect strings
        aspect_lines = []
        for aspect in scene_aspects:
            aspect_str = aspect.get_full_aspect_string(is_gm=is_gm)
            if aspect_str:  # Skip empty strings (hidden aspects for non-GMs)
                aspect_lines.append(aspect_str)
        
        if aspect_lines:
            embed.add_field(
                name="Scene Aspects",
                value="\n".join(aspect_lines),
                inline=False
            )
            
        # 2. Get zone aspects (if zones implementation supports aspects)
        zone_aspects = []
        scene_zones = repositories.fate_zones.get_zones(str(interaction.guild.id), str(active_scene.scene_id)) or []
        
        # In this example, we're assuming zones don't yet have aspects
        # This is where you'd add zone aspect handling if implemented
        
        # 3. Get character aspects from NPCs in the scene
        npc_aspects_by_character = {}
        npc_ids = repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), str(active_scene.scene_id))
        
        for npc_id in npc_ids:
            # Get all characters and find the specific NPC
            npc = repositories.character.get_by_id(str(npc_id))
            if not npc:
                continue
                
            # Get aspect data for this NPC
            character_aspects = []
            if npc.aspects:
                # Format each aspect string
                for aspect in npc.aspects:
                    aspect_str = aspect.get_full_aspect_string(is_gm=is_gm)
                    if aspect_str:  # Skip empty strings (hidden aspects for non-GMs)
                        character_aspects.append(aspect_str)
                    
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
        pc_aspects_by_character = {}
        
        # Get all characters for the guild that aren't NPCs
        all_characters = repositories.character.get_pcs_by_guild(str(interaction.guild.id))
        for character in all_characters:
            # Get aspect data for this PC
            character_aspects = []
            if character.aspects:
                # Format each aspect string
                for aspect in character.aspects:
                    # Check if this user owns the character
                    is_owner = str(character.owner_id) == str(interaction.user.id)
                    aspect_str = aspect.get_full_aspect_string(is_gm=is_gm, is_owner=is_owner)
                    if aspect_str:  # Skip empty strings (hidden aspects for non-GMs/non-owners)
                        character_aspects.append(aspect_str)
                    
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