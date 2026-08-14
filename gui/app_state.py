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

# Global analysis tracking
active_analysis_game = None
current_analysis_node = None
_analysis_callbacks = []


def register_analysis_callback(callback):
    """Register a function to be called when an analysis game is selected."""
    if callback not in _analysis_callbacks:
        _analysis_callbacks.append(callback)


def set_active_analysis_game(game_node):
    """Stores the active game node globally and notifies all registered listeners."""
    global active_analysis_game, current_analysis_node
    active_analysis_game = game_node
    current_analysis_node = game_node

    for callback in _analysis_callbacks:
        try:
            callback(game_node)
        except Exception as e:
            print(f"Error updating analysis callback: {e}")


# Alias to support any existing calls to load_analysis_game
def load_analysis_game(game_node):
    set_active_analysis_game(game_node)


def reset_state():
    """Wipes all in-memory game data, lookups, and imported file tracking."""
    global loaded_games, pgn_lookup, pgn_item_lookup, pgn_games_lookup
    global game_data_vars, other_data_vars, tag_corrections
    global imported_files, cataloged_files
    global active_analysis_game, current_analysis_node

    loaded_games.clear()
    pgn_lookup.clear()
    pgn_item_lookup.clear()
    pgn_games_lookup.clear()
    game_data_vars.clear()
    other_data_vars.clear()
    tag_corrections.clear()

    imported_files.clear()
    cataloged_files.clear()
    active_analysis_game = None
    current_analysis_node = None