import discord
from discord.ext import commands
from discord import app_commands
from core.utils import _get_character_by_name_or_nickname
from data.repositories.repository_factory import repositories

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

@app_commands.context_menu(name="View Character Sheet")
async def view_character_sheet_from_narration_context(interaction: discord.Interaction, message: discord.Message):
    """Context menu command to view a character sheet."""
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

    # Check if user has permission to view this message
    if not await can_user_edit_message(interaction.guild.id, interaction.user, message):
        await interaction.response.send_message("❌ You can only view your own narrated messages.", ephemeral=True)
        return

    # Show character sheet
    character_name = message.author.display_name if hasattr(message.author, 'display_name') else None
    if character_name:
        character = await _get_character_by_name_or_nickname(interaction.guild.id, character_name)
        if character:
            is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
            embed = character.format_full_sheet(interaction.guild.id, is_gm=is_gm)
            view = character.get_sheet_edit_view(interaction.user.id, is_gm=is_gm)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            return

    await interaction.response.send_message("❌ Character sheet not found.", ephemeral=True)

class NarrationEditModal(discord.ui.Modal):
    def __init__(self, message: discord.Message):
        super().__init__(title="Edit Narration")
        self.message = message
        
        # Extract current content from embed
        current_content = ""
        if message.embeds and message.embeds[0].description:
            current_content = message.embeds[0].description
        else:
            # Fallback to message content if no embed
            current_content = message.content
            
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
                # For threads, we need to specify the thread when deleting
                if isinstance(self.message.channel, discord.Thread):
                    await webhook.delete_message(self.message.id, thread=self.message.channel)
                else:
                    await webhook.delete_message(self.message.id)
                await interaction.response.send_message("❌ Message deleted.", ephemeral=True)
                return
            
            # Update the message with new content
            edit_params = {}
            
            # Handle embed format (typical for character narration)
            if self.message.embeds:
                embed = self.message.embeds[0].copy()
                embed.description = new_content
                edit_params['embeds'] = [embed]
            else:
                # Fallback to content editing for non-embed messages
                edit_params['content'] = new_content
            
            # For threads, specify the thread parameter
            if isinstance(self.message.channel, discord.Thread):
                edit_params['thread'] = self.message.channel
            
            await webhook.edit_message(self.message.id, **edit_params)
            await interaction.response.send_message("✅ Narration updated successfully.", ephemeral=True)
                
        except discord.NotFound:
            await interaction.response.send_message("❌ Message not found.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to edit this message.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error updating message: {str(e)}", ephemeral=True)

async def setup_narration_context_menu_commands(bot: commands.Bot):
    # Add context menus to the command tree
    bot.tree.add_command(edit_narration_context)
    bot.tree.add_command(view_character_sheet_from_narration_context)