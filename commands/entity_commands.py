import uuid
import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
from core import channel_restriction
from core.base_models import BaseEntity, EntityType, EntityLinkType
from data.repositories.repository_factory import repositories
import core.factories as factories

# Autocomplete functions
async def entity_type_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for entity types based on current system"""
    system = repositories.server.get_system(str(interaction.guild.id))
    valid_types = factories.get_system_entity_types(system)
    
    # Filter based on user input
    filtered_types = [entity_type for entity_type in valid_types if current.lower() in entity_type.value.lower()]
    
    return [
        app_commands.Choice(name=entity_type.value.title(), value=entity_type.value)
        for entity_type in filtered_types[:25]
    ]

async def entity_name_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for entity names - shows entities user owns or all if GM"""
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    
    if is_gm:
        # GMs can see all entities
        entities = repositories.entity.get_all_by_guild(str(interaction.guild.id))
    else:
        # Users can only see their own entities
        entities = repositories.entity.get_all_by_owner(str(interaction.guild.id), str(interaction.user.id))
    
    # Filter by current input
    filtered_entities = [
        entity for entity in entities 
        if current.lower() in entity.name.lower()
    ]
    
    return [
        app_commands.Choice(name=f"{entity.name} ({entity.entity_type.value})", value=entity.name)
        for entity in filtered_entities[:25]
    ]

async def top_level_entity_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for parent entities - entities that can own other entities"""
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    
    if is_gm:
        # GMs can see all entities as potential parents
        entities = repositories.entity.get_all_by_guild(str(interaction.guild.id))
    else:
        # Users can only use their own entities as parents
        entities = repositories.entity.get_all_by_owner(str(interaction.guild.id), str(interaction.user.id))
    
    # Add "None" option for top-level entities
    choices = [app_commands.Choice(name="None (Top Level)", value="")]
    
    # Filter by current input
    filtered_entities = [
        entity for entity in entities 
        if current.lower() in entity.name.lower()
    ]
    
    choices.extend([
        app_commands.Choice(name=f"{entity.name} ({entity.entity_type.value})", value=entity.name)
        for entity in filtered_entities[:24]  # 24 to make room for "None" option
    ])
    
    return choices

class EntityCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    entity_group = app_commands.Group(name="entity", description="Entity management commands")

    @entity_group.command(name="create", description="Create a new entity")
    @app_commands.describe(
        entity_type="Type of entity to create",
        name="Name for the new entity"
    )
    @app_commands.autocomplete(
        entity_type=entity_type_autocomplete
    )
    @channel_restriction.no_ic_channels()
    async def entity_create(
        self, 
        interaction: discord.Interaction, 
        entity_type: str, 
        name: str
    ):
        """Create a new entity"""
        await interaction.response.defer(ephemeral=True)
        
        system = repositories.server.get_system(str(interaction.guild.id))
        
        # Validate entity type for current system
        valid_types = factories.get_system_entity_types(system)
        
        if entity_type not in [type.value for type in valid_types]:
            await interaction.followup.send(f"❌ Invalid entity type '{entity_type}' for {system.upper()} system.", ephemeral=True)
            return
        
        e_type = EntityType(entity_type)
        
        # Check if entity with this name already exists
        existing = repositories.entity.get_by_name(str(interaction.guild.id), name)
        if existing:
            await interaction.followup.send(f"❌ An entity named `{name}` already exists.", ephemeral=True)
            return
        
        # Create the entity using the new factory method
        entity = factories.build_and_save_entity(
            system=system,
            entity_type=e_type,
            name=name,
            owner_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id)
        )
        
        await interaction.followup.send(f"✅ Created {entity_type}: **{name}**", ephemeral=True)

    @entity_group.command(name="delete", description="Delete an entity")
    @app_commands.describe(
        entity_name="Name of the entity to delete",
        transfer_inventory="If true, releases possessed items instead of blocking deletion"
    )
    @app_commands.autocomplete(entity_name=entity_name_autocomplete)
    @channel_restriction.no_ic_channels()
    async def entity_delete(self, interaction: discord.Interaction, entity_name: str, transfer_inventory: bool = False):
        """Delete an entity with confirmation"""
        entity = repositories.entity.get_by_name(str(interaction.guild.id), entity_name)
        if not entity:
            await interaction.response.send_message(f"❌ Entity `{entity_name}` not found.", ephemeral=True)
            return
        
        # Check permissions
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm and str(entity.owner_id) != str(interaction.user.id):
            await interaction.response.send_message("❌ You can only delete entities you own.", ephemeral=True)
            return
        
        # Check if entity possesses other entities (through links)
        possessed_entities = repositories.link.get_children(
            str(interaction.guild.id), 
            entity.id, 
            EntityLinkType.POSSESSES.value
        )
        
        if possessed_entities and not transfer_inventory:
            entity_names = [entity.name for entity in possessed_entities]
            await interaction.response.send_message(
                f"❌ Cannot delete `{entity_name}` because it possesses other entities: {', '.join(entity_names)}.\n"
                f"Use `transfer_inventory: True` to release these items, transfer them manually, or use `/link remove` to remove the possession links.",
                ephemeral=True
            )
            return
        
        view = ConfirmDeleteEntityView(entity, transfer_inventory)
        
        confirmation_msg = f"⚠️ Are you sure you want to delete `{entity_name}` ({entity.entity_type.value})?\n"
        
        if possessed_entities and transfer_inventory:
            entity_names = [entity.name for entity in possessed_entities]
            confirmation_msg += f"\n**This will also release the following possessed items:**\n{', '.join(entity_names)}\n"
        
        confirmation_msg += "\nThis action cannot be undone."
        
        await interaction.response.send_message(
            confirmation_msg,
            view=view,
            ephemeral=True
        )

    @entity_group.command(name="list", description="List entities")
    @app_commands.describe(
        owner_entity="Entity to list owned entities of (leave empty for top-level)",
        entity_type="Filter by entity type",
        show_links="Show ownership links"
    )
    @app_commands.autocomplete(
        owner_entity=top_level_entity_autocomplete,
        entity_type=entity_type_autocomplete
    )
    @channel_restriction.no_ic_channels()
    async def entity_list(
        self, 
        interaction: discord.Interaction, 
        owner_entity: str = None, 
        entity_type: str = None,
        show_links: bool = False
    ):
        """List entities with optional filtering"""
        await interaction.response.defer(ephemeral=True)
        
        # Determine what entities to show
        if owner_entity and owner_entity.strip():
            # List entities owned by specific entity
            owner = repositories.entity.get_by_name(str(interaction.guild.id), owner_entity)
            if not owner:
                await interaction.followup.send(f"❌ Owner entity `{owner_entity}` not found.", ephemeral=True)
                return
            
            entities = repositories.link.get_children(
                str(interaction.guild.id), 
                owner.id, 
                EntityLinkType.POSSESSES.value
            )
            title = f"Entities possessed by {owner.name}"
        else:
            # List top-level entities (those without owners)
            all_entities = repositories.entity.get_all_by_guild(str(interaction.guild.id))
            
            # Filter to only entities that are not owned by other entities
            entities = []
            for entity in all_entities:
                owners = repositories.link.get_parents(
                    str(interaction.guild.id), 
                    entity.id, 
                    EntityLinkType.POSSESSES.value
                )
                if not owners:  # No owners = top-level
                    entities.append(entity)
            
            title = "Top-level entities"
            if entity_type:
                # Apply entity type filter
                entities = [e for e in entities if e.entity_type.value == entity_type]
                title += f" ({entity_type})"
        
        if not entities:
            await interaction.followup.send("No entities found.", ephemeral=True)
            return
        
        # Create embed
        embed = discord.Embed(title=title, color=discord.Color.blue())
        
        if show_links:
            # Show detailed link information
            links = []
            for entity in entities:
                links_str = EntityLinkType.get_links_str(str(interaction.guild.id), entity)
                links_str = f"{entity.name} - {links_str if links_str else 'No links'}"
                links.append(links_str)
            embed.description = "\n\n".join(links)
        else:
            # Group by entity type for simple view
            by_type = {}
            for entity in entities:
                type_name = entity.entity_type.value
                if type_name not in by_type:
                    by_type[type_name] = []
                by_type[type_name].append(entity)
            
            # Add fields for each type
            for type_name, type_entities in by_type.items():
                entity_list = []
                for entity in type_entities:
                    # Show possessed entities count if any
                    possessed_entities = repositories.link.get_children(
                        str(interaction.guild.id), 
                        entity.id, 
                        EntityLinkType.POSSESSES.value
                    )
                    possessed_info = f" ({len(possessed_entities)} possessed)" if possessed_entities else ""
                    entity_list.append(f"• {entity.name}{possessed_info}")
                
                embed.add_field(
                    name=f"{type_name.title()} ({len(type_entities)})",
                    value="\n".join(entity_list)[:1024],  # Discord field limit
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @entity_group.command(name="view", description="View entity details with edit interface")
    @app_commands.describe(
        entity_name="Name of the entity to view",
        show_links="Show detailed link information"
    )
    @app_commands.autocomplete(entity_name=entity_name_autocomplete)
    @channel_restriction.no_ic_channels()
    async def entity_view(self, interaction: discord.Interaction, entity_name: str, show_links: bool = False):
        """View detailed information about an entity with edit interface"""
        entity = repositories.entity.get_by_name(str(interaction.guild.id), entity_name)
        if not entity:
            await interaction.response.send_message(f"❌ Entity `{entity_name}` not found.", ephemeral=True)
            return
        
        # Check permissions - only owners and GMs can view entities
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm and str(entity.owner_id) != str(interaction.user.id):
            await interaction.response.send_message("❌ You can only view entities you own.", ephemeral=True)
            return
        
        # Get the entity's sheet edit view
        sheet_view = entity.get_sheet_edit_view(interaction.user.id, is_gm=is_gm)
        
        # Format the full sheet embed
        embed = entity.format_full_sheet(str(interaction.guild.id), is_gm=is_gm)
        
        # Add link information if requested
        if show_links:
            # Add link information to the embed
            link_info = EntityLinkType.get_links_str(str(interaction.guild.id), entity)
            
            if link_info:
                embed.add_field(name="🔗 Links", value="\n".join(link_info), inline=False)

        await interaction.response.send_message(
            embed=embed,
            view=sheet_view,
            ephemeral=True
        )

    @entity_group.command(name="rename", description="Rename an entity")
    @app_commands.describe(
        entity_name="Current name of the entity",
        new_name="New name for the entity"
    )
    @app_commands.autocomplete(entity_name=entity_name_autocomplete)
    @channel_restriction.no_ic_channels()
    async def entity_rename(self, interaction: discord.Interaction, entity_name: str, new_name: str):
        """Rename an entity"""
        entity = repositories.entity.get_by_name(str(interaction.guild.id), entity_name)
        if not entity:
            await interaction.response.send_message(f"❌ Entity `{entity_name}` not found.", ephemeral=True)
            return
        
        # Check permissions
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm and str(entity.owner_id) != str(interaction.user.id):
            await interaction.response.send_message("❌ You can only rename entities you own.", ephemeral=True)
            return
        
        # Check if new name already exists
        existing = repositories.entity.get_by_name(str(interaction.guild.id), new_name)
        if existing and existing.id != entity.id:
            await interaction.response.send_message(f"❌ An entity named `{new_name}` already exists.", ephemeral=True)
            return
        
        # Perform rename
        repositories.entity.rename_entity(entity.id, new_name)
        
        await interaction.response.send_message(
            f"✅ Renamed `{entity_name}` to `{new_name}`.",
            ephemeral=True
        )

    @entity_group.command(name="deleteall", description="Delete all entities with no links (GM only)")
    @app_commands.describe(
        entity_type="Filter by entity type (optional)",
        confirm="Type 'DELETE' to confirm this destructive action"
    )
    @app_commands.autocomplete(entity_type=entity_type_autocomplete)
    @channel_restriction.no_ic_channels()
    async def entity_delete_all(
        self, 
        interaction: discord.Interaction, 
        confirm: str,
        entity_type: str = None
    ):
        """Delete all entities with no links - GM only command"""
        # Check GM permissions
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm:
            await interaction.response.send_message("❌ Only GMs can use this command.", ephemeral=True)
            return
        
        # Require confirmation
        if confirm.upper() != "DELETE":
            await interaction.response.send_message(
                "❌ You must type `DELETE` exactly to confirm this destructive action.",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Get all entities in the guild
        all_entities = repositories.entity.get_all_by_guild(str(interaction.guild.id))
        
        # Filter by entity type if specified
        if entity_type:
            all_entities = [e for e in all_entities if e.entity_type.value == entity_type]
        
        # Find entities with no links
        entities_to_delete = []
        entities_with_links = []
        
        for entity in all_entities:
            # Check if entity has any links (incoming or outgoing)
            links = repositories.link.get_links_for_entity(str(interaction.guild.id), entity.id)
            
            if not links:
                entities_to_delete.append(entity)
            else:
                entities_with_links.append(entity)
        
        if not entities_to_delete:
            filter_text = f" of type '{entity_type}'" if entity_type else ""
            await interaction.followup.send(
                f"✅ No entities{filter_text} found without links. Nothing to delete.",
                ephemeral=True
            )
            return
        
        # Show confirmation with detailed information
        view = ConfirmDeleteAllView(entities_to_delete, entity_type)
        
        # Create summary embed
        embed = discord.Embed(
            title="⚠️ Bulk Entity Deletion",
            color=discord.Color.red(),
            description=f"Found **{len(entities_to_delete)}** entities without links that will be deleted."
        )
        
        # Group entities by type for display
        by_type = {}
        for entity in entities_to_delete:
            type_name = entity.entity_type.value
            if type_name not in by_type:
                by_type[type_name] = []
            by_type[type_name].append(entity.name)
        
        # Add fields for each type (limit to prevent embed size issues)
        for type_name, entity_names in by_type.items():
            display_names = entity_names[:10]  # Show first 10
            if len(entity_names) > 10:
                display_names.append(f"... and {len(entity_names) - 10} more")
            
            embed.add_field(
                name=f"{type_name.title()} ({len(entity_names)})",
                value="\n".join([f"• {name}" for name in display_names]),
                inline=True
            )
        
        if entities_with_links:
            embed.add_field(
                name="ℹ️ Entities Preserved",
                value=f"{len(entities_with_links)} entities with links will be preserved",
                inline=False
            )
        
        embed.set_footer(text="This action cannot be undone. Click Confirm to proceed.")
        
        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )


class ConfirmDeleteAllView(discord.ui.View):
    """Confirmation view for bulk entity deletion"""
    def __init__(self, entities_to_delete: List[BaseEntity], entity_type: str = None):
        super().__init__(timeout=60)
        self.entities_to_delete = entities_to_delete
        self.entity_type = entity_type

    @discord.ui.button(label="Confirm Delete All", style=discord.ButtonStyle.danger)
    async def confirm_delete_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Execute the bulk deletion"""
        await interaction.response.defer()
        
        deleted_count = 0
        failed_deletions = []
        
        # Delete each entity
        for entity in self.entities_to_delete:
            try:
                repositories.entity.delete_entity(str(interaction.guild.id), entity.id)
                deleted_count += 1
            except Exception as e:
                failed_deletions.append(f"{entity.name}: {str(e)}")
        
        # Create result message
        filter_text = f" of type '{self.entity_type}'" if self.entity_type else ""
        success_msg = f"✅ Successfully deleted **{deleted_count}** entities{filter_text} without links."
        
        if failed_deletions:
            error_msg = "\n\n❌ **Failed to delete:**\n" + "\n".join(failed_deletions[:5])
            if len(failed_deletions) > 5:
                error_msg += f"\n... and {len(failed_deletions) - 5} more errors"
            success_msg += error_msg
        
        # Create summary embed
        embed = discord.Embed(
            title="🗑️ Bulk Deletion Complete",
            description=success_msg,
            color=discord.Color.green() if not failed_deletions else discord.Color.orange()
        )
        
        if deleted_count > 0:
            embed.add_field(
                name="Deleted",
                value=f"{deleted_count} entities",
                inline=True
            )
        
        if failed_deletions:
            embed.add_field(
                name="Failed",
                value=f"{len(failed_deletions)} entities",
                inline=True
            )
        
        await interaction.edit_original_response(
            embed=embed,
            view=None
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_delete_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the bulk deletion"""
        embed = discord.Embed(
            title="❌ Bulk Deletion Cancelled",
            description="No entities were deleted.",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

class ConfirmDeleteEntityView(discord.ui.View):
    def __init__(self, entity: BaseEntity, transfer_inventory: bool = False):
        super().__init__(timeout=60)
        self.entity = entity
        self.transfer_inventory = transfer_inventory

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.transfer_inventory:
            # Remove all POSSESSES links for this entity
            possessed_entities = repositories.link.get_children(
                str(interaction.guild.id),
                self.entity.id,
                EntityLinkType.POSSESSES.value
            )
            
            for possessed_entity in possessed_entities:
                repositories.link.delete_links_by_entities(
                    str(interaction.guild.id),
                    self.entity.id,
                    possessed_entity.id,
                    EntityLinkType.POSSESSES.value
                )
        
        # Delete the entity (this will also delete all remaining links)
        repositories.entity.delete_entity(str(interaction.guild.id), self.entity.id)
        
        delete_msg = f"✅ Deleted entity `{self.entity.name}`."
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

async def setup_entity_commands(bot: commands.Bot):
    await bot.add_cog(EntityCommands(bot))