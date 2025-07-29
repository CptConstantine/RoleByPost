import random
import re
from typing import Dict
from dataclasses import dataclass
from core.base_models import RollFormula
from typing import TYPE_CHECKING

from core.generic_roll_mechanics import CoreRollMechanicType, RollMechanicConfig, SuccessCriteria

if TYPE_CHECKING:
    from rpg_systems.mgt2e.mgt2e_character import MGT2ECharacter

@dataclass
class BoonBane:
    """Represents boons and banes in MGT2E"""
    boons: int = 0
    banes: int = 0
    
    @property
    def net_effect(self) -> int:
        """Calculate net effect: positive = boons, negative = banes"""
        return self.boons - self.banes
    
    @property
    def has_effect(self) -> bool:
        """Check if there are any boons or banes"""
        return self.boons > 0 or self.banes > 0
    
    def __str__(self) -> str:
        if not self.has_effect:
            return ""
        
        if self.net_effect > 0:
            return f"Boon +{self.net_effect}"
        elif self.net_effect < 0:
            return f"Bane {self.net_effect}"
        else:
            return "Boon/Bane (cancel out)"

class MGT2ERollFormula(RollFormula):
    """
    A roll formula specifically for the MGT2E RPG system.
    It can handle any roll parameters as needed, including boons and banes.
    """
    def __init__(self, roll_parameters_dict: dict = None):
        roll_config = RollMechanicConfig(
            mechanic_type=CoreRollMechanicType.ROLL_AND_SUM,
            dice_formula="2d6",
            success_criteria=SuccessCriteria.GREATER_EQUAL
        )
        super().__init__(roll_config, roll_parameters_dict)
        self.skill = roll_parameters_dict.get("skill") if roll_parameters_dict else None
        self.attribute = roll_parameters_dict.get("attribute") if roll_parameters_dict else None
        self.boon_bane = self._parse_boon_bane(roll_parameters_dict)

    def _parse_boon_bane(self, roll_parameters_dict: dict) -> BoonBane:
        """Parse boon/bane from roll parameters, including from modifier values"""
        if not roll_parameters_dict:
            return BoonBane()
        
        boons = 0
        banes = 0
        
        # Process each parameter
        for key, value in roll_parameters_dict.items():
            key_lower = key.lower()
            value_lower = str(value).lower() if value else ""
            
            # Check if the key itself indicates boon/bane
            if key_lower in ["boon", "boons", "advantage", "adv"]:
                try:
                    boons += int(value) if str(value).isdigit() else 1
                except (ValueError, TypeError):
                    boons += 1
            elif key_lower in ["bane", "banes", "disadvantage", "disadv", "dis"]:
                try:
                    banes += int(value) if str(value).isdigit() else 1
                except (ValueError, TypeError):
                    banes += 1
            elif key_lower == "b":
                try:
                    boons += int(value) if str(value).isdigit() else 1
                except (ValueError, TypeError):
                    boons += 1
            elif key_lower == "d":
                try:
                    banes += int(value) if str(value).isdigit() else 1
                except (ValueError, TypeError):
                    banes += 1
            elif value_lower in ["boon", "boons", "advantage", "adv"]:
                boons += 1
            elif value_lower in ["bane", "banes", "disadvantage", "disadv", "dis"]:
                banes += 1
        
        return BoonBane(boons=max(0, boons), banes=max(0, banes))

    def get_modifiers(self, character: "MGT2ECharacter") -> Dict[str, str]:
        modifiers = {}
        
        # Get base modifiers first, but filter out boon/bane values
        base_modifiers = super().get_modifiers(character)
        for key, value in base_modifiers.items():
            value_lower = str(value).lower() if value else ""
            # Skip entries that are boons/banes
            if value_lower not in ["boon", "boons", "bane", "banes", "advantage", "adv", "disadvantage", "disadv", "dis"]:
                modifiers[key] = str(value)
        
        # Add skill modifier
        if self.skill:
            skill_value = character.get_skill_modifier(character.skills, self.skill)
            modifiers[self.skill] = str(skill_value)
        
        # Add attribute modifier
        if self.attribute:
            attribute_value = character.attributes.get(self.attribute.upper(), 0)
            attr_mod = character.get_attribute_modifier(attribute_value)
            modifiers[self.attribute.upper()] = str(attr_mod)
        
        # Add boon/bane effect to modifiers for display
        if self.boon_bane.has_effect:
            modifiers["Boon/Bane"] = str(self.boon_bane)
            
        return modifiers
    
    def get_total_dice_formula(self):
        """
        Get the total dice formula including boon/bane, skill and attribute modifiers.
        """
        super().get_total_dice_formula()
        formula = "2d6"
        if self.boon_bane.has_effect:
            if self.boon_bane.net_effect > 0:
                formula = "3d6(boon)"
            elif self.boon_bane.net_effect < 0:
                formula = "3d6(bane)"
        
        if self.skill:
            formula += f"+{self.skill}"
        if self.attribute:
            formula += f"+{self.attribute}"

        # Append simple modifiers
        total_numeric_modifier = 0
        
        for key, value in self.modifiers.items():
            if isinstance(value, str) and re.match(r'^\d*d\d+', value.replace(" ", "")):
                formula += f"+{value}"
            else:
                if not isinstance(value, bool):
                    try:
                        mod = int(value)
                        total_numeric_modifier += mod
                    except (ValueError, TypeError):
                        continue
        
        # Add combined numeric modifier if non-zero
        if total_numeric_modifier != 0:
            formula += f"{total_numeric_modifier:+d}"

        return formula

    def roll_formula(self, character: "MGT2ECharacter", base_roll: str) -> tuple:
        """Execute MGT2E boon/bane rolling mechanics"""
        
        # For MGT2E, the base roll should be 2d6, but we'll roll 3d6 for boons/banes
        if not base_roll.startswith("2d6"):
            # If it's not a 2d6 roll, fall back to standard mechanics
            return super().roll_formula(character, base_roll, self)
        
        # Roll 3d6 for boon/bane mechanics
        dice_rolls = [random.randint(1, 6) for _ in range(3)]
        dice_rolls.sort()
        
        # Determine which dice to keep based on net boon/bane effect
        net_effect = self.boon_bane.net_effect
        
        if net_effect > 0:  # Boons - keep highest 2
            dice_rolls = [random.randint(1, 6) for _ in range(3)]
            dice_rolls.sort()
            kept_dice = dice_rolls[-2:]
            boon_bane_instruction = f"Boon"
        elif net_effect < 0:  # Banes - keep lowest 2
            dice_rolls = [random.randint(1, 6) for _ in range(3)]
            dice_rolls.sort()
            kept_dice = dice_rolls[:2]
            boon_bane_instruction = f"Bane"
        else:  # Cancel out - keep first 2 (standard roll)
            dice_rolls = [random.randint(1, 6) for _ in range(2)]
            kept_dice = dice_rolls
            boon_bane_instruction = ""
        
        base_total = sum(kept_dice)
        
        # Calculate other modifiers (excluding boon/bane)
        modifier_descriptions = []
        total_mod = 0
        
        for key, value in self.get_modifiers(character).items():
            if key == "Boon/Bane":
                continue  # Already handled above
            try:
                mod = int(value)
                total_mod += mod
                sign = "+" if mod >= 0 else ""
                modifier_descriptions.append(f"{key} ({sign}{mod})")
            except (ValueError, TypeError):
                continue
        
        total = base_total + total_mod
        
        # Format the result
        all_dice_str = f"[{', '.join(str(d) for d in dice_rolls)}]"
        kept_dice_str = f"[{', '.join(str(d) for d in kept_dice)}]"
        
        if boon_bane_instruction:
            formula_str = f"3d6 {all_dice_str} → {kept_dice_str} ({boon_bane_instruction})"
        else:
            formula_str = f"2d6 {all_dice_str}"
        if modifier_descriptions:
            formula_str += " + " + " + ".join(modifier_descriptions)
        
        response = f'🎲 {formula_str}\n🧮 Total: {total}'
        return response, total
