import threading
import chess
import chess.engine
from core.chess_engine import ChessEngine
from core.constants import THEME
from ..engine_mixins.engine_review_mixin import EngineReviewMixin
from ..engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from ..engine_mixins.engine_standard_mixin import EngineStandardMixin


class CatalogEngineMixin(EngineReviewMixin, EngineCandidateMixin, EngineStandardMixin):
    """Manages background analysis workers, raw engine evaluation, and mode routing."""

    def on_piece_moved(self, move=None):
        """Triggers a full reset of the live raw engine analysis when pieces are moved."""
        print("[DEBUG] Piece moved detected. Resetting live engine analysis.")
        self.stop_raw_engine_analysis()
        self.clear_raw_engine_display()

    def clear_raw_engine_display(self):
        """Clears out the PV text display box."""
        self.update_engine_display("[No active position to evaluate.]\n")

    def update_engine_display(self, text):
        """Displays engine evaluation lines in the left panel textbox below the board with a smaller font."""
        target_box = None
        for attr_name in ("pv_textbox", "raw_engine_textbox", "engine_textbox", "left_textbox", "_cached_analysis_box"):
            box = getattr(self, attr_name, None)
            if box:
                target_box = box
                break

        if target_box:
            try:
                target_box.configure(fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))

                # Make font slightly smaller to accommodate all 5 lines cleanly
                try:
                    inner_box.configure(font=("Arial", 11))
                except Exception:
                    pass

                inner_box.configure(state="normal")
                inner_box.delete("1.0", "end")
                inner_box.insert("end", text)
                inner_box.configure(state="disabled")
            except Exception as e:
                print(f"[ENGINE DISPLAY ERROR] {e}")
        else:
            print(f"[ENGINE DISPLAY WARNING] No engine textbox found on UI! Text was:\n{text}")

    def toggle_engine_action(self):
        """Controls the independent Engine button with start/stop/pause depth-30 state management."""
        is_running = getattr(self, "_engine_running", False)
        pausing_state = getattr(self, "_engine_pausing_to_depth_30", False)
        worker = getattr(self, "_current_raw_engine_worker", None)

        if is_running and (worker is None or not worker.is_alive()):
            is_running = False
            self._engine_running = False
            self._engine_pausing_to_depth_30 = False

        print(f"[DEBUG] Engine button clicked! Synced state: running={is_running}, pausing={pausing_state}")

        if not is_running:
            # START STATE
            self._engine_running = True
            self._engine_pausing_to_depth_30 = False
            self.start_raw_engine_analysis()
        elif is_running and not pausing_state:
            # FIRST STOP PRESS: Gracefully pause updates until depth 30
            print("[DEBUG] Stop requested: Letting analysis continue smoothly up to depth 30...")
            self._engine_pausing_to_depth_30 = True
            if worker:
                worker.pausing_to_depth_30 = True
        else:
            # SECOND STOP PRESS: Reset completely right away
            print("[DEBUG] Second stop press: Resetting engine display completely.")
            self.stop_raw_engine_analysis()
            self.clear_raw_engine_display()

    def start_raw_engine_analysis(self):
        """Runs background worker for raw engine lines with MultiPV=5 and depth 30 limit using chess.engine."""
        print("[DEBUG] start_raw_engine_analysis triggered.")

        if not hasattr(self, "current_node") or self.current_node is None or isinstance(self.current_node, int):
            game_obj = getattr(self, "current_game", None) or getattr(self, "active_game", None)
            lists_to_check = ["game_list", "filtered_games", "current_games", "games"]
            if not game_obj:
                for lst_name in lists_to_check:
                    lst = getattr(self, lst_name, None)
                    if lst:
                        idx = self.current_node if isinstance(self.current_node, int) else 0
                        if 0 <= idx < len(lst):
                            game_obj = lst[idx]
                            break
            if game_obj:
                if hasattr(game_obj, "root"):
                    self.current_node = game_obj.root()
                elif hasattr(game_obj, "board"):
                    self.current_node = game_obj
                elif isinstance(game_obj, dict) and "game" in game_obj:
                    g = game_obj["game"]
                    self.current_node = g.root() if hasattr(g, "root") else g

        if not hasattr(self, "current_node") or self.current_node is None or isinstance(self.current_node, int):
            self.update_engine_display("[No active position to evaluate.]\n")
            return

        try:
            board_obj = self.current_node.board()
        except Exception as e:
            self.update_engine_display(f"[Error evaluating position: {e}]\n")
            return

        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True

        self._engine_running = True
        self._engine_pausing_to_depth_30 = False

        for btn_name in ("btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_hover"], text="Stop Engine")
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
                print("[RAW ENGINE WORKER] Starting thread analysis (MultiPV=5)...")
                engine = None
                try:
                    engine = chess.engine.SimpleEngine.popen_uci("stockfish")
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
                                    # Updated clean layout: No brackets, no vertical bars (|)
                                    formatted_lines.append(f"{idx}. Depth {d}  Eval: {e}  {moves_str}")

                                display_text = "\n\n".join(formatted_lines) + "\n"
                                self.outer.after(0, lambda dt=display_text: self.outer.update_engine_display(dt))

                            if current_depth >= 30 and self.pausing_to_depth_30:
                                print("[ENGINE] Reached max depth 30. Stopping engine updates.")
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

                        steps = move_num * 2 - (1 if is_white else 0)
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
                                comment_str = ""
                                self.white_streak = 0
                                self.black_streak = 0
                            elif 1.0 <= loss <= 2.5:
                                tag_to_apply = "orange"
                                eval_str = f" {{{curr_eval:+.2f}}}"
                                comment_str = ""
                                self.white_streak = 0
                                self.black_streak = 0
                            elif 0.3 <= loss < 1.0:
                                comment_str = ""
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
        """Renders the analysis panel completely like a continuous book."""
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

        _apply_styles()
        self.after_idle(_apply_styles)

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

        if mode == "review":
            EngineReviewMixin.trigger_engine_mode(self, "review")
        elif mode == "candidates":
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")