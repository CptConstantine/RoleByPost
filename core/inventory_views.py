import discord
from discord import ui
from core.base_models import BaseEntity, EntityLinkType, EntityType
from data.repositories.repository_factory import repositories

class EditInventoryView(ui.View):
    def __init__(self, guild_id: int, user_id: int, parent_id: str):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.parent_id = parent_id
        self.items_per_page = 10
        self.page = 0
        self.selected_items = []  # For multi-select operations

        self.entity = None
        self.inventory = []
        self.max_page = 0
        self.load_data()
        self.render()

    def refresh_view(self):
        """Refresh the inventory view with current data"""
        self.load_data()
        self.render()
        return self

    def load_data(self):
        self.entity = repositories.entity.get_by_id(self.parent_id)
        if not self.entity:
            self.inventory = []
        else:
            self.inventory = self.entity.get_inventory(str(self.guild_id))
        self.max_page = max(0, (len(self.inventory) - 1) // self.items_per_page)

    def render(self):
        self.clear_items()
        
        if not self.inventory:
            self.add_item(ui.Button(label="No items in inventory", disabled=True, row=0))
        else:
            # Calculate page bounds
            start_idx = self.page * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, len(self.inventory))
            page_items = self.inventory[start_idx:end_idx]
            
            # Create select dropdown for items on current page
            options = []
            for i, item in enumerate(page_items):
                # Show quantity if available
                quantity_info = ""
                links = self.entity.get_links_to_entity(
                    str(self.guild_id), item.id, EntityLinkType.POSSESSES
                )
                if links:
                    quantity = links[0].metadata.get("quantity", 1) if hasattr(links[0], 'metadata') else 1
                    if quantity > 1:
                        quantity_info = f" (x{quantity})"
                
                options.append(discord.SelectOption(
                    label=f"{item.name}{quantity_info}",
                    value=str(start_idx + i),
                    description=item.name[:50] if len(item.name) > 50 else None
                ))
            
            if options:
                select = ui.Select(
                    placeholder="Select an item to manage...", 
                    options=options,
                    row=0
                )
                select.callback = self.item_selected
                self.add_item(select)

            # Page info and navigation
            page_info = f"Page {self.page + 1}/{self.max_page + 1} ({len(self.inventory)} items total)"
            self.add_item(ui.Button(label=page_info, disabled=True, row=1))
            
            # Navigation buttons
            if self.page > 0:
                prev_btn = ui.Button(label="◀️ Previous", style=discord.ButtonStyle.secondary, row=1)
                prev_btn.callback = self.previous_page
                self.add_item(prev_btn)
            
            if self.page < self.max_page:
                next_btn = ui.Button(label="Next ▶️", style=discord.ButtonStyle.secondary, row=1)
                next_btn.callback = self.next_page
                self.add_item(next_btn)
        
        # Action buttons
        self.add_item(ui.Button(label="➕ Create Item", style=discord.ButtonStyle.success, row=2, custom_id="create_item"))
        self.add_item(ui.Button(label="🔍 Search", style=discord.ButtonStyle.secondary, row=2, custom_id="search"))
        self.add_item(ui.Button(label="✅ Done", style=discord.ButtonStyle.secondary, row=2, custom_id="done_inventory"))
        
        # Assign callbacks for action buttons
        for item in self.children:
            if isinstance(item, ui.Button) and item.custom_id:
                item.callback = self.make_callback(item.custom_id)

    async def item_selected(self, interaction: discord.Interaction):
        """Handle item selection from dropdown"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return
            
        selected_idx = int(interaction.data['values'][0])
        selected_item = self.inventory[selected_idx]
        
        # Show item management options
        is_gm = is_gm=repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        view = ItemManagementView(self.guild_id, self.user_id, self.parent_id, selected_item, selected_idx, parent_view=self)
        parent_embed = self.entity.format_full_sheet(self.guild_id, is_gm=is_gm)
        item_embed = selected_item.format_full_sheet(self.guild_id, is_gm=is_gm)

        await interaction.response.edit_message(
            content=f"Managing **{selected_item.name}**:",
            embeds=[parent_embed, item_embed],
            view=view
        )

    async def previous_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return
        
        self.page = max(0, self.page - 1)
        self.render()
        await interaction.response.edit_message(view=self)

    async def next_page(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return
        
        self.page = min(self.max_page, self.page + 1)
        self.render()
        await interaction.response.edit_message(view=self)

    def make_callback(self, cid):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                await interaction.response.send_message("You can't edit this character.", ephemeral=True)
                return
            
            if cid == "create_item":
                await interaction.response.send_modal(CreateItemModal(self.parent_id, str(self.guild_id)))
                return
            elif cid == "search":
                await interaction.response.send_modal(InventorySearchModal(self.parent_id, self))
                return
            elif cid == "done_inventory":
                is_gm = repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
                await interaction.response.edit_message(
                    content="✅ Done editing inventory.",
                    embed=self.entity.format_full_sheet(interaction.guild.id, is_gm=is_gm),
                    view=self.entity.get_sheet_edit_view(interaction.user.id, is_gm=is_gm)
                )
                return
        
        return callback

class ItemManagementView(ui.View):
    """Individual item management view shown when an item is selected"""
    def __init__(self, guild_id: int, user_id: int, parent_id: str, item: BaseEntity, item_index: int, parent_view: EditInventoryView):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.parent_id = parent_id
        self.item = item
        self.item_index = item_index
        self.parent_view = parent_view

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="✏️ View/Edit", style=discord.ButtonStyle.primary, row=0)
    async def edit_item(self, interaction: discord.Interaction, button: ui.Button):
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        sheet_view = self.item.get_sheet_edit_view(interaction.user.id, is_gm=is_gm)
        embed = self.item.format_full_sheet(interaction.guild.id, is_gm=is_gm)
        
        await interaction.response.send_message(
            content=f"Editing **{self.item.name}**:",
            embed=embed,
            view=sheet_view,
            ephemeral=True
        )
    
    @ui.button(label="Transfer Item", style=discord.ButtonStyle.primary, row=0)
    async def transfer_item(self, interaction: discord.Interaction, button: ui.Button):
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        view = TransferItemView(self.parent_id, self.guild_id, interaction.user.id, self.item, parent_view=self.parent_view)
        parent = repositories.entity.get_by_id(self.parent_id)
        embed = parent.format_full_sheet(interaction.guild.id, is_gm=is_gm)
        await interaction.response.edit_message(
            content="Select destination for transfer:",
            embed=embed,
            view=view
        )

    @ui.button(label="📊 Edit Quantity", style=discord.ButtonStyle.secondary, row=0)
    async def edit_quantity(self, interaction: discord.Interaction, button: ui.Button):
        # Only show quantity editing for items
        if self.item.entity_type != EntityType.ITEM:
            await interaction.response.send_message("❌ Quantity editing is only available for items.", ephemeral=True)
            return
        
        await interaction.response.send_modal(EditItemQuantityModal(self.parent_id, self.item, str(self.guild_id)))

    @ui.button(label="🗑️ Remove from Inventory", style=discord.ButtonStyle.danger, row=1)
    async def remove_item(self, interaction: discord.Interaction, button: ui.Button):
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        parent = repositories.entity.get_by_id(self.parent_id)
        parent.remove_from_inventory(str(self.guild_id), self.item)
        repositories.entity.upsert_entity(interaction.guild.id, parent, system=parent.system)
        embed = parent.format_full_sheet(interaction.guild.id, is_gm=is_gm)
        view = EditInventoryView(self.guild_id, self.user_id, self.parent_id)
        
        await interaction.response.edit_message(
            content=f"✅ Removed **{self.item.name}** from inventory.",
            embed=embed,
            view=view
        )

    @ui.button(label="🔙 Back to Inventory", style=discord.ButtonStyle.secondary, row=1)
    async def back_to_inventory(self, interaction: discord.Interaction, button: ui.Button):
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        entity = repositories.entity.get_by_id(self.parent_id)
        embed = entity.format_full_sheet(interaction.guild.id, is_gm=is_gm)
        view = EditInventoryView(self.guild_id, self.user_id, self.parent_id)
        await interaction.response.edit_message(
            content="Returned to inventory management.",
            embed=embed,
            view=view
        )

class EditItemQuantityModal(ui.Modal, title="Edit Item Quantity"):
    def __init__(self, parent_id: str, item: BaseEntity, guild_id: str):
        super().__init__()
        self.parent_id = parent_id
        self.item = item
        self.guild_id = guild_id
        
        # Get current quantity for default value
        char = repositories.entity.get_by_id(parent_id)
        links = char.get_links_to_entity(guild_id, item.id, EntityLinkType.POSSESSES)
        self.current_quantity = links[0].metadata.get("quantity", 1) if links and hasattr(links[0], 'metadata') else 1
        
        self.quantity_field = ui.TextInput(
            label="New Quantity",
            placeholder="Enter the new quantity",
            default=str(self.current_quantity),
            required=True,
            max_length=10
        )
        self.add_item(self.quantity_field)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            new_quantity = int(self.quantity_field.value.strip())
            if new_quantity < 0:
                await interaction.response.send_message("❌ Quantity cannot be negative.", ephemeral=True)
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
            return
        
        char = repositories.entity.get_by_id(self.parent_id)
        
        if new_quantity == 0:
            # Remove the item entirely
            char.remove_item(self.guild_id, self.item)
            message = f"✅ Removed all **{self.item.name}** from inventory."
        else:
            # Update the quantity by first removing all, then adding the new amount
            char.remove_item(self.guild_id, self.item)  # Remove all existing
            char.add_item(self.guild_id, self.item, new_quantity)  # Add new quantity
            message = f"✅ Set **{self.item.name}** quantity from {self.current_quantity} to {new_quantity}."

        repositories.entity.upsert_entity(interaction.guild.id, char, system=char.system)
        
        await interaction.response.send_message(message, ephemeral=True)

class InventorySearchModal(ui.Modal, title="Search Inventory"):
    def __init__(self, parent_id: int, parent_view: EditInventoryView):
        super().__init__()
        self.parent_id = parent_id
        self.parent_view = parent_view
    
    search_term = ui.TextInput(
        label="Search for item",
        placeholder="Enter item name to search...",
        required=True,
        max_length=100
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        search_term = self.search_term.value.lower().strip()
        
        # Filter inventory based on search term
        filtered_items = [
            item for item in self.parent_view.inventory 
            if search_term in item.name.lower()
        ]
        
        if not filtered_items:
            await interaction.response.send_message(
                f"❌ No items found matching '{search_term}'", 
                ephemeral=True
            )
            return
        
        # Show filtered results in a new view
        view = FilteredInventoryView(
            self.parent_view.guild_id, 
            self.parent_view.user_id, 
            self.parent_view.parent_id, 
            filtered_items,
            search_term,
            self.parent_view
        )

        parent = repositories.entity.get_by_id(self.parent_id)
        embed = parent.format_full_sheet(interaction.guild.id, is_gm=repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user))

        await interaction.response.edit_message(
            content=f"🔍 Found {len(filtered_items)} items matching '{search_term}':",
            embed=embed,
            view=view
        )

class FilteredInventoryView(ui.View):
    """View for displaying search results"""
    def __init__(self, guild_id: int, user_id: int, parent_id: str, filtered_items: list[BaseEntity], search_term: str, parent_view: EditInventoryView):
        super().__init__(timeout=120)
        self.guild_id = guild_id
        self.user_id = user_id
        self.parent_id = parent_id
        self.filtered_items = filtered_items
        self.search_term = search_term
        self.parent_view = parent_view
        self.render()

    def render(self):
        self.clear_items()
        
        if not self.filtered_items:
            self.add_item(ui.Button(label="No items found", disabled=True, row=0))
            return
        
        # Create select dropdown for filtered items (limit to 25 for Discord)
        options = []
        for i, item in enumerate(self.filtered_items[:25]):
            options.append(discord.SelectOption(
                label=item.name,
                value=str(i),
                description=item.name[:50] if len(item.name) > 50 else None
            ))
        
        if options:
            select = ui.Select(
                placeholder="Select an item from search results...", 
                options=options,
                row=0
            )
            select.callback = self.item_selected
            self.add_item(select)
        
        if len(self.filtered_items) > 25:
            self.add_item(ui.Button(
                label=f"Showing first 25 of {len(self.filtered_items)} results", 
                disabled=True, 
                row=1
            ))

    async def item_selected(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return
            
        selected_idx = int(interaction.data['values'][0])
        selected_item = self.filtered_items[selected_idx]
        
        # Find the actual index in the full inventory
        char = repositories.entity.get_by_id(self.parent_id)
        full_inventory = char.get_inventory(str(self.guild_id))
        actual_index = next((i for i, item in enumerate(full_inventory) if item.id == selected_item.id), 0)
        
        # Show item management options
        view = ItemManagementView(self.guild_id, self.user_id, self.parent_id, selected_item, actual_index, self.parent_view)
        parent_embed = char.format_full_sheet(self.guild_id, is_gm=repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user))
        item_embed = selected_item.format_full_sheet(self.guild_id)
        
        await interaction.response.edit_message(
            content=f"Managing **{selected_item.name}** (from search results):",
            embeds=[parent_embed, item_embed],
            view=view
        )

class CreateItemModal(ui.Modal, title="Add New Item"):
    def __init__(self, parent_id: str, guild_id: str):
        super().__init__()
        self.parent_id = parent_id
        self.guild_id = guild_id
        
        self.name_field = ui.TextInput(
            label="Item Name",
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

        self.quantity_field = ui.TextInput(
            label="Quantity",
            style=discord.TextStyle.short,
            max_length=10,
            default="1",
            required=True
        )
        self.add_item(self.quantity_field)

    async def on_submit(self, interaction: discord.Interaction):
        from core.factories import build_and_save_entity
        parent = repositories.entity.get_by_id(self.parent_id)
        
        name = self.name_field.value.strip()
        description = self.description_field.value.strip()
        quantity_str = self.quantity_field.value.strip()
        quantity = int(quantity_str) if quantity_str.isdigit() else 1
        
        if not name:
            await interaction.response.send_message("❌ Item name cannot be empty.", ephemeral=True)
            return
        
        # Check if item already exists
        existing_item = repositories.entity.get_by_name(self.guild_id, name)
        if existing_item:
            await interaction.response.send_message(f"❌ An entity named '{name}' already exists.", ephemeral=True)
            return
        
        # Create new item using the factory
        new_item = build_and_save_entity(
            system=repositories.server.get_system(self.guild_id),
            entity_type=EntityType.ITEM,
            name=name,
            owner_id=str(interaction.user.id),
            guild_id=self.guild_id,
            notes=[description] if description else None
        )
        
        # Add to character's inventory
        parent.add_item(self.guild_id, new_item, quantity=quantity)
        repositories.entity.upsert_entity(interaction.guild.id, parent, system=parent.system)
        
        await interaction.response.edit_message(
            content=f"✅ Created and added **{name}** to inventory.",
            view=EditInventoryView(interaction.guild.id, interaction.user.id, self.parent_id)
        )

class TransferItemView(ui.View):
    """Unified view for transferring items between entities"""
    
    def __init__(self, parent_id: str, guild_id: int, user_id: int, item: BaseEntity = None, parent_view=None):
        super().__init__(timeout=300)
        self.parent_id = parent_id
        self.guild_id = guild_id
        self.user_id = user_id
        self.selected_item = item
        self.selected_target = None
        self.parent_view = parent_view
        self.build_components()
    
    def build_components(self):
        self.clear_items()
        
        # Item selection dropdown (only if the item hasn't already been selected)
        if not self.selected_item:
            item_options = self._get_available_items()
            if item_options:
                item_select = ui.Select(
                    placeholder="Select item to transfer...",
                    options=item_options[:25],
                    row=0
                )
                item_select.callback = self.item_selected
                self.add_item(item_select)
        
        # Target selection dropdown (only show after item is selected)
        if self.selected_item and not self.selected_target:
            target_options = self._get_available_targets()
            if target_options:
                target_select = ui.Select(
                    placeholder="Select destination...",
                    options=target_options[:25],
                    row=1
                )
                target_select.callback = self.target_selected
                self.add_item(target_select)
        
        # Transfer button (only show when both item and target selected)
        if self.selected_item and self.selected_target:
            transfer_btn = ui.Button(
                label=f"Transfer {self.selected_item.name} to {self.selected_target.name}",
                style=discord.ButtonStyle.success,
                row=2
            )
            transfer_btn.callback = self.confirm_transfer
            self.add_item(transfer_btn)

    async def item_selected(self, interaction: discord.Interaction):
        """Handle item selection from dropdown"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return
        
        selected_item_id = interaction.data['values'][0]
        
        # Find the selected item
        source = repositories.entity.get_by_id(self.parent_id)
        items = source.get_inventory(self.guild_id)
        selected_item_entity = next((item for item in items if item.id == selected_item_id), None)
        
        if not selected_item_entity:
            await interaction.response.send_message("❌ Selected item not found.", ephemeral=True)
            return
        
        # Get quantity info
        links = source.get_links_to_entity(self.guild_id, selected_item_id, EntityLinkType.POSSESSES)
        quantity = links[0].metadata.get("quantity", 1) if links else 1
        
        # Store selection
        self.selected_item = selected_item_entity
        
        # Rebuild components to show target selection
        self.build_components()
        
        await interaction.response.edit_message(
            content=f"Selected **{selected_item_entity.name}** (x{quantity}). Now select destination:",
            view=self
        )
    
    async def target_selected(self, interaction: discord.Interaction):
        """Handle target selection from dropdown"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return
        
        selected_target_id = interaction.data['values'][0]
        
        # Find the selected target entity
        target_entity = repositories.entity.get_by_id(selected_target_id)
        if not target_entity:
            await interaction.response.send_message("❌ Selected destination not found.", ephemeral=True)
            return
        
        # Verify user has access to the target
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not target_entity.can_be_accessed_by(self.user_id, is_gm):
            await interaction.response.send_message("❌ You don't have access to that destination.", ephemeral=True)
            return
        
        # Store selection
        self.selected_target = target_entity
        
        # Rebuild components to show transfer button
        self.build_components()

        quantity = repositories.link.get_possessed_quantity(interaction.guild.id, self.parent_id, self.selected_item.id)
        
        await interaction.response.edit_message(
            content=f"Transfer **{self.selected_item.name}** (x{quantity}) to **{target_entity.name}**:",
            view=self
        )
    
    async def confirm_transfer(self, interaction: discord.Interaction):
        """Handle the final transfer confirmation"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return
        
        if not self.selected_item or not self.selected_target:
            await interaction.response.send_message("❌ Please select both an item and destination.", ephemeral=True)
            return
        
        # Show quantity selection modal with parent view tracking
        await interaction.response.send_modal(
            TransferQuantityModal(
                self.selected_item,
                self.selected_target,
                self.parent_id,
                self.guild_id,
                parent_view=self.parent_view
            )
        )
    
    def _get_available_items(self):
        """Get items available for transfer from source entity"""
        source = repositories.entity.get_by_id(self.parent_id)
        items = source.get_inventory(self.guild_id)
        
        options = []
        for item in items[:25]:  # Discord limit
            # Get quantity info
            links = source.get_links_to_entity(self.guild_id, item.id, EntityLinkType.POSSESSES)
            quantity = links[0].metadata.get("quantity", 1) if links else 1
            quantity_str = f" (x{quantity})" if quantity > 1 else ""
            
            options.append(discord.SelectOption(
                label=f"{item.name}{quantity_str}",
                value=item.id,
                description=f"Available: {quantity}"
            ))
        
        return options
    
    def _get_available_targets(self):
        """Get available transfer destinations"""
        options = []
        
        # Get user's characters
        user_chars = repositories.character.get_accessible_characters(self.guild_id, self.user_id)
        for char in user_chars:
            if char.id != self.parent_id:  # Don't include source
                options.append(discord.SelectOption(
                    label=f"{char.name} ({char.entity_type.value})",
                    value=char.id,
                    description="Your character"
                ))
        
        # Get accessible containers
        containers = repositories.entity.get_all_by_type(self.guild_id, EntityType.CONTAINER)
        for container in containers:
            if container.id != self.parent_id and container.can_be_accessed_by(self.user_id, False):
                options.append(discord.SelectOption(
                    label=f"{container.name} (Container)",
                    value=container.id,
                    description="Container"
                ))
        
        return options[:25]
    
class TransferQuantityModal(ui.Modal, title="Transfer Quantity"):
    """Modal for specifying transfer quantity"""
    
    def __init__(self, selected_item: BaseEntity, selected_target: BaseEntity, source_entity_id: str, guild_id: str, parent_view=None):
        super().__init__()
        self.selected_item = selected_item
        self.selected_target = selected_target
        self.source_entity_id = source_entity_id
        self.guild_id = guild_id
        self.quantity = repositories.link.get_possessed_quantity(guild_id, source_entity_id, selected_item.id)
        self.parent_view = parent_view  # Track the parent view
        
        self.quantity_field = ui.TextInput(
            label="Quantity to Transfer",
            placeholder=f"Max: {self.quantity}",
            default=str(self.quantity),
            required=True,
            max_length=10
        )
        self.add_item(self.quantity_field)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            transfer_quantity = int(self.quantity_field.value.strip())
            if transfer_quantity <= 0:
                await interaction.response.send_message("❌ Transfer quantity must be greater than 0.", ephemeral=True)
                return
            if transfer_quantity > self.quantity:
                await interaction.response.send_message(
                    f"❌ Cannot transfer {transfer_quantity}. Only {self.quantity} available.",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
            return
        
        # Perform the transfer
        source_entity = repositories.entity.get_by_id(self.source_entity_id)
        target_entity = self.selected_target
        item_entity = self.selected_item
        
        # Remove from source
        source_entity.remove_item(self.guild_id, item_entity, transfer_quantity)
        
        # Add to target
        target_entity.add_item(self.guild_id, item_entity, transfer_quantity)
        
        # Save both entities
        repositories.entity.upsert_entity(interaction.guild.id, source_entity, system=source_entity.system)
        repositories.entity.upsert_entity(interaction.guild.id, target_entity, system=target_entity.system)
        
        # Refresh parent view if it exists
        if self.parent_view:
            await self._refresh_parent_view(interaction, transfer_quantity, item_entity, source_entity, target_entity)
        else:
            await interaction.response.edit_message(
                content=f"✅ Transferred {transfer_quantity}x **{item_entity.name}** from **{source_entity.name}** to **{target_entity.name}**.",
                view=None,
                embed=None
            )

    async def _refresh_parent_view(self, interaction: discord.Interaction, transfer_quantity, item_entity: BaseEntity, source_entity: BaseEntity, target_entity: BaseEntity):
        """Refresh the parent view based on its type"""
        if isinstance(self.parent_view, EditInventoryView):
            # Refresh inventory view
            self.parent_view.load_data()
            self.parent_view.render()
            
            await interaction.response.edit_message(
                content=f"✅ Transferred {transfer_quantity}x **{item_entity.name}** to **{target_entity.name}**. Inventory updated.",
                view=self.parent_view,
                embed=None
            )
        elif hasattr(self.parent_view, 'format_full_sheet'):
            # Refresh character sheet view
            is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            updated_embed = source_entity.format_full_sheet(interaction.guild.id, is_gm=is_gm)
            updated_view = source_entity.get_sheet_edit_view(interaction.user.id, is_gm=is_gm)
            
            await interaction.response.edit_message(
                content=f"✅ Transferred {transfer_quantity}x **{item_entity.name}** to **{target_entity.name}**.",
                embed=updated_embed,
                view=updated_view
            )
        else:
            # Default fallback
            await interaction.response.edit_message(
                content=f"✅ Transferred {transfer_quantity}x **{item_entity.name}** from **{source_entity.name}** to **{target_entity.name}**.",
                view=None,
                embed=None
            )