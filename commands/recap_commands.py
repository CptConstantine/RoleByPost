import asyncio
import discord
from discord.ext import commands
from discord import app_commands
import datetime
import json
import openai
import time
import logging
from core import channel_restriction
from data.repositories.repository_factory import repositories

class RecapCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.recap_tasks = {}  # Store auto-recap tasks by guild_id
        self.inactive_threshold_days = 30  # Consider a server inactive after 30 days of no messages
        
        # Schedule recovery of recap tasks on bot startup
        bot.loop.create_task(self._startup_recovery())
        
        # Add periodic cleanup task (runs once a day)
        bot.loop.create_task(self._periodic_cleanup())
    
    recap_group = app_commands.Group(name="recap", description="Commands for AI story recaps")
    
    @recap_group.command(
        name="generate",
        description="Generate a summary of recent game events"
    )
    @app_commands.describe(
        days="Number of days to include in the recap (default: 7)",
        private="Whether to show the recap only to you (default: False)"
    )
    @channel_restriction.no_ic_channels()
    async def recap_generate(
        self, 
        interaction: discord.Interaction, 
        days: int = 7,
        private: bool = False
    ):
        # Check if API key is configured
        api_key = repositories.api_key.get_openai_key(str(interaction.guild.id))
        if not api_key:
            await interaction.response.send_message("❌ No API key has been set. A GM must set one with `/setup openai set_api_key`.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=private)
        
        # Gather messages
        messages = await self._gather_story_messages(interaction.channel, days)
        if not messages:
            await interaction.followup.send(f"❌ No story content found in the last {days} days.", ephemeral=private)
            return
            
        try:
            # Generate the recap
            summary = await self._generate_summary(messages, api_key)
            
            # Create embed
            embed = discord.Embed(
                title=f"📜 Story Recap - Past {days} Days",
                description=summary,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"Generated {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
            
            await interaction.followup.send(embed=embed, ephemeral=private)
        except Exception as e:
            await interaction.followup.send(f"❌ Error generating recap: {str(e)}", ephemeral=True)
    
    @recap_group.command(
        name="set-auto",
        description="GM: Set up automatic story recaps"
    )
    @app_commands.describe(
        enabled="Whether automatic recaps are enabled",
        channel="Channel to post recaps in (defaults to current channel)",
        days_interval="How often to post recaps (in days, default: 7)",
        days_to_include="How many days of history to include (default: 7)"
    )
    @channel_restriction.no_ic_channels()
    async def recap_setauto(
        self,
        interaction: discord.Interaction,
        enabled: bool = None,
        channel: discord.TextChannel = None,
        days_interval: int = 7,
        days_to_include: int = 7
    ):
        # Check if user has GM permissions
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can configure automatic recaps.", ephemeral=True)
            return
        
        # Check if API key is configured
        api_key = repositories.api_key.get_openai_key(str(interaction.guild.id))
        if not api_key and enabled:
            await interaction.response.send_message("❌ No API key has been set. Please set one with `/setup openai set_api_key` first.", ephemeral=True)
            return
            
        # If channel is not specified, use current channel
        if channel is None:
            channel = interaction.channel
            
        # Get current settings
        current_settings = repositories.auto_recap.get_settings(str(interaction.guild.id))
        
        # Update settings if provided
        if enabled is not None:
            # Save to DB
            repositories.auto_recap.update_settings(
                str(interaction.guild.id),
                enabled,
                str(channel.id) if enabled else current_settings.channel_id,
                days_interval,
                days_to_include
            )
            
            # If enabling, schedule the task. If disabling, cancel any existing task
            if enabled:
                # Schedule the task
                if interaction.guild.id in self.recap_tasks:
                    self.recap_tasks[interaction.guild.id].cancel()
                self._schedule_guild_recap(str(interaction.guild.id))
                await interaction.response.send_message(
                    f"✅ Automatic recaps enabled. A recap will be posted to {channel.mention} every {days_interval} days, including {days_to_include} days of history.",
                    ephemeral=True
                )
            else:
                # Cancel the task if it exists
                if interaction.guild.id in self.recap_tasks:
                    self.recap_tasks[interaction.guild.id].cancel()
                    del self.recap_tasks[interaction.guild.id]
                await interaction.response.send_message("✅ Automatic recaps disabled.", ephemeral=True)
            return
            
        # If no parameters were provided, show current settings
        if current_settings and current_settings.enabled:
            channel_id = current_settings.channel_id
            channel_mention = f"<#{channel_id}>" if channel_id else "default channel"
            interval = current_settings.days_interval
            days_count = current_settings.days_to_include
            
            # Calculate next recap time
            last_recap = current_settings.last_recap_time or 0
            if last_recap:
                next_recap = last_recap + (interval * 86400)
                next_recap_str = f"<t:{int(next_recap)}:R>"
            else:
                next_recap_str = "soon"
            
            await interaction.response.send_message(
                f"✅ Automatic recaps are enabled.\n"
                f"• Posting to: {channel_mention}\n"
                f"• Frequency: Every {interval} days\n"
                f"• Including: {days_count} days of history\n"
                f"• Next recap: {next_recap_str}",
                ephemeral=True
            )
        else:
            await interaction.response.send_message("❌ Automatic recaps are currently disabled.", ephemeral=True)
    
    @recap_group.command(
        name="auto-now",
        description="GM: Force an automatic recap to be generated now"
    )
    @channel_restriction.no_ic_channels()
    async def auto_recap_now(self, interaction: discord.Interaction):
        # Check if user has GM permissions
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can force recaps.", ephemeral=True)
            return
            
        # Check if auto recaps are enabled
        settings = repositories.auto_recap.get_settings(str(interaction.guild.id))
        if not settings or not settings.enabled:
            await interaction.response.send_message("❌ Automatic recaps are not enabled for this server.", ephemeral=True)
            return
        
        # Check if API key is configured
        api_key = repositories.api_key.get_openai_key(str(interaction.guild.id))
        if not api_key:
            await interaction.response.send_message("❌ No API key has been set. Please set one with `/setup openai set_api_key` first.", ephemeral=True)
            return
            
        await interaction.response.send_message("Generating automatic recap now...", ephemeral=True)
        
        # Cancel existing task if it exists
        guild_id = str(interaction.guild.id)
        if guild_id in self.recap_tasks:
            self.recap_tasks[guild_id].cancel()
            del self.recap_tasks[guild_id]
            
        # Create a new task to run immediately
        task = self.bot.loop.create_task(
            self._post_scheduled_recap(
                guild_id,
                settings.channel_id,
                settings.days_to_include,
                0  # Run immediately
            )
        )
        self.recap_tasks[guild_id] = task
    
    @recap_group.command(
        name="auto-status",
        description="Check the status of automatic story recaps for this server"
    )
    @channel_restriction.no_ic_channels()
    async def recap_auto_status(self, interaction: discord.Interaction):
        """Show the current automatic recap settings for this server"""
        settings = repositories.auto_recap.get_settings(str(interaction.guild.id))
        api_key_set = repositories.api_key.get_openai_key(str(interaction.guild.id)) is not None
        
        # Create embed
        embed = discord.Embed(
            title="📜 Automatic Story Recap Settings",
            color=discord.Color.blue()
        )
        
        # Main settings section
        enabled = settings.enabled
        paused = settings.paused
        
        # Format the interval
        days_interval = settings.days_interval
        days_to_include = settings.days_to_include
        
        # Calculate next recap time if enabled
        next_recap_str = "Not scheduled"
        if enabled and not paused:
            last_recap_time = settings.last_recap_time or 0
            if last_recap_time:
                next_recap_time = last_recap_time + (days_interval * 86400)
                next_recap_str = f"<t:{int(next_recap_time)}:R>"
            else:
                next_recap_str = "Soon"
        
        # Status section
        status_value = []
        if not api_key_set:
            status_value.append("⚠️ **API Key:** Not set (required for recaps)")
        else:
            status_value.append("✅ **API Key:** Set")
        
        status_value.append(f"**Enabled:** {'✅' if enabled else '❌'}")
        if enabled and paused:
            status_value.append("⏸️ **Status:** Paused due to inactivity")
        
        embed.add_field(
            name="Status",
            value="\n".join(status_value),
            inline=False
        )
        
        # Configuration details
        if enabled or api_key_set:
            config_value = []
            
            # Channel info
            channel_id = settings.channel_id
            if channel_id:
                channel_mention = f"<#{channel_id}>"
                config_value.append(f"**Channel:** {channel_mention}")
            else:
                config_value.append("**Channel:** Not set")
            
            # Schedule info
            config_value.append(f"**Frequency:** Every {days_interval} days")
            config_value.append(f"**History:** {days_to_include} days of messages")
            config_value.append(f"**Next Recap:** {next_recap_str}")
            
            # Activity check info
            activity_check = settings.check_activity
            config_value.append(f"**Activity Checks:** {'✅ Enabled' if activity_check else '❌ Disabled'}")
            
            embed.add_field(
                name="Configuration",
                value="\n".join(config_value),
                inline=False
            )
        
        # Add footer with commands based on user permissions
        if await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            footer_text = "GM Commands: /recap setauto, /setup openai set_api_key, /recap autonow"
        else:
            footer_text = "Only GMs can modify automatic recap settings"
            
        embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    async def _startup_recovery(self):
        """Recover and reschedule all automatic recaps when the bot starts up"""
        # Wait until the bot is fully ready before scheduling recap tasks
        await self.bot.wait_until_ready()
        logging.info("Starting recap task recovery...")
        
        # Get all guilds with auto recap enabled
        guilds = repositories.auto_recap.get_all_enabled_guilds()
        count = 0
        
        for guild_id in guilds:
            try:
                # Verify the guild still exists and the bot is still in it
                if not self.bot.get_guild(int(guild_id)):
                    logging.warning(f"Guild {guild_id} not found or bot not in guild, skipping recap recovery")
                    continue
                    
                # Schedule the recap task
                self._schedule_guild_recap(guild_id)
                count += 1
            except Exception as e:
                logging.error(f"Error recovering recap for guild {guild_id}: {e}")
        
        logging.info(f"Recovered {count} automatic recap tasks")
    
    async def _periodic_cleanup(self):
        """Run once a day to check for and clean up inactive or deleted servers"""
        await self.bot.wait_until_ready()
        
        while not self.bot.is_closed():
            try:
                logging.info("Starting periodic cleanup of inactive recap servers")
                await self._cleanup_inactive_servers()
                logging.info("Inactive server cleanup complete")
                
                # Wait 24 hours before the next cleanup
                await asyncio.sleep(86400)  # 24 hours
            except Exception as e:
                logging.error(f"Error in periodic cleanup: {e}")
                await asyncio.sleep(3600)  # Wait an hour and try again if there was an error
    
    async def _cleanup_inactive_servers(self):
        """Check for and clean up inactive or deleted servers"""
        # Get all guilds with auto recap enabled
        guilds = repositories.auto_recap.get_all_enabled_guilds()
        for guild_id in guilds:
            try:
                # Check if the guild still exists/bot is still in it
                guild = self.bot.get_guild(int(guild_id))
                if not guild:
                    # Guild not found - either deleted or bot was kicked
                    logging.warning(f"Guild {guild_id} not found during cleanup. Disabling auto recaps.")
                    await self._disable_recaps_for_deleted_guild(guild_id)
                    continue
                
                # Get the channel for this guild's recaps
                settings = repositories.auto_recap.get_settings(guild_id)
                if not settings or not settings.enabled:
                    continue
                    
                channel_id = settings.channel_id
                channel = guild.get_channel(int(channel_id)) if channel_id else None
                if not channel:
                    # Channel was deleted, disable recaps
                    logging.warning(f"Channel {channel_id} not found in guild {guild_id}. Disabling auto-recaps.")
                    await self._disable_recaps_for_missing_channel(guild_id)
                    continue
                
                # Check for server activity
                if settings.check_activity:  # Allow servers to opt out of activity checks
                    is_active = await self._check_server_activity(channel, self.inactive_threshold_days)
                    if not is_active:
                        # Server is inactive, pause recaps temporarily
                        await self._pause_recaps_for_inactive_guild(guild_id)
                        continue
                    else:
                        # Server became active again, unpause if needed
                        await self._unpause_recaps_if_needed(guild_id)
                
            except Exception as e:
                logging.error(f"Error checking guild {guild_id} during cleanup: {e}")
    
    async def _check_server_activity(self, channel, days):
        """Check if there has been any activity in the channel in the specified number of days"""
        # Calculate cutoff time
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff_time = now - datetime.timedelta(days=days)
        
        # Check for any recent messages
        try:
            async for message in channel.history(limit=1, after=cutoff_time):
                # Found at least one message in the time period
                return True
        except discord.Forbidden:
            # Bot lost permission to read the channel
            logging.warning(f"Lost permission to read channel {channel.id} in guild {channel.guild.id}")
            return False
        except Exception as e:
            logging.error(f"Error checking activity in channel {channel.id}: {e}")
            # In case of API errors, assume active to avoid false negatives
            return True
            
        # No messages found in the time period
        return False
    
    async def _disable_recaps_for_deleted_guild(self, guild_id):
        """Handle a guild that no longer exists or the bot is no longer in"""
        try:
            # Cancel any running tasks
            if guild_id in self.recap_tasks:
                self.recap_tasks[guild_id].cancel()
                del self.recap_tasks[guild_id]
            
            # Disable recaps in the database
            repositories.auto_recap.update_settings(
                guild_id,
                enabled=False,
                channel_id=None,
                days_interval=7,
                days_to_include=7
            )
            
            # Optionally, clean up the API key if the guild is truly gone
            # This is more aggressive so maybe only do this after multiple confirmations
            # repositories.api_key.set_openai_key(guild_id, None)
            
            logging.info(f"Disabled recaps for deleted guild {guild_id}")
        except Exception as e:
            logging.error(f"Error disabling recaps for deleted guild {guild_id}: {e}")
    
    async def _disable_recaps_for_missing_channel(self, guild_id):
        """Handle a case where the recap channel was deleted"""
        try:
            # Cancel any running tasks
            if guild_id in self.recap_tasks:
                self.recap_tasks[guild_id].cancel()
                del self.recap_tasks[guild_id]
            
            # Disable recaps in the database
            repositories.auto_recap.update_settings(
                guild_id,
                enabled=False,
                channel_id=None,
                days_interval=7,
                days_to_include=7
            )
            
            # Try to send a notification to the guild's system channel if possible
            guild = self.bot.get_guild(int(guild_id))
            if guild and guild.system_channel:
                try:
                    await guild.system_channel.send(
                        "⚠️ The channel configured for automatic story recaps no longer exists. "
                        "Auto-recaps have been disabled. Use `/recap autostatus` to set up a new channel."
                    )
                except:
                    pass  # Silently fail if we can't send the message
                    
            logging.info(f"Disabled recaps for guild {guild_id} due to missing channel")
        except Exception as e:
            logging.error(f"Error disabling recaps for guild {guild_id} with missing channel: {e}")
    
    async def _pause_recaps_for_inactive_guild(self, guild_id):
        """Temporarily pause recaps for an inactive guild"""
        try:
            # Get current settings
            settings = repositories.auto_recap.get_settings(guild_id)
            
            # Only pause if not already paused
            if not settings.paused:
                # Mark as paused in database
                repositories.auto_recap.update_pause_state(guild_id, True)
                
                # Cancel any running tasks but don't delete from the recap_tasks dictionary
                # This keeps track of the paused state
                if guild_id in self.recap_tasks:
                    self.recap_tasks[guild_id].cancel()
                    # Replace with a placeholder
                    self.recap_tasks[guild_id] = "PAUSED"
                
                logging.info(f"Paused recaps for inactive guild {guild_id}")
        except Exception as e:
            logging.error(f"Error pausing recaps for inactive guild {guild_id}: {e}")
    
    async def _unpause_recaps_if_needed(self, guild_id):
        """Re-enable recaps for a guild if it was previously paused due to inactivity"""
        try:
            # Check if currently paused
            settings = repositories.auto_recap.get_settings(guild_id)
            if settings.paused:
                # Un-pause in the database
                repositories.auto_recap.update_pause_state(guild_id, False)
                
                # Reschedule the task
                if guild_id in self.recap_tasks and self.recap_tasks[guild_id] == "PAUSED":
                    self._schedule_guild_recap(guild_id)
                
                logging.info(f"Unpaused recaps for guild {guild_id} as it's active again")
        except Exception as e:
            logging.error(f"Error unpausing recaps for guild {guild_id}: {e}")
    
    async def _gather_story_messages(self, channel, days):
        """Gather messages from the last X days that contain story content"""
        # Calculate cutoff time
        now = datetime.datetime.now(datetime.timezone.utc)
        cutoff_time = now - datetime.timedelta(days=days)
        
        story_messages = []
        async for message in channel.history(limit=1000, after=cutoff_time):
            # Skip bot messages that aren't narration
            if message.author.bot and not (
                # Include webhook messages (narrations)
                message.webhook_id or 
                # Include embeds with narration/story content
                (message.embeds and message.author.id == self.bot.user.id and
                 any(e.description for e in message.embeds))
            ):
                continue
                
            # Skip command messages
            if message.content and message.content.startswith('/'):
                continue
                
            # Skip system messages
            if not message.content and not message.embeds:
                continue
                
            # If it's a narration message with embed, extract content
            if message.embeds and message.author.id == self.bot.user.id:
                for embed in message.embeds:
                    if embed.description:
                        author_name = embed.author.name if embed.author else "Narrator"
                        story_messages.append({
                            'author': author_name,
                            'content': embed.description,
                            'timestamp': message.created_at.isoformat()
                        })
            # Regular user message
            elif message.content:
                story_messages.append({
                    'author': message.author.display_name,
                    'content': message.content,
                    'timestamp': message.created_at.isoformat()
                })
                    
        return story_messages
    
    async def _generate_summary(self, messages, api_key):
        """Use OpenAI API to generate a summary of the story messages"""
        # Sort messages by timestamp
        messages.sort(key=lambda x: x['timestamp'])
        
        # Construct prompt
        messages_text = "\n\n".join([f"{msg['author']}: {msg['content']}" for msg in messages])
        
        prompt = [
            {"role": "system", "content": "You are a skilled storyteller tasked with creating concise summaries of tabletop RPG play-by-post games. Focus on the narrative, character development, and key plot points. Ignore out-of-character discussions, dice rolls, and game mechanics. Your summary should read like a story recap that helps players remember what happened."},
            {"role": "user", "content": f"Here are the recent posts from our play-by-post RPG game. Please provide a coherent, well-structured summary of the main story events:\n\n{messages_text}"}
        ]
        
        # Make API request using OpenAI client library
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=prompt,
                max_tokens=1000,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logging.error(f"Error calling OpenAI API: {str(e)}")
            raise Exception(f"OpenAI API error: {str(e)}")

    def _schedule_guild_recap(self, guild_id):
        """Schedule a recap task for a specific guild"""
        try:
            settings = repositories.auto_recap.get_settings(guild_id)
            if not settings or not settings.enabled:
                return
                
            # Calculate when the next recap should be posted
            last_recap_time = settings.last_recap_time or 0
            now = datetime.datetime.now().timestamp()
            interval_seconds = settings.days_interval * 86400
            next_recap_time = last_recap_time + interval_seconds
            
            # If the next recap time is in the past, schedule it for now + 10 seconds
            if next_recap_time <= now:
                delay_seconds = 10
            else:
                delay_seconds = next_recap_time - now
                
            # Log the scheduling
            next_time = datetime.datetime.fromtimestamp(now + delay_seconds)
            logging.info(f"Scheduling recap for guild {guild_id} at {next_time.strftime('%Y-%m-%d %H:%M:%S')} (in {delay_seconds/3600:.1f} hours)")
            
            # Schedule the task
            task = self.bot.loop.create_task(
                self._post_scheduled_recap(
                    guild_id,
                    settings.channel_id,
                    settings.days_to_include,
                    delay_seconds
                )
            )
            
            # Store the task with additional metadata for recovery
            self.recap_tasks[guild_id] = task
            
        except Exception as e:
            logging.error(f"Error scheduling recap for guild {guild_id}: {e}")
        
    async def _post_scheduled_recap(self, guild_id, channel_id, days_to_include, delay_seconds):
        """Post a scheduled recap after the specified delay"""
        try:
            # Wait for the scheduled time
            await asyncio.sleep(delay_seconds)
            
            # Additional check for deleted/inaccessible guild before proceeding
            guild = self.bot.get_guild(int(guild_id))
            if not guild:
                logging.error(f"Guild {guild_id} not found or inaccessible")
                await self._disable_recaps_for_deleted_guild(guild_id)
                return
            
            # Check if recap is still enabled
            settings = repositories.auto_recap.get_settings(guild_id)
            if not settings or not settings.enabled or settings.paused:
                logging.info(f"Recap for guild {guild_id} is now disabled or paused, skipping")
                return
            
            # Get the channel
            channel = guild.get_channel(int(channel_id)) if channel_id else None
            if not channel:
                logging.error(f"Channel {channel_id} not found in guild {guild_id}")
                await self._disable_recaps_for_missing_channel(guild_id)
                return
            
            # Get the API key
            api_key = repositories.api_key.get_openai_key(guild_id)
            if not api_key:
                logging.error(f"No API key for guild {guild_id}")
                return
                
            # Gather messages
            messages = await self._gather_story_messages(channel, days_to_include)
            if not messages:
                logging.info(f"No messages to summarize for guild {guild_id}")
                # Reschedule the next one even if there are no messages
                repositories.auto_recap.update_last_recap_time(guild_id, datetime.datetime.now().timestamp())
                self._schedule_guild_recap(guild_id)
                return
                
            # Generate the recap
            logging.info(f"Generating recap for guild {guild_id} with {len(messages)} messages")
            summary = await self._generate_summary(messages, api_key)
            
            # Create embed
            embed = discord.Embed(
                title=f"📜 Automatic Story Recap - Past {days_to_include} Days",
                description=summary,
                color=discord.Color.blue()
            )
            
            current_time = datetime.datetime.now()
            embed.set_footer(text=f"Generated {current_time.strftime('%Y-%m-%d %H:%M')}")
            
            await channel.send(embed=embed)
            logging.info(f"Posted recap to guild {guild_id}, channel {channel_id}")
            
            # Update the last recap time
            repositories.auto_recap.update_last_recap_time(guild_id, current_time.timestamp())
            
            # After success, check server activity before rescheduling
            last_activity = await self._check_server_recent_activity(channel)
            if last_activity < self.inactive_threshold_days:
                # Server still active, reschedule as normal
                self._schedule_guild_recap(guild_id)
            else:
                # Server inactive, pause recaps
                await self._pause_recaps_for_inactive_guild(guild_id)
            
        except Exception as e:
            logging.error(f"Error posting scheduled recap: {e}")
            # Attempt to reschedule anyway with a shorter delay to retry
            try:
                # Use a retry delay of 1 hour
                task = self.bot.loop.create_task(
                    self._post_scheduled_recap(
                        guild_id,
                        channel_id,
                        days_to_include,
                        3600  # 1 hour retry 
                    )
                )
                self.recap_tasks[guild_id] = task
            except Exception as reschedule_error:
                logging.error(f"Error rescheduling recap: {reschedule_error}")
    
    async def _check_server_recent_activity(self, channel):
        """Check when the server was last active and return days since last activity"""
        now = datetime.datetime.now(datetime.timezone.utc)
        last_message_time = now
        
        try:
            # Try to get the most recent message
            async for message in channel.history(limit=1):
                last_message_time = message.created_at
                break
        except:
            # If we can't access history, assume recent activity
            return 0
        
        # Calculate days since last activity
        days_since = (now - last_message_time).days
        return days_since

async def setup_recap_commands(bot: commands.Bot):
    await bot.add_cog(RecapCommands(bot))