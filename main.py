import os
import logging
import dotenv
import discord
from discord.ext import commands
from commands.narration import process_narration
from commands import character_commands, entity_commands, initiative_commands, relationship_commands, reminder_commands, roll_commands, scene_commands, setup_commands, recap_commands, rules_commands
from rpg_systems.fate import fate_commands
from core.initiative_views import GenericInitiativeView, PopcornInitiativeView
from core.scene_views import GenericSceneView
from rpg_systems.fate.fate_scene_views import FateSceneView
from rpg_systems.mgt2e.mgt2e_scene_views import MGT2ESceneView
from data.repositories.repository_factory import repositories

dotenv.load_dotenv()

# Check if we're using PostgreSQL or SQLite
use_postgresql = os.getenv('DATABASE_URL') is not None

from data.database import db_manager

def initialize_database():
    """Initialize PostgreSQL database with schema"""
    schema_file = 'data/init_db.sql'
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
    
    print("PostgreSQL database schema initialized successfully.")

initialize_database()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def setup_hook():
    """Setup hook runs before the bot connects to Discord"""
    # Register command trees
    await setup_commands.setup_setup_commands(bot)
    await character_commands.setup_character_commands(bot)
    await scene_commands.setup_scene_commands(bot)
    await initiative_commands.setup_initiative_commands(bot)
    await roll_commands.setup_roll_commands(bot)
    await reminder_commands.setup_reminder_commands(bot)
    await recap_commands.setup_recap_commands(bot)
    await rules_commands.setup_rules_commands(bot)
    await entity_commands.setup_entity_commands(bot)
    await relationship_commands.setup_relationship_commands(bot)
    # System-specific commands
    await fate_commands.setup_fate_commands(bot)
    
    # Register empty instances of views for persistence
    bot.add_view(GenericInitiativeView()) 
    bot.add_view(PopcornInitiativeView())
    bot.add_view(GenericSceneView())
    bot.add_view(FateSceneView())
    bot.add_view(MGT2ESceneView())

    # Sync the command tree
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
            "Please set up your server with:\n"
            "`/setup` commands"
        )
    except Exception:
        # If DM fails, send to first text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                await channel.send(
                    f"👋 Thanks for adding me to **{guild.name}**!\n"
                    "Please set up your server with:\n"
                    "`/setup` commands"
                )
                break

@bot.event
async def on_message(message: discord.Message):
    # Don't process commands here - we use the app_commands system
    
    # Update the last message time for the user
    if message.guild:
        if message.author.id != bot.user.id:
            repositories.last_message_time.update_last_message_time(message.guild.id, message.author.id, message.created_at.timestamp())
    
    # Handle mentions for automatic reminders (only for non-narration messages)
    if message.guild and message.mentions:
        reminder_cog = bot.get_cog("ReminderCommands")
        if reminder_cog:
            for user in message.mentions:
                await reminder_cog.handle_mention(message, user)

    # Process narration
    if message.author.id != bot.user.id and (message.content.startswith("gm::") or message.content.startswith("pc::") or message.content.startswith("npc::")):
        try:
            await process_narration(message)
        except Exception as e:
            print(f"Error processing narration: {e}")
            try:
                await message.reply(f"❌ Error processing character speech: {str(e)}", delete_after=10)
            except:
                pass
        return

    await bot.process_commands(message)

@bot.command()
async def myguild(ctx):
    await ctx.send(f"This server's guild_id is {ctx.guild.id}")

is_deployment = os.getenv("RAILWAY_ENVIRONMENT") is not None
log_level = logging.INFO if is_deployment else logging.DEBUG

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
bot.run(os.getenv("DISCORD_BOT_TOKEN"), log_handler=handler, log_level=log_level)