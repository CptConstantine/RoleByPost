from dataclasses import dataclass
from enum import Enum
from typing import Optional, Dict, Any, List, Tuple
import discord
from discord import ui
import re
import random

class CoreRollMechanic(Enum):
    D20_SYSTEM = "d20"
    ROLL_UNDER = "roll_under"
    DICE_POOL = "dice_pool"
    TWO_D6 = "2d6"
    DUALITY = "duality"
    EXPLODING = "exploding"
    GENERIC = "generic"

@dataclass
class RollMechanicConfig:
    """Configuration for a server's core roll mechanic"""
    mechanic_type: CoreRollMechanic
    dice_formula: str  # e.g., "1d20", "2d6", "1d100", "5d6"
    success_criteria: Optional[str] = None  # e.g., ">=", "<=", "6+", "8+"
    target_number: Optional[int] = None  # For roll-under or fixed DC systems
    explode_on: Optional[int] = None  # For exploding dice (e.g., 6, 10, 20)
    hope_fear_enabled: bool = False  # For duality systems
    custom_formula: Optional[str] = None  # For generic systems
    description: str = ""  # User-friendly description

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "mechanic_type": self.mechanic_type.value,
            "dice_formula": self.dice_formula,
            "success_criteria": self.success_criteria,
            "target_number": self.target_number,
            "explode_on": self.explode_on,
            "hope_fear_enabled": self.hope_fear_enabled,
            "custom_formula": self.custom_formula,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RollMechanicConfig':
        """Create from dictionary from database"""
        return cls(
            mechanic_type=CoreRollMechanic(data["mechanic_type"]),
            dice_formula=data["dice_formula"],
            success_criteria=data.get("success_criteria"),
            target_number=data.get("target_number"),
            explode_on=data.get("explode_on"),
            hope_fear_enabled=data.get("hope_fear_enabled", False),
            custom_formula=data.get("custom_formula"),
            description=data.get("description", "")
        )

class CoreRollMechanicSelectView(ui.View):
    """Main view for selecting core roll mechanic type"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_config: Optional[RollMechanicConfig] = None
        
    @ui.select(
        placeholder="Choose your game's core roll mechanic...",
        options=[
            discord.SelectOption(
                label="d20 System (D&D, Pathfinder)",
                value="d20",
                description="Roll 1d20 + modifiers vs difficulty"
            ),
            discord.SelectOption(
                label="2d6 System (Traveller, Apocalypse World)",
                value="2d6",
                description="Roll 2d6 + modifiers vs difficulty"
            ),
            discord.SelectOption(
                label="Roll Under (Call of Cthulhu, d100 games)",
                value="roll_under",
                description="Roll dice, succeed if result ≤ target"
            ),
            discord.SelectOption(
                label="Dice Pool (World of Darkness, Shadowrun)",
                value="dice_pool",
                description="Roll multiple dice, count successes"
            ),
            discord.SelectOption(
                label="Exploding Dice (Savage Worlds)",
                value="exploding",
                description="Dice explode on maximum values"
            ),
            discord.SelectOption(
                label="Duality Dice (Daggerheart)",
                value="duality",
                description="Hope/Fear duality mechanics"
            ),
            discord.SelectOption(
                label="Generic/Custom Formula",
                value="generic",
                description="Define your own custom roll formula"
            )
        ]
    )
    async def select_mechanic(self, interaction: discord.Interaction, select: ui.Select):
        mechanic_type = CoreRollMechanic(select.values[0])
        
        # Create configuration view based on selection
        config_view = self._get_config_view(mechanic_type)
        
        embed = discord.Embed(
            title=f"Configure {select.options[0].label}",
            description="Set up the specific parameters for your roll mechanic.",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=config_view)
    
    def _get_config_view(self, mechanic_type: CoreRollMechanic) -> ui.View:
        """Get the appropriate configuration view for the mechanic type"""
        if mechanic_type == CoreRollMechanic.D20_SYSTEM:
            return D20ConfigView()
        elif mechanic_type == CoreRollMechanic.TWO_D6:
            return TwoD6ConfigView()
        elif mechanic_type == CoreRollMechanic.ROLL_UNDER:
            return RollUnderConfigView()
        elif mechanic_type == CoreRollMechanic.DICE_POOL:
            return DicePoolConfigView()
        elif mechanic_type == CoreRollMechanic.EXPLODING:
            return ExplodingDiceConfigView()
        elif mechanic_type == CoreRollMechanic.DUALITY:
            return DualityConfigView()
        elif mechanic_type == CoreRollMechanic.GENERIC:
            return GenericConfigView()
        else:
            return BasicConfigView(mechanic_type)

class D20ConfigView(ui.View):
    """Configuration view for d20 systems"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanic.D20_SYSTEM,
            dice_formula="1d20",
            success_criteria=">=",
            description="d20 + modifiers vs DC"
        )
    
    @ui.button(label="Confirm d20 Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**d20 System** is now active for this server.\n\n"
                       f"Players will roll: `1d20 + modifiers` vs difficulty",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class TwoD6ConfigView(ui.View):
    """Configuration view for 2d6 systems"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanic.TWO_D6,
            dice_formula="2d6",
            success_criteria=">=",
            description="2d6 + modifiers vs target"
        )
    
    @ui.button(label="Confirm 2d6 Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**2d6 System** is now active for this server.\n\n"
                       f"Players will roll: `2d6 + modifiers` vs difficulty",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class RollUnderConfigView(ui.View):
    """Configuration view for roll-under systems"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanic.ROLL_UNDER,
            dice_formula="1d100",
            success_criteria="<=",
            description="Roll under target number"
        )
    
    dice_options = [
        ("1d100", "d100 (Call of Cthulhu, WFRP)"),
        ("1d20", "d20 (some OSR games)"),
        ("3d6", "3d6 (GURPS)")
    ]
    
    @ui.select(
        placeholder="Choose dice for roll-under system...",
        options=[
            discord.SelectOption(label=desc, value=value, description=desc)
            for value, desc in dice_options
        ]
    )
    async def select_dice(self, interaction: discord.Interaction, select: ui.Select):
        self.config.dice_formula = select.values[0]
        selected_option = next(opt for opt in select.options if opt.value == select.values[0])
        
        embed = discord.Embed(
            title="Roll-Under System Configuration",
            description=f"**Selected:** {selected_option.label}\n"
                       f"Players will roll `{self.config.dice_formula}` and succeed if ≤ target number",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="Confirm Roll-Under Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**Roll-Under System** is now active for this server.\n\n"
                       f"Players will roll: `{self.config.dice_formula}` ≤ target number",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class DicePoolConfigView(ui.View):
    """Configuration view for dice pool systems"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanic.DICE_POOL,
            dice_formula="1d10",  # Base die type
            success_criteria="8+",
            description="Count successes in dice pool"
        )
    
    @ui.select(
        placeholder="Choose die type for pool...",
        options=[
            discord.SelectOption(label="d10 (World of Darkness)", value="1d10", description="Success on 8+"),
            discord.SelectOption(label="d6 (Shadowrun)", value="1d6", description="Success on 5+"),
            discord.SelectOption(label="d8 (Custom)", value="1d8", description="Configure success threshold"),
            discord.SelectOption(label="d12 (Custom)", value="1d12", description="Configure success threshold")
        ]
    )
    async def select_die_type(self, interaction: discord.Interaction, select: ui.Select):
        self.config.dice_formula = select.values[0]
        
        # Set default success criteria based on die type
        if "d10" in select.values[0]:
            self.config.success_criteria = "8+"
        elif "d6" in select.values[0]:
            self.config.success_criteria = "5+"
        else:
            self.config.success_criteria = "6+"
        
        embed = discord.Embed(
            title="Dice Pool Configuration",
            description=f"**Die Type:** {select.values[0]}\n"
                       f"**Success Threshold:** {self.config.success_criteria}\n\n"
                       f"Players will roll multiple {select.values[0]} and count successes.",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="Confirm Dice Pool Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**Dice Pool System** is now active for this server.\n\n"
                       f"Players will roll multiple {self.config.dice_formula} dice and count successes ({self.config.success_criteria})",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class ExplodingDiceConfigView(ui.View):
    """Configuration view for exploding dice systems"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanic.EXPLODING,
            dice_formula="1d6",
            explode_on=6,
            success_criteria=">=",
            description="Dice explode on maximum value"
        )
    
    @ui.select(
        placeholder="Choose base die and explosion threshold...",
        options=[
            discord.SelectOption(label="d6 explodes on 6", value="1d6:6", description="Savage Worlds style"),
            discord.SelectOption(label="d8 explodes on 8", value="1d8:8", description="Custom system"),
            discord.SelectOption(label="d10 explodes on 10", value="1d10:10", description="Custom system"),
            discord.SelectOption(label="d20 explodes on 20", value="1d20:20", description="Custom system")
        ]
    )
    async def select_exploding_config(self, interaction: discord.Interaction, select: ui.Select):
        value_parts = select.values[0].split(":")
        self.config.dice_formula = value_parts[0]
        self.config.explode_on = int(value_parts[1])
        
        embed = discord.Embed(
            title="Exploding Dice Configuration",
            description=f"**Die Type:** {self.config.dice_formula}\n"
                       f"**Explodes On:** {self.config.explode_on}\n\n"
                       f"When rolling {self.config.explode_on}, roll again and add to total!",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    @ui.button(label="Confirm Exploding Dice Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**Exploding Dice System** is now active for this server.\n\n"
                       f"Players will roll {self.config.dice_formula}, exploding on {self.config.explode_on}",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class DualityConfigView(ui.View):
    """Configuration view for duality dice systems"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanic.DUALITY,
            dice_formula="1d12",
            hope_fear_enabled=True,
            description="Duality dice with Hope/Fear"
        )
    
    @ui.button(label="Confirm Duality Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**Duality Dice System** is now active for this server.\n\n"
                       f"Players will roll with Hope/Fear mechanics (Daggerheart style)",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class GenericConfigView(ui.View):
    """Configuration view for generic/custom systems"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanic.GENERIC,
            dice_formula="1d20",  # Default
            custom_formula="",
            description="Custom roll formula"
        )
    
    @ui.button(label="Set Custom Formula", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def set_formula(self, interaction: discord.Interaction, button: ui.Button):
        modal = CustomFormulaModal(self.config)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Confirm Generic Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        if not self.config.custom_formula:
            await interaction.response.send_message("❌ Please set a custom formula first.", ephemeral=True)
            return
        await self._save_config(interaction)
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**Generic/Custom System** is now active for this server.\n\n"
                       f"Formula: `{self.config.custom_formula}`",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class CustomFormulaModal(ui.Modal, title="Custom Roll Formula"):
    """Modal for entering custom roll formulas"""
    
    formula = ui.TextInput(
        label="Roll Formula",
        placeholder="e.g., 3d6, 1d20+5, 2d10+1d6",
        required=True,
        max_length=100
    )
    
    def __init__(self, config: RollMechanicConfig):
        super().__init__()
        self.config = config
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate the formula
        if not self._validate_formula(self.formula.value):
            await interaction.response.send_message(
                "❌ Invalid formula format. Use formats like: 1d20, 2d6+1, 3d8-2", 
                ephemeral=True
            )
            return
        
        self.config.custom_formula = self.formula.value
        self.config.dice_formula = self.formula.value
        self.config.description = f"Custom: {self.formula.value}"
        
        embed = discord.Embed(
            title="Custom Formula Set",
            description=f"**Formula:** `{self.formula.value}`\n\n"
                       f"Players will use this formula for rolls.",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    def _validate_formula(self, formula: str) -> bool:
        """Validate dice formula format"""
        import re
        # Accept formats like: 1d20, 2d6+3, 3d8-2, 1d100, etc.
        pattern = r'^\d*d\d+([+-]\d+)?$'
        return bool(re.match(pattern, formula.replace(' ', '').lower()))

class BasicConfigView(ui.View):
    """Fallback configuration view for simple mechanics"""
    
    def __init__(self, mechanic_type: CoreRollMechanic):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=mechanic_type,
            dice_formula="1d20",
            description=f"{mechanic_type.value} system"
        )
    
    @ui.button(label="Confirm Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**{self.config.mechanic_type.value}** is now active for this server.",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
