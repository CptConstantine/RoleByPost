from hmac import new
import discord
from discord import ui
import re
from core.base_models import BaseCharacter
from core.generic_roll_mechanics import RollMechanicConfig
from core.shared_views import FinalizeRollButton, RollFormulaView
from core.generic_roll_formulas import CustomRollFormula, DicePoolRollFormula, RollFormula
from data.repositories.repository_factory import repositories

class RollAndSumFormulaView(RollFormulaView):
    """
    Roll formula view for Roll-and-Sum mechanics.
    Simple view with just modifiers and finalize button.
    """
    def __init__(self, character: BaseCharacter, roll_formula_obj: RollFormula, difficulty: int = None):
        super().__init__(roll_formula_obj, character, difficulty)
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))

    # Override to ensure we get the character before building the view
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not self.character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return False
        return True

class DicePoolFormulaView(RollFormulaView):
    """
    Roll formula view for Dice Pool mechanics.
    Includes buttons for adding dice and setting target number.
    """
    def __init__(self, character: BaseCharacter, roll_formula_obj: DicePoolRollFormula, difficulty: int = None):
        super().__init__(roll_formula_obj, character, difficulty)

        self.roll_formula_obj = roll_formula_obj

        self.add_item(AddDiceButton(self))
        self.add_item(ClearDicePoolButton(self))
        targetLabel = f"Set Target Number" if roll_formula_obj.roll_config.target_number is None else f"Target Number: {roll_formula_obj.roll_config.target_number}"
        self.add_item(SetTargetNumberButton(self, targetLabel))
        self.add_item(FinalizeRollButton(roll_formula_obj))

    # Override to ensure we get the character before building the view
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not self.character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return False
        return True

class CustomFormulaView(RollFormulaView):
    """
    Roll formula view for Custom mechanics.
    Allows complex custom formulas with modifiers.
    """
    def __init__(self, character: BaseCharacter, roll_formula_obj: CustomRollFormula, difficulty: int = None):
        super().__init__(roll_formula_obj, character, difficulty)

        self.roll_formula_obj = roll_formula_obj

        self.add_item(SetCustomFormulaButton(self))
        self.add_item(FinalizeRollButton(roll_formula_obj, difficulty))

    # Override to ensure we get the character before building the view
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        self.character = repositories.active_character.get_active_character(interaction.guild.id, interaction.user.id)
        if not self.character:
            await interaction.response.send_message("❌ No active character found.", ephemeral=True)
            return False
        return True

class AddDiceButton(ui.Button):
    """Button to add dice to a dice pool"""
    
    def __init__(self, parent_view: DicePoolFormulaView):
        super().__init__(
            label="Add Dice",
            style=discord.ButtonStyle.primary,
            emoji="🎲",
            row=2
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        modal = AddDiceModal(self.parent_view)
        await interaction.response.send_modal(modal)

class ClearDicePoolButton(ui.Button):
    """Button to clear additional dice from the pool"""
    
    def __init__(self, parent_view: DicePoolFormulaView):
        super().__init__(
            label="Clear Added",
            style=discord.ButtonStyle.danger,
            emoji="🗑️",
            row=2
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        # Clear the additional dice
        if hasattr(self.parent_view.roll_formula_obj, 'additional_dice'):
            old_count = len(self.parent_view.roll_formula_obj.additional_dice)
            self.parent_view.roll_formula_obj.additional_dice.clear()
            
            # Show the updated formula
            current_formula = self.parent_view.roll_formula_obj.get_total_dice_formula()
            
            if old_count > 0:
                content = f"✅ Cleared {old_count} additional dice from pool.\n**Current pool:** {current_formula}"
            else:
                content = f"ℹ️ No additional dice to clear.\n**Current pool:** {current_formula}"
        else:
            current_formula = self.parent_view.roll_formula_obj.get_total_dice_formula()
            content = f"ℹ️ No additional dice to clear.\n**Current pool:** {current_formula}"
        
        await interaction.response.edit_message(
            content=content,
            view=self.parent_view
        )

class SetTargetNumberButton(ui.Button):
    """Button to set the difficulty (number of successes needed) for dice pools"""
    
    def __init__(self, parent_view: DicePoolFormulaView, label: str):
        super().__init__(
            label=label or "Set Difficulty",
            style=discord.ButtonStyle.secondary,
            emoji="🎯",
            row=2
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        modal = SetTargetNumberModal(self.parent_view)
        await interaction.response.send_modal(modal)

class SetCustomFormulaButton(ui.Button):
    """Button to set a custom dice formula"""
    
    def __init__(self, parent_view: CustomFormulaView):
        super().__init__(
            label="Set Formula",
            style=discord.ButtonStyle.primary,
            emoji="🔧",
            row=2
        )
        self.parent_view = parent_view
    
    async def callback(self, interaction: discord.Interaction):
        modal = SetCustomFormulaModal(self.parent_view)
        await interaction.response.send_modal(modal)

class AddDiceModal(ui.Modal, title="Add Dice to Pool"):
    """Modal for adding dice to a dice pool"""
    
    dice_input = ui.TextInput(
        label="Dice to Add",
        placeholder="e.g., 3d20, d12, 2d6",
        required=True,
        max_length=50
    )
    
    def __init__(self, parent_view: DicePoolFormulaView):
        super().__init__()
        self.parent_view = parent_view
    
    async def on_submit(self, interaction: discord.Interaction):
        dice_expr = self.dice_input.value.strip()
        
        # Validate the dice expression
        if not self._validate_dice_expression(dice_expr):
            await interaction.response.send_message(
                "❌ Invalid dice format. Use formats like: `3d20`, `d12`, `2d6`",
                ephemeral=True
            )
            return
        
        # Add to the additional dice list
        self.parent_view.roll_formula_obj.additional_dice.append(dice_expr)
        
        new_view = DicePoolFormulaView(
            character=self.parent_view.character,
            roll_formula_obj=self.parent_view.roll_formula_obj,
            difficulty=self.parent_view.difficulty
        )

        await interaction.response.edit_message(
            view=new_view
        )
    
    def _validate_dice_expression(self, expr: str) -> bool:
        """Validate that the expression is a proper dice format"""
        expr = expr.strip().lower()
        
        # Match "3d20", "d12", etc.
        pattern = r'^\d*d\d+$'
        if not re.match(pattern, expr):
            return False
        
        # Extract and validate numbers
        match = re.match(r'^(\d*)d(\d+)$', expr)
        if match:
            count = int(match.group(1)) if match.group(1) else 1
            die_size = int(match.group(2))
            
            # Reasonable limits
            if count > 100 or count < 1:
                return False
            if die_size > 1000 or die_size < 2:
                return False
        
        return True

class SetTargetNumberModal(ui.Modal, title="Set Difficulty"):
    """Modal for setting the number of successes needed"""
    
    target_number_input = ui.TextInput(
        label="Target Number",
        placeholder="e.g., 3",
        required=True,
        max_length=3
    )
    
    def __init__(self, parent_view: DicePoolFormulaView):
        super().__init__()
        self.parent_view = parent_view
        self.target_number_input.default = str(parent_view.roll_formula_obj.roll_config.target_number)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            target_number = int(self.target_number_input.value)
            if target_number < 1:
                await interaction.response.send_message(
                    "❌ Target number must be at least 1.",
                    ephemeral=True
                )
                return

            # Update the target number
            self.parent_view.roll_formula_obj.roll_config.target_number = target_number

            # Update the button label
            for item in self.parent_view.children:
                if isinstance(item, SetTargetNumberButton):
                    item.label = f"Target Number: {target_number}"
                    break
            
            await interaction.response.edit_message(
                content=f"✅ Set target number to {target_number}.",
                view=self.parent_view
            )
        
        except ValueError:
            await interaction.response.send_message(
                "❌ Please enter a valid number.",
                ephemeral=True
            )

class SetCustomFormulaModal(ui.Modal, title="Set Custom Formula"):
    """Modal for setting a custom dice formula"""
    def __init__(self, parent_view: CustomFormulaView):
        super().__init__()

        self.parent_view = parent_view

        self.formula_input = ui.TextInput(
            label="Custom Formula",
            placeholder="e.g., 1d20+1d4, 2d6+3, 3d8-2",
            default=parent_view.roll_formula_obj.roll_config.dice_formula,
            required=True,
            max_length=100
        )
        self.add_item(self.formula_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        formula = self.formula_input.value.strip()
        
        # Validate the formula (use the same validation from CustomFormulaModal in roll_mechanics.py)
        if not self._validate_formula(formula):
            await interaction.response.send_message(
                "❌ Invalid formula format. Use formats like:\n"
                "• Simple: `1d20`, `2d6`, `3d8`\n"
                "• With modifiers: `1d20+5`, `2d6-2`\n"
                "• With dice modifiers: `1d20+1d4`, `2d6+1d6-1`",
                ephemeral=True
            )
            return
        
        # Store the custom formula in the roll config
        self.parent_view.roll_formula_obj.roll_config.dice_formula = formula

        for item in self.parent_view.children:
            if isinstance(item, FinalizeRollButton):
                item.label = f"Roll {self.parent_view.roll_formula_obj.get_total_dice_formula()}"
                break
        
        await interaction.response.edit_message(
            content=f"✅ Set custom formula: `{formula}`",
            view=self.parent_view
        )
    
    def _validate_formula(self, formula: str) -> bool:
        """Validate dice formula format - supports dice in modifiers"""
        import re
        
        # Remove spaces and convert to lowercase
        clean_formula = formula.replace(' ', '').lower()
        
        # Pattern to match dice expressions with optional dice/numeric modifiers
        base_pattern = r'^\d*d\d+'  # Base dice (e.g., 1d20, 2d6)
        modifier_pattern = r'([+-](?:\d*d\d+|\d+))*'  # Optional modifiers (dice or numbers)
        full_pattern = base_pattern + modifier_pattern + '$'
        
        if not re.match(full_pattern, clean_formula):
            return False
        
        # Additional validation: ensure each dice expression is valid
        parts = re.split(r'([+-])', clean_formula)
        
        for i, part in enumerate(parts):
            if part in ['+', '-']:
                continue
            
            # Check if it's a dice expression
            if 'd' in part:
                dice_match = re.match(r'^(\d*)d(\d+)$', part)
                if not dice_match:
                    return False
                
                # Validate numbers are reasonable
                num_dice = int(dice_match.group(1)) if dice_match.group(1) else 1
                die_size = int(dice_match.group(2))
                
                if num_dice > 100 or die_size > 1000:
                    return False
            else:
                # Check if it's a valid number
                try:
                    int(part)
                except ValueError:
                    return False
        
        return True
