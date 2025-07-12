import discord
from discord.ext import commands
from discord import app_commands
from data.repositories.repository_factory import repositories
from core.base_models import AccessType, EntityLinkType, EntityType
from core.base_models import BaseEntity
from typing import Optional, List
from .entity_commands import entity_autocomplete

async def _transfer_requires_public_access(new_owner: BaseEntity, guild_id: str) -> bool:
    parent_entities = new_owner.get_parents(guild_id)
    # If any controlling entities' owner is not a gm, set access to public
    if parent_entities:
        for parent in parent_entities:
            if not await repositories.server.has_gm_permission(guild_id, parent.owner_id) or parent.access_type == AccessType.PUBLIC:
                requires_public = True
                break
    if not requires_public:
        requires_public = await repositories.server.has_gm_permission(guild_id, new_owner.owner_id)

    return requires_public

async def link_type_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for link types"""
    link_types = EntityLinkType.get_all_dict()
    
    # Filter based on current input
    if current:
        filtered_types = {name: value for name, value in link_types.items() if current.lower() in name.lower()}
    else:
        filtered_types = link_types
    
    return [
        app_commands.Choice(name=name, value=value.value)
        for name, value in filtered_types.items()
    ]

class LinkCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Create the link command group
    link_group = app_commands.Group(name="link", description="Manage links between entities")

    @link_group.command(name="create", description="Create a link between two entities")
    @app_commands.describe(
        from_entity="The entity that has the link",
        link_type="Type of link",
        to_entity="The entity that is the target of the link", 
        description="Optional description of the link"
    )
    @app_commands.autocomplete(from_entity=entity_autocomplete)
    @app_commands.autocomplete(link_type=link_type_autocomplete)
    @app_commands.autocomplete(to_entity=entity_autocomplete)
    async def create_link(self, interaction: discord.Interaction, from_entity: str, link_type: str, to_entity: str, description: str = None):
        """Create a link between two entities"""
        # Check GM permissions for certain link types
        if link_type in [EntityLinkType.POSSESSES.value, EntityLinkType.CONTROLS.value]:
            if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
                await interaction.response.send_message("❌ Only GMs can create ownership and control links.", ephemeral=True)
                return
        
        # Get the entities - try both character and entity repositories
        from_char = self._find_entity_by_name(interaction.guild.id, from_entity)
        to_char = self._find_entity_by_name(interaction.guild.id, to_entity)
        
        if not from_char:
            await interaction.response.send_message(f"❌ Entity '{from_entity}' not found.", ephemeral=True)
            return
        
        if not to_char:
            await interaction.response.send_message(f"❌ Entity '{to_entity}' not found.", ephemeral=True)
            return
        
        # Check if link already exists
        existing = repositories.link.get_link_by_entities(
            str(interaction.guild.id), from_char.id, to_char.id, link_type
        )
        
        if existing:
            await interaction.response.send_message(f"❌ Link already exists between {from_entity} and {to_entity}.", ephemeral=True)
            return
        
        # Create the link
        metadata = {"description": description} if description else {}
        link = repositories.link.create_link(
            str(interaction.guild.id),
            from_char.id,
            to_char.id,
            link_type,
            metadata
        )
        
        link_name = link_type.replace("_", " ").title()
        await interaction.response.send_message(
            f"✅ Created link: **{from_entity}** {link_name.lower()} **{to_entity}**", 
            ephemeral=True
        )

    @link_group.command(name="remove", description="Remove a link between two entities")
    @app_commands.describe(
        from_entity="The entity that has the link",
        to_entity="The entity that is the target of the link",
        link_type="Type of link to remove (leave blank to remove all)"
    )
    @app_commands.autocomplete(from_entity=entity_autocomplete)
    @app_commands.autocomplete(to_entity=entity_autocomplete)
    @app_commands.autocomplete(link_type=link_type_autocomplete)
    async def remove_link(self, interaction: discord.Interaction, from_entity: str, to_entity: str, link_type: str = None):
        """Remove a link between two entities"""
        
        # Get the entities - try both character and entity repositories
        from_entity = self._find_entity_by_name(interaction.guild.id, from_entity)
        to_entity = self._find_entity_by_name(interaction.guild.id, to_entity)
        
        if not from_entity or not to_entity:
            await interaction.response.send_message("❌ One or both entities not found.", ephemeral=True)
            return
        
        # Check permissions for certain link types
        if link_type in [EntityLinkType.POSSESSES.value, EntityLinkType.CONTROLS.value]:
            if from_entity.owner_id != interaction.user.id and not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
                await interaction.response.send_message("❌ Only owners or GMs can remove ownership and control links.", ephemeral=True)
                return
        
        # Remove the link
        success = repositories.link.delete_links_by_entities(
            str(interaction.guild.id), from_entity.id, to_entity.id, link_type
        )
        
        if success:
            if link_type:
                link_name = link_type.replace("_", " ").title()
                await interaction.response.send_message(
                    f"✅ Removed {link_name.lower()} link between **{from_entity.name}** and **{to_entity.name}**", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Removed all links between **{from_entity.name}** and **{to_entity.name}**", 
                    ephemeral=True
                )
        else:
            await interaction.response.send_message("❌ No link found to remove.", ephemeral=True)

    @link_group.command(name="remove-all", description="Remove all links to and from an entity")
    @app_commands.describe(entity_name="The entity to remove all links for")
    @app_commands.autocomplete(entity_name=entity_autocomplete)
    async def remove_all_links(self, interaction: discord.Interaction, entity_name: str):
        """Remove all links involving an entity"""
        # Get the entity
        entity = self._find_entity_by_name(interaction.guild.id, entity_name)
        if not entity:
            await interaction.response.send_message(f"❌ Entity '{entity_name}' not found.", ephemeral=True)
            return
        
        # Check permissions - only GMs or entity owners can remove all links
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not is_gm and entity.entity_type == EntityType.PC and entity.owner_id != str(interaction.user.id):
            await interaction.response.send_message("❌ You can only remove links for PCs you own.", ephemeral=True)
            return
        elif not is_gm and entity.entity_type != EntityType.PC:
            await interaction.response.send_message("❌ Only GMs can remove links for non-PC entities.", ephemeral=True)
            return
        
        # Get all links involving this entity
        all_links = repositories.link.get_links_for_entity(str(interaction.guild.id), entity.id)
        
        if not all_links:
            await interaction.response.send_message(f"**{entity_name}** has no links to remove.", ephemeral=True)
            return
        
        # Show confirmation with link details
        view = ConfirmRemoveAllLinksView(entity, all_links)
        
        embed = discord.Embed(
            title=f"⚠️ Remove All Links for {entity_name}",
            description=f"This will remove **{len(all_links)}** links involving this entity.",
            color=discord.Color.orange()
        )
        
        # Group links by type for display
        link_summary = {}
        for link in all_links:
            link_type = link.link_type.replace("_", " ").title()
            if link_type not in link_summary:
                link_summary[link_type] = 0
            link_summary[link_type] += 1
        
        summary_text = "\n".join([f"• {count}x {link_type}" for link_type, count in link_summary.items()])
        embed.add_field(name="Links to Remove", value=summary_text, inline=False)
        
        embed.set_footer(text="This action cannot be undone. Click Confirm to proceed.")
        
        await interaction.response.send_message(
            embed=embed,
            view=view,
            ephemeral=True
        )

    @link_group.command(name="list", description="List all links for an entity")
    @app_commands.describe(entity_name="The entity to show links for")
    @app_commands.autocomplete(entity_name=entity_autocomplete)
    async def list_links(self, interaction: discord.Interaction, entity_name: str):
        """List all links for an entity"""
        # Get the entity - try both character and entity repositories
        entity = self._find_entity_by_name(interaction.guild.id, entity_name)
        if not entity:
            await interaction.response.send_message(f"❌ Entity '{entity_name}' not found.", ephemeral=True)
            return
        
        # Get all links involving this entity using the view
        entity_details = repositories.entity_details.get_by_id(entity.id)
        
        if not entity_details:
             await interaction.response.send_message(f"**{entity_name}** has no links.", ephemeral=True)
             return

        embed = discord.Embed(
            title=f"🔗 Links for {entity_name}",
            color=discord.Color.blue()
        )
        
        outgoing_links = []
        incoming_links = []

        # Add pre-aggregated links from the view
        if entity_details.possessed_items:
            outgoing_links.extend([f"• **Possesses** {entity['name']}" for entity in entity_details.possessed_items])
        if entity_details.controls:
            outgoing_links.extend([f"• **Controls** {entity['name']}" for entity in entity_details.controls])
        if entity_details.possessed_by:
            incoming_links.extend([f"• **{entity['name']}** possesses this entity" for entity in entity_details.possessed_by])
        if entity_details.controlled_by:
            incoming_links.extend([f"• **{entity['name']}** controls this entity" for entity in entity_details.controlled_by])
        
        if not outgoing_links and not incoming_links:
            await interaction.response.send_message(f"**{entity_name}** has no links.", ephemeral=True)
            return

        if outgoing_links:
            embed.add_field(
                name="Links To Others",
                value="\n".join(outgoing_links),
                inline=False
            )
        
        if incoming_links:
            embed.add_field(
                name="Links From Others", 
                value="\n".join(incoming_links),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @link_group.command(name="transfer", description="Transfer possession of an entity to another entity")
    @app_commands.describe(
        possessed_entity="The entity to transfer possession of",
        new_owner="The entity that will become the new owner",
        quantity="Quantity to transfer (for items only, leave blank for all)"
    )
    @app_commands.autocomplete(possessed_entity=entity_autocomplete)
    @app_commands.autocomplete(new_owner=entity_autocomplete)
    async def transfer_possession(self, interaction: discord.Interaction, possessed_entity: str, new_owner: str, quantity: int = None):
        """Transfer possession of an entity to another entity (GM only)"""
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can transfer possession.", ephemeral=True)
            return
        
        # Get the entities
        possessed = self._find_entity_by_name(interaction.guild.id, possessed_entity)
        new_possessor = self._find_entity_by_name(interaction.guild.id, new_owner)
        
        if not possessed or not new_possessor:
            await interaction.response.send_message("❌ One or both entities not found.", ephemeral=True)
            return
        
        # Handle item transfers with quantity
        if possessed.entity_type == EntityType.ITEM:
            await self._transfer_item_with_quantity(interaction, possessed, new_possessor, quantity)
        else:
            # Handle non-item transfers (existing logic)
            await self._transfer_entity_ownership(interaction, possessed, new_possessor)

    async def _transfer_item_with_quantity(self, interaction: discord.Interaction, item: BaseEntity, new_owner: BaseEntity, quantity: int = None):
        """Handle item transfers with quantity support"""
        guild_id = str(interaction.guild.id)
        
        # Find current owners and their quantities
        current_possessors = repositories.link.get_parents(guild_id, item.id, EntityLinkType.POSSESSES.value)
        
        if not current_possessors:
            await interaction.response.send_message(f"❌ {item.name} is not currently possessed by anyone.", ephemeral=True)
            return
        
        # For simplicity, handle single possessor case first
        if len(current_possessors) > 1:
            await interaction.response.send_message(f"❌ {item.name} has multiple possessors. Please specify which one to transfer from.", ephemeral=True)
            return
        
        current_owner = current_possessors[0]
        current_links = current_owner.get_links_to_entity(guild_id, item.id, EntityLinkType.POSSESSES)
        current_quantity = current_links[0].metadata.get("quantity", 1) if current_links else 1
        
        # Determine transfer quantity
        transfer_quantity = quantity if quantity is not None else current_quantity
        
        if transfer_quantity <= 0:
            await interaction.response.send_message("❌ Transfer quantity must be positive.", ephemeral=True)
            return
        
        if transfer_quantity > current_quantity:
            await interaction.response.send_message(
                f"❌ {current_owner.name} only has {current_quantity}x {item.name}. Cannot transfer {transfer_quantity}.",
                ephemeral=True
            )
            return
        
        # Remove from current owner
        current_owner.remove_item(guild_id, item, transfer_quantity)
        
        # Add to new owner
        new_owner.add_item(guild_id, item, transfer_quantity)
        
        # Save both entities
        repositories.entity.upsert_entity(interaction.guild.id, current_owner, system=current_owner.system)
        repositories.entity.upsert_entity(interaction.guild.id, new_owner, system=new_owner.system)
        
        await interaction.response.send_message(
            f"✅ Transferred {transfer_quantity}x **{item.name}** from **{current_owner.name}** to **{new_owner.name}**",
            ephemeral=True
        )

    async def _transfer_entity_ownership(self, interaction: discord.Interaction, entity: BaseEntity, new_owner: BaseEntity):
        """Handle non-item entity transfers (existing logic)"""
        guild_id = str(interaction.guild.id)
        
        # Remove existing ownership links
        existing_possessors = repositories.link.get_parents(guild_id, entity.id, EntityLinkType.POSSESSES.value)
        for possessor in existing_possessors:
            repositories.link.delete_links_by_entities(
                guild_id, possessor.id, entity.id, EntityLinkType.POSSESSES.value
            )
        
        # Create new ownership link
        repositories.link.create_link(
            guild_id,
            new_owner.id,
            entity.id,
            EntityLinkType.POSSESSES.value,
            {"transferred_by": str(interaction.user.id)}
        )
        
        # Set access to public if transferring to a player character or companion
        if await _transfer_requires_public_access(new_owner, guild_id):
            entity.set_access_type(AccessType.PUBLIC)
            system = repositories.server.get_system(guild_id)
            repositories.entity.upsert_entity(guild_id, entity, system)
            
            await interaction.response.send_message(
                f"✅ **{new_owner.name}** now possesses **{entity.name}** and entity access set to public",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"✅ **{new_owner.name}** now possesses **{entity.name}**",
                ephemeral=True
            )

    def _find_entity_by_name(self, guild_id: str, entity_name: str) -> Optional[BaseEntity]:
        """Helper method to find an entity by name in both character and entity repositories"""
        entity = repositories.entity.get_by_name(str(guild_id), entity_name)
        return entity

    def _find_entity_by_id(self, entity_id: str) -> Optional[BaseEntity]:
        """Helper method to find an entity by ID in both character and entity repositories"""
        entity = repositories.entity.get_by_id(entity_id)
        return entity

class ConfirmRemoveAllLinksView(discord.ui.View):
    """Confirmation view for removing all links from an entity"""
    def __init__(self, entity: BaseEntity, links_to_remove: List):
        super().__init__(timeout=60)
        self.entity = entity
        self.links_to_remove = links_to_remove

    @discord.ui.button(label="Confirm Remove All", style=discord.ButtonStyle.danger)
    async def confirm_remove_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Execute the link removal"""
        await interaction.response.defer()
        
        removed_count = 0
        failed_removals = []
        
        # Remove each link
        for link in self.links_to_remove:
            try:
                repositories.link.delete_link(link.id)
                removed_count += 1
            except Exception as e:
                failed_removals.append(f"{link.link_type}: {str(e)}")
        
        # Create result message
        success_msg = f"✅ Successfully removed **{removed_count}** links from **{self.entity.name}**."
        
        if failed_removals:
            error_msg = "\n\n❌ **Failed to remove:**\n" + "\n".join(failed_removals[:3])
            if len(failed_removals) > 3:
                error_msg += f"\n... and {len(failed_removals) - 3} more errors"
            success_msg += error_msg
        
        # Create summary embed
        embed = discord.Embed(
            title="🔗 Link Removal Complete",
            description=success_msg,
            color=discord.Color.green() if not failed_removals else discord.Color.orange()
        )
        
        if removed_count > 0:
            embed.add_field(
                name="Removed",
                value=f"{removed_count} links",
                inline=True
            )
        
        if failed_removals:
            embed.add_field(
                name="Failed",
                value=f"{len(failed_removals)} links",
                inline=True
            )
        
        await interaction.edit_original_response(
            embed=embed,
            view=None
        )

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_remove_all(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Cancel the link removal"""
        embed = discord.Embed(
            title="❌ Link Removal Cancelled",
            description="No links were removed.",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(
            embed=embed,
            view=None
        )

async def setup_link_commands(bot: commands.Bot):
    await bot.add_cog(LinkCommands(bot))