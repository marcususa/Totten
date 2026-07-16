import os
from tkinter import messagebox
import gui.app_state as state
from gui.catalog_workspace import show_catalog_workspace

def clear_catalog():

    answer = messagebox.askyesno(
        "Clear Catalog",
        "Delete the entire opening catalog?"
    )

    if not answer:
        return

    if os.path.exists("personal_catalog.json"):
        os.remove("personal_catalog.json")

    state.cataloged_files.clear()
    state.imported_files.clear()
    state.pgn_lookup.clear()
    state.pgn_item_lookup.clear()
    state.pgn_games_lookup.clear()
    for item in state.sidebar.get_children(state.pgn_node):
        state.sidebar.delete(item)
    for item in state.sidebar.get_children(state.pgn_games_node):
        state.sidebar.delete(item)

    state.status.configure(
        text="Catalog cleared."

    )

    show_catalog_workspace()
