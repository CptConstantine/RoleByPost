import discord
from discord.ext import commands
from discord import app_commands
import openai
from core import command_decorators
from core.base_models import SystemType
from core.command_decorators import channel_restricted, gm_role_required, no_ic_channels, player_or_gm_role_required
from data.repositories.repository_factory import repositories

# Autocomplete function for homebrew rule names
async def homebrew_rule_autocomplete(interaction: discord.Interaction, current: str):
    """
    Provide autocomplete suggestions for homebrew rule names.
    
    Args:
        interaction: Discord interaction object
        current: Current text being typed
        
    Returns:
        List of app_commands.Choice objects for autocomplete
    """
    try:
        homebrew_rules = repositories.homebrew.get_all_homebrew_rules(str(interaction.guild.id))
        options = [rule.rule_name for rule in homebrew_rules if current.lower() in rule.rule_name.lower()]
        return [app_commands.Choice(name=name, value=name) for name in options[:25]]
    except Exception:
        return []

class RulesCommands(commands.Cog):
    """
    Commands for asking rules questions and managing homebrew rules.
    Integrates with OpenAI to provide AI-powered answers about RPG systems.
    """
    
    def __init__(self, bot):
        self.bot = bot
    
    rules_group = app_commands.Group(name="rules", description="Commands for rules questions and homebrew management")

    @rules_group.command(
        name="question", 
        description="Ask a question about the rules of your current RPG system"
    )
    @app_commands.describe(
        prompt="Your rules question (e.g., 'How does combat initiative work?')"
    )
    @command_decorators.no_ic_channels()
    @player_or_gm_role_required()
    @no_ic_channels()
    async def rules_question(self, interaction: discord.Interaction, prompt: str):
        """
        Handle rules questions by querying OpenAI with system context and homebrew rules.
        
        Args:
            interaction: Discord interaction object
            prompt: The user's rules question
        """
        # Check if API key is configured
        api_key = repositories.api_key.get_openai_key(str(interaction.guild.id))
        if not api_key:
            await interaction.response.send_message(
                "❌ No API key has been set. A GM must set one with `/setup openai set_api_key`.", 
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        
        try:
            # Get system and homebrew context
            system = repositories.server.get_system(str(interaction.guild.id))
            homebrew_rules_entities = repositories.homebrew.get_all_homebrew_rules(str(interaction.guild.id))
            
            # Convert to dictionary for compatibility with existing code
            homebrew_rules = {rule.rule_name: rule.rule_text for rule in homebrew_rules_entities}
            
            # Generate response using OpenAI
            response = await self._generate_rules_response(prompt, system, homebrew_rules, api_key)
            
            # Create embed for the response
            embed = discord.Embed(
                title="📚 Rules Answer",
                description=response,
                color=discord.Color.blue()
            )
            embed.set_footer(text=f"System: {system.value.upper()} | Asked by {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error generating rules response: {str(e)}", 
                ephemeral=True
            )

    @rules_group.command(
        name="homebrew",
        description="GM: Add or update a homebrew rule for this server"
    )
    @app_commands.describe(
        rule_name="Short name for the rule (e.g., 'critical_hits')",
        rule_text="The homebrew rule text or clarification"
    )
    @command_decorators.no_ic_channels()
    @gm_role_required()
    @no_ic_channels()
    async def rules_homebrew(
        self, 
        interaction: discord.Interaction, 
        rule_name: str, 
        rule_text: str
    ):
        """
        Allow GMs to add or update homebrew rules that will be used as context for AI responses.
        
        Args:
            interaction: Discord interaction object
            rule_name: Identifier for the homebrew rule
            rule_text: The actual rule content
        """
        # Validate inputs
        if len(rule_name) > 100:
            await interaction.response.send_message(
                "❌ Rule name must be 100 characters or less.", 
                ephemeral=True
            )
            return
            
        if len(rule_text) > 2000:
            await interaction.response.send_message(
                "❌ Rule text must be 2000 characters or less.", 
                ephemeral=True
            )
            return
        
        # Save the homebrew rule
        repositories.homebrew.upsert_rule(str(interaction.guild.id), rule_name, rule_text)
        
        await interaction.response.send_message(
            f"✅ Homebrew rule '{rule_name}' has been saved.", 
            ephemeral=True
        )

    @rules_group.command(
        name="homebrew-list",
        description="View all homebrew rules for this server"
    )
    @command_decorators.no_ic_channels()
    @player_or_gm_role_required()
    @no_ic_channels()
    async def rules_homebrew_list(self, interaction: discord.Interaction):
        """
        Display all homebrew rules for the current server.
        
        Args:
            interaction: Discord interaction object
        """
        homebrew_rules_entities = repositories.homebrew.get_all_homebrew_rules(str(interaction.guild.id))
        
        if not homebrew_rules_entities:
            await interaction.response.send_message(
                "📚 No homebrew rules have been set for this server.", 
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📚 Homebrew Rules",
            color=discord.Color.green()
        )
        
        # Add each rule as a field (truncate if too long)
        for rule in homebrew_rules_entities:
            display_text = rule.rule_text if len(rule.rule_text) <= 1024 else rule.rule_text[:1021] + "..."
            embed.add_field(
                name=rule.rule_name,
                value=display_text,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @rules_group.command(
        name="home-brew-remove",
        description="GM: Remove a homebrew rule from this server"
    )
    @app_commands.describe(
        rule_name="Name of the homebrew rule to remove"
    )
    @app_commands.autocomplete(rule_name=homebrew_rule_autocomplete)
    @gm_role_required()
    @no_ic_channels()
    async def rules_homebrew_remove(self, interaction: discord.Interaction, rule_name: str):
        """
        Allow GMs to remove homebrew rules.
        
        Args:
            interaction: Discord interaction object
            rule_name: Name of the rule to remove
        """
        # Check if rule exists and remove it
        success = repositories.homebrew.remove_rule(str(interaction.guild.id), rule_name)
        if not success:
            await interaction.response.send_message(
                f"❌ No homebrew rule named '{rule_name}' found.", 
                ephemeral=True
            )
            return
        
        await interaction.response.send_message(
            f"✅ Homebrew rule '{rule_name}' has been removed.", 
            ephemeral=True
        )

    async def _generate_rules_response(
        self, 
        prompt: str, 
        system: SystemType, 
        homebrew_rules: dict, 
        api_key: str
    ) -> str:
        """
        Generate a rules response using OpenAI API with system and homebrew context.
        
        Args:
            prompt: The user's rules question
            system: The RPG system being used
            homebrew_rules: Dictionary of homebrew rules for context
            api_key: OpenAI API key
            
        Returns:
            str: The AI-generated response
        """
        # Build system context
        system_context = self._get_system_context(system)
        
        # Build homebrew context
        homebrew_context = ""
        if homebrew_rules:
            homebrew_context = "\n\nHOMEBREW RULES AND CLARIFICATIONS:\n"
            for rule_name, rule_text in homebrew_rules.items():
                homebrew_context += f"- {rule_name}: {rule_text}\n"
        
        # Construct the full prompt
        full_context = f"""You are an expert on tabletop RPG rules, specifically {system_context}. 
        
You should answer rules questions accurately based on the official rules of the system. 
When homebrew rules are provided, prioritize them over official rules if there's a conflict.
Be concise but thorough, and cite specific rule sections when possible.
If you're unsure about a rule, say so rather than guessing.
Only answer using content from the official SRD. Do not reference setting-specific content or copyrighted examples.

{homebrew_context}

Question: {prompt}"""

        # Make API request
        try:
            client = openai.OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a helpful RPG rules expert."},
                    {"role": "user", "content": full_context}
                ],
                max_tokens=1000,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")

    def _get_system_context(self, system: SystemType) -> str:
        """
        Get appropriate context description for the RPG system.
        
        Args:
            system: The system identifier (e.g., 'fate', 'mgt2e', 'generic')
            
        Returns:
            str: Description of the system for AI context
        """
        system_contexts = {
            SystemType.FATE: 'Fate Core, Fate Condensed, and Fate Accelerated RPG systems',
            SystemType.MGT2E: 'Mongoose Traveller 2nd Edition RPG system',
            SystemType.GENERIC: 'Generic tabletop RPG system with no specific rules'
        }

        return system_contexts.get(system, 'Generic tabletop RPG system with no specific rules')

async def setup_rules_commands(bot: commands.Bot):
    """
    Setup function to add the RulesCommands cog to the bot.
    
    Args:
        bot: The Discord bot instance
    """
    await bot.add_cog(RulesCommands(bot))