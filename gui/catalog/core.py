import json
from pathlib import Path
import customtkinter as ctk
import chess
import chess.pgn
import gui.app_state as state

from core.analysis_panel import AnalysisPanelMixin
from core.constants import THEME
from .catalog_init_mixin import CatalogInitMixin
from .engine import CatalogEngineMixin
from .navigation import CatalogNavigationMixin


class CatalogAnalysis(ctk.CTkFrame, CatalogInitMixin, CatalogNavigationMixin, CatalogEngineMixin, AnalysisPanelMixin):
    """
    Dedicated self-contained workspace controller for Catalog Analysis.
    Absorbs the complete layout grid, tree view navigation, board management, PGN state handling, and engine analysis modes.
    """

    def __init__(self, parent, filename=None, initial_games=None, *args, **kwargs):
        super().__init__(parent, fg_color=THEME["bg_panel"], corner_radius=0, *args, **kwargs)

        self.filename = filename or "personal_catalog.pgn"

        if not initial_games and hasattr(state, "catalog_state"):
            initial_games = state.catalog_state.get("active_games")

        self.game_list = list(initial_games) if initial_games else []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}

        self.active_game = None
        self.root_game_node = None
        self.current_node = None
        self.active_engine_mode = state.catalog_state.get("active_engine_mode") if hasattr(state, "catalog_state") else None
        self.analysis_rows = {}
        self._current_analysis_worker = None

        self.init_layout()
        self._inject_stop_analysis_button()
        self.load_catalog_data()
        self._bind_engine_buttons()
        self._bind_global_shortcuts()

        if hasattr(self, "board_widget") and self.board_widget:
            try:
                self.board_widget.on_step_back = self.on_prev_move
                self.board_widget.on_step_forward = self.on_next_move
                self.board_widget.on_jump_start = self.on_first_move
                self.board_widget.on_jump_end = self.on_last_move
            except Exception as e:
                print(f"[BOARD WIDGET BIND ERROR] {e}")

        self.after(50, self.focus_force)

    def _inject_stop_analysis_button(self):
        """Adds a Stop Analysis button right next to the engine/review controls if it doesn't already exist."""
        try:
            if hasattr(self, "review_container") and self.review_container:
                if not hasattr(self, "btn_stop_analysis") or self.btn_stop_analysis is None:
                    self.btn_stop_analysis = ctk.CTkButton(
                        self.review_container,
                        text="Stop Analysis",
                        fg_color=THEME.get("btn_active", THEME["btn_hover"]),
                        hover_color=THEME["btn_hover"],
                        text_color=THEME["text_primary"],
                        border_width=1,
                        border_color=THEME.get("border_color", THEME["bg_surface"]),
                        command=self.stop_current_analysis
                    )
                    self.btn_stop_analysis.pack(side="top", pady=5, padx=5, fill="x")
        except Exception as e:
            print(f"[STOP BUTTON INJECTION ERROR] {e}")

    def stop_current_analysis(self):
        """Cancels any running Stockfish background analysis worker safely."""
        try:
            if hasattr(self, '_current_analysis_worker') and self._current_analysis_worker:
                self._current_analysis_worker.cancel = True
                self._current_analysis_worker = None
            print("[ENGINE WORKER] Analysis stopped by user.")
        except Exception as e:
            print(f"[STOP ANALYSIS ERROR] {e}")

    def _bind_global_shortcuts(self):
        try:
            top_level = self.winfo_toplevel()

            for key, callback in [
                ("<Left>", self.on_prev_move),
                ("<Right>", self.on_next_move),
                ("<Up>", self.on_first_move),
                ("<Down>", self.on_last_move),
                ("f", self.on_flip_board),
                ("F", self.on_flip_board)
            ]:
                top_level.bind(key, lambda e, cb=callback: self._safe_handle_shortcut(cb, e))
                self.bind(key, lambda e, cb=callback: self._safe_handle_shortcut(cb, e))

            if hasattr(self, "pgn_tree") and self.pgn_tree:
                self.pgn_tree.bind("<Left>", lambda e: self._safe_handle_shortcut(self.on_prev_move, e))
                self.pgn_tree.bind("<Right>", lambda e: self._safe_handle_shortcut(self.on_next_move, e))
                self.pgn_tree.bind("<Up>", lambda e: self._safe_handle_shortcut(self.on_first_move, e))
                self.pgn_tree.bind("<Down>", lambda e: self._safe_handle_shortcut(self.on_last_move, e))

            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.bind("<Left>", lambda e: self._safe_handle_shortcut(self.on_prev_move, e))
                self.board_widget.bind("<Right>", lambda e: self._safe_handle_shortcut(self.on_next_move, e))
        except Exception as e:
            print(f"[SHORTCUT BIND ERROR] {e}")

    def _safe_handle_shortcut(self, callback, event):
        try:
            focused = self.winfo_toplevel().focus_get()
            if focused and type(focused).__name__ in ("CTkTextbox", "CTkEntry", "Text", "Entry"):
                return

            if callable(callback):
                callback(event)
                return "break"
        except Exception as e:
            print(f"[SHORTCUT EXECUTION ERROR] {e}")

    def _bind_engine_buttons(self):
        try:
            for btn_name in ("btn_review", "btn_review_mode"):
                btn = getattr(self, btn_name, None)
                if btn is not None:
                    btn.configure(
                        command=lambda: self.trigger_engine_mode("review"),
                        hover_color=THEME["btn_hover"]
                    )

            for btn_name in ("btn_candidates", "btn_candidate_moves"):
                btn = getattr(self, btn_name, None)
                if btn is not None:
                    btn.configure(
                        command=lambda: self.trigger_engine_mode("candidates"),
                        hover_color=THEME["btn_hover"]
                    )

            for btn_name in ("btn_standard", "btn_standard_mode", "btn_engines"):
                btn = getattr(self, btn_name, None)
                if btn is not None:
                    btn.configure(
                        command=lambda: self.trigger_engine_mode("standard"),
                        hover_color=THEME["btn_hover"]
                    )

            if self.active_engine_mode:
                self.trigger_engine_mode(self.active_engine_mode)
        except Exception as e:
            print(f"[ENGINE BUTTON BIND ERROR] {e}")

    def write_analysis(self, text):
        self.update_engine_display(text)

    def write(self, text):
        self.update_engine_display(text)

    def append(self, text):
        self.update_engine_display(text)

    def _update_active_boards(self, board_obj):
        if hasattr(self, "board_widget") and self.board_widget and board_obj:
            try:
                self.board_widget.set_position_fen(board_obj.fen())
            except Exception as e:
                print(f"[UPDATE ACTIVE BOARDS ERROR] {e}")

    def load_games_list(self, games_list, focused_game=None):
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
            try:
                self.board_widget.toggle_popout()
            except Exception as e:
                print(f"[POPOUT ERROR] {e}")

    def load_catalog_data(self):
        if self.game_list:
            if hasattr(self, "pgn_tree"):
                active_game = None
                if hasattr(state, "catalog_state") and "active_index" in state.catalog_state:
                    idx = state.catalog_state.get("active_index", 0)
                    if 0 <= idx < len(self.game_list):
                        active_game = self.game_list[idx]

                self.populate_catalog_tree(self.game_list, active_game=active_game)
            return

        source_games = []
        target_file = Path(self.filename) if Path(self.filename).exists() else Path("personal_catalog.pgn")
        offset_file = Path("catalog_offset.txt")

        chunk_size = 100
        current_offset = 0

        if offset_file.exists():
            try:
                current_offset = int(offset_file.read_text().strip())
            except Exception:
                current_offset = 0

        if target_file.exists():
            try:
                with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                    skipped = 0
                    while skipped < current_offset:
                        g = chess.pgn.read_game(f)
                        if g is None:
                            current_offset = 0
                            f.seek(0)
                            break
                        skipped += 1

                    while len(source_games) < chunk_size:
                        g = chess.pgn.read_game(f)
                        if g is None:
                            break
                        source_games.append(g)

                if not source_games and current_offset > 0:
                    current_offset = 0
                    with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                        while len(source_games) < chunk_size:
                            g = chess.pgn.read_game(f)
                            if g is None:
                                break
                            source_games.append(g)

                next_offset = current_offset + len(source_games)
                if len(source_games) < chunk_size:
                    next_offset = 0

                offset_file.write_text(str(next_offset))
            except Exception as e:
                print(f"[CATALOG ANALYSIS DEBUG] Error reading catalog file: {e}")

        self.game_list = source_games
        if hasattr(state, "all_games"):
            state.all_games = source_games

        if self.game_list and hasattr(self, "pgn_tree"):
            self.populate_catalog_tree(self.game_list)

    def populate_catalog_tree(self, games_to_display, active_game=None):
        if not hasattr(self, "pgn_tree") or not hasattr(self, "preview_lookup"):
            return

        try:
            self.pgn_tree.delete(*self.pgn_tree.get_children())
            self.preview_lookup.clear()
        except Exception as e:
            print(f"[TREE CLEAR ERROR] {e}")

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

            try:
                item_id = self.pgn_tree.insert("", "end", values=(idx, white, black, result))
                self.preview_lookup[item_id] = g

                if target and g == target:
                    self.pgn_tree.selection_set(item_id)
                    self.pgn_tree.see(item_id)
            except Exception as e:
                print(f"[TREE INSERT ERROR] {e}")

        if target:
            self.load_game(target)
        self.after(50, self.focus_set)

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
            self.load_game(game_node)

    def on_hardwired_tree_select(self, game):
        self.load_game(game)