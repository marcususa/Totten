# gui/app_state.py

# ==========================================
# 3-Way Selective Workspace State Persistence
# ==========================================

catalog_state = {
    "active_games": None,
    "active_focus": None,
    "current_filename": "personal_catalog.pgn"
}

mixed_state = {
    "active_games": None,
    "current_filename": None
}

search_state = {
    "search_results": None,
    "last_query": None
}

patterns_state = {
    "active_games": None,
    "active_focus": None,
    "current_filename": "patterns_analysis.pgn"
}

def set_active_patterns_collection(games_list, focused_game=None):
    """Sets the active patterns collection and triggers registered analysis callbacks."""
    patterns_state["active_games"] = games_list
    patterns_state["active_focus"] = focused_game
    for cb in _analysis_callbacks:
        try:
            cb(focused_game, category_source="patterns")
        except Exception as e:
            print(f"[APP STATE DEBUG] Error executing patterns analysis callback: {e}")

# General active workspace references
workspace = None
mixed_workspace = None

# Global event callbacks registry
_analysis_callbacks = []

def register_analysis_callback(callback):
    """Registers a callback function to be notified on game load events."""
    if callback not in _analysis_callbacks:
        _analysis_callbacks.append(callback)

def notify_analysis_callbacks(game_obj, category_source=None):
    """Triggers all registered game load callbacks."""
    for cb in _analysis_callbacks:
        try:
            cb(game_obj, category_source=category_source)
        except Exception as e:
            print(f"[APP STATE DEBUG] Error executing analysis callback: {e}")
