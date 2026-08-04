# gui/menus.py

import tkinter as tk
import gui.app_state as state
from pgn.importer import import_pgn, import_fen, reset_importer_state
from catalog.catalog_manager import clear_catalog
from gui.sidebar import toggle_sidebar


def handle_clear_catalog():
    """
    1. Clears backend catalog JSON/DB state.
    2. Resets in-memory import lists & sidebar tracking.
    3. Archives/rotates active 'personal_catalog.pgn' and resets active PGN workspaces.
    4. Clears treeview UI state to show 0 games.
    """
    # 1. Clear backend catalog data
    clear_catalog()

    # 2. Wipe memory tracking (imported_files list, PGN lookups, sidebar nodes)
    reset_importer_state()

    # 3. Reset active PGN/game workspace instances using valid workspace keys
    if hasattr(state, "workspaces"):
        for key in ["pgn_games", "import"]:
            if key in state.workspaces:
                workspace_obj = state.workspaces[key]
                if hasattr(workspace_obj, "clear_and_reset_catalog"):
                    workspace_obj.clear_and_reset_catalog()
                elif hasattr(workspace_obj, "clear_table"):
                    workspace_obj.clear_table()
                elif hasattr(workspace_obj, "load_games"):
                    workspace_obj.load_games("personal_catalog.pgn")

    # 4. Refresh Catalog/Search workspace view
    if hasattr(state, "workspaces"):
        for key in ["catalog", "search_catalog", "search"]:
            if key in state.workspaces:
                workspace_obj = state.workspaces[key]
                if hasattr(workspace_obj, "load_catalog"):
                    workspace_obj.load_catalog()
                elif hasattr(workspace_obj, "load_data"):
                    workspace_obj.load_data()


def handle_import_pgn():
    """Opens the PGN import dialog first, updates app state, then refreshes and shows the workspace."""
    from gui.workspace import show_workspace

    # 1. Run file dialog to pick file and update state.current_filename
    import_pgn()

    # 2. Switch view to import workspace
    show_workspace("import")

    # 3. Trigger immediate refresh on the import workspace instance
    if hasattr(state, "workspaces") and "import" in state.workspaces:
        state.workspaces["import"].refresh_view()


def handle_import_fen():
    """Opens the FEN import dialog first, updates app state, then refreshes and shows the workspace."""
    from gui.workspace import show_workspace

    import_fen()
    show_workspace("import")

    if hasattr(state, "workspaces") and "import" in state.workspaces:
        state.workspaces["import"].refresh_view()


def show_catalog():
    """Switches to the Search Catalog Workspace and reloads latest data."""
    from gui.workspace import show_workspace

    target_key = "catalog"
    if hasattr(state, "workspaces"):
        for key in ["catalog", "search_catalog", "search"]:
            if key in state.workspaces:
                target_key = key
                break

    show_workspace(target_key)

    if hasattr(state, "workspaces") and target_key in state.workspaces:
        workspace_obj = state.workspaces[target_key]
        if hasattr(workspace_obj, "load_catalog"):
            workspace_obj.load_catalog()
        elif hasattr(workspace_obj, "load_data"):
            workspace_obj.load_data()


def show_analyze():
    """Switches to the PGN Games Workspace (Games Data)."""
    from gui.workspace import show_workspace

    target_key = "pgn_games"
    if hasattr(state, "workspaces"):
        for key in ["pgn_games", "games", "analysis"]:
            if key in state.workspaces:
                target_key = key
                break

    show_workspace(target_key)

    if hasattr(state, "workspaces") and target_key in state.workspaces:
        workspace_obj = state.workspaces[target_key]
        if hasattr(workspace_obj, "refresh_view"):
            workspace_obj.refresh_view()
        elif hasattr(workspace_obj, "load_games"):
            workspace_obj.load_games()


def create_menu(app):
    menu_bar = tk.Menu(app)
    app.config(menu=menu_bar)

    # ----------------------------
    # File Menu
    # ----------------------------
    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="File", menu=file_menu)

    file_menu.add_command(label="Import PGN...", command=handle_import_pgn)
    file_menu.add_command(label="Import FEN...", command=handle_import_fen)
    file_menu.add_command(label="Export PGN")

    file_menu.add_separator()
    file_menu.add_command(label="Catalog", command=show_catalog)
    file_menu.add_command(label="Clear Catalog", command=handle_clear_catalog)

    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=app.quit)

    # ----------------------------
    # Edit Menu
    # ----------------------------
    edit_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Edit", menu=edit_menu)

    # ----------------------------
    # View Menu
    # ----------------------------
    view_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="View", menu=view_menu)

    view_menu.add_command(
        label="Show / Hide Sidebar",
        command=toggle_sidebar
    )

    # ----------------------------
    # Tools Menu
    # ----------------------------
    tools_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Tools", menu=tools_menu)

    tools_menu.add_command(
        label="Catalog",
        command=show_catalog
    )
    tools_menu.add_command(
        label="Analyze",
        command=show_analyze
    )

    # ----------------------------
    # Help Menu
    # ----------------------------
    help_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Help", menu=help_menu)