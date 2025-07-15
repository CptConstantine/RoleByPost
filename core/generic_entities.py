from typing import Any, ClassVar, Dict, List
import discord
from discord import ui
from .base_models import AccessType, BaseCharacter, BaseEntity, EntityDefaults, EntityType, EntityLinkType, SystemType
from .inventory_views import EditInventoryView
from .shared_views import EditNameModal, EditNotesModal, FinalizeRollButton, RollFormulaView
from .roll_formula import RollFormula


class GenericEntity(BaseEntity):
    """Generic system entity - simple entity with basic properties"""
    SUPPORTED_ENTITY_TYPES: ClassVar[List[EntityType]] = [EntityType.GENERIC, EntityType.ITEM]
    
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.GENERIC: {
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
        view = GenericRollFormulaView(roll_formula_obj, difficulty)
        await interaction.response.send_message(
            content="Adjust your roll formula as needed, then finalize to roll.",
            view=view,
            ephemeral=True
        )

    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollFormula, difficulty: int = None):
        """
        Prints the roll result
        """
        from data.repositories.repository_factory import repositories
        base_roll = repositories.server.get_generic_base_roll(interaction.guild.id)
        result, total = roll_formula_obj.roll_formula(self, base_roll=(base_roll or "1d20"))

        difficulty_str = ""
        if difficulty:
            difficulty_str = f" (Needed {difficulty})"
            if total >= difficulty:
                result += f"\n✅ Success.{difficulty_str}"
            else:
                result += f"\n❌ Failure.{difficulty_str}"
        
        await interaction.response.send_message(result, ephemeral=False)

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
        from core.generic_entities import GenericRollFormula, GenericRollFormulaView
        
        roll_formula_obj = GenericRollFormula(roll_parameters)
        view = GenericRollFormulaView(roll_formula_obj, difficulty)
        
        await interaction.response.send_message(
            content=f"Rolling for {self.name}. Adjust as needed:",
            view=view,
            ephemeral=True
        )
    
    async def send_roll_message(self, interaction: discord.Interaction, roll_formula_obj: RollFormula, difficulty: int = None):
        """
        Prints the roll result
        """
        from data.repositories.repository_factory import repositories
        base_roll = repositories.server.get_generic_base_roll(interaction.guild.id)
        result, total = roll_formula_obj.roll_formula(self, base_roll=(base_roll or "1d20"))

        difficulty_str = ""
        if difficulty:
            difficulty_str = f" (Needed {difficulty})"
            if total >= difficulty:
                result += f"\n✅ Success.{difficulty_str}"
            else:
                result += f"\n❌ Failure.{difficulty_str}"
        
        await interaction.response.send_message(result, ephemeral=False)

class GenericRollFormula(RollFormula):
    """
    A roll formula specifically for the generic RPG system.
    It can handle any roll parameters as needed.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        super().__init__(roll_parameters_dict)

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

class GenericRollFormulaView(RollFormulaView):
    """
    Generic roll modifiers view with just the basic modifier functionality.
    """
    def __init__(self, roll_formula_obj: RollFormula, difficulty: int = None):
        super().__init__(roll_formula_obj, difficulty)
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))

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
        super().__init__(timeout=60*60*24) # 24 hours timeout
        self.editor_id = editor_id
        self.char_id = char_id
        self.system = system
        self.is_gm = is_gm
        
        # Build the view components based on current state
        self.build_view_components()

    def build_view_components(self):
        """Build view components based on GM status"""
        # Clear existing items
        self.clear_items()
        
        # Add basic buttons
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

        # Add item interaction buttons
        take_button = ui.Button(label="Take Items", style=discord.ButtonStyle.success, row=1)
        take_button.callback = self.take_items
        self.add_item(take_button)
        
        give_button = ui.Button(label="Give Items", style=discord.ButtonStyle.primary, row=1)
        give_button.callback = self.give_items
        self.add_item(give_button)
        
        # Add management buttons (GM/owner only)
        if self.is_gm:
            inventory_button = ui.Button(label="Manage Contents", style=discord.ButtonStyle.secondary, row=2)
            inventory_button.callback = self.manage_inventory
            self.add_item(inventory_button)
            
            access_button = ui.Button(label="Access Control", style=discord.ButtonStyle.secondary, row=2)
            access_button.callback = self.manage_access
            self.add_item(access_button)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Allow access if user can access the container or is GM
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Update the is_gm flag for proper display
        if self.is_gm != is_gm:
            self.is_gm = is_gm
            # Rebuild view if GM status changed
            self.build_view_components()
        
        if not container.can_be_accessed_by(str(interaction.user.id), is_gm):
            await interaction.response.send_message("❌ You don't have access to this container.", ephemeral=True)
            return False
        return True

    # Remove all @ui.button decorators and just define the methods
    async def edit_name(self, interaction: discord.Interaction):
        # Only owner or GM can edit name
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ Only the owner or GM can edit the container name.", ephemeral=True)
            return
            
        await interaction.response.send_modal(EditNameModal(self.char_id, self.system))

    async def edit_notes(self, interaction: discord.Interaction):
        # Only owner or GM can edit notes
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ Only the owner or GM can edit the container notes.", ephemeral=True)
            return
            
        await interaction.response.send_modal(EditNotesModal(self.char_id, self.system))

    async def refresh_view(self, interaction: discord.Interaction):
        """Refresh the container display with current data"""
        from data.repositories.repository_factory import repositories
        
        container = repositories.entity.get_by_id(self.char_id)
        if not container:
            await interaction.response.send_message("❌ Container not found.", ephemeral=True)
            return
        
        # Update GM status for proper display
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Get fresh container data and create new view
        embed = container.format_full_sheet(interaction.guild.id, is_gm=is_gm)
        new_view = GenericContainerEditView(self.editor_id, self.char_id, self.system, is_gm=is_gm)
        
        await interaction.response.edit_message(
            embed=embed, 
            view=new_view
        )

    async def reveal_to_players(self, interaction: discord.Interaction):
        """Reveal the container to all players by making it public"""
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        # Only owner or GM can reveal containers
        if not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ Only the owner or GM can reveal containers to players.", ephemeral=True)
            return
        
        # Make the container public
        container.reveal_to_players()
        repositories.entity.upsert_entity(str(interaction.guild.id), container, system=container.system)
        
        # Send a public message announcing the reveal
        embed = container.format_full_sheet(interaction.guild.id, is_gm=False)  # Player view
        public_view = GenericContainerEditView(interaction.user.id, self.char_id, self.system, is_gm=False)
        
        await interaction.response.send_message(
            content=f"📦 **{container.name}** has been revealed!",
            embed=embed,
            view=public_view,
            ephemeral=False  # Public message
        )

    async def take_items(self, interaction: discord.Interaction):
        await interaction.response.send_modal(TakeItemModal(self.char_id, str(interaction.user.id)))

    async def give_items(self, interaction: discord.Interaction):
        await interaction.response.send_modal(GiveItemModal(self.char_id, str(interaction.user.id)))

    async def manage_inventory(self, interaction: discord.Interaction):
        """Open the container's inventory for management using EditInventoryView"""
        # Only owner or GM can manage contents directly
        from data.repositories.repository_factory import repositories
        container = repositories.entity.get_by_id(self.char_id)
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        
        if not (container.is_owned_by(str(interaction.user.id)) or is_gm):
            await interaction.response.send_message("❌ Only the owner or GM can directly manage container contents.", ephemeral=True)
            return
        
        # Use EditInventoryView to manage the container's contents
        inventory_view = EditInventoryView(interaction.guild.id, interaction.user.id, self.char_id)
        
        await interaction.response.edit_message(
            content=f"Managing contents of **{container.name}**:",
            view=inventory_view
        )
    
    async def manage_access(self, interaction: discord.Interaction):
        # Only owner or GM can manage access
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
            await interaction.response.send_message(
                f"✅ Updated {container.name} access to '{access_type.value}'.",
                ephemeral=True
            )
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error updating access control: {str(e)}", ephemeral=True)

class TakeItemModal(ui.Modal, title="Take Items from Container"):
    def __init__(self, container_id: str, user_id: str):
        super().__init__()
        self.container_id = container_id
        self.user_id = user_id
        
    item_name = ui.TextInput(
        label="Item Name",
        placeholder="Enter the name of the item to take",
        required=True
    )
    
    quantity = ui.TextInput(
        label="Quantity",
        placeholder="How many to take? (default: 1)",
        required=False,
        default="1"
    )
    
    character_name = ui.TextInput(
        label="Character Name",
        placeholder="Which character should receive the items?",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        
        container = repositories.entity.get_by_id(self.container_id)
        if not container:
            await interaction.response.send_message("❌ Container not found.", ephemeral=True)
            return
        
        # Parse quantity
        try:
            quantity = int(self.quantity.value or "1")
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError:
            await interaction.response.send_message("❌ Invalid quantity. Please enter a positive number.", ephemeral=True)
            return
        
        # Find the character
        character_name = self.character_name.value.strip()
        character = repositories.entity.get_by_name(str(interaction.guild.id), character_name)
        if not character:
            await interaction.response.send_message(f"❌ Character '{character_name}' not found.", ephemeral=True)
            return
        
        # Check if user can control this character
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not character.can_be_accessed_by(self.user_id, is_gm):
            await interaction.response.send_message(f"❌ You don't have access to {character_name}.", ephemeral=True)
            return
        
        # Check if container is locked
        if container.is_locked and not (container.is_owned_by(self.user_id) or is_gm):
            await interaction.response.send_message("❌ This container is locked.", ephemeral=True)
            return
        
        item_name = self.item_name.value.strip()
        guild_id = str(interaction.guild.id)
        
        # Check if item exists in container with sufficient quantity
        if not container.can_take_item(guild_id, item_name, quantity):
            available = container.get_item_quantity(guild_id, item_name)
            await interaction.response.send_message(
                f"❌ Not enough {item_name} in container. Available: {available}, Requested: {quantity}",
                ephemeral=True
            )
            return
        
        # Take the item
        item = container.take_item(guild_id, item_name, quantity)
        if not item:
            await interaction.response.send_message(f"❌ Could not take {item_name} from container.", ephemeral=True)
            return
        
        # Add to character's inventory
        character.add_item(guild_id, item, quantity)
        
        # Save both entities
        repositories.entity.upsert_entity(guild_id, container, system=container.system)
        repositories.entity.upsert_entity(guild_id, character, system=character.system)
        
        await interaction.response.send_message(
            f"✅ {character_name} took {quantity}x {item_name} from {container.name}.\n"
            f"💡 Click 🔄 Refresh to see updated container contents.",
            ephemeral=True
        )

class GiveItemModal(ui.Modal, title="Give Items to Container"):
    def __init__(self, container_id: str, user_id: str):
        super().__init__()
        from data.repositories.repository_factory import repositories
        self.user_id = user_id
        self.container = repositories.entity.get_by_id(container_id)
        
    item_name = ui.TextInput(
        label="Item Name",
        placeholder="Enter the name of the item to give",
        required=True
    )
    
    quantity = ui.TextInput(
        label="Quantity",
        placeholder="How many to give? (default: 1)",
        required=False,
        default="1"
    )
    
    character_name = ui.TextInput(
        label="Character Name",
        placeholder="Which character is giving the items?",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        if not self.container:
            await interaction.response.send_message("❌ Container not found.", ephemeral=True)
            return
        
        # Parse quantity
        try:
            quantity = int(self.quantity.value or "1")
            if quantity <= 0:
                raise ValueError("Quantity must be positive")
        except ValueError:
            await interaction.response.send_message("❌ Invalid quantity. Please enter a positive number.", ephemeral=True)
            return
        
        # Find the character
        character_name = self.character_name.value.strip()
        character = repositories.entity.get_by_name(str(interaction.guild.id), character_name)
        if not character:
            await interaction.response.send_message(f"❌ Character '{character_name}' not found.", ephemeral=True)
            return
        
        # Check if user can control this character
        is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
        if not character.can_be_accessed_by(self.user_id, is_gm):
            await interaction.response.send_message(f"❌ You don't have access to {character_name}.", ephemeral=True)
            return
        
        item_name = self.item_name.value.strip()
        guild_id = str(interaction.guild.id)
        
        # Find the item in character's inventory
        inventory_items = character.get_inventory(guild_id)
        target_item = None
        available_quantity = 0
        
        for inv_item in inventory_items:
            if inv_item.name == item_name:
                target_item = inv_item
                # Get quantity from character's inventory
                links = character.get_links_to_entity(guild_id, inv_item.id, EntityLinkType.POSSESSES)
                if links:
                    available_quantity += links[0].metadata.get("quantity", 1)
        
        if not target_item:
            await interaction.response.send_message(f"❌ {character_name} doesn't have {item_name} in their inventory.", ephemeral=True)
            return
        
        if available_quantity < quantity:
            await interaction.response.send_message(
                f"❌ {character_name} only has {available_quantity}x {item_name}. Cannot give {quantity}.",
                ephemeral=True
            )
            return
        
        # Check if container has space (if limited)
        max_items = self.container.max_items
        if max_items > 0:
            current_unique_items = len(self.container.get_contained_items(guild_id))
            existing_quantity = self.container.get_item_quantity(guild_id, item_name)
            
            # If item doesn't exist in container and we're at max capacity
            if existing_quantity == 0 and current_unique_items >= max_items:
                await interaction.response.send_message(
                    f"❌ Container is full (max {max_items} unique items).",
                    ephemeral=True
                )
                return
        
        # Remove from character's inventory
        character.remove_item(guild_id, target_item, quantity)
        
        # Add to container
        self.container.add_item(guild_id, target_item, quantity)
        
        # Save both entities
        repositories.entity.upsert_entity(guild_id, character, system=character.system)
        repositories.entity.upsert_entity(guild_id, self.container, system=self.container.system)
        
        await interaction.response.send_message(
            f"✅ {character_name} gave {quantity}x {item_name} to {self.container.name}.\n"
            f"💡 Click 🔄 Refresh to see updated container contents.",
            ephemeral=True
        )

class ContainerManageModal(ui.Modal, title="Manage Container Contents"):
    def __init__(self, container_id: str):
        super().__init__()
        self.container_id = container_id
        
    item_name = ui.TextInput(
        label="Item Name",
        placeholder="Enter item name to add/remove",
        required=True
    )
    
    quantity = ui.TextInput(
        label="Quantity",
        placeholder="Enter quantity (positive to add, negative to remove)",
        required=True,
        default="1"
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        
        container = repositories.entity.get_by_id(self.container_id)
        if not container:
            await interaction.response.send_message("❌ Container not found.", ephemeral=True)
            return
        
        item_name = self.item_name.value.strip()
        try:
            quantity = int(self.quantity.value)
        except ValueError:
            await interaction.response.send_message("❌ Invalid quantity. Please enter a number.", ephemeral=True)
            return
        
        # Find the item
        item = repositories.entity.get_by_name(str(interaction.guild.id), item_name)
        if not item:
            await interaction.response.send_message(f"❌ Item '{item_name}' not found.", ephemeral=True)
            return
        
        if item.entity_type != EntityType.ITEM:
            await interaction.response.send_message(f"❌ '{item_name}' is not an item.", ephemeral=True)
            return
        
        guild_id = str(interaction.guild.id)
        
        if quantity > 0:
            # Add items
            if container.add_item(guild_id, item, quantity):
                repositories.entity.upsert_entity(guild_id, container, system=container.system)
                await interaction.response.send_message(
                    f"✅ Added {quantity}x {item_name} to {container.name}.\n"
                    f"💡 Click 🔄 Refresh to see updated container contents.", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(f"❌ Could not add {item_name} to {container.name}. Container may be full.", ephemeral=True)
        else:
            # Remove items
            if container.remove_item(guild_id, item, abs(quantity)):
                repositories.entity.upsert_entity(guild_id, container, system=container.system)
                await interaction.response.send_message(
                    f"✅ Removed {abs(quantity)}x {item_name} from {container.name}.\n"
                    f"💡 Click 🔄 Refresh to see updated container contents.", 
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(f"❌ Could not remove {item_name} from {container.name}.", ephemeral=True)