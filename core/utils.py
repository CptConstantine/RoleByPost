from data import repo


def get_character(guild_id, char_id):
    character = repo.get_character_by_id(guild_id, char_id)
    return character if character else None