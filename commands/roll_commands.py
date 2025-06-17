import discord
from discord.ext import commands
from discord import app_commands
from core.shared_views import RequestRollView
from core.utils import roll_parameters_to_dict
import core.factories as factories
from data import repo

async def skill_autocomplete(interaction: discord.Interaction, current: str):
    try:
        all_chars = repo.get_all_characters(interaction.guild.id)
        character = next((c for c in all_chars if not c.is_npc and str(c.owner_id) == str(interaction.user.id)), None)
        if not character:
            return []
        skills = character.skills
        options = [k for k in skills.keys() if current.lower() in k.lower()]
        return [app_commands.Choice(name=k, value=k) for k in options[:25]]
    except Exception as e:
        print("Autocomplete error:", e)
        return []

async def pc_name_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repo.get_all_characters(interaction.guild.id)
    pcs = [c for c in all_chars if not c.is_npc]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

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
    async def roll_check(self, interaction: discord.Interaction, roll_parameters: str = None, difficulty: int = None):
        character = repo.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.response.send_message("❌ No active character set or character not found.", ephemeral=True)
            return
        
        system = repo.get_system(interaction.guild.id)
        roll_parameters_dict = roll_parameters_to_dict(roll_parameters)
        roll_formula_obj = factories.get_specific_roll_formula(system, roll_parameters_dict)
        await character.send_roll_message(interaction, roll_formula_obj, difficulty)

    @roll_group.command(
        name="custom",
        description="Open the custom roll interface for your character"
    )
    async def roll_custom(self, interaction: discord.Interaction):
        """Open a fully interactive UI for rolling dice with your character"""
        character = repo.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.response.send_message("❌ No active character set. Use `/character switch` to choose one.", ephemeral=True)
            return
        
        system = repo.get_system(interaction.guild.id)
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
    async def roll_request(
        self,
        interaction: discord.Interaction,
        chars_to_roll: str,
        roll_parameters: str = None,
        difficulty: int = None
    ):
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ Only GMs can use this command.", ephemeral=True)
            return

        system = repo.get_system(interaction.guild.id)
        all_chars = repo.get_all_characters(interaction.guild.id, system=system)
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
        roll_parameters_dict = roll_parameters_to_dict(roll_parameters)
        roll_formula_obj = factories.get_specific_roll_formula(system, roll_parameters_dict)

        view = RequestRollView(roll_formula=roll_formula_obj, difficulty=difficulty)
        await interaction.response.send_message(
            content=f"{mention_str}\n{interaction.user.display_name} requests a roll: `{roll_parameters}`",
            view=view
        )

async def setup_roll_commands(bot: commands.Bot):
    await bot.add_cog(RollCommands(bot))