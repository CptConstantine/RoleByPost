from typing import Any, ClassVar, Dict, List
import discord
from discord import ui
from core.base_models import BaseCharacter, BaseEntity, EntityDefaults, EntityType
from core.shared_views import EditNameModal, EditNotesModal, FinalizeRollButton, RollFormulaView
from core.roll_formula import RollFormula

SYSTEM = "generic"
    
class GenericEntity(BaseEntity):
    """Generic system entity - simple entity with basic properties"""
    
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.GENERIC: { }
    })
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        self.entity_type = EntityType.GENERIC
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericEntity":
        return cls(data)
    
    def get_sheet_edit_view(self, editor_id: int) -> ui.View:
        from core.generic_entities import GenericSheetEditView
        return GenericSheetEditView(editor_id=editor_id, char_id=self.id)
    
    def apply_defaults(self, entity_type: EntityType = None, guild_id: str = None):
        """Apply defaults for generic entities"""
        super().apply_defaults(entity_type=entity_type, guild_id=guild_id)

class GenericCharacter(BaseCharacter):
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.PC: { },
        EntityType.NPC: { }
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
        return GenericSheetEditView(editor_id=editor_id, char_id=self.id)

    def format_full_sheet(self) -> discord.Embed:
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
    ENTITY_DEFAULTS = EntityDefaults({
        EntityType.COMPANION: { }
    })
    
    SUPPORTED_ENTITY_TYPES: ClassVar[List[EntityType]] = [EntityType.COMPANION]
    
    def __init__(self, data: Dict[str, Any]):
        super().__init__(data)
        if self.entity_type != EntityType.COMPANION:
            self.entity_type = EntityType.COMPANION
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GenericCompanion":
        return cls(data)
    
    def get_sheet_edit_view(self, editor_id: int) -> ui.View:
        return GenericSheetEditView(editor_id=editor_id, char_id=self.id)
    
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
    def __init__(self, editor_id: int, char_id: str):
        super().__init__(timeout=120)
        self.editor_id = editor_id
        self.char_id = char_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.editor_id:
            await interaction.response.send_message("You can't edit this character.", ephemeral=True)
            return False
        return True

    @ui.button(label="Edit Name", style=discord.ButtonStyle.secondary, row=0)
    async def edit_name(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNameModal(self.char_id, SYSTEM))

    @ui.button(label="Edit Notes", style=discord.ButtonStyle.secondary, row=0)
    async def edit_notes(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditNotesModal(self.char_id, SYSTEM))

class GenericRollFormulaView(RollFormulaView):
    """
    Generic roll modifiers view with just the basic modifier functionality.
    """
    def __init__(self, roll_formula_obj: RollFormula, difficulty: int = None):
        super().__init__(roll_formula_obj, difficulty)
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))