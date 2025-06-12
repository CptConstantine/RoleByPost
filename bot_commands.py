import discord
from discord.ext import commands
from discord import app_commands
from core import shared_views
from data import repo
from core.abstract_models import get_pc_id, get_npc_id
import core.system_factory as system_factory
import json
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

async def pc_name_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repo.get_all_characters(interaction.guild.id)
    pcs = [
        c for c in all_chars
        if not c.is_npc and str(c.owner_id) == str(interaction.user.id)
    ]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def pc_name_gm_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repo.get_all_characters(interaction.guild.id)
    pcs = [c for c in all_chars if not c.is_npc]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def npc_name_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repo.get_all_characters(interaction.guild.id)
    scene_npcs = set(repo.get_scene_npcs(interaction.guild.id))
    npcs = [
        c for c in all_chars
        if c.is_npc and get_npc_id(c.name) not in scene_npcs and current.lower() in c.name.lower()
    ]
    options = [c.name for c in npcs]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

def setup(bot):
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
        valid_systems = ["fate", "mgt2e"]
        system = system.lower()
        if system not in valid_systems:
            await ctx.send(f"❌ Invalid system. Valid options: {', '.join(valid_systems)}")
            return
        repo.set_system(ctx.guild.id, system)
        await ctx.send(f"✅ System set to {system.upper()} for this server.")

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
        sheet = system_factory.get_specific_sheet(system)
        char_id = repo.get_active_character_id(interaction.guild.id, interaction.user.id)
        character = repo.get_character(interaction.guild.id, char_id) if char_id else None
        if not character:
            await interaction.followup.send("❌ No active character set or character not found.", ephemeral=True)
            return
        result = sheet.roll(character, skill=skill, attribute=attribute)
        await interaction.followup.send(result, ephemeral=True)

    @bot.tree.command(name="createchar", description="Create a new character (PC) with a required name.")
    @app_commands.describe(char_name="The name of your new character")
    async def createchar(interaction: discord.Interaction, char_name: str):
        await interaction.response.defer(ephemeral=True)
        system = repo.get_system(interaction.guild.id)
        CharacterClass = system_factory.get_specific_character(system)
        char_id = get_pc_id(char_name)
        existing = repo.get_character(interaction.guild.id, char_id)
        if existing:
            await interaction.followup.send(f"❌ A character named `{char_name}` already exists.", ephemeral=True)
            return
        # Create a new Character instance and apply defaults using the Character method
        character = CharacterClass({
            "id": char_id,
            "name": char_name,
            "owner_id": interaction.user.id,
            "is_npc": False,
            "notes": []
        })
        character.apply_defaults(is_npc=False, guild_id=interaction.guild.id)
        repo.set_character(interaction.guild.id, character, system=system)
        if not repo.get_active_character_id(interaction.guild.id, interaction.user.id):
            repo.set_active_character(interaction.guild.id, interaction.user.id, char_id)
        await interaction.followup.send(f'📝 Created {system.upper()} character: **{char_name}**.', ephemeral=True)

    @bot.tree.command(name="createnpc", description="GM: Create a new NPC with a required name.")
    @app_commands.describe(npc_name="The name of the new NPC")
    async def createnpc(interaction: discord.Interaction, npc_name: str):
        await interaction.response.defer(ephemeral=True)
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.followup.send("❌ Only GMs can create NPCs.", ephemeral=True)
            return
        system = repo.get_system(interaction.guild.id)
        CharacterClass = system_factory.get_specific_character(system)
        npc_id = get_npc_id(npc_name)
        existing = repo.get_character(interaction.guild.id, npc_id)
        if existing:
            await interaction.followup.send(f"❌ An NPC named `{npc_name}` already exists.", ephemeral=True)
            return
        # Create a new Character instance and apply defaults using the Character method
        character = CharacterClass({
            "id": npc_id,
            "name": npc_name,
            "owner_id": interaction.user.id,
            "is_npc": True,
            "notes": []
        })
        character.apply_defaults(is_npc=True, guild_id=interaction.guild.id)
        repo.set_character(interaction.guild.id, character, system=system)
        await interaction.followup.send(f"🤖 Created NPC: **{npc_name}**", ephemeral=True)

    @bot.command()
    async def sheet(ctx, char_name: str = None):
        system = repo.get_system(ctx.guild.id)
        sheet = system_factory.get_specific_sheet(system)
        if char_name is None:
            char_id = repo.get_active_character_id(ctx.guild.id, ctx.author.id)
            if not char_id:
                await ctx.send("❌ No active character set. Use /setactive to choose one.")
                return
        else:
            if repo.is_gm(ctx.guild.id, ctx.author.id):
                npc_id = get_npc_id(char_name)
                npc = repo.get_character(ctx.guild.id, npc_id)
                if npc:
                    char_id = npc_id
                else:
                    char_id = get_pc_id(char_name)
            else:
                char_id = get_pc_id(char_name)
        character = repo.get_character(ctx.guild.id, char_id)
        if not character:
            await ctx.send("❌ Character not found.")
            return
        embed = sheet.format_full_sheet(character)
        await ctx.send(embed=embed, ephemeral=True)

    @bot.tree.command(name="sheet", description="View a character or NPC's full sheet")
    @app_commands.describe(char_name="Leave blank to view your character, or enter an NPC name.")
    async def sheet(interaction: discord.Interaction, char_name: str = None):
        is_ephemeral = True
        if char_name:
            npc_id = get_npc_id(char_name)
            npc = repo.get_character(interaction.guild.id, npc_id)
            if npc:
                char_id = npc_id
            else:
                char_id = get_pc_id(char_name)
        else:
            char_id = repo.get_active_character_id(interaction.guild.id, interaction.user.id)
            if not char_id:
                await interaction.response.send_message("❌ No active character set. Use /setactive to choose one.", ephemeral=True)
                return
        system = repo.get_system(interaction.guild.id)
        sheet_obj = system_factory.get_specific_sheet(system)
        sheet_view = system_factory.get_specific_sheet_view(system, interaction.user.id, char_id)
        character = repo.get_character(interaction.guild.id, char_id)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return
        if character.is_npc:
            if not repo.is_gm(interaction.guild.id, interaction.user.id):
                await interaction.response.send_message("❌ Only the GM can view NPCs.", ephemeral=True)
                return
        embed = sheet_obj.format_full_sheet(character)
        await interaction.response.send_message(embed=embed, view=sheet_view, ephemeral=is_ephemeral)

    @bot.tree.command(name="scene_add", description="Add an NPC to the current scene.")
    @app_commands.describe(npc_name="The name of the NPC to add to the scene")
    @app_commands.autocomplete(npc_name=npc_name_autocomplete)
    async def scene_add(interaction: discord.Interaction, npc_name: str):
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ Only GMs can manage the scene.", ephemeral=True)
            return
        npc_id = get_npc_id(npc_name)
        npc = repo.get_character(interaction.guild.id, npc_id)
        if not npc:
            await interaction.response.send_message("❌ NPC not found. Did you create it with `/createnpc`?", ephemeral=True)
            return
        scene_npcs = repo.get_scene_npcs(interaction.guild.id)
        if npc_id in scene_npcs:
            await interaction.response.send_message("⚠️ That NPC is already in the scene.", ephemeral=True)
            return
        repo.add_scene_npc(interaction.guild.id, npc_id)
        await interaction.response.send_message(f"✅ **{npc_name}** added to the scene.", ephemeral=True)

    @bot.command()
    async def scene_remove(ctx, *, name: str):
        if not repo.is_gm(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Only GMs can manage the scene.")
            return
        npc_id = get_npc_id(name)
        scene_npcs = repo.get_scene_npcs(ctx.guild.id)
        if npc_id not in scene_npcs:
            await ctx.send("❌ That NPC isn't in the scene.")
            return
        repo.remove_scene_npc(ctx.guild.id, npc_id)
        await ctx.send(f"🗑️ **{name}** removed from the scene.")

    @bot.command()
    async def scene_clear(ctx):
        if not repo.is_gm(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Only GMs can manage the scene.")
            return
        repo.clear_scenes(ctx.guild.id)
        await ctx.send("🧹 Scene NPC list cleared.")

    @bot.command()
    async def scene(ctx):
        system = repo.get_system(ctx.guild.id)
        sheet = system_factory.get_specific_sheet(system)
        npc_ids = repo.get_scene_npcs(ctx.guild.id)
        is_gm = repo.is_gm(ctx.guild.id, ctx.author.id)
        lines = []
        for npc_id in npc_ids:
            npc = repo.get_character(ctx.guild.id, npc_id)
            if npc:
                lines.append(sheet.format_npc_scene_entry(npc, is_gm))
        notes = repo.get_scene_notes(ctx.guild.id)
        description = ""
        if notes:
            description += f"**Notes:**\n{notes}\n\n"
        if lines:
            description += "\n\n".join(lines)
        else:
            description += "📭 No NPCs are currently in the scene."
        embed = discord.Embed(
            title="🎭 The Current Scene",
            description=description,
            color=discord.Color.purple()
        )
        view = shared_views.SceneNotesEditView(ctx.guild.id, is_gm)
        await ctx.send(embed=embed, view=view)

    @bot.command()
    async def setdefaultskills(ctx, *, skills: str):
        if not repo.is_gm(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Only GMs can set default skills.")
            return
        system = repo.get_system(ctx.guild.id)
        sheet = system_factory.get_specific_sheet(system)
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
        sheet = system_factory.get_specific_sheet(system)
        if hasattr(sheet, "parse_and_validate_skills"):
            skills_str = ", ".join(f"{k}:{v}" for k, v in skills_dict.items())
            skills_dict = sheet.parse_and_validate_skills(skills_str)
            if not skills_dict:
                await interaction.followup.send("❌ The skills list is invalid for this system.", ephemeral=True)
                return
        repo.set_default_skills(interaction.guild.id, system, skills_dict)
        await interaction.followup.send(f"✅ Default skills for {system.upper()} updated from file.", ephemeral=True)

    @bot.tree.command(name="exportchar", description="Export your character or an NPC (if GM) as a JSON file.")
    @app_commands.describe(char_name="Leave blank to export your character, or enter an NPC name.")
    async def exportchar(interaction: discord.Interaction, char_name: str = None):
        await interaction.response.defer(ephemeral=True)
        system = repo.get_system(interaction.guild.id)
        if char_name is None:
            all_chars = repo.get_all_characters(interaction.guild.id, system=system)
            character = next((c for c in all_chars if not c.is_npc and str(c.owner_id) == str(interaction.user.id)), None)
            if not character:
                await interaction.followup.send("❌ You don't have a character to export.", ephemeral=True)
                return
            char_id = get_pc_id(character.name)
        else:
            if repo.is_gm(interaction.guild.id, interaction.user.id):
                npc_id = get_npc_id(char_name)
                npc = repo.get_character(interaction.guild.id, npc_id)
                if npc:
                    character = npc
                    char_id = npc_id
                else:
                    char_id = get_pc_id(char_name)
                    character = repo.get_character(interaction.guild.id, char_id)
            else:
                char_id = get_pc_id(char_name)
                character = repo.get_character(interaction.guild.id, char_id)
                if character and str(character.owner_id) != str(interaction.user.id):
                    await interaction.followup.send("❌ You can only export your own character.", ephemeral=True)
                    return
        if not character:
            await interaction.followup.send("❌ Character not found.", ephemeral=True)
            return
        if character.is_npc and not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.followup.send("❌ Only the GM can export NPCs.", ephemeral=True)
            return
        export_data = character.data
        export_data["system"] = system
        import io
        file_content = json.dumps(export_data, indent=2)
        file = discord.File(io.BytesIO(file_content.encode('utf-8')), filename=f"{character.name}.json")
        await interaction.followup.send(f"Here is your exported character `{character.name}`.", file=file, ephemeral=True)

    @bot.tree.command(name="importchar", description="Import a character or NPC from a JSON file. The owner will be set to you.")
    @app_commands.describe(file="A .json file exported from this bot")
    async def importchar(interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        if not file.filename.endswith('.json'):
            await interaction.followup.send("❌ Only .json files are supported.", ephemeral=True)
            return
        try:
            file_bytes = await file.read()
            data = json.loads(file_bytes.decode('utf-8'))
        except Exception:
            await interaction.followup.send("❌ Could not decode or parse the file. Make sure it's a valid JSON export from this bot.", ephemeral=True)
            return
        system = repo.get_system(interaction.guild.id)
        CharacterClass = system_factory.get_specific_character(system)
        character = CharacterClass.from_dict(data)
        character.apply_defaults(is_npc=character.is_npc, guild_id=interaction.guild.id)
        repo.set_character(interaction.guild.id, character, system=system)
        await interaction.followup.send(f"✅ Imported {'NPC' if character.is_npc else 'character'} `{character.name}`.", ephemeral=True)

    @bot.tree.command(name="transferchar", description="GM: Transfer a PC to another player.")
    @app_commands.describe(
        char_name="Name of the character to transfer",
        new_owner="The user to transfer ownership to"
    )
    @app_commands.autocomplete(char_name=pc_name_gm_autocomplete)
    async def transferchar(interaction: discord.Interaction, char_name: str, new_owner: discord.Member):
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ Only GMs can transfer characters.", ephemeral=True)
            return
        char_id = get_pc_id(char_name)
        character = repo.get_character(interaction.guild.id, char_id)
        if not character or character.is_npc:
            await interaction.response.send_message("❌ PC not found.", ephemeral=True)
            return
        character.owner_id = new_owner.id
        system = repo.get_system(interaction.guild.id)
        repo.set_character(interaction.guild.id, character, system=system)
        await interaction.response.send_message(
            f"✅ Ownership of `{char_name}` transferred to {new_owner.display_name}.", ephemeral=True
        )

    @bot.tree.command(name="setactive", description="Set your active character (PC) for this server.")
    @app_commands.describe(char_name="The name of your character to set as active")
    @app_commands.autocomplete(char_name=pc_name_autocomplete)
    async def setactive(interaction: discord.Interaction, char_name: str):
        all_chars = repo.get_all_characters(interaction.guild.id)
        character = next(
            (c for c in all_chars if not c.is_npc and str(c.owner_id) == str(interaction.user.id) and c.name.lower() == char_name.lower()),
            None
        )
        if not character:
            await interaction.response.send_message(f"❌ You don't have a character named `{char_name}`.", ephemeral=True)
            return
        char_id = get_pc_id(char_name)
        repo.set_active_character(interaction.guild.id, interaction.user.id, char_id)
        await interaction.response.send_message(f"✅ `{char_name}` is now your active character.", ephemeral=True)

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