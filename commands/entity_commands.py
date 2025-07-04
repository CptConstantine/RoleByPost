import uuid
import discord
from discord import app_commands
from discord.ext import commands
from typing import List, Optional
from core import channel_restriction
from core.models import BaseEntity, EntityType, RelationshipType
from data.repositories.repository_factory import repositories
import core.factories as factories

# Autocomplete functions
async def entity_type_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for entity types based on current system"""
    system = repositories.server.get_system(str(interaction.guild.id))
    
    # Get available entity types for the current system
    entity_types = []
    if system == "generic":
        entity_types = ["generic"]
    elif system == "fate":
        entity_types = ["generic"]
    elif system == "mgt2e":
        entity_types = ["generic"]
    else:
        entity_types = ["generic"]
    
    # Filter based on user input
    filtered_types = [
        entity_type for entity_type in entity_types 
        if current.lower() in entity_type.lower()
    ]
    
    return [
        app_commands.Choice(name=entity_type.title(), value=entity_type)
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

async def parent_entity_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
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
        name="Name for the new entity",
        parent_entity="Optional: Parent entity that will own this entity"
    )
    @app_commands.autocomplete(
        entity_type=entity_type_autocomplete,
        parent_entity=parent_entity_autocomplete
    )
    @channel_restriction.no_ic_channels()
    async def entity_create(
        self, 
        interaction: discord.Interaction, 
        entity_type: str, 
        name: str,
        parent_entity: str = None
    ):
        """Create a new entity"""
        await interaction.response.defer(ephemeral=True)
        
        system = repositories.server.get_system(str(interaction.guild.id))
        
        # Validate entity type for current system
        valid_types = []
        if system == "generic":
            valid_types = ["generic"]
        elif system == "fate":
            valid_types = ["generic"]
        elif system == "mgt2e":
            valid_types = ["generic"]
        
        if entity_type not in valid_types:
            await interaction.followup.send(f"❌ Invalid entity type '{entity_type}' for {system.upper()} system.", ephemeral=True)
            return
        
        # Check if entity with this name already exists
        existing = repositories.entity.get_by_name(str(interaction.guild.id), name)
        if existing:
            await interaction.followup.send(f"❌ An entity named `{name}` already exists.", ephemeral=True)
            return
        
        # Validate parent entity if specified
        parent = None
        if parent_entity and parent_entity.strip():
            parent = repositories.entity.get_by_name(str(interaction.guild.id), parent_entity)
            if not parent:
                await interaction.followup.send(f"❌ Parent entity `{parent_entity}` not found.", ephemeral=True)
                return
            
            # Check if user can use this entity as a parent
            is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            if not is_gm and str(parent.owner_id) != str(interaction.user.id):
                await interaction.followup.send("❌ You can only create entities under entities you own.", ephemeral=True)
                return
        
        # Create the entity
        entity_id = str(uuid.uuid4())
        EntityClass = factories.get_specific_entity(system, entity_type)
        
        # Map entity type string to EntityType enum
        if entity_type == "generic":
            enum_type = EntityType.GENERIC
        elif entity_type == "extra":
            enum_type = EntityType.GENERIC  # Fate extras use generic type with system-specific handling
        else:
            enum_type = EntityType.GENERIC  # Default for system-specific types
        
        entity_dict = BaseEntity.build_entity_dict(
            id=entity_id,
            name=name,
            owner_id=str(interaction.user.id),
            entity_type=enum_type
        )
        
        entity = EntityClass(entity_dict)
        entity.apply_defaults(entity_type=enum_type, guild_id=str(interaction.guild.id))
        
        # Save the entity first
        repositories.entity.upsert_entity(str(interaction.guild.id), entity, system=system)
        
        # Create ownership relationship if parent specified
        if parent:
            repositories.relationship.create_relationship(
                guild_id=str(interaction.guild.id),
                from_entity_id=parent.id,
                to_entity_id=entity_id,
                relationship_type=RelationshipType.OWNS.value,
                metadata={"created_by": str(interaction.user.id)}
            )
            parent_info = f" owned by **{parent_entity}**"
        else:
            parent_info = ""
        
        await interaction.followup.send(f"✅ Created {entity_type}: **{name}**{parent_info}", ephemeral=True)

    @entity_group.command(name="delete", description="Delete an entity")
    @app_commands.describe(entity_name="Name of the entity to delete")
    @app_commands.autocomplete(entity_name=entity_name_autocomplete)
    @channel_restriction.no_ic_channels()
    async def entity_delete(self, interaction: discord.Interaction, entity_name: str):
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
        
        # Check if entity owns other entities (through relationships)
        owned_entities = repositories.relationship.get_children(
            str(interaction.guild.id), 
            entity.id, 
            RelationshipType.OWNS.value
        )
        
        if owned_entities:
            entity_names = [owned_entity.name for owned_entity in owned_entities]
            await interaction.response.send_message(
                f"❌ Cannot delete `{entity_name}` because it owns other entities: {', '.join(entity_names)}.\n"
                f"Please transfer or delete these entities first, or use `/relationship remove` to remove the ownership relationships.",
                ephemeral=True
            )
            return
        
        view = ConfirmDeleteEntityView(entity)
        await interaction.response.send_message(
            f"⚠️ Are you sure you want to delete `{entity_name}` ({entity.entity_type.value})?\n"
            f"This action cannot be undone.",
            view=view,
            ephemeral=True
        )

    @entity_group.command(name="list", description="List entities")
    @app_commands.describe(
        owner_entity="Entity to list owned entities of (leave empty for top-level)",
        entity_type="Filter by entity type",
        show_relationships="Show ownership relationships"
    )
    @app_commands.autocomplete(
        owner_entity=parent_entity_autocomplete,
        entity_type=entity_type_autocomplete
    )
    @channel_restriction.no_ic_channels()
    async def entity_list(
        self, 
        interaction: discord.Interaction, 
        owner_entity: str = None, 
        entity_type: str = None,
        show_relationships: bool = False
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
            
            entities = repositories.relationship.get_children(
                str(interaction.guild.id), 
                owner.id, 
                RelationshipType.OWNS.value
            )
            title = f"Entities owned by {owner.name}"
        else:
            # List top-level entities (those without owners)
            all_entities = repositories.entity.get_all_by_guild(str(interaction.guild.id))
            
            # Filter to only entities that are not owned by other entities
            entities = []
            for entity in all_entities:
                owners = repositories.relationship.get_parents(
                    str(interaction.guild.id), 
                    entity.id, 
                    RelationshipType.OWNS.value
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
        
        if show_relationships:
            # Show detailed relationship information
            entity_info = []
            for entity in entities:
                # Get owned entities
                owned_entities = repositories.relationship.get_children(
                    str(interaction.guild.id), 
                    entity.id, 
                    RelationshipType.OWNS.value
                )
                
                # Get controlled entities
                controlled_entities = repositories.relationship.get_children(
                    str(interaction.guild.id), 
                    entity.id, 
                    RelationshipType.CONTROLS.value
                )
                
                info = f"**{entity.name}** ({entity.entity_type.value})"
                if owned_entities:
                    owned_names = [e.name for e in owned_entities]
                    info += f"\n  *Owns: {', '.join(owned_names)}*"
                if controlled_entities:
                    controlled_names = [e.name for e in controlled_entities]
                    info += f"\n  *Controls: {', '.join(controlled_names)}*"
                
                entity_info.append(info)
            
            embed.description = "\n\n".join(entity_info)
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
                    # Show owned entities count if any
                    owned_entities = repositories.relationship.get_children(
                        str(interaction.guild.id), 
                        entity.id, 
                        RelationshipType.OWNS.value
                    )
                    owned_info = f" ({len(owned_entities)} owned)" if owned_entities else ""
                    entity_list.append(f"• {entity.name}{owned_info}")
                
                embed.add_field(
                    name=f"{type_name.title()} ({len(type_entities)})",
                    value="\n".join(entity_list)[:1024],  # Discord field limit
                    inline=False
                )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @entity_group.command(name="view", description="View entity details")
    @app_commands.describe(entity_name="Name of the entity to view")
    @app_commands.autocomplete(entity_name=entity_name_autocomplete)
    @channel_restriction.no_ic_channels()
    async def entity_view(self, interaction: discord.Interaction, entity_name: str):
        """View detailed information about an entity"""
        entity = repositories.entity.get_by_name(str(interaction.guild.id), entity_name)
        if not entity:
            await interaction.response.send_message(f"❌ Entity `{entity_name}` not found.", ephemeral=True)
            return
        
        # Create embed with entity details
        embed = discord.Embed(
            title=f"{entity.name}",
            description=f"Type: {entity.entity_type.value}",
            color=discord.Color.green()
        )
        
        # Add basic info
        owner = interaction.guild.get_member(int(entity.owner_id))
        owner_name = owner.display_name if owner else f"User {entity.owner_id}"
        embed.add_field(name="Owner", value=owner_name, inline=True)
        
        # Add relationship information
        # Entities this entity owns
        owned_entities = repositories.relationship.get_children(
            str(interaction.guild.id), 
            entity.id, 
            RelationshipType.OWNS.value
        )
        if owned_entities:
            owned_names = [e.name for e in owned_entities[:5]]  # Show first 5
            owned_text = ", ".join(owned_names)
            if len(owned_entities) > 5:
                owned_text += f" (+{len(owned_entities) - 5} more)"
            embed.add_field(name=f"Owns ({len(owned_entities)})", value=owned_text, inline=False)
        
        # Entities that own this entity
        owners = repositories.relationship.get_parents(
            str(interaction.guild.id), 
            entity.id, 
            RelationshipType.OWNS.value
        )
        if owners:
            owner_names = [e.name for e in owners]
            embed.add_field(name="Owned By", value=", ".join(owner_names), inline=False)
        
        # Control relationships
        controlled_entities = repositories.relationship.get_children(
            str(interaction.guild.id), 
            entity.id, 
            RelationshipType.CONTROLS.value
        )
        if controlled_entities:
            controlled_names = [e.name for e in controlled_entities]
            embed.add_field(name="Controls", value=", ".join(controlled_names), inline=False)
        
        controllers = repositories.relationship.get_parents(
            str(interaction.guild.id), 
            entity.id, 
            RelationshipType.CONTROLS.value
        )
        if controllers:
            controller_names = [e.name for e in controllers]
            embed.add_field(name="Controlled By", value=", ".join(controller_names), inline=False)
        
        # Add notes if any
        if entity.notes:
            notes_text = "\n".join(entity.notes[:3])  # Show first 3 notes
            if len(entity.notes) > 3:
                notes_text += f"\n(+{len(entity.notes) - 3} more notes)"
            embed.add_field(name="Notes", value=notes_text[:1024], inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

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

class ConfirmDeleteEntityView(discord.ui.View):
    def __init__(self, entity: BaseEntity):
        super().__init__(timeout=60)
        self.entity = entity

    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Delete the entity (this will also delete all relationships)
        repositories.entity.delete_entity(str(interaction.guild.id), self.entity.id)
        await interaction.response.edit_message(
            content=f"✅ Deleted entity `{self.entity.name}`.",
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