# gui/app_state.py

app = None
left_frame = None
workspace = None
status = None
sidebar = None
pgn_node = None
pgn_games_node = None
mixed_collections_node = None
catalog_node = None
notes_node = None

loaded_games = {}
pgn_lookup = {}
pgn_item_lookup = {}
pgn_games_lookup = {}
game_data_vars = {}
other_data_vars = {}
tag_corrections = {}
depth_menu = None
rating_filter = None

imported_files = []
cataloged_files = []
sidebar_visible = True


def reset_state():
    """Wipes all in-memory game data, lookups, and imported file tracking."""
    global loaded_games, pgn_lookup, pgn_item_lookup, pgn_games_lookup
    global game_data_vars, other_data_vars, tag_corrections
    global imported_files, cataloged_files

    loaded_games.clear()
    pgn_lookup.clear()
    pgn_item_lookup.clear()
    pgn_games_lookup.clear()
    game_data_vars.clear()
    other_data_vars.clear()
    tag_corrections.clear()

    imported_files.clear()
    cataloged_files.clear()