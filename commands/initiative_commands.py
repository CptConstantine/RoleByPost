import discord
from discord.ext import commands
from discord import app_commands
from commands.autocomplete import initiative_addable_names_autocomplete, initiative_participant_names_autocomplete, initiative_type_autocomplete
from core.command_decorators import gm_role_required, no_ic_channels
from core.initiative_types import InitiativeParticipant
from data.repositories.repository_factory import repositories
import core.factories as factories

class InitiativeCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    initiative_group = app_commands.Group(name="init", description="Initiative management commands")

    @initiative_group.command(name="start", description="Start initiative in this channel.")
    @app_commands.describe(
        type="Type of initiative (e.g. popcorn, generic). Leave blank for server default."
    )
    @app_commands.autocomplete(type=initiative_type_autocomplete)
    @gm_role_required()
    @no_ic_channels()
    async def initiative_start(self, interaction: discord.Interaction, type: str = None):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id

        # End any existing initiative in this channel
        initiative = repositories.initiative.get_active_initiative(str(guild_id), str(channel_id))
        if initiative:
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
                await interaction.followup.send("❌ No default initiative type set. Please set it with `/init set-default`.", ephemeral=True)
                return

        InitiativeClass = factories.get_specific_initiative(type)

        # Gather participants: PCs and scene NPCs
        all_chars = repositories.character.get_all_pcs_and_npcs_by_guild(str(guild_id))
        non_gm_pcs = [c for c in all_chars if not c.is_npc and not repositories.server.has_gm_permission(str(guild_id), c.owner_id)]
        scene = repositories.scene.get_active_scene(str(guild_id))
        if not scene:
            npcs = []
        else:
            npcs = repositories.scene_npc.get_scene_npcs(str(guild_id), scene.name)
        participants = [
            InitiativeParticipant(
                id=str(c.id),
                name=c.name,
                owner_id=str(c.owner_id),
                is_npc=bool(c.is_npc)
            )
            for c in non_gm_pcs + npcs
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
    @gm_role_required()
    @no_ic_channels()
    async def initiative_end(self, interaction: discord.Interaction):
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

    @initiative_group.command(name="add-char", description="Add a PC or NPC to the current initiative.")
    @app_commands.describe(name="Name of the PC or NPC to add")
    @app_commands.autocomplete(name=initiative_addable_names_autocomplete)
    @gm_role_required()
    @no_ic_channels()
    async def initiative_add_char(self, interaction: discord.Interaction, name: str, position: int = None):
        initiative = repositories.initiative.get_active_initiative(str(interaction.guild.id), str(interaction.channel.id))
        if not initiative:
            await interaction.response.send_message("❌ No active initiative.", ephemeral=True)
            return
            
        char = repositories.character.get_by_name(str(interaction.guild.id), name)
        if not char:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return
        
        # Check if participant already exists
        if any(p.name.lower() == name.lower() for p in initiative.participants):
            await interaction.response.send_message("❌ Character already in initiative.", ephemeral=True)
            return
            
        participant = InitiativeParticipant(
            id=str(char.id),
            name=char.name,
            owner_id=str(char.owner_id),
            is_npc=bool(char.is_npc)
        )
        initiative.add_participant(participant, position)
        repositories.initiative.update_initiative_state(str(interaction.guild.id), str(interaction.channel.id), initiative)
        
        # Create a view and update the pinned message 
        message_id = repositories.initiative.get_initiative_message_id(str(interaction.guild.id), str(interaction.channel.id))
        view = factories.get_specific_initiative_view(
            interaction.guild.id, 
            interaction.channel.id, 
            initiative,
            message_id
        )
        await view.update_view(interaction)
        
        await interaction.followup.send(f"✅ Added {char.name} to initiative.", ephemeral=True)

    @initiative_group.command(name="remove-char", description="Remove a PC or NPC from the current initiative.")
    @app_commands.describe(name="Name of the PC or NPC to remove")
    @app_commands.autocomplete(name=initiative_participant_names_autocomplete)
    @gm_role_required()
    @no_ic_channels()
    async def initiative_remove_char(self, interaction: discord.Interaction, name: str):
        initiative = repositories.initiative.get_active_initiative(str(interaction.guild.id), str(interaction.channel.id))
        if not initiative:
            await interaction.response.send_message("❌ No active initiative.", ephemeral=True)
            return

        if name.lower() not in [p.name.lower() for p in initiative.participants]:
            await interaction.response.send_message("❌ Name not found in initiative.", ephemeral=True)
            return

        if initiative.participants.__len__() <= 1:
            await interaction.response.send_message("❌ Cannot remove the last participant from initiative. Use `/init end` instead", ephemeral=True)
            return
        
        char_id = next((str(p.id) for p in initiative.participants if p.name.lower() == name.lower()), None)
        
        initiative.remove_participant(char_id)
            
        repositories.initiative.update_initiative_state(str(interaction.guild.id), str(interaction.channel.id), initiative)
        
        # Update the pinned message with the new state
        message_id = repositories.initiative.get_initiative_message_id(str(interaction.guild.id), str(interaction.channel.id))
        view = factories.get_specific_initiative_view(
            interaction.guild.id, 
            interaction.channel.id, 
            initiative,
            message_id
        )
        await view.update_view(interaction)
        
        await interaction.followup.send(f"✅ Removed {name} from initiative.", ephemeral=True)

    @initiative_group.command(name="set-default", description="Set the default initiative type for this server.")
    @app_commands.describe(type="Type of initiative (e.g., popcorn, generic)")
    @app_commands.autocomplete(type=initiative_type_autocomplete)
    @gm_role_required()
    @no_ic_channels()
    async def set_default_initiative(self, interaction: discord.Interaction, type: str):
        repositories.server_initiative_defaults.set_default_type(str(interaction.guild.id), type)
        await interaction.response.send_message(f"✅ Default initiative type set to {type}.", ephemeral=True)

async def setup_initiative_commands(bot: commands.Bot):
    await bot.add_cog(InitiativeCommands(bot))