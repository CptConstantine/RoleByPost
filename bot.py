import re
import random
import discord
from character_sheets import sheet_utils, sheet_views
from discord.ext import commands
from discord.ui import View, Button
from discord import app_commands
from dotenv import load_dotenv
import os

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
async def roll(ctx, *, arg):
    """
    Rolls standard dice (e.g. 2d6+1) or Fudge dice (e.g. 4df).
    """
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


class CharacterView(View):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.add_item(Button(label="Roll Athletics", style=discord.ButtonStyle.primary, custom_id="roll_athletics"))
        self.add_item(Button(label="Cheat Fate (+2)", style=discord.ButtonStyle.danger, custom_id="cheat_fate"))


@bot.command()
async def createchar(ctx):
    character = {
        "name": "default name",
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
    sheet_utils.set_character(ctx.author.id, character)
    await ctx.send(f'📝 Created character for {ctx.author.display_name}.')


@bot.command()
async def createnpc(ctx, name: str):
    if not sheet_utils.is_gm(ctx.author.id):
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
    sheet_utils.set_npc(npc_id, character)
    await ctx.send(f"🤖 Created NPC: **{name}**")


@bot.command()
async def sheet(ctx, char_name: str = None):
    if char_name is None:
        char_id = str(ctx.author.id)
    else:
        if sheet_utils.is_gm(ctx.author.id):
            char_id = f"npc:{char_name.lower().replace(' ', '_')}"
        else:
            await ctx.send("❌ You can only view your own sheet.")
            return

    character = sheet_utils.get_character(char_id)
    if not character:
        await ctx.send("❌ Character not found.")
        return

    aspects = character["aspects"]
    hidden_aspects = character["hidden_aspects"]
    aspect_lines = []
    if aspects:
        for idx, aspect in enumerate(aspects):
            if idx in hidden_aspects:
                aspect_lines.append(f"*{aspect}*")
            else:
                aspect_lines.append(f"{aspect}")

    consequences = character["consequences"]
    stress = character["stress"]

    stress_lines = [
        f"**Physical Stress**: {' '.join('[☒]' if x else '[☐]' for x in stress['physical'])}",
        f"**Mental Stress**: {' '.join('[☒]' if x else '[☐]' for x in stress['mental'])}"
    ]

    conseq_lines = consequences

    embed = discord.Embed(title=f"{character['name']}'s Sheet")
    embed.add_field(name="Aspects", value="\n".join(aspect_lines), inline=False)
    embed.add_field(name="Stress", value="\n".join(stress_lines), inline=False)
    embed.add_field(name="Consequences", value="\n".join(conseq_lines), inline=False)

    await ctx.send(embed=embed)


@bot.command()
@commands.is_owner()
async def setgm(ctx):
    sheet_utils.set_gm(ctx.author.id)
    await ctx.send(f"✅ {ctx.author.display_name} is now a GM.")


@bot.command()
async def scene_add(ctx, *, name: str):
    if not sheet_utils.is_gm(ctx.author.id):
        await ctx.send("❌ Only GMs can manage the scene.")
        return

    npc_id = f"npc:{name.lower().replace(' ', '_')}"
    char_data = sheet_utils.load_character_data()
    scene_data = sheet_utils.load_scene_data()

    if npc_id not in char_data["npcs"]:
        await ctx.send("❌ NPC not found. Did you create it with `!createnpc`?")
        return

    if npc_id in scene_data["current_scene"]["npc_ids"]:
        await ctx.send("⚠️ That NPC is already in the scene.")
        return

    scene_data["current_scene"]["npc_ids"].append(npc_id)
    sheet_utils.save_scene_data(scene_data)
    await ctx.send(f"✅ **{name}** added to the scene.")


@bot.command()
async def scene_remove(ctx, *, name: str):
    if not sheet_utils.is_gm(ctx.author.id):
        await ctx.send("❌ Only GMs can manage the scene.")
        return

    npc_id = f"npc:{name.lower().replace(' ', '_')}"
    scene_data = sheet_utils.load_scene_data()

    if npc_id not in scene_data["current_scene"]["npc_ids"]:
        await ctx.send("❌ That NPC isn't in the scene.")
        return

    scene_data["current_scene"]["npc_ids"].remove(npc_id)
    sheet_utils.save_scene_data(scene_data)
    await ctx.send(f"🗑️ **{name}** removed from the scene.")


@bot.command()
async def scene_clear(ctx):
    if not sheet_utils.is_gm(ctx.author.id):
        await ctx.send("❌ Only GMs can manage the scene.")
        return

    scene_data = sheet_utils.load_scene_data()
    scene_data["current_scene"]["npc_ids"] = []
    sheet_utils.save_scene_data(scene_data)
    await ctx.send("🧹 Scene NPC list cleared.")


@bot.command()
async def scene(ctx):
    data = sheet_utils.load_character_data()
    npc_ids = data["current_scene"]["npc_ids"]
    if not npc_ids:
        await ctx.send("📭 No NPCs are currently in the scene.")
        return

    is_gm = sheet_utils.is_gm(ctx.author.id)
    lines = []
    for npc_id in npc_ids:
        npc = data["npcs"].get(npc_id)
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
    data = sheet_utils.load_character_data()

    view = None
    is_ephemeral = True

    if char_name:  # NPC
        if not sheet_utils.is_gm(interaction.user.id):
            await interaction.response.send_message("❌ Only the GM can view NPCs.", ephemeral=True)
            return

        npc = next((npc for npc in data.get("npcs", {}).values() if npc.get("name", "").lower() == char_name), None)
        if not npc:
            await interaction.response.send_message("❌ NPC not found.", ephemeral=True)
            return

        embed = sheet_utils.format_full_sheet(char_name, npc)
        view = sheet_views.SheetEditView(interaction.user.id, "npcs", f'npc:{char_name}', char_name)
        is_ephemeral = True  # Still private for GM

    else:  # Player character
        cid = str(interaction.user.id)
        character = data["characters"].get(cid)
        if not character:
            await interaction.response.send_message("❌ Character not found.", ephemeral=True)
            return

        embed = sheet_utils.format_full_sheet(character["name"], character)
        view = sheet_views.SheetEditView(interaction.user.id, "characters", cid, character["name"])

    await interaction.response.send_message(embed=embed, view=view, ephemeral=is_ephemeral)


bot.run(os.getenv("DISCORD_BOT_TOKEN"))