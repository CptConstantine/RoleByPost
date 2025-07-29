import discord
from discord.ext import commands
from discord import app_commands
from commands.autocomplete import multi_character_autocomplete, roll_parameters_autocomplete
from core.command_decorators import no_ic_channels, player_or_gm_role_required
from core.generic_roll_formulas import RollFormula
from core.generic_roll_mechanics import execute_roll
from core.shared_views import RequestRollView
import core.factories as factories
from data.repositories import character_repository
from data.repositories.repository_factory import repositories

class RollCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    roll_group = app_commands.Group(name="roll", description="Dice rolling commands")

    @roll_group.command(
        name="simple",
        description="Roll a simple dice formula (e.g., 1d20+5, 2d6+1d4-2)"
    )
    @app_commands.describe(
        formula="Dice formula to roll (e.g., 1d20+5, 2d6, 3d8-1)"
    )
    @player_or_gm_role_required()
    @no_ic_channels()
    async def roll_simple(self, interaction: discord.Interaction, formula: str):
        """Roll a simple dice formula without requiring character sheets"""
        from core.generic_roll_formulas import RollFormula
        
        # Validate and clean the formula
        formula = formula.strip()
        if not formula:
            await interaction.response.send_message("❌ Please provide a dice formula.", ephemeral=True)
            return
        
        # Basic validation - ensure it contains 'd' and looks like a dice formula
        if 'd' not in formula.lower():
            await interaction.response.send_message("❌ Invalid dice formula. Use format like `1d20+5`, `2d6`, `3d8-1`, etc.", ephemeral=True)
            return
        
        try:
            # Create a basic roll formula with no modifiers
            from core.generic_roll_mechanics import RollMechanicConfig, CoreRollMechanicType, SuccessCriteria
            roll_config = RollMechanicConfig(
                mechanic_type=CoreRollMechanicType.ROLL_AND_SUM,
                dice_formula=formula,
                success_criteria=SuccessCriteria.GREATER_EQUAL
            )
            
            # Create roll formula with empty modifiers
            roll_formula_obj = RollFormula(roll_config, {})
            
            result = execute_roll(roll_formula_obj=roll_formula_obj)
            
            if result is None:
                await interaction.response.send_message("❌ Invalid dice formula format. Use like `2d6+3-2`, `1d20+5-1`, `1d100`, or `4dF+1`.", ephemeral=True)
                return
            
            await interaction.response.send_message(content=result['description'])
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Error rolling dice: {str(e)}", ephemeral=True)

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
        roll_formula_obj = factories.get_specific_roll_formula(interaction.guild.id, system, roll_parameters_dict)
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
        roll_formula_obj = factories.get_specific_roll_formula(interaction.guild.id, system, {})
        formula_view = factories.get_specific_roll_formula_view(interaction.guild.id, character, system, roll_formula_obj)
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
        users_requested = []
        for char in chars:
            if not char.is_npc:
                try:
                    member = await interaction.guild.fetch_member(int(char.owner_id))
                    if member and member not in mentions:
                        mentions.append(member.mention)
                        users_requested.append(member.id)
                except discord.NotFound:
                    continue  # Member not found in guild
                except discord.HTTPException:
                    continue  # Network or API error
        mention_str = " ".join(mentions) if mentions else ""

        # Parse roll_parameters
        roll_parameters_dict = RollFormula.roll_parameters_to_dict(roll_parameters)
        roll_formula_obj = factories.get_specific_roll_formula(interaction.guild.id, system, roll_parameters_dict)

        view = RequestRollView(users_requested=users_requested, roll_formula=roll_formula_obj, difficulty=difficulty)
        await interaction.response.send_message(
            content=f"{mention_str}\n{interaction.user.display_name} requests a roll: `{roll_parameters}`",
            view=view
        )

async def setup_roll_commands(bot: commands.Bot):
    await bot.add_cog(RollCommands(bot))