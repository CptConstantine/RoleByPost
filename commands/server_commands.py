import discord
from discord.ext import commands
from discord import app_commands
from data import repo
import core.factories as factories
import re
import random
import asyncio
import datetime

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

def setup_server_commands(bot: commands.Bot):
    @bot.command()
    async def myguild(ctx):
        await ctx.send(f"This server's guild_id is {ctx.guild.id}")

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setgm(ctx):
        repo.set_gm(ctx.guild.id, ctx.author.id)
        await ctx.send(f"✅ {ctx.author.display_name} is now a GM.")

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setsystem(ctx, system: str):
        valid_systems = ["generic", "fate", "mgt2e"]
        system = system.lower()
        if system not in valid_systems:
            await ctx.send(f"❌ Invalid system. Valid options: {', '.join(valid_systems)}")
            return
        repo.set_system(ctx.guild.id, system)
        await ctx.send(f"✅ System set to {system.upper()} for this server.")

    @bot.command()
    async def setdefaultskills(ctx, *, skills: str):
        if not repo.is_gm(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Only GMs can set default skills.")
            return
        system = repo.get_system(ctx.guild.id)
        sheet = factories.get_specific_sheet(system)
        if not hasattr(sheet, "parse_and_validate_skills"):
            await ctx.send("❌ This system does not support setting default skills.")
            return
        skills_dict = sheet.parse_and_validate_skills(skills)
        if not skills_dict:
            await ctx.send("❌ Invalid format or no skills provided. Example: `Admin:0, Gun Combat:1, Pilot:2`")
            return
        repo.set_default_skills(ctx.guild.id, system, skills_dict)
        await ctx.send(f"✅ Default skills for {system.upper()} updated for this server.")

    @bot.tree.command(name="setdefaultskillsfile", description="Set default skills for this server's system with a .txt file (one skill per line).")
    @app_commands.describe(file="A .txt file with skills, one per line or Skill:Value per line")
    async def setdefaultskillsfile(interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.followup.send("❌ Only GMs can set default skills.", ephemeral=True)
            return
        if not file.filename.endswith('.txt'):
            await interaction.followup.send("❌ Only .txt files are supported.", ephemeral=True)
            return
        try:
            file_bytes = await file.read()
            content = file_bytes.decode('utf-8')
        except Exception:
            await interaction.followup.send("❌ Could not decode file. Please ensure it's a UTF-8 encoded .txt file.", ephemeral=True)
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
                    await interaction.followup.send(f"❌ Invalid value for skill: `{line}`. All values must be integers.", ephemeral=True)
                    return
            else:
                skills_dict[line] = -3
        if not skills_dict:
            await interaction.followup.send("❌ No skills found in the file.", ephemeral=True)
            return
        system = repo.get_system(interaction.guild.id)
        sheet = factories.get_specific_sheet(system)
        if hasattr(sheet, "parse_and_validate_skills"):
            skills_str = ", ".join(f"{k}:{v}" for k, v in skills_dict.items())
            skills_dict = sheet.parse_and_validate_skills(skills_str)
            if not skills_dict:
                await interaction.followup.send("❌ The skills list is invalid for this system.", ephemeral=True)
                return
        repo.set_default_skills(interaction.guild.id, system, skills_dict)
        await interaction.followup.send(f"✅ Default skills for {system.upper()} updated from file.", ephemeral=True)

    @bot.tree.command(name="remind", description="GM: Remind a player or a role to post.")
    @app_commands.describe(
        user="Select a user to remind",
        role="Optionally select a role to remind all its members",
        message="Optional custom reminder message",
        delay="How long to wait before DMing (e.g. '24h', '2d', '90m'). Default: 24h"
    )
    async def remind(
        interaction: discord.Interaction,
        user: discord.Member = None,
        role: discord.Role = None,
        message: str = "Please remember to post your actions!",
        delay: str = "24h"
    ):
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ Only GMs can send reminders.", ephemeral=True)
            return
        targets = set()
        if user:
            targets.add(user)
        if role:
            targets.update(role.members)
        if not targets:
            await interaction.response.send_message("❌ Please specify at least one user or role to remind.", ephemeral=True)
            return
        delay_seconds = 86400
        match = re.fullmatch(r"(\d+)([dhm]?)", delay.strip().lower())
        if match:
            num = int(match.group(1))
            unit = match.group(2)
            if unit == "d":
                delay_seconds = num * 86400
            elif unit == "h":
                delay_seconds = num * 3600
            elif unit == "m":
                delay_seconds = num * 60
            else:
                delay_seconds = num
        else:
            await interaction.response.send_message("❌ Invalid delay format. Use like '24h', '2d', or '90m'.", ephemeral=True)
            return
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        for user in targets:
            repo.set_reminder_time(interaction.guild.id, user.id, now)
            bot.loop.create_task(schedule_dm_reminder(interaction.guild.id, user, message, now, delay_seconds))
        await interaction.response.send_message(f"⏰ Reminder scheduled for {delay}.", ephemeral=True)

    async def schedule_dm_reminder(guild_id, user, message, reminder_time, delay_seconds):
        await asyncio.sleep(delay_seconds)
        last_msg = repo.get_last_message_time(guild_id, user.id)
        if not last_msg or last_msg < reminder_time:
            try:
                await user.send(message)
            except Exception:
                pass  # Can't DM user

    @bot.command()
    async def roll(ctx, *, arg):
        arg = arg.replace(" ", "").lower()
        fudge_pattern = r'(\d*)d[fF]([+-]\d+)?'
        fudge_match = re.fullmatch(fudge_pattern, arg)
        if fudge_match:
            num_dice = int(fudge_match.group(1)) if fudge_match.group(1) else 4
            modifier = int(fudge_match.group(2)) if fudge_match.group(2) else 0
            rolls = [random.choice([-1, 0, 1]) for _ in range(num_dice)]
            symbols = ['+' if r == 1 else '-' if r == -1 else '0' for r in rolls]
            total = sum(rolls) + modifier
            response = f'🎲 Fudge Rolls: `{" ".join(symbols)}`'
            if modifier:
                response += f' {"+" if modifier > 0 else ""}{modifier}'
            response += f'\n🧮 Total: {total}'
            await ctx.send(response)
            return
        pattern = r'(\d*)d(\d+)([+-]\d+)?'
        match = re.fullmatch(pattern, arg)
        if match:
            num_dice = int(match.group(1)) if match.group(1) else 1
            die_size = int(match.group(2))
            modifier = int(match.group(3)) if match.group(3) else 0
            if num_dice > 100 or die_size > 1000:
                await ctx.send("😵 That's a lot of dice. Try fewer.")
                return
            rolls = [random.randint(1, die_size) for _ in range(num_dice)]
            total = sum(rolls) + modifier
            response = f'🎲 Rolled: {rolls}'
            if modifier:
                response += f' {"+" if modifier > 0 else ""}{modifier}'
            response += f'\n🧮 Total: {total}'
            await ctx.send(response)
            return
        await ctx.send("❌ Invalid format. Use like `2d6+3` or `4df+1`.")

    @bot.tree.command(
        name="roll",
        description="Roll dice for your system (Players only)."
    )
    @app_commands.describe(
        skill="Skill name (optional)",
        attribute="Attribute name (optional)"
    )
    @app_commands.autocomplete(
        skill=skill_autocomplete,
        attribute=attribute_autocomplete
    )
    async def roll(
        interaction: discord.Interaction,
        skill: str = None,
        attribute: str = None
    ):
        await interaction.response.defer(ephemeral=True)
        system = repo.get_system(interaction.guild.id)
        sheet = factories.get_specific_sheet(system)
        character = repo.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.followup.send("❌ No active character set or character not found.", ephemeral=True)
            return
        result = sheet.roll(character, skill=skill, attribute=attribute)
        await interaction.followup.send(result, ephemeral=True)