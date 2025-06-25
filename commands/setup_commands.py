import re
import asyncio
import datetime
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

async def attribute_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repo.get_all_characters(interaction.guild.id)
    character = next((c for c in all_chars if not c.is_npc and str(c.owner_id) == str(interaction.user.id)), None)
    if not character:
        return []
    attributes = character.attributes
    options = [k for k in attributes.keys() if current.lower() in k.lower()]
    return [app_commands.Choice(name=k, value=k) for k in options[:25]]

class SetupCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    setup_group = app_commands.Group(name="setup", description="Server setup commands")

    @setup_group.command(
        name="gmrole",
        description="Set a Discord role as the GM role for the server. You must be an Admin."
    )
    @app_commands.describe(role="The Discord role to set as the GM role")
    async def setup_gmrole(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only admins can set the GM role.", ephemeral=True)
            return
        
        repo.set_gm_role(interaction.guild.id, role.id)
        
        await interaction.response.send_message(
            f"✅ Set role `{role.name}` as the GM role. Members with this role now have GM permissions.",
            ephemeral=True
        )

    @setup_group.command(
        name="playerrole",
        description="Set a Discord role as the player role for the server. You must be an Admin."
    )
    @app_commands.describe(role="The Discord role to set as the player role")
    async def setup_playerrole(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only admins can set the player role.", ephemeral=True)
            return
        
        repo.set_player_role(interaction.guild.id, role.id)
        
        await interaction.response.send_message(
            f"✅ Set role `{role.name}` as the player role. Members with this role now have player permissions.",
            ephemeral=True
        )

    @setup_group.command(name="system", description="Set the RPG system for your server. You must be an Admin.")
    @app_commands.describe(system="The system to use (e.g. generic, fate, mgt2e)")
    async def setup_system(self, interaction: discord.Interaction, system: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only admins can set the system.", ephemeral=True)
            return
        valid_systems = ["generic", "fate", "mgt2e"]
        system = system.lower()
        if system not in valid_systems:
            await interaction.response.send_message(f"❌ Invalid system. Valid options: {', '.join(valid_systems)}", ephemeral=True)
            return
        repo.set_system(interaction.guild.id, system)
        await interaction.response.send_message(f"✅ System set to {system.upper()} for this server.", ephemeral=True)

    @setup_group.command(name="defaultskillsfile", description="Set default skills for this server's system with a .txt file (one skill per line).")
    @app_commands.describe(file="A .txt file with skills, one per line or Skill:Value per line")
    async def setup_defaultskillsfile(self, interaction: discord.Interaction, file: discord.Attachment):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can set default skills.", ephemeral=True)
            return
        if not file.filename.endswith('.txt'):
            await interaction.response.send_message("❌ Only .txt files are supported.", ephemeral=True)
            return
        try:
            file_bytes = await file.read()
            content = file_bytes.decode('utf-8')
        except Exception:
            await interaction.response.send_message("❌ Could not decode file. Please ensure it's a UTF-8 encoded .txt file.", ephemeral=True)
            return
        skills_dict = {}
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                k, v = line.split(':', 1)
                try:
                    skills_dict[k.strip()] = int(v.strip())
                except ValueError:
                    await interaction.response.send_message(f"❌ Invalid value for skill: `{line}`. All values must be integers.", ephemeral=True)
                    return
            else:
                skills_dict[line] = -3
        if not skills_dict:
            await interaction.response.send_message("❌ No skills found in the file.", ephemeral=True)
            return
        system = repo.get_system(interaction.guild.id)
        sheet = factories.get_specific_sheet(system)
        if hasattr(sheet, "parse_and_validate_skills"):
            skills_str = ", ".join(f"{k}:{v}" for k, v in skills_dict.items())
            skills_dict = sheet.parse_and_validate_skills(skills_str)
            if not skills_dict:
                await interaction.response.send_message("❌ The skills list is invalid for this system.", ephemeral=True)
                return
        repo.set_default_skills(interaction.guild.id, system, skills_dict)
        await interaction.response.send_message(f"✅ Default skills for {system.upper()} updated from file.", ephemeral=True)

    @setup_group.command(name="defaultskills", description="Set default skills for this server's system via text.")
    @app_commands.describe(skills="Skill list, e.g. Admin:0, Gun Combat:1, Pilot:2")
    async def setup_defaultskills(self, interaction: discord.Interaction, skills: str):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can set default skills.", ephemeral=True)
            return
        system = repo.get_system(interaction.guild.id)
        sheet = factories.get_specific_sheet(system)
        if not hasattr(sheet, "parse_and_validate_skills"):
            await interaction.response.send_message("❌ This system does not support setting default skills.", ephemeral=True)
            return
        skills_dict = sheet.parse_and_validate_skills(skills)
        if not skills_dict:
            await interaction.response.send_message("❌ Invalid format or no skills provided. Example: `Admin:0, Gun Combat:1, Pilot:2`", ephemeral=True)
            return
        repo.set_default_skills(interaction.guild.id, system, skills_dict)
        await interaction.response.send_message(f"✅ Default skills for {system.upper()} updated for this server.", ephemeral=True)

async def setup_setup_commands(bot: commands.Bot):
    await bot.add_cog(SetupCommands(bot))