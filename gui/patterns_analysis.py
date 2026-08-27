# File titled "patterns_analysis.py"

from pathlib import Path
import chess.pgn
from tkinter import ttk
from gui.statusbar import set_status_message

PATTERNS_ANALYSIS_FILE = Path(__file__).resolve().parent.parent / "pgn" / "patterns_analysis.pgn"


class PatternsAnalysisMixin:
    def __init__(self, parent=None, filename=None):
        self.filename = filename
        self.preview_lookup = {}
        self._apply_tree_styles()
        self._bind_pattern_events()

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

    def _bind_pattern_events(self):
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

    def load_patterns_collection(self, games_list, target_game=None):
        """Writes a list of pattern collection games to disk, populates the tree view, and forces a UI refresh."""
        PATTERNS_ANALYSIS_FILE.parent.mkdir(parents=True, exist_ok=True)

        extracted_games = []
        for item in games_list:
            if isinstance(item, dict):
                g_obj = item.get("game_object")
                if g_obj:
                    extracted_games.append(g_obj)
            elif isinstance(item, chess.pgn.Game):
                extracted_games.append(item)

        if not target_game and extracted_games:
            target_game = extracted_games[0]
        elif isinstance(target_game, dict):
            target_game = target_game.get("game_object", target_game)

        try:
            with open(PATTERNS_ANALYSIS_FILE, "w", encoding="utf-8") as f:
                exporter = chess.pgn.FileExporter(f)
                for g in extracted_games:
                    g.accept(exporter)
                    f.write("\n")
        except Exception as e:
            set_status_message(f"Error saving patterns collection: {e}")
            return

        self.filename = PATTERNS_ANALYSIS_FILE
        self.load_games(filename=PATTERNS_ANALYSIS_FILE)

        self.load_game_from_state(target_game, category_source=PATTERNS_ANALYSIS_FILE)

        self.update_idletasks()
        if hasattr(self, "pgn_tree") and self.pgn_tree:
            self.pgn_tree.update()

    def load_games(self, filename=None):
        """Loads games from the patterns analysis file into the tree view by cycling through the file contents."""
        if filename:
            self.filename = filename

        active_load_file = self.filename if self.filename else PATTERNS_ANALYSIS_FILE
        print(f"[DEBUG load_games] Loading from file: {active_load_file}")

        if hasattr(self, "pgn_tree") and self.pgn_tree:
            try:
                self.pgn_tree.configure(style="Analysis.Treeview")
            except Exception:
                pass
            self.pgn_tree.delete(*self.pgn_tree.get_children())

        self.preview_lookup.clear()
        game_list = []

        if Path(active_load_file).exists():
            try:
                with open(active_load_file, "r", encoding="utf-8") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        game_list.append(game)
            except Exception as e:
                set_status_message(f"Error loading patterns PGN file: {e}")

        print(f" -> Successfully parsed {len(game_list)} games from disk.")

        if hasattr(self, "pgn_tree") and self.pgn_tree:
            for idx, game in enumerate(game_list, start=1):
                headers = game.headers
                white = headers.get("White", "Unknown")
                black = headers.get("Black", "Unknown")
                result = headers.get("Result", "*")

                item_id = self.pgn_tree.insert("", "end", values=(idx, white, black, result))
                self.preview_lookup[item_id] = game

        if not game_list and hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
            self.lbl_empty_state.configure(text="No pattern games loaded in memory.")
            self.lbl_empty_state.pack(padx=20, pady=20)
        elif hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
            self.lbl_empty_state.pack_forget()


    def load_game_from_state(self, target_game, category_file=None, category_source=None):
        """Matches target_game in the already loaded tree view without wiping it."""
        active_file = category_source if category_source else category_file
        if active_file and active_file != self.filename:
            self.load_games(filename=active_file)

        if not hasattr(self, "pgn_tree") or not self.pgn_tree or not self.preview_lookup:
            return

        matched_item = None

        if target_game:
            target_white = target_game.headers.get("White", "").strip()
            target_black = target_game.headers.get("Black", "").strip()
            target_date = target_game.headers.get("Date", "").strip()

            for item_id, game in self.preview_lookup.items():
                if target_white and target_black:
                    if (
                            game.headers.get("White", "").strip() == target_white
                            and game.headers.get("Black", "").strip() == target_black
                    ):
                        matched_item = item_id
                        break
                else:
                    if game.headers.get("Date", "").strip() == target_date:
                        matched_item = item_id
                        break

        if not matched_item and self.preview_lookup:
            matched_item = list(self.preview_lookup.keys())[0]

        if matched_item:
            self.pgn_tree.selection_set(matched_item)
            self.pgn_tree.see(matched_item)
            game = self.preview_lookup[matched_item]
            if hasattr(self, "load_game_on_board"):
                self.load_game_on_board(game)