import gui.app_state as state
import customtkinter as ctk
from tkinter import ttk
left_frame = None
sidebar = None

pgn_node = None
pgn_games_node = None
mixed_collections_node = None
catalog_node = None
notes_node = None

sidebar_visible = True

from gui.events import on_tree_select

def toggle_sidebar():

    global sidebar_visible

    if sidebar_visible:
        left_frame.grid_remove()
        sidebar_app.grid_columnconfigure(0, minsize=0)
    else:
        left_frame.grid()
        left_frame.configure(width=250)
        sidebar_app.grid_columnconfigure(0, minsize=250)

    sidebar_visible = not sidebar_visible



def create_sidebar(app):

    global sidebar_app
    sidebar_app = app

    global left_frame
    global sidebar

    global pgn_node
    global pgn_games_node
    global mixed_collections_node
    global catalog_node
    global notes_node

    # ----------------------------
    # Sidebar Frame
    # ----------------------------

    left_frame = ctk.CTkFrame(
        app,
        width=250,
        fg_color="#374154"
    )

    left_frame.grid(
        row=1,
        column=0,
        sticky="nsew",
        padx=0,
        pady=0
    )

    app.grid_columnconfigure(0, weight=0)
    app.grid_columnconfigure(1, weight=1)

    left_frame.grid_propagate(False)



    # ----------------------------
    # Tree Style
    # ----------------------------

    style = ttk.Style()
    style.theme_use("default")

    style.configure(
        "Treeview",
        background="#273144",
        fieldbackground="#273144",
        foreground="#eeeeee",
        relief="flat",
        borderwidth=0,
        rowheight=24
    )

    style.configure(
        "Treeview.Heading",
        relief="solid",
        borderwidth=0,
        padding="2",
        background="#1f6aa5",
        foreground="#eeeeee"
    )


    style.map(
        "Treeview",
        background=[("selected", "#346934")],
        foreground=[("selected", "#dddddd")]
    )


    # ----------------------------
    # Sidebar Tree
    # ----------------------------

    sidebar = ttk.Treeview(
        left_frame,
        style="Treeview",
        show="tree"
    )
    sidebar.bind("<<TreeviewSelect>>", on_tree_select)

    sidebar.pack(
        fill="both",
        expand=True,
        padx=(0,4),
        pady=(0,4)
    )

    sidebar.bind("<<TreeviewSelect>>", on_tree_select)

    # ----------------------------
    # Root Items
    # ----------------------------

    pgn_node = sidebar.insert(
        "",
        "end",
        text="PGN Collection",
        open=True
    )

    pgn_games_node = sidebar.insert(
        "",
        "end",
        text="PGN Games",
        open=True
    )

    mixed_collections_node = sidebar.insert(
        "",
        "end",
        text="Mixed Collections",
        open=True
    )

    catalog_node = sidebar.insert(
        "",
        "end",
        text="Catalog",
        open=True
    )

    notes_node = sidebar.insert(
        "",
        "end",
        text="Notes",
        open=True
    )

    # Export to app_state

    state.left_frame = left_frame
    state.sidebar = sidebar

    state.pgn_node = pgn_node
    state.pgn_games_node = pgn_games_node
    state.mixed_collections_node = mixed_collections_node
    state.catalog_node = catalog_node
    state.notes_node = notes_node