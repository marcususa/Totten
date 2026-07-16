import customtkinter as ctk
import tkinter as tk
from pathlib import Path
import chess.pgn

import gui.app_state as state

def show_import_workspace(
    filename,
    catalog_pgns,
    import_pgn,
    show_catalog_workspace,
    imported_files,
    status
):

    global add_catalog_button, import_button, catalog_button

    print(f"Opening {filename}")

    # Clear workspace
    for widget in state.workspace.winfo_children():

        widget.destroy()


    # Scan the entire PGN and collect every unique header tag
    all_tags = set()

    with open(filename, encoding="utf-8") as pgn_file:
        while True:
            game = chess.pgn.read_game(pgn_file)
            if game is None:
                break

            all_tags.update(game.headers.keys())

    # No games found
    if not all_tags:
        return
    print("all_tags =", all_tags)
    print("EventType" in all_tags)
    print("EventDate" in all_tags)
    print("Number of unique tags =", len(all_tags))
    game_data_tags = []

    # Event
    if "Event" in all_tags:
        game_data_tags.append("Event")

    # Round
    if "Round" in all_tags:
        game_data_tags.append("Round")

    # Result
    if "Result" in all_tags:
        game_data_tags.append("Result")

    # Title (WhiteTitle and/or BlackTitle)
    if "WhiteTitle" in all_tags or "BlackTitle" in all_tags:
        game_data_tags.append("Title")

    other_data_tags = []

    column1_groups = {
        "Event",
        "Site",
        "Date",
        "Round",
        "Players",
        "Result",
        "Title",
    }

    # Clear the workspace
    for widget in state.workspace.winfo_children():
        widget.destroy()

    # Title
    title = ctk.CTkLabel(
        state.workspace,
        text=f"{Path(filename).name}",
        font=("Arial", 24, "bold")
    )
    title.pack(
        anchor="w",
        padx=20,
        pady=(10, 20)
    )

    # Button frame
    button_frame = ctk.CTkFrame(state.workspace, fg_color="transparent")
    button_frame.pack(anchor="w", padx=20, pady=5)
    ACTIVE_BUTTON_COLOR = "#a51f3d"
    ACTIVE_BUTTON_HOVER = "#8c1933"

    # Import, Add to Catalog, Catalog buttons
    add_catalog_button = ctk.CTkButton(
        button_frame,
        text="Add to Catalog",
        command=lambda: catalog_pgns(
            add_catalog_button,
            import_button,
            catalog_button,
            imported_files,
            status,
            state.workspace
        ),
        # fg_color = "#a51f3d",
        hover_color=ACTIVE_BUTTON_HOVER,
        text_color="white"
    )

    add_catalog_button.pack(side="left", padx=(10, 0))

    import_button = ctk.CTkButton(
        button_frame,
        text="Import",
        command=import_pgn,
        # fg_color = "#a51f3d",
        hover_color=ACTIVE_BUTTON_HOVER,
        text_color="white"
    )

    import_button.pack(side="left", padx=(10, 0))

    catalog_button = ctk.CTkButton(
        button_frame,
        text="Catalog",
        command=show_catalog_workspace,
        # fg_color = "#a51f3d",
        hover_color=ACTIVE_BUTTON_HOVER,
        text_color="white"
    )

    catalog_button.pack(side="left", padx=(10, 0))

    add_catalog_button.configure(state="normal")

    import_button.configure(state="disabled")

    catalog_button.configure(state="disabled")

    # Main container

    options_frame = ctk.CTkFrame(state.workspace,
                                 fg_color="#283858"
                                 )  # game_data_panel
    options_frame.pack(fill="x", padx=20, pady=10)

    # Three columns
    game_data_frame = ctk.CTkFrame(options_frame,  # fg_color="#34426e" fg_color="#00ff00"
                                   fg_color="#283858")  # column color over game_data_panel_background
    other_data_frame = ctk.CTkFrame(options_frame, fg_color="#283858")  # same
    depth_rating = ctk.CTkFrame(options_frame, fg_color="#283858")  # same

    # Pack the columns
    for col in (game_data_frame, other_data_frame, depth_rating):
        col.pack(side="left", anchor="n", padx=(10, 30), pady=10)

    # ---------- Column 1 ----------
    ctk.CTkLabel(
        game_data_frame,
        text="Game Data",
        font=("Arial", 16, "bold")
    ).pack(anchor="w", pady=(0, 10))

    game_data_vars = {}

    for tag in game_data_tags:
        print("FINAL other_data_tags =", other_data_tags)
        game_data_vars[tag] = tk.BooleanVar(value=False)

        ctk.CTkCheckBox(
            game_data_frame,
            text=tag,
            variable=game_data_vars[tag],
            fg_color="#68aa68",
            hover_color="#347434",
            border_color="#68aa68",
            checkmark_color="#346834",
            text_color="#aabbaa"
        ).pack(anchor="w", pady=4)

    # ---------- Column 2 ----------

    ctk.CTkLabel(
        other_data_frame,
        text="",
        height=28
    ).pack(anchor="w", pady=(0, 10))

    other_data_tags = [
        "Elo",
        "FideId",
        "EventDate",
        "EventType"
    ]
    other_data_vars = {}

    print(other_data_tags)
    print(len(other_data_tags))

    print("other_data_tags =", other_data_tags)
    print("Number of displayed tags =", len(other_data_tags))

    # Remove tags that are already represented in Columns 1 and 2
    known_tags = {
        "Fen",
        "White", "Black",
        "Result",
        "ECO",
        "Opening",
        "Variation",
        "WhiteTitle", "BlackTitle",
        "WhiteElo", "BlackElo",
        "WhiteFideId", "BlackFideId",
        "EventDate",
        "EventType"
    }

    # Standard tags that belong in Column 2
    recognized_other_tags = [
        tag for tag in (
            "WhiteFideId", "BlackFideId",
            "EventDate",
            "EventType"
        )
        if tag in all_tags
    ]

    # Unknown or misspelled tags
    unknown_tags = sorted(
        tag for tag in all_tags
        if tag not in known_tags
    )
    # Show recognized tags first
    other_data_tags.extend(recognized_other_tags)

    # Then show unknown tags
    other_data_tags.extend(unknown_tags)

    other_data_tags = [
        tag for tag in other_data_tags
        if not tag.startswith(("White", "Black"))
    ]

    other_data_tags = [
        tag for tag in other_data_tags
        if tag not in column1_groups
    ]

    for tag in other_data_tags:
        other_data_vars[tag] = tk.BooleanVar(value=False)

        # Amber if the tag is unknown
        if tag in unknown_tags:

            ctk.CTkCheckBox(
                other_data_frame,
                text=tag,
                variable=other_data_vars[tag],
                fg_color="#d98c00",
                hover_color="#b36f00",
                border_color="#d98c00",
                checkmark_color="#8a5600",
                text_color="#ffcc66"
            ).pack(anchor="w", pady=4)

        # Blue if the tag is recognized
        else:

            ctk.CTkCheckBox(
                other_data_frame,
                text=tag,
                variable=other_data_vars[tag],
                fg_color="#1f6aa5",
                hover_color="#2d5a90",
                border_color="#3d6ca8",
                checkmark_color="#214c7a",
                text_color="#82b8ff"
            ).pack(anchor="w", pady=4)

    # ---------- Column 3 ----------
    ctk.CTkLabel(
        depth_rating,
        text="Depth Rating"
    ).pack(anchor="w", pady=(35, 0))

    depth_menu = ctk.CTkOptionMenu(
        depth_rating,
        values=[
            "15 Moves",
            "20 Moves",
            "25 Moves",
            "30 Moves",
            "All Moves"
        ]
    )
    depth_menu.pack(anchor="w")
    depth_menu.set("15 Moves")

    ctk.CTkLabel(
        depth_rating,
        text="Rating Filter"
    ).pack(anchor="w", pady=(20, 0))

    rating_filter = ctk.CTkOptionMenu(
        depth_rating,
        values=[
            "2100+",
            "2400+",
            "2600+",
            "All"
        ]
    )
    rating_filter.pack(anchor="w")
    rating_filter.set("2100+")

    state.game_data_vars = game_data_vars
    state.other_data_vars = other_data_vars
    state.depth_menu = depth_menu
    state.rating_filter = rating_filter