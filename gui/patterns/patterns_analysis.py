# gui/patterns/patterns_analysis.py

import threading
import chess
import customtkinter as ctk
import gui.app_state as state

from core.constants import THEME
from core.chess_engine import ChessEngine
from gui.engine_mixins.engine_review_mixin import EngineReviewMixin
from gui.engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from gui.engine_mixins.engine_standard_mixin import EngineStandardMixin
from gui.catalog.catalog_init_mixin import CatalogInitMixin

from gui.patterns.patterns_analysis_navigation import PatternsAnalysisNavigationMixin
from gui.patterns.patterns_analysis_board import PatternsAnalysisBoardMixin


class PatternsAnalysis(
    ctk.CTkFrame,
    CatalogInitMixin,
    EngineReviewMixin,
    EngineCandidateMixin,
    EngineStandardMixin,
    PatternsAnalysisNavigationMixin,
    PatternsAnalysisBoardMixin,
):
    """
    Dedicated self-contained workspace controller for Patterns Analysis.
    Absorbs the complete layout grid, tree view navigation, board management, PGN state handling, and engine analysis modes.
    """

    def __init__(self, parent, filename=None, initial_games=None, target_game=None, active_index=None, *args, **kwargs):
        kwargs.pop('target_game', None)
        kwargs.pop('active_index', None)

        super().__init__(parent, fg_color=THEME["bg_panel"], corner_radius=0, *args, **kwargs)

        self.filename = filename or "personal_catalog.pgn"

        if not initial_games and hasattr(state, "catalog_state"):
            initial_games = state.catalog_state.get("active_games")

        if not initial_games and hasattr(state, "all_games"):
            initial_games = state.all_games

        self.game_list = list(initial_games) if initial_games else []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}

        self.active_game = None
        self.root_game_node = None
        self.current_node = None
        self.active_engine_mode = None  # Start idle with no engine mode active
        self.analysis_rows = {}
        self._cached_analysis_box = None

        self.init_layout()
        self._find_and_cache_analysis_box()
        self.load_catalog_data()
        self._bind_engine_buttons()
        self._bind_global_shortcuts()

        if active_index is not None and 0 <= active_index < len(self.game_list):
            target_game = self.game_list[active_index]

        if target_game and hasattr(self, "load_game"):
            self.load_game(target_game)

        if hasattr(self, "board_widget") and self.board_widget:
            self.board_widget.on_step_back = self.on_prev_move
            self.board_widget.on_step_forward = self.on_next_move
            self.board_widget.on_jump_start = self.on_first_move
            self.board_widget.on_jump_end = self.on_last_move

        self.after(50, self.focus_force)

    def _resolve_game_obj(self, item):
        if item is None:
            return None
        if hasattr(item, "board") and hasattr(item, "headers"):
            return item
        if isinstance(item, dict):
            for k in ("game_object", "game", "game_obj", "node", "pgn", "item", "target_game"):
                if k in item and item[k] is not None:
                    res = self._resolve_game_obj(item[k])
                    if res is not None:
                        return res
        return item

    def _find_and_cache_analysis_box(self):
        found_boxes = {}
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                val = getattr(self, attr_name, None)
                if val is not None and hasattr(val, "insert") and hasattr(val, "delete"):
                    found_boxes[attr_name] = val

        if "analysis_textbox" in found_boxes:
            self._cached_analysis_box = found_boxes["analysis_textbox"]
            return

        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                val = getattr(self, attr_name, None)
                if val is not None and hasattr(val, "insert") and hasattr(val, "delete"):
                    self._cached_analysis_box = val
                    return

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

        for btn_name in ("btn_standard", "btn_standard_mode"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    command=lambda: self.trigger_engine_mode("standard"),
                    hover_color=THEME["btn_hover"]
                )

        # Properly bind the raw engine action buttons here:
        for btn_name in ("btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    command=self.toggle_engine_action,
                    hover_color=THEME["btn_hover"]
                )

    def toggle_engine_action(self):
        """Controls the independent Engine button for raw live evaluation on the left."""
        is_running = getattr(self, "_engine_running", False)
        if is_running:
            self.stop_raw_engine_analysis()
        else:
            self.start_raw_engine_analysis()

    def start_raw_engine_analysis(self):
        """Runs a lightweight background worker for raw engine lines targeting only pv_textbox."""
        if not hasattr(self, "current_node") or not self.current_node:
            print("[RAW ENGINE] Error: No current_node found.")
            self.update_engine_display("[No active position to evaluate.]\n")
            return

        try:
            board_obj = self.current_node.board()
        except Exception as e:
            print(f"[RAW ENGINE] Error getting board from node: {e}")
            return

        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True

        # Mark as running and update button appearance immediately
        self._engine_running = True
        for btn_name in ("btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_hover"], text="Stop")
                except Exception:
                    pass

        class RawEngineWorker(threading.Thread):
            def __init__(self, board_state, outer):
                super().__init__()
                self.board_state = board_state
                self.outer = outer
                self.cancel = False
                self.daemon = True

            def run(self):
                print("[RAW ENGINE WORKER] Starting thread analysis...")
                try:
                    engine = ChessEngine()

                    def callback(res):
                        if self.cancel:
                            return
                        print(f"[RAW ENGINE WORKER] Received result callback: {res}")
                        current_depth = res.get('depth', 25)
                        raw_eval = res.get('eval', 0.0)

                        if isinstance(raw_eval, str) and "M" in raw_eval:
                            eval_str = raw_eval
                        else:
                            eval_str = f"{float(raw_eval):+.2f}"

                        pv_lines = res.get('pv_lines', [])
                        if isinstance(pv_lines, list) and pv_lines:
                            formatted_lines = []
                            for idx, line in enumerate(pv_lines, start=1):
                                temp_board = self.board_state.copy()
                                move_tokens = line.strip().split()
                                numbered_pv = []

                                for move_str in move_tokens:
                                    try:
                                        move = temp_board.parse_san(move_str)
                                        if temp_board.turn == chess.WHITE:
                                            numbered_pv.append(f"{temp_board.fullmove_number}. {move_str}")
                                        else:
                                            if len(numbered_pv) == 0:
                                                numbered_pv.append(f"{temp_board.fullmove_number}... {move_str}")
                                            else:
                                                numbered_pv.append(move_str)
                                        temp_board.push(move)
                                    except Exception:
                                        numbered_pv.append(move_str)

                                moves_str = " ".join(numbered_pv)
                                formatted_lines.append(f"{idx}. {current_depth} | Eval: {eval_str} {moves_str}")

                            display_text = "\n\n".join(formatted_lines) + "\n"
                        else:
                            display_text = f"1. {current_depth} | Eval: {eval_str} | PV: (none)\n"

                        self.outer.after(0, lambda: self.outer.update_engine_display(display_text))

                    engine.analyze_position(
                        self.board_state,
                        depths=(10, 15, 20, 25),
                        multipv=3,
                        callback=callback,
                        worker_ref=self
                    )
                except Exception as e:
                    print(f"[RAW ENGINE WORKER CRASH] {e}")

        self._current_raw_engine_worker = RawEngineWorker(board_obj, self)
        self._current_raw_engine_worker.start()

    def stop_raw_engine_analysis(self):
        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True
            self._current_raw_engine_worker = None

        self._engine_running = False
        for btn_name in ("btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_initial"], text="Engine")
                except Exception:
                    pass


    def update_engine_display(self, text):
        """Strictly controls the left-column pv_textbox for raw engine outputs without touching the right analysis column."""
        target_box = getattr(self, "pv_textbox", None)
        if target_box:
            try:
                target_box.configure(fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
                inner_box.configure(state="normal")
                inner_box.delete("1.0", "end")
                inner_box.insert("end", text)
                inner_box.configure(state="disabled")
            except Exception as e:
                print(f"[ENGINE DISPLAY ERROR] {e}")

    def write_analysis(self, text):
        self.update_engine_display(text)

    def write(self, text):
        self.update_engine_display(text)

    def append(self, text):
        self.update_engine_display(text)

    def start_game_review(self, target_game):
        self._run_analysis_worker(target_game, mode="review")

    def _run_analysis_worker(self, target_game, mode="review"):
        self.analysis_rows = {}

        if hasattr(self, '_current_analysis_worker') and self._current_analysis_worker:
            self._current_analysis_worker.cancel = True

        class WorkerThread(threading.Thread):
            def __init__(self, game_obj, outer, analysis_mode):
                super().__init__()
                self.game_obj = game_obj
                self.outer = outer
                self.analysis_mode = analysis_mode
                self.cancel = False
                self.daemon = True
                self.white_streak = 0
                self.black_streak = 0
                self.last_eval = 0.0

            def run(self):
                def stream_callback(res):
                    if self.cancel:
                        return

                    try:
                        move_num = res['move_num']
                        is_white = res['is_white']
                        curr_eval = res.get('eval_after', 0.0)
                        played_san = res['played_san']

                        steps = move_num * 2 - 1 if is_white else move_num * 2
                        curr_n = self.game_obj
                        for _ in range(steps):
                            if curr_n.variations:
                                curr_n = curr_n.variation(0)

                        if move_num < 8:
                            move_display = played_san
                            tag_to_apply = "default"
                            self.last_eval = curr_eval
                        else:
                            if is_white:
                                loss = self.last_eval - curr_eval
                            else:
                                loss = curr_eval - self.last_eval

                            self.last_eval = curr_eval

                            tag_to_apply = "default"
                            eval_str = ""
                            comment_str = ""

                            if loss >= 2.6:
                                tag_to_apply = "red"
                                eval_str = f" {{{curr_eval:+.2f}}}"
                                comment_str = " ??"
                                self.white_streak = 0
                                self.black_streak = 0
                            elif 1.0 <= loss <= 2.5:
                                tag_to_apply = "orange"
                                eval_str = f" {{{curr_eval:+.2f}}}"
                                comment_str = " ?"
                                self.white_streak = 0
                                self.black_streak = 0
                            elif 0.3 <= loss < 1.0:
                                comment_str = " ?!"
                                if is_white:
                                    if self.black_streak > 0:
                                        self.black_streak -= 1
                                    else:
                                        self.white_streak += 1
                                    tag_to_apply = "green" if self.white_streak >= 3 else "light_blue"
                                else:
                                    if self.white_streak > 0:
                                        self.white_streak -= 1
                                    else:
                                        self.black_streak += 1
                                    tag_to_apply = "green" if self.black_streak >= 3 else "light_blue"

                            move_display = f"{played_san}{eval_str}{comment_str}"

                        if move_num not in self.outer.analysis_rows:
                            self.outer.analysis_rows[move_num] = {
                                "white": "", "black": "",
                                "white_tag": "default", "black_tag": "default",
                                "white_node": None, "black_node": None
                            }

                        if is_white:
                            self.outer.analysis_rows[move_num]["white"] = move_display
                            self.outer.analysis_rows[move_num]["white_tag"] = tag_to_apply
                            self.outer.analysis_rows[move_num]["white_node"] = curr_n
                        else:
                            self.outer.analysis_rows[move_num]["black"] = move_display
                            self.outer.analysis_rows[move_num]["black_tag"] = tag_to_apply
                            self.outer.analysis_rows[move_num]["black_node"] = curr_n

                        self.outer.after(0, self.outer._sync_analysis_selection)

                    except Exception as ex:
                        print(f"[STREAM CALLBACK ERROR] {ex}")

                try:
                    print(f"[ENGINE WORKER] Starting analysis for mode: {self.analysis_mode}")
                    engine_worker = ChessEngine()
                    engine_worker.analyze_game(self.game_obj, mode=self.analysis_mode, callback=stream_callback)
                except Exception as e:
                    print(f"[ENGINE WORKER CRASH] Mode {self.analysis_mode} failed: {e}")

        self._current_analysis_worker = WorkerThread(target_game, self, mode)
        self._current_analysis_worker.start()

    def _sync_analysis_selection(self):
        """Renders the analysis panel completely like a continuous book horizontally."""
        target_box = getattr(self, "analysis_textbox", None)
        if not target_box and hasattr(self, "_cached_analysis_box"):
            target_box = self._cached_analysis_box

        if not target_box:
            return

        try:
            target_box.configure(state="normal", fg_color=THEME["bg_surface"])
            inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
            inner_box.delete("1.0", "end")

            eval_tag_colors = {
                "red": THEME["eval_red"],
                "orange": THEME["eval_orange"],
                "green": THEME["eval_green"],
                "light_blue": THEME["eval_light_blue"],
                "default": THEME["eval_default"]
            }

            for tag_name, color in eval_tag_colors.items():
                inner_box.tag_config(tag_name, foreground=color)

            inner_box.tag_config("active_tracker", background=THEME["active_tracker_bg"], foreground=THEME["active_tracker_fg"])

            sorted_moves = sorted(self.analysis_rows.keys())
            for move_num in sorted_moves:
                row = self.analysis_rows[move_num]
                inner_box.insert("end", f"{move_num}. ")

                w_text = row.get("white", "")
                w_tag = row.get("white_tag", "default")
                w_node = row.get("white_node")

                if w_text:
                    w_tag_name = f"w_{move_num}_{id(w_node)}" if w_node else f"w_{move_num}"
                    is_active_white = (
                            (hasattr(self, "current_node") and self.current_node == w_node) or
                            (hasattr(self, "board_node") and self.board_node == w_node)
                    )
                    applied_tag = "active_tracker" if is_active_white else (
                        w_tag if w_tag in eval_tag_colors else "default")

                    inner_box.insert("end", f"{w_text} ", (applied_tag, w_tag_name))
                    if w_node:
                        inner_box.tag_bind(w_tag_name, "<Button-1>", lambda e, n=w_node: self.jump_to_node(n))
                else:
                    inner_box.insert("end", "... ")

                b_text = row.get("black", "")
                b_tag = row.get("black_tag", "default")
                b_node = row.get("black_node")

                if b_text:
                    b_tag_name = f"b_{move_num}_{id(b_node)}" if b_node else f"b_{move_num}"
                    is_active_black = (
                            (hasattr(self, "current_node") and self.current_node == b_node) or
                            (hasattr(self, "board_node") and self.board_node == b_node)
                    )
                    applied_tag = "active_tracker" if is_active_black else (
                        b_tag if b_tag in eval_tag_colors else "default")

                    inner_box.insert("end", f"{b_text} ", (applied_tag, b_tag_name))
                    if b_node:
                        inner_box.tag_bind(b_tag_name, "<Button-1>", lambda e, n=b_node: self.jump_to_node(n))

                inner_box.insert("end", "    ")

            inner_box.configure(state="disabled")
        except Exception as e:
            print(f"[SYNC ANALYSIS ERROR] {e}")

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
            self.board_widget.toggle_popout()

    def load_game(self, game_node, category_source=None):
        resolved = self._resolve_game_obj(game_node)
        if hasattr(self, "load_game_hardwired"):
            return self.load_game_hardwired(resolved, category_source=category_source)
        return self.load_game_from_state(resolved, category_source=category_source)

    def trigger_engine_mode(self, mode):
        """Routes engine mode changes, updates button/frame highlights, and delegates to mixin handlers."""
        self.active_engine_mode = mode
        self._selected_mode_button = mode

        mode_buttons = {
            "review": ("btn_review", "btn_review_mode"),
            "candidates": ("btn_candidates", "btn_candidate_moves"),
            "standard": ("btn_standard", "btn_standard_mode", "btn_engines")
        }

        def _apply_styles():
            for m, btn_names in mode_buttons.items():
                is_active = (mode == m)
                for name in btn_names:
                    btn = getattr(self, name, None)
                    if btn is not None:
                        try:
                            btn.configure(
                                fg_color=THEME["btn_hover"] if is_active else THEME["btn_initial"],
                                hover_color=THEME["btn_hover"],
                                text_color=THEME["text_primary"],
                            )
                        except Exception:
                            pass

        # Apply styles immediately and re-apply after the idle queue settles
        # to outlast CTk's internal button-release reset and mixin callbacks
        _apply_styles()
        self.after_idle(_apply_styles)

        # Update frame border highlights if present
        if hasattr(self, "frame_review") and self.frame_review:
            try:
                self.frame_review.configure(border_width=0 if mode == "review" else 1)
            except Exception:
                pass
        if hasattr(self, "frame_candidates") and self.frame_candidates:
            try:
                self.frame_candidates.configure(border_width=0 if mode == "candidates" else 1)
            except Exception:
                pass
        if hasattr(self, "frame_standard") and self.frame_standard:
            try:
                self.frame_standard.configure(border_width=0 if mode == "standard" else 1)
            except Exception:
                pass

        # Delegate directly to the respective mixin handler
        if mode == "review":
            EngineReviewMixin.trigger_engine_mode(self, "review")
        elif mode == "candidates":
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")


def create_workspace(master, initial_games=None, **kwargs):
    import gui.app_state as state_mod

    if initial_games is None:
        initial_games = (
                getattr(state_mod, "catalog_state", {}).get("active_games") or
                getattr(state_mod, "active_group_games", None) or
                getattr(state_mod, "active_search_results", None) or
                getattr(state_mod, "active_category_source", None) or
                getattr(state_mod, "all_games", None)
        )

    active_index = kwargs.get("active_index", getattr(state_mod, "catalog_state", {}).get("active_index", 0))

    defocus = (
            kwargs.get("target_game") or
            getattr(state_mod, "catalog_state", {}).get("active_focus") or
            getattr(state_mod, "active_focus_game", None)
    )

    if initial_games and 0 <= active_index < len(initial_games) and not defocus:
        defocus = initial_games[active_index]

    instance = PatternsAnalysis(master, filename="personal_catalog.pgn", initial_games=initial_games, target_game=defocus,
                                active_index=active_index)
    state_mod.workspace = instance
    return instance


def create_patterns_analysis_workspace(master, initial_games=None, **kwargs):
    return create_workspace(master, initial_games=initial_games, **kwargs)