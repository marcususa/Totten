import chess
import chess.pgn
from pathlib import Path
import customtkinter as ctk
from gui.layout_analysis import LayoutAnalysisMixin
import gui.app_state as state


class CatalogAnalysis(ctk.CTkFrame, LayoutAnalysisMixin):
    """
    Dedicated workspace controller for Catalog Analysis.
    Integrates layout mixins, engine selection/analysis, and catalog PGN data routing.
    """

    def __init__(self, parent, filename=None, *args, **kwargs):
        super().__init__(parent, fg_color="#172134", corner_radius=0, *args, **kwargs)
        self.filename = filename or "personal_catalog.pgn"
        self.game_list = []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}

        # Initialize the full UI shell layout (including board buttons and panels)
        self.init_layout()

        # Initial load of catalog data
        self.load_catalog_data()

    def load_catalog_data(self):
        """Loads all games from the target catalog PGN file into memory."""
        source_games = []
        catalog_path = self.filename

        if Path(catalog_path).exists():
            try:
                with open(catalog_path, "r", encoding="utf-8", errors="replace") as f:
                    while True:
                        g = chess.pgn.read_game(f)
                        if g is None:
                            break
                        source_games.append(g)
                self.game_list = source_games
                if hasattr(self, "app_state"):
                    setattr(self.app_state, "all_games", source_games)
            except Exception as e:
                print(f"[CATALOG ANALYSIS DEBUG] Error reading catalog file: {e}")

        # Populate initial tree state if games were found
        if self.game_list and hasattr(self, "pgn_tree"):
            self.populate_catalog_tree(self.game_list)

    def populate_catalog_tree(self, games_to_display, active_game=None):
        """Populates the tree view with the provided list of catalog games."""
        if not hasattr(self, "pgn_tree") or not hasattr(self, "preview_lookup"):
            return

        self.pgn_tree.delete(*self.pgn_tree.get_children())
        self.preview_lookup.clear()

        if hasattr(self, "lbl_empty_state") and self.lbl_empty_state and games_to_display:
            try:
                self.lbl_empty_state.pack_forget()
            except Exception:
                pass

        target = active_game or (games_to_display[0] if games_to_display else None)

        for idx, g in enumerate(games_to_display, start=1):
            headers = g.headers
            white = headers.get("White", "Unknown")
            black = headers.get("Black", "Unknown")
            result = headers.get("Result", "*")

            item_id = self.pgn_tree.insert("", "end", values=(idx, white, black, result))
            self.preview_lookup[item_id] = g

            if target and g == target:
                self.pgn_tree.selection_set(item_id)
                self.pgn_tree.see(item_id)

        if target:
            self.load_game_from_state(target)

    def load_games_by_eco(self, eco_code, active_game=None):
        """Filters and displays catalog games by ECO code."""
        if not eco_code:
            return

        eco_clean = str(eco_code).strip().upper()

        if not self.game_list and hasattr(state, "all_games") and state.all_games:
            self.game_list = state.all_games
        elif not self.game_list:
            self.load_catalog_data()

        eco_games = [
            g for g in self.game_list
            if hasattr(g, "headers") and g.headers.get("ECO", "").strip().upper() == eco_clean
        ]

        target_game = active_game or (eco_games[0] if eco_games else None)

        if eco_games:
            if hasattr(state, "active_category_source"):
                state.active_category_source = eco_games

        self.populate_catalog_tree(eco_games, active_game=target_game)

    def load_game_hardwired(self, game_node, category_source=None):
        """Hardwired highway entry point for Catalog Analysis view updates."""
        if isinstance(category_source, list):
            self.game_list = category_source
            self.populate_catalog_tree(self.game_list, active_game=game_node)
        else:
            self.load_game_from_state(game_node)

    def on_hardwired_tree_select(self, game):
        """Catalog-specific tree row selection action."""
        self.load_game_from_state(game)

    def load_game_from_state(self, game_obj, category_source=None):
        """Loads a game object into the analysis board and notation view."""
        if not game_obj:
            return
        self.current_game = game_obj
        self.board_node = game_obj

        if hasattr(self, "chess_board") and self.chess_board:
            self.chess_board.set_board(game_obj.board())

        headers = game_obj.headers
        white = headers.get("White", "Unknown")
        black = headers.get("Black", "Unknown")
        result = headers.get("Result", "*")

        if hasattr(self, "lbl_header") and self.lbl_header:
            self.lbl_header.configure(text=f"{white} vs {black} ({result})")

        if hasattr(self, "txt_moves") and self.txt_moves:
            self.txt_moves.configure(state="normal")
            self.txt_moves.delete("1.0", "end")
            self.txt_moves.insert("1.0", str(game_obj.mainline()))
            self.txt_moves.configure(state="disabled")

    def on_prev_move(self):
        if hasattr(self, "board_node") and self.board_node and self.board_node.parent:
            self.board_node = self.board_node.parent
            if hasattr(self, "chess_board") and self.chess_board:
                self.chess_board.set_board(self.board_node.board())

    def on_next_move(self):
        if hasattr(self, "board_node") and self.board_node and self.board_node.variations:
            self.board_node = self.board_node.variation(0)
            if hasattr(self, "chess_board") and self.chess_board:
                self.chess_board.set_board(self.board_node.board())

    def on_first_move(self):
        if hasattr(self, "current_game") and self.current_game:
            self.board_node = self.current_game
            if hasattr(self, "chess_board") and self.chess_board:
                self.chess_board.set_board(self.current_game.board())

    def on_last_move(self):
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game
            while node.variations:
                node = node.variation(0)
            self.board_node = node
            if hasattr(self, "chess_board") and self.chess_board:
                self.chess_board.set_board(node.board())


# Standalone factory and view helper functions for main.py integration
def create_workspace(master):
    """Instantiates CatalogAnalysis directly as the primary startup view."""
    instance = CatalogAnalysis(master, filename="personal_catalog.pgn")
    state.workspace = instance
    return instance


def show_workspace(name=None):
    """Handles independent navigation triggered by the sidebar."""
    if not hasattr(state, "workspace") or not state.workspace:
        return

    # If the user clicks catalog from the sidebar
    if name in ("search_catalog", "catalog", "catalog_analysis"):
        if hasattr(state.workspace, "tkraise"):
            state.workspace.tkraise()

    # If the user clicks mixed or patterns, handle their independent views here
    elif name in ("mixed", "mixed_analysis"):
        # TODO: Route to independent mixed module if active
        pass
    elif name in ("patterns", "patterns_analysis"):
        # TODO: Route to independent patterns module if active
        pass