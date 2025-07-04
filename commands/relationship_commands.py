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

    async def character_or_npc_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for any character or NPC name"""
        if not interaction.guild:
            return []
        
        # Get all characters and NPCs
        characters = repositories.character.get_all_by_guild(str(interaction.guild.id))
        
        # Filter based on current input
        if current:
            characters = [char for char in characters if current.lower() in char.name.lower()]
        
        # Limit to 25 results
        return [
            app_commands.Choice(name=char.name, value=char.name)
            for char in characters[:25]
        ]

    async def relationship_type_autocomplete(self, interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
        """Autocomplete for relationship types"""
        relationship_types = [
            ("Owns", RelationshipType.OWNS.value),
            ("Controls", RelationshipType.CONTROLS.value),
            ("Companion", RelationshipType.COMPANION.value),
            ("Minion", RelationshipType.MINION.value),
            ("Hired", RelationshipType.HIRED.value),
            ("Allied", RelationshipType.ALLIED.value),
            ("Enemy", RelationshipType.ENEMY.value),
        ]
        
        # Filter based on current input
        if current:
            relationship_types = [(name, value) for name, value in relationship_types 
                                if current.lower() in name.lower()]
        
        return [
            app_commands.Choice(name=name, value=value)
            for name, value in relationship_types
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
    @app_commands.autocomplete(from_entity=character_or_npc_autocomplete)
    @app_commands.autocomplete(to_entity=character_or_npc_autocomplete)
    @app_commands.autocomplete(relationship_type=relationship_type_autocomplete)
    async def create_relationship(self, interaction: discord.Interaction, from_entity: str, to_entity: str, relationship_type: str, description: str = None):
        """Create a relationship between two entities"""
        # Check GM permissions for certain relationship types
        if relationship_type in [RelationshipType.OWNS.value, RelationshipType.CONTROLS.value]:
            if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
                await interaction.response.send_message("❌ Only GMs can create ownership and control relationships.", ephemeral=True)
                return
        
        # Get the entities
        from_char = repositories.character.get_character_by_name(interaction.guild.id, from_entity)
        to_char = repositories.character.get_character_by_name(interaction.guild.id, to_entity)
        
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
    @app_commands.autocomplete(from_entity=character_or_npc_autocomplete)
    @app_commands.autocomplete(to_entity=character_or_npc_autocomplete)
    @app_commands.autocomplete(relationship_type=relationship_type_autocomplete)
    async def remove_relationship(self, interaction: discord.Interaction, from_entity: str, to_entity: str, relationship_type: str = None):
        """Remove a relationship between two entities"""
        # Check GM permissions for certain relationship types
        if relationship_type in [RelationshipType.OWNS.value, RelationshipType.CONTROLS.value]:
            if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
                await interaction.response.send_message("❌ Only GMs can remove ownership and control relationships.", ephemeral=True)
                return
        
        # Get the entities
        from_char = repositories.character.get_character_by_name(interaction.guild.id, from_entity)
        to_char = repositories.character.get_character_by_name(interaction.guild.id, to_entity)
        
        if not from_char or not to_char:
            await interaction.response.send_message("❌ One or both entities not found.", ephemeral=True)
            return
        
        # Remove the relationship
        success = repositories.relationship.delete_relationships_by_entities(
            str(interaction.guild.id), from_char.id, to_char.id, relationship_type
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
    @app_commands.autocomplete(entity_name=character_or_npc_autocomplete)
    async def list_relationships(self, interaction: discord.Interaction, entity_name: str):
        """List all relationships for an entity"""
        # Get the entity
        entity = repositories.character.get_character_by_name(interaction.guild.id, entity_name)
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
                target_entity = repositories.character.get_by_id(rel.to_entity_id)
                if target_entity:
                    rel_name = rel.relationship_type.replace("_", " ").title()
                    description = rel.metadata.get("description", "") if rel.metadata else ""
                    line = f"• **{rel_name}** {target_entity.name}"
                    if description:
                        line += f" - *{description}*"
                    outgoing_relationships.append(line)
            else:
                # Another entity has a relationship TO this entity
                source_entity = repositories.character.get_by_id(rel.from_entity_id)
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
    @app_commands.autocomplete(owned_entity=character_or_npc_autocomplete)
    @app_commands.autocomplete(new_owner=character_or_npc_autocomplete)
    async def transfer_ownership(self, interaction: discord.Interaction, owned_entity: str, new_owner: str):
        """Transfer ownership of an entity to another entity (GM only)"""
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can transfer ownership.", ephemeral=True)
            return
        
        # Get the entities
        owned_char = repositories.character.get_character_by_name(interaction.guild.id, owned_entity)
        new_owner_char = repositories.character.get_character_by_name(interaction.guild.id, new_owner)
        
        if not owned_char or not new_owner_char:
            await interaction.response.send_message("❌ One or both entities not found.", ephemeral=True)
            return
        
        # Remove existing ownership relationships
        existing_owners = repositories.relationship.get_parents(str(interaction.guild.id), owned_char.id, RelationshipType.OWNS.value)
        for owner in existing_owners:
            repositories.relationship.delete_relationships_by_entities(
                str(interaction.guild.id), owner.id, owned_char.id, RelationshipType.OWNS.value
            )
        
        # Create new ownership relationship
        repositories.relationship.create_relationship(
            str(interaction.guild.id),
            new_owner_char.id,
            owned_char.id,
            RelationshipType.OWNS.value,
            {"transferred_by": str(interaction.user.id)}
        )
        
        await interaction.response.send_message(
            f"✅ **{new_owner}** now owns **{owned_entity}**", 
            ephemeral=True
        )

async def setup_relationship_commands(bot: commands.Bot):
    await bot.add_cog(RelationshipCommands(bot))