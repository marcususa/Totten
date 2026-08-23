import sys
import inspect
import importlib.util
from pathlib import Path
import chess.pgn
import gui.app_state as state
from tkinter import filedialog
from gui.splash import LoadingOverlay

# Resolve path to catalog_builder.py in cousin folder /catalog/
CATALOG_BUILDER_PATH = Path(__file__).resolve().parent.parent / "catalog" / "catalog_builder.py"

spec = importlib.util.spec_from_file_location("catalog_builder", CATALOG_BUILDER_PATH)
catalog_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_builder)


def reset_importer_state():
    """Resets in-memory tracking lists and removes imported nodes from the sidebar tree."""
    state.imported_files = []
    state.pgn_games_lookup = {}
    state.pgn_lookup = {}
    state.current_filename = None

    tree_widget = getattr(state, 'sidebar_tree', getattr(state, 'tree', None))
    pgn_item_lookup = getattr(state, 'pgn_item_lookup', {})

    if tree_widget and hasattr(tree_widget, 'delete'):
        for item_id in pgn_item_lookup.values():
            try:
                tree_widget.delete(item_id)
            except Exception:
                pass
        state.pgn_item_lookup = {}


def import_pgn():
    print("1 - import_pgn started")

    filename = filedialog.askopenfilename(
        title="Import PGN",
        filetypes=[("PGN Files", "*.pgn"), ("All Files", "*.*")]
    )

    if not filename:
        return

    # Force the main application window to flash/clear the OS file picker ghost frame immediately
    root_window = state.workspaces.get("catalog") or getattr(state, "app_root", None)
    if not root_window:
        for ws in state.workspaces.values():
            root_window = ws
            break

    if root_window:
        try:
            root_window.update()
        except Exception:
            pass

    print(f"2 - Selected: {filename}")
    short_name = Path(filename).name

    if not hasattr(state, 'imported_files'):
        state.imported_files = []
    if not hasattr(state, 'pgn_games_lookup'):
        state.pgn_games_lookup = {}
    if not hasattr(state, 'pgn_lookup'):
        state.pgn_lookup = {}

    # Check duplicate in memory
    if filename in state.imported_files:
        if getattr(state, 'status', None):
            try:
                state.status.configure(text=f"{short_name} is already imported.")
            except Exception:
                pass
        return

    overlay = None
    if root_window:
        try:
            overlay = LoadingOverlay(root_window, title_text="Totten", message="Reading PGN games... (0)")
            root_window.update_idletasks()
        except Exception:
            pass

    # --- 1. Parse PGN Games into memory with live counter ---
    games = []
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as pgn_file:
            count = 0
            while True:
                game = chess.pgn.read_game(pgn_file)
                if game is None:
                    break
                games.append(game)
                count += 1
                if count % 25 == 0 and overlay:
                    try:
                        overlay.update_message(f"Reading PGN games... ({count})")
                        root_window.update_idletasks()
                    except Exception:
                        pass
    except Exception as e:
        print(f"Error reading PGN file: {e}")
        if overlay:
            try:
                overlay.close()
            except Exception:
                pass
        if getattr(state, 'status', None):
            try:
                state.status.configure(text=f"Failed to read {short_name}")
            except Exception:
                pass
        return

    state.pgn_games_lookup[filename] = games
    state.imported_files.insert(0, filename)
    state.pgn_lookup[short_name] = filename
    state.current_filename = filename

    print(f"3 - Successfully loaded {len(games)} games from {short_name}")

    if overlay:
        try:
            overlay.update_message("Building catalog database...")
            root_window.update_idletasks()
        except Exception:
            pass

    # --- 2. Execute catalog_builder.catalog_pgns with relative path handling ---
    try:
        if hasattr(catalog_builder, "catalog_pgns"):
            added_count = catalog_builder.catalog_pgns(filename)
            print(f"Catalog builder processed {added_count} new games.")
    except Exception as err:
        print(f"Warning: catalog_builder.catalog_pgns failed: {err}")

    if overlay:
        try:
            overlay.close()
        except Exception:
            pass

    # --- 3. Update Sidebar Tree ---
    tree_widget = getattr(state, 'sidebar_tree', getattr(state, 'tree', None))
    parent_node = getattr(state, 'pgn_games_node', '')

    if tree_widget and hasattr(tree_widget, 'insert'):
        pgn_item = tree_widget.insert(
            parent_node,
            0,
            text=short_name,
            open=True
        )
        if not hasattr(state, 'pgn_item_lookup'):
            state.pgn_item_lookup = {}
        state.pgn_item_lookup[filename] = pgn_item

        tree_widget.insert(pgn_item, "end", text="Game Data")

    # --- 4. Refresh Workspace Views ---
    if hasattr(state, 'workspaces'):
        pgn_ws = state.workspaces.get("pgn_games")
        if pgn_ws and hasattr(pgn_ws, 'load_games'):
            pgn_ws.load_games()

        for cat_key in ["catalog", "search_catalog", "search"]:
            cat_ws = state.workspaces.get(cat_key)
            if cat_ws:
                if hasattr(cat_ws, 'load_catalog'):
                    cat_ws.load_catalog()
                elif hasattr(cat_ws, 'load_data'):
                    cat_ws.load_data()

        imp_ws = state.workspaces.get("import")
        if imp_ws:
            if hasattr(imp_ws, "filename"):
                imp_ws.filename = filename
            if hasattr(imp_ws, "refresh_view"):
                imp_ws.refresh_view()

    if getattr(state, 'status', None):
        try:
            state.status.configure(text=f"Added {short_name} ({len(games)} games) to catalog.")
        except Exception:
            pass


def import_fen():
    print("Import FEN selected")