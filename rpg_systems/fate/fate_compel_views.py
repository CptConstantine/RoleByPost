from enum import Enum
import discord
from core.base_models import SystemType
from core.shared_views import embed_to_text
from data.repositories.repository_factory import repositories
from core.utils import _get_character_by_name_or_nickname, _get_gm_mention
from rpg_systems.fate.fate_character import FateCharacter


def _truncate_text(text: str, limit: int = 4000) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"

class CompelType(Enum):
    GM = "gm"
    PLAYER = "player"

class CompelView(discord.ui.View):
    def __init__(self, compel_type: CompelType, target_character: str, compeller_user_id: int, 
                 target_user_id: str, message: str, guild_id: int):
        super().__init__(timeout=60 * 60 * 24 * 7)  # 1 week timeout
        self.compel_type = compel_type
        self.target_character = target_character
        self.compeller_user_id = compeller_user_id
        self.target_user_id = target_user_id
        self.message = message
        self.negotiation_message = ""
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
    
    async def update_message(self, interaction: discord.Interaction, message: str = None):
        """Update the embed based on current decisions"""
        # Mention different users based on interaction
        mentions = await self.get_compel_interaction_mentions(interaction)
        
        message_content = ""
        if mentions:
            message_content = ", ".join(mentions)
        if message:
            message_content += f"\n**Update:** {message}"
        embed = self.create_status_embed()
        self._update_button_states()
        
        # Delete the original message to avoid clutter
        await interaction.channel.send(content=message_content, embed=embed, view=self)
        await interaction.message.delete()
        await interaction.response.defer()

    async def get_compel_interaction_mentions(self, interaction: discord.Interaction) -> list[str]:
        """Get mentions based on the interaction context"""
        mentions = []
        if self.compel_type == CompelType.GM:
            if interaction.user.id == self.compeller_user_id:
                # Mention the target user if the interaction is from the compeller
                target_user = interaction.guild.get_member(int(self.target_user_id))
                if target_user:
                    mentions.append(target_user.mention)
            elif str(interaction.user.id) == str(self.target_user_id):
                # Mention the GM role if the interaction is from the target player
                gm_mention = await _get_gm_mention(interaction)
                if gm_mention:
                    mentions.append(gm_mention)
        elif self.compel_type == CompelType.PLAYER:
            if interaction.user.id == self.compeller_user_id:
                # Mention the GM and target player if the interaction is from the compeller
                target_user = interaction.guild.get_member(int(self.target_user_id))
                if target_user:
                    mentions.append(target_user.mention)
                gm_mention = await _get_gm_mention(interaction)
                if gm_mention:
                    mentions.append(gm_mention)
            elif str(interaction.user.id) == str(self.target_user_id):
                # Mention the GM if the interaction is from the target player
                gm_mention = await _get_gm_mention(interaction)
                if gm_mention:
                    mentions.append(gm_mention)
            elif await repositories.server.has_gm_permission(self.guild_id, interaction.user):
                # If the interaction is from a GM, mention the target player
                target_user = interaction.guild.get_member(int(self.target_user_id))
                if target_user:
                    mentions.append(target_user.mention)
        return mentions
    
    def create_status_embed(self) -> discord.Embed:
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
        embed.add_field(name="Negotiation", value=self.negotiation_message or "None yet.", inline=False)
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


class CompelViewV2(discord.ui.LayoutView):
    def __init__(self, compel_type: CompelType, target_character: str, compeller_user_id: int,
                 target_user_id: str, message: str, guild_id: int, announcement_message: str = None,
                 status_message: str = None):
        super().__init__(timeout=60 * 60 * 24 * 7)
        self.compel_type = compel_type
        self.target_character = target_character
        self.compeller_user_id = compeller_user_id
        self.target_user_id = target_user_id
        self.message = message
        self.negotiation_message = ""
        self.guild_id = guild_id
        self.announcement_message = announcement_message
        self.status_message = status_message

        self.player_decision = None
        self.gm_decision = None
        self._build_layout()

    def _build_layout(self):
        self.clear_items()

        if self.announcement_message:
            self.add_item(
                discord.ui.Container(
                    discord.ui.TextDisplay(_truncate_text(self.announcement_message, 1500)),
                    accent_colour=discord.Colour.blurple(),
                )
            )

        if self.status_message:
            self.add_item(
                discord.ui.Container(
                    discord.ui.TextDisplay(_truncate_text(self.status_message, 1500)),
                    accent_colour=discord.Colour.green(),
                )
            )

        self.add_item(
            discord.ui.Container(
                discord.ui.TextDisplay(_truncate_text(embed_to_text(self.create_status_embed()), 3000)),
                accent_colour=discord.Colour.orange() if self.compel_type == CompelType.GM else discord.Colour.blue(),
            )
        )
        self.add_item(discord.ui.Separator())

        if self.compel_type == CompelType.GM:
            decision_row = discord.ui.ActionRow()

            accept_button = AcceptCompelButton()
            accept_button.disabled = self.player_decision is not None or self.is_complete()
            decision_row.add_item(accept_button)

            reject_button = RejectCompelButton()
            reject_button.disabled = self.player_decision is not None or self.is_complete()
            decision_row.add_item(reject_button)
            self.add_item(decision_row)

            negotiate_row = discord.ui.ActionRow()
            negotiate_button = NegotiateCompelButton()
            negotiate_button.disabled = self.is_complete()
            negotiate_row.add_item(negotiate_button)
            self.add_item(negotiate_row)
        else:
            player_row = discord.ui.ActionRow()

            accept_button = AcceptCompelButton()
            accept_button.disabled = self.player_decision is not None or self.is_complete()
            player_row.add_item(accept_button)

            reject_button = RejectCompelButton()
            reject_button.disabled = self.player_decision is not None or self.is_complete()
            player_row.add_item(reject_button)

            negotiate_button = NegotiateCompelButton()
            negotiate_button.disabled = self.is_complete()
            player_row.add_item(negotiate_button)
            self.add_item(player_row)

            gm_row = discord.ui.ActionRow()
            approve_button = GMApproveButton()
            approve_button.disabled = self.gm_decision is not None or self.is_complete()
            gm_row.add_item(approve_button)

            reject_gm_button = GMRejectButton()
            reject_gm_button.disabled = self.gm_decision is not None or self.is_complete()
            gm_row.add_item(reject_gm_button)
            self.add_item(gm_row)

    async def update_message(self, interaction: discord.Interaction, message: str = None):
        mentions = await self.get_compel_interaction_mentions(interaction)
        lines = []
        if mentions:
            lines.append(", ".join(mentions))
        if message:
            lines.append(f"**Update:** {message}")
        self.status_message = "\n".join(lines) if lines else None
        self._build_layout()
        await interaction.response.edit_message(content=None, embed=None, view=self)

    async def get_compel_interaction_mentions(self, interaction: discord.Interaction) -> list[str]:
        return await CompelView.get_compel_interaction_mentions(self, interaction)

    def create_status_embed(self) -> discord.Embed:
        return CompelView.create_status_embed(self)

    def is_complete(self) -> bool:
        return CompelView.is_complete(self)

    async def resolve_compel(self, interaction: discord.Interaction):
        await CompelView.resolve_compel(self, interaction)

    async def _award_fate_point(self, character: FateCharacter) -> bool:
        return await CompelView._award_fate_point(self, character)

    async def _spend_fate_point(self, character: FateCharacter) -> bool:
        return await CompelView._spend_fate_point(self, character)

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
        await view.update_message(interaction, message="Player accepted the compel!")
        
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
        await view.update_message(interaction, message="Player rejected the compel.")

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
        await view.update_message(interaction, message="GM approved the compel!")

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
        await view.update_message(interaction, message="GM rejected the compel.")

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
        self.parent_view.negotiation_message = self.parent_view.negotiation_message + f"\n{interaction.user.display_name}: {self.message.value}"
        await self.parent_view.update_message(interaction, message=f"Negotiation update from {interaction.user.display_name}")