from typing import List
import discord
from discord.ext import commands
from discord import app_commands
from commands.character_commands import multi_character_autocomplete
from core.base_models import SystemType
from core.command_decorators import no_ic_channels, player_or_gm_role_required
from core.roll_formula import RollFormula
from core.shared_views import RequestRollView
import core.factories as factories
from data.repositories.repository_factory import repositories
from rpg_systems.fate.fate_character import FateCharacter
from rpg_systems.mgt2e.mgt2e_character import MGT2ECharacter

async def roll_parameters_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Provide helpful autocomplete for roll parameters based on the system"""
    system = repositories.server.get_system(str(interaction.guild.id))
    
    choices = []
    
    # Parse what's already been typed
    parts = current.split(',') if current else []
    current_typing = parts[-1].strip() if parts else ""
    
    # System-specific suggestions
    if system == SystemType.FATE:
        choices.extend(await _get_fate_roll_parameter_choices(interaction.guild.id, current, parts, current_typing))
    elif system == SystemType.MGT2E:
        choices.extend(await _get_mgt2e_roll_parameter_choices(interaction.guild.id, current, parts, current_typing))
    else:
        # Generic system - just add modifiers
        choices.extend(_get_generic_modifier_choices(current, parts))
    
    return choices[:25]  # Discord limit

async def _get_fate_roll_parameter_choices(guild_id: str, current: str, parts: List[str], current_typing: str) -> List[app_commands.Choice[str]]:
    """Get Fate-specific roll parameter choices"""
    choices = []
    
    # Check if skill is already specified
    has_skill = any("skill:" in part for part in parts)
    
    # If nothing is typed yet or we're starting fresh, show main categories
    if not current_typing:
        if not has_skill:
            choice_value = f"{current},skill:" if current else "skill:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        # Build the prefix correctly - everything except the current incomplete part
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        # Add modifier option
        existing_mods = len([p for p in parts if p.strip().startswith("mod")])
        if existing_mods < 3:
            mod_num = existing_mods + 1
            choice_value = f"{prefix}mod{mod_num}:" if current else f"mod{mod_num}:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        return choices
    
    # If they're typing after "skill:", show skill suggestions
    if current_typing.startswith("skill:"):
        skill_part = current_typing[6:]  # Remove "skill:" prefix
        
        # Get default skills for this guild/system
        default_skills = repositories.default_skills.get_default_skills(guild_id, SystemType.FATE)
        if not default_skills:
            default_skills = FateCharacter.DEFAULT_SKILLS
        
        # Build the prefix correctly - everything except the current incomplete part
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        # Offer specific skills from the guild's default list
        for skill_name in sorted(default_skills.keys())[:15]:  # Limit to prevent overflow
            if not skill_part or skill_name.lower().startswith(skill_part.lower()):
                choice_value = f"{prefix}skill:{skill_name}"
                choices.append(app_commands.Choice(
                    name=choice_value, 
                    value=choice_value
                ))
    
    # If they're typing after "modX:", show number suggestions
    elif any(current_typing.startswith(f"mod{i}:") for i in range(1, 4)):
        mod_part = current_typing.split(":", 1)[1] if ":" in current_typing else ""
        mod_name = current_typing.split(":", 1)[0] if ":" in current_typing else current_typing
        
        # Build the prefix correctly
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        # Common modifier values
        common_values = ["-3", "-2", "-1", "+1", "+2", "+3"]
        for value in common_values:
            if not mod_part or value.startswith(mod_part):
                choice_value = f"{prefix}{mod_name}:{value}"
                choices.append(app_commands.Choice(
                    name=choice_value, 
                    value=choice_value
                ))
    
    return choices

async def _get_mgt2e_roll_parameter_choices(guild_id: str, current: str, parts: List[str], current_typing: str) -> List[app_commands.Choice[str]]:
    """Get MGT2E-specific roll parameter choices"""
    choices = []
    
    # Check what's already specified
    has_skill = any("skill:" in part for part in parts)
    has_attribute = any("attribute:" in part for part in parts)
    has_boon = any("boon" in part.lower() for part in parts)
    has_bane = any("bane" in part.lower() for part in parts)
    
    # If nothing is typed yet or we're starting fresh, show main categories
    if not current_typing:
        if not has_skill:
            choice_value = f"{current}skill:" if current else "skill:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        if not has_attribute:
            choice_value = f"{current}attribute:" if current else "attribute:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        if not has_boon and not has_bane:
            choice_value = f"{current}boon" if current else "boon"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
            
            choice_value = f"{current}bane" if current else "bane"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        # Add modifier option
        existing_mods = len([p for p in parts if p.strip().startswith("mod")])
        if existing_mods < 3:
            mod_num = existing_mods + 1
            choice_value = f"{current}mod{mod_num}:" if current else f"mod{mod_num}:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        return choices
    
    # If they're typing after "skill:", show skill suggestions
    if current_typing.startswith("skill:"):
        skill_part = current_typing[6:]  # Remove "skill:" prefix
        
        # Get default skills for this guild/system
        default_skills = repositories.default_skills.get_default_skills(guild_id, SystemType.MGT2E)
        if not default_skills:
            default_skills = MGT2ECharacter.DEFAULT_SKILLS
        
        # Build the prefix correctly
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        if default_skills:
            # Show a few popular skills first
            popular_skills = ["Admin", "Athletics", "Gun Combat", "Pilot", "Recon", "Stealth"]
            for skill_name in popular_skills:
                if skill_name in default_skills and (not skill_part or skill_name.lower().startswith(skill_part.lower())):
                    choice_value = f"{prefix}skill:{skill_name}"
                    choices.append(app_commands.Choice(
                        name=choice_value, 
                        value=choice_value
                    ))
    
    # If they're typing after "attribute:", show attribute suggestions
    elif current_typing.startswith("attribute:"):
        attr_part = current_typing[10:]  # Remove "attribute:" prefix
        
        # Build the prefix correctly
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        attributes = ["STR", "DEX", "END", "INT", "EDU", "SOC"]
        for attr in attributes:
            if not attr_part or attr.lower().startswith(attr_part.lower()):
                choice_value = f"{prefix}attribute:{attr}"
                choices.append(app_commands.Choice(
                    name=choice_value, 
                    value=choice_value
                ))
    
    # If they're typing after "modX:", show number suggestions
    elif any(current_typing.startswith(f"mod{i}:") for i in range(1, 4)):
        mod_part = current_typing.split(":", 1)[1] if ":" in current_typing else ""
        mod_name = current_typing.split(":", 1)[0] if ":" in current_typing else current_typing
        
        # Build the prefix correctly
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        # Common modifier values
        common_values = ["-3", "-2", "-1", "+1", "+2", "+3"]
        for value in common_values:
            if not mod_part or value.startswith(mod_part):
                choice_value = f"{prefix}{mod_name}:{value}"
                choices.append(app_commands.Choice(
                    name=choice_value, 
                    value=choice_value
                ))
    
    return choices

def _get_mgt2e_skill_categories(skills_dict: dict) -> dict:
    """Group MGT2E skills by category"""
    categories = {}
    for skill_name in skills_dict.keys():
        if "(" in skill_name and ")" in skill_name:
            category = skill_name.split("(", 1)[0].strip()
            if category not in categories:
                categories[category] = []
            categories[category].append(skill_name)
        else:
            categories[skill_name] = [skill_name]
    return categories

def _get_generic_modifier_choices(current: str, parts: List[str]) -> List[app_commands.Choice[str]]:
    """Get generic modifier choices that work for any system"""
    choices = []
    
    # Count existing modifiers
    existing_mods = len([p for p in parts if p.strip().startswith("mod")])
    
    if existing_mods < 3:
        mod_num = existing_mods + 1
        choice_value = f"{current},mod{mod_num}:" if current else f"mod{mod_num}:"
        choices.append(app_commands.Choice(
            name=choice_value, 
            value=choice_value
        ))
    
    return choices

class RollCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    roll_group = app_commands.Group(name="roll", description="Dice rolling commands")

    @roll_group.command(
        name="check",
        description="Roll dice for your active character"
    )
    @app_commands.describe(
        roll_parameters="Roll parameters, e.g. skill:Athletics,attribute:END,mod1:2,mod2:-1",
        difficulty="Optional difficulty number to compare against (e.g. 15)"
    )
    @app_commands.autocomplete(roll_parameters=roll_parameters_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def roll_check(self, interaction: discord.Interaction, roll_parameters: str = None, difficulty: int = None):
        character = repositories.active_character.get_active_character(str(interaction.guild.id), str(interaction.user.id))
        if not character:
            await interaction.response.send_message("❌ No active character set or character not found.", ephemeral=True)
            return
        
        system = repositories.server.get_system(str(interaction.guild.id))
        roll_parameters_dict = RollFormula.roll_parameters_to_dict(roll_parameters)
        roll_formula_obj = factories.get_specific_roll_formula(system, roll_parameters_dict)
        await character.send_roll_message(interaction, roll_formula_obj, difficulty)

    @roll_group.command(
        name="custom",
        description="Open the custom roll interface for your character"
    )
    @player_or_gm_role_required()
    @no_ic_channels()
    async def roll_custom(self, interaction: discord.Interaction):
        """Open a fully interactive UI for rolling dice with your character"""
        character = repositories.active_character.get_active_character(str(interaction.guild.id), str(interaction.user.id))
        if not character:
            await interaction.response.send_message("❌ No active character set. Use `/char switch` to choose one.", ephemeral=True)
            return
        
        system = repositories.server.get_system(str(interaction.guild.id))
        roll_formula_obj = factories.get_specific_roll_formula(system, {})
        formula_view = factories.get_specific_roll_formula_view(system, roll_formula_obj)
        await interaction.response.send_message(
            content=f"🎲 What will **{character.name}** roll?",
            view=formula_view,
            ephemeral=True
        )

    @roll_group.command(
        name="request", 
        description="GM: Prompt selected characters to roll with a button"
    )
    @app_commands.describe(
        chars_to_roll="Comma-separated character names to request",
        roll_parameters="Roll parameters, e.g. skill:Athletics,attribute:END",
        difficulty="Optional difficulty number to compare against (e.g. 15)"
    )
    @app_commands.autocomplete(chars_to_roll=multi_character_autocomplete)
    @app_commands.autocomplete(roll_parameters=roll_parameters_autocomplete)
    @player_or_gm_role_required()
    @no_ic_channels()
    async def roll_request(
        self,
        interaction: discord.Interaction,
        chars_to_roll: str,
        roll_parameters: str = None,
        difficulty: int = None
    ):
        system = repositories.server.get_system(str(interaction.guild.id))
        all_chars = repositories.character.get_all_pcs_and_npcs_by_guild(str(interaction.guild.id))
        char_names = [name.strip() for name in chars_to_roll.split(",") if name.strip()]
        chars = [c for c in all_chars if c.name in char_names]
        if not chars:
            await interaction.response.send_message("❌ No matching characters found.", ephemeral=True)
            return

        # Mention users
        mentions = []
        for char in chars:
            if not char.is_npc:
                try:
                    member = await interaction.guild.fetch_member(int(char.owner_id))
                    if member and member not in mentions:
                        mentions.append(member.mention)
                except discord.NotFound:
                    continue  # Member not found in guild
                except discord.HTTPException:
                    continue  # Network or API error
        mention_str = " ".join(mentions) if mentions else ""

        # Parse roll_parameters
        roll_parameters_dict = RollFormula.roll_parameters_to_dict(roll_parameters)
        roll_formula_obj = factories.get_specific_roll_formula(system, roll_parameters_dict)

        view = RequestRollView(roll_formula=roll_formula_obj, difficulty=difficulty)
        await interaction.response.send_message(
            content=f"{mention_str}\n{interaction.user.display_name} requests a roll: `{roll_parameters}`",
            view=view
        )

async def setup_roll_commands(bot: commands.Bot):
    await bot.add_cog(RollCommands(bot))