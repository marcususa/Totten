import customtkinter as ctk
import gui.app_state as state
from gui.search_catalog_workspace import SearchCatalogWorkspace
from gui.pgn_games_workspace import show_pgn_games_workspace
from gui.import_workspace import ImportWorkspace


def on_tree_select(event):
    global notes_box

    item = state.sidebar.focus()
    text = state.sidebar.item(item, "text")
    parent = state.sidebar.parent(item)

    # Save notes if leaving Notes view
    if text != "Notes" and "notes_box" in globals():
        state.save_notes()

    # Clear current workspace frame
    if hasattr(state, 'workspace') and state.workspace:
        for widget in state.workspace.winfo_children():
            widget.destroy()

    # 1. Notes
    if text == "Notes":
        notes_box = ctk.CTkTextbox(state.workspace)
        notes_box.pack(fill="both", expand=True, padx=10, pady=10)
        try:
            with open("notes.txt", "r") as f:
                notes_box.insert("1.0", f.read())
        except FileNotFoundError:
            pass

    # 2. Catalog Root
    elif text == "Catalog":
        view = SearchCatalogWorkspace(state.workspace, app_state=state)
        view.pack(fill="both", expand=True)

    # 3. Game Data
    elif text == "Game Data":
        view = ImportWorkspace(state.workspace, app_state=state)
        view.pack(fill="both", expand=True)

    # 4. PGN Games (loads pgn_games_workspace.py)
    elif text == "PGN Games" or parent == getattr(state, 'pgn_games_node', None):
        filename = text if parent == getattr(state, 'pgn_games_node', None) else None
        show_pgn_games_workspace(filename)

    # 5. Default Fallback
    else:
        show_pgn_games_workspace(None)