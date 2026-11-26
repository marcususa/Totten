import threading
import chess
from core.chess_engine import ChessEngine, classify_move_evaluation
from core.constants import THEME
from ..engine_mixins.engine_review_mixin import EngineReviewMixin
from ..engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from ..engine_mixins.engine_standard_mixin import EngineStandardMixin


class CatalogEngineMixin(EngineReviewMixin, EngineCandidateMixin, EngineStandardMixin):
    """
    Manages background analysis workers, live raw engine evaluation,
    visual PV formatting, and mode routing for Catalog Analysis.
    All engine evaluations and metadata remain strictly in memory for the session.
    """

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

    def _resolve_current_board(self):
        if not hasattr(self, "current_node") or self.current_node is None or isinstance(self.current_node, int):
            game_obj = getattr(self, "current_game", None) or getattr(self, "active_game", None)
            lists_to_check = ("game_list", "filtered_games", "current_games", "games")
            if not game_obj:
                for lst_name in lists_to_check:
                    lst = getattr(self, lst_name, None)
                    if lst:
                        idx = self.current_node if isinstance(self.current_node, int) else 0
                        if 0 <= idx < len(lst):
                            game_obj = lst[idx]
                            break

            if game_obj:
                if hasattr(game_obj, "root") and callable(game_obj.root):
                    self.current_node = game_obj.root()
                elif hasattr(game_obj, "board") and callable(game_obj.board):
                    self.current_node = game_obj
                elif isinstance(game_obj, dict) and "game" in game_obj:
                    g = game_obj["game"]
                    self.current_node = g.root() if hasattr(g, "root") and callable(g.root) else g

        if not hasattr(self, "current_node") or self.current_node is None or isinstance(self.current_node, int):
            return None

        if hasattr(self.current_node, "board") and callable(self.current_node.board):
            return self.current_node.board()
        if isinstance(self.current_node, chess.Board):
            return self.current_node.copy()
        return None

    def notify_live_engine_position_changed(self):
        """
        Called whenever the board position changes while live raw engine analysis is active.
        Debounces rapid navigation clicks so the engine shifts gears cleanly without stuttering.
        """
        if not getattr(self, "_engine_running", False):
            return

        self._raw_engine_gen = getattr(self, "_raw_engine_gen", 0) + 1
        pending_after = getattr(self, "_raw_engine_debounce_id", None)
        if pending_after and hasattr(self, "after_cancel"):
            try:
                self.after_cancel(pending_after)
            except Exception:
                pass

        prev_worker = getattr(self, "_current_raw_engine_worker", None)
        if prev_worker:
            prev_worker.cancel = True
            if getattr(prev_worker, "engine_client", None):
                try:
                    prev_worker.engine_client.stop_active_engine()
                except Exception:
                    pass

        if hasattr(self, "after"):
            self._raw_engine_debounce_id = self.after(90, self.start_raw_engine_analysis)
        else:
            self.start_raw_engine_analysis()

    def toggle_engine_action(self):
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
        self._raw_engine_debounce_id = None
        board_obj = self._resolve_current_board()
        if board_obj is None:
            self.update_engine_display("No active position to evaluate.\n")
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
        for btn_name in ("btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_hover"], text="Stop Engine")
                except Exception:
                    pass

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
                    engine = ChessEngine()
                    self.engine_client = engine

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

                    engine.analyze_position(
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
                self.outer.update_engine_display("", structured_lines=structured)

        worker = RawEngineWorker(board_obj, self, current_gen)
        self._current_raw_engine_worker = worker
        worker.start()

    def stop_raw_engine_analysis(self):
        self._raw_engine_gen = getattr(self, "_raw_engine_gen", 0) + 1
        pending_after = getattr(self, "_raw_engine_debounce_id", None)
        if pending_after and hasattr(self, "after_cancel"):
            try:
                self.after_cancel(pending_after)
            except Exception:
                pass
        self._raw_engine_debounce_id = None

        worker = getattr(self, "_current_raw_engine_worker", None)
        if worker:
            worker.cancel = True
            if getattr(worker, "engine_client", None):
                try:
                    worker.engine_client.stop_active_engine()
                except Exception:
                    pass
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

        prev_worker = getattr(self, "_current_analysis_worker", None)
        if prev_worker:
            prev_worker.cancel = True
            if getattr(prev_worker, "engine_client", None):
                try:
                    prev_worker.engine_client.stop_active_engine()
                except Exception:
                    pass

        class WorkerThread(threading.Thread):
            def __init__(self, game_obj, outer, analysis_mode):
                super().__init__()
                self.game_obj = game_obj
                self.outer = outer
                self.analysis_mode = analysis_mode
                self.cancel = False
                self.daemon = True
                self.engine_client = None
                self.white_streak = 0
                self.black_streak = 0
                self.last_eval = 0.0

            def run(self):
                def stream_callback(res):
                    if self.cancel:
                        return

                    try:
                        move_num = res["move_num"]
                        is_white = res["is_white"]
                        curr_eval = res.get("eval_after", 0.0)
                        played_san = res["played_san"]
                        board_before_mv = res.get("board")

                        steps = move_num * 2 - 1 if is_white else move_num * 2
                        curr_n = self.game_obj
                        parent_n = self.game_obj
                        for _ in range(steps):
                            if curr_n.variations:
                                parent_n = curr_n
                                curr_n = curr_n.variation(0)

                        b_before = board_before_mv if board_before_mv is None else parent_n.board()
                        mv_obj = curr_n.move if getattr(curr_n, "move", None) else None

                        tag_to_apply, self.white_streak, self.black_streak, _ = classify_move_evaluation(
                            move_num=move_num,
                            is_white=is_white,
                            eval_before=self.last_eval,
                            eval_after=curr_eval,
                            white_streak=self.white_streak,
                            black_streak=self.black_streak,
                            board_before=b_before,
                            move=mv_obj,
                        )
                        self.last_eval = curr_eval

                        if move_num < 8 or tag_to_apply == "default":
                            move_display = played_san
                        else:
                            move_display = f"{played_san} {{{curr_eval:+.2f}}}"

                        if move_num not in self.outer.analysis_rows:
                            self.outer.analysis_rows[move_num] = {
                                "white": "", "black": "",
                                "white_tag": "default", "black_tag": "default",
                                "white_node": None, "black_node": None,
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
                    self.engine_client = engine_worker
                    engine_worker.analyze_game(
                        self.game_obj,
                        mode=self.analysis_mode,
                        callback=stream_callback,
                        worker_ref=self,
                    )
                except Exception as e:
                    if not self.cancel:
                        print(f"[ENGINE WORKER CRASH] Mode {self.analysis_mode} failed: {e}")

        self._current_analysis_worker = WorkerThread(target_game, self, mode)
        self._current_analysis_worker.start()

    def _sync_analysis_selection(self):
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return

        box = self.analysis_textbox
        box.configure(fg_color=THEME["bg_surface"])
        target_box = getattr(box, "_textbox", getattr(box, "textbox", box))

        active_node = (
            getattr(self, "board_node", None)
            or getattr(self, "current_node", None)
        )

        try:
            target_box.configure(state="normal")
            target_box.delete("1.0", "end")

            eval_tag_colors = {
                "red": THEME["eval_red"],
                "orange": THEME["eval_orange"],
                "green": THEME["eval_green"],
                "light_blue": THEME["eval_light_blue"],
                "default": THEME["eval_default"],
            }

            for tag_name, color in eval_tag_colors.items():
                target_box.tag_config(tag_name, foreground=color)

            target_box.tag_config(
                "comment_tag",
                foreground=THEME.get("text_secondary", THEME["eval_default"]),
            )
            target_box.tag_config(
                "active_tracker",
                background=THEME["active_tracker_bg"],
                foreground=THEME["active_tracker_fg"],
            )

            rows = getattr(self, "analysis_rows", {}) or {}
            for move_num in sorted(rows.keys()):
                row = rows[move_num]
                target_box.insert("end", f"{move_num}. ")

                w_text = row.get("white", "")
                w_tag = row.get("white_tag", "default")
                w_node = row.get("white_node")
                w_alts = row.get("white_alts", "")

                if w_text:
                    w_tag_name = f"w_{move_num}_{id(w_node)}" if w_node else f"w_{move_num}"
                    base_w_tag = w_tag if w_tag in eval_tag_colors else "default"
                    is_active_white = (active_node is not None and w_node is not None and active_node == w_node)
                    tags = [base_w_tag, w_tag_name]
                    if is_active_white:
                        tags.append("active_tracker")
                    target_box.insert("end", f"{w_text} ", tuple(tags))
                    if w_node:
                        target_box.tag_bind(w_tag_name, "<Button-1>", lambda e, n=w_node: self.jump_to_node(n))
                else:
                    target_box.insert("end", "... ")

                if w_alts:
                    target_box.insert("end", f"{w_alts} ", ("comment_tag",))

                b_text = row.get("black", "")
                b_tag = row.get("black_tag", "default")
                b_node = row.get("black_node")
                b_alts = row.get("black_alts", "")

                if b_text:
                    b_tag_name = f"b_{move_num}_{id(b_node)}" if b_node else f"b_{move_num}"
                    base_b_tag = b_tag if b_tag in eval_tag_colors else "default"
                    is_active_black = (active_node is not None and b_node is not None and active_node == b_node)
                    tags = [base_b_tag, b_tag_name]
                    if is_active_black:
                        tags.append("active_tracker")
                    target_box.insert("end", f"{b_text} ", tuple(tags))
                    if b_node:
                        target_box.tag_bind(b_tag_name, "<Button-1>", lambda e, n=b_node: self.jump_to_node(n))

                if b_alts:
                    target_box.insert("end", f"{b_alts} ", ("comment_tag",))

                target_box.insert("end", " ")

            if active_node:
                for tag in target_box.tag_names():
                    if tag.endswith(f"_{id(active_node)}") or tag == f"node_{id(active_node)}":
                        ranges = target_box.tag_ranges(tag)
                        if ranges:
                            target_box.tag_add("active_tracker", ranges[0], ranges[1])
                            target_box.see(ranges[0])
                            break
        finally:
            try:
                target_box.configure(state="disabled")
            except Exception:
                pass

    def trigger_engine_mode(self, mode):
        self.active_engine_mode = mode
        self._selected_mode_button = mode

        mode_buttons = {
            "review": ("btn_review", "btn_review_mode"),
            "candidates": ("btn_candidates", "btn_candidate_moves"),
            "standard": ("btn_standard", "btn_standard_mode", "btn_engines"),
        }

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

        for frame_attr, m_key in (
            ("frame_review", "review"),
            ("frame_candidates", "candidates"),
            ("frame_standard", "standard"),
        ):
            frm = getattr(self, frame_attr, None)
            if frm:
                try:
                    frm.configure(border_width=0 if mode == m_key else 1)
                except Exception:
                    pass

        if mode == "review":
            EngineReviewMixin.trigger_engine_mode(self, "review")
        elif mode == "candidates":
            if getattr(self, "_engine_running", False) and hasattr(self, "stop_raw_engine_analysis"):
                self.stop_raw_engine_analysis()
            self.update_engine_display("")
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")