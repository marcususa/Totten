# gui/patterns/patterns_analysis.py

import threading
import os
import platform
from pathlib import Path
import chess
import chess.engine
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

        # FORCE ALWAYS STARTING AT THE TOP (Index 0)
        if self.game_list and hasattr(self, "load_game"):
            self.load_game(self.game_list[0])

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
                self.pgn_tree.bind("f", lambda e: self._safe_handle_shortcut(self.on_flip_board, e))
                self.pgn_tree.bind("F", lambda e: self._safe_handle_shortcut(self.on_flip_board, e))

            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.bind("<Left>", lambda e: self._safe_handle_shortcut(self.on_prev_move, e))
                self.board_widget.bind("<Right>", lambda e: self._safe_handle_shortcut(self.on_next_move, e))
                self.board_widget.bind("f", lambda e: self._safe_handle_shortcut(self.on_flip_board, e))
                self.board_widget.bind("F", lambda e: self._safe_handle_shortcut(self.on_flip_board, e))
        except Exception as e:
            print(f"[SHORTCUT BIND ERROR] {e}")

    def on_flip_board(self, event=None):
        """Explicitly calls toggle_flip() on the board widget when 'f' or 'F' is pressed."""
        try:
            if hasattr(self, "board_widget") and self.board_widget:
                if hasattr(self.board_widget, "toggle_flip") and callable(self.board_widget.toggle_flip):
                    self.board_widget.toggle_flip()
                    print("[BOARD DEBUG] Board widget toggle_flip() executed successfully.")
        except Exception as e:
            print(f"[BOARD FLIP ERROR] {e}")

    def _safe_handle_shortcut(self, callback, event):
        try:
            print(f"[SHORTCUT DEBUG] Key pressed: {event.keysym}")
            focused = self.winfo_toplevel().focus_get()
            if focused and type(focused).__name__ in ("CTkTextbox", "CTkEntry", "Text", "Entry"):
                print("[SHORTCUT DEBUG] Ignored because focus is in a text box.")
                return

            if callable(callback):
                print(f"[SHORTCUT DEBUG] Executing callback: {callback.__name__}")
                try:
                    callback(event)
                except TypeError:
                    callback()
                return "break"
        except Exception as e:
            print(f"[SHORTCUT EXECUTION ERROR] {e}")

    def _bind_engine_buttons(self):
        # --- ONLY bind the standalone Engine button here (renamed from PV Engine) ---
        if hasattr(self, "btn_pv") and self.btn_pv:
            self.btn_pv.configure(
                text="Engine",
                command=self.toggle_engine_action,
                hover_color=THEME["btn_hover"]
            )

        # --- BUTTON 2: White Patterns ---
        for btn_name in ("btn_white", "btn_white_patterns"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(
                    text="White Patterns",
                    command=lambda: (print("[DEBUG CLICK] White Patterns clicked!"),
                                     self.trigger_engine_mode("white_patterns_mode")),
                    hover_color=THEME["btn_hover"]
                )
                break

        # --- BUTTON 3: Black Patterns ---
        for btn_name in ("btn_black", "btn_black_patterns"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(
                    text="Black Patterns",
                    command=lambda: (print("[DEBUG CLICK] Black Patterns clicked!"),
                                     self.trigger_engine_mode("black_patterns_mode")),
                    hover_color=THEME["btn_hover"]
                )
                break

        # --- BUTTON 4: Opening ---
        if hasattr(self, "btn_opening") and self.btn_opening:
            self.btn_opening.configure(
                text="Opening",
                command=lambda: (print("[DEBUG CLICK] Opening clicked!"),
                                 self.trigger_engine_mode("opening_pattern_mode")),
                hover_color=THEME["btn_hover"]
            )

        # --- BUTTON 5: Calculation ---
        if hasattr(self, "btn_calculation") and self.btn_calculation:
            self.btn_calculation.configure(
                text="Calculation",
                command=lambda: (print("[DEBUG CLICK] Calculation clicked!"),
                                 self.trigger_engine_mode("calculation_pattern_mode")),
                hover_color=THEME["btn_hover"]
            )

    def toggle_engine_action(self):
        """Controls the independent Engine button with start/stop/pause depth-30 state management."""
        is_running = getattr(self, "_engine_running", False)
        pausing_state = getattr(self, "_engine_pausing_to_depth_30", False)
        worker = getattr(self, "_current_raw_engine_worker", None)

        if is_running and (worker is None or not worker.is_alive()):
            is_running = False
            self._engine_running = False
            self._engine_pausing_to_depth_30 = False

        if not is_running:
            self._engine_running = True
            self._engine_pausing_to_depth_30 = False
            # Clear pattern mode so engine takes exclusive control
            self.active_engine_mode = None
            self.start_raw_engine_analysis()
        elif is_running and not pausing_state:
            self._engine_pausing_to_depth_30 = True
            if worker:
                worker.pausing_to_depth_30 = True
        else:
            self.stop_raw_engine_analysis()
            self.update_engine_display("[No active position to evaluate.]\n")

    def start_raw_engine_analysis(self):
        """Runs background worker for raw engine lines with MultiPV=5 and depth 30 limit using dynamic engine discovery."""
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
        self._engine_pausing_to_depth_30 = False

        for btn_name in ("btn_engine_action", "btn_engines", "btn_pv"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_hover"], text="Stop")
                except Exception:
                    pass

        outer_self = self

        class RawEngineWorker(threading.Thread):
            def __init__(self, board_state, outer):
                super().__init__()
                self.board_state = board_state
                self.outer = outer
                self.cancel = False
                self.pausing_to_depth_30 = False
                self.daemon = True

            def run(self):
                engine = None
                try:
                    # Dynamically look for an engine binary inside local /engine or /engines directories
                    engine_path = "stockfish"
                    exe_filename = "stockfish.exe" if platform.system() == "Windows" else "stockfish"

                    for folder_name in ("engine", "engines"):
                        folder_path = Path(folder_name)
                        if folder_path.exists() and folder_path.is_dir():
                            candidate = folder_path / exe_filename
                            if candidate.exists():
                                engine_path = str(candidate.resolve())
                                break
                            for file_path in folder_path.iterdir():
                                if file_path.is_file():
                                    if platform.system() == "Windows" and file_path.suffix.lower() == ".exe":
                                        engine_path = str(file_path.resolve())
                                        break
                                    elif platform.system() != "Windows":
                                        engine_path = str(file_path.resolve())
                                        break

                    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
                    limit = chess.engine.Limit(depth=30)

                    with engine.analysis(self.board_state, limit, multipv=5) as analysis:
                        latest_lines = {}
                        for info in analysis:
                            if self.cancel:
                                break

                            current_depth = info.get("depth", 0)
                            multipv_idx = info.get("multipv", 1)
                            score = info.get("score")
                            pv = info.get("pv", [])

                            if score and pv:
                                score_cp = score.white().score(mate_score=10000)
                                if score.is_mate():
                                    mate_val = score.white().mate()
                                    eval_str = f"M{abs(mate_val)}" if mate_val != 0 else "M0"
                                    if mate_val < 0:
                                        eval_str = f"-{eval_str}"
                                    else:
                                        eval_str = f"+{eval_str}"
                                else:
                                    eval_str = f"{score_cp / 100.0:+.2f}"

                                latest_lines[multipv_idx] = {
                                    "depth": current_depth,
                                    "eval": eval_str,
                                    "pv": pv
                                }

                                formatted_lines = []
                                for idx in sorted(latest_lines.keys()):
                                    line_data = latest_lines[idx]
                                    d = line_data["depth"]
                                    e = line_data["eval"]
                                    moves = line_data["pv"]

                                    temp_board = self.board_state.copy()
                                    numbered_pv = []
                                    for move in moves:
                                        san_move = temp_board.san(move)
                                        if temp_board.turn == chess.WHITE:
                                            numbered_pv.append(f"{temp_board.fullmove_number}. {san_move}")
                                        else:
                                            if len(numbered_pv) == 0:
                                                numbered_pv.append(f"{temp_board.fullmove_number}... {san_move}")
                                            else:
                                                numbered_pv.append(san_move)
                                        temp_board.push(move)

                                    moves_str = " ".join(numbered_pv)
                                    formatted_lines.append(f"{idx}. Depth {d}  Eval: {e}  {moves_str}")

                                display_text = "\n\n".join(formatted_lines) + "\n"
                                self.outer.after(0, lambda dt=display_text: self.outer.update_engine_display(dt))

                            if current_depth >= 30 and self.pausing_to_depth_30:
                                break

                except Exception as e:
                    print(f"[RAW ENGINE WORKER CRASH] {e}")
                finally:
                    if engine:
                        try:
                            engine.quit()
                        except Exception:
                            pass
                    self.outer.after(0, self.outer.stop_raw_engine_analysis)

        self._current_raw_engine_worker = RawEngineWorker(board_obj, self)
        self._current_raw_engine_worker.start()

    def stop_raw_engine_analysis(self):
        try:
            if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
                self._current_raw_engine_worker.cancel = True
                self._current_raw_engine_worker = None
        except Exception as e:
            print(f"[STOP ENGINE ERROR] {e}")

        self._engine_running = False

        # Reset engine button visual state safely
        for btn_name in ("btn_engine_action", "btn_engines", "btn_pv"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_initial"], text="Engine")
                except Exception:
                    pass

    def update_engine_display(self, text):
        # If a pattern mode is currently selected, ignore background engine ticks
        if getattr(self, "active_engine_mode", None) is not None:
            return

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

        p_id = str(piece_id).strip().lower()

        target_color = None
        target_type_char = None

        if len(p_id) == 2:
            target_color = chess.WHITE if p_id[0] == 'w' else chess.BLACK
            target_type_char = p_id[1]
        elif len(p_id) == 1:
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

            type_matches = (piece_type == expected_piece_type)
            color_matches = (target_color is None) or (piece_color == target_color)

            if type_matches and color_matches:
                sequence.append((board.fullmove_number, san_move))

            board.push(move)

        return sequence

    def _sync_analysis_selection(self):
        """Renders the analysis panel completely, dynamically pulling the live game moves and highlighting pattern piece moves."""
        if hasattr(state, "patterns_state") and isinstance(state.patterns_state, dict):
            p_state_val = state.patterns_state.get("target_piece")
            if p_state_val:
                self.target_piece = p_state_val
        if hasattr(state, "selected_piece") and state.selected_piece:
            self.target_piece = state.selected_piece

        highlighted_moves = set()
        if self.current_game and hasattr(self, "analyze_piece_sequence"):
            try:
                seq = self.analyze_piece_sequence(self.current_game, self.target_piece)
                highlighted_moves = set(seq)
            except Exception as e:
                print(f"[HIGHLIGHT ERROR] {e}")

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

                eval_tag_colors = {
                    "red": THEME["eval_red"],
                    "orange": THEME["eval_orange"],
                    "green": THEME.get("eval_green", "#2b8a3e"),
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
                        is_pattern_match = (move_num, w_text) in highlighted_moves

                        applied_tag = "green" if is_pattern_match else (
                            w_tag if w_tag in eval_tag_colors else "default")
                        is_active_white = (
                                (hasattr(self, "current_node") and self.current_node == w_node) or
                                (hasattr(self, "board_node") and self.board_node == w_node)
                        )
                        if is_active_white:
                            applied_tag = "active_tracker"

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
                        is_pattern_match = (move_num, b_text) in highlighted_moves

                        applied_tag = "green" if is_pattern_match else (
                            b_tag if b_tag in eval_tag_colors else "default")
                        is_active_black = (
                                (hasattr(self, "current_node") and self.current_node == b_node) or
                                (hasattr(self, "board_node") and self.board_node == b_node)
                        )
                        if is_active_black:
                            applied_tag = "active_tracker"

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
        self.active_game = resolved

        self.root_game_node = resolved
        self.current_node = resolved
        self.board_node = resolved

        self.analysis_rows = {}

        if resolved:
            try:
                curr = resolved
                while curr.variations:
                    next_node = curr.variation(0)
                    board_at_curr = curr.board()
                    move = next_node.move
                    san = board_at_curr.san(move)
                    move_num = board_at_curr.fullmove_number
                    is_white = (board_at_curr.turn == chess.WHITE)

                    if move_num not in self.analysis_rows:
                        self.analysis_rows[move_num] = {}

                    if is_white:
                        self.analysis_rows[move_num]["white"] = san
                        self.analysis_rows[move_num]["white_node"] = next_node
                    else:
                        self.analysis_rows[move_num]["black"] = san
                        self.analysis_rows[move_num]["black_node"] = next_node

                    curr = next_node
            except Exception as e:
                print(f"[ANALYSIS PARSE ERROR] {e}")

        res = None
        if hasattr(self, "load_game_hardwired") and callable(self.load_game_hardwired):
            res = self.load_game_hardwired(resolved, category_source=category_source)
        elif hasattr(self, "load_game_from_state") and callable(self.load_game_from_state):
            res = self.load_game_from_state(resolved, category_source=category_source)
        elif hasattr(super(), "load_game"):
            res = super().load_game(resolved, category_source=category_source)

        if hasattr(self, "board_widget") and self.board_widget and hasattr(self.board_widget, "set_position"):
            try:
                self.board_widget.set_position(resolved.board())
            except Exception:
                pass

        if hasattr(self, "active_engine_mode") and self.active_engine_mode:
            self.trigger_engine_mode(self.active_engine_mode)

        self._sync_analysis_selection()
        return res

    def trigger_engine_mode(self, mode):
        """Handles data loading for the selected analysis mode with clean exclusive textbox control."""
        # Instantly halt any running background engine tasks
        self.stop_raw_engine_analysis()

        self.active_engine_mode = mode
        self._selected_mode_button = mode

        if hasattr(self, "pv_textbox") and self.pv_textbox:
            try:
                target_box = self.pv_textbox
                target_box.configure(fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
                inner_box.configure(state="normal")
                inner_box.delete("1.0", "end")

                if mode == "white_patterns_mode":
                    from core.piecepatterns import fetch_patterns_by_color
                    patterns = fetch_patterns_by_color("white")
                    inner_box.insert("end", str(patterns) + "\n")
                elif mode == "black_patterns_mode":
                    from core.piecepatterns import fetch_patterns_by_color
                    patterns = fetch_patterns_by_color("black")
                    inner_box.insert("end", str(patterns) + "\n")
                elif mode == "opening_pattern_mode":
                    if hasattr(self, "current_game") and self.current_game:
                        eco_val = self.current_game.headers.get("ECO")
                        if eco_val and hasattr(self, "load_games_by_eco"):
                            self.load_games_by_eco(eco_val, active_game=self.current_game)
                        else:
                            inner_box.insert("end", "[Opening Filter] Current game has no ECO header.\n")
                    else:
                        inner_box.insert("end", "[Opening Filter] No active game loaded.\n")
                elif mode == "calculation_pattern_mode":
                    inner_box.insert("end", "[Calculation Patterns Workspace Ready]\n")

                inner_box.configure(state="disabled")
            except Exception as e:
                print(f"[ERROR loading pattern mode {mode}]: {e}")


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