import discord
from discord.ext import commands
from discord import app_commands
from core.command_decorators import ic_channel_only, player_or_gm_role_required
from data.repositories.repository_factory import repositories
import re

async def can_user_edit_message(guild_id: int, user: discord.User, message: discord.Message) -> bool:
    """Check if user can edit/delete this narrated message."""
    
    # For GM narration, check if user is a GM
    if message.embeds and message.embeds[0].author and message.embeds[0].author.name == "GM":
        return await repositories.server.has_gm_permission(guild_id, user)
        
    # For character messages, check character ownership
    character_name = message.author.display_name if hasattr(message.author, 'display_name') else None
    if not character_name:
        return False
        
    # Try to find the character
    character = repositories.character.get_character_by_name(guild_id, character_name)
    if not character:
        # For temporary NPCs, check if user is GM
        return await repositories.server.has_gm_permission(guild_id, user)
        
    # Check if user can speak as this character (reuse existing logic)
    from commands.narration import can_user_speak_as_character
    return await can_user_speak_as_character(guild_id, user.id, character)

@app_commands.context_menu(name="Edit Narration")
@player_or_gm_role_required()
@ic_channel_only()
async def edit_narration_context(interaction: discord.Interaction, message: discord.Message):
    """Context menu command to edit a narrated message."""
    
    # Check if this is a webhook message from our bot
    if not message.webhook_id:
        await interaction.response.send_message("❌ This is not a narrated message.", ephemeral=True)
        return
        
    # Get the webhook to verify it's ours
    try:
        webhook = await interaction.client.fetch_webhook(message.webhook_id)
        if webhook.name != "RoleByPostCharacters":
            await interaction.response.send_message("❌ This is not a narrated message from this bot.", ephemeral=True)
            return
    except:
        await interaction.response.send_message("❌ Unable to verify message origin.", ephemeral=True)
        return
        
    # Check if user has permission to edit this message
    if not await can_user_edit_message(interaction.guild.id, interaction.user, message):
        await interaction.response.send_message("❌ You can only edit your own narrated messages.", ephemeral=True)
        return
        
    # Show edit modal
    modal = NarrationEditModal(message)
    await interaction.response.send_modal(modal)

class NarrationEditModal(discord.ui.Modal):
    def __init__(self, message: discord.Message):
        super().__init__(title="Edit Narration")
        self.message = message
        
        # Extract current content from embed
        current_content = ""
        if message.embeds and message.embeds[0].description:
            current_content = message.embeds[0].description
            
        self.content_input = discord.ui.TextInput(
            label="Message Content (leave empty to delete)",
            style=discord.TextStyle.paragraph,
            default=current_content,
            max_length=2000,
            required=False
        )
        self.add_item(self.content_input)

    async def on_submit(self, interaction: discord.Interaction):
        """Handle the edit submission."""
        new_content = self.content_input.value.strip()

        try:
            webhook = await interaction.client.fetch_webhook(self.message.webhook_id)
            
            # Delete the old message if content is empty
            if not new_content:
                await webhook.delete_message(self.message.id)
                await interaction.response.send_message("❌ Message deleted.", ephemeral=True)
                return
            
            # Update the embed with new content
            if self.message.embeds:
                embed = self.message.embeds[0].copy()
                embed.description = new_content
                
                await webhook.edit_message(
                    self.message.id,
                    embeds=[embed]
                )
                
                await interaction.response.send_message("✅ Narration updated successfully.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Unable to update message format.", ephemeral=True)
                
        except discord.NotFound:
            await interaction.response.send_message("❌ Message not found.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to edit this message.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error updating message: {str(e)}", ephemeral=True)

async def setup_narration_commands(bot: commands.Bot):
    # Add context menus to the command tree
    bot.tree.add_command(edit_narration_context)