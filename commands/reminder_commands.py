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

async def setup_reminder_commands(bot: commands.Bot):
    await bot.add_cog(ReminderCommands(bot))