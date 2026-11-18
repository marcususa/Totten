# ==========================================
# FILE: gui/patterns/patterns_evaluation.py
# ==========================================

import threading
import chess
import chess.engine
import gui.app_state as state
from core.chess_engine import ChessEngine
from core.constants import THEME
from core.patterns_db import PatternsDatabase, mark_move_good, mark_move_bad

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

        if not target_boxes and self._cached_analysis_box:
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

                inner_box.tag_config("active_tracker", background=THEME["active_tracker_bg"],
                                       foreground=THEME["active_tracker_fg"])

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
                            if (hasattr(self, "current_node") and self.current_node == w_node):
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

    def on_eval_good(self):
        current_node = getattr(self, "board_node", None) or getattr(self, "current_node", None)
        if current_node and current_node.parent and hasattr(current_node, "move"):
            clean_san = current_node.parent.board().san(current_node.move).replace("+", "").replace("#", "").lower()
            mark_move_good(clean_san)

    def on_eval_bad(self):
        current_node = getattr(self, "board_node", None) or getattr(self, "current_node", None)
        if current_node and current_node.parent and hasattr(current_node, "move"):
            clean_san = current_node.parent.board().san(current_node.move).replace("+", "").replace("#", "").lower()
            mark_move_bad(clean_san)

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
                    san = board_at_curr.san(next_node.move)
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

    def toggle_engine_action(self):
        """Identical toggle controller matching Mixed Collections and Catalog engine behavior."""
        is_running = getattr(self, "_engine_running", False)
        worker = getattr(self, "_current_raw_engine_worker", None)

        if is_running and (worker is None or not worker.is_alive()):
            is_running = False
            self._engine_running = False

        if is_running:
            self.stop_raw_engine_analysis()
        else:
            self.start_raw_engine_analysis()

    def start_raw_engine_analysis(self):
        """Runs exact background worker via ChessEngine matching mixed_core.py, targeting pv_textbox only."""
        if not hasattr(self, "current_node") or not self.current_node:
            if self.game_list:
                self.current_node = self._resolve_game_obj(self.game_list[0])
            else:
                self.update_engine_display("[No active position to evaluate.]\n")
                return

        try:
            board_obj = self.current_node.board()
        except Exception as e:
            self.update_engine_display(f"[Error getting board: {e}]\n")
            return

        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True

        self._engine_running = True
        if hasattr(self, "btn_pv") and self.btn_pv:
            try:
                self.btn_pv.configure(fg_color=THEME["btn_hover"], text="Stop Engine")
            except Exception:
                pass

        outer_self = self

        class RawEngineWorker(threading.Thread):
            def __init__(self, board_state):
                super().__init__()
                self.board_state = board_state
                self.cancel = False
                self.daemon = True

            def run(self):
                try:
                    eng = ChessEngine()

                    def callback(res):
                        if self.cancel:
                            return
                        depth = res.get('depth', 25)
                        raw_eval = res.get('eval', 0.0)
                        eval_str = raw_eval if "M" in str(raw_eval) else f"{float(raw_eval):+.2f}"
                        pv_lines = res.get('pv_lines', [])

                        formatted_lines = []
                        for idx, line in enumerate(pv_lines, start=1):
                            temp_b = self.board_state.copy()
                            numbered_pv = []
                            for m_str in line.strip().split():
                                try:
                                    m = temp_b.parse_san(m_str)
                                    if temp_b.turn == chess.WHITE:
                                        numbered_pv.append(f"{temp_b.fullmove_number}. {m_str}")
                                    else:
                                        if not numbered_pv:
                                            numbered_pv.append(f"{temp_b.fullmove_number}... {m_str}")
                                        else:
                                            numbered_pv.append(m_str)
                                    temp_b.push(m)
                                except Exception:
                                    numbered_pv.append(m_str)
                            formatted_lines.append(f"{idx}. {depth} | Eval: {eval_str} {' '.join(numbered_pv)}")

                        display_text = "\n\n".join(formatted_lines) + "\n" if formatted_lines else f"1. {depth} | Eval: {eval_str}\n"
                        outer_self.after(0, lambda: outer_self.update_engine_display(display_text))

                    eng.analyze_position(self.board_state, depths=(10, 15, 20, 25), multipv=5, callback=callback, worker_ref=self)
                except Exception as e:
                    outer_self.after(0, lambda: outer_self.update_engine_display(f"[Engine Error: {e}]\n"))
                finally:
                    outer_self.after(0, outer_self.stop_raw_engine_analysis)

        worker = RawEngineWorker(board_obj)
        self._current_raw_engine_worker = worker
        worker.start()

    def update_engine_display(self, text_content):
        """Strictly outputs raw engine results to pv_textbox only, leaving the analysis panel untouched."""
        target_box = getattr(self, "pv_textbox", None)
        if target_box:
            try:
                target_box.configure(state="normal", fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
                inner_box.delete("1.0", "end")
                inner_box.insert("end", text_content)
                target_box.configure(state="disabled")
            except Exception as e:
                print(f"[ENGINE DISPLAY ERROR] {e}")

    def stop_raw_engine_analysis(self):
        self._engine_running = False
        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True
            self._current_raw_engine_worker = None

        if hasattr(self, "btn_pv") and self.btn_pv:
            try:
                self.btn_pv.configure(fg_color=THEME["btn_initial"], text="Engine")
            except Exception:
                pass