import discord
from discord.ext import commands
from discord import app_commands
from data.repositories.repository_factory import repositories
from core.models import RelationshipType
from core.models import BaseEntity
from typing import Optional, List
import core.factories as factories

class RelationshipCommands(commands.Cog):
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
            characters = repositories.character.get_all_by_guild(str(interaction.guild.id))
            other_entities = repositories.entity.get_all_by_guild(str(interaction.guild.id))
            
            # Combine both lists, avoiding duplicates
            all_entities = []
            character_ids = {char.id for char in characters}
            
            # Add all characters
            all_entities.extend(characters)
            
            # Add other entities that aren't already in the character list
            for entity in other_entities:
                if entity.id not in character_ids:
                    all_entities.append(entity)
        else:
            # Users can only see entities they own
            user_characters = repositories.character.get_user_characters(str(interaction.guild.id), str(interaction.user.id))
            user_entities = repositories.entity.get_all_by_owner(str(interaction.guild.id), str(interaction.user.id))
            
            # Combine both lists, avoiding duplicates
            all_entities = []
            character_ids = {char.id for char in user_characters}
            
            # Add user's characters
            all_entities.extend(user_characters)
            
            # Add user's other entities that aren't already in the character list
            for entity in user_entities:
                if entity.id not in character_ids:
                    all_entities.append(entity)
        
        # Filter based on current input
        if current:
            all_entities = [entity for entity in all_entities if current.lower() in entity.name.lower()]
        
        # Format the choices with entity type for clarity
        choices = []
        for entity in all_entities[:25]:  # Limit to 25 results
            if hasattr(entity, 'is_npc'):
                # This is a character
                entity_type = "NPC" if entity.is_npc else "PC"
            else:
                # This is a regular entity
                entity_type = entity.entity_type.value.upper()
            
            choices.append(
                app_commands.Choice(name=f"{entity.name} ({entity_type})", value=entity.name)
            )
        
        return choices

    async def relationship_type_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for relationship types"""
        relationship_types = RelationshipType.get_all_dict()
        
        # Filter based on current input
        if current:
            filtered_types = {name: value for name, value in relationship_types.items() if current.lower() in name.lower()}
        else:
            filtered_types = relationship_types
        
        return [
            app_commands.Choice(name=name, value=value.value)
            for name, value in filtered_types.items()
        ]

    # Create the relationship command group
    relationship_group = app_commands.Group(name="relationship", description="Manage relationships between entities")

    @relationship_group.command(name="create", description="Create a relationship between two entities")
    @app_commands.describe(
        from_entity="The entity that has the relationship",
        to_entity="The entity that is the target of the relationship", 
        relationship_type="Type of relationship",
        description="Optional description of the relationship"
    )
    @app_commands.autocomplete(from_entity=entity_autocomplete)
    @app_commands.autocomplete(to_entity=entity_autocomplete)
    @app_commands.autocomplete(relationship_type=relationship_type_autocomplete)
    async def create_relationship(self, interaction: discord.Interaction, from_entity: str, to_entity: str, relationship_type: str, description: str = None):
        """Create a relationship between two entities"""
        # Check GM permissions for certain relationship types
        if relationship_type in [RelationshipType.POSSESSES.value, RelationshipType.CONTROLS.value]:
            if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
                await interaction.response.send_message("❌ Only GMs can create ownership and control relationships.", ephemeral=True)
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
        
        # Check if relationship already exists
        existing = repositories.relationship.get_relationship_by_entities(
            str(interaction.guild.id), from_char.id, to_char.id, relationship_type
        )
        
        if existing:
            await interaction.response.send_message(f"❌ Relationship already exists between {from_entity} and {to_entity}.", ephemeral=True)
            return
        
        # Create the relationship
        metadata = {"description": description} if description else {}
        relationship = repositories.relationship.create_relationship(
            str(interaction.guild.id),
            from_char.id,
            to_char.id,
            relationship_type,
            metadata
        )
        
        relationship_name = relationship_type.replace("_", " ").title()
        await interaction.response.send_message(
            f"✅ Created relationship: **{from_entity}** {relationship_name.lower()} **{to_entity}**", 
            ephemeral=True
        )

    @relationship_group.command(name="remove", description="Remove a relationship between two entities")
    @app_commands.describe(
        from_entity="The entity that has the relationship",
        to_entity="The entity that is the target of the relationship",
        relationship_type="Type of relationship to remove (leave blank to remove all)"
    )
    @app_commands.autocomplete(from_entity=entity_autocomplete)
    @app_commands.autocomplete(to_entity=entity_autocomplete)
    @app_commands.autocomplete(relationship_type=relationship_type_autocomplete)
    async def remove_relationship(self, interaction: discord.Interaction, from_entity: str, to_entity: str, relationship_type: str = None):
        """Remove a relationship between two entities"""
        
        # Get the entities - try both character and entity repositories
        from_entity = self._find_entity_by_name(interaction.guild.id, from_entity)
        to_entity = self._find_entity_by_name(interaction.guild.id, to_entity)
        
        if not from_entity or not to_entity:
            await interaction.response.send_message("❌ One or both entities not found.", ephemeral=True)
            return
        
        # Check permissions for certain relationship types
        if relationship_type in [RelationshipType.POSSESSES.value, RelationshipType.CONTROLS.value]:
            if from_entity.owner_id != interaction.user.id and not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
                await interaction.response.send_message("❌ Only owners or GMs can remove ownership and control relationships.", ephemeral=True)
                return
        
        # Remove the relationship
        success = repositories.relationship.delete_relationships_by_entities(
            str(interaction.guild.id), from_entity.id, to_entity.id, relationship_type
        )
        
        if success:
            if relationship_type:
                relationship_name = relationship_type.replace("_", " ").title()
                await interaction.response.send_message(
                    f"✅ Removed {relationship_name.lower()} relationship between **{from_entity}** and **{to_entity}**", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    f"✅ Removed all relationships between **{from_entity}** and **{to_entity}**", 
                    ephemeral=True
                )
        else:
            await interaction.response.send_message("❌ No relationship found to remove.", ephemeral=True)

    @relationship_group.command(name="list", description="List all relationships for an entity")
    @app_commands.describe(entity_name="The entity to show relationships for")
    @app_commands.autocomplete(entity_name=entity_autocomplete)
    async def list_relationships(self, interaction: discord.Interaction, entity_name: str):
        """List all relationships for an entity"""
        # Get the entity - try both character and entity repositories
        entity = self._find_entity_by_name(interaction.guild.id, entity_name)
        if not entity:
            await interaction.response.send_message(f"❌ Entity '{entity_name}' not found.", ephemeral=True)
            return
        
        # Get all relationships involving this entity
        relationships = repositories.relationship.get_relationships_for_entity(str(interaction.guild.id), entity.id)
        
        if not relationships:
            await interaction.response.send_message(f"**{entity_name}** has no relationships.", ephemeral=True)
            return
        
        embed = discord.Embed(
            title=f"🔗 Relationships for {entity_name}",
            color=discord.Color.blue()
        )
        
        outgoing_relationships = []
        incoming_relationships = []
        
        for rel in relationships:
            if rel.from_entity_id == entity.id:
                # This entity has a relationship TO another entity
                target_entity = self._find_entity_by_id(rel.to_entity_id)
                if target_entity:
                    rel_name = rel.relationship_type.replace("_", " ").title()
                    description = rel.metadata.get("description", "") if rel.metadata else ""
                    line = f"• **{rel_name}** {target_entity.name}"
                    if description:
                        line += f" - *{description}*"
                    outgoing_relationships.append(line)
            else:
                # Another entity has a relationship TO this entity
                source_entity = self._find_entity_by_id(rel.from_entity_id)
                if source_entity:
                    rel_name = rel.relationship_type.replace("_", " ").title()
                    description = rel.metadata.get("description", "") if rel.metadata else ""
                    line = f"• **{source_entity.name}** {rel_name.lower()} this entity"
                    if description:
                        line += f" - *{description}*"
                    incoming_relationships.append(line)
        
        if outgoing_relationships:
            embed.add_field(
                name="Relationships To Others",
                value="\n".join(outgoing_relationships),
                inline=False
            )
        
        if incoming_relationships:
            embed.add_field(
                name="Relationships From Others", 
                value="\n".join(incoming_relationships),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @relationship_group.command(name="transfer", description="Transfer ownership of an entity to another entity")
    @app_commands.describe(
        owned_entity="The entity to transfer ownership of",
        new_owner="The entity that will become the new owner"
    )
    @app_commands.autocomplete(owned_entity=entity_autocomplete)
    @app_commands.autocomplete(new_owner=entity_autocomplete)
    async def transfer_ownership(self, interaction: discord.Interaction, owned_entity: str, new_owner: str):
        """Transfer ownership of an entity to another entity (GM only)"""
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can transfer ownership.", ephemeral=True)
            return
        
        # Get the entities - try both character and entity repositories
        owned_char = self._find_entity_by_name(interaction.guild.id, owned_entity)
        new_owner_char = self._find_entity_by_name(interaction.guild.id, new_owner)
        
        if not owned_char or not new_owner_char:
            await interaction.response.send_message("❌ One or both entities not found.", ephemeral=True)
            return
        
        # Remove existing ownership relationships
        existing_owners = repositories.relationship.get_parents(str(interaction.guild.id), owned_char.id, RelationshipType.POSSESSES.value)
        for owner in existing_owners:
            repositories.relationship.delete_relationships_by_entities(
                str(interaction.guild.id), owner.id, owned_char.id, RelationshipType.POSSESSES.value
            )
        
        # Create new ownership relationship
        repositories.relationship.create_relationship(
            str(interaction.guild.id),
            new_owner_char.id,
            owned_char.id,
            RelationshipType.POSSESSES.value,
            {"transferred_by": str(interaction.user.id)}
        )
        
        await interaction.response.send_message(
            f"✅ **{new_owner}** now owns **{owned_entity}**", 
            ephemeral=True
        )

    def _find_entity_by_name(self, guild_id: str, entity_name: str) -> Optional[BaseEntity]:
        """Helper method to find an entity by name in both character and entity repositories"""
        # Try character repository first
        entity = repositories.character.get_character_by_name(guild_id, entity_name)
        if entity:
            return entity
        
        # Try entity repository
        entity = repositories.entity.get_by_name(str(guild_id), entity_name)
        return entity

    def _find_entity_by_id(self, entity_id: str) -> Optional[BaseEntity]:
        """Helper method to find an entity by ID in both character and entity repositories"""
        # Try character repository first
        entity = repositories.character.get_by_id(entity_id)
        if entity:
            return entity
        
        # Try entity repository
        entity = repositories.entity.get_by_id(entity_id)
        return entity

async def setup_relationship_commands(bot: commands.Bot):
    await bot.add_cog(RelationshipCommands(bot))