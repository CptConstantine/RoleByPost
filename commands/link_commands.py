import discord
from discord.ext import commands
from discord import app_commands
from data.repositories.repository_factory import repositories
from core.base_models import EntityLinkType
from core.base_models import BaseEntity
from typing import Optional, List
import core.factories as factories

class EntityLinkCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def entity_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for any entity name - shows all entities if GM, owned entities if not GM"""
        if not interaction.guild:
            return []
        
        # Check if user is GM
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if is_gm:
            # GMs can see all entities (both characters and other entities)
            all_entities = repositories.entity.get_all_by_guild(str(interaction.guild.id))
        else:
            # Users can only see entities they own
            all_entities = repositories.entity.get_all_by_owner(str(interaction.guild.id), str(interaction.user.id))
        
        # Filter based on current input
        if current:
            all_entities = [entity for entity in all_entities if current.lower() in entity.name.lower()]
        
        # Format the choices with entity type for clarity
        choices = []
        for entity in all_entities[:25]:  # Limit to 25 results
            entity_type = entity.entity_type.value.upper()
            choices.append(
                app_commands.Choice(name=f"{entity.name} ({entity_type})", value=entity.name)
            )
        
        return choices

    async def link_type_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
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

    # Create the link command group
    link_group = app_commands.Group(name="link", description="Manage links between entities")

    @link_group.command(name="create", description="Create a link between two entities")
    @app_commands.describe(
        from_entity="The entity that has the link",
        to_entity="The entity that is the target of the link", 
        link_type="Type of link",
        description="Optional description of the link"
    )
    @app_commands.autocomplete(from_entity=entity_autocomplete)
    @app_commands.autocomplete(to_entity=entity_autocomplete)
    @app_commands.autocomplete(link_type=link_type_autocomplete)
    async def create_link(self, interaction: discord.Interaction, from_entity: str, to_entity: str, link_type: str, description: str = None):
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
        
        # Get all links involving this entity
        links = repositories.link.get_links_for_entity(str(interaction.guild.id), entity.id)
        
        if not links:
            await interaction.response.send_message(f"**{entity_name}** has no links.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🔗 Links for {entity_name}",
            color=discord.Color.blue()
        )
        
        outgoing_links = []
        incoming_links = []
        
        for rel in links:
            if rel.from_entity_id == entity.id:
                # This entity has a link TO another entity
                target_entity = self._find_entity_by_id(rel.to_entity_id)
                if target_entity:
                    rel_name = rel.link_type.replace("_", " ").title()
                    description = rel.metadata.get("description", "") if rel.metadata else ""
                    line = f"• **{rel_name}** {target_entity.name}"
                    if description:
                        line += f" - *{description}*"
                    outgoing_links.append(line)
            else:
                # Another entity has a link TO this entity
                source_entity = self._find_entity_by_id(rel.from_entity_id)
                if source_entity:
                    rel_name = rel.link_type.replace("_", " ").title()
                    description = rel.metadata.get("description", "") if rel.metadata else ""
                    line = f"• **{source_entity.name}** {rel_name.lower()} this entity"
                    if description:
                        line += f" - *{description}*"
                    incoming_links.append(line)
        
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
        new_owner="The entity that will become the new owner"
    )
    @app_commands.autocomplete(possessed_entity=entity_autocomplete)
    @app_commands.autocomplete(new_owner=entity_autocomplete)
    async def transfer_possession(self, interaction: discord.Interaction, possessed_entity: str, new_owner: str):
        """Transfer possession of an entity to another entity (GM only)"""
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can transfer possession.", ephemeral=True)
            return
        
        # Get the entities - try both character and entity repositories
        owned_char = self._find_entity_by_name(interaction.guild.id, possessed_entity)
        new_owner_char = self._find_entity_by_name(interaction.guild.id, new_owner)
        
        if not owned_char or not new_owner_char:
            await interaction.response.send_message("❌ One or both entities not found.", ephemeral=True)
            return
        
        # Remove existing ownership links
        existing_owners = repositories.link.get_parents(str(interaction.guild.id), owned_char.id, EntityLinkType.POSSESSES.value)
        for owner in existing_owners:
            repositories.link.delete_links_by_entities(
                str(interaction.guild.id), owner.id, owned_char.id, EntityLinkType.POSSESSES.value
            )
        
        # Create new ownership link
        repositories.link.create_link(
            str(interaction.guild.id),
            new_owner_char.id,
            owned_char.id,
            EntityLinkType.POSSESSES.value,
            {"transferred_by": str(interaction.user.id)}
        )
        
        await interaction.response.send_message(
            f"✅ **{new_owner}** now possesses **{possessed_entity}**", 
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

async def setup_link_commands(bot: commands.Bot):
    await bot.add_cog(EntityLinkCommands(bot))