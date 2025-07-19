import os
import logging
import re
import dotenv
import discord
from discord.ext import commands
from commands import narration_commands, narration_context_menu, user_context_menu
from commands.narration import can_user_speak_as_character, process_narration, send_narration_webhook
from commands import character_commands, entity_commands, help_commands, initiative_commands, link_commands, reminder_commands, roll_commands, scene_commands, setup_commands, recap_commands, rules_commands
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
    view_file = 'data/views.sql'
    
    with open(schema_file, 'r') as f:
        schema_sql = f.read()

    with open(view_file, 'r') as f:
        view_sql = f.read()

    with db_manager.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema_sql)
            cur.execute(view_sql)

    print("PostgreSQL database schema and views initialized successfully.")

initialize_database()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def setup_hook():
    """Setup hook runs before the bot connects to Discord"""
    # Register command trees
    await help_commands.setup_help_commands(bot)
    await setup_commands.setup_setup_commands(bot)
    await character_commands.setup_character_commands(bot)
    await scene_commands.setup_scene_commands(bot)
    await initiative_commands.setup_initiative_commands(bot)
    await roll_commands.setup_roll_commands(bot)
    await reminder_commands.setup_reminder_commands(bot)
    await recap_commands.setup_recap_commands(bot)
    await rules_commands.setup_rules_commands(bot)
    await entity_commands.setup_entity_commands(bot)
    await link_commands.setup_link_commands(bot)
    await narration_commands.setup_narration_commands(bot)
    await narration_context_menu.setup_narration_context_menu_commands(bot)
    await user_context_menu.setup_user_context_menu_commands(bot)
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
    print(f'Logged in as {bot.user} ({bot.user.name})!')

@bot.event
async def on_guild_join(guild):
    # Try to DM the owner
    try:
        await guild.owner.send(
            f"👋 Thanks for adding me to **{guild.name}**!\n"
            "Please set up your server with:\n"
            "`/setup` commands\n"
            "or use `/help`\n\n"
            "**Links**\n"
            "[Documentation](https://github.com/CptConstantine/RoleByPost)\n"
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
    # Skip processing webhook messages entirely
    if message.webhook_id:
        return

    # Update the last message time for the user
    if message.guild:
        if message.author.id != bot.user.id:
            repositories.last_message_time.update_last_message_time(str(message.guild.id), str(message.author.id), message.created_at.timestamp())
    
    # Handle mentions for automatic reminders (only for non-narration messages)
    if message.guild and message.mentions:
        reminder_cog = bot.get_cog("ReminderCommands")
        if reminder_cog:
            for user in message.mentions:
                await reminder_cog.handle_mention(message, user)

    if message.guild and message.author.id != bot.user.id:
        # For threads, check the parent channel's type
        channel_to_check = message.channel.parent if isinstance(message.channel, discord.Thread) else message.channel
        channel_type = repositories.channel_permissions.get_channel_type(str(message.guild.id), str(channel_to_check.id))
        
        if channel_type == 'ic':
            # Process narration
            content_lower = message.content.lower()
            if content_lower.startswith(("pc::", "npc::", "gm::")) or re.match(r"[^:]+::", message.content):
                try:
                    await process_narration(message)
                except Exception as e:
                    print(f"Error processing narration: {e}")
                    try:
                        await message.reply(f"❌ Error processing character speech: {str(e)}", delete_after=10)
                    except:
                        pass
                return
            else:
                # Check for sticky character in this channel
                sticky_char_id = repositories.sticky_narration.get_sticky_character(
                    str(message.guild.id), 
                    str(message.author.id), 
                    str(channel_to_check.id) # Use the parent channel if we are in a thread
                )
                if sticky_char_id:
                    # Get the character and process as normal narration
                    char = repositories.character.get_by_id(sticky_char_id)
                    if char and await can_user_speak_as_character(str(message.guild.id), message.author.id, char):
                        await send_narration_webhook(message, char, message.content)
                        await message.delete()
                        return

    await bot.process_commands(message)

@bot.event
async def on_raw_message_edit(payload: discord.RawMessageUpdateEvent):
    """Handle raw message edits to catch edits on uncached messages."""
    # Don't process edits from bots
    if payload.cached_message and payload.cached_message.author.bot:
        return
        
    try:
        channel = await bot.fetch_channel(payload.channel_id)
        after = await channel.fetch_message(payload.message_id)
    except (discord.NotFound, discord.Forbidden):
        return

    # Ignore edits from the bot itself
    if after.author.id == bot.user.id:
        return

    # This logic assumes we only care about edits that *result* in a narration command.
    after_content_lower = after.content.lower()
    if after_content_lower.startswith(("pc::", "npc::", "gm::")):
        try:
            await process_narration(after)
        except Exception as e:
            print(f"Error processing narration from edit: {e}")
            try:
                await after.reply(f"❌ Error processing character speech from edit: {str(e)}", delete_after=10)
            except:
                pass
        return
    
    # Handle mentions for automatic reminders on edits
    if after.guild and after.mentions:
        reminder_cog = bot.get_cog("ReminderCommands")
        if reminder_cog:
            for user in after.mentions:
                await reminder_cog.handle_mention(after, user)

    # If you want to process commands on edit, you can do so here.
    await bot.process_commands(after)

@bot.command()
async def myguild(ctx: commands.Context):
    await ctx.send(f"This server's guild_id is {ctx.guild.id}")

is_deployment = os.getenv("RAILWAY_ENVIRONMENT") is not None
log_level = logging.INFO if is_deployment else logging.DEBUG

handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
bot.run(os.getenv("DISCORD_BOT_TOKEN"), log_handler=handler, log_level=log_level)