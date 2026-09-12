import threading
import chess
import chess.pgn
from core.chess_engine import ChessEngine


class EngineReviewMixin:
    def _safe_configure_textbox(self, box, state=None, text_content=None):
        try:
            bg_color = "#1e293b"
            if state:
                try:
                    box.configure(state=state)
                except Exception:
                    pass
            try:
                box.configure(bg=bg_color)
            except Exception:
                pass

            target_box = getattr(box, "_textbox", getattr(box, "textbox", box))
            if target_box is not box:
                try:
                    target_box.configure(bg=bg_color)
                except Exception:
                    pass

            if text_content is not None:
                target_box.delete("1.0", "end")
                target_box.insert("end", text_content)
        except Exception as e:
            print(f"[TEXTBOX CONFIG ERROR] {e}")

    def trigger_engine_mode(self, mode_name):
        self.active_engine_mode = mode_name

        if hasattr(self, "btn_review") and self.btn_review:
            try:
                self.btn_review.configure(bg="#344268")
            except Exception:
                pass
        if hasattr(self, "candidates_container"):
            try:
                self.candidates_container.pack_forget()
            except Exception:
                pass
        if hasattr(self, "review_container"):
            try:
                self.review_container.pack(fill="both", expand=True)
            except Exception:
                pass

        if mode_name == "review":
            if hasattr(self, "active_game") and self.active_game:
                self.start_game_review(self.active_game)

    def start_game_review(self, target_game):
        if not target_game:
            print("[ENGINE REVIEW] No target game provided for review.")
            return

        game_id = id(target_game)
        if hasattr(self, "analysis_cache") and game_id in self.analysis_cache:
            self.analysis_rows = self.analysis_cache[game_id]
            self._sync_analysis_selection()
            return

        self._run_analysis_worker(target_game, mode="review")

    def toggle_game(self, event):
        item = self.pgn_tree.identify_row(event.y)
        if not item:
            return

        self.pgn_tree.selection_set(item)
        game = self.preview_lookup.get(item)
        if not game:
            return

        if getattr(self, "active_game", None) == game:
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

        if not hasattr(self, "analysis_cache"):
            self.analysis_cache = {}

        game_id = id(game)
        if game_id in self.analysis_cache:
            self.analysis_rows = self.analysis_cache[game_id]
            self._sync_analysis_selection()
        else:
            self.analysis_rows = {}
            if hasattr(self, "analysis_textbox") and self.analysis_textbox:
                box = self.analysis_textbox
                target_box = getattr(box, "_textbox", getattr(box, "textbox", box))
                self._safe_configure_textbox(box, state="normal", text_content="[Game loaded. Click Game Review to analyze full game.]\n")
                target_box.configure(state="disabled")

    def jump_to_node(self, node):
        if not node:
            return
        self.current_node = node
        self.board_node = node
        self._update_active_boards(node.board())
        if hasattr(self, "update_active_move_highlight"):
            self.update_active_move_highlight()
        self._sync_analysis_selection()

    def _load_plain_game_moves(self, game_obj):
        if not game_obj:
            return
        try:
            game = game_obj
            temp_board = game.board()

            if hasattr(self, "analysis_secondary_textbox") and self.analysis_secondary_textbox:
                box = self.analysis_secondary_textbox
                moves_box = getattr(box, "_textbox", getattr(box, "textbox", box))
                self._safe_configure_textbox(box, state="normal")
                moves_box.delete("1.0", "end")

                node = game
                move_num = 1

                while node.variations:
                    next_node = node.variation(0)
                    move = next_node.move
                    move_san = temp_board.san(move)
                    is_white = temp_board.turn == chess.WHITE
                    temp_board.push(move)

                    tag_name = str(id(next_node))
                    if is_white:
                        moves_box.insert("end", f"{move_num}. {move_san} ", ("default", tag_name))
                    else:
                        moves_box.insert("end", f"{move_san} ", ("default", tag_name))
                        move_num += 1

                    moves_box.tag_bind(tag_name, "<Button-1>", lambda e, n=next_node: self.jump_to_node(n))
                    moves_box.tag_config(tag_name, foreground="#f8fafc")
                    node = next_node

                moves_box.configure(state="disabled")
        except Exception as e:
            print(f"DEBUG: Error parsing game moves -> {e}")

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

                        move_display = played_san
                        tag_to_apply = "default"

                        if move_num >= 8:
                            loss = (self.last_eval - curr_eval) if is_white else (curr_eval - self.last_eval)
                            self.last_eval = curr_eval
                            if loss >= 2.6:
                                tag_to_apply = "red"
                                move_display = f"{played_san} {{{curr_eval:+.2f}}} ??"
                            elif 1.0 <= loss <= 2.5:
                                tag_to_apply = "orange"
                                move_display = f"{played_san} {{{curr_eval:+.2f}}} ?"

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
                    engine_worker = ChessEngine()
                    engine_worker.analyze_game(self.game_obj, mode=self.analysis_mode, callback=stream_callback)
                    if not self.cancel and self.analysis_mode == "review":
                        if not hasattr(self.outer, "analysis_cache"):
                            self.outer.analysis_cache = {}
                        self.outer.analysis_cache[id(self.game_obj)] = self.outer.analysis_rows
                except Exception as e:
                    print(f"[ENGINE WORKER CRASH] {e}")

        self._current_analysis_worker = WorkerThread(target_game, self, mode)
        self._current_analysis_worker.start()

    def _sync_analysis_selection(self):
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return

        box = self.analysis_textbox
        target_box = getattr(box, "_textbox", getattr(box, "textbox", box))

        try:
            self._safe_configure_textbox(box, state="normal")
            target_box.delete("1.0", "end")

            eval_tag_colors = {
                "red": "#e5534b",
                "orange": "#f0883e",
                "green": "#57ab5a",
                "light_blue": "#539bf5",
                "default": "#f8fafc"
            }

            for tag_name, color in eval_tag_colors.items():
                target_box.tag_config(tag_name, foreground=color)

            target_box.tag_config("active_tracker", background="#11587a", foreground="#ffffff")

            for move_num in sorted(self.analysis_rows.keys()):
                row = self.analysis_rows[move_num]
                target_box.insert("end", f"{move_num}. ")

                w_text = row.get("white", "")
                w_tag = row.get("white_tag", "default")
                w_node = row.get("white_node")

                if w_text:
                    w_tag_name = f"w_{move_num}_{id(w_node)}" if w_node else f"w_{move_num}"
                    is_active_white = (
                        (hasattr(self, "current_node") and self.current_node == w_node) or
                        (hasattr(self, "board_node") and self.board_node == w_node)
                    )
                    applied_tag = "active_tracker" if is_active_white else (w_tag if w_tag in eval_tag_colors else "default")
                    target_box.insert("end", f"{w_text} ", (applied_tag, w_tag_name))
                    if w_node:
                        target_box.tag_bind(w_tag_name, "<Button-1>", lambda e, n=w_node: self.jump_to_node(n))
                else:
                    target_box.insert("end", "... ")

                b_text = row.get("black", "")
                b_tag = row.get("black_tag", "default")
                b_node = row.get("black_node")

                if b_text:
                    b_tag_name = f"b_{move_num}_{id(b_node)}" if b_node else f"b_{move_num}"
                    is_active_black = (
                        (hasattr(self, "current_node") and self.current_node == b_node) or
                        (hasattr(self, "board_node") and self.board_node == b_node)
                    )
                    applied_tag = "active_tracker" if is_active_black else (b_tag if b_tag in eval_tag_colors else "default")
                    target_box.insert("end", f"{b_text}\n", (applied_tag, b_tag_name))
                    if b_node:
                        target_box.tag_bind(b_tag_name, "<Button-1>", lambda e, n=b_node: self.jump_to_node(n))
                else:
                    target_box.insert("end", "\n")

            target_box.configure(state="disabled")
        except Exception as e:
            print(f"[SYNC ANALYSIS ERROR] {e}")