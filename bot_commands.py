import discord
from discord.ext import commands
from discord import app_commands
from data import repo
from character_sheets.base_sheet import get_pc_id, get_npc_id
import character_sheets.sheet_factory as sheet_factory
import json
import re
import random


async def skill_autocomplete(interaction: discord.Interaction, current: str):
    try:
        all_chars = repo.get_all_characters(interaction.guild.id)
        character = next((c for c in all_chars if not c.get("is_npc") and str(c.get("owner_id")) == str(interaction.user.id)), None)
        if not character:
            return []
        skills = character.get("skills", {})
        options = [k for k in skills.keys() if current.lower() in k.lower()]
        return [app_commands.Choice(name=k, value=k) for k in options[:25]]
    except Exception as e:
        print("Autocomplete error:", e)
        return []

async def attribute_autocomplete(interaction: discord.Interaction, current: str):
    # Get user's character
    all_chars = repo.get_all_characters(interaction.guild.id)
    character = next((c for c in all_chars if not c.get("is_npc") and str(c.get("owner_id")) == str(interaction.user.id)), None)
    if not character:
        return []
    attributes = character.get("attributes", {})
    options = [k for k in attributes.keys() if current.lower() in k.lower()]
    return [app_commands.Choice(name=k, value=k) for k in options[:25]]


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
        """Set the RPG system for this server. Example: !setsystem fate or !setsystem mgt2e"""
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

        # Fudge dice pattern
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

        # Standard dice pattern
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
        description="Roll dice for your system (Players only).",
        guild=discord.Object(id=1379609249834864721)
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
        sheet = sheet_factory.get_specific_sheet(system)
        all_chars = repo.get_all_characters(interaction.guild.id, system=system)
        is_gm = repo.is_gm(interaction.guild.id, interaction.user.id)

        # Only allow players to use this command
        if is_gm:
            await interaction.followup.send("❌ Only players can use this command.", ephemeral=True)
            return

        character = next((c for c in all_chars if not c.get("is_npc") and str(c.get("owner_id")) == str(interaction.user.id)), None)
        if not character:
            await interaction.followup.send("❌ Character not found.", ephemeral=True)
            return

        result = sheet.roll(character, skill=skill, attribute=attribute)
        await interaction.followup.send(result, ephemeral=True)


    @bot.command()
    async def createchar(ctx, name: str = None):
        system = repo.get_system(ctx.guild.id)
        sheet = sheet_factory.get_specific_sheet(system)

        char_name = name if name else f"{ctx.author.display_name}'s Character"
        char_id = get_pc_id(char_name)
        character = {
            "name": char_name,
            "owner_id": ctx.author.id,
            "is_npc": False,
            "notes": ""
        }
        sheet.apply_defaults(character, is_npc=False, guild_id=ctx.guild.id)
        repo.set_character(ctx.guild.id, char_id, character, system=system)
        await ctx.send(f'📝 Created {system.upper()} character for {ctx.author.display_name}.')


    @bot.command()
    async def createnpc(ctx, name: str):
        if not repo.is_gm(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Only GMs can create NPCs.")
            return
        
        system = repo.get_system(ctx.guild.id)
        sheet = sheet_factory.get_specific_sheet(system)

        npc_id = get_npc_id(name)
        character = {
            "name": name,
            "owner_id": ctx.author.id,
            "is_npc": True,
            "notes": ""
        }
        sheet.apply_defaults(character, is_npc=True, guild_id=ctx.guild.id)
        repo.set_npc(ctx.guild.id, npc_id, character, system=system)
        await ctx.send(f"🤖 Created NPC: **{name}**")


    @bot.command()
    async def sheet(ctx, char_name: str = None):
        system = repo.get_system(ctx.guild.id)
        sheet = sheet_factory.get_specific_sheet(system)

        if char_name is None:
            # Default to the user's own character
            char_name = f"{ctx.author.display_name}'s Character"
            char_id = get_pc_id(char_name)
        else:
            # If GM, allow viewing NPCs or any PC by name
            if repo.is_gm(ctx.guild.id, ctx.author.id):
                # Try NPC first
                npc_id = get_npc_id(char_name)
                npc = repo.get_character(ctx.guild.id, npc_id)
                if npc:
                    char_id = npc_id
                else:
                    char_id = get_pc_id(char_name)
            else:
                # Only allow viewing their own PC
                char_id = get_pc_id(f"{ctx.author.display_name}'s Character")
                if char_name and char_name.lower() != ctx.author.display_name.lower():
                    await ctx.send("❌ You can only view your own sheet.")
                    return

        character = repo.get_character(ctx.guild.id, char_id)
        if not character:
            await ctx.send("❌ Character not found.")
            return

        embed = sheet.format_full_sheet(character)
        await ctx.send(embed=embed)


    @bot.command()
    async def scene_add(ctx, *, name: str):
        if not repo.is_gm(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Only GMs can manage the scene.")
            return

        npc_id = f"npc:{name.lower().replace(' ', '_')}"
        npc = repo.get_character(ctx.guild.id, npc_id)
        if not npc:
            await ctx.send("❌ NPC not found. Did you create it with `!createnpc`?")
            return

        scene_npcs = repo.get_scenes(ctx.guild.id)
        if npc_id in scene_npcs:
            await ctx.send("⚠️ That NPC is already in the scene.")
            return

        repo.add_scene_npc(ctx.guild.id, npc_id)
        await ctx.send(f"✅ **{name}** added to the scene.")


    @bot.command()
    async def scene_remove(ctx, *, name: str):
        if not repo.is_gm(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Only GMs can manage the scene.")
            return

        npc_id = f"npc:{name.lower().replace(' ', '_')}"
        scene_npcs = repo.get_scenes(ctx.guild.id)
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
        sheet = sheet_factory.get_specific_sheet(system)

        npc_ids = repo.get_scenes(ctx.guild.id)
        if not npc_ids:
            await ctx.send("📭 No NPCs are currently in the scene.")
            return

        is_gm = repo.is_gm(ctx.guild.id, ctx.author.id)
        lines = []
        for npc_id in npc_ids:
            npc = repo.get_character(ctx.guild.id, npc_id)
            if npc:
                lines.append(sheet.format_npc_scene_entry(npc, is_gm))

        embed = discord.Embed(
            title="🎭 NPCs in the Scene",
            description="\n\n".join(lines),
            color=discord.Color.purple()
        )
        await ctx.send(embed=embed)


    @bot.tree.command(name="sheet", description="View a character or NPC's full sheet")
    @app_commands.describe(char_name="Leave blank to view your character, or enter an NPC name.")
    async def sheet(interaction: discord.Interaction, char_name: str = None):
        is_ephemeral = True

        if char_name:
            # Try NPC first
            npc_id = get_npc_id(char_name)
            npc = repo.get_character(interaction.guild.id, npc_id)
            if npc:
                char_id = npc_id
            else:
                char_id = get_pc_id(char_name)
        else:
            char_name = f"{interaction.user.display_name}'s Character"
            char_id = get_pc_id(char_name)

        system = repo.get_system(interaction.guild.id)
        sheet = sheet_factory.get_specific_sheet(system)
        sheet_view = sheet_factory.get_specific_sheet_view(system, interaction.user.id, char_id)

        character = repo.get_character(interaction.guild.id, char_id)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return

        # If it's an NPC, only GMs can view
        if character.get("is_npc"):
            if not repo.is_gm(interaction.guild.id, interaction.user.id):
                await interaction.response.send_message("❌ Only the GM can view NPCs.", ephemeral=True)
                return

        embed = sheet.format_full_sheet(character)
        await interaction.response.send_message(embed=embed, view=sheet_view, ephemeral=is_ephemeral)


    @bot.command()
    async def setdefaultskills(ctx, *, skills: str):
        """Set the default skills for this server's current system. Format: Skill1:0,Skill2:1,..."""
        if not repo.is_gm(ctx.guild.id, ctx.author.id):
            await ctx.send("❌ Only GMs can set default skills.")
            return

        system = repo.get_system(ctx.guild.id)
        sheet = sheet_factory.get_specific_sheet(system)

        # Defer parsing/validation to the system sheet
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
        """Slash command: Set default skills by uploading a .txt file."""
        await interaction.response.defer(ephemeral=True)

        # GM check
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

        # Parse lines: allow "Skill" or "Skill:Value" (default -3)
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

        # Defer to system sheet for validation
        system = repo.get_system(interaction.guild.id)
        sheet = sheet_factory.get_specific_sheet(system)
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

        # If no name is given, find the user's PC by owner_id
        if char_name is None:
            all_chars = repo.get_all_characters(interaction.guild.id, system=system)
            character = next((c for c in all_chars if not c.get("is_npc") and str(c.get("owner_id")) == str(interaction.user.id)), None)
            if not character:
                await interaction.followup.send("❌ You don't have a character to export.", ephemeral=True)
                return
            char_id = get_pc_id(character["name"])
        else:
            # If GM, allow exporting NPCs or any PC by name
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
                # Only allow exporting their own PC
                if character and str(character.get("owner_id")) != str(interaction.user.id):
                    await interaction.followup.send("❌ You can only export your own character.", ephemeral=True)
                    return

        if not character:
            await interaction.followup.send("❌ Character not found.", ephemeral=True)
            return

        # Only allow exporting NPCs if GM
        if character.get("is_npc") and not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.followup.send("❌ Only the GM can export NPCs.", ephemeral=True)
            return

        export_data = character.copy()
        export_data["system"] = system

        import io, json
        file_content = json.dumps(export_data, indent=2)
        file = discord.File(io.BytesIO(file_content.encode('utf-8')), filename=f"{character['name']}.json")
        await interaction.followup.send(f"Here is your exported character `{character['name']}`.", file=file, ephemeral=True)


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

        data["owner_id"] = interaction.user.id
        name = data.get("name", f"{interaction.user.display_name}'s Character")
        is_npc = data.get("is_npc", False)
        if is_npc:
            if not repo.is_gm(interaction.guild.id, interaction.user.id):
                await interaction.followup.send("❌ Only GMs can import NPCs.", ephemeral=True)
                return
            char_id = get_npc_id(name)
        else:
            char_id = get_pc_id(name)

        system = repo.get_system(interaction.guild.id)
        sheet = sheet_factory.get_specific_sheet(system)
        sheet.apply_defaults(data, is_npc=is_npc, guild_id=interaction.guild.id)

        if is_npc:
            repo.set_npc(interaction.guild.id, char_id, data, system=system)
        else:
            repo.set_character(interaction.guild.id, char_id, data, system=system)

        await interaction.followup.send(f"✅ Imported {'NPC' if is_npc else 'character'} `{name}`.", ephemeral=True)