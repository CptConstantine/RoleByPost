import discord
from discord import app_commands
from discord.ext import commands
from typing import List
from commands.autocomplete import accessible_entities_autocomplete, entity_type_autocomplete, top_level_entities_autocomplete
from core.base_models import AccessType, BaseEntity, EntityType, EntityLinkType
from core.command_decorators import gm_role_required, no_ic_channels, player_or_gm_role_required
from core.shared_views import ConfirmDialogV2
from data.repositories.repository_factory import repositories
import core.factories as factories

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
    @player_or_gm_role_required()
    @no_ic_channels()
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
            await interaction.followup.send(f"❌ Invalid entity type '{entity_type}' for {system.value.upper()} system.", ephemeral=True)
            return
        
        e_type = EntityType(entity_type)
        
        # Check if entity with this name already exists
        existing = repositories.entity.get_by_name(str(interaction.guild.id), name)
        if existing:
            await interaction.followup.send(f"❌ An entity named `{name}` already exists.", ephemeral=True)
            return
        
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Create the entity using the new factory method
        entity = factories.build_and_save_entity(
            system=system,
            entity_type=e_type,
            name=name,
            owner_id=str(interaction.user.id),
            guild_id=str(interaction.guild.id),
            access_type=AccessType.GM_ONLY if is_gm else AccessType.PUBLIC
        )
        
        await interaction.followup.send(f"✅ Created {entity_type}: **{name}**", ephemeral=True)

    @entity_group.command(name="delete", description="Delete an entity")
    @app_commands.describe(
        entity_name="Name of the entity to delete",
        transfer_inventory="If true, releases possessed items instead of blocking deletion"
    )
    @app_commands.autocomplete(entity_name=accessible_entities_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
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
        
        confirmation_msg = f"⚠️ Are you sure you want to delete `{entity_name}` ({entity.entity_type.value})?\n"
        
        if possessed_entities and transfer_inventory:
            entity_names = [entity.name for entity in possessed_entities]
            confirmation_msg += f"\n**This will also release the following possessed items:**\n{', '.join(entity_names)}\n"
        
        confirmation_msg += "\nThis action cannot be undone."
        
        # Components v2 confirmation dialog
        view = ConfirmDeleteEntityViewV2(entity, transfer_inventory, confirmation_msg)
        await interaction.response.send_message(view=view, ephemeral=True)

    @entity_group.command(name="list", description="List entities")
    @app_commands.describe(
        owner_entity="Entity to list owned entities of (leave empty for top-level)",
        entity_type="Filter by entity type",
        show_details="Show additional details (access level, ownership info)"
    )
    @app_commands.autocomplete(
        owner_entity=top_level_entities_autocomplete,
        entity_type=entity_type_autocomplete
    )
    @player_or_gm_role_required()
    @no_ic_channels()
    async def entity_list(
        self, 
        interaction: discord.Interaction, 
        owner_entity: str = None, 
        entity_type: str = None,
        show_details: bool = False
    ):
        """List entities with optional filtering"""
        await interaction.response.defer(ephemeral=True)
        
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Get accessible entities based on user permissions
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
            # Get accessible entities for this user
            entities = repositories.entity.get_all_accessible(
                str(interaction.guild.id), 
                str(interaction.user.id), 
                is_gm
            )
            
            # Filter to only entities that are not owned by other entities
            top_level_entities = []
            for entity in entities:
                owners = repositories.link.get_parents(
                    str(interaction.guild.id), 
                    entity.id, 
                    EntityLinkType.POSSESSES.value
                )
                if not owners:  # No owners = top-level
                    top_level_entities.append(entity)
            
            entities = top_level_entities
            title = "Accessible top-level entities"
            
            if entity_type:
                # Apply entity type filter
                entities = [e for e in entities if e.entity_type.value == entity_type]
                title += f" ({entity_type})"
        
        if not entities:
            await interaction.followup.send("No entities found.", ephemeral=True)
            return
        
        # Create embed
        embed = discord.Embed(title=title, color=discord.Color.blue())
        embed.set_footer(text="🌐 = Public, 🔒 = GM Only")
        
        # Group by entity type for display
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
                # Always show access level indicator
                access_indicator = "🔒" if entity.access_type == AccessType.GM_ONLY else "🌐"
                entry = f"• {entity.name} {access_indicator}"
                
                if show_details:
                    # Add ownership info for GMs or for user's own entities
                    if is_gm and entity.owner_id:
                        entry += f" (owned by <@{entity.owner_id}>)"
                    elif not is_gm and entity.entity_type == EntityType.PC and entity.owner_id == str(interaction.user.id):
                        entry += " (your PC)"
                
                # Show possessed entities count if any
                possessed_entities = repositories.link.get_children(
                    str(interaction.guild.id), 
                    entity.id, 
                    EntityLinkType.POSSESSES.value
                )
                if possessed_entities:
                    entry += f" ({len(possessed_entities)} possessed)"
                
                entity_list.append(entry)
            
            field_value = "\n".join(entity_list)[:1024]  # Discord field limit
            
            embed.add_field(
                name=f"{type_name.title()} ({len(type_entities)})",
                value=field_value,
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @entity_group.command(name="view", description="View entity details with edit interface")
    @app_commands.describe(
        entity_name="Name of the entity to view",
        show_links="Show detailed link information"
    )
    @app_commands.autocomplete(entity_name=accessible_entities_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
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
        sheet_view = entity.get_sheet_edit_view(interaction.user.id, is_gm=is_gm, guild_id=str(interaction.guild.id))
        
        if isinstance(sheet_view, discord.ui.LayoutView):
            await interaction.response.send_message(view=sheet_view, ephemeral=True)
        else:
            # V1 fallback: format embed externally
            embed = entity.format_full_sheet(str(interaction.guild.id), is_gm=is_gm)
            
            # Add link information if requested
            if show_links:
                link_info = EntityLinkType.get_links_str(str(interaction.guild.id), entity)
                if link_info:
                    embed.add_field(name="\U0001F517 Links", value="\n".join(link_info), inline=False)

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
    @app_commands.autocomplete(entity_name=accessible_entities_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
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

    @entity_group.command(name="delete-all", description="Delete all entities with no links (GM only)")
    @app_commands.describe(
        entity_type="Filter by entity type (optional)",
        confirm="Type 'DELETE' to confirm this destructive action"
    )
    @app_commands.autocomplete(entity_type=entity_type_autocomplete)
    @gm_role_required()
    @no_ic_channels()
    async def entity_delete_all(
        self, 
        interaction: discord.Interaction, 
        confirm: str,
        entity_type: str = None
    ):
        """Delete all entities with no links - GM only command"""
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
        
        # Show confirmation with detailed information (Components v2)
        view = ConfirmDeleteAllViewV2(entities_to_delete, entity_type, preserved_count=len(entities_with_links))
        await interaction.followup.send(view=view, ephemeral=True)

    @entity_group.command(name="set-access", description="Set access level for an entity and its possessed entities")
    @app_commands.describe(
        entity_name="Name of the entity",
        access_type="Access level (public or gm_only)"
    )
    @app_commands.autocomplete(entity_name=accessible_entities_autocomplete)
    @app_commands.choices(access_type=[
        app_commands.Choice(name="Public", value="public"),
        app_commands.Choice(name="GM Only", value="gm_only")
    ])
    @player_or_gm_role_required()
    @no_ic_channels()
    async def entity_set_access(
        self, 
        interaction: discord.Interaction, 
        entity_name: str, 
        access_type: str
    ):
        """Set access level for an entity and all its possessed entities"""
        entity = repositories.entity.get_by_name(str(interaction.guild.id), entity_name)
        if not entity:
            await interaction.response.send_message(f"❌ Entity `{entity_name}` not found.", ephemeral=True)
            return
        
        # Check permissions - only GMs and PC owners can change access
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm and entity.entity_type == EntityType.PC and entity.owner_id != str(interaction.user.id):
            await interaction.response.send_message("❌ You can only change access for PCs you own.", ephemeral=True)
            return
        elif not is_gm and entity.entity_type != EntityType.PC:
            await interaction.response.send_message("❌ Only GMs can change access for non-PC entities.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Validate and set access type
        try:
            new_access_type = AccessType(access_type)
        except ValueError:
            await interaction.followup.send(f"❌ Invalid access type. Must be 'public' or 'gm_only'.", ephemeral=True)
            return
        
        # Get all possessed entities recursively
        def get_all_possessed_recursively(entity_id: str, visited: set = None) -> List[BaseEntity]:
            """Recursively get all possessed entities to avoid infinite loops"""
            if visited is None:
                visited = set()
            
            if entity_id in visited:
                return []
            
            visited.add(entity_id)
            possessed = repositories.link.get_children(
                str(interaction.guild.id), 
                entity_id, 
                EntityLinkType.POSSESSES.value
            )
            
            all_possessed = possessed.copy()
            for child in possessed:
                all_possessed.extend(get_all_possessed_recursively(child.id, visited))
            
            return all_possessed
        
        # Set access for the main entity
        entity.set_access_type(new_access_type)
        system = repositories.server.get_system(str(interaction.guild.id))
        repositories.entity.upsert_entity(str(interaction.guild.id), entity, system=system)
        
        # Get all possessed entities
        all_possessed = get_all_possessed_recursively(entity.id)
        
        # Set access for all possessed entities
        updated_count = 1  # Count the main entity
        failed_updates = []
        
        for possessed_entity in all_possessed:
            try:
                possessed_entity.set_access_type(new_access_type)
                repositories.entity.upsert_entity(str(interaction.guild.id), possessed_entity, system=system)
                updated_count += 1
            except Exception as e:
                failed_updates.append(f"{possessed_entity.name}: {str(e)}")
        
        # Create response message
        access_display = "Public" if new_access_type.value == "public" else "GM Only"
        success_msg = f"✅ Set access level for **{entity_name}** to **{access_display}**."
        
        if len(all_possessed) > 0:
            success_msg += f"\n\nAlso updated {len(all_possessed)} possessed entities:"
            
            # Group possessed entities by type for display
            by_type = {}
            for possessed in all_possessed:
                type_name = possessed.entity_type.value
                if type_name not in by_type:
                    by_type[type_name] = []
                by_type[type_name].append(possessed.name)
            
            type_summary = []
            for type_name, names in by_type.items():
                if len(names) <= 3:
                    type_summary.append(f"• {type_name}: {', '.join(names)}")
                else:
                    type_summary.append(f"• {type_name}: {', '.join(names[:3])} (+{len(names)-3} more)")
            
            success_msg += "\n" + "\n".join(type_summary)
        
        if failed_updates:
            error_msg = f"\n\n❌ **Failed to update {len(failed_updates)} entities:**\n"
            error_msg += "\n".join(failed_updates[:3])
            if len(failed_updates) > 3:
                error_msg += f"\n... and {len(failed_updates) - 3} more errors"
            success_msg += error_msg
        
        # Create embed for better formatting
        embed = discord.Embed(
            title="🔐 Access Level Updated",
            description=success_msg,
            color=discord.Color.green() if not failed_updates else discord.Color.orange()
        )
        
        embed.add_field(
            name="New Access Level",
            value=f"**{access_display}**",
            inline=True
        )
        
        embed.add_field(
            name="Entities Updated",
            value=f"{updated_count} total",
            inline=True
        )
        
        if failed_updates:
            embed.add_field(
                name="Failed Updates",
                value=f"{len(failed_updates)} entities",
                inline=True
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

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


class ConfirmDeleteAllViewV2(ConfirmDialogV2):
    """Components v2 confirmation dialog for bulk entity deletion."""

    def __init__(self, entities_to_delete: List[BaseEntity], entity_type: str = None, preserved_count: int = 0):
        self.entities_to_delete = entities_to_delete
        self.entity_type = entity_type

        # Build the detailed warning text (replaces the embed from V1 call site)
        filter_text = f" of type '{entity_type}'" if entity_type else ""
        lines = [
            f"## ⚠️ Bulk Entity Deletion",
            f"Found **{len(entities_to_delete)}** entities{filter_text} without links that will be deleted.\n",
        ]

        # Group by type
        by_type: dict[str, list[str]] = {}
        for entity in entities_to_delete:
            by_type.setdefault(entity.entity_type.value, []).append(entity.name)

        for type_name, names in by_type.items():
            display = names[:10]
            if len(names) > 10:
                display.append(f"... and {len(names) - 10} more")
            lines.append(f"**{type_name.title()} ({len(names)}):**")
            lines.extend(f"• {n}" for n in display)
            lines.append("")

        if preserved_count > 0:
            lines.append(f"ℹ️ {preserved_count} entities with links will be preserved.\n")

        lines.append("*This action cannot be undone.*")

        super().__init__(
            message="\n".join(lines),
            confirm_label="Confirm Delete All",
        )

    async def on_confirm(self, interaction: discord.Interaction):
        await interaction.response.defer()

        deleted_count = 0
        failed_deletions = []

        for entity in self.entities_to_delete:
            try:
                repositories.entity.delete_entity(str(interaction.guild.id), entity.id)
                deleted_count += 1
            except Exception as e:
                failed_deletions.append(f"{entity.name}: {str(e)}")

        filter_text = f" of type '{self.entity_type}'" if self.entity_type else ""
        success_msg = f"✅ Successfully deleted **{deleted_count}** entities{filter_text} without links."

        if failed_deletions:
            error_msg = "\n\n❌ **Failed to delete:**\n" + "\n".join(failed_deletions[:5])
            if len(failed_deletions) > 5:
                error_msg += f"\n... and {len(failed_deletions) - 5} more errors"
            success_msg += error_msg

        embed = discord.Embed(
            title="🗑️ Bulk Deletion Complete",
            description=success_msg,
            color=discord.Color.green() if not failed_deletions else discord.Color.orange()
        )
        if deleted_count > 0:
            embed.add_field(name="Deleted", value=f"{deleted_count} entities", inline=True)
        if failed_deletions:
            embed.add_field(name="Failed", value=f"{len(failed_deletions)} entities", inline=True)

        await interaction.edit_original_response(embed=embed, view=None)

    async def on_cancel(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="❌ Bulk Deletion Cancelled",
            description="No entities were deleted.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=None)


class ConfirmDeleteEntityViewV2(ConfirmDialogV2):
    """Components v2 confirmation dialog for single entity deletion."""

    def __init__(self, entity: BaseEntity, transfer_inventory: bool = False, confirmation_msg: str = ""):
        self.entity = entity
        self.transfer_inventory = transfer_inventory
        super().__init__(
            message=confirmation_msg,
            confirm_label="Delete",
        )

    async def on_confirm(self, interaction: discord.Interaction):
        if self.transfer_inventory:
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

        repositories.entity.delete_entity(str(interaction.guild.id), self.entity.id)

        delete_msg = f"✅ Deleted entity `{self.entity.name}`."
        if self.transfer_inventory:
            delete_msg += " Released all possessed items."

        await interaction.response.edit_message(content=delete_msg, view=None)

    async def on_cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="❌ Deletion cancelled.", view=None)


async def setup_entity_commands(bot: commands.Bot):
    await bot.add_cog(EntityCommands(bot))