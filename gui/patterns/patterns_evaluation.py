# ==========================================
# FILE: gui/patterns/patterns_evaluation.py
# ==========================================

import threading
import chess
import chess.engine
import gui.app_state as state
from core.chess_engine import ChessEngine
from core.constants import THEME
from core.patterns_db import PatternsDatabase


class PatternsEvaluation(PatternsDatabase):
    """Handles game evaluation, piece sequence analysis, board state loading, UI synchronization, and ChessEngine worker threads."""

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

    def analyze_piece_sequence(self, game_obj, piece_id):
        resolved_game = self._resolve_game_obj(game_obj)
        if not resolved_game:
            return []

        try:
            board = resolved_game.board()
        except Exception:
            return []

        p_id = str(piece_id).strip().lower()
        target_color = chess.WHITE if len(p_id) == 2 and p_id[0] == 'w' else (chess.BLACK if len(p_id) == 2 else None)
        target_type_char = p_id[1] if len(p_id) == 2 else p_id

        expected_piece_type = {
            "p": chess.PAWN, "n": chess.KNIGHT, "b": chess.BISHOP,
            "r": chess.ROOK, "q": chess.QUEEN, "k": chess.KING
        }.get(target_type_char, chess.PAWN)

        sequence = []
        for move_num, move in enumerate(resolved_game.mainline_moves(), start=1):
            san_move = board.san(move)
            piece_type = board.piece_type_at(move.from_square)
            piece_color = board.color_at(move.from_square)

            if piece_type == expected_piece_type and (target_color is None or piece_color == target_color):
                sequence.append((board.fullmove_number, san_move))

            board.push(move)

        return sequence

    def _sync_analysis_selection(self):
        if getattr(self, "_has_tagged_pattern_view", False):
            return
        if hasattr(state, "patterns_state") and isinstance(state.patterns_state, dict):
            p_state_val = state.patterns_state.get("target_piece")
            if p_state_val:
                self.target_piece = p_state_val

        target_boxes = []
        for name in ("analysis_textbox", "analysis_box", "patterns_textbox"):
            box = getattr(self, name, None)
            if box and box not in target_boxes:
                target_boxes.append(box)

        if not target_boxes and getattr(self, "_cached_analysis_box", None):
            target_boxes.append(self._cached_analysis_box)

        if not target_boxes:
            return

        try:
            highlighted_moves = set()
            if self.current_game and hasattr(self, "analyze_piece_sequence"):
                try:
                    seq = self.analyze_piece_sequence(self.current_game, self.target_piece)
                    highlighted_moves = set(seq)
                except Exception:
                    pass

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

                inner_box.tag_config(
                    "active_tracker",
                    background=THEME["active_tracker_bg"],
                    foreground=THEME["active_tracker_fg"]
                )

                sorted_moves = sorted(self.analysis_rows.keys())
                for move_num in sorted_moves:
                    row = self.analysis_rows[move_num]
                    inner_box.insert("end", f"{move_num}. ")

                    for color_key, text_key, node_key in [("white", "white", "white_node"), ("black", "black", "black_node")]:
                        w_text = row.get(text_key, "")
                        w_node = row.get(node_key)
                        if w_text:
                            is_match = (move_num, w_text) in highlighted_moves
                            applied_tag = "green" if is_match else "default"
                            if hasattr(self, "current_node") and self.current_node == w_node:
                                applied_tag = "active_tracker"
                            inner_box.insert("end", f"{w_text} ", (applied_tag, f"{color_key}_{move_num}"))
                            if w_node:
                                inner_box.tag_bind(f"{color_key}_{move_num}", "<Button-1>", lambda *args, n=w_node: self.jump_to_node(n))
                        else:
                            if color_key == "white":
                                inner_box.insert("end", "... ")

                    inner_box.insert("end", " ")
                target_box.configure(state="disabled")
        except Exception as e:
            print(f"[SYNC ANALYSIS ERROR] {e}")

    def load_games_list(self, games_list, focused_game=None):
        if not games_list:
            return
        self.game_list = games_list
        if hasattr(self, "populate_catalog_tree"):
            self.populate_catalog_tree(self.game_list)
        if hasattr(self, "load_game"):
            self.load_game(focused_game if focused_game else games_list[0])

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
        if hasattr(super(), "load_game"):
            res = super().load_game(resolved, category_source=category_source)

        if hasattr(self, "board_widget") and self.board_widget and resolved:
            try:
                self.board_widget.set_position(resolved.board())
            except Exception:
                pass

        self._sync_analysis_selection()
        return res

    def _get_current_engine_name(self) -> str:
        if getattr(self, "current_engine", None):
            return self.current_engine
        app_state = globals().get("state")
        patterns_state = getattr(app_state, "patterns_state", None) if app_state is not None else None
        if isinstance(patterns_state, dict):
            return patterns_state.get("current_engine") or "Stockfish"
        return "Stockfish"

    def _get_live_engine_textbox(self):
        for attr_name in ("pv_textbox", "raw_engine_textbox", "engine_textbox", "_cached_analysis_box"):
            box = getattr(self, attr_name, None)
            if box:
                return box
        return None

    def _ensure_pv_tags(self, inner_box):
        primary_color = THEME.get("text_primary", "#ffffff")
        secondary_color = THEME.get("text_secondary", primary_color)
        inner_box.tag_config(
            "pv_header",
            foreground=primary_color,
            font=("Arial", 11, "bold"),
            spacing1=4,
            spacing3=1,
        )
        inner_box.tag_config(
            "pv_eval_pos",
            foreground=primary_color,
            font=("Arial", 11, "bold"),
        )
        inner_box.tag_config(
            "pv_eval_neg",
            foreground=primary_color,
            font=("Arial", 11, "bold"),
        )
        inner_box.tag_config(
            "pv_eval_even",
            foreground=primary_color,
            font=("Arial", 11, "bold"),
        )
        inner_box.tag_config(
            "pv_moves",
            foreground=secondary_color,
            font=("Arial", 11),
            spacing1=0,
            spacing3=6,
        )
        inner_box.tag_config(
            "pv_status",
            foreground=secondary_color,
            font=("Arial", 11),
        )

    def _eval_tag_for_string(self, eval_str: str) -> str:
        text = str(eval_str or "").strip()
        if text.startswith("+"):
            try:
                val = float(text)
                if val >= 0.35:
                    return "pv_eval_pos"
                if val <= -0.35:
                    return "pv_eval_neg"
                return "pv_eval_even"
            except ValueError:
                return "pv_eval_pos"
        if text.startswith("-"):
            return "pv_eval_neg"
        return "pv_eval_even"

    def toggle_engine_action(self):
        """Identical toggle controller matching Mixed Collections and Catalog engine behavior."""
        is_running = getattr(self, "_engine_running", False)
        worker = getattr(self, "_current_raw_engine_worker", None)

        if is_running and (worker is None or not worker.is_alive()) and not getattr(self, "_raw_engine_debounce_id", None):
            is_running = False
            self._engine_running = False

        if is_running:
            self.stop_raw_engine_analysis()
        else:
            self.start_raw_engine_analysis()

    def start_raw_engine_analysis(self):
        """Runs exact background worker via ChessEngine matching mixed_engine.py, targeting pv_textbox only."""
        self._raw_engine_debounce_id = None
        if not hasattr(self, "current_node") or not self.current_node:
            if getattr(self, "game_list", None):
                self.current_node = self._resolve_game_obj(self.game_list[0])
            else:
                self.update_engine_display("No active position to evaluate.\n")
                return

        try:
            board_obj = self.current_node.board()
        except Exception as e:
            self.update_engine_display(f"[Error getting board: {e}]\n")
            return

        self._raw_engine_gen = getattr(self, "_raw_engine_gen", 0) + 1
        current_gen = self._raw_engine_gen

        prev_worker = getattr(self, "_current_raw_engine_worker", None)
        if prev_worker:
            prev_worker.cancel = True
            if getattr(prev_worker, "engine_client", None):
                try:
                    prev_worker.engine_client.stop_active_engine()
                except Exception:
                    pass

        self._engine_running = True
        for btn_name in ("btn_pv", "btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_hover"], text="Stop Engine")
                except Exception:
                    pass

        outer_self = self

        class RawEngineWorker(threading.Thread):
            def __init__(self, board_state, outer, gen_token):
                super().__init__()
                self.board_state = board_state
                self.outer = outer
                self.generation = gen_token
                self.expected_generation = gen_token
                self.cancel = False
                self.pausing_to_depth_30 = False
                self.daemon = True
                self.engine_client = None

            def run(self):
                try:
                    eng = ChessEngine(current_engine=self.outer._get_current_engine_name())
                    self.engine_client = eng

                    def callback(res):
                        if self.cancel or self.generation != getattr(self.outer, "_raw_engine_gen", self.generation):
                            return

                        raw_lines = res.get("lines", [])
                        structured = []
                        if raw_lines:
                            for entry in raw_lines:
                                item = dict(entry)
                                item["board_state"] = self.board_state
                                structured.append(item)
                        else:
                            current_depth = res.get("depth", 0)
                            raw_eval = res.get("eval", 0.0)
                            eval_str = raw_eval if isinstance(raw_eval, str) else f"{float(raw_eval):+.2f}"
                            pv_lines = res.get("pv_lines", [])
                            for idx, line in enumerate(pv_lines, start=1):
                                structured.append({
                                    "pv_index": idx,
                                    "depth": current_depth,
                                    "eval": eval_str,
                                    "moves_san": line.strip().split() if line else [],
                                    "board_state": self.board_state,
                                })

                        self.outer.after(
                            0,
                            lambda sl=structured, g=self.generation: self._apply_ui_update(g, sl),
                        )

                    eng.analyze_position(
                        self.board_state,
                        depths=(1, 5, 10, 15, 20, 25),
                        multipv=5,
                        callback=callback,
                        worker_ref=self,
                        max_depth=30,
                    )
                except Exception as e:
                    if not self.cancel:
                        print(f"[RAW ENGINE WORKER CRASH] {e}")
                finally:
                    if self.generation == getattr(self.outer, "_raw_engine_gen", self.generation) and not self.cancel:
                        self.outer.after(0, self.outer.stop_raw_engine_analysis)

            def _apply_ui_update(self, gen_token, structured):
                if self.cancel or gen_token != getattr(self.outer, "_raw_engine_gen", gen_token):
                    return
                if not getattr(self.outer, "_engine_running", False):
                    return
                outer_self.update_engine_display("", structured_lines=structured)

        worker = RawEngineWorker(board_obj, self, current_gen)
        self._current_raw_engine_worker = worker
        worker.start()

    def update_engine_display(self, text, structured_lines=None):
        """
        Renders live PV output into the left-column engine panel with clean visual
        separation between lines (eval + depth header, then numbered moves) and
        zero time/millisecond metrics. Left-panel evaluations use the primary theme color
        while colored evaluations remain reserved for the right-side Analysis panel.
        """
        target_box = self._get_live_engine_textbox()
        if not target_box:
            return

        try:
            primary_color = THEME.get("text_primary", "#ffffff")
            target_box.configure(fg_color=THEME["bg_surface"], text_color=primary_color)
            inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
            inner_box.configure(state="normal", fg=primary_color)
            self._ensure_pv_tags(inner_box)
            for tag_name in ("red", "orange", "green", "light_blue", "default"):
                inner_box.tag_config(tag_name, foreground=primary_color)
            inner_box.delete("1.0", "end")
            if text:
                inner_box.insert("end", text, ("pv_status",))

            if structured_lines:
                for line_info in structured_lines:
                    idx = line_info.get("pv_index", 1)
                    depth = line_info.get("depth", 0)
                    eval_str = line_info.get("eval", "+0.00")
                    moves = line_info.get("moves_san", [])
                    board_state = line_info.get("board_state")

                    numbered_pv = []
                    if board_state is not None and moves:
                        temp_board = board_state.copy()
                        for m_idx, san_move in enumerate(moves):
                            if temp_board.turn == chess.WHITE:
                                numbered_pv.append(f"{temp_board.fullmove_number}. {san_move}")
                            else:
                                if m_idx == 0:
                                    numbered_pv.append(f"{temp_board.fullmove_number}... {san_move}")
                                else:
                                    numbered_pv.append(san_move)
                            try:
                                mv = temp_board.parse_san(san_move)
                                temp_board.push(mv)
                            except Exception:
                                break
                    else:
                        numbered_pv = list(moves)

                    moves_str = " ".join(numbered_pv) if numbered_pv else "(none)"
                    eval_tag = self._eval_tag_for_string(eval_str)

                    inner_box.insert("end", f"#{idx} ", ("pv_header",))
                    inner_box.insert("end", f"{eval_str}", (eval_tag,))
                    inner_box.insert("end", f" | Depth {depth}\n", ("pv_header",))
                    inner_box.insert("end", f" {moves_str}\n", ("pv_moves",))

            inner_box.configure(state="disabled")
        except Exception as e:
            print(f"[ENGINE DISPLAY ERROR] {e}")

    def stop_raw_engine_analysis(self):
        self._raw_engine_gen = getattr(self, "_raw_engine_gen", 0) + 1
        pending_after = getattr(self, "_raw_engine_debounce_id", None)
        if pending_after and hasattr(self, "after_cancel"):
            try:
                self.after_cancel(pending_after)
            except Exception:
                pass
        self._raw_engine_debounce_id = None

        self._engine_running = False
        if hasattr(self, "_current_raw_engine_worker") and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True
            if getattr(self._current_raw_engine_worker, "engine_client", None):
                try:
                    self._current_raw_engine_worker.engine_client.stop_active_engine()
                except Exception:
                    pass
            self._current_raw_engine_worker = None

        for btn_name in ("btn_pv", "btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_initial"], text="Engine")
                except Exception:
                    pass