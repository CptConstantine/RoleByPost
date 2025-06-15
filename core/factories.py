from core import initiative_types, initiative_views
from rpg_systems.fate import fate_character
from rpg_systems.mgt2e import mgt2e_character
from rpg_systems.generic import generic_character

def get_specific_character(system: str):
    if system == "fate":
        return fate_character.FateCharacter
    elif system == "mgt2e":
        return mgt2e_character.MGT2ECharacter
    elif system == "generic":
        return generic_character.GenericCharacter
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_sheet(system: str):
    if system == "fate":
        return fate_character.FateSheet()
    elif system == "mgt2e":
        return mgt2e_character.MGT2ESheet()
    elif system == "generic":
        return generic_character.GenericSheet()
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_sheet_view(system: str, editor_id: str, char_id: str):
    if system == "fate":
        return fate_character.FateSheetEditView(editor_id=editor_id, char_id=char_id)
    elif system == "mgt2e":
        return mgt2e_character.MGT2ESheetEditView(editor_id=editor_id, char_id=char_id)
    elif system == "generic":
        return generic_character.GenericSheetEditView(editor_id=editor_id, char_id=char_id)
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_initiative(initiative_type: str):
    if initiative_type == "popcorn":
        return initiative_types.PopcornInitiative
    elif initiative_type == "generic":
        return initiative_types.GenericInitiative
    else:
        raise ValueError(f"Unknown initiative type: {initiative_type}")

def get_specific_initiative_view(guild_id: str, channel_id: str, initiative):
    if initiative.type == "popcorn":
        return initiative_views.PopcornInitiativeView(guild_id=guild_id, channel_id=channel_id, initiative=initiative)
    elif initiative.type == "generic":
        return initiative_views.GenericInitiativeView(guild_id=guild_id, channel_id=channel_id, initiative=initiative)
    else:
        raise ValueError(f"Unknown initiative type: {initiative.type}")