import threading
import chess.pgn
from core.chess_engine import ChessEngine


class EngineAnalysisMixin:
    def trigger_engine_mode(self, mode_name):
        self.active_engine_mode = mode_name

        self.btn_review.configure(fg_color="#1e293b")
        self.btn_candidates.configure(fg_color="#1e293b")
        self.btn_standard.configure(fg_color="#1e293b")

        if mode_name == "review":
            self.btn_review.configure(fg_color="#2e4a8c")
            self.candidates_container.pack_forget()
            self.review_container.pack(fill="both", expand=True)
            if self.active_game:
                self.start_game_review(self.active_game)
        elif mode_name == "candidates":
            self.btn_candidates.configure(fg_color="#2e4a8c")
            self.review_container.pack_forget()
            self.candidates_container.pack(fill="both", expand=True)
            if self.active_game:
                self.start_candidates_analysis(self.active_game)
        else:
            self.btn_standard.configure(fg_color="#2e4a8c")
            self.candidates_container.pack_forget()
            self.review_container.pack(fill="both", expand=True)
            if self.active_game:
                self.start_standard_analysis(self.active_game)

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

        # columns=None prevents hard 75-character line breaks, stopping weird gaps
        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
        pgn_text_export = game.accept(exporter)

        self.pgn_data_text.configure(state="normal")
        self.pgn_data_text.delete("1.0", "end")
        self.pgn_data_text.insert("end", pgn_text_export)
        self.pgn_data_text.configure(state="disabled")

        # Load plain game moves into analysis view immediately so navigation works
        self._load_plain_game_moves(game)

        self.candidates_textbox.configure(state="normal")
        self.candidates_textbox.delete("1.0", "end")
        self.candidates_textbox.configure(state="disabled")

    def _load_plain_game_moves(self, game):
        self.analysis_rows = {}
        temp_board = game.board()

        for i, move in enumerate(game.mainline_moves()):
            ply = i + 1
            move_num = (i // 2) + 1
            is_white = (i % 2 == 0)
            played_san = temp_board.san(move)
            temp_board.push(move)

            if move_num not in self.analysis_rows:
                self.analysis_rows[move_num] = {
                    "white": "", "black": "",
                    "white_tag": "default", "black_tag": "default"
                }

            if is_white:
                self.analysis_rows[move_num]["white"] = played_san
            else:
                self.analysis_rows[move_num]["black"] = played_san

        self._sync_analysis_selection()

    def start_game_review(self, target_game):
        self._run_analysis_worker(target_game, mode="review")

    def start_standard_analysis(self, target_game):
        self._run_analysis_worker(target_game, mode="standard")

    def _run_analysis_worker(self, target_game, mode="review"):
        self.analysis_rows = {}

        # Cancel any previous running thread if it exists
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

            def run(self):
                def stream_callback(res):
                    if self.cancel:
                        return  # Stop processing if cancelled

                    move_num = res['move_num']
                    is_white = res['is_white']
                    curr_eval = res['eval_after']

                    # For standard mode, append PV line if available
                    pv_line = res.get('pv_line', '')
                    eval_str = f" {curr_eval:+.1f}" if abs(curr_eval) >= 1.5 else ""
                    pv_str = f" [{pv_line}]" if pv_line and self.analysis_mode == "standard" else ""

                    move_display = f"{res['played_san']}{eval_str}{pv_str}"
                    tag = res.get('tag', 'default')

                    if move_num not in self.outer.analysis_rows:
                        self.outer.analysis_rows[move_num] = {
                            "white": "", "black": "",
                            "white_tag": "default", "black_tag": "default"
                        }

                    if is_white:
                        self.outer.analysis_rows[move_num]["white"] = move_display
                        self.outer.analysis_rows[move_num]["white_tag"] = tag
                    else:
                        self.outer.analysis_rows[move_num]["black"] = move_display
                        self.outer.analysis_rows[move_num]["black_tag"] = tag

                    self.outer.after(0, self.outer._sync_analysis_selection)

                engine_worker = ChessEngine()
                engine_worker.analyze_game(self.game_obj, mode=self.analysis_mode, callback=stream_callback)

        self._current_analysis_worker = WorkerThread(target_game, self, mode)
        self._current_analysis_worker.start()

    def start_candidates_analysis(self, target_game):
        def run_candidates_thread(game_obj):
            temp_lines_data = {}

            def stream_callback(res):
                move_num = res['move_num']
                is_white = res['is_white']
                played_san = res['played_san']
                tag = res.get('tag', 'default')
                base_eval = res.get('eval_after', 0.0)
                raw_alts = res.get('top_alternatives', res.get('recs', []))

                filtered_candidates = [
                    alt.get('san', alt) if isinstance(alt, dict) else alt
                    for alt in raw_alts
                    if not isinstance(alt, dict) or (base_eval - alt.get('eval', base_eval)) < 0.9
                ]
                filtered_candidates = [c for c in filtered_candidates if c != played_san][:3]
                alts_str = ", ".join(filtered_candidates)
                rec_block = f" {{{alts_str}}}" if alts_str else ""

                if move_num not in temp_lines_data:
                    temp_lines_data[num := move_num] = {
                        "white_text": "", "white_tag": "default",
                        "black_text": "", "black_tag": "default"
                    }

                if is_white:
                    temp_lines_data[move_num]["white_text"] = f"{move_num}. {played_san}{rec_block}"
                    temp_lines_data[move_num]["white_tag"] = tag
                else:
                    temp_lines_data[move_num]["black_text"] = f"{move_num}... {played_san}{rec_block}"
                    temp_lines_data[move_num]["black_tag"] = tag

                def update_textbox_ui():
                    self.candidates_textbox.configure(state="normal")
                    self.candidates_textbox.delete("1.0", "end")

                    for m_num in sorted(temp_lines_data.keys()):
                        entry = temp_lines_data[m_num]
                        w_txt = entry["white_text"]
                        w_tag = entry["white_tag"]
                        if w_txt:
                            self.candidates_textbox.insert("end", w_txt + "\n", (w_tag,))

                        b_txt = entry["black_text"]
                        b_tag = entry["black_tag"]
                        if b_txt:
                            self.candidates_textbox.insert("end", f"    {b_txt}\n", (b_tag,))

                self.after(0, update_textbox_ui)

            engine_worker = ChessEngine()
            engine_worker.analyze_game(game_obj, mode="candidates", callback=stream_callback)

        threading.Thread(target=run_candidates_thread, args=(target_game,), daemon=True).start()