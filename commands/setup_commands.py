import re
import asyncio
import datetime
import discord
from discord.ext import commands
from discord import app_commands
from core.shared_views import RequestRollView
from core.utils import roll_parameters_to_dict
import core.factories as factories
from data.repositories.repository_factory import repositories


async def skill_autocomplete(interaction: discord.Interaction, current: str):
    try:
        all_chars = repositories.character.get_all_characters(str(interaction.guild.id))
        character = next((c for c in all_chars if not c.is_npc and str(c.owner_id) == str(interaction.user.id)), None)
        if not character:
            return []
        skills = character.skills
        options = [k for k in skills.keys() if current.lower() in k.lower()]
        return [app_commands.Choice(name=k, value=k) for k in options[:25]]
    except Exception as e:
        print("Autocomplete error:", e)
        return []

async def attribute_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repositories.character.get_all_characters(str(interaction.guild.id))
    character = next((c for c in all_chars if not c.is_npc and str(c.owner_id) == str(interaction.user.id)), None)
    if not character:
        return []
    attributes = character.attributes
    options = [k for k in attributes.keys() if current.lower() in k.lower()]
    return [app_commands.Choice(name=k, value=k) for k in options[:25]]

class SetupCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    setup_group = app_commands.Group(name="setup", description="Server setup commands")
    openai_group = app_commands.Group(name="openai", description="OpenAI API key management", parent=setup_group)

    @setup_group.command(
        name="gmrole",
        description="Set a Discord role as the GM role for the server. You must be an Admin."
    )
    @app_commands.describe(role="The Discord role to set as the GM role")
    async def setup_gmrole(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only admins can set the GM role.", ephemeral=True)
            return
        
        repositories.server.set_gm_role(str(interaction.guild.id), str(role.id))
        
        await interaction.response.send_message(
            f"✅ Set role `{role.name}` as the GM role. Members with this role now have GM permissions.",
            ephemeral=True
        )

    @setup_group.command(
        name="playerrole",
        description="Set a Discord role as the player role for the server. You must be an Admin."
    )
    @app_commands.describe(role="The Discord role to set as the player role")
    async def setup_playerrole(self, interaction: discord.Interaction, role: discord.Role):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only admins can set the player role.", ephemeral=True)
            return
        
        repositories.server.set_player_role(str(interaction.guild.id), str(role.id))
        
        await interaction.response.send_message(
            f"✅ Set role `{role.name}` as the player role. Members with this role are now considered players.",
            ephemeral=True
        )

    @setup_group.command(name="system", description="Set the RPG system for your server. You must be an Admin.")
    @app_commands.describe(system="The system to use (e.g. generic, fate, mgt2e)")
    async def setup_system(self, interaction: discord.Interaction, system: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only admins can set the system.", ephemeral=True)
            return
        valid_systems = ["generic", "fate", "mgt2e"]
        system = system.lower()
        if system not in valid_systems:
            await interaction.response.send_message(f"❌ Invalid system. Valid options: {', '.join(valid_systems)}", ephemeral=True)
            return
        repositories.server.set_system(str(interaction.guild.id), system)
        await interaction.response.send_message(f"✅ System set to {system.upper()} for this server.", ephemeral=True)

    @setup_group.command(name="defaultskillsfile", description="Set default skills for this server's system with a .txt file (one skill per line).")
    @app_commands.describe(file="A .txt file with skills, one per line or Skill:Value per line")
    async def setup_defaultskillsfile(self, interaction: discord.Interaction, file: discord.Attachment):
        if not repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can set default skills.", ephemeral=True)
            return
        if not file.filename.endswith('.txt'):
            await interaction.response.send_message("❌ Only .txt files are supported.", ephemeral=True)
            return
        try:
            file_bytes = await file.read()
            content = file_bytes.decode('utf-8')
        except Exception:
            await interaction.response.send_message("❌ Could not decode file. Please ensure it's a UTF-8 encoded .txt file.", ephemeral=True)
            return
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
                    await interaction.response.send_message(f"❌ Invalid value for skill: `{line}`. All values must be integers.", ephemeral=True)
                    return
            else:
                skills_dict[line] = -3
        if not skills_dict:
            await interaction.response.send_message("❌ No skills found in the file.", ephemeral=True)
            return
        system = repositories.server.get_system(str(interaction.guild.id))
        sheet = factories.get_specific_sheet(system)
        if hasattr(sheet, "parse_and_validate_skills"):
            skills_str = ", ".join(f"{k}:{v}" for k, v in skills_dict.items())
            skills_dict = sheet.parse_and_validate_skills(skills_str)
            if not skills_dict:
                await interaction.response.send_message("❌ The skills list is invalid for this system.", ephemeral=True)
                return
        repositories.default_skills.set_default_skills(str(interaction.guild.id), system, skills_dict)
        await interaction.response.send_message(f"✅ Default skills for {system.upper()} updated from file.", ephemeral=True)

    @setup_group.command(name="defaultskills", description="Set default skills for this server's system via text.")
    @app_commands.describe(skills="Skill list, e.g. Admin:0, Gun Combat:1, Pilot:2")
    async def setup_defaultskills(self, interaction: discord.Interaction, skills: str):
        if not repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can set default skills.", ephemeral=True)
            return
        system = repositories.server.get_system(str(interaction.guild.id))
        sheet = factories.get_specific_sheet(system)
        if not hasattr(sheet, "parse_and_validate_skills"):
            await interaction.response.send_message("❌ This system does not support setting default skills.", ephemeral=True)
            return
        skills_dict = sheet.parse_and_validate_skills(skills)
        if not skills_dict:
            await interaction.response.send_message("❌ Invalid format or no skills provided. Example: `Admin:0, Gun Combat:1, Pilot:2`", ephemeral=True)
            return
        repositories.default_skills.set_default_skills(str(interaction.guild.id), system, skills_dict)
        await interaction.response.send_message(f"✅ Default skills for {system.upper()} updated for this server.", ephemeral=True)

    @openai_group.command(
        name="set_api_key",
        description="GM: Set the OpenAI API key used for generating recaps and other AI features"
    )
    @app_commands.describe(api_key="Your OpenAI API key (will be stored securely)")
    async def openai_set_key(self, interaction: discord.Interaction, api_key: str):
        """Set the OpenAI API key for this server"""
        # Check if user has GM permissions
        if not repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can set the API key.", ephemeral=True)
            return
        
        # Simple validation - check if it starts with the usual pattern
        if not api_key.startswith(("sk-", "org-")):
            await interaction.response.send_message("❌ The API key format doesn't look right. It should start with 'sk-'.", ephemeral=True)
            return
            
        # Store the API key
        repositories.api_key.set_openai_key(str(interaction.guild.id), api_key)
        
        await interaction.response.send_message("✅ OpenAI API key set successfully. You can now use AI features like story recaps.", ephemeral=True)

    @openai_group.command(
        name="status",
        description="Check if an OpenAI API key is configured for this server"
    )
    async def openai_status(self, interaction: discord.Interaction):
        """Check the status of the OpenAI API key for this server"""
        api_key_set = repositories.api_key.get_openai_key(str(interaction.guild.id)) is not None
        
        embed = discord.Embed(
            title="🔑 OpenAI API Key Status",
            color=discord.Color.green() if api_key_set else discord.Color.red()
        )
        
        if api_key_set:
            embed.add_field(
                name="Status",
                value="✅ **Set** - AI features are available",
                inline=False
            )
            embed.add_field(
                name="Available Features",
                value="• Story recaps (`/recap generate`)\n• Automatic recaps (`/recap setauto`)\n• Rules questions (`/rules question`)",
                inline=False
            )
        else:
            embed.add_field(
                name="Status", 
                value="❌ **Not set** - AI features are unavailable",
                inline=False
            )
            embed.add_field(
                name="To Enable AI Features",
                value="A GM must set an API key with `/setup openai set_api_key`",
                inline=False
            )
        
        # Add footer based on permissions
        if repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            footer_text = "GM Commands: /setup openai set_api_key [key]"
        else:
            footer_text = "Only GMs can modify the API key"
            
        embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @setup_group.command(
        name="status",
        description="GM: View comprehensive server bot configuration and statistics"
    )
    async def setup_status(self, interaction: discord.Interaction):
        """Display comprehensive server bot settings and statistics"""
        if not repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can view server bot settings.", ephemeral=True)
            return
        
        guild = interaction.guild
        guild_id = str(guild.id)
        
        # Get basic server settings
        system = repositories.server.get_system(guild_id)
        gm_role_id = repositories.server.get_gm_role_id(guild_id)
        player_role_id = repositories.server.get_player_role_id(guild_id)
        
        # Get role objects
        gm_role = guild.get_role(int(gm_role_id)) if gm_role_id else None
        player_role = guild.get_role(int(player_role_id)) if player_role_id else None
        
        # Get current GMs
        gm_members = []
        if gm_role:
            gm_members = [member.display_name for member in gm_role.members]
        
        # Get game state info
        active_scene = repositories.scene.get_active_scene(guild_id)
        all_scenes = repositories.scene.get_all_scenes(guild_id)
        
        # Get initiative info
        initiative_data = None
        for channel in guild.text_channels:
            init_data = repositories.initiative._get_initiative_tracker(guild_id, str(channel.id))
            if init_data and init_data.is_active:
                initiative_data = init_data
                initiative_data.channel_id = channel.id
                break
        
        default_initiative = repositories.server_initiative_defaults.get_default_type(guild_id)
        
        # Get character counts
        all_characters = repositories.character.get_all_characters(guild_id)
        pcs = [c for c in all_characters if not c.is_npc]
        npcs = [c for c in all_characters if c.is_npc]
        
        # Get feature settings
        auto_reminder_settings = repositories.auto_reminder_settings.get_settings(guild_id)
        auto_recap_settings = repositories.auto_recap.get_settings(guild_id)
        
        # Check for default skills
        has_default_skills = repositories.default_skills.get_default_skills(guild_id, system) is not None
        
        # Check API key status (don't show the actual key)
        api_key_set = repositories.api_key.get_openai_key(guild_id) is not None
        
        # Get homebrew rules count
        homebrew_rules_entities = repositories.homebrew.get_all_homebrew_rules(guild_id)
        homebrew_count = len(homebrew_rules_entities)
        
        # Create embed
        embed = discord.Embed(
            title=f"🛠️ Server Bot Configuration: {guild.name}",
            color=discord.Color.blue()
        )
        
        # Basic Configuration
        config_lines = []
        config_lines.append(f"**System:** {system.upper()}")
        config_lines.append(f"**GM Role:** {gm_role.mention if gm_role else '❌ Not set'}")
        config_lines.append(f"**Player Role:** {player_role.mention if player_role else '❌ Not set'}")
        
        if gm_members:
            gm_list = ", ".join(gm_members[:5])  # Show first 5 GMs
            if len(gm_members) > 5:
                gm_list += f" (+{len(gm_members) - 5} more)"
            config_lines.append(f"**Current GMs:** {gm_list}")
        else:
            config_lines.append("**Current GMs:** None")
        
        embed.add_field(
            name="📋 Basic Configuration",
            value="\n".join(config_lines),
            inline=False
        )
        
        # Active Game State
        game_state_lines = []
        if active_scene:
            game_state_lines.append(f"**Active Scene:** {active_scene.name}")
        else:
            game_state_lines.append("**Active Scene:** None")
        
        game_state_lines.append(f"**Total Scenes:** {len(all_scenes)}")
        
        if initiative_data:
            init_channel = interaction.guild.get_channel(int(initiative_data.channel_id))
            game_state_lines.append(f"**Initiative Active:** Yes (#{init_channel.name})")
        else:
            game_state_lines.append("**Initiative Active:** No")
        
        if default_initiative:
            game_state_lines.append(f"**Default Initiative:** {default_initiative}")
        else:
            game_state_lines.append("**Default Initiative:** Not set")
        
        embed.add_field(
            name="🎮 Active Game State",
            value="\n".join(game_state_lines),
            inline=False
        )
        
        # Character Statistics
        char_lines = []
        char_lines.append(f"**Player Characters:** {len(pcs)}")
        char_lines.append(f"**NPCs:** {len(npcs)}")
        char_lines.append(f"**Total Characters:** {len(all_characters)}")
        
        embed.add_field(
            name="👥 Characters",
            value="\n".join(char_lines),
            inline=True
        )
        
        # Feature Configuration
        feature_lines = []
        
        # Auto Reminders
        reminder_status = "✅ Enabled" if auto_reminder_settings.enabled else "❌ Disabled"
        delay_seconds = auto_reminder_settings.delay_seconds
        if delay_seconds >= 86400:
            delay_str = f"{delay_seconds // 86400}d"
        elif delay_seconds >= 3600:
            delay_str = f"{delay_seconds // 3600}h"
        elif delay_seconds >= 60:
            delay_str = f"{delay_seconds // 60}m"
        else:
            delay_str = f"{delay_seconds}s"
        feature_lines.append(f"**Auto Reminders:** {reminder_status} ({delay_str})")
        
        # Auto Recaps
        recap_enabled = auto_recap_settings.enabled
        recap_status = "✅ Enabled" if recap_enabled else "❌ Disabled"
        if recap_enabled:
            recap_channel_id = auto_recap_settings.channel_id
            if recap_channel_id:
                recap_channel = guild.get_channel(int(recap_channel_id))
                channel_mention = recap_channel.mention if recap_channel else "Unknown Channel"
            else:
                channel_mention = "No channel set"
            
            days_interval = auto_recap_settings.days_interval
            feature_lines.append(f"**Auto Recaps:** {recap_status} ({channel_mention}, every {days_interval}d)")
        else:
            feature_lines.append(f"**Auto Recaps:** {recap_status}")
        
        # Default Skills
        skills_status = "✅ Set" if has_default_skills else "❌ Not set"
        feature_lines.append(f"**Default Skills:** {skills_status}")
        
        embed.add_field(
            name="⚙️ Features",
            value="\n".join(feature_lines),
            inline=True
        )
        
        # API Integration & Homebrew
        integration_lines = []
        api_status = "✅ Set" if api_key_set else "❌ Not set"
        integration_lines.append(f"**OpenAI API Key:** {api_status}")
        integration_lines.append(f"**Homebrew Rules:** {homebrew_count}")
        
        embed.add_field(
            name="🔧 Integration & Homebrew",
            value="\n".join(integration_lines),
            inline=False
        )
        
        # Add footer with helpful info
        embed.set_footer(text="Use /setup commands to modify these settings • GM permissions required")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup_setup_commands(bot: commands.Bot):
    await bot.add_cog(SetupCommands(bot))