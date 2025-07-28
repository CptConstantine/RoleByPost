from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Optional, Dict, Any
import discord
from discord import ui
import re
import random

if TYPE_CHECKING:
    from core.generic_roll_formulas import RollFormula

class CoreRollMechanicType(Enum):
    ROLL_AND_SUM = "roll_and_sum"
    DICE_POOL = "dice_pool"
    CUSTOM = "custom"

class SuccessCriteria(Enum):
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUAL = "=="

@dataclass
class RollMechanicConfig:
    """Configuration for a server's core roll mechanic"""
    mechanic_type: CoreRollMechanicType
    dice_formula: str  # e.g., "1d20", "2d6", "5d6"
    success_criteria: SuccessCriteria = SuccessCriteria.GREATER_EQUAL
    target_number: Optional[int] = None  # For success threshold
    exploding_dice: bool = False  # Whether dice explode on max roll
    explode_threshold: Optional[int] = None  # What number causes explosion
    description: str = ""  # User-friendly description

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage"""
        return {
            "mechanic_type": self.mechanic_type.value,
            "dice_formula": self.dice_formula,
            "success_criteria": self.success_criteria.value,
            "target_number": self.target_number,
            "exploding_dice": self.exploding_dice,
            "explode_threshold": self.explode_threshold,
            "description": self.description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RollMechanicConfig':
        """Create from dictionary from database"""
        return cls(
            mechanic_type=CoreRollMechanicType(data["mechanic_type"]),
            dice_formula=data["dice_formula"],
            success_criteria=SuccessCriteria(data.get("success_criteria", ">=")),
            target_number=data.get("target_number"),
            exploding_dice=data.get("exploding_dice", False),
            explode_threshold=data.get("explode_threshold"),
            description=data.get("description", "")
        )

def execute_roll(roll_formula_obj: 'RollFormula', modifier: int = 0, difficulty: Optional[int] = None) -> Dict[str, Any]:
    """
    Execute a roll based on the configured mechanic
    
    Args:
        config: The roll mechanic configuration
        modifier: Modifier to add to rolls (for ROLL_AND_SUM)
        target: Target number for success checks
        pool_size: Number of dice in pool (for DICE_POOL)
    
    Returns:
        Dictionary with roll results including:
        - total: Final result/total successes
        - rolls: Individual die results
        - description: Human-readable description
        - success: Whether target was met (if applicable)
    """
    if roll_formula_obj.roll_config.mechanic_type == CoreRollMechanicType.ROLL_AND_SUM:
        return _execute_roll_and_sum(roll_formula_obj, modifier, difficulty)
    elif roll_formula_obj.roll_config.mechanic_type == CoreRollMechanicType.DICE_POOL:
        return _execute_dice_pool(roll_formula_obj, difficulty)
    elif roll_formula_obj.roll_config.mechanic_type == CoreRollMechanicType.CUSTOM:
        return _execute_custom_roll(roll_formula_obj, modifier, difficulty)
    else:
        return {"total": 0, "rolls": [], "description": "Unknown mechanic", "success": False}

def _execute_roll_and_sum(roll_formula_obj: 'RollFormula', modifier: int, difficulty: Optional[int]) -> Dict[str, Any]:
    """Execute roll-and-sum mechanic with support for complex dice formulas"""
    formula = roll_formula_obj.get_total_dice_formula().replace(' ', '').lower()
    
    # Check if this is a simple formula (single dice type with numeric modifiers only)
    simple_pattern = r'^(\d*)d(\d+)([+-]\d+)*$'
    simple_match = re.match(simple_pattern, formula)
    
    if simple_match:
        # Handle simple formula efficiently
        num_dice = int(simple_match.group(1)) if simple_match.group(1) else 1
        die_size = int(simple_match.group(2))
        modifiers_str = simple_match.group(3) or ""
        modifiers_list = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
        formula_modifier = sum(modifiers_list)
        
        # Roll dice
        rolls = []
        for _ in range(num_dice):
            roll = random.randint(1, die_size)
            # Handle exploding dice
            if roll_formula_obj.roll_config.exploding_dice and roll_formula_obj.roll_config.explode_threshold and roll >= roll_formula_obj.roll_config.explode_threshold:
                explosion_rolls = [roll]
                while roll >= roll_formula_obj.roll_config.explode_threshold:
                    roll = random.randint(1, die_size)
                    explosion_rolls.append(roll)
                rolls.append(explosion_rolls)
            else:
                rolls.append(roll)
        
        # Calculate total
        total = 0
        for roll_result in rolls:
            if isinstance(roll_result, list):  # Exploding dice
                total += sum(roll_result)
            else:
                total += roll_result
        
        total += formula_modifier + modifier
        
        # Format description
        roll_desc = []
        for roll_result in rolls:
            if isinstance(roll_result, list):  # Exploding dice
                roll_desc.append(f"[{'+'.join(map(str, roll_result))}]")
            else:
                roll_desc.append(str(roll_result))
        
        description = f"{roll_formula_obj.roll_config.dice_formula}: [{', '.join(roll_desc)}]"
        if formula_modifier != 0:
            description += f" {'+' if formula_modifier >= 0 else ''}{formula_modifier}"
        if modifier != 0:
            description += f" {'+' if modifier >= 0 else ''}{modifier}"
        description += f" = {total}"
        
    else:
        # Handle complex formula with mixed dice types
        total_value = 0
        roll_parts = []
        
        # Split formula into parts while preserving operators
        parts = re.split(r'([+-])', formula)
        current_sign = 1  # Start positive
        
        for i, part in enumerate(parts):
            if part == '+':
                current_sign = 1
                continue
            elif part == '-':
                current_sign = -1
                continue
            
            if 'd' in part:
                # This is a dice expression
                dice_match = re.match(r'^(\d*)d(\d+)$', part)
                if not dice_match:
                    continue
                
                num_dice = int(dice_match.group(1)) if dice_match.group(1) else 1
                die_size = int(dice_match.group(2))
                
                # Roll the dice
                dice_rolls = []
                for _ in range(num_dice):
                    roll = random.randint(1, die_size)
                    
                    # Handle exploding dice
                    if roll_formula_obj.roll_config.exploding_dice and roll_formula_obj.roll_config.explode_threshold and roll >= roll_formula_obj.roll_config.explode_threshold:
                        explosion_rolls = [roll]
                        while roll >= roll_formula_obj.roll_config.explode_threshold:
                            roll = random.randint(1, die_size)
                            explosion_rolls.append(roll)
                        dice_rolls.append(explosion_rolls)
                    else:
                        dice_rolls.append(roll)
                
                # Calculate subtotal for this dice group
                subtotal = 0
                roll_desc_parts = []
                for roll_result in dice_rolls:
                    if isinstance(roll_result, list):  # Exploding dice
                        subtotal += sum(roll_result)
                        roll_desc_parts.append(f"[{'+'.join(map(str, roll_result))}]")
                    else:
                        subtotal += roll_result
                        roll_desc_parts.append(str(roll_result))
                
                # Apply sign and add to total
                signed_subtotal = current_sign * subtotal
                total_value += signed_subtotal
                
                # Format description part
                sign_str = '+' if current_sign > 0 and roll_parts else ''
                if current_sign < 0:
                    sign_str = '-'
                
                if num_dice == 1:
                    roll_parts.append(f"{sign_str}{part}[{roll_desc_parts[0]}]")
                else:
                    roll_parts.append(f"{sign_str}{part}[{', '.join(roll_desc_parts)}]")
            
            else:
                # This is a numeric modifier
                try:
                    numeric_value = int(part)
                    signed_value = current_sign * numeric_value
                    total_value += signed_value
                    
                    sign_str = '+' if current_sign > 0 and roll_parts else ''
                    if current_sign < 0:
                        sign_str = '-'
                    
                    roll_parts.append(f"{sign_str}{abs(numeric_value)}")
                except ValueError:
                    continue
        
        # Add the character modifier
        total_value += modifier
        total = total_value
        
        # Format description for complex formula
        description = ''.join(roll_parts)
        if modifier != 0:
            description += f" {'+' if modifier >= 0 else ''}{modifier}"
        description += f" = {total}"
        
        # Set rolls to the formatted parts for complex formulas
        rolls = roll_parts
    
    # Check success if target provided
    success = None
    if difficulty is not None:
        if roll_formula_obj.roll_config.success_criteria == SuccessCriteria.GREATER_EQUAL:
            success = total >= difficulty
        elif roll_formula_obj.roll_config.success_criteria == SuccessCriteria.LESS_EQUAL:
            success = total <= difficulty
        elif roll_formula_obj.roll_config.success_criteria == SuccessCriteria.EQUAL:
            success = total == difficulty
    
    if difficulty is not None:
        description += f" vs {difficulty} ({'✅' if success else '❌'})"
    
    return {
        "total": total,
        "rolls": rolls,
        "description": description,
        "success": success,
        "modifier": modifier,
        "target": difficulty
    }

def _execute_dice_pool(roll_formula_obj: 'RollFormula', difficulty: Optional[int]) -> Dict[str, Any]:
    """Execute dice pool mechanic - supports mixed die types"""
    import re

    formula = roll_formula_obj.get_total_dice_formula().replace(' ', '').lower()

    # Parse complex dice formulas (e.g., "1d20+2d6+1d4" or "3d10-1d8")
    # Split formula into parts while preserving operators
    parts = re.split(r'([+-])', formula)
    
    # Roll dice pool with mixed die types
    all_rolls = []
    successes = 0
    total_dice_count = 0
    
    # Ensure target_number and explode_threshold are integers
    target_number = int(roll_formula_obj.roll_config.target_number) if roll_formula_obj.roll_config.target_number is not None else 8
    explode_threshold = int(roll_formula_obj.roll_config.explode_threshold) if roll_formula_obj.roll_config.explode_threshold is not None else None

    current_sign = 1  # Start positive
    
    for i, part in enumerate(parts):
        if part == '+':
            current_sign = 1
            continue
        elif part == '-':
            current_sign = -1
            continue
        
        # Skip numeric modifiers in dice pools - only process dice expressions
        if 'd' not in part:
            continue
            
        # Parse dice expression (e.g., "2d10", "1d6", "3d8")
        dice_match = re.match(r'^(\d*)d(\d+)$', part)
        if not dice_match:
            continue
        
        num_dice = int(dice_match.group(1)) if dice_match.group(1) else 1
        die_size = int(dice_match.group(2))
        
        # Only count dice if they're being added (positive sign)
        if current_sign < 0:
            continue
            
        total_dice_count += num_dice
        
        # Roll each die of this type
        for _ in range(num_dice):
            roll = random.randint(1, die_size)
            original_roll = roll
            
            # Handle exploding dice - use die-specific threshold if not set globally
            explosion_rolls = [roll]
            effective_explode_threshold = explode_threshold if explode_threshold is not None else die_size

            if roll_formula_obj.roll_config.exploding_dice and roll >= effective_explode_threshold:
                while roll >= effective_explode_threshold:
                    roll = random.randint(1, die_size)
                    explosion_rolls.append(roll)
            
            # Count successes for each exploding die individually
            die_successes = 0
            for explosion_roll in explosion_rolls:
                roll_success = False
                if roll_formula_obj.roll_config.success_criteria == SuccessCriteria.GREATER_EQUAL:
                    roll_success = explosion_roll >= target_number
                elif roll_formula_obj.roll_config.success_criteria == SuccessCriteria.LESS_EQUAL:
                    roll_success = explosion_roll <= target_number
                elif roll_formula_obj.roll_config.success_criteria == SuccessCriteria.EQUAL:
                    roll_success = explosion_roll == target_number
                
                if roll_success:
                    die_successes += 1
            
            successes += die_successes
            
            # Final value is still the sum for display purposes
            final_value = sum(explosion_rolls) if len(explosion_rolls) > 1 else original_roll
            
            all_rolls.append({
                'value': final_value,
                'original': original_roll,
                'die_type': f"d{die_size}",
                'exploded': len(explosion_rolls) > 1,
                'explosion_rolls': explosion_rolls if len(explosion_rolls) > 1 else None,
                'success': die_successes > 0,
                'success_count': die_successes
            })
    
    # Handle case where no valid dice were found
    if total_dice_count == 0:
        return {"total": 0, "rolls": [], "description": "No valid dice found in formula", "success": False}
    
    # Check overall success if target provided
    overall_success = None
    if difficulty is not None:
        overall_success = successes >= difficulty
    
    # Format description grouped by die type
    die_groups = {}
    for roll_info in all_rolls:
        die_type = roll_info['die_type']
        if die_type not in die_groups:
            die_groups[die_type] = []
        die_groups[die_type].append(roll_info)
    
    # Create grouped roll descriptions
    group_descriptions = []
    for die_type in sorted(die_groups.keys(), key=lambda x: int(x[1:]), reverse=True):  # Sort by die size, largest first
        group_rolls = die_groups[die_type]
        roll_descs = []
        
        for roll_info in group_rolls:
            if roll_info['exploded']:
                desc = f"[{'+'.join(map(str, roll_info['explosion_rolls']))}]"
            else:
                desc = str(roll_info['value'])
            
            if roll_info['success']:
                desc += "✅"
            
            roll_descs.append(desc)
        
        group_descriptions.append(f"{len(group_rolls)}{die_type}: [{', '.join(roll_descs)}]")
    
    # Create a more readable description
    description = f"{formula}: {' + '.join(group_descriptions)}"
    description += f" = {successes} successes"
    
    if difficulty is not None:
        description += f" (needed {difficulty})"
    
    return {
        "total": successes,
        "rolls": all_rolls,
        "description": description,
        "success": overall_success,
        "total_dice": total_dice_count,
        "target": difficulty
    }

def _execute_custom_roll(roll_formula_obj: 'RollFormula', modifier: int, difficulty: Optional[int]) -> Dict[str, Any]:
    """Execute custom roll mechanic with support for complex dice formulas"""
    import re

    formula = roll_formula_obj.get_total_dice_formula().replace(' ', '').lower()

    # Check if this is a simple formula that can use roll-and-sum
    simple_pattern = r'^\d*d\d+([+-]\d+)*$'
    if re.match(simple_pattern, formula):
        # Simple formula with only numeric modifiers - use roll-and-sum
        return _execute_roll_and_sum(roll_formula_obj, modifier, difficulty)
    
    # Complex formula with dice modifiers - need custom parsing
    total_value = 0
    roll_parts = []
    
    # Split formula into parts while preserving operators
    parts = re.split(r'([+-])', formula)
    current_sign = 1  # Start positive
    
    for i, part in enumerate(parts):
        if part == '+':
            current_sign = 1
            continue
        elif part == '-':
            current_sign = -1
            continue
        
        if 'd' in part:
            # This is a dice expression
            dice_match = re.match(r'^(\d*)d(\d+)$', part)
            if not dice_match:
                continue
            
            num_dice = int(dice_match.group(1)) if dice_match.group(1) else 1
            die_size = int(dice_match.group(2))
            
            # Roll the dice
            dice_rolls = []
            for _ in range(num_dice):
                roll = random.randint(1, die_size)
                
                # Handle exploding dice
                if roll_formula_obj.roll_config.exploding_dice and roll_formula_obj.roll_config.explode_threshold and roll >= roll_formula_obj.roll_config.explode_threshold:
                    explosion_rolls = [roll]
                    while roll >= roll_formula_obj.roll_config.explode_threshold:
                        roll = random.randint(1, die_size)
                        explosion_rolls.append(roll)
                    dice_rolls.append(explosion_rolls)
                else:
                    dice_rolls.append(roll)
            
            # Calculate subtotal for this dice group
            subtotal = 0
            roll_desc_parts = []
            for roll_result in dice_rolls:
                if isinstance(roll_result, list):  # Exploding dice
                    subtotal += sum(roll_result)
                    roll_desc_parts.append(f"[{'+'.join(map(str, roll_result))}]")
                else:
                    subtotal += roll_result
                    roll_desc_parts.append(str(roll_result))
            
            # Apply sign and add to total
            signed_subtotal = current_sign * subtotal
            total_value += signed_subtotal
            
            # Format description part
            sign_str = '+' if current_sign > 0 and roll_parts else ''
            if current_sign < 0:
                sign_str = '-'
            
            if num_dice == 1:
                roll_parts.append(f"{sign_str}{part}[{roll_desc_parts[0]}]")
            else:
                roll_parts.append(f"{sign_str}{part}[{', '.join(roll_desc_parts)}]")
        
        else:
            # This is a numeric modifier
            try:
                numeric_value = int(part)
                signed_value = current_sign * numeric_value
                total_value += signed_value
                
                sign_str = '+' if current_sign > 0 and roll_parts else ''
                if current_sign < 0:
                    sign_str = '-'
                
                roll_parts.append(f"{sign_str}{abs(numeric_value)}")
            except ValueError:
                continue
    
    # Add the character modifier
    total_value += modifier
    
    # Check success if target provided
    success = None
    if difficulty is not None:
        if roll_formula_obj.roll_config.success_criteria == SuccessCriteria.GREATER_EQUAL:
            success = total_value >= difficulty
        elif roll_formula_obj.roll_config.success_criteria == SuccessCriteria.LESS_EQUAL:
            success = total_value <= difficulty
        elif roll_formula_obj.roll_config.success_criteria == SuccessCriteria.EQUAL:
            success = total_value == difficulty
    
    # Format description
    description = ''.join(roll_parts)
    if modifier != 0:
        description += f" {'+' if modifier >= 0 else ''}{modifier}"
    description += f" = {total_value}"
    
    if difficulty is not None:
        description += f" vs {difficulty} ({'✅' if success else '❌'})"
    
    return {
        "total": total_value,
        "rolls": roll_parts,  # Store the formatted parts
        "description": description,
        "success": success,
        "modifier": modifier,
        "target": difficulty
    }

class CoreRollMechanicSelectView(ui.View):
    """Main view for selecting core roll mechanic type"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.selected_config: Optional[RollMechanicConfig] = None
        
    @ui.select(
        placeholder="Choose your core roll mechanic type...",
        options=[
            discord.SelectOption(
                label="Roll and Sum",
                value="roll_and_sum",
                description="Roll dice, add them up, compare to target (D&D, Traveller, etc.)",
                emoji="🎲"
            ),
            discord.SelectOption(
                label="Dice Pool",
                value="dice_pool", 
                description="Roll multiple dice, count individual successes (World of Darkness, etc.)",
                emoji="🎯"
            ),
            discord.SelectOption(
                label="Custom",
                value="custom",
                description="Flexible custom roll configuration for unique systems",
                emoji="🔧"
            )
        ]
    )
    async def select_mechanic(self, interaction: discord.Interaction, select: ui.Select):
        mechanic_type = CoreRollMechanicType(select.values[0])
        
        # Create configuration view based on selection
        config_view = self._get_config_view(mechanic_type)
        
        embed = discord.Embed(
            title=f"Configure {select.options[0].label}",
            description="Set up the specific parameters for your roll mechanic.",
            color=discord.Color.blue()
        )
        
        await interaction.response.edit_message(embed=embed, view=config_view)
    
    def _get_config_view(self, mechanic_type: CoreRollMechanicType) -> ui.View:
        """Get the appropriate configuration view for the mechanic type"""
        if mechanic_type == CoreRollMechanicType.ROLL_AND_SUM:
            return RollAndSumConfigView()
        elif mechanic_type == CoreRollMechanicType.DICE_POOL:
            return DicePoolConfigView()
        elif mechanic_type == CoreRollMechanicType.CUSTOM:
            return CustomConfigView()
        else:
            return BasicConfigView(mechanic_type)

class RollAndSumConfigView(ui.View):
    """Configuration view for Roll and Sum mechanics"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanicType.ROLL_AND_SUM,
            dice_formula="1d20",
            success_criteria=SuccessCriteria.GREATER_EQUAL,
            description="Roll and sum dice vs target"
        )
    
    @ui.select(
        placeholder="Choose base dice formula...",
        options=[
            discord.SelectOption(label="1d20 (D&D style)", value="1d20", description="Single d20 roll"),
            discord.SelectOption(label="2d6 (Traveller style)", value="2d6", description="Two d6 dice"),
            discord.SelectOption(label="3d6 (GURPS style)", value="3d6", description="Three d6 dice"),
            discord.SelectOption(label="1d100 (Percentile)", value="1d100", description="d100 roll"),
            discord.SelectOption(label="2d10 (Numenera style)", value="2d10", description="Two d10 dice"),
        ]
    )
    async def select_dice(self, interaction: discord.Interaction, select: ui.Select):
        self.config.dice_formula = select.values[0]
        await self._update_display(interaction)
    
    @ui.select(
        placeholder="Choose success criteria...",
        options=[
            discord.SelectOption(label=">= (Greater than or equal)", value=">=", description="Roll must be >= target"),
            discord.SelectOption(label="<= (Less than or equal)", value="<=", description="Roll must be <= target"),
            discord.SelectOption(label="== (Exactly equal)", value="==", description="Roll must exactly equal target"),
        ]
    )
    async def select_success(self, interaction: discord.Interaction, select: ui.Select):
        self.config.success_criteria = SuccessCriteria(select.values[0])
        await self._update_display(interaction)
    
    @ui.button(label="Set Custom Formula", style=discord.ButtonStyle.primary, emoji="🎲")
    async def set_custom_formula(self, interaction: discord.Interaction, button: ui.Button):
        modal = CustomFormulaModal(self.config)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Toggle Exploding Dice", style=discord.ButtonStyle.secondary, emoji="💥")
    async def toggle_exploding(self, interaction: discord.Interaction, button: ui.Button):
        self.config.exploding_dice = not self.config.exploding_dice
        if self.config.exploding_dice and not self.config.explode_threshold:
            # Set default explosion threshold based on dice type
            if "d6" in self.config.dice_formula:
                self.config.explode_threshold = 6
            elif "d8" in self.config.dice_formula:
                self.config.explode_threshold = 8
            elif "d10" in self.config.dice_formula:
                self.config.explode_threshold = 10
            elif "d20" in self.config.dice_formula:
                self.config.explode_threshold = 20
            else:
                self.config.explode_threshold = 6  # Default
        await self._update_display(interaction)
    
    @ui.button(label="Confirm Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _update_display(self, interaction: discord.Interaction):
        embed = self._create_config_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def _create_config_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎲 Roll and Sum Configuration",
            description="Configure how dice are rolled and summed for success checks.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Dice Formula", value=self.config.dice_formula, inline=True)
        embed.add_field(name="Success Criteria", value=self.config.success_criteria.value, inline=True)
        embed.add_field(name="Exploding Dice", value="✅ Enabled" if self.config.exploding_dice else "❌ Disabled", inline=True)
        
        if self.config.exploding_dice:
            embed.add_field(name="Explode Threshold", value=str(self.config.explode_threshold), inline=True)
        
        example = f"`{self.config.dice_formula}` {self.config.success_criteria.value} target"
        if self.config.exploding_dice:
            example += f" (explodes on {self.config.explode_threshold})"
        embed.add_field(name="Example", value=example, inline=False)
        
        return embed
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        self.config.description = f"{self.config.dice_formula} {self.config.success_criteria.value} target"
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**Roll and Sum** is now active for this server.\n\n"
                       f"Players will roll: `{self.config.dice_formula}` {self.config.success_criteria.value} target",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class DicePoolConfigView(ui.View):
    """Configuration view for Dice Pool mechanics"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanicType.DICE_POOL,
            dice_formula="1d10",
            success_criteria=SuccessCriteria.GREATER_EQUAL,
            target_number=8,
            description="Count successes in dice pool"
        )
    
    @ui.select(
        placeholder="Choose die type for pool...",
        options=[
            discord.SelectOption(label="d6 (many systems)", value="1d6", description="Single six-sided dice"),
            discord.SelectOption(label="d8 (some systems)", value="1d8", description="Single eight-sided dice"),
            discord.SelectOption(label="d10 (World of Darkness)", value="1d10", description="Single ten-sided dice"),
            discord.SelectOption(label="d12 (rare systems)", value="1d12", description="Single twelve-sided dice"),
            discord.SelectOption(label="2d6 (complex pools)", value="2d6", description="Two d6 per pool entry"),
            discord.SelectOption(label="2d10 (complex pools)", value="2d10", description="Two d10 per pool entry"),
        ]
    )
    async def select_die_type(self, interaction: discord.Interaction, select: ui.Select):
        self.config.dice_formula = select.values[0]
        # Set default success threshold based on die type
        if "d6" in select.values[0]:
            self.config.target_number = 5
        elif "d8" in select.values[0]:
            self.config.target_number = 6
        elif "d10" in select.values[0]:
            self.config.target_number = 8
        elif "d12" in select.values[0]:
            self.config.target_number = 9
        
        # For multi-dice pools, use higher thresholds
        if select.values[0] == "2d6":
            self.config.target_number = 8  # Sum of 2d6 >= 8
        elif select.values[0] == "2d10":
            self.config.target_number = 12  # Sum of 2d10 >= 12
            
        await self._update_display(interaction)
    
    @ui.select(
        placeholder="Choose success criteria...",
        options=[
            discord.SelectOption(label=">= (Greater than or equal)", value=">=", description="Die shows >= target"),
            discord.SelectOption(label="<= (Less than or equal)", value="<=", description="Die shows <= target"),
            discord.SelectOption(label="== (Exactly equal)", value="==", description="Die shows exactly target"),
        ]
    )
    async def select_success(self, interaction: discord.Interaction, select: ui.Select):
        self.config.success_criteria = SuccessCriteria(select.values[0])
        await self._update_display(interaction)
    
    @ui.button(label="Set Success Threshold", style=discord.ButtonStyle.primary, emoji="🎯")
    async def set_threshold(self, interaction: discord.Interaction, button: ui.Button):
        modal = SuccessThresholdModal(self.config)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Set Custom Formula", style=discord.ButtonStyle.primary, emoji="🎲")
    async def set_custom_formula(self, interaction: discord.Interaction, button: ui.Button):
        modal = CustomFormulaModal(self.config)
        await interaction.response.send_modal(modal)
    
    @ui.button(label="Toggle Exploding Dice", style=discord.ButtonStyle.secondary, emoji="💥")
    async def toggle_exploding(self, interaction: discord.Interaction, button: ui.Button):
        self.config.exploding_dice = not self.config.exploding_dice
        if self.config.exploding_dice and not self.config.explode_threshold:
            # Set explosion threshold to max die value
            if "d6" in self.config.dice_formula:
                self.config.explode_threshold = 6
            elif "d8" in self.config.dice_formula:
                self.config.explode_threshold = 8
            elif "d10" in self.config.dice_formula:
                self.config.explode_threshold = 10
            elif "d12" in self.config.dice_formula:
                self.config.explode_threshold = 12
        await self._update_display(interaction)
    
    @ui.button(label="Confirm Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        await self._save_config(interaction)
    
    async def _update_display(self, interaction: discord.Interaction):
        embed = self._create_config_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def _create_config_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🎯 Dice Pool Configuration",
            description="Configure how dice pools work and what counts as success.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Die Type", value=self.config.dice_formula, inline=True)
        embed.add_field(name="Success Criteria", value=self.config.success_criteria.value, inline=True)
        embed.add_field(name="Success Threshold", value=str(self.config.target_number), inline=True)
        embed.add_field(name="Exploding Dice", value="✅ Enabled" if self.config.exploding_dice else "❌ Disabled", inline=True)
        
        if self.config.exploding_dice:
            embed.add_field(name="Explode Threshold", value=str(self.config.explode_threshold), inline=True)
        
        example = f"Roll multiple {self.config.dice_formula}, count successes ({self.config.success_criteria.value} {self.config.target_number})"
        if self.config.exploding_dice:
            example += f", explodes on {self.config.explode_threshold}"
        embed.add_field(name="Example", value=example, inline=False)
        
        return embed
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        self.config.description = f"Pool of {self.config.dice_formula}, success on {self.config.success_criteria.value} {self.config.target_number}"
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**Dice Pool** is now active for this server.\n\n"
                       f"Players will roll pools of {self.config.dice_formula} and count successes ({self.config.success_criteria.value} {self.config.target_number})",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class CustomConfigView(ui.View):
    """Configuration view for Custom mechanics"""
    
    def __init__(self):
        super().__init__(timeout=300)
        self.config = RollMechanicConfig(
            mechanic_type=CoreRollMechanicType.CUSTOM,
            dice_formula="1d20",
            success_criteria=SuccessCriteria.GREATER_EQUAL,
            description="Custom roll configuration"
        )
    
    @ui.button(label="Set Dice Formula", style=discord.ButtonStyle.primary, emoji="🎲")
    async def set_formula(self, interaction: discord.Interaction, button: ui.Button):
        modal = CustomFormulaModal(self.config)
        await interaction.response.send_modal(modal)
    
    @ui.select(
        placeholder="Choose success criteria...",
        options=[
            discord.SelectOption(label=">= (Greater than or equal)", value=">=", description="Roll must be >= target"),
            discord.SelectOption(label="<= (Less than or equal)", value="<=", description="Roll must be <= target"),
            discord.SelectOption(label="== (Exactly equal)", value="==", description="Roll must exactly equal target"),
        ]
    )
    async def select_success(self, interaction: discord.Interaction, select: ui.Select):
        self.config.success_criteria = SuccessCriteria(select.values[0])
        await self._update_display(interaction)
    
    @ui.button(label="Toggle Exploding Dice", style=discord.ButtonStyle.secondary, emoji="💥")
    async def toggle_exploding(self, interaction: discord.Interaction, button: ui.Button):
        self.config.exploding_dice = not self.config.exploding_dice
        if self.config.exploding_dice and not self.config.explode_threshold:
            modal = ExplodeThresholdModal(self.config)
            await interaction.response.send_modal(modal)
            return
        await self._update_display(interaction)
    
    @ui.button(label="Confirm Setup", style=discord.ButtonStyle.success, emoji="✅")
    async def confirm_setup(self, interaction: discord.Interaction, button: ui.Button):
        if not self.config.dice_formula or self.config.dice_formula == "1d20":
            await interaction.response.send_message("❌ Please set a custom dice formula first.", ephemeral=True)
            return
        await self._save_config(interaction)
    
    async def _update_display(self, interaction: discord.Interaction):
        embed = self._create_config_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    def _create_config_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="🔧 Custom Configuration",
            description="Create a flexible custom roll configuration.",
            color=discord.Color.blue()
        )
        
        embed.add_field(name="Dice Formula", value=self.config.dice_formula, inline=True)
        embed.add_field(name="Success Criteria", value=self.config.success_criteria.value, inline=True)
        embed.add_field(name="Exploding Dice", value="✅ Enabled" if self.config.exploding_dice else "❌ Disabled", inline=True)
        
        if self.config.exploding_dice and self.config.explode_threshold:
            embed.add_field(name="Explode Threshold", value=str(self.config.explode_threshold), inline=True)
        
        example = f"`{self.config.dice_formula}` {self.config.success_criteria.value} target"
        if self.config.exploding_dice:
            example += f" (explodes on {self.config.explode_threshold})"
        embed.add_field(name="Example", value=example, inline=False)
        
        return embed
    
    async def _save_config(self, interaction: discord.Interaction):
        from data.repositories.repository_factory import repositories
        self.config.description = f"Custom: {self.config.dice_formula} {self.config.success_criteria.value} target"
        repositories.server.set_core_roll_mechanic(interaction.guild.id, self.config.to_dict())
        
        embed = discord.Embed(
            title="✅ Roll Mechanic Configured",
            description=f"**Custom** mechanics are now active for this server.\n\n"
                       f"Players will use: `{self.config.dice_formula}` {self.config.success_criteria.value} target",
            color=discord.Color.green()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)

class SuccessThresholdModal(ui.Modal, title="Set Success Threshold"):
    """Modal for setting success threshold for dice pools"""
    
    threshold = ui.TextInput(
        label="Success Threshold",
        placeholder="e.g., 8 (for d10), 5 (for d6)",
        required=True,
        max_length=2
    )
    
    def __init__(self, config: RollMechanicConfig):
        super().__init__()
        self.config = config
        if config.target_number:
            self.threshold.default = str(config.target_number)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            threshold_val = int(self.threshold.value)
            if threshold_val < 1 or threshold_val > 20:
                await interaction.response.send_message("❌ Threshold must be between 1 and 20.", ephemeral=True)
                return
            
            self.config.target_number = threshold_val
            await interaction.response.send_message("✅ Success threshold updated!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)

class CustomFormulaModal(ui.Modal, title="Custom Dice Formula"):
    """Modal for entering custom dice formulas"""
    
    formula = ui.TextInput(
        label="Dice Formula",
        placeholder="e.g., 3d6, 1d20+5, 2d10+1d6, 3d8-2",
        required=True,
        max_length=100
    )
    
    def __init__(self, config: RollMechanicConfig):
        super().__init__()
        self.config = config
        if config.dice_formula and config.dice_formula != "1d20":
            self.formula.default = config.dice_formula
    
    async def on_submit(self, interaction: discord.Interaction):
        # Validate the formula
        if not self._validate_formula(self.formula.value):
            await interaction.response.send_message(
                "❌ Invalid formula format. Use formats like:\n"
                "• Simple: `1d20`, `2d6`, `3d8`\n"
                "• With modifiers: `1d20+5`, `2d6-2`\n"
                "• With dice modifiers: `1d20+1d4`, `2d6+1d6-1`, `1d10+2d4-3`", 
                ephemeral=True
            )
            return
        
        self.config.dice_formula = self.formula.value
        await interaction.response.send_message("✅ Custom formula set!", ephemeral=True)
    
    def _validate_formula(self, formula: str) -> bool:
        """Validate dice formula format - now supports dice in modifiers"""
        import re
        
        # Remove spaces and convert to lowercase
        clean_formula = formula.replace(' ', '').lower()
        
        # Pattern to match dice expressions with optional dice/numeric modifiers
        # Examples: 1d20, 2d6+3, 3d8-2, 1d20+1d4, 2d6+1d6-1, 1d10+2d4-3
        base_pattern = r'^\d*d\d+'  # Base dice (e.g., 1d20, 2d6)
        modifier_pattern = r'([+-](?:\d*d\d+|\d+))*'  # Optional modifiers (dice or numbers)
        full_pattern = base_pattern + modifier_pattern + '$'
        
        if not re.match(full_pattern, clean_formula):
            return False
        
        # Additional validation: ensure each dice expression is valid
        # Split by + and - while keeping the operators
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

class ExplodeThresholdModal(ui.Modal, title="Set Explosion Threshold"):
    """Modal for setting explosion threshold"""
    
    threshold = ui.TextInput(
        label="Explosion Threshold",
        placeholder="e.g., 6 (for d6), 20 (for d20)",
        required=True,
        max_length=2
    )
    
    def __init__(self, config: RollMechanicConfig):
        super().__init__()
        self.config = config
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            threshold_val = int(self.threshold.value)
            if threshold_val < 1 or threshold_val > 100:
                await interaction.response.send_message("❌ Threshold must be between 1 and 100.", ephemeral=True)
                return
            
            self.config.explode_threshold = threshold_val
            await interaction.response.send_message("✅ Explosion threshold set!", ephemeral=True)
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number.", ephemeral=True)

class BasicConfigView(ui.View):
    """Fallback configuration view"""
    
    def __init__(self, mechanic_type: CoreRollMechanicType):
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
