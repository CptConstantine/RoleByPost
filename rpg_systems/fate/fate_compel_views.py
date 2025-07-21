from enum import Enum
import discord
from core.base_models import SystemType
from data.repositories.repository_factory import repositories
from core.utils import _get_character_by_name_or_nickname
from rpg_systems.fate.fate_character import FateCharacter

class CompelType(Enum):
    GM = "gm"
    PLAYER = "player"

class CompelView(discord.ui.View):
    def __init__(self, compel_type: CompelType, target_character: str, compeller_user_id: int, 
                 target_user_id: str, message: str, guild_id: int):
        super().__init__(timeout=300)  # 5 minute timeout
        self.compel_type = compel_type
        self.target_character = target_character
        self.compeller_user_id = compeller_user_id
        self.target_user_id = target_user_id
        self.message = message
        self.guild_id = guild_id
        
        # Track decisions
        self.player_decision = None  # "accept" or "reject"
        self.gm_decision = None      # "gm_accept" or "gm_reject" (only for player compels)
        
        self._setup_buttons()
    
    def _setup_buttons(self):
        if self.compel_type == CompelType.GM:
            # GM compel: only player accept/reject buttons
            self.add_item(AcceptCompelButton())
            self.add_item(RejectCompelButton())
            self.add_item(NegotiateCompelButton())
        else:
            # Player compel: player accept/reject + GM worth/not worth buttons
            self.add_item(AcceptCompelButton())
            self.add_item(RejectCompelButton())
            self.add_item(GMApproveButton())
            self.add_item(GMRejectButton())
            self.add_item(NegotiateCompelButton())
    
    async def update_embed(self, interaction: discord.Interaction):
        """Update the embed based on current decisions"""
        embed = self._create_status_embed()
        self._update_button_states()
        
        await interaction.response.edit_message(embed=embed, view=self)
    
    def _create_status_embed(self) -> discord.Embed:
        """Create embed showing current compel status"""
        if self.compel_type == CompelType.GM:
            title = "GM Compel"
            color = 0xff6b35  # Orange
            if self.player_decision == "accept":
                status = f"✅ **{self.target_character}** accepted the compel and gained 1 fate point!"
            elif self.player_decision == "reject":
                status = f"❌ **{self.target_character}** rejected the compel and spent 1 fate point."
            else:
                status = f"⏳ Waiting for **{self.target_character}** to decide..."
        else:
            title = "Player Compel Suggestion"
            color = 0x4dabf7  # Blue
            
            player_status = "⏳ Pending"
            gm_status = "⏳ Pending"
            
            if self.player_decision == "accept":
                player_status = "✅ Accepted"
            elif self.player_decision == "reject":
                player_status = "❌ Rejected"
            
            if self.gm_decision == "gm_accept":
                gm_status = "✅ GM approved"
            elif self.gm_decision == "gm_reject":
                gm_status = "❌ GM rejected"

            if self.is_complete():
                if self.player_decision == "reject":
                    status = f"❌ **{self.target_character}** spent 1 fate point to reject the compel."
                elif self.gm_decision == "gm_reject":
                    status = f"❌ GM rejected the compel."
                else:
                    status = f"✅ Compel approved! **{self.target_character}** gained 1 fate point!"
            else:
                status = f"Player Decision: {player_status} | GM Decision: {gm_status}"
        
        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="Character", value=self.target_character, inline=True)
        embed.add_field(name="Compel", value=self.message, inline=False)
        embed.set_footer(text=status)
        
        return embed
    
    def _update_button_states(self):
        """Update button enabled/disabled states based on decisions"""
        for item in self.children:
            if isinstance(item, (AcceptCompelButton, RejectCompelButton)):
                item.disabled = self.player_decision is not None
            elif isinstance(item, (GMApproveButton, GMRejectButton)):
                item.disabled = self.gm_decision is not None
            
            # Disable all buttons when complete
            if self.is_complete():
                item.disabled = True
    
    def is_complete(self) -> bool:
        """Check if all required decisions have been made"""
        if self.compel_type == CompelType.GM:
            return self.player_decision is not None
        else:
            return self.player_decision is not None and self.gm_decision is not None
    
    async def resolve_compel(self, interaction: discord.Interaction):
        """Apply the final compel result based on all decisions"""
        character = await _get_character_by_name_or_nickname(self.guild_id, self.target_character)
        if not character:
            return
        
        from .fate_character import FateCharacter
        if not isinstance(character, FateCharacter):
            return
        
        success = False
        
        if self.compel_type == CompelType.GM:
            if self.player_decision == "accept":
                success = await self._award_fate_point(character)
            elif self.player_decision == "reject":
                success = await self._spend_fate_point(character)
        else:
            # Player compel - only award if both player accepted and GM says worth FP
            if self.player_decision == "accept" and self.gm_decision == "gm_accept":
                success = await self._award_fate_point(character)
            else:
                success = True  # No FP change needed
        
        if not success and self.player_decision == "reject":
            # Failed to spend fate point - probably insufficient
            embed = discord.Embed(
                title="❌ Insufficient Fate Points",
                description=f"**{self.target_character}** doesn't have enough fate points to reject this compel.",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    async def _award_fate_point(self, character: FateCharacter) -> bool:
        """Award 1 fate point to character"""
        try:
            character.fate_points = character.fate_points + 1
            repositories.entity.upsert_entity(self.guild_id, character, SystemType.FATE)
            return True
        except Exception:
            return False

    async def _spend_fate_point(self, character: FateCharacter) -> bool:
        """Spend 1 fate point from character"""
        if character.fate_points <= 0:
            return False
        
        try:
            character.fate_points = character.fate_points - 1
            repositories.entity.upsert_entity(self.guild_id, character, SystemType.FATE)
            return True
        except Exception:
            return False

class AcceptCompelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Player Accept", style=discord.ButtonStyle.green, emoji="✅")
    
    async def callback(self, interaction: discord.Interaction):
        view: CompelView = self.view
        
        # Check if user is the target player
        if str(interaction.user.id) != view.target_user_id:
            await interaction.response.send_message("❌ Only the compelled player can accept or reject this compel.", ephemeral=True)
            return
        
        view.player_decision = "accept"
        await view.update_embed(interaction)
        
        if view.is_complete():
            await view.resolve_compel(interaction)

class RejectCompelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Player Reject", style=discord.ButtonStyle.red, emoji="❌")
    
    async def callback(self, interaction: discord.Interaction):
        view: CompelView = self.view
        
        # Check if user is the target player
        if str(interaction.user.id) != view.target_user_id:
            await interaction.response.send_message("❌ Only the compelled player can accept or reject this compel.", ephemeral=True)
            return
        
        view.player_decision = "reject"
        await view.update_embed(interaction)
        
        if view.is_complete():
            await view.resolve_compel(interaction)

class GMApproveButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="GM Approve", style=discord.ButtonStyle.primary, emoji="⭐")
    
    async def callback(self, interaction: discord.Interaction):
        view: CompelView = self.view
        
        # Check if user is GM
        is_gm = await repositories.server.has_gm_permission(view.guild_id, interaction.user)
        if not is_gm:
            await interaction.response.send_message("❌ Only GMs can do this.", ephemeral=True)
            return
        
        view.gm_decision = "gm_accept"
        await view.update_embed(interaction)
        
        if view.is_complete():
            await view.resolve_compel(interaction)

class GMRejectButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="GM Reject", style=discord.ButtonStyle.secondary, emoji="🚫")
    
    async def callback(self, interaction: discord.Interaction):
        view: CompelView = self.view
        
        # Check if user is GM
        is_gm = await repositories.server.has_gm_permission(view.guild_id, interaction.user)
        if not is_gm:
            await interaction.response.send_message("❌ Only GMs can do this.", ephemeral=True)
            return
        
        view.gm_decision = "gm_reject"
        await view.update_embed(interaction)
        
        if view.is_complete():
            await view.resolve_compel(interaction)

class NegotiateCompelButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Negotiate Compel", style=discord.ButtonStyle.blurple, emoji="🤝")
    
    async def callback(self, interaction: discord.Interaction):
        view: CompelView = self.view
        modal = NegotiationModal(view)
        await interaction.response.send_modal(modal)

class NegotiationModal(discord.ui.Modal, title="Negotiate Compel"):
    message = discord.ui.TextInput(label="Suggest a change to the compel", style=discord.TextStyle.long, required=True, max_length=500)

    def __init__(self, parent_view: CompelView):
        super().__init__()
        self.parent_view = parent_view

    async def on_submit(self, interaction: discord.Interaction):
        self.parent_view.message = self.parent_view.message + f"\n{interaction.user.display_name}: {self.message.value}"
        await self.parent_view.update_embed(interaction)
        
        mentions = []
        
        # Add target player
        target_user = interaction.guild.get_member(int(self.parent_view.target_user_id))
        if target_user and target_user.id != interaction.user.id:
            mentions.append(target_user.mention)
        
        # Add compeller if different from current user
        compeller = interaction.guild.get_member(self.parent_view.compeller_user_id)
        if compeller and compeller.id != interaction.user.id:
            mentions.append(compeller.mention)
        
        # Add GMs for player compels
        if self.parent_view.compel_type == CompelType.PLAYER:
            gm_role_id = await repositories.server.get_gm_role_id(interaction.guild.id)
            for member in interaction.guild.members:
                if any(role.id in gm_role_id for role in member.roles):
                    if member.id != interaction.user.id and member.mention not in mentions:
                        mentions.append(member.mention)
        
        # Send timed notification if there are people to mention
        if mentions:
            mention_text = " ".join(mentions)
            await interaction.followup.send(
                f"{mention_text} - Compel negotiation update from {interaction.user.display_name}",
                delete_after=60
            )