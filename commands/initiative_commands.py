import discord
from discord.ext import commands
from discord import app_commands
from core.initiative_types import InitiativeParticipant
from data.repositories.repository_factory import repositories
import core.factories as factories

class InitiativeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    initiative_group = app_commands.Group(name="initiative", description="Initiative management commands")

    @initiative_group.command(name="start", description="Start initiative in this channel.")
    @app_commands.describe(
        type="Type of initiative (e.g. popcorn, generic). Leave blank for server default.",
        scene="Scene name to grab NPCs from (optional)."
    )
    async def initiative_start(self, interaction: discord.Interaction, type: str = None, scene: str = None):
        # Check GM permissions
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can start initiative.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id

        # End any existing initiative in this channel
        initiative_data = repositories.initiative.get_initiative_data(str(guild_id), str(channel_id))
        if initiative_data and initiative_data["is_active"]:
            # Try to delete the old pinned message
            message_id = repositories.initiative.get_initiative_message_id(str(guild_id), str(channel_id))
            if message_id:
                try:
                    message = await interaction.channel.fetch_message(int(message_id))
                    await message.delete()
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    pass  # Ignore if we can't find or delete the message
            repositories.initiative.end_initiative(str(guild_id), str(channel_id))

        # Use default initiative type if not specified
        if not type:
            type = repositories.server_initiative_defaults.get_default_type(str(guild_id))
            if not type:
                await interaction.followup.send("❌ No default initiative type set. Please set it with `/initiative default`.", ephemeral=True)
                return

        InitiativeClass = factories.get_specific_initiative(type)

        # Gather participants: PCs and scene NPCs
        pcs = repositories.character.get_non_gm_active_characters(str(guild_id))
        npcs = repositories.scene_npc.get_scene_npcs(str(guild_id), scene)
        participants = [
            InitiativeParticipant(
                id=str(c.id),
                name=c.name,
                owner_id=str(c.owner_id),
                is_npc=bool(c.is_npc)
            )
            for c in pcs + npcs
        ]

        if not participants:
            await interaction.followup.send("❌ No participants found for initiative.", ephemeral=True)
            return

        initiative = InitiativeClass.from_participants(participants)
        repositories.initiative.start_initiative(str(guild_id), str(channel_id), type, initiative.to_dict())
        
        # Create view and initialize the pinned message
        view = factories.get_specific_initiative_view(guild_id, channel_id, initiative)
        
        # We need to trigger the view update to create the pinned message
        await view.update_view(interaction)
        await interaction.followup.send("🚦 Initiative started and pinned!", ephemeral=True)

    @initiative_group.command(name="end", description="End initiative in this channel.")
    async def initiative_end(self, interaction: discord.Interaction):
        # Check GM permissions
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can end initiative.", ephemeral=True)
            return
            
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        
        # Try to delete the pinned message
        message_id = repositories.initiative.get_initiative_message_id(str(guild_id), str(channel_id))
        if message_id:
            try:
                message = await interaction.channel.fetch_message(int(message_id))
                await message.delete()
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass  # Ignore if we can't find or delete the message
    
        repositories.initiative.end_initiative(str(guild_id), str(channel_id))
        await interaction.response.send_message("🛑 Initiative ended.", ephemeral=False)

    @initiative_group.command(name="add", description="Add a PC or NPC to the current initiative.")
    @app_commands.describe(name="Name of the PC or NPC to add")
    async def initiative_add(self, interaction: discord.Interaction, name: str):
        # Check GM permissions
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can add participants to initiative.", ephemeral=True)
            return
            
        initiative_data = repositories.initiative.get_initiative_data(str(interaction.guild.id), str(interaction.channel.id))
        if not initiative_data or not initiative_data["is_active"]:
            await interaction.response.send_message("❌ No active initiative.", ephemeral=True)
            return
            
        InitiativeClass = factories.get_specific_initiative(initiative_data["type"])
        initiative = InitiativeClass.from_dict(initiative_data["initiative_state"])
        all_chars = repositories.character.find_all_by_column('guild_id', str(interaction.guild.id))
        char = next((c for c in all_chars if c.name.lower() == name.lower()), None)
        if not char:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return
            
        participant = InitiativeParticipant(
            id=str(char.id),
            name=char.name,
            owner_id=str(char.owner_id),
            is_npc=bool(char.is_npc)
        )
        initiative.participants.append(participant)
        repositories.initiative.update_initiative_state(str(interaction.guild.id), str(interaction.channel.id), initiative.to_dict())
        
        # Create a view and update the pinned message 
        message_id = repositories.initiative.get_initiative_message_id(str(interaction.guild.id), str(interaction.channel.id))
        view = factories.get_specific_initiative_view(
            interaction.guild.id, 
            interaction.channel.id, 
            initiative,
            message_id
        )
        await view.update_view(interaction)
        
        await interaction.response.send_message(f"✅ Added {char.name} to initiative.", ephemeral=True)

    @initiative_group.command(name="remove", description="Remove a PC or NPC from the current initiative.")
    @app_commands.describe(name="Name of the PC or NPC to remove")
    async def initiative_remove(self, interaction: discord.Interaction, name: str):
        # Check GM permissions
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can remove participants from initiative.", ephemeral=True)
            return
            
        initiative_data = repositories.initiative.get_initiative_data(str(interaction.guild.id), str(interaction.channel.id))
        if not initiative_data or not initiative_data["is_active"]:
            await interaction.response.send_message("❌ No active initiative.", ephemeral=True)
            return
            
        InitiativeClass = factories.get_specific_initiative(initiative_data["type"])
        initiative = InitiativeClass.from_dict(initiative_data["initiative_state"])
        before = len(initiative.participants)
        initiative.participants = [p for p in initiative.participants if p.name.lower() != name.lower()]
        if len(initiative.participants) == before:
            await interaction.response.send_message("❌ Name not found in initiative.", ephemeral=True)
            return
            
        repositories.initiative.update_initiative_state(str(interaction.guild.id), str(interaction.channel.id), initiative.to_dict())
        
        # Update the pinned message with the new state
        message_id = repositories.initiative.get_initiative_message_id(str(interaction.guild.id), str(interaction.channel.id))
        view = factories.get_specific_initiative_view(
            interaction.guild.id, 
            interaction.channel.id, 
            initiative,
            message_id
        )
        await view.update_view(interaction)
        
        await interaction.response.send_message(f"✅ Removed {name} from initiative.", ephemeral=True)

    @initiative_group.command(name="default", description="Set the default initiative type for this server.")
    @app_commands.describe(type="Type of initiative (e.g., popcorn, generic)")
    async def set_default_initiative(self, interaction: discord.Interaction, type: str):
        # Check GM permissions
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can set the default initiative type.", ephemeral=True)
            return
            
        repositories.server_initiative_defaults.set_default_type(str(interaction.guild.id), type)
        await interaction.response.send_message(f"✅ Default initiative type set to {type}.", ephemeral=True)

async def setup_initiative_commands(bot: commands.Bot):
    await bot.add_cog(InitiativeCommands(bot))