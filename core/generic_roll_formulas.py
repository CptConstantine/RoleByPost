from abc import ABC
import random
import re
from typing import Dict, TYPE_CHECKING

from core.generic_roll_mechanics import RollMechanicConfig

if TYPE_CHECKING:
    from core.base_models import BaseCharacter

class RollFormula(ABC):
    """
    A flexible container for roll parameters (e.g., skill, attribute, modifiers).
    Non-modifier properties (like skill, attribute) are stored in a separate dictionary.
    Modifiers are stored in self.modifiers.
    """
    def __init__(self, roll_config: RollMechanicConfig, roll_parameters_dict: dict = None):
        self.roll_config = roll_config

        self.modifiers = {}  # Store direct numeric modifiers (e.g., mod1, mod2)
        if roll_parameters_dict:
            for key, modifier in roll_parameters_dict.items():
                self.modifiers[key] = modifier

    def __getitem__(self, key):
        return self.modifiers.get(key)

    def __setitem__(self, key, value):
        self.modifiers[key] = value

    def to_dict(self):
        return dict(self.modifiers)

    def get_modifiers(self, character: "BaseCharacter") -> Dict[str, str]:
        """
        Returns a dictionary of all modifiers
        """
        return dict(self.modifiers)

    def get_total_dice_formula(self) -> str:
        """
        Returns the total dice formula as a string.
        Combines simple numeric modifiers while keeping dice formula modifiers separate.
        """
        # Start with the base dice formula from roll config
        parts = []
        if self.roll_config.dice_formula:
            parts.append(self.roll_config.dice_formula)
        
        # Separate dice formulas and numeric modifiers
        dice_formulas = []
        total_numeric_modifier = 0
        
        for key, value in self.modifiers.items():
            if isinstance(value, str) and re.match(r'^\d*d\d+', value.replace(" ", "")):
                dice_formulas.append(f"+{value}")
            else:
                try:
                    mod = int(value)
                    total_numeric_modifier += mod
                except (ValueError, TypeError):
                    continue
        
        # Add dice formulas
        parts.extend(dice_formulas)
        
        # Add combined numeric modifier if non-zero
        if total_numeric_modifier != 0:
            parts.append(f"{total_numeric_modifier:+d}")
        
        return "".join(parts) if parts else "1d20"
    
    def roll_formula(self, character: "BaseCharacter", base_roll: str):
        """
        Parses and rolls a dice formula like '2d6+3-2', '1d20+5-1', '1d100', etc.
        Modifiers can now also be dice formulas (e.g., Athletics: 1d6, mod1: 1d12+9).
        Returns a tuple: (result_string, total)
        The result string breaks out the formula into its elements, e.g.:
        4df (+ - - 0) + Athletics (2) + mod1 (10)
        """
        modifier_descriptions = []
        total_mod = 0
        rolled_mods = {}

        # Gather all modifiers and their sources, supporting dice formulas
        for key, value in self.get_modifiers(character).items():
            if isinstance(value, str) and re.match(r'^\d*d\d+', value.replace(" ", "")):
                mod, desc = RollFormula.roll_dice_formula(value)
                rolled_mods[key] = mod  # Store the rolled value for later use
                total_mod += mod
                # Extract the total from the roll_dice_formula result (mod)
                modifier_descriptions.append(f"{key} ({desc})")
            else:
                try:
                    mod = int(value)
                    rolled_mods[key] = mod
                    total_mod += mod
                    sign = "+" if mod >= 0 else ""
                    modifier_descriptions.append(f"{key} ({sign}{mod})")
                except Exception:
                    continue

        # Build the full formula string for rolling, using the already rolled modifiers
        formula = base_roll
        for key, mod in rolled_mods.items():
            if mod >= 0:
                formula += f"+{mod}"
            else:
                formula += f"{mod}"

        formula = formula.replace(" ", "").lower()
        fudge_pattern = r'(\d*)d[fF]((?:[+-]\d+)*)'
        fudge_match = re.fullmatch(fudge_pattern, formula)
        if fudge_match:
            num_dice = int(fudge_match.group(1)) if fudge_match.group(1) else 4
            modifiers_str = fudge_match.group(2) or ""
            modifiers_list = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
            modifier = sum(modifiers_list)
            rolls = [random.choice([-1, 0, 1]) for _ in range(num_dice)]
            symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
            total = sum(rolls) + modifier
            # Compose the detailed formula string
            formula_str = f"{base_roll} `{' '.join(symbols)}`"
            if modifier_descriptions:
                formula_str += " + " + " + ".join(modifier_descriptions)
            response = f'🎲 {formula_str}\n🧮 Total: {total}'
            return response, total

        # Accepts 1d20+3-2, 2d6+1-1, etc.
        pattern = r'(\d*)d(\d+)((?:[+-]\d+)*)'
        match = re.fullmatch(pattern, formula)
        if match:
            num_dice = int(match.group(1)) if match.group(1) else 1
            die_size = int(match.group(2))
            modifiers_str = match.group(3) or ""
            modifiers_list = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
            modifier = sum(modifiers_list)
            if num_dice > 100 or die_size > 1000:
                return "😵 That's a lot of dice. Try fewer.", None
            rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            total = sum(rolls) + modifier
            # Compose the detailed formula string
            formula_str = f"{base_roll} [{', '.join(str(r) for r in rolls)}]"
            if modifier_descriptions:
                formula_str += " + " + " + ".join(modifier_descriptions)
            response = f'🎲 {formula_str}\n🧮 Total: {total}'
            return response, total

        return "❌ Invalid format. Use like `2d6+3-2`, `1d20+5-1`, `1d100`, or `4df+1`.", None

    @staticmethod
    def roll_dice_formula(formula: str):
        formula = formula.replace(" ", "").lower()
        pattern = r'(\d*)d(\d+)((?:[+-]\d+)*)'
        match = re.fullmatch(pattern, formula)
        if match:
            num_dice = int(match.group(1)) if match.group(1) else 1
            die_size = int(match.group(2))
            modifiers_str = match.group(3) or ""
            modifiers_list = [int(m) for m in re.findall(r'[+-]\d+', modifiers_str)]
            modifier = sum(modifiers_list)
            rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            subtotal = sum(rolls) + modifier
            return subtotal, f"{formula} [{subtotal}]"
        # Try to parse as a simple integer
        try:
            return int(formula), str(formula)
        except Exception:
            return 0, formula
        
    @staticmethod
    def roll_parameters_to_dict(roll_parameters: str) -> dict:
        # Parse roll_parameters into roll_parameters_dict
        roll_parameters_dict = {}
        if roll_parameters:
            for param in roll_parameters.split(","):
                if ":" in param:
                    k, v = param.split(":", 1)
                    roll_parameters_dict[k.strip()] = v.strip()
                else:
                    # Handle key-only parameters (e.g., "boon")
                    roll_parameters_dict[param.strip()] = True
        return roll_parameters_dict

class GenericRollFormula(RollFormula):
    """
    A roll formula specifically for the generic RPG system.
    It can handle any roll parameters as needed and supports simplified roll mechanics.
    """
    def __init__(self, roll_config: "RollMechanicConfig", roll_parameters_dict: dict = None):
        super().__init__(roll_config, roll_parameters_dict)

    def roll_formula(self, character: "BaseCharacter", base_roll: str):
        """
        Enhanced roll formula that supports the simplified core roll mechanics
        """
        from core.generic_roll_mechanics import CoreRollMechanicType, execute_roll
        
        # Calculate modifier from character's roll parameters
        total_modifier = 0
        modifier_descriptions = []
        
        for key, value in self.get_modifiers(character).items():
            try:
                mod = int(value)
                total_modifier += mod
                sign = "+" if mod >= 0 else ""
                modifier_descriptions.append(f"{key} ({sign}{mod})")
            except (ValueError, TypeError):
                continue
        
        # Execute the roll using the new simplified mechanics
        try:
            # The dice pool view will handle its own dice formula customization
            # For basic rolls, just use the configured dice formula
            roll_result = execute_roll(self, total_modifier)
            
            # Format the response based on mechanic type
            if self.roll_config.mechanic_type == CoreRollMechanicType.DICE_POOL:
                # For dice pools, format with success display
                response_parts = [f"🎲 {roll_result['description']}"]
                if modifier_descriptions:
                    response_parts.append(f"📝 Modifiers: {', '.join(modifier_descriptions)}")
                
                return "\n".join(response_parts), roll_result['total']
            
            else:
                # For roll-and-sum and custom mechanics
                response_parts = [f"🎲 {roll_result['description']}"]
                if modifier_descriptions and total_modifier != 0:
                    response_parts.append(f"📝 Modifiers: {', '.join(modifier_descriptions)}")
                
                return "\n".join(response_parts), roll_result['total']
                
        except Exception as e:
            # Fallback to standard rolling if the new system fails
            return super().roll_formula(character, self.roll_config.dice_formula or "1d20")

class DicePoolRollFormula(RollFormula):
    """
    A roll formula specifically for Dice Pool mechanics.
    Allows adding multiple dice and setting a target number of successes.
    """
    def __init__(self, roll_config: RollMechanicConfig, roll_parameters_dict: dict = None, difficulty: int = None):
        super().__init__(roll_config, roll_parameters_dict)

        self.difficulty = difficulty
        self.additional_dice = []  # Store additional dice expressions

    def roll_formula(self, character: "BaseCharacter", base_roll: str):
        """Custom roll execution that uses our combined dice formula"""
        from core.generic_roll_mechanics import execute_roll
        
        # Get modifiers using the original method
        total_modifier = 0
        modifier_descriptions = []
        
        for key, value in self.get_modifiers(character).items():
            try:
                mod = int(value)
                total_modifier += mod
                sign = "+" if mod >= 0 else ""
                modifier_descriptions.append(f"{key} ({sign}{mod})")
            except (ValueError, TypeError):
                continue
        
        # Override the dice formula with our combined formula
        combined_formula = self.get_total_dice_formula()
        self.roll_config.dice_formula = combined_formula
        
        # Execute the roll
        try:
            roll_result = execute_roll(self, total_modifier, self.difficulty)

            # Format the response for dice pools
            response_parts = [f"🎲 {roll_result['description']}"]
            if modifier_descriptions:
                response_parts.append(f"📝 Modifiers: {', '.join(modifier_descriptions)}")
            
            return "\n".join(response_parts), roll_result['total']
            
        except Exception as e:
            # Fallback
            return f"❌ Roll failed: {str(e)}", 0
    
    def get_total_dice_formula(self) -> str:
        """Combine base dice formula with additional dice, merging dice of the same size"""
        # Parse and combine all dice
        dice_counts = {}  # {die_size: count}
        
        # Add base dice
        self._add_dice_to_count(self.roll_config.dice_formula, dice_counts)
        
        # Add additional dice
        for dice_expr in self.additional_dice:
            self._add_dice_to_count(dice_expr, dice_counts)
        
        # Format the combined formula, sorted by die size for consistency
        parts = []
        for die_size in sorted(dice_counts.keys(), reverse=True):  # Largest dice first
            count = dice_counts[die_size]
            if count > 0:
                parts.append(f"{count}d{die_size}")
        
        return " + ".join(parts) if parts else "1d10"
    
    def _add_dice_to_count(self, dice_expr: str, dice_counts: dict):
        """Parse a dice expression and add to the count dictionary"""
        # Handle expressions like "3d20", "d12", "2d6", "1d10"
        dice_expr = dice_expr.strip().lower()
        
        # Match patterns like "3d20" or "d12"
        match = re.match(r'^(\d*)d(\d+)$', dice_expr)
        if match:
            count = int(match.group(1)) if match.group(1) else 1
            die_size = int(match.group(2))
            
            # Validate reasonable limits
            if count > 100:
                count = 100  # Cap at 100 dice
            if die_size > 1000:
                die_size = 1000  # Cap at d1000
            
            dice_counts[die_size] = dice_counts.get(die_size, 0) + count

class CustomRollFormula(RollFormula):
    """
    Custom roll formula for complex mechanics.
    Allows custom formulas with modifiers and additional dice.
    """
    def __init__(self, roll_config: RollMechanicConfig, roll_parameters_dict: dict = None, difficulty: int = None):
        super().__init__(roll_config, roll_parameters_dict)
        
        self.difficulty = difficulty

    def roll_formula(self, character, dice_formula_override=None):
        """Custom roll execution that uses our custom formula"""
        from core.generic_roll_mechanics import execute_roll
        
        # Get modifiers using the original method
        total_modifier = 0
        modifier_descriptions = []
        
        for key, value in self.get_modifiers(character).items():
            try:
                mod = int(value)
                total_modifier += mod
                sign = "+" if mod >= 0 else ""
                modifier_descriptions.append(f"{key} ({sign}{mod})")
            except (ValueError, TypeError):
                continue
        
        # Execute the roll
        try:
            roll_result = execute_roll(self, total_modifier, self.difficulty)

            # Format the response
            response_parts = [f"🎲 {roll_result['description']}"]
            if modifier_descriptions and total_modifier != 0:
                response_parts.append(f"📝 Modifiers: {', '.join(modifier_descriptions)}")
            
            return "\n".join(response_parts), roll_result['total']
            
        except Exception as e:
            # Fallback
            return f"❌ Roll failed: {str(e)}", 0