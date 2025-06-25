import uuid
import discord
from discord import app_commands
from discord.ext import commands
from core.models import BaseCharacter
from data import repo
import core.factories as factories
import json

async def pc_name_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repo.get_all_characters(interaction.guild.id)
    pcs = [
        c for c in all_chars
        if not c.is_npc and str(c.owner_id) == str(interaction.user.id)
    ]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def pc_name_gm_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repo.get_all_characters(interaction.guild.id)
    pcs = [c for c in all_chars if not c.is_npc]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

class CharacterCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    character_group = app_commands.Group(name="character", description="Character management commands")
    
    create_group = app_commands.Group(name="create", description="Create characters and NPCs", parent=character_group)
    
    @create_group.command(name="pc", description="Create a new player character (PC) with a required name")
    @app_commands.describe(char_name="The name of your new character")
    async def create_pc(self, interaction: discord.Interaction, char_name: str):
        await interaction.response.defer(ephemeral=True)
        system = repo.get_system(interaction.guild.id)
        CharacterClass = factories.get_specific_character(system)
        existing = repo.get_character(interaction.guild.id, char_name)
        if existing:
            await interaction.followup.send(f"❌ A character named `{char_name}` already exists.", ephemeral=True)
            return
        
        # Create a new Character instance using the helper method
        char_id = str(uuid.uuid4())
        character_dict = BaseCharacter.create_base_character(
            id=char_id,
            name=char_name,
            owner_id=interaction.user.id,
            is_npc=False
        )
        
        character = CharacterClass(character_dict)
        character.apply_defaults(is_npc=False, guild_id=interaction.guild.id)
        repo.set_character(interaction.guild.id, character, system=system)
        
        if not repo.get_active_character(interaction.guild.id, interaction.user.id):
            repo.set_active_character(interaction.guild.id, interaction.user.id, char_id)
        await interaction.followup.send(f'📝 Created {system.upper()} character: **{char_name}**.', ephemeral=True)

    @create_group.command(name="npc", description="GM: Create a new NPC with a required name")
    @app_commands.describe(npc_name="The name of the new NPC")
    async def create_npc(self, interaction: discord.Interaction, npc_name: str):
        await interaction.response.defer(ephemeral=True)
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.followup.send("❌ Only GMs can create NPCs.", ephemeral=True)
            return
            
        system = repo.get_system(interaction.guild.id)
        CharacterClass = factories.get_specific_character(system)
        existing = repo.get_character(interaction.guild.id, npc_name)
        if existing:
            await interaction.followup.send(f"❌ An NPC named `{npc_name}` already exists.", ephemeral=True)
            return
            
        # Create a new Character instance using the helper method
        npc_id = str(uuid.uuid4())
        character_dict = BaseCharacter.create_base_character(
            id=npc_id,
            name=npc_name,
            owner_id=interaction.user.id,
            is_npc=True
        )
        
        character = CharacterClass(character_dict)
        character.apply_defaults(is_npc=True, guild_id=interaction.guild.id)
        repo.set_character(interaction.guild.id, character, system=system)
        await interaction.followup.send(f"🤖 Created NPC: **{npc_name}**", ephemeral=True)

    @character_group.command(name="sheet", description="View a character or NPC's full sheet")
    @app_commands.describe(char_name="Leave blank to view your character, or enter an NPC name")
    async def sheet(self, interaction: discord.Interaction, char_name: str = None):
        character = None
        if not char_name:
            character = repo.get_active_character(interaction.guild.id, interaction.user.id)
            if not character:
                await interaction.response.send_message("❌ No active character set. Use `/character switch` to choose one.", ephemeral=True)
                return
        else:
            character = repo.get_character(interaction.guild.id, char_name)
            if not character:
                await interaction.response.send_message("❌ Character not found.", ephemeral=True)
                return

        if character.is_npc and not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only the GM can view NPCs.", ephemeral=True)
            return
        
        system = repo.get_system(interaction.guild.id)
        sheet_obj = factories.get_specific_sheet(system)
        sheet_view = factories.get_specific_sheet_view(system, interaction.user.id, character.id)
        embed = sheet_obj.format_full_sheet(character)
        await interaction.response.send_message(embed=embed, view=sheet_view, ephemeral=True)

    @character_group.command(name="export", description="Export your character or an NPC (if GM) as a JSON file")
    @app_commands.describe(char_name="Leave blank to export your character, or enter an NPC name")
    async def export(self, interaction: discord.Interaction, char_name: str = None):
        await interaction.response.defer(ephemeral=True)
        system = repo.get_system(interaction.guild.id)
        
        if char_name is None:
            all_chars = repo.get_all_characters(interaction.guild.id, system=system)
            character = next((c for c in all_chars if not c.is_npc and str(c.owner_id) == str(interaction.user.id)), None)
            if not character:
                await interaction.followup.send("❌ You don't have a character to export.", ephemeral=True)
                return
        else:
            character = repo.get_character(interaction.guild.id, char_name) if char_name else None
            if character and character.is_npc and not await repo.has_gm_permission(interaction.guild.id, interaction.user):
                await interaction.followup.send("❌ Only the GM can export NPCs.", ephemeral=True)
                return
            elif not character.is_npc:
                await interaction.followup.send("❌ You can only export your own character.", ephemeral=True)
                return
            else:
                character = repo.get_character(interaction.guild.id, char_name)
                if character and str(character.owner_id) != str(interaction.user.id):
                    await interaction.followup.send("❌ You can only export your own character.", ephemeral=True)
                    return
                    
        if not character:
            await interaction.followup.send("❌ Character not found.", ephemeral=True)
            return
            
        if character.is_npc and not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.followup.send("❌ Only the GM can export NPCs.", ephemeral=True)
            return
            
        export_data = character.data
        export_data["system"] = system
        import io
        file_content = json.dumps(export_data, indent=2)
        file = discord.File(io.BytesIO(file_content.encode('utf-8')), filename=f"{character.name}.json")
        await interaction.followup.send(f"Here is your exported character `{character.name}`.", file=file, ephemeral=True)

    @character_group.command(name="import", description="Import a character or NPC from a JSON file. The owner will be set to you")
    @app_commands.describe(file="A .json file exported from this bot")
    async def import_char(self, interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        
        if not file.filename.endswith('.json'):
            await interaction.followup.send("❌ Only .json files are supported.", ephemeral=True)
            return
            
        try:
            file_bytes = await file.read()
            data = json.loads(file_bytes.decode('utf-8'))
        except Exception:
            await interaction.followup.send("❌ Could not decode or parse the file. Make sure it's a valid JSON export from this bot.", ephemeral=True)
            return
            
        system = repo.get_system(interaction.guild.id)
        CharacterClass = factories.get_specific_character(system)
        
        # Extract key fields from imported data
        id = data.get("id") or str(uuid.uuid4())
        name = data.get("name", "Imported Character")
        is_npc = data.get("is_npc", False)
        notes = data.get("notes", [])
        avatar_url = data.get("avatar_url")
        
        # Use the helper method
        character_dict = BaseCharacter.create_base_character(
            id=id,
            name=name,
            owner_id=interaction.user.id,  # Always set owner to current user
            is_npc=is_npc,
            notes=notes,
            avatar_url=avatar_url
        )
        
        # Copy over any system-specific fields
        system_fields = CharacterClass.SYSTEM_SPECIFIC_NPC if is_npc else CharacterClass.SYSTEM_SPECIFIC_CHARACTER
        for key in system_fields:
            if key in data:
                character_dict[key] = data[key]
    
        character = CharacterClass(character_dict)
        character.apply_defaults(is_npc=is_npc, guild_id=interaction.guild.id)
        
        if character.is_npc and not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.followup.send("❌ Only GMs can import NPCs.", ephemeral=True)
            return
            
        repo.set_character(interaction.guild.id, character, system=system)
        await interaction.followup.send(f"✅ Imported {'NPC' if character.is_npc else 'character'} `{character.name}`.", ephemeral=True)

    @character_group.command(name="transfer", description="GM: Transfer a PC to another player")
    @app_commands.describe(
        char_name="Name of the character to transfer",
        new_owner="The user to transfer ownership to"
    )
    @app_commands.autocomplete(char_name=pc_name_gm_autocomplete)
    async def transfer(self, interaction: discord.Interaction, char_name: str, new_owner: discord.Member):
        if not await repo.has_gm_permission(interaction.guild.id, interaction.user):
            await interaction.response.send_message("❌ Only GMs can transfer characters.", ephemeral=True)
            return
            
        character = repo.get_character(interaction.guild.id, char_name)
        if not character or character.is_npc:
            await interaction.response.send_message("❌ PC not found.", ephemeral=True)
            return
            
        character.owner_id = new_owner.id
        system = repo.get_system(interaction.guild.id)
        repo.set_character(interaction.guild.id, character, system=system)
        await interaction.response.send_message(
            f"✅ Ownership of `{char_name}` transferred to {new_owner.display_name}.", ephemeral=True
        )

    @character_group.command(name="switch", description="Set your active character (PC) for this server")
    @app_commands.describe(char_name="The name of your character to set as active")
    @app_commands.autocomplete(char_name=pc_name_autocomplete)
    async def switch(self, interaction: discord.Interaction, char_name: str):
        all_chars = repo.get_all_characters(interaction.guild.id)
        character = next(
            (c for c in all_chars if not c.is_npc and str(c.owner_id) == str(interaction.user.id) and c.name.lower() == char_name.lower()),
            None
        )
        if not character:
            await interaction.response.send_message(f"❌ You don't have a character named `{char_name}`.", ephemeral=True)
            return
            
        repo.set_active_character(interaction.guild.id, interaction.user.id, character.id)
        await interaction.response.send_message(f"✅ `{char_name}` is now your active character.", ephemeral=True)

    @character_group.command(name="setavatar", description="Set your character's avatar image")
    @app_commands.describe(
        avatar_url="URL to an image for your character's avatar"
    )
    async def character_setavatar(self, interaction: discord.Interaction, avatar_url: str):
        """Set an avatar image URL for your character"""
        # Get the active character
        character = repo.get_active_character(interaction.guild.id, interaction.user.id)
        if not character:
            await interaction.response.send_message("❌ You don't have an active character set.", ephemeral=True)
            return
        
        # Basic URL validation
        if not avatar_url.startswith(("http://", "https://")):
            await interaction.response.send_message("❌ Please provide a valid image URL starting with http:// or https://", ephemeral=True)
            return
        
        # Save the avatar URL to the character
        character.avatar_url = avatar_url
        system = repo.get_system(interaction.guild.id)
        repo.set_character(interaction.guild.id, character, system=system)
        
        # Show a preview
        embed = discord.Embed(
            title="Avatar Updated",
            description=f"Avatar for **{character.name}** has been set.",
            color=discord.Color.green()
        )
        embed.set_image(url=avatar_url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @character_group.command(name="narration", description="Get help with character narration formatting")
    async def character_narration_help(self, interaction: discord.Interaction):
        """Display help information about speaking as characters and GM narration"""
        
        embed = discord.Embed(
            title="📢 Character Narration Guide",
            description="How to speak as characters or narrate as a GM in play-by-post games",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Speaking as Your Character",
            value=(
                "Type a message starting with `pc::` followed by what your character says.\n"
                "Example: `pc::I draw my sword and advance cautiously.`\n\n"
                "Your active character will be used. Make sure to set an active character first with `/character switch`."
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
                "`/character setavatar [url]`\n\n"
                "This avatar will appear with your character's messages."
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup_character_commands(bot: commands.Bot):
    await bot.add_cog(CharacterCommands(bot))