from abc import ABC, abstractmethod
import logging
import discord
from discord import ui, SelectOption
from core.initiative_types import GenericInitiative, PopcornInitiative
from core.base_models import BaseInitiative
from data.repositories.repository_factory import repositories

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
        embed = discord.Embed(
            title="📊 Initiative Tracker",
            color=discord.Color.blue()
        )
        
        # Add fields to the embed based on initiative state
        if not self.initiative or not self.initiative.is_started:
            content = "🎲 **INITIATIVE TRACKING** 🎲\nPress Start Initiative to begin."
            embed.description = "Press Start Initiative to begin."
            embed.description += "\n\nCurrent Initiative Order: {" + ", ".join([p.name for p in self.initiative.participants]) + "}" if self.initiative and self.initiative.participants else ""
            
        elif not self.initiative.participants:
            content = "🎲 **INITIATIVE TRACKING** 🎲\nNo participants in initiative."
            embed.description = "No participants in initiative."
            
        else:
            current_name = self.initiative.get_participant_name(self.initiative.current)

            content = f"🎲 **INITIATIVE TRACKING** 🎲\n\n🔔 It's now **{current_name}**'s turn! (Round {self.initiative.round_number})"

            # Add round information
            embed.add_field(name="Round", value=str(self.initiative.round_number), inline=True)
            embed.add_field(name="Current Turn", value=current_name, inline=True)
            
            # Add the initiative order to the embed
            order_text = "\n".join([
                f"{i+1}. {p.name}" + (" ◀️" if p.id == self.initiative.current else "") 
                for i, p in enumerate(self.initiative.participants)
            ])
            embed.add_field(name="Initiative Order", value=order_text or "No participants", inline=False)
            
        return embed, content

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
    def __init__(self, parent_view: GenericInitiativeView, current_order: str):
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

        await interaction.response.send_message(
            "✅ Initiative order set to " + ", ".join([p.name for p in new_order]),
            ephemeral=False
        )