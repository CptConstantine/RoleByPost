from typing import Any, ClassVar, Dict, List
import discord
from discord import ui
from core.base_models import BaseCharacter, BaseEntity, EntityDefaults, EntityType, RelationshipType, AccessLevel
from core.shared_views import EditNameModal, EditNotesModal, FinalizeRollButton, RollFormulaView
from core.roll_formula import RollFormula

class GenericEntity(BaseEntity):
    """Generic system entity - simple entity with basic properties"""
    
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.GENERIC: {
        }
    })
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self.entity_type = EntityType.GENERIC
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericEntity":
        return cls(data)
    
    def get_sheet_edit_view(self, editor_id: int) -> ui.View:
        from core.generic_entities import GenericSheetEditView
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
    
    def get_sheet_edit_view(self, editor_id: int) -> ui.View:
        from core.generic_entities import GenericSheetEditView
        return GenericSheetEditView(editor_id=editor_id, char_id=self.id, system=self.system)

    def format_full_sheet(self, guild_id: int) -> discord.Embed:
        """Format the character sheet for generic system"""
        embed = discord.Embed(
            title=f"{self.name or 'Character'}",
            color=discord.Color.greyple()
        )
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
    
    def get_sheet_edit_view(self, editor_id: int) -> ui.View:
        return GenericSheetEditView(editor_id=editor_id, char_id=self.id, system=self.system)

    def format_full_sheet(self) -> discord.Embed:
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
    def __init__(self, editor_id: int, char_id: str, system: str):
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
    
    def get_sheet_edit_view(self, editor_id: int) -> ui.View:
        return GenericContainerEditView(editor_id=editor_id, char_id=self.id, system=self.system)

    def format_full_sheet(self, guild_id: int) -> discord.Embed:
        """Format the container sheet"""
        embed = discord.Embed(
            title=f"{self.name or 'Container'} (Container)",
            color=discord.Color.gold()
        )
        
        # Container properties
        max_items = self.data.get("max_items", 0)
        is_locked = self.data.get("is_locked", False)
        access_control = self.access_control
        
        # Format access control display
        access_display = access_control.access_type.replace("_", " ").title()
        if access_control.access_type == "specific_users":
            total_users = len(self.get_all_allowed_users())
            if total_users > 0:
                access_display += f" ({total_users} users)"
        
        embed.add_field(
            name="Properties",
            value=f"**Max Items:** {'Unlimited' if max_items == 0 else max_items}\n"
                  f"**Locked:** {'Yes' if is_locked else 'No'}\n"
                  f"**Access:** {access_display}",
            inline=False
        )
        
        # Show owner and additional allowed users
        access_info = []
        if self.owner_id:
            access_info.append(f"**Owner:** <@{self.owner_id}>")
        
        if access_control.access_type == "specific_users" and access_control.allowed_user_ids:
            try:
                # Show up to 5 additional users
                additional_users = [uid for uid in access_control.allowed_user_ids if uid != self.owner_id][:5]
                if additional_users:
                    user_mentions = [f"<@{user_id}>" for user_id in additional_users]
                    additional_text = ", ".join(user_mentions)
                    if len(access_control.allowed_user_ids) > 5:
                        additional_text += f" ... and {len(access_control.allowed_user_ids) - 5} more"
                    access_info.append(f"**Additional Access:** {additional_text}")
            except:
                # Fallback
                additional_count = len([uid for uid in access_control.allowed_user_ids if uid != self.owner_id])
                if additional_count > 0:
                    access_info.append(f"**Additional Access:** {additional_count} users")
        
        if access_info:
            embed.add_field(
                name="Access Control",
                value="\n".join(access_info),
                inline=False
            )
        
        # Show contained items
        contained_items = self.get_contained_items(guild_id)
        if contained_items:
            items_display = []
            for item in contained_items:
                # Get quantity from relationship metadata if available
                relationships = self.get_relationships_to_entity(guild_id, item.id, RelationshipType.POSSESSES)
                quantity = 1
                if relationships:
                    quantity = relationships[0].metadata.get("quantity", 1)
                
                quantity_str = f" x{quantity}" if quantity > 1 else ""
                items_display.append(f"• {item.name}{quantity_str}")
            
            embed.add_field(
                name=f"Contents ({len(contained_items)})",
                value="\n".join(items_display)[:1024],
                inline=False
            )
        else:
            embed.add_field(name="Contents", value="*Empty*", inline=False)
        
        # Add notes
        notes = self.notes
        if notes:
            notes_display = "\n".join(notes)
            embed.add_field(name="Notes", value=notes_display, inline=False)
        
        return embed
    
    def apply_defaults(self, entity_type: EntityType = None, guild_id: str = None):
        """Apply defaults for containers"""
        super().apply_defaults(entity_type=entity_type, guild_id=guild_id)
        
        if self.ENTITY_DEFAULTS:
            defaults = self.ENTITY_DEFAULTS.get_defaults(EntityType.CONTAINER)
            for key, value in defaults.items():
                self._apply_default_field(key, value, guild_id)
    
    def get_contained_items(self, guild_id: str) -> List[BaseEntity]:
        """Get all items contained in this container"""
        return [item for item in self.get_children(guild_id, RelationshipType.POSSESSES) if item.entity_type == EntityType.ITEM]
    
    def add_item(self, guild_id: str, item: BaseEntity, quantity: int = 1) -> bool:
        """Add an item to the container with specified quantity"""
        if item.entity_type != EntityType.ITEM:
            return False
        
        # Check if container has space
        max_items = self.data.get("max_items", 0)
        if max_items > 0:
            current_items = len(self.get_contained_items(guild_id))
            if current_items >= max_items:
                return False
        
        # Create relationship with quantity metadata
        metadata = {"quantity": quantity}
        self.add_relationship(guild_id, item, RelationshipType.POSSESSES, metadata)
        return True
    
    def remove_item(self, guild_id: str, item: BaseEntity, quantity: int = None) -> bool:
        """Remove an item from the container"""
        if item.entity_type != EntityType.ITEM:
            return False
        
        # If no quantity specified, remove all
        if quantity is None:
            return self.remove_relationship(guild_id, item, RelationshipType.POSSESSES)
        
        # Get current relationship to check quantity
        relationships = self.get_relationships_to_entity(guild_id, item.id, RelationshipType.POSSESSES)
        if not relationships:
            return False
        
        relationship = relationships[0]
        current_quantity = relationship.metadata.get("quantity", 1)
        
        if quantity >= current_quantity:
            # Remove completely
            return self.remove_relationship(guild_id, item, RelationshipType.POSSESSES)
        else:
            # Update quantity
            from data.repositories.repository_factory import repositories
            relationship.metadata["quantity"] = current_quantity - quantity
            repositories.relationship.save(relationship)
            return True
    
    def get_relationships_to_entity(self, guild_id: str, entity_id: str, relationship_type: RelationshipType) -> List:
        """Helper method to get relationships to a specific entity"""
        from data.repositories.repository_factory import repositories
        all_relationships = repositories.relationship.get_relationships_for_entity(guild_id, self.id)
        return [rel for rel in all_relationships 
                if rel.from_entity_id == self.id and rel.to_entity_id == entity_id 
                and rel.relationship_type == relationship_type.value]

class GenericContainerEditView(ui.View):
    def __init__(self, editor_id: int, char_id: str, system: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id
        self.system = system

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this container.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=0)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNameModal(self.char_id, self.system))

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=0)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNotesModal(self.char_id, self.system))

    @ui.button(label="Manage Contents", style=discord.ButtonStyle.primary, row=1)
    async def manage_contents(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ContainerManageModal(self.char_id))
    
    @ui.button(label="Access Control", style=discord.ButtonStyle.secondary, row=1)
    async def manage_access(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(ContainerAccessModal(self.char_id))

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
            if container.add_to_inventory(guild_id, item):
                await interaction.response.send_message(f"✅ Added {quantity}x {item_name} to {container.name}.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Could not add {item_name} to {container.name}. Container may be full.", ephemeral=True)
        else:
            # Remove items
            if container.remove_from_inventory(guild_id, item):
                await interaction.response.send_message(f"✅ Removed {abs(quantity)}x {item_name} from {container.name}.", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ Could not remove {item_name} from {container.name}.", ephemeral=True)

class ContainerAccessModal(ui.Modal, title="Manage Container Access"):
    def __init__(self, container_id: str):
        super().__init__()
        self.container_id = container_id
        
    access_type = ui.TextInput(
        label="Access Type",
        placeholder="Enter: public, gm_only, or specific_users",
        required=True
    )
    
    user_mentions = ui.TextInput(
        label="Additional Users (for specific_users only)",
        placeholder="@user1 @user2 or user IDs separated by spaces",
        required=False,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        
        container = repositories.entity.get_by_id(self.container_id)
        if not container:
            await interaction.response.send_message("❌ Container not found.", ephemeral=True)
            return
        
        access_type = self.access_type.value.strip().lower()
        valid_types = ["public", "gm_only", "specific_users"]
        
        if access_type not in valid_types:
            await interaction.response.send_message(
                f"❌ Invalid access type. Must be one of: {', '.join(valid_types)}", 
                ephemeral=True
            )
            return
        
        try:
            container.set_access_type(access_type)
            
            # Handle additional user list for specific_users access type
            if access_type == "specific_users" and self.user_mentions.value.strip():
                user_input = self.user_mentions.value.strip()
                user_ids = []
                
                # Parse user mentions and IDs
                import re
                # Extract user IDs from mentions (<@!123456> or <@123456>)
                mention_pattern = r'<@!?(\d+)>'
                mentioned_ids = re.findall(mention_pattern, user_input)
                user_ids.extend(mentioned_ids)
                
                # Extract raw user IDs (just numbers)
                words = user_input.split()
                for word in words:
                    # Remove mention formatting and check if it's a valid user ID
                    clean_word = re.sub(r'[<@!>]', '', word)
                    if clean_word.isdigit() and len(clean_word) >= 17:  # Discord user IDs are typically 17-19 digits
                        user_ids.append(clean_word)
                
                # Clear existing additional users (but keep owner_id separate)
                access_control = container.access_control
                access_control.allowed_user_ids = []
                for user_id in set(user_ids):  # Remove duplicates
                    # Don't add the owner to the additional access list
                    if user_id != container.owner_id:
                        access_control.add_user(user_id)
                container.access_control = access_control
                
                repositories.entity.upsert_entity(str(interaction.guild.id), container, system=container.system)
                
                total_users = len(container.get_all_allowed_users())
                await interaction.response.send_message(
                    f"✅ Updated {container.name} access to '{access_type}' with {total_users} total users (owner + {len(user_ids)} additional).",
                    ephemeral=True
                )
            else:
                repositories.entity.upsert_entity(str(interaction.guild.id), container, system=container.system)
                await interaction.response.send_message(
                    f"✅ Updated {container.name} access to '{access_type}'.",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.response.send_message(f"❌ Error updating access control: {str(e)}", ephemeral=True)