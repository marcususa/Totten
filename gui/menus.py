import tkinter as tk

from pgn.importer import import_pgn, import_fen
from catalog.catalog_manager import clear_catalog
from gui.sidebar import toggle_sidebar
from gui.catalog_workspace import show_catalog_workspace

def create_menu(app):

    menu_bar = tk.Menu(app)

    app.config(menu=menu_bar)

    # ----------------------------
    # File Menu
    # ----------------------------

    file_menu = tk.Menu(menu_bar, tearoff=0)

    menu_bar.add_cascade(
        label="File",
        menu=file_menu
    )

    file_menu.add_command(
        label="Import PGN...",
        command=import_pgn
    )

    file_menu.add_command(
        label="Import FEN...",
        command=import_fen
    )

    file_menu.add_command(label="Export PGN")

    file_menu.add_separator()

    file_menu.add_command(
        label="Clear Catalog",
        command=clear_catalog
    )

    file_menu.add_separator()

    file_menu.add_command(
        label="Exit",
        command=app.quit
    )

    # ----------------------------
    # Edit Menu
    # ----------------------------

    edit_menu = tk.Menu(menu_bar, tearoff=0)

    menu_bar.add_cascade(
        label="Edit",
        menu=edit_menu
    )

    # ----------------------------
    # View Menu
    # ----------------------------

    view_menu = tk.Menu(menu_bar, tearoff=0)

    menu_bar.add_cascade(
        label="View",
        menu=view_menu
    )

    view_menu.add_command(
        label="Show / Hide Sidebar",
        command=toggle_sidebar
    )

    # ----------------------------
    # Tools Menu
    # ----------------------------

    tools_menu = tk.Menu(menu_bar, tearoff=0)

    menu_bar.add_cascade(
        label="Tools",
        menu=tools_menu
    )

    tools_menu.add_command(
        label="Catalog",
        command=show_catalog_workspace
    )

    tools_menu.add_command(label="Sort")
    tools_menu.add_command(label="Analyze")

    # ----------------------------
    # Help Menu
    # ----------------------------

    help_menu = tk.Menu(menu_bar, tearoff=0)

    menu_bar.add_cascade(
        label="Help",
        menu=help_menu
    )
