import discord
from discord import ui, SelectOption
from core.inventory_views import EditInventoryView, EditInventoryViewV2
from core.shared_views import PaginatedSelectView, PaginatedSelectViewV2, EditNameModal, EditNotesModal, embed_to_text
from rpg_systems.fate.aspect import Aspect
from rpg_systems.fate.fate_character import FateCharacter, get_character, SYSTEM
from data.repositories.repository_factory import repositories
from rpg_systems.fate.consequence_track import ConsequenceTrack, Consequence
from rpg_systems.fate.stress_track import StressBox, StressTrack


def _truncate_text(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _add_action_button(action_row: ui.ActionRow, label: str, style: discord.ButtonStyle, callback):
    button = ui.Button(label=label, style=style)
    button.callback = callback
    action_row.add_item(button)
    return button

class FateSheetEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Stress", style=discord.ButtonStyle.primary, row=1)
    async def edit_stress(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing stress tracks:", view=EditStressTracksView(interaction.guild.id, self.editor_id, self.char_id, 0))

    @ui.button(label="Edit Consequences", style=discord.ButtonStyle.primary, row=1)
    async def edit_consequences(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing consequences:", view=EditConsequencesView(interaction.guild.id, self.editor_id, self.char_id))

    @ui.button(label="Edit Fate Points/Refresh", style=discord.ButtonStyle.primary, row=1)
    async def edit_fate_points(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditFatePointsModal(self.char_id))

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=2)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNameModal(self.char_id, SYSTEM))

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=2)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNotesModal(self.char_id, SYSTEM))

    @ui.button(label="Edit Aspects", style=discord.ButtonStyle.secondary, row=2)
    async def edit_aspects(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing aspects:", view=EditAspectsView(interaction.guild.id, self.editor_id, self.char_id))

    @ui.button(label="Edit Skills", style=discord.ButtonStyle.secondary, row=2)
    async def edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(self.char_id)
        
        # Create a view with buttons for different skill operations
        view = SkillManagementView(character, self.editor_id, self.char_id)
        await interaction.response.send_message(
            "Choose how you want to manage skills:",
            view=view,
            ephemeral=True
        )

    @ui.button(label="Edit Stunts", style=discord.ButtonStyle.secondary, row=2)
    async def edit_stunts(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing stunts:", view=EditStuntsView(interaction.guild.id, self.editor_id, self.char_id))

    @ui.button(label="Inventory", style=discord.ButtonStyle.secondary, row=3)
    async def edit_inventory(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing inventory:", view=EditInventoryView(interaction.guild.id, self.editor_id, self.char_id))

class EditAspectsView(ui.View):
    def __init__(self, guild_id: int, user_id: int, char_id: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.page = 0

        self.char = None
        self.aspects = []
        self.max_page = 0
        self.load_data()
        self.render()

    def load_data(self):
        self.char = get_character(self.char_id)
        if not self.char:
            self.aspects = []
        else:
            self.aspects = self.char.aspects
        self.max_page = max(0, len(self.aspects) - 1)

    def render(self):
        self.clear_items()
        if self.aspects:
            current_aspect = self.aspects[self.page]
            aspect_name = current_aspect.name
            is_hidden = current_aspect.is_hidden
            
            label = f"{self.page + 1}/{len(self.aspects)}: {aspect_name[:30]}"
            self.add_item(ui.Button(label=label, disabled=True, row=0))
            
            # Add view description button if there is a description
            if current_aspect.description:  # Changed from description key access
                self.add_item(ui.Button(label="📖 View Description", style=discord.ButtonStyle.primary, row=0, custom_id="view_desc"))
            
            # Navigation buttons
            if self.page > 0:
                self.add_item(ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, row=1, custom_id="prev"))
            if self.page < self.max_page:
                self.add_item(ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, row=1, custom_id="next"))
            
            # Action buttons
            self.add_item(ui.Button(label="✏️ Edit", style=discord.ButtonStyle.primary, row=2, custom_id="edit"))
            self.add_item(ui.Button(label="🗑 Remove", style=discord.ButtonStyle.danger, row=2, custom_id="remove"))
            
            # Visibility toggle
            toggle_label = "🙈 Hide" if not is_hidden else "👁 Unhide"
            toggle_style = discord.ButtonStyle.secondary if not is_hidden else discord.ButtonStyle.success
            self.add_item(ui.Button(label=toggle_label, style=toggle_style, row=2, custom_id="toggle_hidden"))
        
        # Add aspect button and done button
        self.add_item(ui.Button(label="➕ Add New", style=discord.ButtonStyle.success, row=3, custom_id="add"))
        self.add_item(ui.Button(label="✅ Done", style=discord.ButtonStyle.secondary, row=3, custom_id="done_aspects"))
        
        # Assign callbacks
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id:
                item.callback = self.make_callback(item.custom_id)

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't edit this character.", ephemeral=True)
                return

            self.char = get_character(self.char_id)
            self.aspects = self.char.aspects

            if cid == "prev":
                self.page = max(0, self.page - 1)
            elif cid == "next":
                self.page = min(self.max_page, self.page + 1)
            elif cid == "view_desc":
                current_aspect = self.aspects[self.page]
                name = current_aspect.name
                description = current_aspect.description
                await interaction.response.send_message(
                    f"**{name}**\n{description}", 
                    ephemeral=True
                )
                return
            elif cid == "edit":
                await interaction.response.send_modal(EditAspectModal(self.char_id, self.page, self.aspects[self.page]))
                return
            elif cid == "remove":
                del self.aspects[self.page]
                self.char.aspects = self.aspects
                repositories.entity.upsert_entity(interaction.guild.id, self.char, system=SYSTEM)
                self.page = max(0, self.page - 1)
            elif cid == "toggle_hidden":
                current_aspect = self.aspects[self.page]
                current_aspect.is_hidden = not current_aspect.is_hidden
                self.char.aspects = self.aspects
                repositories.entity.upsert_entity(interaction.guild.id, self.char, system=SYSTEM)
            elif cid == "add":
                await interaction.response.send_modal(AddAspectModal(self.char_id))
                return
            elif cid == "done_aspects":
                await interaction.response.edit_message(
                    content="✅ Done editing aspects.", 
                    embed=self.char.format_full_sheet(interaction.guild.id), 
                    view=FateSheetEditView(interaction.user.id, self.char_id)
                )
                return

            # Save changes and update view
            repositories.entity.upsert_entity(interaction.guild.id, self.char, system=SYSTEM)
            self.load_data()
            self.render()
            await interaction.response.edit_message(embed=self.char.format_full_sheet(interaction.guild.id), view=self)
        
        return callback
    
class EditStressTracksView(ui.View):
    def __init__(self, guild_id: int, user_id: int, char_id: str, track_index: int):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.current_track_index = track_index
        
        self.char = get_character(self.char_id)
        self.stress_tracks = self.char.stress_tracks if self.char else []
        
        self.render()

    def render(self):
        self.clear_items()
        
        if not self.stress_tracks:
            self.add_item(ui.Button(label="No stress tracks available", disabled=True, row=0))
        else:
            # Track selector dropdown
            track_options = [SelectOption(label=track.track_name, value=str(i)) for i, track in enumerate(self.stress_tracks)]
            select = ui.Select(placeholder="Select stress track to edit...", options=track_options, custom_id="track_select")
            select.callback = self.track_selected
            self.add_item(select)
            
            if self.current_track_index < len(self.stress_tracks):
                track = self.stress_tracks[self.current_track_index]
                
                # Display current track status
                status_text = f"**{track.track_name}**"
                if track.linked_skill:
                    status_text += f" (linked to {track.linked_skill})"
                self.add_item(ui.Button(label=status_text, disabled=True, row=1))
                
                # Box editing buttons - limit to 5 to stay within Discord's button limits
                for i, box in enumerate(track.boxes):
                    if i >= 5:  # Limit to prevent Discord button limit
                        break
                    status = "☒" if box.is_filled else "☐"
                    button = ui.Button(
                        label=f"{status}[{box.value}]",
                        style=discord.ButtonStyle.success if box.is_filled else discord.ButtonStyle.secondary,
                        row=2,
                        custom_id=f"box_{i}"
                    )
                    button.callback = self.make_box_callback(i)
                    self.add_item(button)
                
                # Management buttons row
                self.add_item(ui.Button(label="➕ Add Box", style=discord.ButtonStyle.success, row=3, custom_id="add_box"))
                self.add_item(ui.Button(label="🗑 Remove Box", style=discord.ButtonStyle.danger, row=3, custom_id="remove_box"))
                self.add_item(ui.Button(label="Clear All", style=discord.ButtonStyle.danger, row=3, custom_id="clear_all"))
        
        # Add New Track button (always available)
        self.add_item(ui.Button(label="➕ Add New Track", style=discord.ButtonStyle.primary, row=4, custom_id="add_track"))
        
        # Done button
        self.add_item(ui.Button(label="✅ Done", style=discord.ButtonStyle.secondary, row=4, custom_id="done_stress_tracks"))
        
        # Assign callbacks for non-box buttons
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id in ["add_box", "remove_box", "clear_all", "add_track", "done_stress_tracks"]:
                item.callback = self.make_callback(item.custom_id)

    async def track_selected(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return
        
        self.current_track_index = int(interaction.data['values'][0])
        self.render()
        await interaction.response.edit_message(view=self)

    def make_box_callback(self, box_index):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't edit this character.", ephemeral=True)
                return
            
            # Toggle the box state
            track = self.stress_tracks[self.current_track_index]
            if box_index < len(track.boxes):
                track.boxes[box_index].is_filled = not track.boxes[box_index].is_filled
                
                # Update character
                self.char.stress_tracks = self.stress_tracks
                repositories.entity.upsert_entity(interaction.guild.id, self.char, system=SYSTEM)
                
                self.render()
                await interaction.response.edit_message(view=self)
        
        return callback

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't edit this character.", ephemeral=True)
                return

            if cid == "add_box" and self.current_track_index < len(self.stress_tracks):
                await interaction.response.send_modal(AddStressBoxModal(self.char_id, self.current_track_index))
                return
            elif cid == "remove_box" and self.current_track_index < len(self.stress_tracks):
                await interaction.response.send_modal(RemoveStressBoxModal(self.char_id, self.current_track_index))
                return
            elif cid == "clear_all" and self.current_track_index < len(self.stress_tracks):
                track = self.stress_tracks[self.current_track_index]
                track.clear_all_boxes()
                self.char.stress_tracks = self.stress_tracks
                repositories.entity.upsert_entity(interaction.guild.id, self.char, system=SYSTEM)
                self.render()
                await interaction.response.edit_message(view=self)
            elif cid == "add_track":
                await interaction.response.send_modal(AddStressTrackModal(self.char_id))
                return
            elif cid == "done_stress_tracks":
                await interaction.response.edit_message(
                    content="✅ Done editing stress tracks.", 
                    embed=self.char.format_full_sheet(interaction.guild.id), 
                    view=FateSheetEditView(interaction.user.id, self.char_id)
                )
        
        return callback

class RemoveStressBoxModal(ui.Modal, title="Remove Stress Box"):
    def __init__(self, char_id: str, track_index: int, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.track_index = track_index
        self.guild_id = guild_id
        
        # Get current boxes to show available options
        character = get_character(char_id)
        track = character.stress_tracks[track_index] if track_index < len(character.stress_tracks) else None
        
        if track and track.boxes:
            box_options = ", ".join(f"{i+1}:[{box.value}]" for i, box in enumerate(track.boxes))
            placeholder_text = f"Available boxes: {box_options}"
        else:
            placeholder_text = "No boxes available to remove"
        
        self.box_number_field = ui.TextInput(
            label="Box number to remove (1, 2, 3, etc.)",
            placeholder=placeholder_text,
            required=True,
            max_length=2
        )
        self.add_item(self.box_number_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        stress_tracks = character.stress_tracks
        
        if self.track_index >= len(stress_tracks):
            await interaction.response.send_message("❌ Stress track not found.", ephemeral=True)
            return
        
        track = stress_tracks[self.track_index]
        
        try:
            box_number = int(self.box_number_field.value.strip())
            box_index = box_number - 1  # Convert to 0-based index
            
            if box_index < 0 or box_index >= len(track.boxes):
                await interaction.response.send_message(f"❌ Invalid box number. Must be between 1 and {len(track.boxes)}.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
            return
        
        # Remove the stress box from the track
        removed_box = track.boxes.pop(box_index)

        if not track.boxes:
            stress_tracks.remove(track)

        # Save changes
        character.stress_tracks = stress_tracks
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditStressTracksViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    track_index=self.track_index,
                    status_message=f"✅ Removed stress box with value {removed_box.value} from {track.track_name}."
                )
            )
        else:
            await interaction.response.edit_message(
                content=f"✅ Removed stress box with value {removed_box.value} from {track.track_name}.", 
                view=EditStressTracksView(interaction.guild.id, interaction.user.id, self.char_id, self.track_index)
            )

class AddStressBoxModal(ui.Modal, title="Add Stress Box"):
    def __init__(self, char_id: str, track_index: int, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.track_index = track_index
        self.guild_id = guild_id
        
        self.value_field = ui.TextInput(
            label="Stress Box Value (1-10)",
            placeholder="Enter the value for the new stress box",
            required=True,
            max_length=2
        )
        self.add_item(self.value_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        stress_tracks = character.stress_tracks
        
        if self.track_index >= len(stress_tracks):
            await interaction.response.send_message("❌ Stress track not found.", ephemeral=True)
            return
        
        try:
            value = int(self.value_field.value.strip())
            if value < 1 or value > 10:
                await interaction.response.send_message("❌ Stress box value must be between 1 and 10.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
            return
        
        # Add the new stress box to the track
        track = stress_tracks[self.track_index]
        track.add_box(value, is_filled=False)
        
        # Save changes
        character.stress_tracks = stress_tracks
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditStressTracksViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    track_index=self.track_index,
                    status_message=f"✅ Added stress box with value {value} to {track.track_name}."
                )
            )
        else:
            await interaction.response.edit_message(
                content=f"✅ Added stress box with value {value} to {track.track_name}.", 
                view=EditStressTracksView(interaction.guild.id, interaction.user.id, self.char_id, self.track_index)
            )

class AddStressTrackModal(ui.Modal, title="Add New Stress Track"):
    def __init__(self, char_id: str, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id
        
        self.track_name_field = ui.TextInput(
            label="Track Name",
            placeholder="e.g. Physical, Mental, Social",
            required=True,
            max_length=50
        )
        self.add_item(self.track_name_field)
        
        self.linked_skill_field = ui.TextInput(
            label="Linked Skill (optional)",
            placeholder="e.g. Physique, Will, Rapport",
            required=False,
            max_length=50
        )
        self.add_item(self.linked_skill_field)
        
        self.num_boxes_field = ui.TextInput(
            label="Number of Boxes (1-6)",
            default="2",
            required=True,
            max_length=1
        )
        self.add_item(self.num_boxes_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        stress_tracks = character.stress_tracks
        
        track_name = self.track_name_field.value.strip()
        linked_skill = self.linked_skill_field.value.strip() or None
        
        if not track_name:
            await interaction.response.send_message("❌ Track name cannot be empty.", ephemeral=True)
            return
        
        # Check if track name already exists
        if any(track.track_name.lower() == track_name.lower() for track in stress_tracks):
            await interaction.response.send_message(f"❌ A stress track named '{track_name}' already exists.", ephemeral=True)
            return
        
        try:
            num_boxes = int(self.num_boxes_field.value.strip())
            if num_boxes < 1 or num_boxes > 6:
                await interaction.response.send_message("❌ Number of boxes must be between 1 and 6.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number for boxes.", ephemeral=True)
            return
        
        # Create boxes for the new track
        boxes = [StressBox(value=i + 1, is_filled=False) for i in range(num_boxes)]
        
        # Create the new stress track
        new_track = StressTrack(track_name=track_name, boxes=boxes, linked_skill=linked_skill)
        stress_tracks.append(new_track)
        
        # Save changes
        character.stress_tracks = stress_tracks
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditStressTracksViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    track_index=len(character.stress_tracks) - 1,
                    status_message=f"✅ Added new stress track: '{track_name}' with {num_boxes} boxes."
                )
            )
        else:
            await interaction.response.edit_message(
                content=f"✅ Added new stress track: '{track_name}' with {num_boxes} boxes.", 
                view=EditStressTracksView(interaction.guild.id, interaction.user.id, self.char_id, len(character.stress_tracks) - 1)
            )

class EditConsequencesView(ui.View):
    def __init__(self, guild_id: int, user_id: int, char_id: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.track_index = 0
        self.consequence_index = 0

        self.char = get_character(self.char_id)
        self.consequence_tracks = self.char.consequence_tracks if self.char else []
        
        # Find first available consequence or default to 0
        self.current_consequence = None
        if self.consequence_tracks and self.consequence_tracks[0].consequences:
            self.current_consequence = self.consequence_tracks[0].consequences[0]
        
        self.render()

    def render(self):
        self.clear_items()
        
        if not self.consequence_tracks or not any(track.consequences for track in self.consequence_tracks):
            self.add_item(ui.Button(label="No consequences available", disabled=True, row=0))
        else:
            # Get all consequences from all tracks for navigation
            all_consequences = []
            for track_idx, track in enumerate(self.consequence_tracks):
                for cons_idx, consequence in enumerate(track.consequences):
                    all_consequences.append((track_idx, cons_idx, consequence))
            
            if all_consequences:
                # Find current position in the flat list
                current_pos = 0
                for i, (t_idx, c_idx, cons) in enumerate(all_consequences):
                    if t_idx == self.track_index and c_idx == self.consequence_index:
                        current_pos = i
                        break
                
                current_consequence = all_consequences[current_pos][2]
                
                # Display current consequence info
                if current_consequence.aspect:
                    label = f"{current_pos + 1}/{len(all_consequences)}: {current_consequence.name} - {current_consequence.aspect.name[:20]}"
                else:
                    label = f"{current_pos + 1}/{len(all_consequences)}: {current_consequence.name} - Empty"
                
                self.add_item(ui.Button(label=label[:80], disabled=True, row=0))
                
                # Navigation buttons
                if current_pos > 0:
                    self.add_item(ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, row=1, custom_id="prev"))
                if current_pos < len(all_consequences) - 1:
                    self.add_item(ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, row=1, custom_id="next"))
                
                # Action buttons
                self.add_item(ui.Button(label="✏️ Edit", style=discord.ButtonStyle.primary, row=2, custom_id="edit"))
                if current_consequence.aspect:
                    self.add_item(ui.Button(label="🗑 Clear", style=discord.ButtonStyle.danger, row=2, custom_id="clear"))
        
        # Add New Track button (always available)
        self.add_item(ui.Button(label="➕ Add New Track", style=discord.ButtonStyle.primary, row=3, custom_id="add_track"))
        
        # Done button
        self.add_item(ui.Button(label="✅ Done", style=discord.ButtonStyle.secondary, row=3, custom_id="done_consequences"))
        
        # Assign callbacks
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id:
                item.callback = self.make_callback(item.custom_id)

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't edit this character.", ephemeral=True)
                return

            # Refresh data
            self.char = get_character(self.char_id)
            self.consequence_tracks = self.char.consequence_tracks

            # Get all consequences for navigation
            all_consequences = []
            for track_idx, track in enumerate(self.consequence_tracks):
                for cons_idx, consequence in enumerate(track.consequences):
                    all_consequences.append((track_idx, cons_idx, consequence))

            if not all_consequences and cid not in ["add_track", "done_consequences"]:
                await interaction.response.edit_message(
                    content="✅ Done editing consequences.", 
                    embed=self.char.format_full_sheet(interaction.guild.id), 
                    view=FateSheetEditView(interaction.user.id, self.char_id)
                )
                return

            # Find current position
            current_pos = 0
            for i, (t_idx, c_idx, cons) in enumerate(all_consequences):
                if t_idx == self.track_index and c_idx == self.consequence_index:
                    current_pos = i
                    break

            if cid == "prev":
                current_pos = max(0, current_pos - 1)
                self.track_index, self.consequence_index, _ = all_consequences[current_pos]
            elif cid == "next":
                current_pos = min(len(all_consequences) - 1, current_pos + 1)
                self.track_index, self.consequence_index, _ = all_consequences[current_pos]
            elif cid == "edit":
                current_consequence = all_consequences[current_pos][2]
                await interaction.response.send_modal(
                    EditConsequenceModal(self.char_id, self.track_index, self.consequence_index, current_consequence)
                )
                return
            elif cid == "clear":
                # Clear the consequence aspect
                current_consequence = all_consequences[current_pos][2]
                current_consequence.aspect = None
                self.char.consequence_tracks = self.consequence_tracks
                repositories.entity.upsert_entity(interaction.guild.id, self.char, system=SYSTEM)
            elif cid == "add_track":
                await interaction.response.send_modal(AddConsequenceTrackModal(self.char_id))
                return
            elif cid == "done_consequences":
                await interaction.response.edit_message(
                    content="✅ Done editing consequences.", 
                    embed=self.char.format_full_sheet(interaction.guild.id), 
                    view=FateSheetEditView(interaction.user.id, self.char_id)
                )
                return

            # Update view for non-modal actions
            self.render()
            await interaction.response.edit_message(view=self)
        
        return callback

class EditConsequenceModal(ui.Modal, title="Edit Consequence"):
    def __init__(self, char_id: str, track_index: int, consequence_index: int, consequence: Consequence, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.track_index = track_index
        self.consequence_index = consequence_index
        self.guild_id = guild_id
        
        # Aspect name field
        aspect_name = consequence.aspect.name if consequence.aspect else ""
        self.aspect_name_field = ui.TextInput(
            label=f"{consequence.name} ({consequence.severity}) Aspect",
            default=aspect_name,
            max_length=200,
            required=False,
            placeholder="Leave empty to clear consequence"
        )
        self.aspect_free_invokes_field = ui.TextInput(
            label=f"{consequence.name} ({consequence.severity}) Free Invokes",
            default=str(consequence.aspect.free_invokes) if consequence.aspect else "1",
            max_length=1,
            required=False,
            placeholder="Leave empty to clear invokes"
        )
        self.add_item(self.aspect_name_field)
        self.add_item(self.aspect_free_invokes_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        consequence_tracks = character.consequence_tracks
        
        if (self.track_index >= len(consequence_tracks) or 
            self.consequence_index >= len(consequence_tracks[self.track_index].consequences)):
            await interaction.response.send_message("❌ Consequence not found.", ephemeral=True)
            return
        
        aspect_name = self.aspect_name_field.value.strip()
        free_invokes = self.aspect_free_invokes_field.value.strip()
        consequence = consequence_tracks[self.track_index].consequences[self.consequence_index]
        
        if aspect_name:
            # Create or update the aspect
            try:
                free_invokes = int(free_invokes) if free_invokes else 0
                free_invokes = max(0, free_invokes)  # Ensure non-negative
            except ValueError:
                free_invokes = 0

            consequence.aspect = Aspect(
                name=aspect_name, 
                description="",
                is_hidden=False,
                free_invokes=free_invokes,
                attached_to_id=character.id if character else None
            )
        else:
            # Clear the consequence
            consequence.aspect = None
        
        # Save changes
        character.consequence_tracks = consequence_tracks
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditConsequencesViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    track_index=self.track_index,
                    consequence_index=self.consequence_index,
                    status_message="✅ Consequence updated."
                )
            )
        else:
            await interaction.response.edit_message(
                content="✅ Consequence updated.", 
                view=EditConsequencesView(interaction.guild.id, interaction.user.id, self.char_id)
            )

class AddConsequenceTrackModal(ui.Modal, title="Add New Consequence Track"):
    def __init__(self, char_id: str, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id
        
        self.track_name_field = ui.TextInput(
            label="Track Name",
            placeholder="e.g. Physical, Mental, Extra",
            required=True,
            max_length=50
        )
        self.add_item(self.track_name_field)
        
        self.consequences_field = ui.TextInput(
            label="Consequences (name:severity, comma-separated)",
            placeholder="e.g. Mild:2, Moderate:4, Severe:6",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=200
        )
        self.add_item(self.consequences_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        consequence_tracks = character.consequence_tracks
        
        track_name = self.track_name_field.value.strip()
        
        if not track_name:
            await interaction.response.send_message("❌ Track name cannot be empty.", ephemeral=True)
            return
        
        # Check if track name already exists
        if any(track.name.lower() == track_name.lower() for track in consequence_tracks):
            await interaction.response.send_message(f"❌ A consequence track named '{track_name}' already exists.", ephemeral=True)
            return
        
        # Parse consequences
        consequences = []
        try:
            consequence_entries = self.consequences_field.value.strip().split(',')
            for entry in consequence_entries:
                if ':' not in entry:
                    await interaction.response.send_message("❌ Each consequence must be in format 'name:severity'.", ephemeral=True)
                    return
                
                name, severity_str = entry.split(':', 1)
                name = name.strip()
                severity = int(severity_str.strip())
                
                if not name:
                    await interaction.response.send_message("❌ Consequence name cannot be empty.", ephemeral=True)
                    return
                
                if severity < 1 or severity > 10:
                    await interaction.response.send_message("❌ Consequence severity must be between 1 and 10.", ephemeral=True)
                    return
                
                consequences.append(Consequence(name=name, severity=severity, aspect=None))
        
        except ValueError:
            await interaction.response.send_message("❌ Invalid severity value. Must be a number.", ephemeral=True)
            return
        
        if not consequences:
            await interaction.response.send_message("❌ At least one consequence must be specified.", ephemeral=True)
            return
        
        # Create the new consequence track
        new_track = ConsequenceTrack(name=track_name, consequences=consequences)
        consequence_tracks.append(new_track)
        
        # Save changes
        character.consequence_tracks = consequence_tracks
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        consequence_names = [f"{cons.name}({cons.severity})" for cons in consequences]
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditConsequencesViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    track_index=len(consequence_tracks) - 1,
                    consequence_index=0,
                    status_message=f"✅ Added new consequence track: '{track_name}' with consequences: {', '.join(consequence_names)}"
                )
            )
        else:
            await interaction.response.edit_message(
                content=f"✅ Added new consequence track: '{track_name}' with consequences: {', '.join(consequence_names)}", 
                view=EditConsequencesView(interaction.guild.id, interaction.user.id, self.char_id)
            )

class EditStuntsView(ui.View):
    def __init__(self, guild_id: int, user_id: int, char_id: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.page = 0

        self.char = None
        self.stunts = {}
        self.stunt_names = []
        self.max_page = 0
        self.load_data()
        self.render()

    def load_data(self):
        self.char = get_character(self.char_id)
        if not self.char:
            self.stunts = {}
            self.stunt_names = []
        else:
            self.stunts = self.char.stunts
            self.stunt_names = list(self.stunts.keys())
        self.max_page = max(0, len(self.stunt_names) - 1)

    def render(self):
        self.clear_items()
        if self.stunt_names:
            current_stunt = self.stunt_names[self.page]
            label = f"{self.page + 1}/{len(self.stunt_names)}: {current_stunt[:30]}"
            self.add_item(ui.Button(label=label, disabled=True, row=0))
            
            # Description button to view full description
            self.add_item(ui.Button(label="📖 View Description", style=discord.ButtonStyle.primary, row=0, custom_id="view_desc"))
            
            if self.page > 0:
                self.add_item(ui.Button(label="◀️ Prev", style=discord.ButtonStyle.secondary, row=1, custom_id="prev"))
            if self.page < self.max_page:
                self.add_item(ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, row=1, custom_id="next"))
            
            self.add_item(ui.Button(label="✏️ Edit", style=discord.ButtonStyle.primary, row=2, custom_id="edit"))
            self.add_item(ui.Button(label="🗑 Remove", style=discord.ButtonStyle.danger, row=2, custom_id="remove"))
        
        self.add_item(ui.Button(label="➕ Add New", style=discord.ButtonStyle.success, row=3, custom_id="add"))
        self.add_item(ui.Button(label="✅ Done", style=discord.ButtonStyle.secondary, row=3, custom_id="done_stunts"))
        
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id:
                item.callback = self.make_callback(item.custom_id)

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't edit this character.", ephemeral=True)
                return

            self.char = get_character(self.char_id)
            self.stunts = self.char.stunts
            self.stunt_names = list(self.stunts.keys())

            if cid == "prev":
                self.page = max(0, self.page - 1)
            elif cid == "next":
                self.page = min(self.max_page, self.page + 1)
            elif cid == "view_desc":
                current_stunt = self.stunt_names[self.page]
                description = self.stunts.get(current_stunt, "No description available")
                await interaction.response.send_message(
                    f"**{current_stunt}**\n{description}", 
                    ephemeral=True
                )
                return
            elif cid == "edit":
                current_stunt = self.stunt_names[self.page]
                description = self.stunts.get(current_stunt, "")
                await interaction.response.send_modal(
                    EditStuntModal(self.char_id, current_stunt, description)
                )
                return
            elif cid == "remove":
                current_stunt = self.stunt_names[self.page]
                del self.stunts[current_stunt]
                self.char.stunts = self.stunts
                repositories.entity.upsert_entity(interaction.guild.id, self.char, system=SYSTEM)
                self.stunt_names.remove(current_stunt)
                self.max_page = max(0, len(self.stunt_names) - 1)
                self.page = min(self.page, self.max_page)
            elif cid == "add":
                await interaction.response.send_modal(AddStuntModal(self.char_id))
                return
            elif cid == "done_stunts":
                await interaction.response.edit_message(
                    content="✅ Done editing stunts.", 
                    embed=self.char.format_full_sheet(interaction.guild.id), 
                    view=FateSheetEditView(interaction.user.id, self.char_id)
                )
                return

            # Save changes and update view
            repositories.entity.upsert_entity(interaction.guild.id, self.char, system=SYSTEM)
            self.load_data()
            self.render()
            await interaction.response.edit_message(view=self)
            
        return callback

class SkillManagementView(ui.View):
    def __init__(self, character: FateCharacter, editor_id, char_id):
        super().__init__(timeout=120)
        self.character = character
        self.editor_id = editor_id
        self.char_id = char_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Existing Skill", style=discord.ButtonStyle.primary, row=0)
    async def edit_existing_skill(self, interaction: discord.Interaction, button: ui.Button):
        skills = self.character.skills if self.character.skills else {}
        if not skills:
            await interaction.response.edit_message(
                content="This character doesn't have any skills yet. Add some first!",
                view=None
            )
            return

        skill_options = [SelectOption(label=k, value=k) for k in sorted(skills.keys())]

        async def on_skill_selected(view, interaction2, skill):
            current_value = skills.get(skill, 0)
            await interaction2.response.send_modal(EditSkillValueModal(self.char_id, skill, current_value))

        await interaction.response.edit_message(
            content="Select a skill to edit:",
            view=PaginatedSelectView(
                skill_options, 
                on_skill_selected, 
                interaction.user.id, 
                prompt="Select a skill to edit:"
            )
        )

    @ui.button(label="Add New Skill", style=discord.ButtonStyle.success, row=0)
    async def add_new_skill(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(AddSkillModal(self.char_id))

    @ui.button(label="Remove Skill", style=discord.ButtonStyle.danger, row=0)
    async def remove_skill(self, interaction: discord.Interaction, button: ui.Button):
        skills = self.character.skills if self.character.skills else {}
        if not skills:
            await interaction.response.edit_message(
                content="This character doesn't have any skills to remove.",
                view=None
            )
            return

        skill_options = [SelectOption(label=k, value=k) for k in sorted(skills.keys())]

        async def on_skill_selected(view, interaction2: discord.Interaction, skill):
            # Remove the selected skill
            skills = self.character.skills
            if skill in skills:
                del skills[skill]
                self.character.skills = skills
                repositories.entity.upsert_entity(interaction2.guild.id, self.character, system=SYSTEM)
                embed = self.character.format_full_sheet(interaction2.guild.id)
                view = FateSheetEditView(interaction2.user.id, self.char_id)
                await interaction2.response.edit_message(
                    content=f"✅ Removed skill: **{skill}**",
                    embed=embed,
                    view=view
                )
            else:
                await interaction2.response.edit_message(
                    content=f"❌ Skill not found: {skill}",
                    view=None
                )

        await interaction.response.edit_message(
            content="Select a skill to remove:",
            view=PaginatedSelectView(
                skill_options, 
                on_skill_selected, 
                interaction.user.id, 
                prompt="Select a skill to remove:"
            )
        )

    @ui.button(label="Bulk Edit Skills", style=discord.ButtonStyle.secondary, row=1)
    async def bulk_edit_skills(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(BulkEditSkillsModal(self.char_id))

    @ui.button(label="Cancel", style=discord.ButtonStyle.secondary, row=1)
    async def cancel(self, interaction: discord.Interaction, button: ui.Button):
        character = get_character(self.char_id)
        embed = character.format_full_sheet(interaction.guild.id)
        view = FateSheetEditView(interaction.user.id, self.char_id)
        await interaction.response.edit_message(
            content="Operation cancelled.",
            embed=embed,
            view=view
        )

class EditAspectModal(ui.Modal, title="Edit Aspect"):
    def __init__(self, char_id: str, index: int, aspect: Aspect, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.index = index
        self.guild_id = guild_id
        
        self.name_field = ui.TextInput(
            label="Aspect Name",
            default=aspect.name,
            max_length=100,
            required=True
        )
        self.add_item(self.name_field)
        
        self.description_field = ui.TextInput(
            label="Description (optional)",
            default=aspect.description,
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.description_field)
        
        # Add free invokes field
        self.free_invokes_field = ui.TextInput(
            label="Free Invokes (number)",
            default=str(aspect.free_invokes),
            max_length=2,
            required=False
        )
        self.add_item(self.free_invokes_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        aspects = character.aspects
        if self.index >= len(aspects):
            await interaction.response.send_message("❌ Aspect not found.", ephemeral=True)
            return
        
        # Update the aspect with new values
        aspects[self.index].name = self.name_field.value.strip()
        aspects[self.index].description = self.description_field.value.strip()
        
        # Handle the free invokes value
        try:
            free_invokes = int(self.free_invokes_field.value.strip() or "0")
            aspects[self.index].free_invokes = max(0, free_invokes)  # Ensure non-negative
        except ValueError:
            # If conversion fails, default to 0
            aspects[self.index].free_invokes = 0
        
        # Save changes
        character.aspects = aspects
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditAspectsViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    page=self.index,
                    status_message="✅ Aspect updated."
                )
            )
        else:
            # Local import to avoid circular dependency
            from rpg_systems.fate.fate_sheet_edit_views import EditAspectsView
            await interaction.response.edit_message(
                content="✅ Aspect updated.", 
                embed=character.format_full_sheet(interaction.guild.id), 
                view=EditAspectsView(interaction.guild.id, interaction.user.id, self.char_id)
            )

class AddAspectModal(ui.Modal, title="Add Aspect"):
    def __init__(self, char_id: str, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id
        
        self.name_field = ui.TextInput(
            label="Aspect Name",
            max_length=100,
            required=True
        )
        self.add_item(self.name_field)
        
        self.description_field = ui.TextInput(
            label="Description (optional)",
            style=discord.TextStyle.paragraph,
            max_length=500,
            required=False
        )
        self.add_item(self.description_field)
        
        # Add free invokes field
        self.free_invokes_field = ui.TextInput(
            label="Free Invokes (number)",
            default="0",
            max_length=2,
            required=False
        )
        self.add_item(self.free_invokes_field)

        self.is_hidden_field = ui.CheckboxGroup(
            required=False,
            options=[
                discord.CheckboxGroupOption(
                    label="Hidden",
                    value="hidden"
                )
            ]
        )
        self.add_item(self.is_hidden_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        aspects = character.aspects
        
        # Process the free invokes input
        try:
            free_invokes = int(self.free_invokes_field.value.strip() or "0")
            free_invokes = max(0, free_invokes)  # Ensure non-negative
        except ValueError:
            free_invokes = 0

        is_hidden = "hidden" in self.is_hidden_field.values
        
        # Create new aspect as an Aspect object
        new_aspect = Aspect(
            name=self.name_field.value.strip(),
            description=self.description_field.value.strip(),
            is_hidden=is_hidden,
            free_invokes=free_invokes
        )
        
        aspects.append(new_aspect)
        character.aspects = aspects
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditAspectsViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    page=len(aspects) - 1,
                    status_message="✅ Aspect added."
                )
            )
        else:
            # Local import to avoid circular dependency
            from rpg_systems.fate.fate_sheet_edit_views import EditAspectsView
            await interaction.response.edit_message(
                content="✅ Aspect added.", 
                embed=character.format_full_sheet(interaction.guild.id), 
                view=EditAspectsView(interaction.guild.id, interaction.user.id, self.char_id)
            )

class EditFatePointsModal(ui.Modal, title="Edit Fate Points/Refresh"):
    fate_points = ui.TextInput(label="Fate Points", required=True)
    refresh = ui.TextInput(label="Refresh", required=True)

    def __init__(self, char_id, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id
        
        # Get current values to show as defaults
        character = get_character(char_id)
        if character:
            self.fate_points.default = str(character.fate_points)
            self.refresh.default = str(character.refresh)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        try:
            character.fate_points = int(self.fate_points.value)
            character.refresh = int(self.refresh.value)
        except ValueError:
            await interaction.response.send_message("❌ Invalid number.", ephemeral=True)
            return
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=FateSheetEditViewV2(
                    editor_id=interaction.user.id,
                    char_id=self.char_id,
                    guild_id=self.guild_id,
                    status_message="✅ Fate Points and Refresh updated."
                )
            )
        else:
            # Local import to avoid circular dependency
            from rpg_systems.fate.fate_sheet_edit_views import FateSheetEditView
            await interaction.response.edit_message(
                content="✅ Fate Points and Refresh updated.", 
                embed=character.format_full_sheet(interaction.guild.id), 
                view=FateSheetEditView(interaction.user.id, self.char_id)
            )

class EditSkillValueModal(ui.Modal, title="Edit Skill Value"):
    def __init__(self, char_id: str, skill: str, current_value: int = 0, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.skill = skill
        self.guild_id = guild_id
        label = f"Set value for {skill} (-3 to 6)"
        if len(label) > 45:
            label = label[:42] + "..."
        self.value_field = ui.TextInput(
            label=label,
            required=True,
            default=str(current_value),
            max_length=3
        )
        self.add_item(self.value_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        value = self.value_field.value.strip()
        try:
            value_int = int(value)
            if value_int < -3 or value_int > 6:
                raise ValueError
        except Exception:
            await interaction.response.send_message("❌ Please enter an integer from -3 to 6.", ephemeral=True)
            return
        skills = character.skills
        skills[self.skill] = value_int
        character.skills = skills
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=FateSheetEditViewV2(
                    editor_id=interaction.user.id,
                    char_id=self.char_id,
                    guild_id=self.guild_id,
                    status_message=f"✅ {self.skill} updated."
                )
            )
        else:
            # Local import to avoid circular dependency
            from rpg_systems.fate.fate_sheet_edit_views import FateSheetEditView
            embed = character.format_full_sheet(interaction.guild.id)
            view = FateSheetEditView(interaction.user.id, self.char_id)
            await interaction.response.edit_message(content=f"✅ {self.skill} updated.", embed=embed, view=view)

class AddSkillModal(ui.Modal, title="Add New Skill"):
    skill_name = ui.TextInput(label="Skill Name", required=True, max_length=50)
    skill_value = ui.TextInput(label="Skill Value (-3 to 6)", required=True, default="0", max_length=2)

    def __init__(self, char_id: str, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        
        # Validate skill value
        try:
            value_int = int(self.skill_value.value.strip())
            if value_int < -3 or value_int > 6:
                await interaction.response.send_message("❌ Skill value must be between -3 and 6.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid integer for skill value.", ephemeral=True)
            return
        
        # Add the new skill
        skills = character.skills
        skill_name = self.skill_name.value.strip()
        
        if not skill_name:
            await interaction.response.send_message("❌ Skill name cannot be empty.", ephemeral=True)
            return
            
        if skill_name in skills:
            await interaction.response.send_message(f"❌ Skill '{skill_name}' already exists. Use edit instead.", ephemeral=True)
            return
            
        skills[skill_name] = value_int
        character.skills = skills
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        success_message = f"✅ Added new skill: **{skill_name}** (+{value_int if value_int >= 0 else value_int})"
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=FateSheetEditViewV2(
                    editor_id=interaction.user.id,
                    char_id=self.char_id,
                    guild_id=self.guild_id,
                    status_message=success_message
                )
            )
        else:
            # Local import to avoid circular dependency
            from rpg_systems.fate.fate_sheet_edit_views import FateSheetEditView
            embed = character.format_full_sheet(interaction.guild.id)
            view = FateSheetEditView(interaction.user.id, self.char_id)
            await interaction.response.edit_message(
                content=success_message,
                embed=embed,
                view=view
            )

class BulkEditSkillsModal(ui.Modal, title="Bulk Edit Skills"):
    def __init__(self, char_id: str, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id
        
        # Get current skills to show as default
        character = get_character(char_id)
        skills = character.skills if character and character.skills else {}
        
        self.skills_text = ui.TextInput(
            label="Skills (format: Skill1:2,Skill2:1,Skill3:-1)",
            style=discord.TextStyle.paragraph,
            required=False,
            default=", ".join(f"{k}:{v}" for k, v in skills.items()),
            max_length=1000
        )
        self.add_item(self.skills_text)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        skills_dict = FateCharacter.parse_and_validate_skills(self.skills_text.value)
        
        if not skills_dict:
            skills_dict = {}  # Allow clearing all skills

        # Replace all skills with the new set
        character.skills = skills_dict
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=FateSheetEditViewV2(
                    editor_id=interaction.user.id,
                    char_id=self.char_id,
                    guild_id=self.guild_id,
                    status_message="✅ Skills updated!"
                )
            )
        else:
            # Local import to avoid circular dependency
            from rpg_systems.fate.fate_sheet_edit_views import FateSheetEditView
            embed = character.format_full_sheet(interaction.guild.id)
            view = FateSheetEditView(interaction.user.id, self.char_id)
            await interaction.response.edit_message(
                content="✅ Skills updated!",
                embed=embed,
                view=view
            )
    
class EditStuntModal(ui.Modal, title="Edit Stunt"):
    def __init__(self, char_id: str, stunt_name: str, description: str, guild_id: int = None, page: int = 0):
        super().__init__()
        self.char_id = char_id
        self.original_name = stunt_name
        self.guild_id = guild_id
        self.page = page
        
        self.name_field = ui.TextInput(
            label="Stunt Name",
            default=stunt_name,
            max_length=100,
            required=True
        )
        self.add_item(self.name_field)
        
        self.description_field = ui.TextInput(
            label="Description",
            default=description,
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.description_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        stunts = character.stunts
        
        new_name = self.name_field.value.strip()
        description = self.description_field.value.strip()
        
        if not new_name:
            await interaction.response.send_message("❌ Stunt name cannot be empty.", ephemeral=True)
            return
        
        # If name changed, remove old stunt and add with new name
        if new_name != self.original_name:
            if new_name in stunts and new_name != self.original_name:
                await interaction.response.send_message(f"❌ A stunt with the name '{new_name}' already exists.", ephemeral=True)
                return
            
            del stunts[self.original_name]
            
        stunts[new_name] = description
        character.stunts = stunts
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        success_message = f"✅ Stunt '{new_name}' updated."
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditStuntsViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    page=self.page,
                    status_message=success_message
                )
            )
        else:
            # Local import to avoid circular dependency
            from rpg_systems.fate.fate_sheet_edit_views import EditStuntsView
            await interaction.response.edit_message(
                content=success_message,
                view=EditStuntsView(interaction.guild.id, interaction.user.id, self.char_id)
            )

class AddStuntModal(ui.Modal, title="Add New Stunt"):
    def __init__(self, char_id: str, guild_id: int = None):
        super().__init__()
        self.char_id = char_id
        self.guild_id = guild_id
        
        self.name_field = ui.TextInput(
            label="Stunt Name",
            max_length=100,
            required=True
        )
        self.add_item(self.name_field)
        
        self.description_field = ui.TextInput(
            label="Description",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.description_field)

    async def on_submit(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        stunts = character.stunts
        
        name = self.name_field.value.strip()
        description = self.description_field.value.strip()
        
        if not name:
            await interaction.response.send_message("❌ Stunt name cannot be empty.", ephemeral=True)
            return
            
        if name in stunts:
            await interaction.response.send_message(f"❌ A stunt with the name '{name}' already exists.", ephemeral=True)
            return
            
        stunts[name] = description
        character.stunts = stunts
        repositories.entity.upsert_entity(interaction.guild.id, character, system=SYSTEM)
        
        success_message = f"✅ Added new stunt: '{name}'"
        if self.guild_id is not None:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditStuntsViewV2(
                    self.guild_id,
                    interaction.user.id,
                    self.char_id,
                    page=len(stunts) - 1,
                    status_message=success_message
                )
            )
        else:
            # Local import to avoid circular dependency
            from rpg_systems.fate.fate_sheet_edit_views import EditStuntsView
            await interaction.response.edit_message(
                content=success_message,
                view=EditStuntsView(interaction.guild.id, interaction.user.id, self.char_id)
            )


class FateSheetEditViewV2(ui.LayoutView):
    def __init__(self, editor_id: int, char_id: str, guild_id: int, status_message: str = None):
        super().__init__(timeout=86400)
        self.editor_id = editor_id
        self.char_id = char_id
        self.guild_id = guild_id
        self.status_message = status_message
        self._build_layout()

    def _build_layout(self):
        character = get_character(self.char_id)
        if not character:
            container = ui.Container(accent_colour=discord.Colour.red())
            container.add_item(ui.TextDisplay("❌ Character not found."))
            self.add_item(container)
            return

        if self.status_message:
            status = ui.Container(accent_colour=discord.Colour.green())
            status.add_item(ui.TextDisplay(_truncate_text(self.status_message)))
            self.add_item(status)

        sheet_text = embed_to_text(character.format_full_sheet(self.guild_id, is_gm=True))
        content = ui.Container(accent_colour=discord.Colour.purple())
        content.add_item(ui.TextDisplay(_truncate_text(sheet_text)))
        self.add_item(content)
        self.add_item(ui.Separator())

        primary_row = ui.ActionRow()
        _add_action_button(primary_row, "Edit Stress", discord.ButtonStyle.primary, self.edit_stress)
        _add_action_button(primary_row, "Edit Consequences", discord.ButtonStyle.primary, self.edit_consequences)
        _add_action_button(primary_row, "Edit Fate Points/Refresh", discord.ButtonStyle.primary, self.edit_fate_points)
        self.add_item(primary_row)

        secondary_row = ui.ActionRow()
        _add_action_button(secondary_row, "Edit Name", discord.ButtonStyle.secondary, self.edit_name)
        _add_action_button(secondary_row, "Edit Notes", discord.ButtonStyle.secondary, self.edit_notes)
        _add_action_button(secondary_row, "Edit Aspects", discord.ButtonStyle.secondary, self.edit_aspects)
        _add_action_button(secondary_row, "Edit Skills", discord.ButtonStyle.secondary, self.edit_skills)
        _add_action_button(secondary_row, "Edit Stunts", discord.ButtonStyle.secondary, self.edit_stunts)
        self.add_item(secondary_row)

        inventory_row = ui.ActionRow()
        _add_action_button(inventory_row, "📦 Inventory", discord.ButtonStyle.secondary, self.edit_inventory)
        self.add_item(inventory_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    async def edit_stress(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditStressTracksViewV2(self.guild_id, self.editor_id, self.char_id, 0)
        )

    async def edit_consequences(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditConsequencesViewV2(self.guild_id, self.editor_id, self.char_id)
        )

    async def edit_fate_points(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditFatePointsModal(self.char_id, guild_id=self.guild_id))

    async def edit_name(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditNameModal(self.char_id, SYSTEM))

    async def edit_notes(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditNotesModal(self.char_id, SYSTEM))

    async def edit_aspects(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditAspectsViewV2(self.guild_id, self.editor_id, self.char_id)
        )

    async def edit_skills(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=SkillManagementViewV2(character, self.editor_id, self.char_id, self.guild_id)
        )

    async def edit_stunts(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditStuntsViewV2(self.guild_id, self.editor_id, self.char_id)
        )

    async def edit_inventory(self, interaction: discord.Interaction):
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditInventoryViewV2(interaction.guild.id, self.editor_id, self.char_id, is_gm=is_gm)
        )


class EditAspectsViewV2(ui.LayoutView):
    def __init__(self, guild_id: int, user_id: int, char_id: str, page: int = 0, status_message: str = None):
        super().__init__(timeout=86400)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.status_message = status_message
        self.char = get_character(char_id)
        self.aspects = self.char.aspects if self.char else []
        self.page = max(0, min(page, len(self.aspects) - 1)) if self.aspects else 0
        self.max_page = max(0, len(self.aspects) - 1)
        self._build_layout()

    def _build_layout(self):
        if self.status_message:
            status = ui.Container(accent_colour=discord.Colour.green())
            status.add_item(ui.TextDisplay(_truncate_text(self.status_message)))
            self.add_item(status)

        content = ui.Container(accent_colour=discord.Colour.purple())
        if self.aspects:
            aspect = self.aspects[self.page]
            lines = [
                f"## Aspect {self.page + 1}/{len(self.aspects)}",
                f"**Name:** {aspect.name}",
                f"**Hidden:** {'Yes' if aspect.is_hidden else 'No'}",
                f"**Free Invokes:** {aspect.free_invokes}",
            ]
            if aspect.description:
                lines.extend(["", "**Description**", aspect.description])
            content.add_item(ui.TextDisplay(_truncate_text("\n".join(lines))))
        else:
            content.add_item(ui.TextDisplay("## Aspects\nNo aspects available."))
        self.add_item(content)
        self.add_item(ui.Separator())

        if self.aspects:
            nav_row = ui.ActionRow()
            if self.page > 0:
                _add_action_button(nav_row, "◀️ Prev", discord.ButtonStyle.secondary, self.prev_page)
            if self.page < self.max_page:
                _add_action_button(nav_row, "Next ▶️", discord.ButtonStyle.secondary, self.next_page)
            if nav_row.children:
                self.add_item(nav_row)

            action_row = ui.ActionRow()
            _add_action_button(action_row, "✏️ Edit", discord.ButtonStyle.primary, self.edit_aspect)
            _add_action_button(action_row, "🗑 Remove", discord.ButtonStyle.danger, self.remove_aspect)
            toggle_label = "🙈 Hide" if not self.aspects[self.page].is_hidden else "👁 Unhide"
            toggle_style = discord.ButtonStyle.secondary if not self.aspects[self.page].is_hidden else discord.ButtonStyle.success
            _add_action_button(action_row, toggle_label, toggle_style, self.toggle_hidden)
            self.add_item(action_row)

        footer_row = ui.ActionRow()
        _add_action_button(footer_row, "➕ Add New", discord.ButtonStyle.success, self.add_aspect)
        _add_action_button(footer_row, "✅ Done", discord.ButtonStyle.secondary, self.done)
        self.add_item(footer_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    async def prev_page(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditAspectsViewV2(self.guild_id, self.user_id, self.char_id, page=self.page - 1)
        )

    async def next_page(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditAspectsViewV2(self.guild_id, self.user_id, self.char_id, page=self.page + 1)
        )

    async def edit_aspect(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditAspectModal(self.char_id, self.page, self.aspects[self.page], guild_id=self.guild_id))

    async def remove_aspect(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        aspects = character.aspects
        removed_aspect = aspects.pop(self.page)
        character.aspects = aspects
        repositories.entity.upsert_entity(self.guild_id, character, system=SYSTEM)
        next_page = max(0, min(self.page, len(aspects) - 1)) if aspects else 0
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditAspectsViewV2(
                self.guild_id,
                self.user_id,
                self.char_id,
                page=next_page,
                status_message=f"✅ Removed aspect: **{removed_aspect.name}**"
            )
        )

    async def toggle_hidden(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        aspects = character.aspects
        aspects[self.page].is_hidden = not aspects[self.page].is_hidden
        character.aspects = aspects
        repositories.entity.upsert_entity(self.guild_id, character, system=SYSTEM)
        status = "hidden" if aspects[self.page].is_hidden else "visible"
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditAspectsViewV2(
                self.guild_id,
                self.user_id,
                self.char_id,
                page=self.page,
                status_message=f"✅ Aspect is now {status}."
            )
        )

    async def add_aspect(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddAspectModal(self.char_id, guild_id=self.guild_id))

    async def done(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=FateSheetEditViewV2(self.user_id, self.char_id, self.guild_id, status_message="✅ Done editing aspects.")
        )


class EditStressTracksViewV2(ui.LayoutView):
    def __init__(self, guild_id: int, user_id: int, char_id: str, track_index: int = 0, status_message: str = None):
        super().__init__(timeout=86400)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.status_message = status_message
        self.char = get_character(char_id)
        self.stress_tracks = self.char.stress_tracks if self.char else []
        self.current_track_index = max(0, min(track_index, len(self.stress_tracks) - 1)) if self.stress_tracks else 0
        self._build_layout()

    def _build_layout(self):
        if self.status_message:
            status = ui.Container(accent_colour=discord.Colour.green())
            status.add_item(ui.TextDisplay(_truncate_text(self.status_message)))
            self.add_item(status)

        content = ui.Container(accent_colour=discord.Colour.purple())
        if not self.stress_tracks:
            content.add_item(ui.TextDisplay("## Stress Tracks\nNo stress tracks available."))
        else:
            track = self.stress_tracks[self.current_track_index]
            lines = [f"## {track.track_name}"]
            if track.linked_skill:
                lines.append(f"**Linked Skill:** {track.linked_skill}")
            lines.append("")
            lines.append("**Boxes**")
            for box in track.boxes:
                status = "☒" if box.is_filled else "☐"
                lines.append(f"- {status} [{box.value}]")
            if len(track.boxes) > 5:
                lines.extend(["", "*Only the first 5 boxes have quick-toggle buttons.*"])
            content.add_item(ui.TextDisplay(_truncate_text("\n".join(lines))))
        self.add_item(content)
        self.add_item(ui.Separator())

        if self.stress_tracks:
            track_row = ui.ActionRow()
            track_options = [SelectOption(label=track.track_name, value=str(i)) for i, track in enumerate(self.stress_tracks)]
            track_select = ui.Select(placeholder="Select stress track...", options=track_options)
            track_select.callback = self.track_selected
            track_row.add_item(track_select)
            self.add_item(track_row)

            box_row = ui.ActionRow()
            for idx, box in enumerate(self.stress_tracks[self.current_track_index].boxes[:5]):
                label = f"{'☒' if box.is_filled else '☐'}[{box.value}]"
                button = ui.Button(
                    label=label,
                    style=discord.ButtonStyle.success if box.is_filled else discord.ButtonStyle.secondary
                )
                button.callback = self.make_box_callback(idx)
                box_row.add_item(button)
            if box_row.children:
                self.add_item(box_row)

            manage_row = ui.ActionRow()
            _add_action_button(manage_row, "➕ Add Box", discord.ButtonStyle.success, self.add_box)
            _add_action_button(manage_row, "🗑 Remove Box", discord.ButtonStyle.danger, self.remove_box)
            _add_action_button(manage_row, "Clear All", discord.ButtonStyle.danger, self.clear_all)
            self.add_item(manage_row)

        footer_row = ui.ActionRow()
        _add_action_button(footer_row, "➕ Add New Track", discord.ButtonStyle.primary, self.add_track)
        _add_action_button(footer_row, "✅ Done", discord.ButtonStyle.secondary, self.done)
        self.add_item(footer_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    async def track_selected(self, interaction: discord.Interaction):
        selected_index = int(interaction.data["values"][0])
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditStressTracksViewV2(self.guild_id, self.user_id, self.char_id, track_index=selected_index)
        )

    def make_box_callback(self, box_index: int):
        async def callback(interaction: discord.Interaction):
            character = get_character(self.char_id)
            stress_tracks = character.stress_tracks
            track = stress_tracks[self.current_track_index]
            track.boxes[box_index].is_filled = not track.boxes[box_index].is_filled
            character.stress_tracks = stress_tracks
            repositories.entity.upsert_entity(self.guild_id, character, system=SYSTEM)
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=EditStressTracksViewV2(
                    self.guild_id,
                    self.user_id,
                    self.char_id,
                    track_index=self.current_track_index,
                    status_message=f"✅ Toggled box [{track.boxes[box_index].value}]."
                )
            )

        return callback

    async def add_box(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddStressBoxModal(self.char_id, self.current_track_index, guild_id=self.guild_id))

    async def remove_box(self, interaction: discord.Interaction):
        await interaction.response.send_modal(RemoveStressBoxModal(self.char_id, self.current_track_index, guild_id=self.guild_id))

    async def clear_all(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        stress_tracks = character.stress_tracks
        track = stress_tracks[self.current_track_index]
        track.clear_all_boxes()
        character.stress_tracks = stress_tracks
        repositories.entity.upsert_entity(self.guild_id, character, system=SYSTEM)
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditStressTracksViewV2(
                self.guild_id,
                self.user_id,
                self.char_id,
                track_index=self.current_track_index,
                status_message=f"✅ Cleared all boxes on {track.track_name}."
            )
        )

    async def add_track(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddStressTrackModal(self.char_id, guild_id=self.guild_id))

    async def done(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=FateSheetEditViewV2(self.user_id, self.char_id, self.guild_id, status_message="✅ Done editing stress tracks.")
        )


class EditConsequencesViewV2(ui.LayoutView):
    def __init__(self, guild_id: int, user_id: int, char_id: str, track_index: int = 0, consequence_index: int = 0, status_message: str = None):
        super().__init__(timeout=86400)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.status_message = status_message
        self.char = get_character(char_id)
        self.consequence_tracks = self.char.consequence_tracks if self.char else []
        self.track_index = track_index
        self.consequence_index = consequence_index
        self._build_layout()

    def _all_consequences(self):
        all_consequences = []
        for track_idx, track in enumerate(self.consequence_tracks):
            for cons_idx, consequence in enumerate(track.consequences):
                all_consequences.append((track_idx, cons_idx, consequence))
        return all_consequences

    def _current_position(self, all_consequences):
        if not all_consequences:
            return 0
        for idx, (track_idx, cons_idx, _consequence) in enumerate(all_consequences):
            if track_idx == self.track_index and cons_idx == self.consequence_index:
                return idx
        return 0

    def _build_layout(self):
        if self.status_message:
            status = ui.Container(accent_colour=discord.Colour.green())
            status.add_item(ui.TextDisplay(_truncate_text(self.status_message)))
            self.add_item(status)

        all_consequences = self._all_consequences()
        content = ui.Container(accent_colour=discord.Colour.purple())
        if not all_consequences:
            content.add_item(ui.TextDisplay("## Consequences\nNo consequences available."))
        else:
            current_pos = self._current_position(all_consequences)
            self.track_index, self.consequence_index, consequence = all_consequences[current_pos]
            track = self.consequence_tracks[self.track_index]
            lines = [
                f"## Consequence {current_pos + 1}/{len(all_consequences)}",
                f"**Track:** {track.name}",
                f"**Name:** {consequence.name}",
                f"**Severity:** {consequence.severity}",
                f"**Aspect:** {consequence.aspect.name if consequence.aspect else 'Empty'}",
            ]
            if consequence.aspect and consequence.aspect.free_invokes:
                lines.append(f"**Free Invokes:** {consequence.aspect.free_invokes}")
            content.add_item(ui.TextDisplay(_truncate_text("\n".join(lines))))
        self.add_item(content)
        self.add_item(ui.Separator())

        if all_consequences:
            current_pos = self._current_position(all_consequences)
            nav_row = ui.ActionRow()
            if current_pos > 0:
                _add_action_button(nav_row, "◀️ Prev", discord.ButtonStyle.secondary, self.prev_consequence)
            if current_pos < len(all_consequences) - 1:
                _add_action_button(nav_row, "Next ▶️", discord.ButtonStyle.secondary, self.next_consequence)
            if nav_row.children:
                self.add_item(nav_row)

            action_row = ui.ActionRow()
            _add_action_button(action_row, "✏️ Edit", discord.ButtonStyle.primary, self.edit_consequence)
            if all_consequences[current_pos][2].aspect:
                _add_action_button(action_row, "🗑 Clear", discord.ButtonStyle.danger, self.clear_consequence)
            self.add_item(action_row)

        footer_row = ui.ActionRow()
        _add_action_button(footer_row, "➕ Add New Track", discord.ButtonStyle.primary, self.add_track)
        _add_action_button(footer_row, "✅ Done", discord.ButtonStyle.secondary, self.done)
        self.add_item(footer_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    async def prev_consequence(self, interaction: discord.Interaction):
        all_consequences = self._all_consequences()
        current_pos = max(0, self._current_position(all_consequences) - 1)
        track_index, consequence_index, _ = all_consequences[current_pos]
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditConsequencesViewV2(
                self.guild_id,
                self.user_id,
                self.char_id,
                track_index=track_index,
                consequence_index=consequence_index
            )
        )

    async def next_consequence(self, interaction: discord.Interaction):
        all_consequences = self._all_consequences()
        current_pos = min(len(all_consequences) - 1, self._current_position(all_consequences) + 1)
        track_index, consequence_index, _ = all_consequences[current_pos]
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditConsequencesViewV2(
                self.guild_id,
                self.user_id,
                self.char_id,
                track_index=track_index,
                consequence_index=consequence_index
            )
        )

    async def edit_consequence(self, interaction: discord.Interaction):
        all_consequences = self._all_consequences()
        current_pos = self._current_position(all_consequences)
        consequence = all_consequences[current_pos][2]
        await interaction.response.send_modal(
            EditConsequenceModal(
                self.char_id,
                self.track_index,
                self.consequence_index,
                consequence,
                guild_id=self.guild_id
            )
        )

    async def clear_consequence(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        consequence_tracks = character.consequence_tracks
        consequence = consequence_tracks[self.track_index].consequences[self.consequence_index]
        consequence.aspect = None
        character.consequence_tracks = consequence_tracks
        repositories.entity.upsert_entity(self.guild_id, character, system=SYSTEM)
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditConsequencesViewV2(
                self.guild_id,
                self.user_id,
                self.char_id,
                track_index=self.track_index,
                consequence_index=self.consequence_index,
                status_message=f"✅ Cleared consequence: **{consequence.name}**"
            )
        )

    async def add_track(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddConsequenceTrackModal(self.char_id, guild_id=self.guild_id))

    async def done(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=FateSheetEditViewV2(self.user_id, self.char_id, self.guild_id, status_message="✅ Done editing consequences.")
        )


class EditStuntsViewV2(ui.LayoutView):
    def __init__(self, guild_id: int, user_id: int, char_id: str, page: int = 0, status_message: str = None):
        super().__init__(timeout=86400)
        self.guild_id = guild_id
        self.user_id = user_id
        self.char_id = char_id
        self.status_message = status_message
        self.char = get_character(char_id)
        self.stunts = self.char.stunts if self.char else {}
        self.stunt_names = list(self.stunts.keys())
        self.page = max(0, min(page, len(self.stunt_names) - 1)) if self.stunt_names else 0
        self.max_page = max(0, len(self.stunt_names) - 1)
        self._build_layout()

    def _build_layout(self):
        if self.status_message:
            status = ui.Container(accent_colour=discord.Colour.green())
            status.add_item(ui.TextDisplay(_truncate_text(self.status_message)))
            self.add_item(status)

        content = ui.Container(accent_colour=discord.Colour.purple())
        if self.stunt_names:
            current_stunt = self.stunt_names[self.page]
            lines = [
                f"## Stunt {self.page + 1}/{len(self.stunt_names)}",
                f"**Name:** {current_stunt}",
                "",
                "**Description**",
                self.stunts.get(current_stunt, "No description available"),
            ]
            content.add_item(ui.TextDisplay(_truncate_text("\n".join(lines))))
        else:
            content.add_item(ui.TextDisplay("## Stunts\nNo stunts available."))
        self.add_item(content)
        self.add_item(ui.Separator())

        if self.stunt_names:
            nav_row = ui.ActionRow()
            if self.page > 0:
                _add_action_button(nav_row, "◀️ Prev", discord.ButtonStyle.secondary, self.prev_page)
            if self.page < self.max_page:
                _add_action_button(nav_row, "Next ▶️", discord.ButtonStyle.secondary, self.next_page)
            if nav_row.children:
                self.add_item(nav_row)

            action_row = ui.ActionRow()
            _add_action_button(action_row, "✏️ Edit", discord.ButtonStyle.primary, self.edit_stunt)
            _add_action_button(action_row, "🗑 Remove", discord.ButtonStyle.danger, self.remove_stunt)
            self.add_item(action_row)

        footer_row = ui.ActionRow()
        _add_action_button(footer_row, "➕ Add New", discord.ButtonStyle.success, self.add_stunt)
        _add_action_button(footer_row, "✅ Done", discord.ButtonStyle.secondary, self.done)
        self.add_item(footer_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    async def prev_page(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditStuntsViewV2(self.guild_id, self.user_id, self.char_id, page=self.page - 1)
        )

    async def next_page(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditStuntsViewV2(self.guild_id, self.user_id, self.char_id, page=self.page + 1)
        )

    async def edit_stunt(self, interaction: discord.Interaction):
        current_stunt = self.stunt_names[self.page]
        await interaction.response.send_modal(
            EditStuntModal(
                self.char_id,
                current_stunt,
                self.stunts.get(current_stunt, ""),
                guild_id=self.guild_id,
                page=self.page
            )
        )

    async def remove_stunt(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        stunts = character.stunts
        current_stunt = self.stunt_names[self.page]
        del stunts[current_stunt]
        character.stunts = stunts
        repositories.entity.upsert_entity(self.guild_id, character, system=SYSTEM)
        next_page = max(0, min(self.page, len(stunts) - 1)) if stunts else 0
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=EditStuntsViewV2(
                self.guild_id,
                self.user_id,
                self.char_id,
                page=next_page,
                status_message=f"✅ Removed stunt: **{current_stunt}**"
            )
        )

    async def add_stunt(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddStuntModal(self.char_id, guild_id=self.guild_id))

    async def done(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=FateSheetEditViewV2(self.user_id, self.char_id, self.guild_id, status_message="✅ Done editing stunts.")
        )


class SkillManagementViewV2(ui.LayoutView):
    def __init__(self, character: FateCharacter, editor_id: int, char_id: str, guild_id: int, status_message: str = None):
        super().__init__(timeout=86400)
        self.character = character or get_character(char_id)
        self.editor_id = editor_id
        self.char_id = char_id
        self.guild_id = guild_id
        self.status_message = status_message
        self._build_layout()

    def _build_layout(self):
        if self.status_message:
            status = ui.Container(accent_colour=discord.Colour.green())
            status.add_item(ui.TextDisplay(_truncate_text(self.status_message)))
            self.add_item(status)

        summary = ui.Container(accent_colour=discord.Colour.purple())
        skill_count = len((self.character.skills if self.character else {}) or {})
        summary.add_item(ui.TextDisplay(f"## Skill Management\nChoose how to manage skills.\n\n**Current skills:** {skill_count}"))
        self.add_item(summary)
        self.add_item(ui.Separator())

        primary_row = ui.ActionRow()
        _add_action_button(primary_row, "Edit Existing Skill", discord.ButtonStyle.primary, self.edit_existing_skill)
        _add_action_button(primary_row, "Add New Skill", discord.ButtonStyle.success, self.add_new_skill)
        _add_action_button(primary_row, "Remove Skill", discord.ButtonStyle.danger, self.remove_skill)
        self.add_item(primary_row)

        secondary_row = ui.ActionRow()
        _add_action_button(secondary_row, "Bulk Edit Skills", discord.ButtonStyle.secondary, self.bulk_edit_skills)
        _add_action_button(secondary_row, "Cancel", discord.ButtonStyle.secondary, self.cancel)
        self.add_item(secondary_row)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    async def edit_existing_skill(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        skills = character.skills if character and character.skills else {}
        if not skills:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=SkillManagementViewV2(
                    character,
                    self.editor_id,
                    self.char_id,
                    self.guild_id,
                    status_message="This character doesn't have any skills yet. Add some first!"
                )
            )
            return

        skill_options = [SelectOption(label=k, value=k) for k in sorted(skills.keys())]

        async def on_skill_selected(_view, interaction2, skill):
            current_value = get_character(self.char_id).skills.get(skill, 0)
            await interaction2.response.send_modal(EditSkillValueModal(self.char_id, skill, current_value, guild_id=self.guild_id))

        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=PaginatedSelectViewV2(
                skill_options,
                on_skill_selected,
                interaction.user.id,
                prompt="Select a skill to edit:",
                title="## Select a skill to edit"
            )
        )

    async def add_new_skill(self, interaction: discord.Interaction):
        await interaction.response.send_modal(AddSkillModal(self.char_id, guild_id=self.guild_id))

    async def remove_skill(self, interaction: discord.Interaction):
        character = get_character(self.char_id)
        skills = character.skills if character and character.skills else {}
        if not skills:
            await interaction.response.edit_message(
                content=None,
                embed=None,
                view=SkillManagementViewV2(
                    character,
                    self.editor_id,
                    self.char_id,
                    self.guild_id,
                    status_message="This character doesn't have any skills to remove."
                )
            )
            return

        skill_options = [SelectOption(label=k, value=k) for k in sorted(skills.keys())]

        async def on_skill_selected(_view, interaction2: discord.Interaction, skill):
            current_character = get_character(self.char_id)
            current_skills = current_character.skills
            if skill in current_skills:
                del current_skills[skill]
                current_character.skills = current_skills
                repositories.entity.upsert_entity(interaction2.guild.id, current_character, system=SYSTEM)
                await interaction2.response.edit_message(
                    content=None,
                    embed=None,
                    view=FateSheetEditViewV2(
                        interaction2.user.id,
                        self.char_id,
                        self.guild_id,
                        status_message=f"✅ Removed skill: **{skill}**"
                    )
                )
            else:
                await interaction2.response.edit_message(
                    content=None,
                    embed=None,
                    view=SkillManagementViewV2(
                        current_character,
                        self.editor_id,
                        self.char_id,
                        self.guild_id,
                        status_message=f"❌ Skill not found: {skill}"
                    )
                )

        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=PaginatedSelectViewV2(
                skill_options,
                on_skill_selected,
                interaction.user.id,
                prompt="Select a skill to remove:",
                title="## Select a skill to remove"
            )
        )

    async def bulk_edit_skills(self, interaction: discord.Interaction):
        await interaction.response.send_modal(BulkEditSkillsModal(self.char_id, guild_id=self.guild_id))

    async def cancel(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=None,
            embed=None,
            view=FateSheetEditViewV2(self.editor_id, self.char_id, self.guild_id, status_message="Operation cancelled.")
        )