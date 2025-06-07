import re
import random
import discord
from data import repo
from character_sheets import sheet_utils, sheet_views
from discord.ext import commands
from discord.ui import View, Button
from discord import app_commands
from dotenv import load_dotenv
import os
import logging


load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def setup_hook():
    await bot.tree.sync()


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')


@bot.command()
async def myguild(ctx):
    await ctx.send(f"This server's guild_id is {ctx.guild.id}")


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


@bot.command()
async def createchar(ctx, name: str = None):
    character = {
        "name": name if name else f"{ctx.author.display_name}'s Character",
        "skills": {},
        "fate_points": 3,
        "is_npc": False,
        "owner_id": ctx.author.id,
        "aspects": [],
        "hidden_aspects": [],
        "stress": {
            "physical": [False, False, False],
            "mental": [False, False]
        },
        "consequences": ["Mild: None", "Moderate: None", "Severe: None"]
    }
    repo.set_character(ctx.guild.id, ctx.author.id, character, system="fate")
    await ctx.send(f'📝 Created character for {ctx.author.display_name}.')


@bot.command()
async def createnpc(ctx, name: str):
    if not repo.is_gm(ctx.guild.id, ctx.author.id):
        await ctx.send("❌ Only GMs can create NPCs.")
        return

    npc_id = f"npc:{name.lower().replace(' ', '_')}"
    character = {
        "name": name,
        "skills": {},
        "fate_points": 3,
        "is_npc": True,
        "owner_id": ctx.author.id,
        "aspects": [],
        "hidden_aspects": [],
        "stress": {
            "physical": [False, False, False],
            "mental": [False, False]
        },
        "consequences": ["Mild: None"]
    }
    repo.set_npc(ctx.guild.id, npc_id, character, system="fate")
    await ctx.send(f"🤖 Created NPC: **{name}**")


@bot.command()
async def sheet(ctx, char_name: str = None):
    if char_name is None:
        char_id = str(ctx.author.id)
    else:
        if repo.is_gm(ctx.guild.id, ctx.author.id):
            char_id = f"npc:{char_name.lower().replace(' ', '_')}"
        else:
            await ctx.send("❌ You can only view your own sheet.")
            return

    character = repo.get_character(ctx.guild.id, char_id)
    if not character:
        await ctx.send("❌ Character not found.")
        return

    embed = sheet_utils.format_full_sheet(character["name"], character)
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def setgm(ctx):
    repo.set_gm(ctx.guild.id, ctx.author.id)
    await ctx.send(f"✅ {ctx.author.display_name} is now a GM.")


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
    npc_ids = repo.get_scenes(ctx.guild.id)
    if not npc_ids:
        await ctx.send("📭 No NPCs are currently in the scene.")
        return

    is_gm = repo.is_gm(ctx.guild.id, ctx.author.id)
    lines = []
    for npc_id in npc_ids:
        npc = repo.get_character(ctx.guild.id, npc_id)
        if npc:
            aspects = npc.get("aspects", [])
            hidden = npc.get("hidden_aspects", [])
            aspect_lines = []
            for idx, aspect in enumerate(aspects):
                if idx in hidden:
                    if is_gm:
                        aspect_lines.append(f"*{aspect}*")
                    else:
                        aspect_lines.append("*hidden*")
                else:
                    aspect_lines.append(aspect)
            aspect_str = "\n".join(aspect_lines) if aspect_lines else "_No aspects set_"
            lines.append(f"**{npc['name']}**\n{aspect_str}")

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
    view = None

    if char_name:  # Try to fetch as NPC
        char_id = f"npc:{char_name.lower().replace(' ', '_')}"
    else:  # Player character
        char_id = str(interaction.user.id)

    character = repo.get_character(interaction.guild.id, char_id)
    if not character:
        await interaction.response.send_message("❌ Character not found.", ephemeral=True)
        return

    # If it's an NPC, only GMs can view
    if character.get("is_npc"):
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ Only the GM can view NPCs.", ephemeral=True)
            return

    embed = sheet_utils.format_full_sheet(character["name"], character)
    # Optionally, you can add a view here if you have a DB-compatible SheetEditView
    await interaction.response.send_message(embed=embed, view=view, ephemeral=is_ephemeral)


handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')

bot.run(os.getenv("DISCORD_BOT_TOKEN"), log_handler=handler, log_level=logging.DEBUG)