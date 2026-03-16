import discord
from discord import ui
from discord.ext import commands
from core.base_models import SystemType
from core.scene_views import BasePinnableSceneView, BasePinnableSceneViewV2, PlaceholderPersistentButton, SceneNotesButton
from rpg_systems.fate.aspect import Aspect
from data.repositories.repository_factory import repositories


SYSTEM = SystemType.FATE


def _build_fate_scene_content(guild_id, scene_id, is_gm: bool):
    scene = repositories.scene.find_by_id('scene_id', scene_id)
    if not scene:
        return discord.Embed(
            title="❌ Scene Not Found",
            description="This scene no longer exists.",
            color=discord.Color.red()
        ), "❌ **SCENE ERROR** ❌"

    notes = repositories.scene_notes.get_scene_notes(str(guild_id), str(scene_id))

    game_aspects = repositories.fate_game_aspects.get_game_aspects(str(guild_id)) or []
    scene_aspects = repositories.fate_aspects.get_aspects(str(guild_id), str(scene_id)) or []
    scene_zones = repositories.fate_zones.get_zones(str(guild_id), str(scene_id)) or []
    zone_aspects = repositories.fate_zone_aspects.get_all_zone_aspects_for_scene(str(guild_id), str(scene_id)) or {}

    embed = discord.Embed(
        title=f"🎭 {('Current' if scene.is_active else 'Inactive')} Scene: {scene.name}",
        color=discord.Color.purple() if scene.is_active else discord.Color.dark_grey()
    )

    description = ""
    if notes:
        description += f"**Notes:**\n{notes}\n\n"

    if game_aspects:
        description += "**Game Aspects:**\n"
        hidden_game_aspect_count = 0

        for aspect in game_aspects:
            aspect_str = aspect.get_short_aspect_string(is_gm=is_gm)
            if aspect_str:
                description += f"• {aspect_str}\n"
            else:
                hidden_game_aspect_count += 1

        if hidden_game_aspect_count > 0 and not is_gm:
            description += f"• *{hidden_game_aspect_count} hidden aspect{'s' if hidden_game_aspect_count > 1 else ''}*\n"
        description += "\n"

    if scene_aspects:
        description += "**Scene Aspects:**\n"
        hidden_scene_aspect_count = 0

        for aspect in scene_aspects:
            aspect_str = aspect.get_short_aspect_string(is_gm=is_gm)
            if aspect_str:
                description += f"• {aspect_str}\n"
            else:
                hidden_scene_aspect_count += 1

        if hidden_scene_aspect_count > 0 and not is_gm:
            description += f"• *{hidden_scene_aspect_count} hidden aspect{'s' if hidden_scene_aspect_count > 1 else ''}*\n"
        description += "\n"

    if scene_zones:
        description += "**Zones:**\n"
        for zone in scene_zones:
            zone_line = f"• **{zone}**"
            if zone in zone_aspects and zone_aspects[zone]:
                zone_aspect_strings = []
                hidden_zone_aspect_count = 0

                for aspect in zone_aspects[zone]:
                    aspect_str = aspect.get_short_aspect_string(is_gm=is_gm)
                    if aspect_str:
                        zone_aspect_strings.append(aspect_str)
                    else:
                        hidden_zone_aspect_count += 1

                if zone_aspect_strings:
                    zone_line += f" - {', '.join(zone_aspect_strings)}"

                if hidden_zone_aspect_count > 0 and not is_gm:
                    if zone_aspect_strings:
                        zone_line += f", *{hidden_zone_aspect_count} hidden*"
                    else:
                        zone_line += f" - *{hidden_zone_aspect_count} hidden aspect{'s' if hidden_zone_aspect_count > 1 else ''}*"

            description += zone_line + "\n"
        description += "\n"

    npc_ids = repositories.scene_npc.get_scene_npc_ids(str(guild_id), str(scene_id))
    lines = []
    for npc_id in npc_ids:
        npc = repositories.entity.get_by_id(str(npc_id))
        if npc:
            lines.append(npc.format_npc_scene_entry(is_gm=is_gm))

    if lines:
        description += "**NPCs:**\n"
        description += "\n\n".join(lines)
    else:
        description += "📭 No NPCs are currently in this scene."

    embed.description = description

    if scene.is_active:
        embed.set_footer(text="Scene view will update automatically when the scene changes.")
        content = "🎭 **CURRENT SCENE** 🎭"
    else:
        embed.set_footer(text="This is not the active scene. Use /scene switch to make it active.")
        content = "🎭 **INACTIVE SCENE** 🎭"

    if scene.image_url:
        embed.set_image(url=scene.image_url)

    return embed, content

class FateSceneView(BasePinnableSceneView):
    """Fate-specific scene view with aspects and zones"""
    
    def __init__(self, guild_id: int = None, scene_id: int = None, is_gm: bool = False, message_id: int = None):
        super().__init__(guild_id, scene_id, is_gm, message_id)
        
        if not self.is_initialized:
            # For persistent view registration, add placeholder buttons with the correct custom_ids
            self.add_item(PlaceholderPersistentButton("edit_aspects"))
            self.add_item(PlaceholderPersistentButton("edit_zones"))
            self.add_item(PlaceholderPersistentButton("edit_game_aspects"))
            self.add_item(PlaceholderPersistentButton("manage_npcs"))
            return

    async def create_scene_content(self):
        return _build_fate_scene_content(self.guild_id, self.scene_id, self.is_gm)
        
    def build_view_components(self):
        # Add all buttons regardless of GM status - the interaction_check will handle permissions
        self.clear_items()
        self.add_item(SceneNotesButton(self))
        self.add_item(EditGameAspectsButton(self))
        self.add_item(EditSceneAspectsButton(self))
        self.add_item(EditZonesButton(self))
        self.add_item(ManageNPCsButton(self))


class FateSceneViewV2(BasePinnableSceneViewV2):
    """Components v2 Fate scene view with aspects, zones, and NPC management."""

    def __init__(self, guild_id=None, channel_id=None, scene_id=None, message_id=None, status_message: str = None):
        super().__init__(guild_id=guild_id, channel_id=channel_id, scene_id=scene_id, message_id=message_id, status_message=status_message)

        if not self.is_initialized:
            for row in self.build_action_rows():
                self.add_item(row)

    async def create_scene_content(self):
        return _build_fate_scene_content(self.guild_id, self.scene_id, self.is_gm)

    def build_action_rows(self) -> list[ui.ActionRow]:
        primary_row = ui.ActionRow()
        primary_row.add_item(SceneNotesButton(self))
        primary_row.add_item(EditGameAspectsButton(self))
        primary_row.add_item(EditSceneAspectsButton(self))
        primary_row.add_item(EditZonesButton(self))

        secondary_row = ui.ActionRow()
        secondary_row.add_item(ManageNPCsButton(self))
        return [primary_row, secondary_row]


class EditGameAspectsButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Edit Game Aspects", style=discord.ButtonStyle.secondary, custom_id="edit_game_aspects", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit game aspects.", ephemeral=True)
            return
            
        # Open modal for editing game aspects
        await interaction.response.send_modal(EditGameAspectsModal(self.parent_view))


class EditSceneAspectsButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Edit Scene Aspects", style=discord.ButtonStyle.secondary, custom_id="edit_aspects", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit scene aspects.", ephemeral=True)
            return
            
        # Open modal for editing scene aspects
        await interaction.response.send_modal(EditSceneAspectsModal(self.parent_view))


class EditZonesButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Edit Zones", style=discord.ButtonStyle.secondary, custom_id="edit_zones", row=0)
        self.parent_view = parent_view

    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can edit zones.", ephemeral=True)
            return
            
        # Open zone selection for editing
        if isinstance(self.parent_view, ui.LayoutView):
            await interaction.response.send_message(view=ZoneEditOptionsViewV2(self.parent_view), ephemeral=True)
            return

        await interaction.response.send_message(
            "Choose what to edit:",
            view=ZoneEditOptionsView(self.parent_view),
            ephemeral=True
        )


class ManageNPCsButton(ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Manage NPCs", style=discord.ButtonStyle.primary, custom_id="manage_npcs", row=1)
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        # Check if user has GM role
        if not await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user):
            await interaction.response.send_message("❌ Only GMs can manage NPCs.", ephemeral=True)
            return
        
        # Get available NPCs
        npcs = repositories.character.get_npcs(str(interaction.guild.id))
        
        # Get NPCs currently in the scene
        scene_npc_ids = repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), str(self.parent_view.scene_id))
        
        # Create selection options for NPCs
        options = []
        
        # First, add NPCs already in the scene so they appear at the top
        for npc in npcs:
            if npc.id in scene_npc_ids:
                options.append(discord.SelectOption(
                    label=f"✓ {npc.name}",
                    value=npc.id,
                    description=f"Remove from scene",
                    default=True
                ))
        
        # Then add NPCs not in the scene
        for npc in npcs:
            if npc.id not in scene_npc_ids:
                options.append(discord.SelectOption(
                    label=npc.name,
                    value=npc.id,
                    description=f"Add to scene"
                ))
        
        # Send a message with the menu
        if options:
            view = FateManageNPCsViewV2(self.parent_view, options) if isinstance(self.parent_view, ui.LayoutView) else ManageNPCsView(self.parent_view, options)
            await interaction.response.send_message(
                view=view,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "❌ No NPCs found. Create some with `/char create npc`.", 
                ephemeral=True
            )


class ZoneEditOptionsView(discord.ui.View):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        
    @discord.ui.button(label="Edit Zone List", style=discord.ButtonStyle.primary)
    async def edit_zones(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditZonesModal(self.parent_view))
        
    @discord.ui.button(label="Edit Zone Aspects", style=discord.ButtonStyle.secondary)
    async def edit_zone_aspects(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Get current zones
        zones = repositories.fate_zones.get_zones(str(self.parent_view.guild_id), str(self.parent_view.scene_id)) or []
        
        if not zones:
            await interaction.response.send_message("❌ No zones found. Create zones first.", ephemeral=True)
            return
            
        await interaction.response.send_modal(EditZoneAspectsModal(self.parent_view, zones))


class ZoneEditOptionsViewV2(ui.LayoutView):
    def __init__(self, parent_view: 'FateSceneViewV2'):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        self._build_layout()

    def _build_layout(self):
        self.add_item(
            ui.Container(
                ui.TextDisplay("## Edit Fate Zones\nChoose whether to update the zone list or the aspects attached to zones."),
                accent_colour=discord.Colour.purple(),
            )
        )
        self.add_item(ui.Separator())

        row = ui.ActionRow()
        edit_zones_button = ui.Button(label="Edit Zone List", style=discord.ButtonStyle.primary)
        edit_zones_button.callback = self.edit_zones
        row.add_item(edit_zones_button)

        edit_zone_aspects_button = ui.Button(label="Edit Zone Aspects", style=discord.ButtonStyle.secondary)
        edit_zone_aspects_button.callback = self.edit_zone_aspects
        row.add_item(edit_zone_aspects_button)
        self.add_item(row)

    async def edit_zones(self, interaction: discord.Interaction):
        await interaction.response.send_modal(EditZonesModal(self.parent_view))

    async def edit_zone_aspects(self, interaction: discord.Interaction):
        zones = repositories.fate_zones.get_zones(str(self.parent_view.guild_id), str(self.parent_view.scene_id)) or []

        if not zones:
            await interaction.response.send_message("❌ No zones found. Create zones first.", ephemeral=True)
            return

        await interaction.response.send_modal(EditZoneAspectsModal(self.parent_view, zones))


class ManageNPCsView(discord.ui.View):
    def __init__(self, parent_view: FateSceneView, options):
        super().__init__(timeout=300)  # 5 minute timeout
        self.parent_view = parent_view
        self.add_item(ManageNPCsSelect(parent_view, options))
        self.add_item(DoneButton(parent_view))


class FateManageNPCsViewV2(ui.LayoutView):
    def __init__(self, parent_view, options):
        super().__init__(timeout=300)
        self.parent_view = parent_view
        self.options = options
        self._build_layout()

    def _build_layout(self):
        self.add_item(
            ui.Container(
                ui.TextDisplay(
                    "## Manage Scene NPCs\n"
                    "Selected NPCs stay in the scene. Unselected NPCs currently in the scene will be removed."
                ),
                accent_colour=discord.Colour.blurple(),
            )
        )
        self.add_item(ui.Separator())

        select_row = ui.ActionRow()
        select_row.add_item(ManageNPCsSelect(self.parent_view, self.options))
        self.add_item(select_row)

        done_row = ui.ActionRow()
        done_row.add_item(DoneButton(self.parent_view))
        self.add_item(done_row)


class ManageNPCsSelect(discord.ui.Select):
    def __init__(self, parent_view: FateSceneView, options):
        super().__init__(
            placeholder="Select NPCs to add/remove...",
            min_values=0,
            max_values=len(options),
            options=options
        )
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        # Get current NPCs in scene
        scene_npc_ids = repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), str(self.parent_view.scene_id))
        
        # NPCs to add (selected but not in scene)
        to_add = [npc_id for npc_id in self.values if npc_id not in scene_npc_ids]
        
        # NPCs to remove (in scene but not selected)
        to_remove = [npc_id for npc_id in scene_npc_ids if npc_id not in self.values]
        
        # Perform the updates
        for npc_id in to_add:
            repositories.scene_npc.add_npc_to_scene(str(interaction.guild.id), str(self.parent_view.scene_id), npc_id)
            
        for npc_id in to_remove:
            repositories.scene_npc.remove_npc_from_scene(str(interaction.guild.id), str(self.parent_view.scene_id), npc_id)
    
        # Check if this is the active scene before updating pins
        scene = repositories.scene.find_by_id('scene_id', self.parent_view.scene_id)
    
        # Only update all pinned instances if this is the active scene
        if scene and scene.is_active:
            # Find any SceneCommands cog instance to use its update method
            scene_cog = None
            for cog in interaction.client.cogs.values():
                if isinstance(cog, commands.Cog) and hasattr(cog, "_update_all_pinned_scenes"):
                    scene_cog = cog
                    break
        
            # Update all pinned scenes with this scene ID
            if scene_cog:
                await scene_cog._update_all_pinned_scenes(interaction.guild, self.parent_view.scene_id)
    
        await self.parent_view.update_view(interaction)


class DoneButton(discord.ui.Button):
    def __init__(self, parent_view: FateSceneView):
        super().__init__(label="Done", style=discord.ButtonStyle.secondary)
        self.parent_view = parent_view
        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="✅ NPC management complete.", view=None)


class EditGameAspectsModal(discord.ui.Modal, title="Edit Game Aspects"):
    def __init__(self, parent_view: FateSceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current game aspects
        current_aspects = repositories.fate_game_aspects.get_game_aspects(str(parent_view.guild_id)) or []
        
        # Convert aspects to format suitable for editing in text field
        aspect_lines = []
        for aspect in current_aspects:
            # Format for editing in text area
            if aspect.is_hidden:
                aspect_lines.append(f"*{aspect.name}*")
            else:
                aspect_lines.append(aspect.name)
                
            # If we have free invokes, add them in a bracket
            if aspect.free_invokes > 0:
                aspect_lines[-1] += f" [{aspect.free_invokes}]"
        
        current_text = "\n".join(aspect_lines)
        
        self.aspects = discord.ui.TextInput(
            label="Game Aspects (* for hidden, [#] for invokes)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=current_text,
            placeholder="The Doom Clock Ticks [2]\n*Hidden Cult Influence*\nWar is Coming"
        )
        self.add_item(self.aspects)

    async def on_submit(self, interaction: discord.Interaction):
        # Split by newlines and filter out empty lines
        aspect_lines = [line.strip() for line in self.aspects.value.splitlines()]
        aspect_lines = [line for line in aspect_lines if line]
        
        # Convert to Aspect objects
        aspects = []
        for line in aspect_lines:
            # Check if this aspect has free invokes
            free_invokes = 0
            invoke_match = line.strip().split('[')
            if len(invoke_match) > 1 and invoke_match[1].endswith(']'):
                try:
                    # Extract the number from [#]
                    invoke_str = invoke_match[1].rstrip(']')
                    free_invokes = int(invoke_str)
                    # Remove the [#] part from the line
                    line = invoke_match[0].strip()
                except ValueError:
                    # If we can't parse the number, assume it's part of the name
                    pass
            
            # Check if this aspect is marked as hidden (with asterisks)
            if line.startswith("*") and line.endswith("*"):
                name = line[1:-1].strip()
                aspects.append(Aspect(
                    name=name,
                    description="",
                    is_hidden=True,
                    free_invokes=free_invokes
                ))
            else:
                aspects.append(Aspect(
                    name=line,
                    description="",
                    is_hidden=False,
                    free_invokes=free_invokes
                ))
                
        # Clear existing game aspects first, then add new ones
        repositories.fate_game_aspects.clear_game_aspects(str(self.parent_view.guild_id))
        
        # Update game aspects in DB
        for aspect in aspects:
            repositories.fate_game_aspects.set_game_aspect(str(self.parent_view.guild_id), aspect)
        
        # Update the view - this will now update both pinned and ephemeral messages
        await self.parent_view.update_view(interaction)


class EditSceneAspectsModal(discord.ui.Modal, title="Edit Scene Aspects"):
    def __init__(self, parent_view: FateSceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current aspects
        current_aspects = repositories.fate_aspects.get_aspects(str(parent_view.guild_id), str(parent_view.scene_id)) or []
        
        # Convert aspects to format suitable for editing in text field
        aspect_lines = []
        for aspect in current_aspects:
            # Format for editing in text area
            if aspect.is_hidden:
                aspect_lines.append(f"*{aspect.name}*")
            else:
                aspect_lines.append(aspect.name)
                
            # If we have free invokes, add them in a bracket
            if aspect.free_invokes > 0:
                aspect_lines[-1] += f" [{aspect.free_invokes}]"
        
        current_text = "\n".join(aspect_lines)
        
        self.aspects = discord.ui.TextInput(
            label="Scene Aspects (* for hidden, [#] for invokes)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=current_text,
            placeholder="High Concept\n*A Secret Aspect*\nTrapped in Darkness [2]"
        )
        self.add_item(self.aspects)

    async def on_submit(self, interaction: discord.Interaction):
        # Split by newlines and filter out empty lines
        aspect_lines = [line.strip() for line in self.aspects.value.splitlines()]
        aspect_lines = [line for line in aspect_lines if line]
        
        # Convert to Aspect objects
        aspects = []
        for line in aspect_lines:
            # Check if this aspect has free invokes
            free_invokes = 0
            invoke_match = line.strip().split('[')
            if len(invoke_match) > 1 and invoke_match[1].endswith(']'):
                try:
                    # Extract the number from [#]
                    invoke_str = invoke_match[1].rstrip(']')
                    free_invokes = int(invoke_str)
                    # Remove the [#] part from the line
                    line = invoke_match[0].strip()
                except ValueError:
                    # If we can't parse the number, assume it's part of the name
                    pass
            
            # Check if this aspect is marked as hidden (with asterisks)
            if line.startswith("*") and line.endswith("*"):
                name = line[1:-1].strip()
                aspects.append(Aspect(
                    name=name,
                    description="",
                    is_hidden=True,
                    free_invokes=free_invokes
                ))
            else:
                aspects.append(Aspect(
                    name=line,
                    description="",
                    is_hidden=False,
                    free_invokes=free_invokes
                ))
        
        # Update aspects in DB
        repositories.fate_aspects.set_aspects(str(self.parent_view.guild_id), str(self.parent_view.scene_id), aspects)
        
        # Update the view - this will now update both pinned and ephemeral messages
        await self.parent_view.update_view(interaction)


class EditZonesModal(discord.ui.Modal, title="Edit Scene Zones"):
    def __init__(self, parent_view: FateSceneView):
        super().__init__()
        self.parent_view = parent_view
        
        # Get current zones
        current_zones = repositories.fate_zones.get_zones(str(parent_view.guild_id), str(parent_view.scene_id)) or []
        current_text = "\n".join(current_zones)
        
        self.zones = discord.ui.TextInput(
            label="Scene Zones (one per line)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=current_text,
            placeholder="West Bank\nBridge Span\nEast Bank"
        )
        self.add_item(self.zones)

    async def on_submit(self, interaction: discord.Interaction):
        # Split by newlines and filter out empty lines
        zone_lines = [line.strip() for line in self.zones.value.splitlines()]
        zone_lines = [line for line in zone_lines if line]
        
        # Update zones in DB
        repositories.fate_zones.set_zones(str(self.parent_view.guild_id), str(self.parent_view.scene_id), zone_lines)
        
        # Update the view - this will now update both pinned and ephemeral messages
        await self.parent_view.update_view(interaction)


class EditZoneAspectsModal(discord.ui.Modal, title="Edit Zone Aspects"):
    def __init__(self, parent_view: FateSceneView, zones: list):
        super().__init__()
        self.parent_view = parent_view
        self.zones = zones
        
        # Get current zone aspects for all zones
        zone_aspects = repositories.fate_zone_aspects.get_all_zone_aspects_for_scene(
            str(parent_view.guild_id), str(parent_view.scene_id)
        ) or {}
        
        # Convert to text format: "Zone Name: aspect1, aspect2"
        aspect_lines = []
        for zone in zones:
            zone_aspect_strings = []
            if zone in zone_aspects:
                for aspect in zone_aspects[zone]:
                    aspect_name = aspect.name
                    if aspect.is_hidden:
                        aspect_name = f"*{aspect_name}*"
                    if aspect.free_invokes > 0:
                        aspect_name += f" [{aspect.free_invokes}]"
                    zone_aspect_strings.append(aspect_name)
            
            if zone_aspect_strings:
                aspect_lines.append(f"{zone}: {', '.join(zone_aspect_strings)}")
            else:
                aspect_lines.append(f"{zone}: ")
        
        current_text = "\n".join(aspect_lines)
        
        self.zone_aspects = discord.ui.TextInput(
            label="Zone Aspects (Zone: aspect1, aspect2)",
            style=discord.TextStyle.paragraph,
            required=False,
            max_length=1000,
            default=current_text,
            placeholder="West Bank: Thick Undergrowth\nBridge Span: Crumbling Stonework [1], *Hidden Trap*"
        )
        self.add_item(self.zone_aspects)

    async def on_submit(self, interaction: discord.Interaction):
        # Clear existing zone aspects for this scene
        for zone in self.zones:
            repositories.fate_zone_aspects.clear_zone_aspects(
                str(self.parent_view.guild_id), 
                str(self.parent_view.scene_id)
            )
        
        # Parse new zone aspects
        aspect_lines = [line.strip() for line in self.zone_aspects.value.splitlines()]
        aspect_lines = [line for line in aspect_lines if line and ':' in line]
        
        for line in aspect_lines:
            zone_name, aspects_str = line.split(':', 1)
            zone_name = zone_name.strip()
            aspects_str = aspects_str.strip()
            
            if not aspects_str or zone_name not in self.zones:
                continue
                
            # Parse aspects for this zone
            aspect_names = [name.strip() for name in aspects_str.split(',')]
            aspects = []
            
            for aspect_name in aspect_names:
                if not aspect_name:
                    continue
                    
                # Check for free invokes
                free_invokes = 0
                invoke_match = aspect_name.split('[')
                if len(invoke_match) > 1 and invoke_match[1].endswith(']'):
                    try:
                        invoke_str = invoke_match[1].rstrip(']')
                        free_invokes = int(invoke_str)
                        aspect_name = invoke_match[0].strip()
                    except ValueError:
                        pass
                
                # Check for hidden aspects
                is_hidden = False
                if aspect_name.startswith("*") and aspect_name.endswith("*"):
                    aspect_name = aspect_name[1:-1].strip()
                    is_hidden = True
                
                aspects.append(Aspect(
                    name=aspect_name,
                    description="",
                    is_hidden=is_hidden,
                    free_invokes=free_invokes
                ))
            
            # Save aspects for this zone
            for aspect in aspects:
                repositories.fate_zone_aspects.set_zone_aspect(
                    str(self.parent_view.guild_id),
                    str(self.parent_view.scene_id),
                    zone_name,
                    aspect
                )
        
        # Update the view
        await self.parent_view.update_view(interaction)