# File module titled "mixed_analysis.py"

from pathlib import Path
import chess.pgn
from tkinter import ttk
from gui.statusbar import set_status_message
from gui.layout_analysis import LayoutAnalysisMixin

MIXED_ANALYSIS_FILE = Path(__file__).resolve().parent.parent / "pgn" / "mixed_analysis.pgn"


class MixedAnalysisMixin(LayoutAnalysisMixin):
    def __init__(self, parent, filename=None):
        super().__init__(parent)
        self.filename = filename
        self.preview_lookup = {}
        self._apply_tree_styles()
        self._bind_mixed_events()

    def _apply_tree_styles(self):
        """Applies dark-theme styling to the treeview."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Analysis.Treeview",
            background="#172134",
            foreground="#f8fafc",
            fieldbackground="#172134",
            rowheight=24,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Analysis.Treeview",
            background=[("selected", "#2e4a8c")],
            foreground=[("selected", "#ffffff")]
        )

        if hasattr(self, "pgn_tree") and self.pgn_tree:
            self.pgn_tree.configure(style="Analysis.Treeview")

    def _bind_mixed_events(self):
        """Binds selection events so clicking a game updates the analysis board."""
        if hasattr(self, "pgn_tree") and self.pgn_tree:
            self.pgn_tree.bind("<<TreeviewSelect>>", self._on_game_selected)

    def _on_game_selected(self, event):
        """Handles selecting a game from the tree and updating the board."""
        if not hasattr(self, "pgn_tree") or not self.pgn_tree:
            return

        selected_items = self.pgn_tree.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        if item_id in self.preview_lookup:
            game = self.preview_lookup[item_id]
            if hasattr(self, "load_game_on_board"):
                self.load_game_on_board(game)

    def load_mixed_collection(self, games_list, target_game):
        """Writes a list of mixed collection games to disk, populates the tree view, and forces a UI refresh."""
        MIXED_ANALYSIS_FILE.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(MIXED_ANALYSIS_FILE, "w", encoding="utf-8") as f:
                for g in games_list:
                    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                    f.write(g.accept(exporter) + "\n\n")
        except Exception as e:
            set_status_message(f"Error saving mixed collection: {e}")
            return

        self.load_games(filename=MIXED_ANALYSIS_FILE)

        # Change category_file to category_source here:
        self.load_game_from_state(target_game, category_source=MIXED_ANALYSIS_FILE)

        # Force the UI geometry manager to redraw the workspace containers
        self.update_idletasks()
        if hasattr(self, "pgn_tree") and self.pgn_tree:
            self.pgn_tree.update()

    def load_games(self, filename=None):
        """Loads games from the mixed analysis file into the tree view."""
        if filename:
            self.filename = filename

        if hasattr(self, "pgn_tree") and self.pgn_tree:
            try:
                self.pgn_tree.configure(style="Analysis.Treeview")
            except Exception:
                pass
            self.pgn_tree.delete(*self.pgn_tree.get_children())

        self.preview_lookup.clear()
        game_list = []
        if self.filename and Path(self.filename).exists():
            try:
                with open(self.filename, "r", encoding="utf-8") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        game_list.append(game)
            except Exception as e:
                set_status_message(f"Error loading mixed PGN file: {e}")

        if hasattr(self, "pgn_tree") and self.pgn_tree:
            for idx, game in enumerate(game_list, start=1):
                headers = game.headers
                white = headers.get("White", "Unknown")
                black = headers.get("Black", "Unknown")
                result = headers.get("Result", "*")

                item_id = self.pgn_tree.insert("", "end", values=(idx, white, black, result))
                self.preview_lookup[item_id] = game

        if not game_list and hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
            self.lbl_empty_state.configure(text="No mixed games loaded in memory.")
            self.lbl_empty_state.pack(padx=20, pady=20)
        elif hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
            self.lbl_empty_state.pack_forget()

    def load_game_from_state(self, target_game, category_file=None):
        """Loads games into the catalog tree, matches target_game, or defaults to the first game."""
        if category_file:
            self.load_games(filename=category_file)

        if not hasattr(self, "pgn_tree") or not self.pgn_tree or not self.preview_lookup:
            return

        matched_item = None
        if target_game:
            target_white = target_game.headers.get("White", "").strip()
            target_black = target_game.headers.get("Black", "").strip()

            for item_id, game in self.preview_lookup.items():
                if (
                        game.headers.get("White", "").strip() == target_white
                        and game.headers.get("Black", "").strip() == target_black
                ):
                    matched_item = item_id
                    break

        # Fallback: if no exact match was found, pick the very first game so the view isn't blank
        if not matched_item and self.preview_lookup:
            matched_item = list(self.preview_lookup.keys())[0]

        if matched_item:
            self.pgn_tree.selection_set(matched_item)
            self.pgn_tree.see(matched_item)
            game = self.preview_lookup[matched_item]
            if hasattr(self, "load_game_on_board"):
                self.load_game_on_board(game)
            else:
                LayoutAnalysisMixin.load_game_from_state(self, game)