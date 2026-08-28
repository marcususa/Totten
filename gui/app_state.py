# gui/app_state.py

import sys
import inspect
import importlib.util
from pathlib import Path
import chess.pgn
from tkinter import filedialog
from gui.statusbar import set_status_message, start_progress, update_progress, stop_progress

# --- Central Color Palette & Theme Constants ---
COLORS = {
    "bg_dark": "#0f172a",  # Main panels, headers, card backgrounds
    "bg_textbox": "#1e293b",  # Textboxes and tooltips background
    "border_color": "#334155",  # Borders, dividers, secondary elements
    "text_main": "#f8fafc",  # Primary foreground text color
    "text_muted": "#94a3b8",  # Placeholder labels, titles, inactive text
    "accent_blue": "#2e4a8c",  # Primary buttons, active selection
    "accent_hover": "#4870cd",  # Button hover state
    "secondary_btn": "#334155",  # Popout and neutral buttons
    "secondary_hover": "#475569",  # Neutral button hover state

    # Engine / Move evaluation tags
    "eval_red": "#FF4444",
    "eval_orange": "#FFA500",
    "eval_green": "#00C851",
    "eval_lightblue": "#33b5e5",
    "active_move_bg": "#660000",
}

# Application State Global Variables and Workspace Management Bridges
app_root = None
app_master = None
workspace = None
left_frame = None
analysis_workspace = None
catalog_workspace = None
mixed_workspace = None
patterns_workspace = None

# Importer and Catalog Data tracking
imported_files = []
pgn_games_lookup = {}
pgn_lookup = {}
current_filename = None
sidebar_tree = None
tree = None
pgn_item_lookup = {}

# Active State References
active_game = None
active_analysis_game = None
active_category_source = None
all_games = None

# Resolve path to catalog_builder.py in cousin folder /catalog/
CATALOG_BUILDER_PATH = Path(__file__).resolve().parent.parent / "catalog" / "catalog_builder.py"

spec = importlib.util.spec_from_file_location("catalog_builder", CATALOG_BUILDER_PATH)
catalog_builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(catalog_builder)


def reset_importer_state():
    """Resets in-memory tracking lists and removes imported nodes from the sidebar tree."""
    global imported_files, pgn_games_lookup, pgn_lookup, current_filename, pgn_item_lookup
    imported_files = []
    pgn_games_lookup = {}
    pgn_lookup = {}
    current_filename = None

    tree_widget = sidebar_tree if sidebar_tree else tree

    if tree_widget and hasattr(tree_widget, 'delete'):
        for item_id in pgn_item_lookup.values():
            try:
                tree_widget.delete(item_id)
            except Exception:
                pass
        pgn_item_lookup = {}


def force_search_catalog_view():
    """Placeholder for maintaining view stability during imports."""
    pass


def import_pgn():
    print("1 - import_pgn started")

    filename = filedialog.askopenfilename(
        title="Import PGN",
        filetypes=[("PGN Files", "*.pgn"), ("All Files", "*.*")]
    )

    if not filename:
        return

    root_window = app_root

    if root_window:
        try:
            root_window.update()
        except Exception:
            pass

    print(f"2 - Selected: {filename}")
    short_name = Path(filename).name

    # Check duplicate in memory
    if filename in imported_files:
        set_status_message(f"{short_name} is already imported.")
        return

    # Start progress bar for Phase 1 (Reading file)
    start_progress(indeterminate=False)
    set_status_message(f"Reading {short_name}...")

    # Smoothly climb from 0% to 48% while reading
    def start_phase_1_ticker():
        def tick(val=0.0):
            if val < 0.48:
                new_val = val + 0.02
                update_progress(new_val)
                if root_window and hasattr(root_window, "after"):
                    root_window.after(200, lambda: tick(new_val))

        tick(0.0)

    start_phase_1_ticker()

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
        stop_progress()
        set_status_message(f"Failed to read {short_name}")
        return

    pgn_games_lookup[filename] = games
    imported_files.insert(0, filename)
    pgn_lookup[short_name] = filename
    current_filename = filename

    print(f"3 - Successfully loaded {len(games)} games from {short_name}")

    # --- 2. Handle progress animation events from background thread ---
    def handle_catalog_progress(event_type):
        if event_type == "phase_1_complete":
            update_progress(0.5)
            set_status_message("Saving to database...")

            # Smoothly climb from 50% to 95% while DuckDB saves
            def tick_db(val=0.5):
                if val < 0.95:
                    new_val = val + 0.02
                    update_progress(new_val)
                    if root_window and hasattr(root_window, "after"):
                        root_window.after(300, lambda: tick_db(new_val))

            tick_db(0.5)

        elif event_type == "phase_2_complete":
            update_progress(1.0)

    def on_catalog_complete(added_count):
        print(f"Catalog builder processed {added_count} new games.")
        update_progress(1.0)
        stop_progress()

        # Update Sidebar Tree
        tree_widget = sidebar_tree if sidebar_tree else tree

        if tree_widget and hasattr(tree_widget, 'insert'):
            try:
                pgn_item = tree_widget.insert(
                    "",
                    0,
                    text=short_name,
                    open=True
                )
                pgn_item_lookup[filename] = pgn_item
                tree_widget.insert(pgn_item, "end", text="Game Data")
            except Exception:
                pass

        set_status_message(f"Added {short_name} ({len(games)} games) to catalog.")

    # --- 3. Kick off database building in the background thread ---
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
        stop_progress()


def import_fen():
    print("Import FEN selected")


# --- Added Catalog -> Analysis Linking Bridges ---

def set_active_analysis_game(game_obj):
    """Directly routes a game selected in Search Catalog to the Analysis view."""
    global active_game
    active_game = game_obj
    analysis_ws = analysis_workspace

    if analysis_ws:
        if hasattr(analysis_ws, 'load_game'):
            analysis_ws.load_game(game_obj)
        elif hasattr(analysis_ws, 'set_game'):
            analysis_ws.set_game(game_obj)
        elif hasattr(analysis_ws, 'set_active_game'):
            analysis_ws.set_active_game(game_obj)


# Define module-level flags to capture filtered subsets safely
active_group_games = None
active_focus_game = None

def load_game_group_and_switch(games_list, focused_game=None):
    """Stores the filtered subset and triggers workspace creation so it loads fully populated."""
    global active_game, active_analysis_game, all_games, active_group_games, active_focus_game

    if games_list:
        all_games = games_list
        active_game = focused_game if focused_game else games_list[0]
        active_analysis_game = active_game
        active_group_games = games_list
        active_focus_game = active_game

    show_workspace("catalog_analysis")



def set_active_mixed_collection(game_list, focused_game=None):
    """Passes an entire collection of games to the mixed workspace."""
    global mixed_workspace

    if not mixed_workspace or not hasattr(mixed_workspace, "load_mixed_collection"):
        show_workspace("mixed")

    if mixed_workspace and hasattr(mixed_workspace, "load_mixed_collection"):
        mixed_workspace.load_mixed_collection(game_list, target_game=focused_game)


def _export_games_to_patterns_pgn(games_list):
    """Writes the selected collection of games to pgn/patterns_analysis.pgn on disk."""
    pgn_dir = Path(__file__).resolve().parent.parent / "pgn"
    pgn_dir.mkdir(parents=True, exist_ok=True)
    pgn_path = pgn_dir / "patterns_analysis.pgn"

    try:
        with open(pgn_path, "w", encoding="utf-8") as f:
            for item in games_list:
                game = item.get("game_object") if isinstance(item, dict) else item
                if game and isinstance(game, chess.pgn.Game):
                    exporter = chess.pgn.FileExporter(f)
                    game.accept(exporter)
    except Exception as e:
        print(f"Error exporting patterns PGN: {e}")


def set_active_patterns_collection(games_list, focused_game=None):
    """Saves selected pattern games to disk and navigates to the analysis workspace."""
    global active_analysis_subset, active_target_game
    active_analysis_subset = games_list
    active_target_game = None

    # 1. Export PGN to pgn/patterns_analysis.pgn
    _export_games_to_patterns_pgn(games_list)

    # 2. Switch workspace UI to patterns_analysis
    new_ws = show_workspace("patterns_analysis")

    # 3. Reload PGN tree and auto-select Game #1 into the text box & board
    if new_ws:
        if hasattr(new_ws, "reload_pgn"):
            new_ws.reload_pgn()

        if hasattr(new_ws, "select_first_game"):
            new_ws.select_first_game()

def switch_workspace(workspace_factory, *args, **kwargs):
    """Destroys the current workspace frame and instantiates a new one in column 1."""
    global workspace, analysis_workspace
    if workspace and hasattr(workspace, "destroy"):
        workspace.destroy()

    parent_master = app_master if app_master else app_root
    if not parent_master:
        return None

    new_ws = workspace_factory(parent_master, *args, **kwargs)
    new_ws.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

    workspace = new_ws
    analysis_workspace = new_ws
    return new_ws


def show_workspace(workspace_name):
    """Switches workspaces based on string identifier, routing each to its proper module."""
    from gui.catalog_analysis import create_workspace as create_catalog_ws
    from gui.mixed_analysis import create_mixed_workspace
    from gui.patterns_workspace import create_patterns_workspace
    from gui.patterns_analysis import create_patterns_analysis_workspace

    global catalog_workspace, mixed_workspace, patterns_workspace

    if workspace_name in ("catalog", "catalog_analysis", "search_catalog_workspace"):
        catalog_workspace = switch_workspace(create_catalog_ws)
        return catalog_workspace
    elif workspace_name in ("mixed", "mixed_analysis", "edit_workspace"):
        mixed_workspace = switch_workspace(create_mixed_workspace)
        return mixed_workspace
    elif workspace_name in ("patterns", "patterns_workspace"):
        patterns_workspace = switch_workspace(create_patterns_workspace)
        return patterns_workspace
    elif workspace_name == "patterns_analysis":
        return switch_workspace(create_patterns_analysis_workspace)