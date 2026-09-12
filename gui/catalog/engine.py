import threading
import chess
from core.constants import THEME
from core.chess_engine import ChessEngine


class CatalogEngineMixin:
    """Mixin class to handle background engine workers and evaluation displays."""

    def toggle_engine_action(self):
        """Controls the independent Engine button for raw live evaluation on the left."""
        is_running = getattr(self, "_engine_running", False)
        if is_running:
            self.start_raw_engine_analysis()
        else:
            self.stop_raw_engine_analysis()

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
                                # Format moves with proper numbering starting from current position
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

        if hasattr(self, "btn_engine_action") and self.btn_engine_action:
            try:
                self.btn_engine_action.configure(text="Engine")
            except Exception:
                pass

        # Intentionally left without clearing display text so results remain frozen on screen.

    def update_engine_display(self, text):
        """Strictly controls the left-column pv_textbox for raw engine outputs."""
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
                        target_node = self.game_obj
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
        """Renders the analysis panel completely like a continuous book, letting the textbox handle native word-wrapping."""
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return

        box = self.analysis_textbox
        box.configure(fg_color=THEME["bg_surface"])
        target_box = getattr(box, "_textbox", getattr(box, "textbox", box))

        try:
            target_box.configure(state="normal")
            target_box.delete("1.0", "end")

            eval_tag_colors = {
                "red": THEME["eval_red"],
                "orange": THEME["eval_orange"],
                "green": THEME["eval_green"],
                "light_blue": THEME["eval_light_blue"],
                "default": THEME["eval_default"]
            }

            for tag_name, color in eval_tag_colors.items():
                target_box.tag_config(tag_name, foreground=color)

            target_box.tag_config("active_tracker", background=THEME["active_tracker_bg"],
                                  foreground=THEME["active_tracker_fg"])

            sorted_moves = sorted(self.analysis_rows.keys())
            for move_num in sorted_moves:
                row = self.analysis_rows[move_num]
                target_box.insert("end", f"{move_num}. ")

                # White move formatting
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

                    target_box.insert("end", f"{w_text} ", (applied_tag, w_tag_name))
                    if w_node:
                        target_box.tag_bind(w_tag_name, "<Button-1>", lambda e, n=w_node: self.jump_to_node(n))
                else:
                    target_box.insert("end", "... ")

                # Black move formatting
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

                    target_box.insert("end", f"{b_text} ", (applied_tag, b_tag_name))
                    if b_node:
                        target_box.tag_bind(b_tag_name, "<Button-1>", lambda e, n=b_node: self.jump_to_node(n))

                target_box.insert("end", "    ")

            target_box.configure(state="disabled")
        except Exception as e:
            print(f"[SYNC ANALYSIS ERROR] {e}")