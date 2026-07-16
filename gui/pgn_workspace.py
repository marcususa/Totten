import gui.app_state as state
import customtkinter as ctk
from tkinter import ttk
from pathlib import Path
import chess.pgn

from core.constants import MAX_PLIES
from catalog.continuation import format_continuation


def show_pgn_workspace(filename):
    print("Opening PGN:", filename)

    preview_lookup = {}

    # Clear workspace
    for widget in state.workspace.winfo_children():
        widget.destroy()

    loading_label = ctk.CTkLabel(
        state.workspace,
        text="Loading PGN...",
        font=("Arial", 18)
    )

    loading_label.pack(pady=20)

    state.workspace.update()

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

    # Moves preview box
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

        if text.startswith("□ "):
            pgn_tree.item(item, text=text.replace("□ ", "■ ", 1))

        elif text.startswith("■ "):
            pgn_tree.item(item, text=text.replace("■ ", "□ ", 1))

    pgn_tree.bind("<Button-1>", toggle_game)

    # Read PGN games
    with open(filename, encoding="utf-8") as pgn_file:
        print("Successfully opened file")

        game_number = 1

        while True:
            game = chess.pgn.read_game(pgn_file)

            if game is None:
                break

            headers = game.headers

            white = headers.get("White", "?")
            black = headers.get("Black", "?")

            game_node = pgn_tree.insert(
                "",
                "end",
                text=f"□ Game {game_number}: {white} - {black}"
            )

            board = game.board()
            san_moves = []

            for move in game.mainline_moves():
                san_moves.append(board.san(move))
                board.push(move)

            preview_moves = san_moves[:MAX_PLIES]

            preview_lines = format_continuation(
                preview_moves,
                1
            )

            result = headers.get("Result", "")

            preview_text = f"{white} vs {black}\n\n" + " ".join(preview_lines)
            print(preview_text)

            if result:
                preview_text += f" {result}"

            preview_lookup[game_node] = preview_text

            game_number += 1

        loading_label.destroy()