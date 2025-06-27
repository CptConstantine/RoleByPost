from core import initiative_types, initiative_views, scene_views
from rpg_systems.fate import fate_character, fate_scene_view
from rpg_systems.mgt2e import mgt2e_character, mgt2e_scene_view
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

def get_specific_initiative_view(guild_id: str, channel_id: str, initiative, message_id=None):
    if initiative.type == "popcorn":
        return initiative_views.PopcornInitiativeView(
            guild_id=guild_id, 
            channel_id=channel_id, 
            initiative=initiative,
            message_id=message_id
        )
    elif initiative.type == "generic":
        return initiative_views.GenericInitiativeView(
            guild_id=guild_id, 
            channel_id=channel_id, 
            initiative=initiative,
            message_id=message_id
        )
    else:
        raise ValueError(f"Unknown initiative type: {initiative.type}")
    
def get_specific_roll_formula(system: str, roll_parameters_dict: dict = None):
    if system == "fate":
        return fate_character.FateRollModifiers(roll_parameters_dict)
    elif system == "mgt2e":
        return mgt2e_character.MGT2ERollModifiers(roll_parameters_dict)
    elif system == "generic":
        return generic_character.GenericRollModifiers(roll_parameters_dict)
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_roll_formula_view(system: str, roll_formula_obj, difficulty: int = None):
    if system == "fate":
        return fate_character.FateRollModifiersView(roll_formula_obj, difficulty)
    elif system == "mgt2e":
        return mgt2e_character.MGT2ERollModifiersView(roll_formula_obj, difficulty)
    elif system == "generic":
        return generic_character.GenericRollModifiersView(roll_formula_obj, difficulty)
    else:
        raise ValueError(f"Unknown system: {system}")
    
def get_specific_scene_view(system, guild_id=None, channel_id=None, scene_id=None, message_id=None):
    """Get the appropriate scene view for the given system"""
    if system == "fate":
        return fate_scene_view.FateSceneView(guild_id, channel_id, scene_id, message_id)
    elif system == "mgt2e":
        return mgt2e_scene_view.MGT2ESceneView(guild_id, channel_id, scene_id, message_id)
    else:
        return scene_views.GenericSceneView(guild_id, channel_id, scene_id, message_id)