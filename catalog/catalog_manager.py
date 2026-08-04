# catalog/catalog_manager.py

import json
import os
import gui.app_state as state


def clear_catalog():
    """Completely deletes personal_catalog.json and personal_catalog.pgn, resets memory, clears UI treeviews, and resets status bar."""
    catalog_json_path = "personal_catalog.json"
    catalog_pgn_path = "personal_catalog.pgn"

    # 1. Delete personal_catalog.json off disk if it exists
    if os.path.exists(catalog_json_path):
        try:
            os.remove(catalog_json_path)
            print(f"File {catalog_json_path} successfully deleted.")
        except Exception as e:
            print(f"Error deleting {catalog_json_path}: {e}")

    # 2. Delete personal_catalog.pgn off disk if it exists (THIS WAS MISSING)
    if os.path.exists(catalog_pgn_path):
        try:
            os.remove(catalog_pgn_path)
            print(f"File {catalog_pgn_path} successfully deleted.")
        except Exception as e:
            print(f"Error deleting {catalog_pgn_path}: {e}")
            try:
                with open(catalog_pgn_path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass

    # 3. Reset state variables in memory
    for dict_attr in [
        "loaded_games",
        "pgn_lookup",
        "pgn_item_lookup",
        "pgn_games_lookup",
        "game_data_vars",
        "other_data_vars",
        "tag_corrections",
    ]:
        if hasattr(state, dict_attr) and isinstance(
            getattr(state, dict_attr), dict
        ):
            getattr(state, dict_attr).clear()

    for list_attr in ["imported_files", "cataloged_files"]:
        if hasattr(state, list_attr) and isinstance(
            getattr(state, list_attr), list
        ):
            getattr(state, list_attr).clear()

    if hasattr(state, "current_filename"):
        state.current_filename = None

    # 4. Clear sidebar items safely if present
    if getattr(state, "sidebar", None) is not None and hasattr(
        state, "pgn_games_node"
    ):
        try:
            for item in state.sidebar.get_children(state.pgn_games_node):
                state.sidebar.delete(item)
        except Exception as e:
            print(f"Notice during sidebar cleanup: {e}")

    # 5. Force immediate update and clear active Workspaces
    if hasattr(state, "workspaces"):
        catalog_ws = state.workspaces.get("catalog")
        if catalog_ws:
            if hasattr(catalog_ws, "clear_table"):
                catalog_ws.clear_table()
            elif hasattr(catalog_ws, "tree"):
                for item in catalog_ws.tree.get_children():
                    catalog_ws.tree.delete(item)
            if hasattr(catalog_ws, "load_catalog"):
                catalog_ws.load_catalog()

        import_ws = state.workspaces.get("import")
        if import_ws:
            if hasattr(import_ws, "clear_table"):
                import_ws.clear_table()
            elif hasattr(import_ws, "tree"):
                for item in import_ws.tree.get_children():
                    import_ws.tree.delete(item)
            if hasattr(import_ws, "load_data"):
                import_ws.load_data()

    # 6. Reset Status Bar Display
    if hasattr(state, "status") and state.status:
        try:
            if hasattr(state.status, "configure"):
                state.status.configure(text="Catalog cleared (0 games)")
            elif hasattr(state.status, "config"):
                state.status.config(text="Catalog cleared (0 games)")
            elif isinstance(state.status, str):
                state.status = "Catalog cleared (0 games)"
        except Exception as e:
            print(f"Notice during status update: {e}")