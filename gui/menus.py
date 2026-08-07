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
    clear_catalog()
    reset_importer_state()

    if hasattr(state, "workspaces"):
        for key in ["pgn_games", "edit"]:
            if key in state.workspaces:
                workspace_obj = state.workspaces[key]
                if hasattr(workspace_obj, "clear_and_reset_catalog"):
                    workspace_obj.clear_and_reset_catalog()
                elif hasattr(workspace_obj, "clear_table"):
                    workspace_obj.clear_table()
                elif hasattr(workspace_obj, "load_games"):
                    workspace_obj.load_games("personal_catalog.pgn")

    if hasattr(state, "workspaces"):
        for key in ["catalog", "search_catalog", "search"]:
            if key in state.workspaces:
                workspace_obj = state.workspaces[key]
                if hasattr(workspace_obj, "load_catalog"):
                    workspace_obj.load_catalog()
                elif hasattr(workspace_obj, "load_data"):
                    workspace_obj.load_data()


def handle_import_pgn():
    """Ingests PGN directly into catalog, then jumps straight to Search Catalog Workspace."""
    import_pgn()
    show_catalog()


def handle_import_fen():
    """Ingests FEN directly, then jumps straight to Search Catalog Workspace."""
    import_fen()
    show_catalog()


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


def show_edit_workspace():
    """Switches to the Edit Workspace for playlists, FEN overrides, and tag curation."""
    from gui.workspace import show_workspace

    target_key = "edit"
    if hasattr(state, "workspaces"):
        for key in ["edit", "edit_workspace"]:
            if key in state.workspaces:
                target_key = key
                break

    show_workspace(target_key)

    if hasattr(state, "workspaces") and target_key in state.workspaces:
        workspace_obj = state.workspaces[target_key]
        if hasattr(workspace_obj, "refresh_view"):
            workspace_obj.refresh_view()


def show_analysis():
    """Switches to the Analysis Workspace."""
    from gui.workspace import show_workspace

    target_key = "analysis"
    if hasattr(state, "workspaces"):
        for key in ["analysis", "pgn_games", "games"]:
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


def show_patterns():
    """Switches to the Patterns Workspace."""
    from gui.workspace import show_workspace
    show_workspace("patterns")


def show_mixed_collections():
    """Switches to the Mixed Collections Workspace."""
    from gui.workspace import show_workspace
    show_workspace("mixed_collections")


def show_calendar():
    """Switches to the Calendar Workspace."""
    from gui.workspace import show_workspace
    show_workspace("calendar")


def show_about_dialog():
    """Displays application About information."""
    top = tk.Toplevel()
    top.title("About ChessMusic4")
    top.geometry("320x200")
    top.configure(bg="#172134")

    lbl = tk.Label(top, text="ChessMusic4\n\nModular Chess Analysis, Catalog, & Audio Suite\nVersion 2026.8",
                   bg="#172134", fg="#f8fafc", justify="center")
    lbl.pack(expand=True, padx=20, pady=20)

    btn = tk.Button(top, text="Close", command=top.destroy, bg="#334155", fg="#f8fafc", relief="flat")
    btn.pack(pady=(0, 15))


def create_menu(app):
    menu_bar = tk.Menu(app)
    app.config(menu=menu_bar)

    # ----------------------------
    # File Menu
    # ----------------------------
    file_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="File", menu=file_menu)

    file_menu.add_command(label="Import PGN", command=handle_import_pgn)
    file_menu.add_command(label="Import FEN", command=handle_import_fen)
    file_menu.add_command(label="Export PGN")
    file_menu.add_command(label="Clear Catalog", command=handle_clear_catalog)
    file_menu.add_command(label="Exit", command=app.quit)

    # ----------------------------
    # Edit Menu
    # ----------------------------
    edit_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Edit", menu=edit_menu)

    edit_menu.add_command(label="PGN & Playlists", command=show_edit_workspace)

    # ----------------------------
    # View Menu
    # ----------------------------
    view_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="View", menu=view_menu)

    view_menu.add_command(label="Catalog", command=show_catalog)
    view_menu.add_command(label="Mixed Collections", command=show_mixed_collections)
    view_menu.add_command(label="Calendar", command=show_calendar)
    view_menu.add_command(label="Show / Hide Sidebar", command=toggle_sidebar)

    # ----------------------------
    # Tools Menu
    # ----------------------------
    tools_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Tools", menu=tools_menu)

    tools_menu.add_command(label="Analysis", command=show_analysis)
    tools_menu.add_command(label="Patterns", command=show_patterns)
    tools_menu.add_command(label="Engines", command=show_edit_workspace)

    # ----------------------------
    # Help Menu
    # ----------------------------
    help_menu = tk.Menu(menu_bar, tearoff=0)
    menu_bar.add_cascade(label="Help", menu=help_menu)

    help_menu.add_command(label="About", command=show_about_dialog)