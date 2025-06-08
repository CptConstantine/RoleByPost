import discord


def get_pc_id(name):
    """Generate a player character ID from a name."""
    return f"pc:{name.lower().replace(' ', '_')}"


def get_npc_id(name):
    """Generate an NPC ID from a name."""
    return f"npc:{name.lower().replace(' ', '_')}"


class BaseSheet:
    SYSTEM_SPECIFIC_CHARACTER = {}
    SYSTEM_SPECIFIC_NPC = {}

    def format_full_sheet(self, character: dict) -> discord.Embed:
        raise NotImplementedError

    def format_npc_scene_entry(self, npc: dict, is_gm: bool) -> str:
        raise NotImplementedError