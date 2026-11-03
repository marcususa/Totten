import sys
import inspect
import importlib.util
from pathlib import Path
import chess.pgn
import gui.app_state as state
from tkinter import filedialog
from gui.statusbar import set_status_message, start_progress, update_progress, stop_progress

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
    if hasattr(state, "is_importing"):
        state.is_importing = False

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

    state.is_importing = True

    ws_manager = getattr(state, "workspace", None)
    root_window = None
    if ws_manager:
        root_window = getattr(ws_manager, "catalog", None) or getattr(ws_manager, "search_catalog", None)

    if not root_window:
        root_window = getattr(state, "app_root", None)

    if not root_window and ws_manager and hasattr(ws_manager, "__dict__"):
        for val in ws_manager.__dict__.values():
            if val is not None:
                root_window = val
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

    if filename in state.imported_files:
        set_status_message(f"{short_name} is already imported.")
        state.is_importing = False
        return

    start_progress(indeterminate=False)
    set_status_message(f"Reading and caching {short_name}...")

    def start_phase_1_ticker():
        def tick(val=0.0):
            if getattr(state, "is_importing", False) and val < 0.48:
                new_val = val + 0.02
                update_progress(new_val)
                if root_window and hasattr(root_window, "after"):
                    root_window.after(200, lambda: tick(new_val))

        tick(0.0)

    start_phase_1_ticker()

    # --- 1. Parse PGN Games into memory with raw string caching ---
    games = []
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as pgn_file:
            while True:
                game = chess.pgn.read_game(pgn_file)
                if game is None:
                    break
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                game.cached_pgn_text = game.accept(exporter)
                games.append(game)
    except Exception as e:
        print(f"Error reading PGN file: {e}")
        state.is_importing = False
        stop_progress()
        set_status_message(f"Failed to read {short_name}")
        return

    state.pgn_games_lookup[filename] = games
    state.imported_files.insert(0, filename)
    state.pgn_lookup[short_name] = filename
    state.current_filename = filename

    print(f"3 - Successfully loaded {len(games)} games from {short_name}")

    def handle_catalog_progress(event_type):
        if event_type == "phase_1_complete":
            update_progress(0.5)
            set_status_message("Saving to database...")

            def tick_db(val=0.5):
                if getattr(state, "is_importing", False) and val < 0.95:
                    new_val = val + 0.02
                    update_progress(new_val)
                    if root_window and hasattr(root_window, "after"):
                        root_window.after(300, lambda: tick_db(new_val))

            tick_db(0.5)

        elif event_type == "phase_2_complete":
            pass

    def on_catalog_complete(added_count):
        print(f"Catalog builder processed {added_count} new games.")
        state.is_importing = False
        stop_progress()

        tree_widget = getattr(state, 'sidebar_tree', getattr(state, 'tree', None))
        parent_node = getattr(state, 'pgn_games_node', '')

        if tree_widget and hasattr(tree_widget, 'insert'):
            try:
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
            except Exception:
                pass

        def execute_full_refresh():
            # 1. Switch active workspace view using state.show_workspace if available
            if hasattr(state, "show_workspace") and callable(state.show_workspace):
                for key in ["search_catalog", "catalog", "search", "catalog_workspace"]:
                    try:
                        state.show_workspace(key)
                        break
                    except Exception:
                        continue

            # 2. Directly grab the workspace manager or frame and force load_catalog()
            ws_mgr = getattr(state, "workspace", None)
            if ws_mgr:
                for key in ["search_catalog", "catalog", "search", "catalog_workspace"]:
                    workspace_instance = getattr(ws_mgr, key, None)
                    if workspace_instance and hasattr(workspace_instance, "load_catalog"):
                        workspace_instance.load_catalog()
                        if hasattr(workspace_instance, "update_idletasks"):
                            workspace_instance.update_idletasks()
                        break

            set_status_message(f"Added {short_name} ({len(games)} games) to catalog.")

        if root_window and hasattr(root_window, "after"):
            root_window.after(100, execute_full_refresh)
        else:
            execute_full_refresh()

    try:
        if hasattr(catalog_builder, "run_import_in_background"):
            catalog_builder.run_import_in_background(
                filename,
                tk_root=root_window,
                on_complete_callback=on_catalog_complete,
                progress_callback=handle_catalog_progress
            )
        else:
            added_count = catalog_builder.catalog_pgns(filename)
            on_catalog_complete(added_count)
    except Exception as err:
        print(f"Warning: background cataloging failed: {err}")
        state.is_importing = False
        stop_progress()


def import_fen():
    print("Import FEN selected")