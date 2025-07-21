from typing import List
import discord
from discord import app_commands
from core import factories
from core.base_models import EntityLinkType, EntityType, SystemType
from data.repositories.repository_factory import repositories
from rpg_systems.fate.fate_character import FateCharacter
from rpg_systems.mgt2e.mgt2e_character import MGT2ECharacter


# =================================================
# Characters/Companions
# =================================================

async def owned_player_character_names_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for getting owned player characters"""
    all_chars = repositories.character.get_all_pcs_and_npcs_by_guild(interaction.guild.id)
    pcs = [
        c for c in all_chars
        if not c.is_npc and str(c.owner_id) == str(interaction.user.id)
    ]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def all_pc_names_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for getting all PCs"""
    all_chars = repositories.character.get_all_pcs_and_npcs_by_guild(interaction.guild.id)
    pcs = [c for c in all_chars if not c.is_npc]
    options = [c.name for c in pcs if current.lower() in c.name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def owned_character_npc_or_companion_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for commands that can target PCs, NPCs, and companions"""
    all_chars = repositories.character.get_all_by_guild(interaction.guild.id)
    
    # Check if user is GM
    is_gm = await repositories.server.has_gm_permission(interaction.guild.id, interaction.user)
    
    # Filter characters based on permissions
    options = list[str]()
    for c in all_chars:
        if c.entity_type == EntityType.NPC and is_gm:
            # GMs can see all NPCs
            options.append(c.name)
        elif c.entity_type == EntityType.PC and (str(c.owner_id) == str(interaction.user.id) or is_gm):
            # Users can see their own PCs, GMs can see all PCs
            options.append(c.name)
        elif c.entity_type == EntityType.COMPANION:
            # Users can see companions they own or that are controlled by their characters
            if str(c.owner_id) == str(interaction.user.id) or is_gm:
                options.append(c.name)
            else:
                # Check if user owns any characters that control this companion
                controlling_chars = repositories.link.get_parents(
                    str(interaction.guild.id),
                    c.id,
                    EntityLinkType.CONTROLS.value
                )
                
                user_controls_companion = any(
                    str(controller.owner_id) == str(interaction.user.id) 
                    for controller in controlling_chars
                )
                
                if user_controls_companion:
                    options.append(c.name)
    
    # Filter by current input
    filtered_options = [n for n in options if current.lower() in n.lower()]
    return [app_commands.Choice(name=name, value=name) for name in filtered_options[:25]]

async def owned_companion_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete specifically for companion entities"""
    all_chars = repositories.character.get_all_by_guild(interaction.guild.id)
    
    # Check if user is GM
    is_gm = await repositories.server.has_gm_permission(interaction.guild.id, interaction.user)
    
    # Filter for companions only
    options = []
    for c in all_chars:
        if c.entity_type == EntityType.COMPANION:
            # Users can see companions they own or that are controlled by their characters
            if str(c.owner_id) == str(interaction.user.id) or is_gm:
                options.append(c.name)
            else:
                # Check if user owns any characters that control this companion
                controlling_chars = repositories.link.get_parents(
                    str(interaction.guild.id),
                    c.id,
                    EntityLinkType.CONTROLS.value
                )
                
                user_controls_companion = any(
                    str(controller.owner_id) == str(interaction.user.id) 
                    for controller in controlling_chars
                )
                
                if user_controls_companion:
                    options.append(c.name)
    
    # Filter by current input
    filtered_options = [name for name in options if current.lower() in name.lower()]
    return [app_commands.Choice(name=name, value=name) for name in filtered_options[:25]]

async def owned_player_characters_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for entities that can own other entities"""
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    
    if is_gm:
        # GMs can see all entities as potential owners
        characters = repositories.character.get_all_pcs_and_npcs_by_guild(str(interaction.guild.id))
    else:
        # Users can only use their own entities as owners
        characters = repositories.character.get_user_characters(str(interaction.guild.id), str(interaction.user.id))
    
    # Filter by current input
    filtered_entities = [
        char for char in characters 
        if current.lower() in char.name.lower()
    ]
    
    return [
        app_commands.Choice(name=f"{char.name} ({char.entity_type.value})", value=char.name)
        for char in filtered_entities[:25]
    ]

async def active_player_characters_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for active player characters in the current guild"""
    active_chars = repositories.active_character.get_all_active_characters(interaction.guild.id)
    
    # Filter characters based on permissions
    options = list[str]()
    for c in active_chars:
        options.append(c.name)
    
    # Filter by current input
    filtered_options = [n for n in options if current.lower() in n.lower()]
    return [app_commands.Choice(name=name, value=name) for name in filtered_options[:25]]

async def multi_character_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Enhanced autocomplete that handles comma-separated character names"""
    # Parse what's already been typed
    parts = current.split(',')
    current_typing = parts[-1].strip() if parts else current
    already_selected = [part.strip() for part in parts[:-1]] if len(parts) > 1 else []
    
    # Get available characters (excluding already selected)
    all_chars = repositories.character.get_all_pcs_and_npcs_by_guild(str(interaction.guild.id))
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    
    available_chars = []
    for char in all_chars:
        # Skip if already selected
        if char.name in already_selected:
            continue
            
        # Check if current typing matches
        if current_typing and current_typing.lower() not in char.name.lower():
            continue
            
        # Check permissions
        if char.entity_type == EntityType.NPC and is_gm:
            available_chars.append(char.name)
        elif char.entity_type == EntityType.PC and (str(char.owner_id) == str(interaction.user.id) or is_gm):
            available_chars.append(char.name)
        elif char.entity_type == EntityType.COMPANION:
            if str(char.owner_id) == str(interaction.user.id) or is_gm:
                available_chars.append(char.name)
            else:
                # Check if user owns any characters that control this companion
                controlling_chars = repositories.link.get_parents(
                    str(interaction.guild.id),
                    char.id,
                    EntityLinkType.CONTROLS.value
                )
                
                user_controls_companion = any(
                    str(controller.owner_id) == str(interaction.user.id) 
                    for controller in controlling_chars
                )
                
                if user_controls_companion:
                    available_chars.append(char.name)
    
    # Build the choice values (preserve what's already typed + add new selection)
    prefix = ', '.join(already_selected)
    if prefix:
        prefix += ', '
    
    choices = []
    
    # If nothing is being typed and we have selected characters, show a summary
    if not current_typing and already_selected:
        summary_text = f"Selected: {', '.join(already_selected)} (continue typing...)"
        choices.append(app_commands.Choice(name=summary_text, value=current))
    
    # Add available characters
    for char_name in available_chars[:24]:  # Leave room for summary if needed
        full_value = prefix + char_name
        
        # Create display name showing context
        if already_selected:
            display_name = f"{', '.join(already_selected)}, {char_name}"
        else:
            display_name = char_name
            
        # Truncate display name if too long (Discord limit is 100 chars)
        if len(display_name) > 97:
            display_name = display_name[:94] + "..."
            
        choices.append(app_commands.Choice(name=display_name, value=full_value))
    
    return choices


# =================================================
# Entities
# =================================================

async def entity_type_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for entity types based on current system"""
    system = repositories.server.get_system(str(interaction.guild.id))
    valid_types = factories.get_system_entity_types(system)
    
    # Filter based on user input
    filtered_types = [entity_type for entity_type in valid_types if current.lower() in entity_type.value.lower()]
    
    return [
        app_commands.Choice(name=entity_type.value.title(), value=entity_type.value)
        for entity_type in filtered_types[:25]
    ]

async def accessible_entities_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for any entity name - shows accessible entities"""
    if not interaction.guild:
        return []
    
    # Check if user is GM
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    
    # Get all entities the user can access
    accessible_entities = repositories.entity.get_all_accessible(
        str(interaction.guild.id), 
        str(interaction.user.id), 
        is_gm
    )
    
    # Filter based on current input
    if current:
        accessible_entities = [entity for entity in accessible_entities if current.lower() in entity.name.lower()]
    
    # Format the choices with entity type for clarity
    choices = []
    for entity in accessible_entities[:25]:  # Limit to 25 results
        entity_type = entity.entity_type.value.upper()
        # Add indicator for access type
        access_indicator = ""
        if not is_gm:
            if entity.owner_id == str(interaction.user.id):
                access_indicator = " [OWNED]"
            elif entity.access_type == "public":
                access_indicator = " [PUBLIC]"
            else:
                # Check if controlled
                controlled_entities = repositories.entity.get_entities_controlled_by_user(
                    str(interaction.guild.id), str(interaction.user.id)
                )
                if any(e.id == entity.id for e in controlled_entities):
                    access_indicator = " [CONTROLLED]"
                else:
                    access_indicator = " [ACCESS]"
        
        choices.append(
            app_commands.Choice(
                name=f"{entity.name} ({entity_type}){access_indicator}", 
                value=entity.name
            )
        )
    
    return choices

async def top_level_entities_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for parent entities - entities that can own other entities"""
    is_gm = await repositories.server.has_gm_permission(str(interaction.guild.id), interaction.user)
    
    # Get all entities the user can access
    entities = repositories.entity.get_all_accessible(
        str(interaction.guild.id), 
        str(interaction.user.id), 
        is_gm
    )
    
    # Add "None" option for top-level entities
    choices = [app_commands.Choice(name="None (Top Level)", value="")]
    
    # Filter by current input
    filtered_entities = [entity for entity in entities if current.lower() in entity.name.lower()]
    
    # Add access indicators for clarity
    entity_choices = []
    for entity in filtered_entities[:24]:  # 24 to make room for "None" option
        # Add indicator for access type
        access_indicator = ""
        if not is_gm:
            if entity.owner_id == str(interaction.user.id):
                access_indicator = " [OWNED]"
            elif entity.access_type == "public":
                access_indicator = " [PUBLIC]"
            else:
                # Check if controlled
                controlled_entities = repositories.entity.get_entities_controlled_by_user(
                    str(interaction.guild.id), str(interaction.user.id)
                )
                if any(e.id == entity.id for e in controlled_entities):
                    access_indicator = " [CONTROLLED]"
                else:
                    access_indicator = " [ACCESS]"
        
        entity_choices.append(
            app_commands.Choice(
                name=f"{entity.name} ({entity.entity_type.value}){access_indicator}", 
                value=entity.name
            )
        )
    
    choices.extend(entity_choices)
    return choices


# =================================================
# Initiative
# =================================================

async def initiative_type_autocomplete(
        interaction: discord.Interaction,
        current: str,
    ) -> List[app_commands.Choice[str]]:
        """Autocomplete for initiative types"""
        initiative_types = ["popcorn", "generic"]
        
        # Filter based on what the user has typed so far
        filtered_types = [
            init_type for init_type in initiative_types 
            if current.lower() in init_type.lower()
        ]
        
        return [
            app_commands.Choice(name=init_type.capitalize(), value=init_type)
            for init_type in filtered_types
        ]

async def initiative_participant_names_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for participants in the current initiative."""
    initiative = repositories.initiative.get_active_initiative(str(interaction.guild.id), str(interaction.channel.id))
    if not initiative:
        return []
    # Only suggest names that match the current input
    return [
        app_commands.Choice(name=p.name, value=p.name)
        for p in initiative.participants
        if current.lower() in p.name.lower()
    ][:25]

async def initiative_addable_names_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """
    Autocomplete for PCs and NPCs that are NOT currently in initiative.
    """
    guild_id = str(interaction.guild.id)
    channel_id = str(interaction.channel.id)
    initiative = repositories.initiative.get_active_initiative(guild_id, channel_id)
    if not initiative:
        return []

    # Get all PCs and NPCs in the guild
    all_chars = repositories.character.get_all_pcs_and_npcs_by_guild(guild_id)
    # Names already in initiative (case-insensitive)
    in_initiative = {p.name.lower() for p in initiative.participants}

    # Only suggest those not already in initiative and matching current input
    addable = [
        c for c in all_chars
        if (c.entity_type in (EntityType.PC, EntityType.NPC, EntityType.COMPANION)) and (c.name.lower() not in in_initiative) and (current.lower() in c.name.lower())
    ]

    return [
        app_commands.Choice(name=c.name, value=c.name)
        for c in addable[:25]
    ]


# =================================================
# Links
# =================================================

async def link_type_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Autocomplete for link types"""
    link_types = EntityLinkType.get_all_dict()
    
    # Filter based on current input
    if current:
        filtered_types = {name: value for name, value in link_types.items() if current.lower() in name.lower()}
    else:
        filtered_types = link_types
    
    return [
        app_commands.Choice(name=name, value=value.value)
        for name, value in filtered_types.items()
    ]


# =================================================
# Channels
# =================================================

async def ic_channels_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete for IC channels in the current guild"""
    if not interaction.guild:
        return []
    
    # Get all IC channels for this guild
    all_channels = repositories.channel_permissions.get_all_channel_permissions(str(interaction.guild.id))
    if not all_channels:
        return []
    ic_channel_ids = [channel.channel_id for channel in all_channels if channel.channel_type == 'ic']

    # Filter channels the user can see and match current input
    choices = []
    for channel_id in ic_channel_ids:
        channel = interaction.guild.get_channel(int(channel_id))
        if channel and channel.permissions_for(interaction.user).view_channel:
            channel_name = channel.name
            if current.lower() in channel_name.lower():
                choices.append(app_commands.Choice(
                    name=f"#{channel_name}",
                    value=str(channel.id)
                ))
    
    return choices[:25]  # Discord limit


# =================================================
# Roll Parameters
# =================================================

async def roll_parameters_autocomplete(interaction: discord.Interaction, current: str) -> List[app_commands.Choice[str]]:
    """Provide helpful autocomplete for roll parameters based on the system"""
    system = repositories.server.get_system(str(interaction.guild.id))
    
    choices = []
    
    # Parse what's already been typed
    parts = current.split(',') if current else []
    current_typing = parts[-1].strip() if parts else ""
    
    # System-specific suggestions
    if system == SystemType.FATE:
        choices.extend(await _get_fate_roll_parameter_choices(interaction.guild.id, current, parts, current_typing))
    elif system == SystemType.MGT2E:
        choices.extend(await _get_mgt2e_roll_parameter_choices(interaction.guild.id, current, parts, current_typing))
    else:
        # Generic system - just add modifiers
        choices.extend(await _get_generic_modifier_choices(current, parts))
    
    return choices[:25]  # Discord limit

async def _get_fate_roll_parameter_choices(guild_id: str, current: str, parts: List[str], current_typing: str) -> List[app_commands.Choice[str]]:
    """Get Fate-specific roll parameter choices"""
    choices = []
    
    # Check if skill is already specified
    has_skill = any("skill:" in part for part in parts)
    
    # If nothing is typed yet or we're starting fresh, show main categories
    if not current_typing:
        if not has_skill:
            choice_value = f"{current},skill:" if current else "skill:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        # Build the prefix correctly - everything except the current incomplete part
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        # Add modifier option
        existing_mods = len([p for p in parts if p.strip().startswith("mod")])
        if existing_mods < 3:
            mod_num = existing_mods + 1
            choice_value = f"{prefix}mod{mod_num}:" if current else f"mod{mod_num}:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        return choices
    
    # If they're typing after "skill:", show skill suggestions
    if current_typing.startswith("skill:"):
        skill_part = current_typing[6:]  # Remove "skill:" prefix
        
        # Get default skills for this guild/system
        default_skills = repositories.default_skills.get_default_skills(guild_id, SystemType.FATE)
        if not default_skills:
            default_skills = FateCharacter.DEFAULT_SKILLS
        
        # Build the prefix correctly - everything except the current incomplete part
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        # Offer specific skills from the guild's default list
        for skill_name in sorted(default_skills.keys())[:15]:  # Limit to prevent overflow
            if not skill_part or skill_name.lower().startswith(skill_part.lower()):
                choice_value = f"{prefix}skill:{skill_name}"
                choices.append(app_commands.Choice(
                    name=choice_value, 
                    value=choice_value
                ))
    
    # If they're typing after "modX:", show number suggestions
    elif any(current_typing.startswith(f"mod{i}:") for i in range(1, 4)):
        mod_part = current_typing.split(":", 1)[1] if ":" in current_typing else ""
        mod_name = current_typing.split(":", 1)[0] if ":" in current_typing else current_typing
        
        # Build the prefix correctly
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        # Common modifier values
        common_values = ["-3", "-2", "-1", "+1", "+2", "+3"]
        for value in common_values:
            if not mod_part or value.startswith(mod_part):
                choice_value = f"{prefix}{mod_name}:{value}"
                choices.append(app_commands.Choice(
                    name=choice_value, 
                    value=choice_value
                ))
    
    return choices

async def _get_mgt2e_roll_parameter_choices(guild_id: str, current: str, parts: List[str], current_typing: str) -> List[app_commands.Choice[str]]:
    """Get MGT2E-specific roll parameter choices"""
    choices = []
    
    # Check what's already specified
    has_skill = any("skill:" in part for part in parts)
    has_attribute = any("attribute:" in part for part in parts)
    has_boon = any("boon" in part.lower() for part in parts)
    has_bane = any("bane" in part.lower() for part in parts)
    
    # If nothing is typed yet or we're starting fresh, show main categories
    if not current_typing:
        if not has_skill:
            choice_value = f"{current}skill:" if current else "skill:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        if not has_attribute:
            choice_value = f"{current}attribute:" if current else "attribute:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        if not has_boon and not has_bane:
            choice_value = f"{current}boon" if current else "boon"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
            
            choice_value = f"{current}bane" if current else "bane"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        # Add modifier option
        existing_mods = len([p for p in parts if p.strip().startswith("mod")])
        if existing_mods < 3:
            mod_num = existing_mods + 1
            choice_value = f"{current}mod{mod_num}:" if current else f"mod{mod_num}:"
            choices.append(app_commands.Choice(
                name=choice_value, 
                value=choice_value
            ))
        
        return choices
    
    # If they're typing after "skill:", show skill suggestions
    if current_typing.startswith("skill:"):
        skill_part = current_typing[6:]  # Remove "skill:" prefix
        
        # Get default skills for this guild/system
        default_skills = repositories.default_skills.get_default_skills(guild_id, SystemType.MGT2E)
        if not default_skills:
            default_skills = MGT2ECharacter.DEFAULT_SKILLS
        
        # Build the prefix correctly
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        if default_skills:
            # Show a few popular skills first
            popular_skills = ["Admin", "Athletics", "Gun Combat", "Pilot", "Recon", "Stealth"]
            for skill_name in popular_skills:
                if skill_name in default_skills and (not skill_part or skill_name.lower().startswith(skill_part.lower())):
                    choice_value = f"{prefix}skill:{skill_name}"
                    choices.append(app_commands.Choice(
                        name=choice_value, 
                        value=choice_value
                    ))
    
    # If they're typing after "attribute:", show attribute suggestions
    elif current_typing.startswith("attribute:"):
        attr_part = current_typing[10:]  # Remove "attribute:" prefix
        
        # Build the prefix correctly
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        attributes = ["STR", "DEX", "END", "INT", "EDU", "SOC"]
        for attr in attributes:
            if not attr_part or attr.lower().startswith(attr_part.lower()):
                choice_value = f"{prefix}attribute:{attr}"
                choices.append(app_commands.Choice(
                    name=choice_value, 
                    value=choice_value
                ))
    
    # If they're typing after "modX:", show number suggestions
    elif any(current_typing.startswith(f"mod{i}:") for i in range(1, 4)):
        mod_part = current_typing.split(":", 1)[1] if ":" in current_typing else ""
        mod_name = current_typing.split(":", 1)[0] if ":" in current_typing else current_typing
        
        # Build the prefix correctly
        prefix_parts = parts[:-1] if parts else []
        prefix = ','.join(prefix_parts)
        if prefix:
            prefix += ","
        
        # Common modifier values
        common_values = ["-3", "-2", "-1", "+1", "+2", "+3"]
        for value in common_values:
            if not mod_part or value.startswith(mod_part):
                choice_value = f"{prefix}{mod_name}:{value}"
                choices.append(app_commands.Choice(
                    name=choice_value, 
                    value=choice_value
                ))
    
    return choices

async def _get_generic_modifier_choices(current: str, parts: List[str]) -> List[app_commands.Choice[str]]:
    """Get generic modifier choices that work for any system"""
    choices = []
    
    # Count existing modifiers
    existing_mods = len([p for p in parts if p.strip().startswith("mod")])
    
    if existing_mods < 3:
        mod_num = existing_mods + 1
        choice_value = f"{current},mod{mod_num}:" if current else f"mod{mod_num}:"
        choices.append(app_commands.Choice(
            name=choice_value, 
            value=choice_value
        ))
    
    return choices


# =================================================
# Homebrew
# =================================================

async def homebrew_rules_autocomplete(interaction: discord.Interaction, current: str):
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


# =================================================
# Scenes
# =================================================

async def npcs_not_in_scene_autocomplete(interaction: discord.Interaction, current: str):
    all_chars = repositories.character.get_all_pcs_and_npcs_by_guild(str(interaction.guild.id))
    active_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
    
    if not active_scene:
        return []

    scene_npcs = set(repositories.scene_npc.get_scene_npc_ids(str(interaction.guild.id), str(active_scene.scene_id)))
    npcs = [
        c for c in all_chars
        if c.is_npc and c.id not in scene_npcs and current.lower() in c.name.lower()
    ]
    options = [c.name for c in npcs]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def npcs_in_scene_autocomplete(interaction: discord.Interaction, current: str):
    active_scene = repositories.scene.get_active_scene(str(interaction.guild.id))
    if not active_scene:
        return []
    all_chars = repositories.scene_npc.get_scene_npcs(str(interaction.guild.id), active_scene.scene_id)
    
    npcs = [c for c in all_chars]
    options = [c.name for c in npcs]
    return [app_commands.Choice(name=name, value=name) for name in options[:25]]

async def scene_names_autocomplete(interaction: discord.Interaction, current: str):
    scenes = repositories.scene.get_all_scenes(str(interaction.guild.id))
    return [
        app_commands.Choice(name=f"{s.name}{'✓' if s.is_active else ''}", value=s.name)
        for s in scenes
        if current.lower() in s.name.lower()
    ][:25]
