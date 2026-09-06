# gui/app_state.py

# ==========================================
# Centralized State Hub & Routing Dispatcher
# ==========================================

catalog_state = {
    "active_games": None,
    "active_focus": None,
    "current_filename": "PolgarJ.pgn",
    "source_origin": "search_catalog_workspace"
}

mixed_state = {
    "active_games": None,
    "active_focus": None,
    "current_filename": "mixed_analysis.pgn",
    "source_origin": "edit_workspace"
}

patterns_state = {
    "active_games": None,
    "active_focus": None,
    "current_filename": None,
    "source_origin": "patterns_workspace"
}

# Global active workspace references
workspace = None
mixed_workspace = None
catalog_workspace = None
search_catalog_workspace = None
edit_workspace = None
calendar_workspace = None
patterns_workspace = None

# Navigation and event callbacks registry
_navigation_listeners = []


def register_nav_listener(callback):
    """Registers a UI router/main window listener to handle view switching requests."""
    if callback not in _navigation_listeners:
        _navigation_listeners.append(callback)


def _trigger_navigation(target_view):
    """Internal dispatcher notifying all registered layout routers to swap views."""
    for listener in _navigation_listeners:
        try:
            listener(target_view)
        except Exception as e:
            print(f"[APP STATE ERROR] Navigation listener failed for target '{target_view}': {e}")


def dispatch_to_catalog_analysis(games_list, focused_game=None):
    """Catches payload from search_catalog_workspace.py and routes to catalog_analysis.py."""
    if not games_list:
        print("[APP STATE WARNING] Catalog analysis requested with empty games list.")
        return False

    cleaned = list(games_list)
    catalog_state["active_games"] = cleaned
    catalog_state["active_focus"] = focused_game if focused_game in cleaned else cleaned[0]
    catalog_state["source_origin"] = "search_catalog_workspace"

    print(f"[APP STATE] Routed {len(cleaned)} games from search/catalog to Catalog Analysis.")
    _trigger_navigation("catalog_analysis")
    return True


def dispatch_to_mixed_analysis(games_list, focused_game=None):
    """Catches payload from edit_workspace.py and routes to mixed_analysis.py."""
    if not games_list:
        print("[APP STATE WARNING] Mixed analysis requested with empty games list.")
        return False

    cleaned = list(games_list)
    mixed_state["active_games"] = cleaned
    mixed_state["active_focus"] = focused_game if focused_game in cleaned else cleaned[0]
    mixed_state["source_origin"] = "edit_workspace"

    print(f"[APP STATE] Routed {len(cleaned)} games from edit workspace to Mixed Analysis.")
    _trigger_navigation("mixed_analysis")
    return True


def dispatch_to_patterns_analysis(games_list, focused_game=None):
    """Catches payload from patterns_workspace.py and routes to patterns_analysis.py."""
    if not games_list:
        print("[APP STATE WARNING] Patterns analysis requested with empty games list.")
        return False

    cleaned = list(games_list)
    patterns_state["active_games"] = cleaned
    patterns_state["active_focus"] = focused_game if focused_game in cleaned else cleaned[0]
    patterns_state["source_origin"] = "patterns_workspace"

    print(f"[APP STATE] Routed {len(cleaned)} games from patterns workspace to Patterns Analysis.")
    _trigger_navigation("patterns_analysis")
    return True


# Legacy helper aliases for backwards compatibility
def set_active_mixed_collection(games_list, focused_game=None):
    dispatch_to_mixed_analysis(games_list, focused_game)


def set_active_patterns_collection(games_list, focused_game=None):
    dispatch_to_patterns_analysis(games_list, focused_game)