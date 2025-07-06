import uuid
import discord
from discord.ext import commands
from discord import app_commands
from typing import List
from data.repositories.repository_factory import repositories
from core import channel_restriction
from core.base_models import EntityType, RelationshipType
import core.factories as factories

SYSTEM = "fate"

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

    fate_extra_group = app_commands.Group(
        name="extra",
        description="Fate extra management commands",
        parent=fate_group
    )

    # Autocomplete functions for extras
    async def extra_type_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for extra types"""
        # Only show types that make sense for extras
        extra_types = factories.get_system_entity_types(SYSTEM)
        
        # Filter based on user input
        filtered_types = [entity_type for entity_type in extra_types if current.lower() in entity_type.value.lower()]
        
        return [
            app_commands.Choice(name=entity_type.value.title(), value=entity_type.value)
            for entity_type in filtered_types[:25]
        ]

    async def extra_name_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for extra names - shows extras user owns or all if GM"""
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Get all characters/entities and filter for Fate extras
        if is_gm:
            all_entities = repositories.character.get_all_by_guild(str(interaction.guild.id))
        else:
            all_entities = repositories.character.get_user_characters(str(interaction.guild.id), str(interaction.user.id))
        
        # Filter for extras (non-PC, non-NPC entities)
        extras = [
            entity for entity in all_entities 
            if entity.entity_type in factories.get_system_entity_types(SYSTEM)
            and current.lower() in entity.name.lower()
        ]
        
        return [
            app_commands.Choice(name=f"{extra.name} ({extra.entity_type.value})", value=extra.name)
            for extra in extras[:25]
        ]

    @fate_extra_group.command(name="create", description="Create a new Fate extra")
    @app_commands.describe(
        extra_type="Type of extra to create (generic, item, companion)",
        name="Name for the new extra"
    )
    @app_commands.autocomplete(extra_type=extra_type_autocomplete)
    @channel_restriction.no_ic_channels()
    async def fate_extra_create(
        self, 
        interaction: discord.Interaction, 
        extra_type: str, 
        name: str
    ):
        """Create a new Fate extra"""
        # Check if server is using Fate
        system = repositories.server.get_system(str(interaction.guild.id))
        if system != "fate":
            await interaction.response.send_message("⚠️ This command is only available for Fate games.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        # Validate entity type
        try:
            e_type = EntityType(extra_type)
        except ValueError:
            await interaction.followup.send(f"❌ Invalid extra type '{extra_type}'. Use generic, item, or companion.", ephemeral=True)
            return
        
        # Only allow certain types for extras
        if e_type not in factories.get_system_entity_types(SYSTEM):
            await interaction.followup.send(f"❌ '{extra_type}' is not a valid extra type. Use generic, item, or companion.", ephemeral=True)
            return
        
        # Check if extra with this name already exists
        existing = repositories.entity.get_by_name(str(interaction.guild.id), name)
        if existing:
            await interaction.followup.send(f"❌ A character/extra named `{name}` already exists.", ephemeral=True)
            return
        
        # Create the extra using the factory system
        extra_id = str(uuid.uuid4())
        
        # Get the appropriate character class for this entity type and system
        CharacterClass = factories.get_specific_entity(system, e_type)
        
        # Build entity dict
        from core.base_models import BaseEntity
        extra_dict = BaseEntity.build_entity_dict(
            id=extra_id,
            name=name,
            owner_id=str(interaction.user.id),
            entity_type=e_type
        )
        
        extra = CharacterClass(extra_dict)
        extra.apply_defaults(entity_type=e_type, guild_id=str(interaction.guild.id))
        
        # Save the extra
        repositories.character.upsert_character(str(interaction.guild.id), extra, system=system)
        
        await interaction.followup.send(f"✅ Created Fate {extra_type}: **{name}**", ephemeral=True)

    @fate_extra_group.command(name="delete", description="Delete a Fate extra")
    @app_commands.describe(extra_name="Name of the extra to delete")
    @app_commands.autocomplete(extra_name=extra_name_autocomplete)
    @channel_restriction.no_ic_channels()
    async def fate_extra_delete(self, interaction: discord.Interaction, extra_name: str):
        """Delete a Fate extra with confirmation"""
        # Check if server is using Fate
        system = repositories.server.get_system(str(interaction.guild.id))
        if system != "fate":
            await interaction.response.send_message("⚠️ This command is only available for Fate games.", ephemeral=True)
            return

        extra = repositories.entity.get_by_name(str(interaction.guild.id), extra_name)
        if not extra:
            await interaction.response.send_message(f"❌ Extra `{extra_name}` not found.", ephemeral=True)
            return
        
        # Verify it's actually an extra
        if extra.entity_type not in factories.get_system_entity_types(SYSTEM):
            await interaction.response.send_message(f"❌ `{extra_name}` is not an extra.", ephemeral=True)
            return
        
        # Check permissions
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm and str(extra.owner_id) != str(interaction.user.id):
            await interaction.response.send_message("❌ You can only delete extras you own.", ephemeral=True)
            return
        
        # Check if extra owns other entities (through relationships)
        owned_entities = repositories.relationship.get_children(
            str(interaction.guild.id), 
            extra.id, 
            RelationshipType.POSSESSES.value
        )
        
        if owned_entities:
            entity_names = [owned_entity.name for owned_entity in owned_entities]
            await interaction.response.send_message(
                f"❌ Cannot delete `{extra_name}` because it owns other entities: {', '.join(entity_names)}.\n"
                f"Please transfer or delete these entities first, or use `/relationship remove` to remove the ownership relationships.",
                ephemeral=True
            )
            return
        
        view = ConfirmDeleteExtraView(extra)
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to delete the {extra.entity_type.value} `{extra_name}`?\n"
            f"This action cannot be undone.",
            view=view,
            ephemeral=True
        )

    @fate_extra_group.command(name="view", description="View a Fate extra's details")
    @app_commands.describe(extra_name="Name of the extra to view")
    @app_commands.autocomplete(extra_name=extra_name_autocomplete)
    @channel_restriction.no_ic_channels()
    async def fate_extra_view(self, interaction: discord.Interaction, extra_name: str):
        """View detailed information about a Fate extra"""
        # Check if server is using Fate
        system = repositories.server.get_system(str(interaction.guild.id))
        if system != "fate":
            await interaction.response.send_message("⚠️ This command is only available for Fate games.", ephemeral=True)
            return

        extra = repositories.entity.get_by_name(str(interaction.guild.id), extra_name)
        if not extra:
            await interaction.response.send_message(f"❌ Extra `{extra_name}` not found.", ephemeral=True)
            return
        
        # Verify it's actually an extra
        if extra.entity_type not in factories.get_system_entity_types(SYSTEM):
            await interaction.response.send_message(f"❌ `{extra_name}` is not an extra.", ephemeral=True)
            return
        
        # Check permissions
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm and str(extra.owner_id) != str(interaction.user.id):
            # For companions, also check if user owns characters that control it
            if extra.entity_type == EntityType.COMPANION:
                controlling_chars = repositories.relationship.get_parents(
                    str(interaction.guild.id),
                    extra.id,
                    RelationshipType.CONTROLS.value
                )
                
                user_controls_companion = any(
                    str(controller.owner_id) == str(interaction.user.id) 
                    for controller in controlling_chars
                )
                
                if not user_controls_companion:
                    await interaction.response.send_message("❌ You can only view extras you own or companions controlled by your characters.", ephemeral=True)
                    return
            else:
                await interaction.response.send_message("❌ You can only view extras you own.", ephemeral=True)
                return
        
        # Get the sheet view for editing using the character's class method
        sheet_view = extra.get_sheet_edit_view(interaction.user.id)
        
        embed = extra.format_full_sheet()
        await interaction.response.send_message(embed=embed, view=sheet_view, ephemeral=True)

    @fate_extra_group.command(name="list", description="List Fate extras")
    @app_commands.describe(
        extra_type="Filter by extra type",
        show_relationships="Show ownership and control relationships"
    )
    @app_commands.autocomplete(extra_type=extra_type_autocomplete)
    @channel_restriction.no_ic_channels()
    async def fate_extra_list(
        self, 
        interaction: discord.Interaction, 
        extra_type: str = None,
        show_relationships: bool = False
    ):
        """List Fate extras with optional filtering"""
        # Check if server is using Fate
        system = repositories.server.get_system(str(interaction.guild.id))
        if system != "fate":
            await interaction.response.send_message("⚠️ This command is only available for Fate games.", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        # Get all characters and filter for extras
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if is_gm:
            all_entities = repositories.character.get_all_by_guild(str(interaction.guild.id))
        else:
            all_entities = repositories.character.get_user_characters(str(interaction.guild.id), str(interaction.user.id))
        
        # Filter for extras
        extras = [
            entity for entity in all_entities 
            if entity.entity_type in factories.get_system_entity_types(SYSTEM)
        ]
        
        # Apply type filter if specified
        if extra_type:
            try:
                filter_type = EntityType(extra_type)
                extras = [e for e in extras if e.entity_type == filter_type]
            except ValueError:
                await interaction.followup.send(f"❌ Invalid extra type '{extra_type}'.", ephemeral=True)
                return
        
        if not extras:
            type_text = f" of type {extra_type}" if extra_type else ""
            await interaction.followup.send(f"No Fate extras{type_text} found.", ephemeral=True)
            return
        
        # Create embed
        title = "Fate Extras"
        if extra_type:
            title += f" ({extra_type})"
        
        embed = discord.Embed(title=title, color=discord.Color.purple())
        
        if show_relationships:
            # Show detailed relationship information
            extra_info = []
            for extra in extras:
                # Get owned entities
                owned_entities = repositories.relationship.get_children(
                    str(interaction.guild.id), 
                    extra.id, 
                    RelationshipType.POSSESSES.value
                )
                
                # Get controlled entities
                controlled_entities = repositories.relationship.get_children(
                    str(interaction.guild.id), 
                    extra.id, 
                    RelationshipType.CONTROLS.value
                )
                
                # Get controlling entities (for companions)
                controlling_entities = repositories.relationship.get_parents(
                    str(interaction.guild.id), 
                    extra.id, 
                    RelationshipType.CONTROLS.value
                )
                
                info = f"**{extra.name}** ({extra.entity_type.value})"
                if owned_entities:
                    owned_names = [e.name for e in owned_entities]
                    info += f"\n  *Owns: {', '.join(owned_names)}*"
                if controlled_entities:
                    controlled_names = [e.name for e in controlled_entities]
                    info += f"\n  *Controls: {', '.join(controlled_names)}*"
                if controlling_entities:
                    controller_names = [e.name for e in controlling_entities]
                    info += f"\n  *Controlled by: {', '.join(controller_names)}*"
                
                extra_info.append(info)
            
            embed.description = "\n\n".join(extra_info)
        else:
            # Group by entity type for simple view
            by_type = {}
            for extra in extras:
                type_name = extra.entity_type.value
                if type_name not in by_type:
                    by_type[type_name] = []
                by_type[type_name].append(extra)
            
            # Add fields for each type
            for type_name, type_extras in by_type.items():
                extra_list = []
                for extra in type_extras:
                    # Show controlled by info for companions
                    if extra.entity_type == EntityType.COMPANION:
                        controllers = repositories.relationship.get_parents(
                            str(interaction.guild.id), 
                            extra.id, 
                            RelationshipType.CONTROLS.value
                        )
                        control_info = f" (controlled by {controllers[0].name})" if controllers else ""
                        extra_list.append(f"• {extra.name}{control_info}")
                    else:
                        # Show owned entities count if any
                        owned_entities = repositories.relationship.get_children(
                            str(interaction.guild.id), 
                            extra.id, 
                            RelationshipType.POSSESSES.value
                        )
                        owned_info = f" ({len(owned_entities)} owned)" if owned_entities else ""
                        extra_list.append(f"• {extra.name}{owned_info}")
                
                embed.add_field(
                    name=f"{type_name.title()} ({len(type_extras)})",
                    value="\n".join(extra_list)[:1024],  # Discord field limit
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    # Existing scene aspects command
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
    def __init__(self, extra):
        super().__init__(timeout=60)
        self.extra = extra

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Delete the extra (this will also delete all relationships)
        repositories.character.delete_character(str(interaction.guild.id), self.extra.id)
        await interaction.response.edit_message(
            content=f"✅ Deleted {self.extra.entity_type.value} `{self.extra.name}`.",
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