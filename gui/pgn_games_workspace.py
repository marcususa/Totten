import gui.app_state as state
import customtkinter as ctk
from tkinter import ttk
from pathlib import Path
import chess.pgn

from core.constants import MAX_PLIES
from catalog.continuation import format_continuation

def show_pgn_games_workspace(filename):
    print("Opening PGN:", filename)

    preview_lookup = {}

    # Clear workspace
    for widget in state.workspace.winfo_children():
        widget.destroy()

    # Title
    title = ctk.CTkLabel(
        state.workspace,
        text=Path(filename).name,
        font=("Arial", 24)
    )
    title.pack(pady=10)

    # Create PGN tree
    pgn_tree = ttk.Treeview(
        state.workspace,
        show="tree"
    )

    pgn_tree.pack(
        fill="both",
        expand=True,
        padx=10,
        pady=10
    )

   #### After the tree

    moves_box = ctk.CTkTextbox(
        state.workspace,
        height=250,
        wrap="word"
    )

    moves_box.pack(
        fill="x",
        padx=15,
        pady=(0, 15)
    )

    def toggle_game(event):

        item = pgn_tree.identify_row(event.y)

        if not item:
            return

        text = pgn_tree.item(item, "text")
        moves_box.delete("1.0", "end")

        if item in preview_lookup:
            moves_box.insert("1.0", preview_lookup[item])

        # Only toggle game rows
        if text.startswith("□ "):
            new_text = text.replace("□ ", "■ ", 1)

            pgn_tree.item(
                item,
                text=new_text
            )

        elif text.startswith("■ "):
            new_text = text.replace("■ ", "□ ", 1)

            pgn_tree.item(
                item,
                text=new_text
            )

    pgn_tree.bind(
        "<Button-1>",
        toggle_game
    )
    data = state.pgn_games_lookup.get(filename, [])
    print(data)

    game_number = 1

    for game in data:

        white = game.get("White", "?")
        black = game.get("Black", "?")
        
        game_node = pgn_tree.insert(
            "",
            "end",
            text=f"□ Game {game_number}: {white} - {black}"
        )

        game_text = ""

        tag_order = [
            "Event",
            "Site",
            "Date",
            "Round",
            "White",
            "Black",
            "Result",
            "WhiteTitle",
            "BlackTitle",
            "WhiteElo",
            "BlackElo",
            "WhiteFideId",
            "BlackFideId",
            "ECO",
            "Opening",
            "Variation",
            "EventDate",
            "EventType",
        ]

        for tag in tag_order:
            if tag in game:
                game_text += f'[{tag} "{game[tag]}"]\n'

        # Any unknown (amber) tags
        for tag, value in game.items():
            if tag not in tag_order and tag != "Moves":
                game_text += f'[{tag} "{value}"]\n'

        if "Moves" in game:
            game_text += "\n"
            game_text += game["Moves"]

        preview_lookup[game_node] = game_text
        print(game_text)

        game_number += 1









