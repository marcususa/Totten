# File module titled "mixed_analysis.py"

import chess
import chess.pgn
import customtkinter as ctk
from gui.chess_board import ChessBoardWidget

class MixedAnalysisMixin:
    def init_mixed_bindings(self):
        """Explicit tree bindings for mixed collection analysis view."""
        if hasattr(self, "pgn_tree") and self.pgn_tree:
            self.pgn_tree.bind("<Button-1>", lambda e: self.toggle_game(e))
            self.pgn_tree.bind("<FocusIn>", lambda e: "break")

        self.after(100, self._bind_global_keys)

    def _bind_global_keys(self):
        top = self.winfo_toplevel()
        top.bind("<Left>", lambda e: self.on_prev_move())
        top.bind("<Right>", lambda e: self.on_next_move())
        top.bind("<Up>", lambda e: self.on_first_move())
        top.bind("<Down>", lambda e: self.on_last_move())

    def load_mixed_collection(self, games_list, target_game=None):
        """Populates the tree view with a dynamic list of game objects for mixed collections."""
        if not hasattr(self, "pgn_tree") or not hasattr(self, "preview_lookup"):
            return

        self.pgn_tree.delete(*self.pgn_tree.get_children())
        self.preview_lookup.clear()

        if games_list:
            if hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
                self.lbl_empty_state.pack_forget()

            for idx, game in enumerate(games_list, start=1):
                headers = game.headers
                white = headers.get("White", "Unknown")
                black = headers.get("Black", "Unknown")
                result = headers.get("Result", "*")

                item_id = self.pgn_tree.insert(
                    "",
                    "end",
                    values=(idx, white, black, result)
                )
                self.preview_lookup[item_id] = game

                # Auto-select the target game if it matches
                if target_game and (
                    game.headers.get("White") == target_game.headers.get("White")
                    and game.headers.get("Black") == target_game.headers.get("Black")
                    and game.headers.get("Date") == target_game.headers.get("Date")
                ):
                    self.pgn_tree.selection_set(item_id)
                    self.pgn_tree.see(item_id)
        else:
            if hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
                self.lbl_empty_state.pack(padx=10, pady=15, anchor="center")

    def toggle_game(self, event):
        """Handles clicking a game inside the sidebar tree view."""
        item_id = self.pgn_tree.identify_row(event.y)
        if not item_id or item_id not in self.preview_lookup:
            return

        game = self.preview_lookup[item_id]

        # Grab the full list of games currently loaded in the tree view to keep as the active source
        current_games_list = list(self.preview_lookup.values())

        if hasattr(self, "load_game_from_state"):
            self.load_game_from_state(game, category_source=current_games_list)