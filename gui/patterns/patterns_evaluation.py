import threading
import platform
from pathlib import Path
import chess
import chess.engine
import gui.app_state as state
from core.constants import THEME
from core.patterns_db import PatternsDatabase
from core.patterns_db import mark_move_good, mark_move_bad

class PatternsEvaluation(PatternsDatabase):
    """Handles game evaluation, piece sequence analysis, board state loading, UI synchronization, and Stockfish comparison worker threads."""

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
        """Accurately parses moves from move 1, matching the exact color and piece type."""
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
        """Renders the analysis panel completely, strictly preserving custom pattern/engine results across move navigation."""
        if getattr(self, "_has_tagged_pattern_view", False):
            return
        if hasattr(state, "patterns_state") and isinstance(state.patterns_state, dict):
            p_state_val = state.patterns_state.get("target_piece")
            if p_state_val:
                self.target_piece = p_state_val
        if hasattr(state, "selected_piece") and state.selected_piece:
            self.target_piece = state.selected_piece

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

        # If custom pattern or engine results were sent to the panel, restore them on navigation clicks
        if getattr(self, "_active_custom_analysis_content", None):
            try:
                for target_box in target_boxes:
                    target_box.configure(state="normal", fg_color=THEME["bg_surface"])
                    inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
                    inner_box.delete("1.0", "end")
                    inner_box.insert("end", self._active_custom_analysis_content)
                    target_box.configure(state="disabled")
                return
            except Exception:
                pass

        try:
            highlighted_moves = set()
            if self.current_game and hasattr(self, "analyze_piece_sequence"):
                try:
                    seq = self.analyze_piece_sequence(self.current_game, self.target_piece)
                    highlighted_moves = set(seq)
                except Exception as e:
                    print(f"[HIGHLIGHT ERROR] {e}")

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

                        applied_tag = "green" if is_pattern_match else (w_tag if w_tag in eval_tag_colors else "default")
                        is_active_white = (
                            (hasattr(self, "current_node") and self.current_node == w_node) or
                            (hasattr(self, "board_node") and self.board_node == w_node)
                        )
                        if is_active_white:
                            applied_tag = "active_tracker"

                        inner_box.insert("end", f"{w_text} ", (applied_tag, w_tag_name))
                        if w_node:
                            inner_box.tag_bind(w_tag_name, "<Button-1>", lambda *args, n=w_node: self.jump_to_node(n))
                    else:
                        inner_box.insert("end", "... ")

                    b_text = row.get("black", "")
                    b_tag = row.get("black_tag", "default")
                    b_node = row.get("black_node")

                    if b_text:
                        b_tag_name = f"b_{move_num}_{id(b_node)}" if b_node else f"b_{move_num}"
                        is_pattern_match = (move_num, b_text) in highlighted_moves

                        applied_tag = "green" if is_pattern_match else (b_tag if b_tag in eval_tag_colors else "default")
                        is_active_black = (
                            (hasattr(self, "current_node") and self.current_node == b_node) or
                            (hasattr(self, "board_node") and self.board_node == b_node)
                        )
                        if is_active_black:
                            applied_tag = "active_tracker"

                        inner_box.insert("end", f"{b_text} ", (applied_tag, b_tag_name))
                        if b_node:
                            inner_box.tag_bind(b_tag_name, "<Button-1>", lambda *args, n=b_node: self.jump_to_node(n))

                    inner_box.insert("end", " ")

                target_box.configure(state="disabled")
        except Exception as e:
            print(f"[SYNC ANALYSIS ERROR] {e}")

    def on_eval_good(self):
        """Marks current selected move as Good (forces yellow in engine window)."""
        current_node = getattr(self, "board_node", None) or getattr(self, "current_node", None)
        if current_node and current_node.parent and hasattr(current_node, "move"):
            parent_board = current_node.parent.board()
            san = parent_board.san(current_node.move)
            clean_san = san.replace("+", "").replace("#", "").lower()
            mark_move_good(clean_san)

        active_mode = getattr(self, "active_engine_mode", None)
        if active_mode:
            self.trigger_engine_mode(active_mode)

    def on_eval_bad(self):
        """Marks current selected move as Bad (strips yellow back to white)."""
        current_node = getattr(self, "board_node", None) or getattr(self, "current_node", None)
        if current_node and current_node.parent and hasattr(current_node, "move"):
            parent_board = current_node.parent.board()
            san = parent_board.san(current_node.move)
            clean_san = san.replace("+", "").replace("#", "").lower()
            mark_move_bad(clean_san)

        active_mode = getattr(self, "active_engine_mode", None)
        if active_mode:
            self.trigger_engine_mode(active_mode)

    def on_eval_idk(self):
        """Standby mode."""
        pass

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
        # Clear previous custom analysis cache when switching games
        self._active_custom_analysis_content = None

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

    def toggle_engine_action(self):
        """Controls the independent Engine comparison button with start/stop/pause depth-30 state management."""
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
        """Runs background worker for raw engine comparison lines with MultiPV=5 and depth 30 limit."""
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