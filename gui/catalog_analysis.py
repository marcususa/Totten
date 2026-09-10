import json
from pathlib import Path
import threading
import customtkinter as ctk
import chess
import chess.pgn
import gui.app_state as state

from core.constants import CONFIG_FILE, THEME
from core.chess_engine import ChessEngine
from gui.catalog_init_mixin import CatalogInitMixin
from gui.engine_mixins.engine_review_mixin import EngineReviewMixin
from gui.engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from gui.engine_mixins.engine_standard_mixin import EngineStandardMixin


class CatalogAnalysis(ctk.CTkFrame, CatalogInitMixin, EngineReviewMixin, EngineCandidateMixin, EngineStandardMixin):
    """
    Dedicated self-contained workspace controller for Catalog Analysis.
    Absorbs the complete layout grid, tree view navigation, board management, PGN state handling, and engine analysis modes.
    """

    def __init__(self, parent, filename=None, initial_games=None, *args, **kwargs):
        super().__init__(parent, fg_color=THEME["bg_panel"], corner_radius=0, *args, **kwargs)

        self.filename = filename or "personal_catalog.pgn"

        if not initial_games and hasattr(state, "catalog_state"):
            initial_games = state.catalog_state.get("active_games")

        self.game_list = list(initial_games) if initial_games else []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}

        self.active_game = None
        self.root_game_node = None
        self.current_node = None
        self.active_engine_mode = None
        self.analysis_rows = {}
        self._current_analysis_worker = None

        self.init_layout()
        self._inject_stop_analysis_button()
        self.load_catalog_data()
        self._bind_engine_buttons()
        self._bind_global_shortcuts()

        if hasattr(self, "board_widget") and self.board_widget:
            self.board_widget.on_step_back = self.on_prev_move
            self.board_widget.on_step_forward = self.on_next_move
            self.board_widget.on_jump_start = self.on_first_move
            self.board_widget.on_jump_end = self.on_last_move

        self.after(50, self.focus_force)

    def _inject_stop_analysis_button(self):
        """Adds a Stop Analysis button right next to the engine/review controls if it doesn't already exist."""
        try:
            if hasattr(self, "review_container") and self.review_container:
                if not hasattr(self, "btn_stop_analysis") or self.btn_stop_analysis is None:
                    self.btn_stop_analysis = ctk.CTkButton(
                        self.review_container,
                        text="Stop Analysis",
                        fg_color=THEME.get("btn_active", THEME["btn_hover"]),
                        hover_color=THEME["btn_hover"],
                        text_color=THEME["text_primary"],
                        border_width=1,
                        border_color=THEME.get("border_color", THEME["bg_surface"]),
                        command=self.stop_current_analysis
                    )
                    self.btn_stop_analysis.pack(side="top", pady=5, padx=5, fill="x")
        except Exception as e:
            print(f"[STOP BUTTON INJECTION ERROR] {e}")

    def stop_current_analysis(self):
        """Cancels any running Stockfish background analysis worker safely."""
        try:
            if hasattr(self, '_current_analysis_worker') and self._current_analysis_worker:
                self._current_analysis_worker.cancel = True
                self._current_analysis_worker = None
            print("[ENGINE WORKER] Analysis stopped by user.")
        except Exception as e:
            print(f"[STOP ANALYSIS ERROR] {e}")

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
        for btn_name in ("btn_review", "btn_review_mode"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    command=lambda: self.trigger_engine_mode("review"),
                    hover_color=THEME["btn_hover"]
                )

        for btn_name in ("btn_candidates", "btn_candidate_moves"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    command=lambda: self.trigger_engine_mode("candidates"),
                    hover_color=THEME["btn_hover"]
                )

        for btn_name in ("btn_standard", "btn_standard_mode", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    command=lambda: self.trigger_engine_mode("standard"),
                    hover_color=THEME["btn_hover"]
                )

    def write_analysis(self, text):
        self.update_engine_display(text)

    def write(self, text):
        self.update_engine_display(text)

    def append(self, text):
        self.update_engine_display(text)

    def _update_active_boards(self, board_obj):
        if hasattr(self, "board_widget") and self.board_widget and board_obj:
            try:
                self.board_widget.set_position_fen(board_obj.fen())
            except Exception:
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
        if hasattr(self, "load_game_hardwired"):
            return self.load_game_hardwired(game_node, category_source=category_source)
        return self.load_game_from_state(game_node, category_source=category_source)

    def load_catalog_data(self):
        if self.game_list:
            if hasattr(self, "pgn_tree"):
                active_game = None
                if hasattr(state, "catalog_state") and "active_index" in state.catalog_state:
                    idx = state.catalog_state.get("active_index", 0)
                    if 0 <= idx < len(self.game_list):
                        active_game = self.game_list[idx]

                self.populate_catalog_tree(self.game_list, active_game=active_game)

            if self.game_list:
                target_game = self.game_list[0]
                if hasattr(state, "catalog_state") and "active_index" in state.catalog_state:
                    idx = state.catalog_state.get("active_index", 0)
                    if 0 <= idx < len(self.game_list):
                        target_game = self.game_list[idx]
                self.load_game(target_game)
            return

        source_games = []
        catalog_path = self.filename

        if Path(catalog_path).exists():
            try:
                with open(catalog_path, "r", encoding="utf-8", errors="replace") as f:
                    while True:
                        g = chess.pgn.read_game(f)
                        if g is None:
                            break
                        source_games.append(g)
                self.game_list = source_games
                if hasattr(state, "all_games"):
                    state.all_games = source_games
            except Exception as e:
                print(f"[CATALOG ANALYSIS DEBUG] Error reading catalog file: {e}")

        if self.game_list and hasattr(self, "pgn_tree"):
            self.populate_catalog_tree(self.game_list)
            self.load_game(self.game_list[0])

    def populate_catalog_tree(self, games_to_display, active_game=None):
        if not hasattr(self, "pgn_tree") or not hasattr(self, "preview_lookup"):
            return

        self.pgn_tree.delete(*self.pgn_tree.get_children())
        self.preview_lookup.clear()

        if hasattr(self, "lbl_empty_state") and self.lbl_empty_state and games_to_display:
            try:
                self.lbl_empty_state.pack_forget()
            except Exception:
                pass

        target = active_game or (games_to_display[0] if games_to_display else None)

        for idx, g in enumerate(games_to_display, start=1):
            headers = g.headers
            white = headers.get("White", "Unknown")
            black = headers.get("Black", "Unknown")
            result = headers.get("Result", "*")

            item_id = self.pgn_tree.insert("", "end", values=(idx, white, black, result))
            self.preview_lookup[item_id] = g

            if target and g == target:
                self.pgn_tree.selection_set(item_id)
                self.pgn_tree.see(item_id)

        if target:
            self.load_game_from_state(target)
        self.after(50, self.focus_set)

    def load_games_by_eco(self, eco_code, active_game=None):
        if not eco_code:
            return

        eco_clean = str(eco_code).strip().upper()

        if not self.game_list and hasattr(state, "all_games") and state.all_games:
            self.game_list = state.all_games
        elif not self.game_list:
            self.load_catalog_data()

        eco_games = [
            g for g in self.game_list
            if hasattr(g, "headers") and g.headers.get("ECO", "").strip().upper() == eco_clean
        ]

        target_game = active_game or (eco_games[0] if eco_games else None)

        if eco_games:
            if hasattr(state, "active_category_source"):
                state.active_category_source = eco_games

        self.populate_catalog_tree(eco_games, active_game=target_game)

    def load_game_hardwired(self, game_node, category_source=None):
        if isinstance(category_source, list):
            self.game_list = category_source
            self.populate_catalog_tree(self.game_list, active_game=game_node)
        else:
            self.load_game_from_state(game_node)

    def on_hardwired_tree_select(self, game):
        self.load_game_from_state(game)

    def load_game_from_state(self, game_obj, category_source=None):
        if not game_obj:
            return

        self.current_game = game_obj
        self.board_node = game_obj
        self.active_game = game_obj
        self.root_game_node = game_obj
        self.current_node = game_obj

        if hasattr(self, "board_widget") and self.board_widget:
            try:
                fen_str = game_obj.board().fen()
                self.board_widget.set_position_fen(fen_str)
            except Exception:
                pass

        headers = game_obj.headers
        white = headers.get("White", "Unknown")
        black = headers.get("Black", "Unknown")
        result = headers.get("Result", "*")

        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
                pgn_text_export = game_obj.accept(exporter)

                self.pgn_data_text.configure(fg_color=THEME["bg_surface"])
                inner_pgn = getattr(self.pgn_data_text, "_textbox", getattr(self.pgn_data_text, "textbox", self.pgn_data_text))
                inner_pgn.configure(state="normal")
                inner_pgn.delete("1.0", "end")
                inner_pgn.insert("end", pgn_text_export)
                inner_pgn.configure(state="disabled")
            except Exception:
                pass

        if hasattr(self, "_load_plain_game_moves"):
            try:
                self._load_plain_game_moves(game_obj)
            except Exception:
                pass

        if self.active_engine_mode == "review":
            self.start_game_review(game_obj)

    def _load_plain_game_moves(self, game_obj):
        """Renders plain game moves into the Moves panel in correct order."""
        if not game_obj:
            return

        try:
            game = game_obj
            temp_board = game.board()

            if hasattr(self, "moves_textbox") and self.moves_textbox:
                box = self.moves_textbox
                box.configure(fg_color=THEME["bg_surface"])
                moves_box = getattr(box, "_textbox", getattr(box, "textbox", box))
                moves_box.configure(state="normal")
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
                    moves_box.tag_config(tag_name, foreground=THEME["text_primary"])

                    node = next_node

                moves_box.configure(state="disabled")

        except Exception as e:
            print(f"DEBUG: Error parsing game moves -> {e}")

    def update_active_move_highlight(self):
        if hasattr(self, "moves_textbox") and self.moves_textbox:
            try:
                box = self.moves_textbox
                box.configure(fg_color=THEME["bg_surface"])
                moves_box = getattr(box, "_textbox", getattr(box, "textbox", box))
                moves_box.configure(state="normal")
                moves_box.tag_remove("active_move", "1.0", "end")

                if self.board_node and self.board_node != self.current_game:
                    current_tag = str(id(self.board_node))
                    ranges = moves_box.tag_ranges(current_tag)
                    if ranges:
                        moves_box.tag_add("active_move", ranges[0], ranges[1])
                        moves_box.see(ranges[0])

                moves_box.configure(state="disabled")
            except Exception:
                pass

        if hasattr(self, "_sync_analysis_selection"):
            try:
                self._sync_analysis_selection()
            except Exception:
                pass

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
                    from core.chess_engine import ChessEngine
                    engine = ChessEngine()

                    def callback(res):
                        if self.cancel:
                            return
                        print(f"[RAW ENGINE WORKER] Received result callback: {res}")
                        eval_val = res.get('eval', 0.0)
                        current_depth = res.get('depth', 25)
                        eval_str = f"Eval: {eval_val:+.2f}"

                        pv_lines = res.get('pv_lines', [])
                        if isinstance(pv_lines, list) and pv_lines:
                            formatted_lines = [f"Depth {current_depth} | {eval_str}"]
                            for idx, line in enumerate(pv_lines, start=1):
                                formatted_lines.append(f"PV {idx}:\n{line}")
                            display_text = "\n\n".join(formatted_lines) + "\n"
                        else:
                            display_text = f"Depth {current_depth} | {eval_str} | PV: (none)\n"

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

        self.update_engine_display("[Engine idle. Click 'Engine' to start live analysis.]\n")

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

            target_box.tag_config("active_tracker", background=THEME["active_tracker_bg"], foreground=THEME["active_tracker_fg"])

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

    def on_prev_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.parent:
            self.board_node = self.board_node.parent
            self.current_node = self.board_node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            self.update_active_move_highlight()
        return "break"

    def on_next_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.variations:
            self.board_node = self.board_node.variation(0)
            self.current_node = self.board_node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            self.update_active_move_highlight()
        return "break"

    def on_first_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            self.board_node = self.current_game
            self.current_node = self.board_node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.current_game.board().fen())
            self.update_active_move_highlight()

    def on_last_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game
            while node.variations:
                node = node.variation(0)
            self.board_node = node
            self.current_node = self.board_node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(node.board().fen())
            self.update_active_move_highlight()

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self.board_widget, "flip_board"):
                self.board_widget.flip_board()
            elif hasattr(self.board_widget, "toggle_flip"):
                self.board_widget.toggle_flip()

    def trigger_engine_mode(self, mode):
        self.active_engine_mode = mode
        self._selected_mode_button = mode

        mode_buttons = {
            "review": ("btn_review", "btn_review_mode"),
            "candidates": ("btn_candidates", "btn_candidate_moves"),
            "standard": ("btn_standard", "btn_standard_mode", "btn_engines")
        }

        for m, btn_names in mode_buttons.items():
            is_active = (mode == m)
            for name in btn_names:
                btn = getattr(self, name, None)
                if btn is not None:
                    btn.configure(
                        fg_color=THEME["btn_hover"] if is_active else THEME["btn_initial"],
                        hover_color=THEME["btn_hover"],
                        text_color=THEME["text_primary"],
                    )

        if hasattr(self, "frame_review") and self.frame_review:
            self.frame_review.configure(border_width=0 if mode == "review" else 1)
        if hasattr(self, "frame_candidates") and self.frame_candidates:
            self.frame_candidates.configure(border_width=0 if mode == "candidates" else 1)
        if hasattr(self, "frame_standard") and self.frame_standard:
            self.frame_standard.configure(border_width=0 if mode == "standard" else 1)

        if mode == "review":
            EngineReviewMixin.trigger_engine_mode(self, "review")
        elif mode == "candidates":
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")

def create_workspace(master, initial_games=None, **kwargs):
    import gui.app_state as state_mod

    if initial_games is None:
        initial_games = (
                getattr(state_mod, "catalog_state", {}).get("active_games") or
                getattr(state_mod, "active_group_games", None) or
                getattr(state_mod, "active_search_results", None) or
                getattr(state_mod, "active_category_source", None)
        )

    active_index = getattr(state_mod, "catalog_state", {}).get("active_index", 0)

    focus = (
            getattr(state_mod, "catalog_state", {}).get("active_focus") or
            getattr(state_mod, "active_focus_game", None)
    )

    if initial_games and 0 <= active_index < len(initial_games):
        focus = initial_games[active_index]

    instance = CatalogAnalysis(master, filename="personal_catalog.pgn", initial_games=initial_games)

    if focus and hasattr(instance, "load_game"):
        instance.load_game(focus)
    elif initial_games and hasattr(instance, "load_game"):
        instance.load_game(initial_games[0])

    state_mod.workspace = instance
    return instance