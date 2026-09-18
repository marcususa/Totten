# gui/patterns/patterns_analysis.py

import threading
import chess
import customtkinter as ctk
import gui.app_state as state

from core.constants import THEME
from core.chess_engine import ChessEngine
from gui.patterns.patterns_init_mixin import PatternsInitMixin
from gui.engine_mixins.engine_piece_mixin import EnginePieceMixin

from gui.patterns.patterns_analysis_navigation import PatternsAnalysisNavigationMixin
from gui.patterns.patterns_analysis_board import PatternsAnalysisBoardMixin


class PatternsAnalysis(
    ctk.CTkFrame,
    PatternsInitMixin,
    PatternsAnalysisNavigationMixin,
    PatternsAnalysisBoardMixin,
    EnginePieceMixin,
):


    """
    Dedicated self-contained workspace controller for Patterns Analysis.
    Absorbs the complete layout grid, tree view navigation, board management, PGN state handling, and pattern evaluation.
    """

    def __init__(self, parent, filename=None, initial_games=None, target_game=None, active_index=None,
                 target_piece=None, *args, **kwargs):
        kwargs.pop('target_game', None)
        kwargs.pop('active_index', None)
        kwargs.pop('target_piece', None)

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
        self.active_engine_mode = None
        self.analysis_rows = {}
        self._cached_analysis_box = None

        resolved_piece = (
                target_piece or
                (state.patterns_state.get("target_piece") if hasattr(state, "patterns_state") and isinstance(
                    state.patterns_state, dict) else None) or
                getattr(state, "selected_piece", None) or
                "N"
        )
        self.target_piece = resolved_piece
        self.active_sequence = []

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
        # --- BUTTON 1: PV Engine (Standalone) ---
        if hasattr(self, "btn_pv") and self.btn_pv:
            self.btn_pv.configure(
                text="PV Engine",
                command=self.toggle_engine_action,
                hover_color=THEME["btn_hover"]
            )

        # --- BUTTON 2: Piece Analysis ---
        if hasattr(self, "btn_piece") and self.btn_piece:
            self.btn_piece.configure(
                text="Piece Analysis",
                command=lambda: self.trigger_engine_mode("piece_pattern_mode"),
                hover_color=THEME["btn_hover"]
            )

        # --- BUTTONS 3 & 4: Blank Placeholders ---
        for btn_name in ("btn_placeholder_3", "btn_placeholder_4"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    text="",
                    state="disabled",
                    fg_color=THEME["bg_panel"]
                )

    def toggle_engine_action(self):
        is_running = getattr(self, "_engine_running", False)
        if is_running:
            self.stop_raw_engine_analysis()
        else:
            self.start_raw_engine_analysis()

    def start_raw_engine_analysis(self):
        if not hasattr(self, "current_node") or not self.current_node:
            self.update_engine_display("[No active position to evaluate.]\n")
            return

        try:
            board_obj = self.current_node.board()
        except Exception:
            return

        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True

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
                try:
                    engine = ChessEngine()

                    def callback(res):
                        if self.cancel:
                            return
                        current_depth = res.get('depth', 25)
                        raw_eval = res.get('eval', 0.0)
                        eval_str = raw_eval if isinstance(raw_eval,
                                                          str) and "M" in raw_eval else f"{float(raw_eval):+.2f}"

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
        self.run_patterns_1_analysis(target_game)

    def run_piece_pattern_analysis(self, target_game):
        target_box = getattr(self, "analysis_textbox", None) or getattr(self, "_cached_analysis_box", None)
        if target_box:
            try:
                target_box.configure(state="normal", fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
                inner_box.delete("1.0", "end")
                inner_box.insert("end", f"[{self.target_piece} Patterns: Ready to evaluate active game...]\n")
                inner_box.configure(state="disabled")
            except Exception as e:
                print(f"[PATTERNS DISPLAY ERROR] {e}")

    def analyze_piece_sequence(self, game_obj, piece_id):
        """Accurately parses moves from move 1, matching the exact color and piece type from two-letter codes."""
        resolved_game = self._resolve_game_obj(game_obj)
        if not resolved_game:
            return []

        try:
            board = resolved_game.board()
        except Exception:
            return []

        # Normalize piece_id (e.g., 'wb' -> color='w', type_char='b')
        p_id = str(piece_id).strip().lower()

        target_color = None
        target_type_char = None

        if len(p_id) == 2:
            target_color = chess.WHITE if p_id[0] == 'w' else chess.BLACK
            target_type_char = p_id[1]
        elif len(p_id) == 1:
            # Fallback if a single character is passed
            target_type_char = p_id
            target_color = None

        expected_piece_type = {
            "p": chess.PAWN,
            "n": chess.KNIGHT,
            "b": chess.BISHOP,
            "r": chess.ROOK,
            "q": chess.QUEEN,
            "k": chess.KING
        }.get(target_type_char, chess.PAWN)

        sequence = []
        for move_num, move in enumerate(resolved_game.mainline_moves(), start=1):
            san_move = board.san(move)
            piece_type = board.piece_type_at(move.from_square)
            piece_color = board.color_at(move.from_square)

            # Match piece type
            type_matches = (piece_type == expected_piece_type)

            # Match color if specified by a two-letter code
            color_matches = (target_color is None) or (piece_color == target_color)

            if type_matches and color_matches:
                sequence.append((board.fullmove_number, san_move))

            board.push(move)

        return sequence

    def _sync_analysis_selection(self):
        """Renders the analysis panel completely, dynamically pulling the live game and piece filter for all panels."""
        # --- 1. RESOLVE PIECE FROM ALL POSSIBLE SOURCES ---
        if hasattr(state, "patterns_state") and isinstance(state.patterns_state, dict):
            p_state_val = state.patterns_state.get("target_piece")
            if p_state_val:
                self.target_piece = p_state_val
        if hasattr(state, "selected_piece") and state.selected_piece:
            self.target_piece = state.selected_piece

        # --- 2. TARGET ONLY THE AUTHORIZED ANALYSIS TEXTBOX ---
        target_boxes = []
        for name in ("analysis_textbox", "analysis_box", "patterns_textbox"):
            box = getattr(self, name, None)
            if box and box not in target_boxes:
                target_boxes.append(box)

        if not target_boxes and self._cached_analysis_box:
            target_boxes.append(self._cached_analysis_box)

        if not target_boxes:
            print("[SYNC ERROR] No analysis text boxes found to render into.")
            return

        try:
            for target_box in target_boxes:
                target_box.configure(state="normal", fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
                inner_box.delete("1.0", "end")

                # Insert the target piece sequence header
                if self.current_game:
                    self.active_sequence = self.analyze_piece_sequence(self.current_game, self.target_piece)
                    if self.active_sequence:
                        formatted_seq = " -> ".join([f"{num}. {san}" for num, san in self.active_sequence])
                        inner_box.insert("end",
                                         f"Selected Piece [{self.target_piece}] Moves:\n{formatted_seq}\n\n" + "=" * 50 + "\n\n")
                    else:
                        inner_box.insert("end",
                                         f"Selected Piece [{self.target_piece}] Moves:\n(No movements found for [{self.target_piece}] in this specific game)\n\n" + "=" * 50 + "\n\n")
                else:
                    inner_box.insert("end",
                                     f"Selected Piece [{self.target_piece}] Moves:\n(No active game loaded)\n\n" + "=" * 50 + "\n\n")

                # Render standard move book contents
                eval_tag_colors = {
                    "red": THEME["eval_red"],
                    "orange": THEME["eval_orange"],
                    "green": THEME["eval_green"],
                    "light_blue": THEME["eval_light_blue"],
                    "default": THEME["eval_default"]
                }

                for tag_name, color in eval_tag_colors.items():
                    inner_box.tag_config(tag_name, foreground=color)

                inner_box.tag_config("active_tracker", background=THEME["active_tracker_bg"],
                                     foreground=THEME["active_tracker_fg"])

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
        self.current_game = resolved
        self.active_game = resolved  # Ensure active_game is set for the mixin

        res = None
        if hasattr(self, "load_game_hardwired") and callable(self.load_game_hardwired):
            res = self.load_game_hardwired(resolved, category_source=category_source)
        elif hasattr(self, "load_game_from_state") and callable(self.load_game_from_state):
            res = self.load_game_from_state(resolved, category_source=category_source)
        elif hasattr(super(), "load_game"):
            res = super().load_game(resolved, category_source=category_source)

        self._sync_analysis_selection()
        return res

    def trigger_engine_mode(self, mode):
        self.active_engine_mode = mode
        self._selected_mode_button = mode

        if hasattr(self, "btn_piece") and self.btn_piece:
            is_active = (mode == "piece_pattern_mode")
            try:
                self.btn_piece.configure(
                    fg_color=THEME["btn_hover"] if is_active else THEME["btn_initial"],
                    hover_color=THEME["btn_hover"],
                    text_color=THEME["text_primary"],
                )
            except Exception:
                pass

        if mode == "piece_pattern_mode":
            if hasattr(self, "active_game") and self.active_game:
                self.start_piece_pattern_analysis(self.active_game)
            else:
                print("[ANALYSIS ERROR] No active game loaded to analyze.")

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

    target_piece = (
            kwargs.get("target_piece") or
            (state_mod.patterns_state.get("target_piece") if hasattr(state_mod, "patterns_state") and isinstance(
                state_mod_patterns_state := state_mod.patterns_state, dict) else None) or
            getattr(state_mod, "selected_piece", None) or
            "N"
    )

    instance = PatternsAnalysis(
        master,
        filename="personal_catalog.pgn",
        initial_games=initial_games,
        target_game=defocus,
        active_index=active_index,
        target_piece=target_piece
    )
    state_mod.workspace = instance
    return instance


def create_patterns_analysis_workspace(master, initial_games=None, **kwargs):
    return create_workspace(master, initial_games=initial_games, **kwargs)