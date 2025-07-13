import discord
from discord.ext import commands
from discord import app_commands

class HelpCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    help_command = app_commands.Group(name="help", description="Help commands for the bot")

    @help_command.command(name="guide", description="Show a guide to the help commands")
    async def help(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📖 Help Commands Guide",
            description=(
                "Use the following commands to get help on specific topics:\n"
                "• `/help getting-started` - General help starting out\n"
                "• `/help characters` - Character management commands\n"
                "• `/help entities` - Entity management commands\n"
                "• `/help rolling` - Rolling commands for dice and checks\n"
                "• `/help scenes` - Scene management commands\n"
                "• `/help initiative` - Initiative management commands\n"
                "• `/help recaps` - Recap generation and management\n"
                "• `/help reminders` - Reminder setup and management\n"
                "• `/help rules` - Rules questions and homebrew management\n"
                "• `/help setup` - Setup and configuration commands\n"
                "• `/help narration` - Character speech and narration commands\n"
                "• `/help ai` - AI-powered commands and features"
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @help_command.command(name="getting-started", description="Show help for getting started with the bot")
    async def help_getting_started(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🚀 Getting Started with RoleByPost",
            description=(
                "Welcome to **RoleByPost**, your Discord bot for play-by-post tabletop RPGs!\n\n"
                "Here's how to get your server up and running:\n\n"
                "1. **Set Up Your Server**\n"
                "   - Use `/setup` commands to configure your RPG system, GM and player roles, and channel types.\n"
                "   - Example: `/setup system [system]`, `/setup gm-role [role]`, `/setup player-role [role]`\n\n"
                "2. **Create Characters and NPCs**\n"
                "   - Players: `/char create pc [name]`\n"
                "   - GMs: `/char create npc [name]`\n"
                "   - Set your active character with `/char switch [name]`\n\n"
                "3. **Start Playing**\n"
                "   - Use `/scene create [name]` to start a scene.\n"
                "   - Speak as your character using `pc::Your message here` or as a GM using `npc::` or `gm::` prefixes.\n"
                "   - Roll dice with `/roll ...` commands.\n\n"
                "4. **Explore More Features**\n"
                "   - Manage inventory and entities with `/entity` commands.\n"
                "   - Track initiative with `/init` commands.\n"
                "   - Use `/recap` for AI-powered story summaries.\n"
                "   - Set reminders with `/reminder` commands.\n\n"
                "For a full walkthrough, see the [Getting Started Wiki](https://github.com/CptConstantine/RoleByPost/wiki/Getting-Started)."
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="characters", description="Show help for character commands")
    async def help_characters(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🧑‍🎤 Character Commands Help",
            description=(
                "Manage player characters, NPCs, and companions.\n"
                "• `/char create pc [name]` - Create a player character\n"
                "• `/char create npc [name]` - Create an NPC (GM only)\n"
                "• `/char list` - List your characters\n"
                "• `/char sheet [name]` - View or edit a character sheet\n"
                "• `/char delete [name]` - Delete a character or NPC\n"
                "See `/char ...` commands for more."
            ),
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="entities", description="Show help for entity commands")
    async def help_entities(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📦 Entity Commands Help",
            description=(
                "Manage items, containers, and other entities.\n"
                "• `/entity create [type] [name]` - Create an entity\n"
                "• `/entity list` - List entities\n"
                "• `/entity view [name]` - View entity details\n"
                "• `/entity rename [name] [new_name]` - Rename an entity\n"
                "• `/entity delete [name]` - Delete an entity\n"
                "See `/entity ...` commands for more."
            ),
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="rolling", description="Show help for rolling commands")
    async def help_rolling(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎲 Rolling Commands Help",
            description=(
                "Roll dice for your character or request rolls from others.\n"
                "• `/roll check [parameters] [difficulty]` - Roll dice for your active character\n"
                "• `/roll custom` - Open the custom roll UI\n"
                "• `/roll request [chars] [parameters]` - (GM) Request rolls from players\n"
                "Roll parameters autocomplete based on your RPG system."
            ),
            color=discord.Color.purple()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="scenes", description="Show help for scene management commands")
    async def help_scenes(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎬 Scene Management Help",
            description=(
                "Manage scenes and organize play-by-post sessions.\n"
                "• `/scene create [name]` - Create a new scene (GM)\n"
                "• `/scene switch [name]` - Switch active scene (GM)\n"
                "• `/scene list` - List all scenes (GM)\n"
                "• `/scene view [name]` - View a scene\n"
                "• `/scene add-npc [npc] [scene]` - Add NPC to scene (GM)\n"
                "See `/scene ...` commands for more."
            ),
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="initiative", description="Show help for initiative commands")
    async def help_initiative(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚔️ Initiative Commands Help",
            description=(
                "Manage initiative order for combat or structured scenes.\n"
                "• `/init start [type] [scene]` - Start initiative (GM)\n"
                "• `/init end` - End initiative (GM)\n"
                "• `/init add-npc [name]` - Add NPC to initiative (GM)\n"
                "• `/init set-default [type]` - Set default initiative type (GM)\n"
                "See `/init ...` commands for more."
            ),
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="recaps", description="Show help for recap commands")
    async def help_recaps(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📝 Recap Commands Help",
            description=(
                "Generate and manage story recaps.\n"
                "• `/recap generate [days] [private]` - Generate a summary of recent events\n"
                "• `/recap set-auto [enabled] [channel] [days_interval]` - (GM) Configure automatic recaps\n"
                "• `/recap auto-status` - Check auto-recap settings\n"
                "See `/recap ...` commands for more."
            ),
            color=discord.Color.teal()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="reminders", description="Show help for reminder commands")
    async def help_reminders(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⏰ Reminder Commands Help",
            description=(
                "Set reminders for players and manage auto-reminders.\n"
                "• `/reminder send [user] [role] [message] [delay]` - (GM) Remind a user or role\n"
                "• `/reminder set [user] [time] [message]` - (GM) Set a reminder\n"
                "• `/reminder set-auto [enabled] [delay]` - (GM) Configure auto-reminders\n"
                "• `/reminder auto-opt-out [opt_out]` - Opt out of auto-reminders\n"
                "See `/reminder ...` commands for more."
            ),
            color=discord.Color.gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="rules", description="Show help for rules commands")
    async def help_rules(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📚 Rules Commands Help",
            description=(
                "Ask rules questions and manage homebrew rules.\n"
                "• `/rules question [prompt]` - Ask about the rules of your system\n"
                "• `/rules homebrew [rule_name] [rule_text]` - (GM) Add or update a homebrew rule\n"
                "• `/rules homebrew-list` - View all homebrew rules\n"
                "• `/rules homebrew-remove [rule_name]` - (GM) Remove a homebrew rule\n"
                "See `/rules ...` commands for more."
            ),
            color=discord.Color.dark_teal()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="setup", description="Show help for setup and configuration commands")
    async def help_setup(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="⚙️ Setup & Configuration Help",
            description=(
                "Configure your server for play-by-post RPGs.\n"
                "• `/setup system [system]` - Set the RPG system (Admin)\n"
                "• `/setup gm-role [role]` - Set the GM role (Admin)\n"
                "• `/setup player-role [role]` - Set the player role (Admin)\n"
                "• `/setup default-skills-file [.txt file]` - Set default skills (GM)\n"
                "• `/setup openai set-api-key [api_key]` - Set OpenAI API key (GM)\n"
                "• `/setup channel type [channel] [type]` - Set channel restrictions (GM)\n"
                "See `/setup ...` commands for more."
            ),
            color=discord.Color.dark_gold()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="narration", description="Show help for character speech and narration")
    async def help_narration(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="📢 Character Speech & Narration Help",
            description="How to speak as characters or narrate as a GM in play-by-post games.",
            color=discord.Color.blue()
        )

        embed.add_field(
            name="Speaking as Your Character",
            value=(
                "**Basic Format:** `pc::Your character's message here`\n"
                "Uses your currently active character. Set with `/character switch`.\n\n"
                "**Speaking as a Specific Character/Companion:**\n"
                "`pc::Character Name::Message content`\n"
                "Example: `pc::Fluffy::*growls menacingly at the stranger*`\n\n"
                "You can speak as:\n"
                "• Your own player characters\n"
                "• Companions you own\n"
                "• Companions controlled by your characters"
            ),
            inline=False
        )

        embed.add_field(
            name="For GMs: Speaking as NPCs",
            value=(
                "**Basic Format**\n"
                "`npc::Character Name::Message content`\n"
                "Example: `npc::Bartender::What'll it be, stranger?`\n\n"
                "**With Custom Display Name**\n"
                "`npc::Character Name::Display Name::Message content`\n"
                "Example: `npc::Mysterious Figure::Hooded Stranger::Keep your voice down!`\n\n"
                "**On-the-fly NPCs**\n"
                "If you use a name that doesn't exist in the database, the bot will still create a temporary character to display the message."
            ),
            inline=False
        )

        embed.add_field(
            name="GM Narration",
            value=(
                "As a GM, you can narrate scenes with a distinctive format:\n"
                "`gm::Your narration text here`\n"
                "Example: `gm::The ground trembles as thunder rumbles overhead. The storm is getting closer.`\n\n"
                "GM narration appears with a purple embed and your avatar as the GM."
            ),
            inline=False
        )

        embed.add_field(
            name="⚠️ Channel Restrictions",
            value=(
                "Narration commands (`pc::`, `npc::`, `gm::`) are **not allowed** in **Out-of-Character (OOC)** channels.\n"
                "Use these commands in **In-Character (IC)** or **Unrestricted** channels to maintain immersion.\n\n"
                "GMs can configure channel types with `/setup channel type`."
            ),
            inline=False
        )

        embed.add_field(
            name="Text Formatting",
            value=(
                "You can use Discord's standard formatting in your messages:\n"
                "• *Italics*: `*text*` or `_text_`\n"
                "• **Bold**: `**text**`\n"
                "• __Underline__: `__text__`\n"
                "• ~~Strikethrough~~: `~~text~~`\n"
                "• `Code`: `` `text` ``\n"
                "• ```Block quotes```: \\```text\\```"
            ),
            inline=False
        )

        embed.add_field(
            name="Character Avatars",
            value=(
                "Set your character's avatar with the command:\n"
                "`/char set-avatar [url]`\n\n"
                "This avatar will appear with your character's messages."
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @help_command.command(name="ai", description="Show help for AI-powered commands and features")
    async def help_ai(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🤖 AI Features & Commands Help",
            description=(
                "The bot uses OpenAI to provide advanced features for your play-by-post RPG server. "
                "Below are the commands that use AI and how they work."
            ),
            color=discord.Color.dark_purple()
        )

        embed.add_field(
            name="Story Recaps",
            value=(
                "• `/recap generate [days] [private]`\n"
                "  Generate a summary of recent story events in the current channel using AI. "
                "You can specify how many days to include and whether the recap is private.\n"
                "• `/recap set-auto [enabled] [channel] [days_interval]`\n"
                "  (GM only) Configure automatic AI-generated recaps to be posted on a schedule.\n"
                "• `/recap auto-status`\n"
                "  Check the current automatic recap settings."
            ),
            inline=False
        )

        embed.add_field(
            name="Rules Questions",
            value=(
                "• `/rules question [prompt]`\n"
                "  Ask a question about the rules of your current RPG system. The bot uses AI to answer, "
                "taking into account any homebrew rules set by the GM."
            ),
            inline=False
        )

        embed.add_field(
            name="Setup Required",
            value=(
                "A GM must set an OpenAI API key with `/setup openai set-api-key [api_key]` before any AI features can be used. "
                "You can check the status with `/setup openai status`."
            ),
            inline=False
        )

        embed.add_field(
            name="Privacy & Usage",
            value=(
                "AI features send relevant messages and context to OpenAI for processing. "
                "No private DMs or server settings are sent."
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup_help_commands(bot: commands.Bot):
    await bot.add_cog(HelpCommands(bot))