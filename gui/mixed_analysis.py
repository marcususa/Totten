import json
from pathlib import Path
import customtkinter as ctk
import chess
import chess.pgn
import gui.app_state as state

from core.constants import CONFIG_FILE
from gui.catalog_init_mixin import CatalogInitMixin
from gui.engine_mixins.engine_review_mixin import EngineReviewMixin
from gui.engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from gui.engine_mixins.engine_standard_mixin import EngineStandardMixin


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(
            tw,
            text=self.text,
            fg_color="#1e293b",
            text_color="#f8fafc",
            corner_radius=4,
            font=("Arial", 11)
        )
        label.pack(padx=6, pady=4)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def get_saved_pgn_filename():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("current_pgn_filename")
        except Exception:
            pass
    return None


class MixedAnalysis(ctk.CTkFrame, CatalogInitMixin, EngineReviewMixin, EngineCandidateMixin, EngineStandardMixin):
    """
    Dedicated self-contained workspace controller for Mixed Analysis.
    Absorbs the complete layout grid, tree view navigation, board management, PGN state handling, and engine analysis modes.
    """

    def __init__(self, parent, filename=None, initial_games=None, *args, **kwargs):
        super().__init__(parent, fg_color="#172134", corner_radius=0, *args, **kwargs)
        self.filename = filename

        # Pull from isolated state immediately if initial_games is empty
        if not initial_games and hasattr(state, "mixed_state"):
            initial_games = state.mixed_state.get("active_games")

        self.game_list = list(initial_games) if initial_games else []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}

        # State tracking fields absorbed from layout mixin
        self.active_game = None
        self.root_game_node = None
        self.current_node = None
        self.active_engine_mode = "standard"
        self.analysis_rows = {}

        # Initialize the full UI shell layout
        self.init_layout()

        # Initial load of PGN folder data (will skip file load if initial_games were provided)
        self.load_catalog_data()

        # Wire up engine mode buttons securely
        self._bind_engine_buttons()

    def _find_and_cache_analysis_box(self):
        """Scans once during startup to list all available text widgets."""
        print("[DIAGNOSTIC] Listing all text widgets on MixedAnalysis:")
        found_boxes = {}
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                val = getattr(self, attr_name, None)
                if val is not None and hasattr(val, "insert") and hasattr(val, "delete"):
                    print(f" -> Found widget: '{attr_name}' ({type(val)})")
                    found_boxes[attr_name] = val

        if "analysis_textbox" in found_boxes:
            self._cached_analysis_box = found_boxes["analysis_textbox"]

        # Fallback search through all attributes for something with text-inserting capabilities
        print("[DIAGNOSTIC] Running one-time attribute scan for analysis widget:")
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                val = getattr(self, attr_name, None)
                if val is not None and hasattr(val, "insert") and hasattr(val, "delete"):
                    print(f" -> Found matching widget attribute: '{attr_name}' ({type(val)})")
                    self._cached_analysis_box = val
                    return

        print("[DIAGNOSTIC WARNING] No text-inserting widget found on MixedAnalysis!")

    def _bind_engine_buttons(self):
        """Binds UI buttons to engine mode triggers with debug checks."""
        bound_count = 0
        for btn_name in ("btn_review", "btn_review_mode"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(command=lambda: self.trigger_engine_mode("review"))
                print(f"[DEBUG] Successfully bound {btn_name} to review mode.")
                bound_count += 1

        for btn_name in ("btn_candidates", "btn_candidate_moves"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(command=lambda: self.trigger_engine_mode("candidates"))
                print(f"[DEBUG] Successfully bound {btn_name} to candidates mode.")
                bound_count += 1

        for btn_name in ("btn_standard", "btn_standard_mode"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(command=lambda: self.trigger_engine_mode("standard"))
                print(f"[DEBUG] Successfully bound {btn_name} to standard mode.")
                bound_count += 1

        if bound_count == 0:
            print("[DEBUG WARNING] No engine buttons were found during binding! Check their attribute names.")

    def update_engine_display(self, text):
        """Handles standard mode streaming text output."""
        target_box = self.analysis_textbox
        if target_box:
            try:
                target_box.configure(state="normal")
                target_box.delete("1.0", "end")
                target_box.insert("end", text)
                target_box.configure(state="disabled")
            except Exception as e:
                print(f"[ENGINE DISPLAY ERROR] {e}")

    def write_analysis(self, text):
        self.update_engine_display(text)

    def write(self, text):
        self.update_engine_display(text)

    def append(self, text):
        self.update_engine_display(text)

    def _update_active_boards(self, board_obj):
        """Updates the board widget position when navigating review steps."""
        if hasattr(self, "board_widget") and self.board_widget and board_obj:
            try:
                self.board_widget.set_position_fen(board_obj.fen())
            except Exception:
                pass
    # ---------------------------------------------

    def load_games_list(self, games_list, focused_game=None):
        """Populates the analysis view with a filtered subset of games and loads the board."""
        if not games_list:
            return

        self.game_list = games_list
        if hasattr(self, "populate_catalog_tree"):
            self.populate_catalog_tree(self.game_list)

        target_game = focused_game if focused_game else games_list[0]
        if hasattr(self, "load_game"):
            self.load_game(target_game)

    def pop_out_board(self, *args, **kwargs):
        if hasattr(self, "board_widget") and self.board_widget and hasattr(self.board_widget, "toggle_popout"):
            self.board_widget.toggle_popout()

    def load_game(self, game_node, category_source=None):
        if hasattr(self, "load_game_hardwired"):
            return self.load_game_hardwired(game_node, category_source=category_source)
        return self.load_game_from_state(game_node, category_source=category_source)

    def load_catalog_data(self):
        if self.game_list:
            if hasattr(self, "pgn_tree"):
                self.populate_catalog_tree(self.game_list)
            return

        source_games = []
        if self.filename and Path(self.filename).exists():
            target_path = self.filename
        else:
            base_dir = Path(__file__).resolve().parent.parent / "pgn"
            target_path = base_dir / "open_events.pgn"
            if not target_path.exists():
                pgn_files = list(base_dir.rglob("*.pgn"))
                if pgn_files:
                    target_path = pgn_files[0]

        if Path(target_path).exists():
            try:
                with open(target_path, "r", encoding="utf-8", errors="replace") as f:
                    while True:
                        g = chess.pgn.read_game(f)
                        if g is None:
                            break
                        source_games.append(g)
                self.game_list = source_games
                if hasattr(state, "all_games"):
                    state.all_games = source_games
            except Exception as e:
                print(f"[MIXED ANALYSIS DEBUG] Error reading PGN file: {e}")

        if self.game_list and hasattr(self, "pgn_tree"):
            self.populate_catalog_tree(self.game_list)

    def populate_catalog_tree(self, games_to_display, active_game=None):
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
        if isinstance(category_source, list):
            self.game_list = category_source
            self.populate_catalog_tree(self.game_list, active_game=game_node)
        else:
            self.load_game_from_state(game_node)

    def on_hardwired_tree_select(self, game):
        self.load_game_from_state(game)

    def load_game_from_state(self, game_obj, category_source=None):
        """Loads a game object into the analysis board, notation view, and header metadata with red tracker highlighting intact."""
        if not game_obj:
            return

        self.current_game = game_obj
        self.board_node = game_obj
        self.active_game = game_obj
        self.root_game_node = game_obj
        self.current_node = game_obj

        # 1. Update main chessboard
        if hasattr(self, "board_widget") and self.board_widget:
            try:
                fen_str = game_obj.board().fen()
                self.board_widget.set_position_fen(fen_str)
            except Exception:
                pass

        headers = game_obj.headers
        white = headers.get("White", "Unknown")
        black = headers.get("Black", "Unknown")
        result = headers.get("Result", "*")

        # 2. Update full PGN text details
        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
                pgn_text_export = game_obj.accept(exporter)

                self.pgn_data_text.configure(state="normal")
                self.pgn_data_text.delete("1.0", "end")
                self.pgn_data_text.insert("end", pgn_text_export)
                self.pgn_data_text.configure(state="disabled")
            except Exception:
                pass

        # 3. Update main moves view textbox notation with clean movement tracking and interactive red tracker tags
        if hasattr(self, "moves_textbox") and self.moves_textbox:
            try:
                self.moves_textbox.configure(state="normal")
                self.moves_textbox.delete("1.0", "end")

                temp_node = game_obj
                move_num = 1
                while temp_node.variations:
                    next_node = temp_node.variation(0)
                    san_move = temp_node.board().san(next_node.move)

                    if temp_node.board().turn == chess.WHITE:
                        move_str = f"{move_num}. {san_move} "
                    else:
                        move_str = f"{san_move} "
                        move_num += 1

                    tag_name = id(next_node)
                    self.moves_textbox.insert("end", move_str, ("default", str(tag_name)))
                    self.moves_textbox.tag_bind(str(tag_name), "<Button-1>",
                                                lambda e, n=next_node: self.jump_to_node(n))

                    temp_node = next_node

                self.moves_textbox.configure(state="disabled")
                self.update_active_move_highlight()
            except Exception:
                pass

        if hasattr(self, "_load_plain_game_moves"):
            try:
                self._load_plain_game_moves(game_obj)
            except Exception:
                pass

    def jump_to_node(self, target_node):
        """Jumps directly to a specific game node when clicked in the move list."""
        self.board_node = target_node
        if hasattr(self, "board_widget") and self.board_widget:
            self.board_widget.set_position_fen(self.board_node.board().fen())
        self.update_active_move_highlight()

    def update_active_move_highlight(self):
        """Updates the active background highlight ('red tracker') in the moves textbox corresponding to self.board_node."""
        if not hasattr(self, "moves_textbox") or not self.moves_textbox:
            return

        try:
            self.moves_textbox.configure(state="normal")
            self.moves_textbox.tag_remove("active_move", "1.0", "end")

            if self.board_node and self.board_node != self.current_game:
                current_tag = str(id(self.board_node))
                ranges = self.moves_textbox.tag_ranges(current_tag)
                if ranges:
                    self.moves_textbox.tag_add("active_move", ranges[0], ranges[1])
                    self.moves_textbox.see(ranges[0])

            self.moves_textbox.configure(state="disabled")
        except Exception:
            pass

    def on_prev_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.parent:
            self.board_node = self.board_node.parent
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            self.update_active_move_highlight()

    def on_next_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.variations:
            self.board_node = self.board_node.variation(0)
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            self.update_active_move_highlight()

    def on_first_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            self.board_node = self.current_game
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.current_game.board().fen())
            self.update_active_move_highlight()

    def on_last_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game
            while node.variations:
                node = node.variation(0)
            self.board_node = node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(node.board().fen())
            self.update_active_move_highlight()

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self.board_widget, "flip_board"):
                self.board_widget.flip_board()
            elif hasattr(self.board_widget, "toggle_flip"):
                self.board_widget.toggle_flip()

    def trigger_engine_mode(self, mode):
        """Routes engine mode changes directly to the appropriate mixin handler."""
        self.active_engine_mode = mode

        # Style buttons securely across name variants
        for name in ("btn_review", "btn_review_mode"):
            if hasattr(self, name) and getattr(self, name):
                getattr(self, name).configure(fg_color="#2e4a8c" if mode == "review" else "#1e293b",
                                              hover_color="#4870cd" if mode == "review" else "#334155")
        for name in ("btn_candidates", "btn_candidate_moves"):
            if hasattr(self, name) and getattr(self, name):
                getattr(self, name).configure(fg_color="#2e4a8c" if mode == "candidates" else "#1e293b",
                                              hover_color="#4870cd" if mode == "candidates" else "#334155")
        for name in ("btn_standard", "btn_standard_mode"):
            if hasattr(self, name) and getattr(self, name):
                getattr(self, name).configure(fg_color="#2e4a8c" if mode == "standard" else "#1e293b",
                                              hover_color="#4870cd" if mode == "standard" else "#334155")

        # Delegate directly to the specific mixin's trigger implementation
        if mode == "review":
            EngineReviewMixin.trigger_engine_mode(self, "review")
        elif mode == "candidates":
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")

def create_workspace(master, initial_games=None, filename=None, **kwargs):
    """Instantiates MixedAnalysis, utilizing filtered games and files from the PGN folder structure."""
    import gui.app_state as state_mod

    if initial_games is None and hasattr(state_mod, "mixed_state"):
        initial_games = state_mod.mixed_state.get("active_games")

    if filename is None and hasattr(state_mod, "mixed_state"):
        filename = state_mod.mixed_state.get("current_filename")

    focus = None
    if hasattr(state_mod, "mixed_state"):
        focus = state_mod.mixed_state.get("active_focus")

    instance = MixedAnalysis(master, filename=filename, initial_games=initial_games)

    if focus and hasattr(instance, "load_game"):
        instance.load_game(focus)
    elif initial_games and hasattr(instance, "load_game"):
        instance.load_game(initial_games[0])

    if hasattr(state_mod, "mixed_state"):
        state_mod.mixed_state["active_games"] = None
        state_mod.mixed_state["active_focus"] = None
        state_mod.mixed_state["current_filename"] = None

    state_mod.workspace = instance
    return instance