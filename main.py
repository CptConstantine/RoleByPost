import os
import logging
import dotenv
import discord
from discord.ext import commands
from data import repo
from commands import character_commands, initiative_commands, scene_commands, server_commands

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def setup_hook():
    await bot.tree.sync()

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

@bot.event
async def on_message(message):
    if message.guild and not message.author.bot:
        repo.set_last_message_time(message.guild.id, message.author.id, message.created_at.timestamp())
    await bot.process_commands(message)

# Commands all systems have access to
server_commands.setup_server_commands(bot)
character_commands.setup_character_commands(bot)
scene_commands.setup_scene_commands(bot)
initiative_commands.setup_initiative_commands(bot)

# System-specific commands


handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
bot.run(os.getenv("DISCORD_BOT_TOKEN"), log_handler=handler, log_level=logging.DEBUG)