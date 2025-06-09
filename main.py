import os
import logging
import dotenv
import discord
from discord.ext import commands


dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)


@bot.event
async def setup_hook():
    await bot.tree.sync(guild=discord.Object(id=1379609249834864721))


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')


@bot.event
async def on_guild_join(guild):
    # Try to DM the owner
    try:
        await guild.owner.send(
            f"👋 Thanks for adding me to **{guild.name}**!\n"
            "Please set up your RPG system with:\n"
            "`!setsystem fate` or `!setsystem mgt2e`"
        )
    except Exception:
        # If DM fails, send to first text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"👋 Thanks for adding me to **{guild.name}**!\n"
                    "Please set up your RPG system with:\n"
                    "`!setsystem fate` or `!setsystem mgt2e`"
                )
                break


import bot_commands
bot_commands.setup(bot)

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
bot.run(os.getenv("DISCORD_BOT_TOKEN"), log_handler=handler, log_level=logging.DEBUG)