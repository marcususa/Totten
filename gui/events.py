from gui.import_workspace import show_import_workspace
from catalog.catalog_builder import catalog_pgns
from gui.catalog_workspace import show_catalog_workspace
from pgn.importer import import_pgn
import customtkinter as ctk
import gui.app_state as state

from gui.pgn_workspace import show_pgn_workspace
from gui.pgn_games_workspace import show_pgn_games_workspace
from gui.catalog_workspace import show_catalog_workspace


def on_tree_select(event):
    global notes_box

    item = state.sidebar.focus()
    text = state.sidebar.item(item, "text")

    parent = state.sidebar.parent(item)

    if text == "Back to Import":
        show_import_workspace(
            state.current_filename,
            catalog_pgns,
            import_pgn,
            show_catalog_workspace,
            state.imported_files,
            state.status
        )
        return

    # User clicked a PGN file or Back to Import
    if parent == state.pgn_node:

        if text == "Back to Import":
            print("Back to Import clicked")
            return

        filename = state.pgn_lookup.get(text)

        if filename:
            show_pgn_workspace(filename)

        return


    if text == "Game Data":

        grandparent = state.sidebar.parent(parent)

        if grandparent == state.pgn_node:
            print("PGN Collection:", state.sidebar.item(parent, "text"))

        elif grandparent == state.pgn_games_node:

            filename = state.sidebar.item(parent, "text")

            show_pgn_games_workspace(filename)
            return

    # User clicked one of the PGN's categories
    if state.sidebar.parent(parent) == state.pgn_node:
        return

    print("Item:", item)
    print("Text:", text)
    print("Parent:", parent)
    print("Clicked:", text)

    if text != "Notes" and "notes_box" in globals():
        state.save_notes()

    # Clear the workspace
    for widget in state.workspace.winfo_children():
        widget.destroy()

    if text == "Notes":
        notes_box = ctk.CTkTextbox(state.workspace)
        notes_box.pack(fill="both", expand=True, padx=10, pady=10)

        try:
            with open("notes.txt", "r") as f:
                notes_box.insert("1.0", f.read())
        except FileNotFoundError:
            pass

    elif text == "PGN Collection":
        label = ctk.CTkLabel(
            state.workspace,
            text="PGN Collection",
            font=("Arial", 24)
        )
        label.pack(expand=True)

    elif text == "Catalog":

        show_catalog_workspace()

