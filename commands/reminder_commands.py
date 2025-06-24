import re
import asyncio
import datetime
import discord
from discord.ext import commands
from discord import app_commands
from data import repo

class ReminderCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Dictionary to track active mention reminders by (guild_id, user_id)
        self.active_mention_reminders = {}

    reminder_group = app_commands.Group(name="reminder", description="Commands for reminding users to post")

    @reminder_group.command(
        name="send", 
        description="GM: Remind a player or a role to post after a delay if they haven't posted."
    )
    @app_commands.describe(
        user="Select a user to remind",
        role="Optionally select a role to remind all its members",
        message="Optional custom reminder message",
        delay="How long to wait before DMing (e.g. '24h', '2d', '90m'). Default: 24h"
    )
    async def send_reminder(
        self,
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
            # Use fetch_members to ensure we get all role members
            members = [member async for member in interaction.guild.fetch_members() 
                      if role in member.roles]
            targets.update(members)
            
        if not targets:
            await interaction.response.send_message("❌ Please specify at least one user or role to remind.", ephemeral=True)
            return
            
        # Parse delay format
        delay_seconds = 86400  # Default to 24 hours
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
            self.bot.loop.create_task(self._schedule_dm_reminder(interaction.guild.id, user, message, now, delay_seconds))
            
        await interaction.response.send_message(f"⏰ Reminder{'s' if len(targets) > 1 else ''} scheduled for {delay}.", ephemeral=True)
    
    @app_commands.default_permissions(administrator=True)
    @reminder_group.command(
        name="set",
        description="Set a reminder for yourself or another user"
    )
    @app_commands.describe(
        user="The user to set the reminder for (leave blank for yourself)",
        time="The time for the reminder (e.g. '15 minutes', '2 hours', '1 day')",
        message="The reminder message"
    )
    async def set_reminder(
        self,
        interaction: discord.Interaction,
        user: discord.Member = None,
        time: str = "15 minutes",
        message: str = "This is a reminder!"
    ):
        # Check if the user has permission to use this command
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ You do not have permission to use this command.", ephemeral=True)
            return
        
        # If no user is specified, set the reminder for the command issuer
        if not user:
            user = interaction.user
            
        # Parse the time argument
        time_seconds = self._parse_time_argument(time)
        if time_seconds is None:
            await interaction.response.send_message("❌ Invalid time format. Use like '15 minutes', '2 hours', or '1 day'.", ephemeral=True)
            return
        
        # Set the reminder in the database
        now = datetime.datetime.now(datetime.timezone.utc).timestamp()
        repo.set_reminder_time(interaction.guild.id, user.id, now)
        
        # Schedule the reminder
        self.bot.loop.create_task(
            self._schedule_dm_reminder(interaction.guild.id, user, message, now, time_seconds)
        )
        
        await interaction.response.send_message(f"✅ Reminder set for {user.mention} in {time}.", ephemeral=True)
    
    @reminder_group.command(
        name="setauto", 
        description="GM: Configure automatic reminders when users are mentioned"
    )
    @app_commands.describe(
        enabled="Whether automatic reminders are enabled",
        delay="How long to wait before sending reminders (e.g. '24h', '2d', '90m')"
    )
    async def set_auto_reminders(
        self, 
        interaction: discord.Interaction, 
        enabled: bool = None, 
        delay: str = None
    ):
        if not repo.is_gm(interaction.guild.id, interaction.user.id):
            await interaction.response.send_message("❌ Only GMs can manage automatic reminders.", ephemeral=True)
            return
        
        # Get current settings
        settings = repo.get_auto_reminder_settings(interaction.guild.id)
        current_enabled = settings["enabled"]
        current_delay = settings["delay_seconds"]
        
        # Update enabled setting if provided
        if enabled is not None:
            current_enabled = enabled
        
        # Parse delay if provided
        delay_seconds = current_delay
        formatted_delay = None
        if delay is not None:
            # Parse delay format
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
                
                current_delay = delay_seconds
                formatted_delay = delay
            else:
                await interaction.response.send_message("❌ Invalid delay format. Use like '24h', '2d', or '90m'.", ephemeral=True)
                return
        
        # Save the settings using the combined method
        if enabled is not None or delay is not None:
            repo.set_auto_reminder(interaction.guild.id, current_enabled, current_delay)
        
        # Format the current delay for display
        if formatted_delay is None:
            if current_delay >= 86400:
                formatted_delay = f"{current_delay // 86400}d"
            elif current_delay >= 3600:
                formatted_delay = f"{current_delay // 3600}h"
            elif current_delay >= 60:
                formatted_delay = f"{current_delay // 60}m"
            else:
                formatted_delay = f"{current_delay}s"
        
        # Create response message
        response_parts = []
        if enabled is not None:
            status = "enabled" if current_enabled else "disabled"
            response_parts.append(f"Automatic reminders are now {status}")
        
        if delay is not None:
            response_parts.append(f"Reminder delay set to {formatted_delay}")
        
        if not response_parts:
            # If neither parameter was provided, show current settings
            status = "enabled" if current_enabled else "disabled"
            response_parts.append(f"Automatic reminders are currently {status} with a delay of {formatted_delay}")
        
        await interaction.response.send_message(f"✅ {' and '.join(response_parts)}.", ephemeral=True)
    
    @reminder_group.command(
        name="autooptout", 
        description="Opt out of receiving automatic reminders when mentioned"
    )
    @app_commands.describe(
        opt_out="Whether to opt out of automatic reminders"
    )
    async def auto_optout(self, interaction: discord.Interaction, opt_out: bool = True):
        repo.set_user_optout(interaction.guild.id, interaction.user.id, opt_out)
        status = "opted out of" if opt_out else "opted into"
        await interaction.response.send_message(f"✅ You have {status} automatic reminders.", ephemeral=True)

    @reminder_group.command(
        name="autostatus", 
        description="Check the current automatic reminder settings"
    )
    async def auto_status(self, interaction: discord.Interaction):
        settings = repo.get_auto_reminder_settings(interaction.guild.id)
        is_opted_out = repo.is_user_opted_out(interaction.guild.id, interaction.user.id)
        
        delay_seconds = settings["delay_seconds"]
        if delay_seconds >= 86400:
            formatted = f"{delay_seconds // 86400} day(s)"
        elif delay_seconds >= 3600:
            formatted = f"{delay_seconds // 3600} hour(s)"
        elif delay_seconds >= 60:
            formatted = f"{delay_seconds // 60} minute(s)"
        else:
            formatted = f"{delay_seconds} second(s)"
            
        embed = discord.Embed(
            title="🔔 Automatic Reminder Settings",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Server Settings",
            value=(
                f"**Enabled:** {'✅' if settings['enabled'] else '❌'}\n"
                f"**Delay:** {formatted}"
            ),
            inline=False
        )
        
        embed.add_field(
            name="Your Settings",
            value=f"**Opted Out:** {'✅' if is_opted_out else '❌'}",
            inline=False
        )
        
        if repo.is_gm(interaction.guild.id, interaction.user.id):
            embed.set_footer(text="As a GM, you can change these settings with /reminder setauto")
        else:
            embed.set_footer(text="You can opt out with /reminder auto_optout true")
            
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # Helper methods
    def _parse_time_argument(self, time_str):
        """Parse a time argument in the format '15 minutes', '2 hours', or '1 day'."""
        time_str = time_str.lower()
        if "minute" in time_str:
            match = re.search(r"(\d+)", time_str)
            if match:
                return int(match.group(1)) * 60
        elif "hour" in time_str:
            match = re.search(r"(\d+)", time_str)
            if match:
                return int(match.group(1)) * 3600
        elif "day" in time_str:
            match = re.search(r"(\d+)", time_str)
            if match:
                return int(match.group(1)) * 86400
        return None

    async def _schedule_dm_reminder(self, guild_id, user, message, reminder_time, delay_seconds):
        """Internal method to handle the delayed sending of reminders"""
        await asyncio.sleep(delay_seconds)
        
        # Only send reminder if the user hasn't posted since the reminder was set
        last_msg = repo.get_last_message_time(guild_id, user.id)
        if not last_msg or last_msg < reminder_time:
            try:
                await user.send(f"**Reminder from {self.bot.get_guild(guild_id).name}:** {message}")
            except discord.Forbidden:
                pass  # Can't DM user - they have DMs disabled
            except Exception as e:
                print(f"Error sending reminder to {user}: {e}")

    # New method for handling automatic mention reminders
    async def handle_mention(self, message, mentioned_user):
        """Handle automatic reminders for user mentions"""
        guild_id = message.guild.id
        user_id = mentioned_user.id
        
        # Ignore mentions by bots
        if message.author.bot:
            return
            
        # Check if automatic reminders are enabled for this server
        settings = repo.get_auto_reminder_settings(guild_id)
        if not settings["enabled"]:
            return
            
        # Check if the user has opted out
        if repo.is_user_opted_out(guild_id, user_id):
            return
            
        # Check if there's already an active reminder for this user in this guild
        reminder_key = (guild_id, user_id)
        if reminder_key in self.active_mention_reminders:
            # Update the timestamp of the existing reminder to reset the timer
            self.active_mention_reminders[reminder_key]["timestamp"] = message.created_at.timestamp()
            return
            
        # Create a new reminder
        now = message.created_at.timestamp()
        repo.set_reminder_time(guild_id, user_id, now)
        
        # Create task and store it in the dictionary
        task = self.bot.loop.create_task(
            self._schedule_auto_reminder(
                guild_id, 
                mentioned_user, 
                now, 
                settings["delay_seconds"],
                reminder_key
            )
        )
        self.active_mention_reminders[reminder_key] = {
            "timestamp": now,
            "task": task
        }

    async def _schedule_auto_reminder(self, guild_id, user, reminder_time, delay_seconds, reminder_key):
        """Internal method to handle automatic reminders"""
        try:
            await asyncio.sleep(delay_seconds)
            
            # Only send reminder if the user hasn't posted since the reminder was set
            last_msg = repo.get_last_message_time(guild_id, user.id)
            if not last_msg or last_msg <= reminder_time:
                try:
                    guild_name = self.bot.get_guild(guild_id).name
                    await user.send(
                        f"**Automatic Reminder from {guild_name}:** "
                        f"You were mentioned and haven't responded yet. Please check the server!"
                    )
                except discord.Forbidden:
                    pass  # Can't DM user - they have DMs disabled
                except Exception as e:
                    print(f"Error sending auto reminder to {user}: {e}")
                    
        finally:
            # Remove the reminder from the active list
            if reminder_key in self.active_mention_reminders:
                del self.active_mention_reminders[reminder_key]


async def setup_reminder_commands(bot: commands.Bot):
    await bot.add_cog(ReminderCommands(bot))