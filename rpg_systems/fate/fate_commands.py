import uuid
import discord
from discord.ext import commands
from discord import app_commands
from typing import List
from data.repositories.repository_factory import repositories
from core import command_decorators
from core.base_models import BaseEntity, EntityType, EntityLinkType, SystemType
import core.factories as factories

SYSTEM = SystemType.FATE

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

    # Existing scene aspects command
    @fate_scene_group.command(name="aspects", description="Show detailed aspects in the current scene")
    async def fate_scene_aspects(self, interaction: discord.Interaction):
        """Show all aspects in the current scene and their descriptions"""
        # Check if server is using Fate
        system = repositories.server.get_system(str(interaction.guild.id))
        if system != SystemType.FATE:
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
        
        # 1. Get game aspects
        game_aspects = repositories.fate_game_aspects.get_game_aspects(str(interaction.guild.id)) or []
        
        # Format game aspect strings
        game_aspect_lines = []
        for aspect in game_aspects:
            aspect_str = aspect.get_full_aspect_string(is_gm=is_gm)
            if aspect_str:  # Skip empty strings (hidden aspects for non-GMs)
                game_aspect_lines.append(aspect_str)
        
        if game_aspect_lines:
            embed.add_field(
                name="Game Aspects",
                value="\n".join(f"• {line}" for line in game_aspect_lines),
                inline=False
            )
        
        # 2. Get scene aspects
        scene_aspects = repositories.fate_aspects.get_aspects(str(interaction.guild.id), str(active_scene.scene_id)) or []
        
        # Format scene aspect strings
        scene_aspect_lines = []
        for aspect in scene_aspects:
            aspect_str = aspect.get_full_aspect_string(is_gm=is_gm)
            if aspect_str:  # Skip empty strings (hidden aspects for non-GMs)
                scene_aspect_lines.append(aspect_str)
        
        if scene_aspect_lines:
            embed.add_field(
                name="Scene Aspects",
                value="\n".join(f"• {line}" for line in scene_aspect_lines),
                inline=False
            )
            
        # 3. Get zone aspects
        scene_zones = repositories.fate_zones.get_zones(str(interaction.guild.id), str(active_scene.scene_id)) or []
        zone_aspects = repositories.fate_zone_aspects.get_all_zone_aspects_for_scene(str(interaction.guild.id), str(active_scene.scene_id)) or {}
        
        # Add zone aspects to embed
        for zone_name in scene_zones:
            if zone_name in zone_aspects and zone_aspects[zone_name]:
                zone_aspect_lines = []
                for aspect in zone_aspects[zone_name]:
                    aspect_str = aspect.get_full_aspect_string(is_gm=is_gm)
                    if aspect_str:  # Skip empty strings (hidden aspects for non-GMs)
                        zone_aspect_lines.append(aspect_str)
                
                if zone_aspect_lines:
                    embed.add_field(
                        name=f"{zone_name} Zone Aspects",
                        value="\n".join(f"• {line}" for line in zone_aspect_lines),
                        inline=False
                    )
        
        # 4. Get character aspects from NPCs in the scene
        npc_aspects_by_character = {}
        npc_ids = repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), str(active_scene.scene_id))
        
        for npc_id in npc_ids:
            # Get all characters and find the specific NPC
            npc = repositories.entity.get_by_id(str(npc_id))
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
            
            # Add consequence aspects for NPCs
            if npc.consequence_tracks:
                for track in npc.consequence_tracks:
                    for consequence in track.consequences:
                        if consequence.is_filled():
                            consequence_text = f"{consequence.aspect.name}"
                            if consequence.aspect.free_invokes > 0:
                                consequence_text += f" [{consequence.aspect.free_invokes}]"
                            consequence_text += f" ({consequence.name} Consequence)"
                            character_aspects.append(consequence_text)
                    
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
        
        # 5. Get player character aspects
        pc_aspects_by_character = {}
        
        # Get all characters for the guild that aren't NPCs
        all_characters = repositories.active_character.get_all_active_characters(interaction.guild.id)
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
            
            # Add consequence aspects for PCs
            if character.consequence_tracks:
                for track in character.consequence_tracks:
                    for consequence in track.consequences:
                        if consequence.is_filled():
                            consequence_text = f"{consequence.aspect.name}"
                            if consequence.aspect.free_invokes > 0:
                                consequence_text += f" [{consequence.aspect.free_invokes}]"
                            consequence_text += f" ({consequence.name} Consequence)"
                            character_aspects.append(consequence_text)

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
        else:
            embed.set_footer(text="Hidden aspects are not shown. Contact the GM for more information.")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmDeleteExtraView(discord.ui.View):
    def __init__(self, extra: BaseEntity, transfer_inventory: bool = False):
        super().__init__(timeout=60)
        self.extra = extra
        self.transfer_inventory = transfer_inventory

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.transfer_inventory:
            # Remove all POSSESSES links for this extra
            possessed_entities = repositories.link.get_children(
                str(interaction.guild.id),
                self.extra.id,
                EntityLinkType.POSSESSES.value
            )
            
            for possessed_entity in possessed_entities:
                repositories.link.delete_links_by_entities(
                    str(interaction.guild.id),
                    self.extra.id,
                    possessed_entity.id,
                    EntityLinkType.POSSESSES.value
                )
        
        # Delete the extra (this will also delete all remaining links)
        repositories.entity.delete_entity(str(interaction.guild.id), self.extra.id)
        
        delete_msg = f"✅ Deleted {self.extra.entity_type.value} `{self.extra.name}`."
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

async def setup_fate_commands(bot: commands.Bot):
    await bot.add_cog(FateCommands(bot))