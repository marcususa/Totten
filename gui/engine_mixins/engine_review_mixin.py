import threading
import chess.pgn
from core.chess_engine import ChessEngine


class EngineReviewMixin:
    def trigger_engine_mode(self, mode_name):
        self.active_engine_mode = mode_name

        if hasattr(self, "btn_review") and self.btn_review:
            self.btn_review.configure(fg_color="#2e4a8c")
        if hasattr(self, "candidates_container"):
            self.candidates_container.pack_forget()
        if hasattr(self, "review_container"):
            self.review_container.pack(fill="both", expand=True)
        if self.active_game:
            self.start_game_review(self.active_game)

    def toggle_game(self, event):
        item = self.pgn_tree.identify_row(event.y)
        if not item:
            return

        self.pgn_tree.selection_set(item)

        game = self.preview_lookup.get(item)
        if not game:
            return

        self.active_game = game
        self.current_node = game
        self.root_game_node = game

        self._update_active_boards(self.current_node.board())

        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
        pgn_text_export = game.accept(exporter)

        self.pgn_data_text.configure(state="normal")
        self.pgn_data_text.delete("1.0", "end")
        self.pgn_data_text.insert("end", pgn_text_export)
        self.pgn_data_text.configure(state="disabled")

        self._load_plain_game_moves(game)

    def _load_plain_game_moves(self, game_obj):
        self.after(50, lambda: self._process_game_moves_safely(game_obj))

    def _process_game_moves_safely(self, game_obj):
        if not game_obj:
            return

        try:
            game = game_obj
            temp_board = game.board()

            if hasattr(self, "moves_textbox") and self.moves_textbox:
                box = self.moves_textbox
                moves_box = getattr(box, "_textbox", getattr(box, "textbox", box))
                moves_box.configure(state="normal")
                moves_box.delete("1.0", "end")

                node = game
                move_num = 1
                is_white = True

                while node.variations:
                    next_node = node.variation(0)
                    move = next_node.move
                    move_san = temp_board.san(move)
                    temp_board.push(move)

                    if is_white:
                        prefix = f"{move_num}. "
                        moves_box.insert("end", prefix)
                    else:
                        if node == game:
                            moves_box.insert(f"{move_num}... ")

                    tag_name = str(id(next_node))
                    moves_box.insert("end", f"{move_san} ", tag_name)
                    moves_box.tag_bind(tag_name, "<Button-1>", lambda e, n=next_node: self.jump_to_node(n))
                    moves_box.tag_config(tag_name, foreground="#f8fafc")

                    if not is_white:
                        move_num += 1

                    is_white = not is_white
                    node = next_node

                moves_box.configure(state="disabled")

            if hasattr(self, "_sync_analysis_selection"):
                self._sync_analysis_selection()

        except Exception as e:
            print(f"DEBUG: Error parsing game moves safely -> {e}")
            if hasattr(self, "moves_textbox") and self.moves_textbox:
                try:
                    box = self.moves_textbox
                    tb = getattr(box, "_textbox", getattr(box, "textbox", box))
                    tb.configure(state="disabled")
                except Exception:
                    pass

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

            def run(self):
                def stream_callback(res):
                    if self.cancel:
                        return

                    move_num = res['move_num']
                    is_white = res['is_white']
                    curr_eval = res['eval_after']

                    eval_str = f" {{{curr_eval:+.2f}}}" if abs(curr_eval) >= 0.3 else ""
                    move_display = f"{res['played_san']}{eval_str}"
                    abs_val = abs(curr_eval)

                    is_inaccuracy = (0.3 <= abs_val <= 0.59)
                    tag_to_apply = "default"

                    if abs_val >= 2.6:
                        tag_to_apply = "red"
                        if is_white:
                            self.white_streak = 0
                        else:
                            self.black_streak = 0
                    elif 1.0 <= abs_val <= 2.5:
                        tag_to_apply = "orange"
                        if is_white:
                            self.white_streak = 0
                        else:
                            self.black_streak = 0
                    elif 0.6 <= abs_val <= 0.99:
                        tag_to_apply = "green"
                    elif is_inaccuracy:
                        if is_white:
                            self.white_streak += 1
                            self.black_streak = 0
                            tag_to_apply = "green" if self.white_streak >= 3 else "light_blue"
                        else:
                            self.black_streak += 1
                            self.white_streak = 0
                            tag_to_apply = "green" if self.black_streak >= 3 else "light_blue"

                    if move_num not in self.outer.analysis_rows:
                        self.outer.analysis_rows[move_num] = {
                            "white": "", "black": "",
                            "white_tag": "default", "black_tag": "default"
                        }

                    if is_white:
                        self.outer.analysis_rows[move_num]["white"] = move_display
                        self.outer.analysis_rows[move_num]["white_tag"] = tag_to_apply
                    else:
                        self.outer.analysis_rows[move_num]["black"] = move_display
                        self.outer.analysis_rows[move_num]["black_tag"] = tag_to_apply

                    self.outer.after(0, self.outer._sync_analysis_selection)

                try:
                    print(f"[ENGINE WORKER] Starting analysis for mode: {self.analysis_mode}")
                    engine_worker = ChessEngine()
                    engine_worker.analyze_game(self.game_obj, mode=self.analysis_mode, callback=stream_callback)
                except Exception as e:
                    print(f"[ENGINE WORKER CRASH] Mode {self.analysis_mode} failed: {e}")

        self._current_analysis_worker = WorkerThread(target_game, self, mode)
        self._current_analysis_worker.start()

    def _sync_analysis_selection(self):
        """Renders Mode 1 analysis rows into the analysis textbox using the exact evaluation tags dictated by the review worker."""
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return

        box = self.analysis_textbox
        target_box = getattr(box, "_textbox", getattr(box, "textbox", box))

        try:
            target_box.configure(state="normal")
            target_box.delete("1.0", "end")

            # Match the exact tags produced by the review worker
            eval_tag_colors = {
                "red": "#FF4444",
                "orange": "#FFA500",
                "green": "#00C851",
                "light_blue": "#33b5e5",
                "default": "#f8fafc"
            }

            for tag_name, color in eval_tag_colors.items():
                target_box.tag_config(tag_name, foreground=color)

            for move_num in sorted(self.analysis_rows.keys()):
                row = self.analysis_rows[move_num]
                target_box.insert("end", f"{move_num}. ")

                w_text = row.get("white", "")
                w_tag = row.get("white_tag", "default")
                if w_text:
                    target_box.insert("end", f"{w_text} ", w_tag if w_tag in eval_tag_colors else "default")
                else:
                    target_box.insert("end", "... ")

                b_text = row.get("black", "")
                b_tag = row.get("black_tag", "default")
                if b_text:
                    target_box.insert("end", f"{b_text}\n", b_tag if b_tag in eval_tag_colors else "default")
                else:
                    target_box.insert("end", "\n")

            target_box.configure(state="disabled")
        except Exception as e:
            print(f"[SYNC ANALYSIS ERROR] {e}")