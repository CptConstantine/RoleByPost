import discord
from discord.ext import commands
from discord import app_commands
from core.initiative_types import InitiativeParticipant
from data import repo
import core.system_factory as system_factory

def setup_initiative_commands(bot: commands.Bot):
    

    @bot.tree.command(name="initiative_start", description="Start initiative in this channel.")
    @app_commands.describe(
        type="Type of initiative (e.g. popcorn, classic). Leave blank for server default.",
        scene="Scene name to grab NPCs from (optional)."
    )
    async def initiative_start(interaction: discord.Interaction, type: str = None, scene: str = None):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id

        # Use default initiative type if not specified
        if not type:
            type = repo.get_default_initiative_type(guild_id)
            if not type:
                await interaction.followup.send("❌ No default initiative type set. Please set it with `/set_default_initiative`.", ephemeral=True)
                return

        InitiativeClass = system_factory.get_specific_initiative(type)

        # Gather participants: PCs and scene NPCs
        pcs = repo.get_non_gm_active_characters(guild_id)
        npcs = repo.get_scene_npcs(guild_id)
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

        repo.start_initiative(guild_id, channel_id, type, initiative.to_dict())

        # Use the system-agnostic view factory
        view = system_factory.get_specific_initiative_view(guild_id, channel_id, initiative)
        await interaction.followup.send("🚦 Initiative started!", view=view, ephemeral=False)

    @bot.tree.command(name="initiative_end", description="End initiative in this channel.")
    async def initiative_end(interaction: discord.Interaction):
        repo.end_initiative(interaction.guild.id, interaction.channel.id)
        await interaction.response.send_message("🛑 Initiative ended.", ephemeral=False)

    @bot.tree.command(name="initiative_add", description="Add a PC or NPC to the current initiative.")
    @app_commands.describe(name="Name of the PC or NPC to add")
    async def initiative_add(interaction: discord.Interaction, name: str):
        initiative_data = repo.get_initiative(interaction.guild.id, interaction.channel.id)
        if not initiative_data or not initiative_data["is_active"]:
            await interaction.response.send_message("❌ No active initiative.", ephemeral=True)
            return
        InitiativeClass = system_factory.get_specific_initiative(initiative_data["type"])
        initiative = InitiativeClass.from_dict(initiative_data["initiative_state"])
        all_chars = repo.get_all_characters(interaction.guild.id)
        char = next((c for c in all_chars if c.name.lower() == name.lower()), None)
        if not char:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return
        # Add participant
        initiative.participants.append({"id": str(char.owner_id), "name": char.name})
        repo.update_initiative_state(interaction.guild.id, interaction.channel.id, initiative.to_dict())
        await interaction.response.send_message(f"✅ Added {char.name} to initiative.", ephemeral=True)

    @bot.tree.command(name="initiative_remove", description="Remove a PC or NPC from the current initiative.")
    @app_commands.describe(name="Name of the PC or NPC to remove")
    async def initiative_remove(interaction: discord.Interaction, name: str):
        initiative_data = repo.get_initiative(interaction.guild.id, interaction.channel.id)
        if not initiative_data or not initiative_data["is_active"]:
            await interaction.response.send_message("❌ No active initiative.", ephemeral=True)
            return
        InitiativeClass = system_factory.get_specific_initiative(initiative_data["type"])
        initiative = InitiativeClass.from_dict(initiative_data["initiative_state"])
        before = len(initiative.participants)
        initiative.participants = [p for p in initiative.participants if p["name"].lower() != name.lower()]
        if len(initiative.participants) == before:
            await interaction.response.send_message("❌ Name not found in initiative.", ephemeral=True)
            return
        repo.update_initiative_state(interaction.guild.id, interaction.channel.id, initiative.to_dict())
        await interaction.response.send_message(f"✅ Removed {name} from initiative.", ephemeral=True)

    @bot.tree.command(name="set_default_initiative", description="Set the default initiative type for this server.")
    @app_commands.describe(type="Type of initiative (e.g., popcorn, classic)")
    async def set_default_initiative(interaction: discord.Interaction, type: str):
        repo.set_default_initiative_type(interaction.guild.id, type)
        await interaction.response.send_message(f"✅ Default initiative type set to {type}.", ephemeral=True)

    @bot.tree.command(name="initiative_set_order", description="GM: Set the initiative order for the current channel.")
    @app_commands.describe(order="Comma-separated list of participant names in initiative order")
    async def initiative_set_order(interaction: discord.Interaction, order: str):
        """GM sets the initiative order for the current channel."""
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ Only GMs can set initiative order.", ephemeral=True)
            return

        initiative_data = repo.get_initiative(interaction.guild.id, interaction.channel.id)
        if not initiative_data or not initiative_data["is_active"]:
            await interaction.response.send_message("❌ No active initiative in this channel.", ephemeral=True)
            return

        InitiativeClass = system_factory.get_specific_initiative(initiative_data["type"])
        initiative = InitiativeClass.from_dict(initiative_data["initiative_state"])

        # Parse the order string
        names = [name.strip() for name in order.split(",") if name.strip()]
        if not names:
            await interaction.response.send_message("❌ Please provide a comma-separated list of names.", ephemeral=True)
            return

        # Find matching participants by name (case-insensitive)
        name_to_participant = {p.name.lower(): p for p in initiative.participants}
        new_order = []
        for name in names:
            p = name_to_participant.get(name.lower())
            if not p:
                await interaction.response.send_message(f"❌ Name '{name}' not found among current participants.", ephemeral=True)
                return
            new_order.append(p)

        # Save as dicts for DB
        initiative.participants = new_order

        repo.update_initiative_state(interaction.guild.id, interaction.channel.id, initiative.to_dict())
        await interaction.response.send_message(
            f"✅ Initiative order set: {', '.join([p.name for p in new_order])}. Press Start Initiative to begin.",
            ephemeral=True
        )