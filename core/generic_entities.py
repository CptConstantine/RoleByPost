from typing import Any, ClassVar, Dict, List
import discord
from discord import ui

from core.generic_roll_mechanics import execute_roll
from .base_models import AccessType, BaseCharacter, BaseEntity, EntityDefaults, EntityType, EntityLinkType, SystemType
from .inventory_views import EditInventoryView
from .shared_views import EditNameModal, EditNotesModal
from .generic_roll_formulas import GenericRollFormula, RollFormula


class GenericEntity(BaseEntity):
    """Generic system entity - simple entity with basic properties"""
    SUPPORTED_ENTITY_TYPES: ClassVar[List[EntityType]] = [EntityType.OTHER, EntityType.ITEM]
    
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.OTHER: {
        },
        EntityType.ITEM: {
        }
    })
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericEntity":
        return cls(data)
    
    def get_sheet_edit_view(self, editor_id: int, is_gm: bool) -> ui.View:
        return GenericSheetEditView(editor_id=editor_id, char_id=self.id, system=self.system)
    
    def apply_defaults(self, entity_type: EntityType = None, guild_id: str = None):
        """Apply defaults for generic entities"""
        super().apply_defaults(entity_type=entity_type, guild_id=guild_id)

class GenericCharacter(BaseCharacter):
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.PC: {
        },
        EntityType.NPC: {
        }
    })

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericCharacter":
        return cls(data)
    
    def apply_defaults(self, entity_type = None, guild_id = None):
        super().apply_defaults(entity_type, guild_id)

        if self.ENTITY_DEFAULTS:
            defaults = self.ENTITY_DEFAULTS.get_defaults(entity_type)
            for key, value in defaults.items():
                self._apply_default_field(key, value, guild_id) 
    
    def get_sheet_edit_view(self, editor_id: int, is_gm: bool) -> ui.View:
        return GenericSheetEditView(editor_id=editor_id, char_id=self.id, system=self.system)

    def format_full_sheet(self, guild_id: int, is_gm: bool = False) -> discord.Embed:
        """Format the character sheet for generic system"""
        embed = discord.Embed(
            title=f"{self.name or 'Character'}",
            color=discord.Color.greyple()
        )

        # --- Inventory ---
        items = self.get_inventory(guild_id=guild_id)
        if items:
            # Group items by entity type and count them
            item_counts = {}
            for item in items:
                entity_type = item.entity_type
                if entity_type in item_counts:
                    item_counts[entity_type] += 1
                else:
                    item_counts[entity_type] = 1
            
            # Format the display
            item_lines = [f"• {entity_type.value}(s): {count}" for entity_type, count in item_counts.items()]
            embed.add_field(name="__Inventory__", value="\n".join(item_lines), inline=False)
        else:
            embed.add_field(name="__Inventory__", value="None", inline=False)

        notes = self.notes
        notes_display = "\n".join(notes) if notes else "_No notes_"
        embed.add_field(name="Notes", value=notes_display, inline=False)

        return embed

    def format_npc_scene_entry(self, is_gm: bool) -> str:
        """Format NPC entry for scene display"""
        lines = [f"**{self.name or 'NPC'}**"]
        if is_gm and self.notes:
            notes_display = "\n".join(self.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        return "\n".join(lines)

    async def edit_requested_roll(self, interaction: discord.Interaction, roll_formula_obj: "GenericRollFormula", difficulty: int = None):
        """
        Opens a view for editing the roll parameters.
        Generic version doesn't have skill selection but does allow modifier adjustment.
        """
        from core import factories
        view = factories.get_specific_roll_formula_view(interaction.guild_id, self, SystemType.GENERIC, roll_formula_obj, difficulty)
        await interaction.response.send_message(
            content="Adjust your roll formula as needed, then finalize to roll.",
            view=view,
            ephemeral=True
        )

    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollFormula, difficulty: int = None):
        """
        Prints the roll result using configured roll mechanics
        """
        result = execute_roll(roll_formula_obj, modifier=0, difficulty=difficulty)
        await interaction.response.send_message(result['description'], ephemeral=False)

class GenericCompanion(BaseCharacter):
    """
    System-agnostic companion class that any system can use if there is no system-specific companion implementation.
    """
    SUPPORTED_ENTITY_TYPES: ClassVar[List[EntityType]] = [EntityType.COMPANION]

    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.COMPANION: {
        }
    })
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        if self.entity_type != EntityType.COMPANION:
            self.entity_type = EntityType.COMPANION
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericCompanion":
        return cls(data)
    
    def get_sheet_edit_view(self, editor_id: int, is_gm: bool) -> ui.View:
        return GenericSheetEditView(editor_id=editor_id, char_id=self.id, system=self.system)

    def format_full_sheet(self, guild_id: int, is_gm: bool = False) -> discord.Embed:
        """Format the companion sheet"""
        embed = discord.Embed(
            title=f"{self.name or 'Companion'} (Companion)",
            color=discord.Color.blue()
        )
        
        # Add notes
        notes = self.notes
        if notes:
            notes_display = "\n".join(notes)
            embed.add_field(name="Notes", value=notes_display, inline=False)
        
        return embed
    
    def format_npc_scene_entry(self, is_gm: bool) -> str:
        """Format companion entry for scene display"""
        lines = [f"**{self.name or 'Companion'}** (Companion)"]
        
        if is_gm and self.notes:
            notes_display = "\n".join(self.notes)
            lines.append(f"**Notes:** *{notes_display}*")
        
        return "\n".join(lines)
    
    async def edit_requested_roll(self, interaction: discord.Interaction, roll_parameters: dict, difficulty: int = None):
        """Handle roll request for companions - uses generic system"""
        from core.generic_entities import GenericRollFormula
        from core import factories
        
        roll_formula_obj = GenericRollFormula(roll_parameters)
        view = factories.get_specific_roll_formula_view(interaction.guild_id, self, SystemType.GENERIC, roll_formula_obj, difficulty)

        await interaction.response.send_message(
            content=f"Rolling for {self.name}. Adjust as needed:",
            view=view,
            ephemeral=True
        )
    
    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollFormula, difficulty: int = None):
        """
        Prints the roll result using configured roll mechanics
        """
        result = execute_roll(roll_formula_obj, modifier=0, difficulty=difficulty)
        await interaction.response.send_message(result['description'], ephemeral=False)

class GenericSheetEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str, system: SystemType):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id
        self.system = system

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=0)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNameModal(self.char_id, self.system))

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=0)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNotesModal(self.char_id, self.system))
    
    @ui.button(label="Inventory", style=discord.ButtonStyle.secondary, row=3)
    async def edit_inventory(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(content="Editing inventory:", view=EditInventoryView(interaction.guild.id, self.editor_id, self.char_id))

class GenericContainer(BaseEntity):
    """A container that can hold items for loot distribution"""
    SUPPORTED_ENTITY_TYPES: ClassVar[List[EntityType]] = [EntityType.CONTAINER]
    
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.CONTAINER: {
            "max_items": 0,  # 0 = unlimited
            "is_locked": False
        }
    })

    @property
    def max_items(self) -> int:
        """Maximum number of items this container can hold. 0 means unlimited."""
        return self.data.get("max_items", 0)
    
    @max_items.setter
    def max_items(self, value: int):
        """Set the maximum number of items this container can hold."""
        if value < 0:
            raise ValueError("max_items cannot be negative")
        self.data["max_items"] = value
    
    @property
    def is_locked(self) -> bool:
        """Whether the container is locked."""
        return self.data.get("is_locked", False)

    @is_locked.setter
    def is_locked(self, value: bool):
        """Set whether the container is locked."""
        self.data["is_locked"] = value

    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        if self.entity_type != EntityType.CONTAINER:
            self.entity_type = EntityType.CONTAINER
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericContainer":
        return cls(data)
    
    def get_sheet_edit_view(self, editor_id: int, is_gm: bool) -> ui.View:
        return GenericContainerEditView(editor_id=editor_id, char_id=self.id, system=self.system, is_gm=is_gm)

    def format_full_sheet(self, guild_id: int, is_gm: bool = False) -> discord.Embed:
        """Format the container sheet"""
        embed = discord.Embed(
            title=f"{self.name or 'Container'} (Container)",
            color=discord.Color.gold()
        )
        
        # Only show properties and access control to GMs
        if is_gm:
            # Container properties
            max_items = self.data.get("max_items", 0)
            is_locked = self.data.get("is_locked", False)
            
            # Format access control display
            access_display = self.access_type.value.title()
            embed.add_field(
                name="🔧 Properties (GM Only)",
                value=f"**Max Items:** {'Unlimited' if max_items == 0 else max_items}\n"
                      f"**Locked:** {'Yes' if is_locked else 'No'}\n"
                      f"**Access:** {access_display}",
                inline=False
            )
        
        # Show contained items (visible to everyone who can access the container)
        contained_items = self.get_contained_items(guild_id)
        if contained_items:
            items_display = []
            for item in contained_items:
                # Get quantity from link metadata if available
                links = self.get_links_to_entity(guild_id, item.id, EntityLinkType.POSSESSES)
                quantity = 1
                if links:
                    quantity = links[0].metadata.get("quantity", 1)
                
                quantity_str = f" x{quantity}" if quantity > 1 else ""
                items_display.append(f"• {item.name}{quantity_str}")
            
            embed.add_field(
                name=f"📦 Contents ({len(contained_items)})",
                value="\n".join(items_display)[:1024],
                inline=False
            )
        else:
            embed.add_field(name="📦 Contents", value="*Empty*", inline=False)
        
        # Add notes (visible to everyone)
        notes = self.notes
        if notes:
            notes_display = "\n".join(notes)
            embed.add_field(name="📝 Notes", value=notes_display, inline=False)
        
        return embed

    def reveal_to_players(self) -> None:
        """Set container access to public (reveal to all players)"""
        self.set_access_type(AccessType.PUBLIC)
    
    def apply_defaults(self, entity_type: EntityType = None, guild_id: str = None):
        """Apply defaults for containers"""
        super().apply_defaults(entity_type=entity_type, guild_id=guild_id)
        
        if self.ENTITY_DEFAULTS:
            defaults = self.ENTITY_DEFAULTS.get_defaults(EntityType.CONTAINER)
            for key, value in defaults.items():
                self._apply_default_field(key, value, guild_id)

class GenericContainerEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str, system: SystemType, is_gm: bool = False):
        super().__init__(timeout=60*60*24)  # 24 hours timeout
        self.editor_id = editor_id
        self.char_id = char_id
        self.system = system
        self.is_gm = is_gm
        
        # Build the view components based on current state
        self.build_view_components()

    def build_view_components(self):
        """Build view components based on GM status"""
        self.clear_items()
        
        # Add basic management buttons for GM/owner
        if self.is_gm:
            edit_name_button = ui.Button(label="Edit Name", style=discord.ButtonStyle.secondary, row=0)
            edit_name_button.callback = self.edit_name
            self.add_item(edit_name_button)
            
            edit_notes_button = ui.Button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=0)
            edit_notes_button.callback = self.edit_notes
            self.add_item(edit_notes_button)
        
        refresh_button = ui.Button(label="🔄 Refresh", style=discord.ButtonStyle.secondary, row=0)
        refresh_button.callback = self.refresh_view
        self.add_item(refresh_button)
        
        # Add reveal button only for GM/owner when container is not public
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        if container and self.is_gm and container.access_type != AccessType.PUBLIC:
            reveal_button = ui.Button(label="📢 Reveal to Players", style=discord.ButtonStyle.success, row=0)
            reveal_button.callback = self.reveal_to_players
            self.add_item(reveal_button)

        # Item interaction buttons - use modern UI approach
        transfer_to_button = ui.Button(label="📤 Take Items", style=discord.ButtonStyle.success, row=1)
        transfer_to_button.callback = self.take_items_interactive
        self.add_item(transfer_to_button)
        
        transfer_from_button = ui.Button(label="📥 Give Items", style=discord.ButtonStyle.primary, row=1)
        transfer_from_button.callback = self.give_items_interactive
        self.add_item(transfer_from_button)
        
        # Management buttons (GM/owner only)
        if self.is_gm:
            access_button = ui.Button(label="🔒 Access Control", style=discord.ButtonStyle.secondary, row=2)
            access_button.callback = self.manage_access
            self.add_item(access_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Update the is_gm flag for proper display
        if self.is_gm != is_gm:
            self.is_gm = is_gm
            self.build_view_components()
        
        if not container.can_be_accessed_by(str(interaction.user.id), is_gm):
            await interaction.response.send_message("❌ You don't have access to this container.", ephemeral=True)
            return False
        return True

    async def _refresh_container_view(self, interaction: discord.Interaction, message: str = None):
        """Helper method to refresh the container view with updated data"""
        from data.repositories.repository_factory import repositories
        
        container = repositories.entity.get_by_id(self.char_id)
        if not container:
            await interaction.response.send_message("❌ Container not found.", ephemeral=True)
            return
        
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        embed = container.format_full_sheet(interaction.guild.id, is_gm=is_gm)
        new_view = GenericContainerEditView(self.editor_id, self.char_id, self.system, is_gm=is_gm)
        
        content = message or f"📦 **{container.name}**"
        await interaction.response.edit_message(content=content, embed=embed, view=new_view)

    async def edit_name(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ Only the owner or GM can edit the container name.", ephemeral=True)
            return
            
        await interaction.response.send_modal(EditNameModal(self.char_id, self.system))

    async def edit_notes(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ Only the owner or GM can edit the container notes.", ephemeral=True)
            return
            
        await interaction.response.send_modal(EditNotesModal(self.char_id, self.system))

    async def refresh_view(self, interaction: discord.Interaction):
        """Refresh the container display with current data"""
        await self._refresh_container_view(interaction)

    async def reveal_to_players(self, interaction: discord.Interaction):
        """Reveal the container to all players by making it public"""
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ Only the owner or GM can reveal containers to players.", ephemeral=True)
            return
        
        container.reveal_to_players()
        repositories.entity.upsert_entity(str(interaction.guild.id), container, system=container.system)
        
        # Send a public message announcing the reveal
        embed = container.format_full_sheet(interaction.guild.id, is_gm=False)
        public_view = GenericContainerEditView(interaction.user.id, self.char_id, self.system, is_gm=False)
        
        await interaction.response.send_message(
            content=f"📦 **{container.name}** has been revealed!",
            embed=embed,
            view=public_view,
            ephemeral=False
        )

    async def take_items_interactive(self, interaction: discord.Interaction):
        """Interactive item taking using dropdown selection"""
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        
        # Check if container is locked
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if container.is_locked and not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ This container is locked.", ephemeral=True)
            return
        
        # Show interactive take view
        view = ContainerTakeView(self.char_id, interaction.guild.id, interaction.user.id, parent_view=self)
        await interaction.response.edit_message(
            content=f"📤 **Take items from {container.name}**\nSelect an item and character:",
            view=view
        )

    async def give_items_interactive(self, interaction: discord.Interaction):
        """Interactive item giving using dropdown selection"""
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        
        # Show interactive give view
        view = ContainerGiveView(self.char_id, interaction.guild.id, interaction.user.id, parent_view=self)
        await interaction.response.edit_message(
            content=f"📥 **Give items to {container.name}**\nSelect a character and item:",
            view=view
        )
    
    async def manage_access(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ Only the owner or GM can manage access control.", ephemeral=True)
            return
            
        await interaction.response.send_modal(ContainerAccessModal(self.char_id))


class ContainerAccessModal(ui.Modal, title="Manage Container Access"):
    def __init__(self, container_id: str):
        super().__init__()
        self.container_id = container_id
        
    access_type = ui.TextInput(
        label="Access Type",
        placeholder="Enter: public or gm",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        
        container = repositories.entity.get_by_id(self.container_id)
        if not container:
            await interaction.response.send_message("❌ Container not found.", ephemeral=True)
            return
        
        access_type = self.access_type.value.strip().lower()
        valid_types = ["public", "gm"]
        
        if access_type not in valid_types:
            await interaction.response.send_message(
                f"❌ Invalid access type. Must be one of: {', '.join(valid_types)}", 
                ephemeral=True
            )
            return
        
        access_type = AccessType(access_type if access_type == "public" else "gm_only")
        
        try:
            container.set_access_type(access_type)
            
            repositories.entity.upsert_entity(str(interaction.guild.id), container, system=container.system)
            await interaction.response.edit_message(
                f"✅ Updated {container.name} access to '{access_type.value}'.",
                embed=container.format_full_sheet(interaction.guild.id, is_gm=True),
                view=GenericContainerEditView(
                    interaction.user.id,
                    container_id=container.id,
                    system=container.system,
                    is_gm=True
                ),
                ephemeral=True
            )
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error updating access control: {str(e)}", ephemeral=True)

class ContainerTakeView(ui.View):
    """Interactive view for taking items from container"""
    
    def __init__(self, container_id: str, guild_id: int, user_id: int, parent_view=None):
        super().__init__(timeout=300)
        self.container_id = container_id
        self.guild_id = guild_id
        self.user_id = user_id
        self.parent_view = parent_view
        self.selected_item = None
        self.selected_character = None
        self.build_components()
    
    def build_components(self):
        self.clear_items()
        
        # Item selection dropdown
        if not self.selected_item:
            item_options = self._get_container_items()
            if item_options:
                item_select = ui.Select(
                    placeholder="Select item to take...",
                    options=item_options[:25],
                    row=0
                )
                item_select.callback = self.item_selected
                self.add_item(item_select)
            else:
                self.add_item(ui.Button(label="No items in container", disabled=True, row=0))
        
        # Character selection dropdown (only show after item is selected)
        if self.selected_item and not self.selected_character:
            char_options = self._get_user_characters()
            if char_options:
                char_select = ui.Select(
                    placeholder="Select character to receive item...",
                    options=char_options[:25],
                    row=1
                )
                char_select.callback = self.character_selected
                self.add_item(char_select)
        
        # Transfer button (only show when both are selected)
        if self.selected_item and self.selected_character:
            transfer_btn = ui.Button(
                label=f"Take {self.selected_item['name']} → {self.selected_character['name']}",
                style=discord.ButtonStyle.success,
                row=2
            )
            transfer_btn.callback = self.confirm_take
            self.add_item(transfer_btn)
        
        # Back button
        back_btn = ui.Button(label="🔙 Back to Container", style=discord.ButtonStyle.secondary, row=3)
        back_btn.callback = self.back_to_container
        self.add_item(back_btn)
    
    def _get_container_items(self):
        """Get items available in the container"""
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.container_id)
        items = container.get_contained_items(self.guild_id)
        
        options = []
        for item in items[:25]:
            # Get quantity
            links = container.get_links_to_entity(self.guild_id, item.id, EntityLinkType.POSSESSES)
            quantity = links[0].metadata.get("quantity", 1) if links else 1
            quantity_str = f" (x{quantity})" if quantity > 1 else ""
            
            options.append(discord.SelectOption(
                label=f"{item.name}{quantity_str}",
                value=item.id,
                description=f"Available: {quantity}"
            ))
        
        return options
    
    def _get_user_characters(self):
        """Get characters accessible to the user"""
        from data.repositories.repository_factory import repositories
        user_chars = repositories.character.get_accessible_characters(self.guild_id, self.user_id)
        
        options = []
        for char in user_chars[:25]:
            options.append(discord.SelectOption(
                label=f"{char.name} ({char.entity_type.value})",
                value=char.id,
                description=f"Character"
            ))
        
        return options
    
    async def item_selected(self, interaction: discord.Interaction):
        """Handle item selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this interface.", ephemeral=True)
            return
        
        selected_item_id = interaction.data['values'][0]
        
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.container_id)
        items = container.get_contained_items(self.guild_id)
        selected_item_entity = next((item for item in items if item.id == selected_item_id), None)
        
        if not selected_item_entity:
            await interaction.response.send_message("❌ Selected item not found.", ephemeral=True)
            return
        
        # Get quantity
        links = container.get_links_to_entity(self.guild_id, selected_item_id, EntityLinkType.POSSESSES)
        quantity = links[0].metadata.get("quantity", 1) if links else 1
        
        self.selected_item = {
            'id': selected_item_id,
            'entity': selected_item_entity,
            'name': selected_item_entity.name,
            'quantity': quantity
        }
        
        self.build_components()
        await interaction.response.edit_message(
            content=f"📤 **Take {selected_item_entity.name}** (x{quantity})\nNow select the character:",
            view=self
        )
    
    async def character_selected(self, interaction: discord.Interaction):
        """Handle character selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this interface.", ephemeral=True)
            return
        
        selected_char_id = interaction.data['values'][0]
        
        from data.repositories.repository_factory import repositories
        character = repositories.entity.get_by_id(selected_char_id)
        if not character:
            await interaction.response.send_message("❌ Selected character not found.", ephemeral=True)
            return
        
        # Verify access
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not character.can_be_accessed_by(str(self.user_id), is_gm):
            await interaction.response.send_message("❌ You don't have access to that character.", ephemeral=True)
            return
        
        self.selected_character = {
            'id': selected_char_id,
            'entity': character,
            'name': character.name
        }
        
        self.build_components()
        await interaction.response.edit_message(
            content=f"📤 **Take {self.selected_item['name']}** → **{character.name}**",
            view=self
        )
    
    async def confirm_take(self, interaction: discord.Interaction):
        """Show quantity modal for the transfer"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this interface.", ephemeral=True)
            return
        
        await interaction.response.send_modal(
            ContainerTakeQuantityModal(
                self.selected_item,
                self.selected_character,
                self.container_id,
                self.guild_id,
                parent_view=self.parent_view
            )
        )
    
    async def back_to_container(self, interaction: discord.Interaction):
        """Return to the main container view"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this interface.", ephemeral=True)
            return
        
        if self.parent_view:
            await self.parent_view._refresh_container_view(interaction)
        else:
            from data.repositories.repository_factory import repositories
            container = repositories.entity.get_by_id(self.container_id)
            is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            embed = container.format_full_sheet(interaction.guild.id, is_gm=is_gm)
            view = GenericContainerEditView(interaction.user.id, self.container_id, container.system, is_gm=is_gm)
            
            await interaction.response.edit_message(
                content=f"📦 **{container.name}**",
                embed=embed,
                view=view
            )


class ContainerGiveView(ui.View):
    """Interactive view for giving items to container"""
    
    def __init__(self, container_id: str, guild_id: int, user_id: int, parent_view=None):
        super().__init__(timeout=300)
        self.container_id = container_id
        self.guild_id = guild_id
        self.user_id = user_id
        self.parent_view = parent_view
        self.selected_character = None
        self.selected_item = None
        self.build_components()
    
    def build_components(self):
        self.clear_items()
        
        # Character selection dropdown
        char_options = self._get_user_characters()
        if char_options and not self.selected_character:
            char_select = ui.Select(
                placeholder="Select character to give from...",
                options=char_options[:25],
                row=0
            )
            char_select.callback = self.character_selected
            self.add_item(char_select)
        else:
            self.add_item(ui.Button(label="No accessible characters", disabled=True, row=0))
        
        # Item selection dropdown (only show after character is selected)
        if self.selected_character and not self.selected_item:
            item_options = self._get_character_items()
            if item_options:
                item_select = ui.Select(
                    placeholder="Select item to give...",
                    options=item_options[:25],
                    row=1
                )
                item_select.callback = self.item_selected
                self.add_item(item_select)
            else:
                self.add_item(ui.Button(label="Character has no items", disabled=True, row=1))
        
        # Transfer button (only show when both are selected)
        if self.selected_character and self.selected_item:
            transfer_btn = ui.Button(
                label=f"Give {self.selected_item['name']} from {self.selected_character['name']}",
                style=discord.ButtonStyle.primary,
                row=2
            )
            transfer_btn.callback = self.confirm_give
            self.add_item(transfer_btn)
        
        # Back button
        back_btn = ui.Button(label="🔙 Back to Container", style=discord.ButtonStyle.secondary, row=3)
        back_btn.callback = self.back_to_container
        self.add_item(back_btn)
    
    def _get_user_characters(self):
        """Get characters accessible to the user"""
        from data.repositories.repository_factory import repositories
        user_chars = repositories.character.get_accessible_characters(self.guild_id, self.user_id)
        
        options = []
        for char in user_chars[:25]:
            options.append(discord.SelectOption(
                label=f"{char.name} ({char.entity_type.value})",
                value=char.id,
                description=f"Character"
            ))
        
        return options
    
    def _get_character_items(self):
        """Get items from the selected character"""
        if not self.selected_character:
            return []
        
        character = self.selected_character['entity']
        items = character.get_inventory(self.guild_id)
        
        options = []
        for item in items[:25]:
            # Get quantity
            links = character.get_links_to_entity(self.guild_id, item.id, EntityLinkType.POSSESSES)
            quantity = links[0].metadata.get("quantity", 1) if links else 1
            quantity_str = f" (x{quantity})" if quantity > 1 else ""
            
            options.append(discord.SelectOption(
                label=f"{item.name}{quantity_str}",
                value=item.id,
                description=f"Available: {quantity}"
            ))
        
        return options
    
    async def character_selected(self, interaction: discord.Interaction):
        """Handle character selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this interface.", ephemeral=True)
            return
        
        selected_char_id = interaction.data['values'][0]
        
        from data.repositories.repository_factory import repositories
        character = repositories.entity.get_by_id(selected_char_id)
        if not character:
            await interaction.response.send_message("❌ Selected character not found.", ephemeral=True)
            return
        
        # Verify access
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not character.can_be_accessed_by(str(self.user_id), is_gm):
            await interaction.response.send_message("❌ You don't have access to that character.", ephemeral=True)
            return
        
        self.selected_character = {
            'id': selected_char_id,
            'entity': character,
            'name': character.name
        }
        
        self.build_components()
        await interaction.response.edit_message(
            content=f"📥 **Give items from {character.name}**\nNow select the item:",
            view=self
        )
    
    async def item_selected(self, interaction: discord.Interaction):
        """Handle item selection"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this interface.", ephemeral=True)
            return
        
        selected_item_id = interaction.data['values'][0]
        
        character = self.selected_character['entity']
        items = character.get_inventory(self.guild_id)
        selected_item_entity = next((item for item in items if item.id == selected_item_id), None)
        
        if not selected_item_entity:
            await interaction.response.send_message("❌ Selected item not found.", ephemeral=True)
            return
        
        # Get quantity
        links = character.get_links_to_entity(self.guild_id, selected_item_id, EntityLinkType.POSSESSES)
        quantity = links[0].metadata.get("quantity", 1) if links else 1
        
        self.selected_item = {
            'id': selected_item_id,
            'entity': selected_item_entity,
            'name': selected_item_entity.name,
            'quantity': quantity
        }
        
        self.build_components()
        await interaction.response.edit_message(
            content=f"📥 **Give {selected_item_entity.name}** from **{self.selected_character['name']}**",
            view=self
        )
    
    async def confirm_give(self, interaction: discord.Interaction):
        """Show quantity modal for the transfer"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this interface.", ephemeral=True)
            return
        
        await interaction.response.send_modal(
            ContainerGiveQuantityModal(
                self.selected_character,
                self.selected_item,
                self.container_id,
                self.guild_id,
                parent_view=self.parent_view
            )
        )
    
    async def back_to_container(self, interaction: discord.Interaction):
        """Return to the main container view"""
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("You can't use this interface.", ephemeral=True)
            return
        
        if self.parent_view:
            await self.parent_view._refresh_container_view(interaction)
        else:
            from data.repositories.repository_factory import repositories
            container = repositories.entity.get_by_id(self.container_id)
            is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            embed = container.format_full_sheet(interaction.guild.id, is_gm=is_gm)
            view = GenericContainerEditView(interaction.user.id, self.container_id, container.system, is_gm=is_gm)
            
            await interaction.response.edit_message(
                content=f"📦 **{container.name}**",
                embed=embed,
                view=view
            )


class ContainerTakeQuantityModal(ui.Modal, title="Take Items"):
    """Modal for specifying take quantity"""
    
    def __init__(self, selected_item: dict, selected_character: dict, container_id: str, guild_id: int, parent_view=None):
        super().__init__()
        self.selected_item = selected_item
        self.selected_character = selected_character
        self.container_id = container_id
        self.guild_id = guild_id
        self.parent_view = parent_view
        
        self.quantity_field = ui.TextInput(
            label="Quantity to Take",
            placeholder=f"Max: {selected_item['quantity']}",
            default=str(selected_item['quantity']),
            required=True,
            max_length=10
        )
        self.add_item(self.quantity_field)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            take_quantity = int(self.quantity_field.value.strip())
            if take_quantity <= 0:
                await interaction.response.send_message("❌ Quantity must be greater than 0.", ephemeral=True)
                return
            if take_quantity > self.selected_item['quantity']:
                await interaction.response.send_message(
                    f"❌ Cannot take {take_quantity}. Only {self.selected_item['quantity']} available.",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
            return
        
        # Perform the transfer
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.container_id)
        character = self.selected_character['entity']
        item_entity = self.selected_item['entity']
        
        # Remove from container
        container.remove_item(self.guild_id, item_entity, take_quantity)
        
        # Add to character
        character.add_item(self.guild_id, item_entity, take_quantity)
        
        # Save both entities
        repositories.entity.upsert_entity(self.guild_id, container, system=container.system)
        repositories.entity.upsert_entity(self.guild_id, character, system=character.system)
        
        # Refresh parent view
        success_message = f"✅ **{character.name}** took {take_quantity}x **{item_entity.name}** from **{container.name}**"
        
        if self.parent_view:
            await self.parent_view._refresh_container_view(interaction, success_message)
        else:
            await interaction.response.edit_message(content=success_message, view=None, embed=None)


class ContainerGiveQuantityModal(ui.Modal, title="Give Items"):
    """Modal for specifying give quantity"""
    
    def __init__(self, selected_character: dict, selected_item: dict, container_id: str, guild_id: int, parent_view=None):
        super().__init__()
        self.selected_character = selected_character
        self.selected_item = selected_item
        self.container_id = container_id
        self.guild_id = guild_id
        self.parent_view = parent_view
        
        self.quantity_field = ui.TextInput(
            label="Quantity to Give",
            placeholder=f"Max: {selected_item['quantity']}",
            default=str(selected_item['quantity']),
            required=True,
            max_length=10
        )
        self.add_item(self.quantity_field)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            give_quantity = int(self.quantity_field.value.strip())
            if give_quantity <= 0:
                await interaction.response.send_message("❌ Quantity must be greater than 0.", ephemeral=True)
                return
            if give_quantity > self.selected_item['quantity']:
                await interaction.response.send_message(
                    f"❌ Cannot give {give_quantity}. Only {self.selected_item['quantity']} available.",
                    ephemeral=True
                )
                return
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)
            return
        
        # Check container capacity
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.container_id)
        
        max_items = container.max_items
        if max_items > 0:
            current_unique_items = len(container.get_contained_items(self.guild_id))
            existing_quantity = container.get_item_quantity(self.guild_id, self.selected_item['name'])
            
            if existing_quantity == 0 and current_unique_items >= max_items:
                await interaction.response.send_message(
                    f"❌ Container is full (max {max_items} unique items).",
                    ephemeral=True
                )
                return
        
        # Perform the transfer
        character = self.selected_character['entity']
        item_entity = self.selected_item['entity']
        
        # Remove from character
        character.remove_item(self.guild_id, item_entity, give_quantity)
        
        # Add to container
        container.add_item(self.guild_id, item_entity, give_quantity)
        
        # Save both entities
        repositories.entity.upsert_entity(self.guild_id, character, system=character.system)
        repositories.entity.upsert_entity(self.guild_id, container, system=container.system)
        
        # Refresh parent view
        success_message = f"✅ **{character.name}** gave {give_quantity}x **{item_entity.name}** to **{container.name}**"
        
        if self.parent_view:
            await self.parent_view._refresh_container_view(interaction, success_message)
        else:
            await interaction.response.edit_message(content=success_message, view=None, embed=None)