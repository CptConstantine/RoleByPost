from rpg_systems.fate import fate_sheet, fate_views
from rpg_systems.mgt2e import mgt2e_sheet, mgt2e_views


def get_specific_sheet(system: str):
    if system == "fate":
        return fate_sheet.FateSheet()
    elif system == "mgt2e":
        return mgt2e_sheet.MGT2ESheet()
    else:
        raise ValueError(f"Unknown system: {system}")

def get_specific_sheet_view(system: str, editor_id: str, char_id: str):
    if system == "fate":
        return fate_views.SheetEditView(editor_id=editor_id, char_id=char_id)
    elif system == "mgt2e":
        return mgt2e_views.SheetEditView(editor_id=editor_id, char_id=char_id)
    else:
        raise ValueError(f"Unknown system: {system}")