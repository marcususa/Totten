import sys
import inspect
import importlib.util
from pathlib import Path
import chess.pgn
import gui.app_state as state
from tkinter import filedialog

# Target catalog_builder.py inside the catalog/ directory
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

    # Clear tree items if they exist
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

    print(f"2 - Selected: {filename}")
    short_name = Path(filename).name

    # Initialize data stores in app_state if needed
    if not hasattr(state, 'imported_files'):
        state.imported_files = []
    if not hasattr(state, 'pgn_games_lookup'):
        state.pgn_games_lookup = {}
    if not hasattr(state, 'pgn_lookup'):
        state.pgn_lookup = {}

    # Check duplicate
    if filename in state.imported_files:
        if getattr(state, 'status', None):
            try:
                state.status.configure(text=f"{short_name} is already imported.")
            except Exception:
                pass
        return

    # --- 1. Parse PGN Games into memory ---
    games = []
    try:
        with open(filename, "r", encoding="utf-8", errors="replace") as pgn_file:
            while True:
                game = chess.pgn.read_game(pgn_file)
                if game is None:
                    break
                games.append(game)
    except Exception as e:
        print(f"Error reading PGN file: {e}")
        if getattr(state, 'status', None):
            try:
                state.status.configure(text=f"Failed to read {short_name}")
            except Exception:
                pass
        return

    # Store parsed games into state
    state.pgn_games_lookup[filename] = games

    # Prepend (insert at index 0) so newest file is FIRST
    state.imported_files.insert(0, filename)
    state.pgn_lookup[short_name] = filename
    state.current_filename = filename

    print(f"3 - Successfully loaded {len(games)} games from {short_name}")

    # --- 2. Safely Execute catalog_builder.catalog_pgns ---
    if hasattr(catalog_builder, "catalog_pgns"):
        sig = inspect.signature(catalog_builder.catalog_pgns)
        params = sig.parameters

        # Check if function accepts **kwargs or standard positional args
        accepts_kwargs = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

        class MockWidget:
            def configure(self, **kwargs): pass

        add_btn = getattr(state, 'add_catalog_button', MockWidget())
        imp_btn = getattr(state, 'import_button', MockWidget())
        cat_btn = getattr(state, 'catalog_button', MockWidget())
        status_lbl = getattr(state, 'status', MockWidget())
        workspace_obj = getattr(state, 'workspace', MockWidget())

        kwargs_payload = {
            "add_catalog_button": add_btn,
            "import_button": imp_btn,
            "catalog_button": cat_btn,
            "imported_files": state.imported_files,
            "status": status_lbl,
            "workspace": workspace_obj,
            "game_data_vars": {},
            "other_data_vars": {}
        }

        try:
            if accepts_kwargs:
                # Target function accepts **kwargs, pass everything
                catalog_builder.catalog_pgns(**kwargs_payload)
            else:
                # Filter payload to match ONLY the parameters catalog_pgns actually accepts
                filtered_args = {k: v for k, v in kwargs_payload.items() if k in params}
                if filtered_args:
                    catalog_builder.catalog_pgns(**filtered_args)
                else:
                    # Fallback to single path arg or parameterless call
                    try:
                        catalog_builder.catalog_pgns(filename)
                    except TypeError:
                        catalog_builder.catalog_pgns()
        except Exception as err:
            print(f"Warning: catalog_builder.catalog_pgns failed gracefully: {err}")

    # --- 3. Update Sidebar Tree (Insert newest at index 0 / TOP) ---
    tree_widget = getattr(state, 'sidebar_tree', getattr(state, 'tree', None))
    parent_node = getattr(state, 'pgn_games_node', '')

    if tree_widget and hasattr(tree_widget, 'insert'):
        pgn_item = tree_widget.insert(
            parent_node,
            0,  # Insert at index 0 so second.pgn lands above first.pgn
            text=short_name,
            open=True
        )
        if not hasattr(state, 'pgn_item_lookup'):
            state.pgn_item_lookup = {}
        state.pgn_item_lookup[filename] = pgn_item

        tree_widget.insert(pgn_item, "end", text="Game Data")

    # --- 4. Refresh Workspace Views ---
    if hasattr(state, 'workspaces'):
        # Update PGN Games Workspace
        pgn_ws = state.workspaces.get("pgn_games")
        if pgn_ws and hasattr(pgn_ws, 'load_games'):
            pgn_ws.load_games()

        # Update Search Catalog Workspace
        for cat_key in ["catalog", "search_catalog", "search"]:
            cat_ws = state.workspaces.get(cat_key)
            if cat_ws:
                if hasattr(cat_ws, 'load_catalog'):
                    cat_ws.load_catalog()
                elif hasattr(cat_ws, 'load_data'):
                    cat_ws.load_data()

        # Update Import Workspace UI if loaded
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