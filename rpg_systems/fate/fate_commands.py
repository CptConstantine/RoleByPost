import uuid
import discord
from discord.ext import commands
from discord import app_commands
from typing import List
from commands.autocomplete import active_player_characters_autocomplete
from core.utils import _get_character_by_name_or_nickname
from data.repositories.repository_factory import repositories
from core import command_decorators
from core.base_models import BaseEntity, EntityType, EntityLinkType, SystemType
import core.factories as factories
from rpg_systems.fate.fate_autocomplete import active_player_characters_plus_fate_points_autocomplete
from rpg_systems.fate.fate_character import FateCharacter
from rpg_systems.fate.fate_compel_views import CompelType, CompelView

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
    @command_decorators.player_or_gm_role_required()
    @command_decorators.no_ic_channels()
    @command_decorators.system_required(SYSTEM)
    async def fate_scene_aspects(self, interaction: discord.Interaction):
        """Show all aspects in the current scene and their descriptions"""
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

    @fate_group.command(name="give-fp", description="GM: Award a fate point to a character")
    @app_commands.describe(char_name="Character to award fate point to")
    @app_commands.autocomplete(char_name=active_player_characters_autocomplete)
    @command_decorators.gm_role_required()
    @command_decorators.no_ic_channels()
    @command_decorators.system_required(SYSTEM)
    async def give_fate_point(self, interaction: discord.Interaction, char_name: str):
        """GM awards a fate point to a character"""
        character = await _get_character_by_name_or_nickname(interaction.guild.id, char_name)
        
        if not character:
            await interaction.response.send_message(f"❌ Character '{char_name}' not found.", ephemeral=True)
            return
        
        if not isinstance(character, FateCharacter):
            await interaction.response.send_message(f"❌ Character '{char_name}' is not a Fate character.", ephemeral=True)
            return
        
        # Award fate point
        success = await self._award_fate_point(character, interaction.guild.id)
        
        if success:
            embed = discord.Embed(
                title="Fate Point Awarded",
                description=f"**{character.name}** has been awarded 1 fate point by the GM.",
                color=0x00ff00
            )
            embed.add_field(
                name="Current Fate Points", 
                value=character.fate_points, 
                inline=False
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to award fate point.", ephemeral=True)

    @fate_group.command(name="compel", description="Propose a compel for a character")
    @app_commands.describe(
        char_name="Character to compel",
        message="Description of the compel"
    )
    @app_commands.autocomplete(char_name=active_player_characters_plus_fate_points_autocomplete)
    @command_decorators.player_or_gm_role_required()
    @command_decorators.system_required(SYSTEM)
    async def compel_character(self, interaction: discord.Interaction, char_name: str, message: str):
        """Propose a compel for a character"""
        character = await _get_character_by_name_or_nickname(interaction.guild.id, char_name)
        
        if not character:
            await interaction.response.send_message(f"❌ Character '{char_name}' not found.", ephemeral=True)
            return
        
        if not isinstance(character, FateCharacter):
            await interaction.response.send_message(f"❌ Character '{char_name}' is not a Fate character.", ephemeral=True)
            return
        
        # Check if GM or player compel
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        compel_type = CompelType.GM if is_gm else CompelType.PLAYER

        # Player spends FP if it's a player compel
        if compel_type == CompelType.PLAYER:
            active_char = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
            success = await self._spend_fate_point(active_char, interaction.guild.id)
            if not success:
                await interaction.response.send_message(
                    f"❌ {active_char.name} has no fate points to spend for this compel.",
                    ephemeral=True
                )
                return
        
        # Create compel view
        view = CompelView(
            compel_type=compel_type,
            target_character=character.name,
            compeller_user_id=interaction.user.id,
            target_user_id=character.owner_id,
            message=message,
            guild_id=str(interaction.guild.id)
        )

        embed = view.create_status_embed()
        mentions = await view.get_compel_interaction_mentions(interaction)
        message_content = ", ".join(mentions) if mentions else ""
        message_content += f"\n{interaction.user.display_name} proposed a compel for **{character.name}**"

        await interaction.response.send_message(
            content=message_content,
            embed=embed,
            view=view
        )

    @fate_group.command(name="refresh", description="GM: Reset all active characters' fate points to their refresh values")
    @command_decorators.gm_role_required()
    @command_decorators.no_ic_channels()
    @command_decorators.system_required(SYSTEM)
    async def refresh_fate_points(self, interaction: discord.Interaction, message: str = None):
        """GM resets all active player characters' fate points to their refresh values"""
        # Get all active characters
        all_characters = repositories.active_character.get_all_active_characters(interaction.guild.id)
        
        # Filter to only Fate characters
        fate_characters = [char for char in all_characters if isinstance(char, FateCharacter)]
        
        if not fate_characters:
            await interaction.response.send_message("❌ No active Fate characters found.", ephemeral=True)
            return
        
        # Process each character
        refreshed_characters = []
        unchanged_characters = []
        
        for character in fate_characters:
            # Only refresh if current FP is less than refresh value
            if character.fate_points < character.refresh:
                old_fp = character.fate_points
                character.fate_points = character.refresh
                repositories.entity.upsert_entity(interaction.guild.id, character, SYSTEM)
                refreshed_characters.append(f"**{character.name}**: {old_fp} → {character.refresh} FP")
            else:
                unchanged_characters.append(f"**{character.name}**: {character.fate_points} FP (unchanged)")
        
        # Create response embed
        embed = discord.Embed(
            title="🔄 Fate Points Refreshed",
            color=discord.Color.blue()
        )
        
        if refreshed_characters:
            embed.add_field(
                name="Characters Refreshed",
                value="\n".join(refreshed_characters),
                inline=False
            )
        
        if unchanged_characters:
            embed.add_field(
                name="Characters Already at Refresh or Higher",
                value="\n".join(unchanged_characters),
                inline=False
            )
        
        if not refreshed_characters and not unchanged_characters:
            embed.description = "No characters were processed."
        
        await interaction.response.send_message(content=message, embed=embed)

    async def _award_fate_point(self, character: FateCharacter, guild_id: str) -> bool:
        """Award 1 fate point to character"""
        try:
            character.fate_points = character.fate_points + 1
            repositories.entity.upsert_entity(guild_id, character, SYSTEM)
            return True
        except Exception:
            return False

    async def _spend_fate_point(self, character: FateCharacter, guild_id: str) -> bool:
        """Spend 1 fate point from character, return success"""
        if character.fate_points <= 0:
            return False
        
        try:
            character.fate_points = character.fate_points - 1
            repositories.entity.upsert_entity(guild_id, character, SYSTEM)
            return True
        except Exception:
            return False

async def setup_fate_commands(bot: commands.Bot):
    await bot.add_cog(FateCommands(bot))