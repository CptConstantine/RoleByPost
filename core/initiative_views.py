from abc import ABC, abstractmethod
import logging
import discord
from discord import ui, SelectOption
from core.initiative_types import GenericInitiative, PopcornInitiative
from core.base_models import BaseInitiative
from core.shared_views import embed_to_text
from data.repositories.repository_factory import repositories


def _truncate_text(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _get_embed_colour(embed: discord.Embed, fallback: discord.Colour = discord.Colour.blue()) -> discord.Colour:
    if embed and embed.colour and embed.colour.value:
        return embed.colour
    return fallback


def _build_generic_initiative_content(initiative: GenericInitiative):
    embed = discord.Embed(
        title="📊 Initiative Tracker",
        color=discord.Color.blue()
    )

    if not initiative or not initiative.is_started:
        content = "🎲 **INITIATIVE TRACKING** 🎲\nPress Start Initiative to begin."
        embed.description = "Press Start Initiative to begin."
        embed.description += "\n\nCurrent Initiative Order: {" + ", ".join([p.name for p in initiative.participants]) + "}" if initiative and initiative.participants else ""
    elif not initiative.participants:
        content = "🎲 **INITIATIVE TRACKING** 🎲\nNo participants in initiative."
        embed.description = "No participants in initiative."
    else:
        current_name = initiative.get_participant_name(initiative.current)
        content = f"🎲 **INITIATIVE TRACKING** 🎲\n\n🔔 It's now **{current_name}**'s turn! (Round {initiative.round_number})"
        embed.add_field(name="Round", value=str(initiative.round_number), inline=True)
        embed.add_field(name="Current Turn", value=current_name, inline=True)

        order_text = "\n".join([
            f"{i+1}. {p.name}" + (" ◀️" if p.id == initiative.current else "")
            for i, p in enumerate(initiative.participants)
        ])
        embed.add_field(name="Initiative Order", value=order_text or "No participants", inline=False)

    return embed, content


def _build_popcorn_initiative_content(initiative: PopcornInitiative):
    embed = discord.Embed(
        title="📊 Popcorn Initiative",
        color=discord.Color.gold()
    )

    if not initiative:
        content = "🎲 **POPCORN INITIATIVE** 🎲\nInitiating..."
        embed.description = "Initiating..."
        return embed, content

    embed.add_field(name="Round", value=str(initiative.round_number), inline=True)

    if initiative.remaining_in_round:
        remaining_names = [initiative.get_participant_name(pid) for pid in initiative.remaining_in_round]
        embed.add_field(name="Remaining", value=", ".join(remaining_names), inline=True)

    current_participant = next((p for p in initiative.participants if p.id == initiative.current), None)
    mention = ""
    if current_participant and not current_participant.is_npc and current_participant.owner_id:
        mention = f"<@{current_participant.owner_id}>, it's your turn!"

    if initiative.is_round_end():
        next_name = initiative.get_participant_name(initiative.current)
        content = f"🎲 **POPCORN INITIATIVE** 🎲"
        content += f"\n{mention}"
        embed.description = f"Current Turn: **{next_name}**\n\nEnd of the round\nUse the dropdown below to pick who goes next when your turn is complete."
    elif initiative.current:
        next_name = initiative.get_participant_name(initiative.current)
        content = f"🎲 **POPCORN INITIATIVE** 🎲"
        content += f"\n{mention}"
        embed.description = f"Current Turn: **{next_name}**\n\nUse the dropdown below to pick who goes next when your turn is complete."
    else:
        content = "🎲 **POPCORN INITIATIVE** 🎲"
        embed.description = "GM: pick who goes first."

    participants_list = "\n".join([
        f"{p.name}" + (" ◀️" if p.id == initiative.current else "")
        for p in initiative.participants
    ])
    embed.add_field(name="Participants", value=participants_list or "No participants", inline=False)

    return embed, content

async def get_gm_ids(guild: discord.Guild):
    """Get GM user IDs from the guild"""
    gm_role_id = repositories.server.get_gm_role_id(str(guild.id))
    if not gm_role_id:
        return set()
    
    gm_role = guild.get_role(int(gm_role_id))
    if not gm_role:
        return set()
    
    return {str(member.id) for member in gm_role.members}

class BasePinnedInitiativeView(ABC, discord.ui.View):
    """
    Base class for initiative views that use a single pinned message.
    Handles common functionality for pinning and updating messages.
    """
    def __init__(self, guild_id=None, channel_id=None, initiative: BaseInitiative = None, message_id=None):
        # Always use timeout=None for persistent views
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.initiative = initiative
        self.message_id = message_id
        self.is_initialized = guild_id is not None and channel_id is not None and initiative is not None
        
    async def get_initiative_data(self, interaction):
        """
        Helper method to load initiative data from the database.
        Returns True if successful, False otherwise.
        """
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id
        
        # Get initiative data from the database
        initiative = repositories.initiative.get_active_initiative(str(guild_id), str(channel_id))
        if not initiative:
            return False
            
        # Get the message ID from the database if we don't have it
        message_id = repositories.initiative.get_initiative_message_id(str(guild_id), str(channel_id))
        if not message_id:
            return False
            
        # Set instance variables
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id
        self.initiative = initiative
        self.is_initialized = True
        
        return True
        
    async def get_pinned_initiative_message(self, interaction: discord.Interaction):
        """Get the initiative message if it exists in the database, or create and pin a new one"""
        channel = interaction.channel
        
        # Get the message ID from the database if we don't have it
        if not self.message_id:
            self.message_id = repositories.initiative.get_initiative_message_id(str(self.guild_id), str(self.channel_id))

        # If we have a message ID, try to fetch and update that message
        if self.message_id:
            try:
                message = await channel.fetch_message(int(self.message_id))
                # Update the existing message with current content
                embed, content = await self.create_initiative_content()
                await message.edit(content=content, embed=embed, view=self)
                return message
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                # Message not found or can't be accessed, we'll create a new one
                pass
        
        return None

    @abstractmethod
    async def update_view(self, interaction: discord.Interaction):
        """
        Update the initiative view (e.g., after a turn advances).
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    async def create_initiative_content(self):
        """
        Create the content and embed for the initiative message.
        Should be overridden by subclasses to provide type-specific formatting.
        
        Returns:
            tuple: (embed, content) where embed is a discord.Embed and content is a string
        """
        pass

    async def update_initiative_message(self, interaction: discord.Interaction, content, embed: discord.Embed, view: discord.ui.View):
        """Update the initiative message instead of sending a new one"""
        message = await self.get_pinned_initiative_message(interaction)
        
        if embed is None or content is None:
            embed, content = await self.create_initiative_content()
        
        if not view:
            view = self
        
        if message:
            try:
                # If the message exists, just update it
                await message.edit(content=content, embed=embed, view=view)
            except Exception as e:
                logging.error(f"Error updating initiative message: {e}")
                # Fallback to sending a new message if editing fails
                if not interaction.response.is_done():
                    await interaction.response.send_message(
                        "⚠️ Failed to update the initiative message. The previous initiative message may have been deleted.",
                        ephemeral=True
                    )
                else:
                    await interaction.followup.send(
                        "⚠️ Failed to update the initiative message. The previous initiative message may have been deleted.",
                        ephemeral=True
                    )
                return None
        else:
            # Pin it if it doesn't exist
            message = await interaction.channel.send(content=content, embed=embed, view=view)
        
            try:
                await message.pin(reason="Initiative tracking")
                self.message_id = message.id
                
                # Store the message ID in the database
                repositories.initiative.set_initiative_message_id(str(self.guild_id), str(self.channel_id), str(message.id))
                
                # Send a temporary message indicating the initiative has been pinned
                temp_msg = await interaction.channel.send("📌 Initiative tracking has been pinned. You can always find the current turn at the top of the channel.")
                
                # Delete the pin notification sent by Discord
                async for msg in interaction.channel.history(limit=10):
                    if msg.type == discord.MessageType.pins_add:
                        await msg.delete()
                        break
                        
                # Delete our own temporary message after a delay
                await temp_msg.delete(delay=8.0)
                
                return message
            except discord.Forbidden:
                await message.edit(content=content + "\n⚠️ I don't have permission to pin messages. This initiative tracker won't be pinned.")
                return message
        
        # Mention the current participant if they have an owner ID
        if self.initiative and self.initiative.participants:
            current_participant = next((p for p in self.initiative.participants if p.id == self.initiative.current), None)
            if current_participant and not current_participant.is_npc and current_participant.owner_id:
                mention = f"<@{current_participant.owner_id}>, it's your turn!"
                mention_str= f"{mention}"
                await interaction.response.send_message(mention_str, ephemeral=False)


class BasePinnedInitiativeViewV2(ABC, discord.ui.LayoutView):
    """Components v2 base class for persistent initiative trackers."""

    def __init__(self, guild_id=None, channel_id=None, initiative: BaseInitiative = None, message_id=None, status_message: str = None):
        super().__init__(timeout=None)
        self.guild_id = guild_id
        self.channel_id = channel_id
        self.initiative = initiative
        self.message_id = message_id
        self.status_message = status_message
        self.is_initialized = guild_id is not None and channel_id is not None and initiative is not None

    async def get_initiative_data(self, interaction):
        guild_id = interaction.guild.id
        channel_id = interaction.channel.id

        initiative = repositories.initiative.get_active_initiative(str(guild_id), str(channel_id))
        if not initiative:
            return False

        message_id = repositories.initiative.get_initiative_message_id(str(guild_id), str(channel_id))
        if not message_id:
            return False

        self.guild_id = guild_id
        self.channel_id = channel_id
        self.message_id = message_id
        self.initiative = initiative
        self.is_initialized = True
        return True

    @abstractmethod
    async def update_view(self, interaction: discord.Interaction):
        pass

    @abstractmethod
    async def create_initiative_content(self):
        pass

    @abstractmethod
    def build_action_rows(self) -> list[ui.ActionRow]:
        pass

    async def prepare_layout(self, status_message: str = None):
        if status_message is not None:
            self.status_message = status_message
        await self._build_layout()

    async def _build_layout(self):
        self.clear_items()

        if self.status_message:
            self.add_item(
                ui.Container(
                    ui.TextDisplay(_truncate_text(self.status_message)),
                    accent_colour=discord.Colour.green(),
                )
            )

        if not self.is_initialized:
            return

        embed, content = await self.create_initiative_content()
        colour = _get_embed_colour(embed)

        if content:
            self.add_item(
                ui.Container(
                    ui.TextDisplay(_truncate_text(content, 1000)),
                    accent_colour=colour,
                )
            )

        self.add_item(
            ui.Container(
                ui.TextDisplay(_truncate_text(embed_to_text(embed))),
                accent_colour=colour,
            )
        )

        action_rows = self.build_action_rows()
        if action_rows:
            self.add_item(ui.Separator())
            for row in action_rows:
                self.add_item(row)

    async def get_pinned_initiative_message(self, interaction: discord.Interaction):
        channel = interaction.channel

        if not self.message_id:
            self.message_id = repositories.initiative.get_initiative_message_id(str(self.guild_id), str(self.channel_id))

        if self.message_id:
            try:
                return await channel.fetch_message(int(self.message_id))
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                pass

        return None

    async def _notify_current_participant(self, interaction: discord.Interaction, initiative: BaseInitiative = None):
        initiative = initiative or self.initiative
        if not initiative or not initiative.participants:
            return

        current_participant = next((p for p in initiative.participants if p.id == initiative.current), None)
        if not current_participant or current_participant.is_npc or not current_participant.owner_id:
            return

        mention = f"<@{current_participant.owner_id}>, it's your turn!"
        if not interaction.response.is_done():
            await interaction.response.send_message(mention, ephemeral=False)
        else:
            await interaction.followup.send(mention, ephemeral=False)

    async def update_initiative_message(self, interaction: discord.Interaction, content=None, embed: discord.Embed = None, view: discord.ui.View = None):
        message = await self.get_pinned_initiative_message(interaction)

        if embed is None or content is None:
            embed, content = await self.create_initiative_content()

        if not view:
            view = self

        try:
            if hasattr(view, "prepare_layout"):
                await view.prepare_layout()

            if message:
                await message.edit(content=None, embed=None, view=view)
            else:
                message = await interaction.channel.send(view=view)
                try:
                    await message.pin(reason="Initiative tracking")
                    self.message_id = message.id
                    repositories.initiative.set_initiative_message_id(str(self.guild_id), str(self.channel_id), str(message.id))

                    temp_msg = await interaction.channel.send("📌 Initiative tracking has been pinned. You can always find the current turn at the top of the channel.")

                    async for msg in interaction.channel.history(limit=10):
                        if msg.type == discord.MessageType.pins_add:
                            await msg.delete()
                            break

                    await temp_msg.delete(delay=8.0)
                except discord.Forbidden:
                    await message.edit(view=view)

            initiative = view.initiative if hasattr(view, "initiative") else self.initiative
            await self._notify_current_participant(interaction, initiative=initiative)
            return message
        except Exception as e:
            logging.error(f"Error updating LayoutView initiative message: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "⚠️ Failed to update the initiative message. The previous initiative message may have been deleted.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "⚠️ Failed to update the initiative message. The previous initiative message may have been deleted.",
                    ephemeral=True
                )
            return None

class GenericInitiativeView(BasePinnedInitiativeView):
    """
    View for generic initiative: End Turn button, shows current participant.
    """
    def __init__(self, guild_id=None, channel_id=None, initiative: GenericInitiative = None, message_id=None):
        super().__init__(guild_id, channel_id, initiative, message_id)
        
        # Skip adding buttons during persistent view registration or when not initialized
        if not self.is_initialized:
            # For persistent view registration, add empty buttons with the correct custom_ids
            self.add_item(ui.Button(label="Start Initiative", style=discord.ButtonStyle.success, custom_id="start_initiative"))
            self.add_item(ui.Button(label="End Turn", style=discord.ButtonStyle.primary, custom_id="end_turn"))
            self.add_item(ui.Button(label="Set Order", style=discord.ButtonStyle.secondary, custom_id="set_initiative_order"))
            return
            
        # Store the guild so we can fetch members with the GM role later
        self.guild = None
        self.allowed_ids = []  # Will be populated in initialize_if_needed
        
        if not initiative.is_started:
            self.add_item(SetOrderButton(self))
            self.add_item(StartInitiativeButton(self))
        else:
            # Find the owner ID of the current participant and add it to allowed_ids
            current_participant = next((p for p in initiative.participants 
                                      if p.id == initiative.current), None)
            
            if current_participant and current_participant.owner_id:
                self.allowed_ids.append(current_participant.owner_id)
                
            self.add_item(EndTurnButton(self))
            
    async def initialize_if_needed(self, interaction):
        """Initialize view data if it wasn't loaded during construction"""
        if not self.is_initialized:
            success = await self.get_initiative_data(interaction)
            if not success:
                await interaction.response.send_message("❌ No active initiative in this channel.", ephemeral=True)
                return False
            
            # Set up allowed users - get GM IDs using the role
            self.guild = interaction.guild
            gm_ids = await get_gm_ids(interaction.guild)
            self.allowed_ids = list(gm_ids)
            
            if self.initiative.is_started:
                current_participant = next((p for p in self.initiative.participants 
                                          if p.id == self.initiative.current), None)
                if current_participant and current_participant.owner_id:
                    self.allowed_ids.append(current_participant.owner_id)
            
            return True
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the current participant's owner or GM to interact
        if interaction.user.id == interaction.client.user.id:
            return True  # Allow the bot itself
        
        # Initialize if this is the first interaction after a restart
        if not self.is_initialized:
            if not await self.initialize_if_needed(interaction):
                return False
                
            # Get custom_id from interaction
            component_id = interaction.data.get("custom_id", "")
            
            # Create a new view with the loaded data and process the interaction
            new_view = GenericInitiativeView(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                initiative=self.initiative,
                message_id=self.message_id
            )
            
            # Check if the user is allowed to interact
            gm_ids = await get_gm_ids(interaction.guild)
            is_gm = str(interaction.user.id) in gm_ids
            is_current_participant = False
            
            if self.initiative.current:
                current_participant = next((p for p in self.initiative.participants 
                                          if p.id == self.initiative.current), None)
                is_current_participant = (current_participant and 
                                         str(current_participant.owner_id) == str(interaction.user.id))
            
            # Handle the interaction with the newly created view
            if component_id == "end_turn":
                if not (is_gm or is_current_participant):
                    await interaction.response.send_message("❌ It's not your turn.", ephemeral=True)
                    return False
                await new_view.handle_end_turn(interaction)
            elif component_id == "start_initiative":
                if not is_gm:
                    await interaction.response.send_message("❌ Only GMs can start initiative.", ephemeral=True)
                    return False
                await new_view.handle_start_initiative(interaction)
            elif component_id == "set_initiative_order":
                if not is_gm:
                    await interaction.response.send_message("❌ Only GMs can set the initiative order.", ephemeral=True)
                    return False
                # Create the current order string for the modal
                current_order = ", ".join([p.name for p in new_view.initiative.participants])
                await interaction.response.send_modal(SetInitiativeOrderModal(new_view, current_order))
                
            return False  # We've already handled the interaction
            
        # Add gms to allowed_ids if not already set
        self.guild = interaction.guild
        gm_ids = await get_gm_ids(interaction.guild)
        for gm_id in gm_ids:
            if str(gm_id) not in self.allowed_ids:
                self.allowed_ids.append(str(gm_id))
            
        # Normal interaction check for fully initialized view
        return str(interaction.user.id) in self.allowed_ids

    async def handle_end_turn(self, interaction):
        """Handle the end turn button press"""
        self.initiative.advance_turn()
        repositories.initiative.update_initiative_state(str(self.guild_id), str(self.channel_id), self.initiative)
        embed, content = await self.create_initiative_content()
        new_view = GenericInitiativeView(self.guild_id, self.channel_id, self.initiative, self.message_id)
        await self.update_initiative_message(interaction, content=content, embed=embed, view=new_view)
        if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=False)

        
    async def handle_start_initiative(self, interaction):
        """Handle the start initiative button press"""
        self.initiative.is_started = True
        self.initiative.current_index = 0
        repositories.initiative.update_initiative_state(str(self.guild_id), str(self.channel_id), self.initiative)
        embed, content = await self.create_initiative_content()
        new_view = GenericInitiativeView(self.guild_id, self.channel_id, self.initiative, self.message_id)
        await self.update_initiative_message(interaction, content=content, embed=embed, view=new_view)
        if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=False)

    async def update_view(self, interaction: discord.Interaction):
        """Update the initiative pinned message with current state"""
        new_view = GenericInitiativeView(self.guild_id, self.channel_id, self.initiative, self.message_id)
        embed, content = await self.create_initiative_content()
        await self.update_initiative_message(interaction, content=content, embed=embed, view=new_view)
        if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=False)

    async def create_initiative_content(self):
        """Create the content for a generic initiative view"""
        return _build_generic_initiative_content(self.initiative)


class GenericInitiativeViewV2(BasePinnedInitiativeViewV2):
    """Components v2 generic initiative tracker."""

    def __init__(self, guild_id=None, channel_id=None, initiative: GenericInitiative = None, message_id=None, status_message: str = None):
        super().__init__(guild_id, channel_id, initiative, message_id, status_message=status_message)

        if not self.is_initialized:
            row = ui.ActionRow()
            row.add_item(StartInitiativeButton(self))
            row.add_item(EndTurnButton(self))
            row.add_item(SetOrderButton(self))
            self.add_item(row)

    def build_action_rows(self) -> list[ui.ActionRow]:
        row = ui.ActionRow()
        if not self.initiative or not self.initiative.is_started:
            row.add_item(SetOrderButton(self))
            row.add_item(StartInitiativeButton(self))
        else:
            row.add_item(EndTurnButton(self))
        return [row]

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == interaction.client.user.id:
            return True

        if not self.is_initialized:
            if not await self.get_initiative_data(interaction):
                await interaction.response.send_message("❌ No active initiative in this channel.", ephemeral=True)
                return False

        component_id = interaction.data.get("custom_id", "")
        gm_ids = await get_gm_ids(interaction.guild)
        is_gm = str(interaction.user.id) in gm_ids

        current_participant = None
        if self.initiative and self.initiative.current:
            current_participant = next((p for p in self.initiative.participants if p.id == self.initiative.current), None)

        is_current_participant = (
            current_participant is not None and str(current_participant.owner_id) == str(interaction.user.id)
        )

        if component_id in {"start_initiative", "set_initiative_order"} and not is_gm:
            message = "❌ Only GMs can start initiative." if component_id == "start_initiative" else "❌ Only GMs can set the initiative order."
            await interaction.response.send_message(message, ephemeral=True)
            return False

        if component_id == "end_turn" and not (is_gm or is_current_participant):
            await interaction.response.send_message("❌ It's not your turn.", ephemeral=True)
            return False

        return True

    async def handle_end_turn(self, interaction):
        self.initiative.advance_turn()
        repositories.initiative.update_initiative_state(str(self.guild_id), str(self.channel_id), self.initiative)
        new_view = GenericInitiativeViewV2(self.guild_id, self.channel_id, self.initiative, self.message_id)
        embed, content = await self.create_initiative_content()
        await self.update_initiative_message(interaction, content=content, embed=embed, view=new_view)
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=False)

    async def handle_start_initiative(self, interaction):
        self.initiative.is_started = True
        self.initiative.current_index = 0
        repositories.initiative.update_initiative_state(str(self.guild_id), str(self.channel_id), self.initiative)
        new_view = GenericInitiativeViewV2(self.guild_id, self.channel_id, self.initiative, self.message_id)
        embed, content = await self.create_initiative_content()
        await self.update_initiative_message(interaction, content=content, embed=embed, view=new_view)
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=False)

    async def update_view(self, interaction: discord.Interaction):
        new_view = GenericInitiativeViewV2(self.guild_id, self.channel_id, self.initiative, self.message_id)
        embed, content = await self.create_initiative_content()
        await self.update_initiative_message(interaction, content=content, embed=embed, view=new_view)
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=False)

    async def create_initiative_content(self):
        return _build_generic_initiative_content(self.initiative)

class StartInitiativeButton(ui.Button):
    def __init__(self, parent_view: GenericInitiativeView):
        super().__init__(label="Start Initiative", style=discord.ButtonStyle.success, custom_id="start_initiative")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.handle_start_initiative(interaction)

class EndTurnButton(ui.Button):
    def __init__(self, parent_view: GenericInitiativeView):
        super().__init__(label="End Turn", style=discord.ButtonStyle.primary, custom_id="end_turn")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await self.parent_view.handle_end_turn(interaction)

class FirstPickerSelect(ui.Select):
    def __init__(self, options, parent_view: BasePinnedInitiativeView):
        super().__init__(placeholder="Pick who goes first...", min_values=1, max_values=1, options=options, custom_id="first_picker")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        first_id = self.values[0]
        initiative = self.parent_view.initiative
        # Set the first turn
        initiative.current = first_id
        initiative.remaining_in_round = [p.id for p in initiative.participants if p.id != first_id]
        # Save updated initiative state to DB
        repositories.initiative.update_initiative_state(str(self.parent_view.guild_id), str(self.parent_view.channel_id), initiative)
        await self.parent_view.update_view(interaction)

class PopcornNextSelect(ui.Select):
    def __init__(self, options, parent_view: BasePinnedInitiativeView):
        super().__init__(placeholder="Pick who goes next...", min_values=1, max_values=1, options=options, custom_id="next_picker")
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        next_id = self.values[0]
        initiative = self.parent_view.initiative
        initiative.advance_turn(next_id)
        repositories.initiative.update_initiative_state(str(self.parent_view.guild_id), str(self.parent_view.channel_id), initiative)
        await self.parent_view.update_view(interaction)

class EmptyPersistentSelect(ui.Select):
    """
    A select menu with no options, used for persistent view registration.
    This makes sure the custom_id is registered properly but doesn't need options.
    """
    def __init__(self, parent_view, custom_id, placeholder):
        # Create with an empty option that won't be displayed
        # Discord requires at least one option in a select menu
        super().__init__(
            placeholder=placeholder,
            min_values=1, 
            max_values=1,
            options=[SelectOption(label="Loading...", value="loading")],
            custom_id=custom_id
        )
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        # This shouldn't be called directly, but if it is, we'll handle it by refreshing the view
        await interaction.response.defer(ephemeral=True)
        
        if not self.parent_view.is_initialized:
            await self.parent_view.initialize_if_needed(interaction)
            
        # Create a new properly initialized view
        new_view = PopcornInitiativeView(
            guild_id=self.parent_view.guild_id,
            channel_id=self.parent_view.channel_id,
            initiative=self.parent_view.initiative,
            message_id=self.parent_view.message_id
        )
        
        # Get the new embed/content
        embed, content = await new_view.create_initiative_content()
        
        # Update the message with the properly initialized view
        message = await interaction.channel.fetch_message(int(self.parent_view.message_id))
        await message.edit(content=content, embed=embed, view=new_view)
        
        # Let the user know what happened
        await interaction.followup.send(
            "⚠️ The bot was restarted. The initiative view has been refreshed. Please make your selection now.",
            ephemeral=True
        )


class EmptyPersistentSelectV2(ui.Select):
    """Placeholder select used to register persistent Components v2 popcorn selectors."""

    def __init__(self, parent_view, custom_id, placeholder):
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=[SelectOption(label="Loading...", value="loading")],
            custom_id=custom_id
        )
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        if not await self.parent_view.initialize_if_needed(interaction):
            await interaction.followup.send("❌ No active initiative in this channel.", ephemeral=True)
            return

        new_view = PopcornInitiativeViewV2(
            guild_id=self.parent_view.guild_id,
            channel_id=self.parent_view.channel_id,
            initiative=self.parent_view.initiative,
            message_id=self.parent_view.message_id
        )

        try:
            await new_view.prepare_layout()
            message = await interaction.channel.fetch_message(int(self.parent_view.message_id))
            await message.edit(content=None, embed=None, view=new_view)
            await interaction.followup.send(
                "⚠️ The bot was restarted. The initiative view has been refreshed. Please make your selection now.",
                ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error refreshing LayoutView initiative after restart: {e}")
            await interaction.followup.send(
                "❌ Failed to refresh the initiative view. Please try again or restart initiative.",
                ephemeral=True
            )

class PopcornInitiativeView(BasePinnedInitiativeView):
    """
    Handles both the initial GM pick and the ongoing popcorn initiative.
    """
    def __init__(self, guild_id=None, channel_id=None, initiative=None, message_id=None):
        super().__init__(guild_id, channel_id, initiative, message_id)
        
        # Skip adding UI elements during persistent view registration or when not initialized
        if not self.is_initialized:
            # For persistent view registration, add a placeholder select menu without options
            # This ensures the component with the correct custom_id is registered
            self.add_item(EmptyPersistentSelect(self, "first_picker", "Pick who goes first..."))
            self.add_item(EmptyPersistentSelect(self, "next_picker", "Pick who goes next..."))
            return
        
        # Store the guild so we can fetch members with the GM role later
        self.guild = None
        self.allowed_ids = []  # Will be populated in initialize_if_needed
        
        # If there's a current participant, find their owner_id 
        if initiative.current:
            current_participant = next((p for p in initiative.participants 
                                      if p.id == initiative.current), None)
            if current_participant and current_participant.owner_id:
                self.allowed_ids.append(current_participant.owner_id)

        # If initiative.current is None, it's the first pick (GM chooses)
        if initiative.current is None:
            unique_participants = {}
            for p in initiative.participants:
                unique_participants[p.id] = p
            options = [SelectOption(label=p.name, value=p.id) for p in unique_participants.values()]
            self.add_item(FirstPickerSelect(options, self))
        else:
            options = []
            # If it's the end of the round, allow picking anyone (including yourself)
            if initiative.is_round_end():
                for p in initiative.participants:
                    options.append(SelectOption(label=p.name, value=p.id))
            else:
                for pid in initiative.remaining_in_round:
                    name = initiative.get_participant_name(pid)
                    options.append(SelectOption(label=name, value=pid))
            if options:
                self.add_item(PopcornNextSelect(options, self))

    async def initialize_if_needed(self, interaction):
        """Initialize view data if it wasn't loaded during construction"""
        if not self.is_initialized:
            success = await self.get_initiative_data(interaction)
            if not success:
                await interaction.response.send_message("❌ No active initiative in this channel.", ephemeral=True)
                return False
                
            # Set up allowed users
            self.guild = interaction.guild
            gm_ids = await get_gm_ids(interaction.guild)
            self.allowed_ids = list(gm_ids)
            
            if self.initiative.current:
                current_participant = next((p for p in self.initiative.participants 
                                          if p.id == self.initiative.current), None)
                if current_participant and current_participant.owner_id:
                    self.allowed_ids.append(current_participant.owner_id)
                    
            return True
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Only allow the current participant's owner or GM to interact
        if interaction.user.id == interaction.client.user.id:
            return True  # Allow the bot itself
            
        # Initialize if this is the first interaction after a restart
        if not self.is_initialized:
            if not await self.initialize_if_needed(interaction):
                return False
                
            # Create a new view with the loaded data and properly initialized components
            new_view = PopcornInitiativeView(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                initiative=self.initiative,
                message_id=self.message_id
            )
            
            # Check if the user is allowed to interact
            gm_ids = await get_gm_ids(interaction.guild)
            is_gm = str(interaction.user.id) in gm_ids
            is_current_participant = False
            
            if self.initiative.current:
                current_participant = next((p for p in self.initiative.participants 
                                          if p.id == self.initiative.current), None)
                is_current_participant = (current_participant and 
                                         str(current_participant.owner_id) == str(interaction.user.id))
            
            if not (is_gm or is_current_participant):
                await interaction.response.send_message("❌ It's not your turn or you're not a GM.", ephemeral=True)
                return False
            
            # Get the current embed/content to update the message
            embed, content = await new_view.create_initiative_content()
            
            try:
                # Use the actual message update here instead of trying to handle the select menu directly
                # This preserves correct options in the select menu
                message = await interaction.channel.fetch_message(int(self.message_id))
                await message.edit(content=content, embed=embed, view=new_view)
                
                # Let the user know that they need to select again with the proper menu
                await interaction.response.send_message(
                    "⚠️ The bot was restarted. The initiative view has been refreshed. Please make your selection again.",
                    ephemeral=True
                )
            except Exception as e:
                logging.error(f"Error updating initiative message after restart: {e}")
                await interaction.response.send_message(
                    "❌ Failed to update the initiative view. Please try again or restart initiative.",
                    ephemeral=True
                )
                
            return False
        
        # Add gms to allowed_ids if not already set
        self.guild = interaction.guild
        gm_ids = await get_gm_ids(interaction.guild)
        for gm_id in gm_ids:
            if str(gm_id) not in self.allowed_ids:
                self.allowed_ids.append(str(gm_id))
            
        # Normal interaction check for fully initialized view
        return str(interaction.user.id) in self.allowed_ids

    async def create_initiative_content(self):
        """Create the content for a popcorn initiative view"""
        embed = discord.Embed(
            title="📊 Popcorn Initiative",
            color=discord.Color.gold()
        )
        
        if not self.initiative:
            content = "🎲 **POPCORN INITIATIVE** 🎲\nInitiating..."
            embed.description = "Initiating..."
            return embed, content
            
        # Show round information
        embed.add_field(name="Round", value=str(self.initiative.round_number), inline=True)
        
        # Show the remaining participants
        if self.initiative.remaining_in_round:
            remaining_names = [self.initiative.get_participant_name(pid) for pid in self.initiative.remaining_in_round]
            embed.add_field(name="Remaining", value=", ".join(remaining_names), inline=True)
        
        current_participant = next((p for p in self.initiative.participants if p.id == self.initiative.current), None)
        mention = ""
        if current_participant and not current_participant.is_npc and current_participant.owner_id:
            mention = f"<@{current_participant.owner_id}>, it's your turn!"

        # Different content based on the initiative state
        if self.initiative.is_round_end():
            next_name = self.initiative.get_participant_name(self.initiative.current)
            content = f"🎲 **POPCORN INITIATIVE** 🎲"
            content += f"\n{mention}"
            embed.description = f"Current Turn: **{next_name}**\n\nEnd of the round\nUse the dropdown below to pick who goes next when your turn is complete."
        elif self.initiative.current:
            next_name = self.initiative.get_participant_name(self.initiative.current)
            content = f"🎲 **POPCORN INITIATIVE** 🎲"
            content += f"\n{mention}"
            embed.description = f"Current Turn: **{next_name}**\n\nUse the dropdown below to pick who goes next when your turn is complete."
        else:
            content = "🎲 **POPCORN INITIATIVE** 🎲"
            embed.description = "GM: pick who goes first."
            
        # Add all participants
        participants_list = "\n".join([
            f"{p.name}" + (" ◀️" if p.id == self.initiative.current else "") 
            for p in self.initiative.participants
        ])
        embed.add_field(name="Participants", value=participants_list or "No participants", inline=False)
        
        return embed, content

    async def update_view(self, interaction: discord.Interaction):
        """Update the initiative pinned message with current state"""
        new_view = PopcornInitiativeView(self.guild_id, self.channel_id, self.initiative, self.message_id)
        embed, content = await self.create_initiative_content()
        await self.update_initiative_message(interaction, content=content, embed=embed, view=new_view)
        if not interaction.response.is_done():
                await interaction.response.defer(ephemeral=True, thinking=False)


class PopcornInitiativeViewV2(BasePinnedInitiativeViewV2):
    """Components v2 popcorn initiative tracker."""

    def __init__(self, guild_id=None, channel_id=None, initiative=None, message_id=None, status_message: str = None):
        super().__init__(guild_id, channel_id, initiative, message_id, status_message=status_message)

        if not self.is_initialized:
            first_row = ui.ActionRow()
            first_row.add_item(EmptyPersistentSelectV2(self, "first_picker", "Pick who goes first..."))
            self.add_item(first_row)

            next_row = ui.ActionRow()
            next_row.add_item(EmptyPersistentSelectV2(self, "next_picker", "Pick who goes next..."))
            self.add_item(next_row)

    def build_action_rows(self) -> list[ui.ActionRow]:
        if not self.initiative:
            return []

        if self.initiative.current is None:
            unique_participants = {}
            for participant in self.initiative.participants:
                unique_participants[participant.id] = participant

            options = [SelectOption(label=participant.name, value=participant.id) for participant in unique_participants.values()]
            if not options:
                return []

            row = ui.ActionRow()
            row.add_item(FirstPickerSelect(options, self))
            return [row]

        options = []
        if self.initiative.is_round_end():
            for participant in self.initiative.participants:
                options.append(SelectOption(label=participant.name, value=participant.id))
        else:
            for participant_id in self.initiative.remaining_in_round:
                name = self.initiative.get_participant_name(participant_id)
                options.append(SelectOption(label=name, value=participant_id))

        if not options:
            return []

        row = ui.ActionRow()
        row.add_item(PopcornNextSelect(options, self))
        return [row]

    async def initialize_if_needed(self, interaction):
        if not self.is_initialized:
            if not await self.get_initiative_data(interaction):
                return False
        return True

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == interaction.client.user.id:
            return True

        was_initialized = self.is_initialized
        if not await self.initialize_if_needed(interaction):
            await interaction.response.send_message("❌ No active initiative in this channel.", ephemeral=True)
            return False

        gm_ids = await get_gm_ids(interaction.guild)
        is_gm = str(interaction.user.id) in gm_ids

        current_participant = None
        if self.initiative and self.initiative.current:
            current_participant = next((p for p in self.initiative.participants if p.id == self.initiative.current), None)

        is_current_participant = (
            current_participant is not None and str(current_participant.owner_id) == str(interaction.user.id)
        )

        if interaction.message and not self.message_id:
            self.message_id = str(interaction.message.id)

        if not was_initialized:
            if self.initiative.current is None:
                if not is_gm:
                    await interaction.response.send_message("❌ Only GMs can pick who goes first.", ephemeral=True)
                    return False
            elif not (is_gm or is_current_participant):
                await interaction.response.send_message("❌ It's not your turn or you're not a GM.", ephemeral=True)
                return False

            refreshed_view = PopcornInitiativeViewV2(
                guild_id=self.guild_id,
                channel_id=self.channel_id,
                initiative=self.initiative,
                message_id=self.message_id
            )

            try:
                await refreshed_view.prepare_layout()
                message = await interaction.channel.fetch_message(int(self.message_id))
                await message.edit(content=None, embed=None, view=refreshed_view)
                await interaction.response.send_message(
                    "⚠️ The bot was restarted. The initiative view has been refreshed. Please make your selection again.",
                    ephemeral=True
                )
            except Exception as e:
                logging.error(f"Error updating LayoutView initiative after restart: {e}")
                await interaction.response.send_message(
                    "❌ Failed to update the initiative view. Please try again or restart initiative.",
                    ephemeral=True
                )
            return False

        if self.initiative.current is None:
            if not is_gm:
                await interaction.response.send_message("❌ Only GMs can pick who goes first.", ephemeral=True)
                return False
            return True

        if not (is_gm or is_current_participant):
            await interaction.response.send_message("❌ It's not your turn or you're not a GM.", ephemeral=True)
            return False

        return True

    async def create_initiative_content(self):
        return _build_popcorn_initiative_content(self.initiative)

    async def update_view(self, interaction: discord.Interaction):
        new_view = PopcornInitiativeViewV2(self.guild_id, self.channel_id, self.initiative, self.message_id)
        embed, content = await self.create_initiative_content()
        await self.update_initiative_message(interaction, content=content, embed=embed, view=new_view)
        if not interaction.response.is_done():
            await interaction.response.defer(ephemeral=True, thinking=False)

class SetOrderButton(ui.Button):
    def __init__(self, parent_view: GenericInitiativeView):
        super().__init__(label="Set Order", style=discord.ButtonStyle.secondary, custom_id="set_initiative_order", row=1)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if the user is a GM
        gm_role_id = repositories.server.get_gm_role_id(str(interaction.guild.id))
        is_gm = False
        if gm_role_id:
            gm_role = interaction.guild.get_role(int(gm_role_id))
            if gm_role and gm_role in interaction.user.roles:
                is_gm = True
        
        if not is_gm:
            await interaction.response.send_message("❌ Only GMs can set the initiative order.", ephemeral=True)
            return
            
        # Get current participant names to populate the default value
        current_order = ", ".join([p.name for p in self.parent_view.initiative.participants])
        
        # Open modal for setting order
        await interaction.response.send_modal(SetInitiativeOrderModal(self.parent_view, current_order))

class SetInitiativeOrderModal(discord.ui.Modal, title="Set Initiative Order"):
    def __init__(self, parent_view, current_order: str):
        super().__init__()
        self.parent_view = parent_view
        
        # Create a text input field pre-filled with the current order
        self.order_input = discord.ui.TextInput(
            label="Enter initiative order (comma-separated)",
            placeholder="e.g. Bob, Alice, Charlie, Dave",
            default=current_order,
            style=discord.TextStyle.paragraph,
            required=True
        )
        self.add_item(self.order_input)

    async def on_submit(self, interaction: discord.Interaction):
        order_text = self.order_input.value
        names = [name.strip() for name in order_text.split(",") if name.strip()]
        
        if not names:
            await interaction.response.send_message("❌ Please provide a comma-separated list of names.", ephemeral=True)
            return

        # Map names to participants
        name_to_participant = {p.name.lower(): p for p in self.parent_view.initiative.participants}
        new_order = []
        invalid_names = []
        
        for name in names:
            p = name_to_participant.get(name.lower())
            if p:
                new_order.append(p)
            else:
                invalid_names.append(name)
                
        if invalid_names:
            await interaction.response.send_message(
                f"❌ The following names were not found among current participants: {', '.join(invalid_names)}",
                ephemeral=True
            )
            return
            
        # Make sure we didn't miss any participants
        if len(new_order) != len(self.parent_view.initiative.participants):
            # Find missing participants
            included_names = {p.name.lower() for p in new_order}
            missing_names = [p.name for p in self.parent_view.initiative.participants 
                            if p.name.lower() not in included_names]
            
            await interaction.response.send_message(
                f"⚠️ Warning: Some participants were not included in your order: {', '.join(missing_names)}. "
                "Please include all participants in your order.",
                ephemeral=True
            )
            return

        # Set the new order
        self.parent_view.initiative.participants = new_order
        
        # Reset current_index to 0 if initiative hasn't started yet
        if not self.parent_view.initiative.is_started:
            self.parent_view.initiative.current_index = 0
            
        # Save to database
        repositories.initiative.update_initiative_state(
            str(self.parent_view.guild_id), 
            str(self.parent_view.channel_id), 
            self.parent_view.initiative
        )
        
        # Update the view
        if isinstance(self.parent_view, ui.LayoutView):
            new_view = GenericInitiativeViewV2(
                self.parent_view.guild_id,
                self.parent_view.channel_id,
                self.parent_view.initiative,
                self.parent_view.message_id
            )
        else:
            new_view = GenericInitiativeView(
                self.parent_view.guild_id,
                self.parent_view.channel_id,
                self.parent_view.initiative,
                self.parent_view.message_id
            )
        
        # Create content for the updated view
        embed, content = await new_view.create_initiative_content()
        
        # Update the message
        await self.parent_view.update_initiative_message(
            interaction, 
            content=content, 
            embed=embed, 
            view=new_view
        )

        confirmation = "✅ Initiative order set to " + ", ".join([p.name for p in new_order])
        if not interaction.response.is_done():
            await interaction.response.send_message(confirmation, ephemeral=False)
        else:
            await interaction.followup.send(confirmation, ephemeral=False)