import threading
import chess.pgn
from core.chess_engine import ChessEngine


class EngineStandardMixin:
    def trigger_engine_mode(self, mode_name):
        self.active_engine_mode = mode_name

        if hasattr(self, "btn_standard") and self.btn_standard:
            self.btn_standard.configure(fg_color="#2e4a8c")
        if hasattr(self, "candidates_container"):
            self.candidates_container.pack_forget()
        if hasattr(self, "review_container"):
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

        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
        pgn_text_export = game.accept(exporter)

        self.pgn_data_text.configure(state="normal")
        self.pgn_data_text.delete("1.0", "end")
        self.pgn_data_text.insert("end", pgn_text_export)
        self.pgn_data_text.configure(state="disabled")

        self._load_plain_game_moves(game)

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

    def start_standard_analysis(self, target_game):
        self._run_analysis_worker(target_game, mode="standard")

    def _run_analysis_worker(self, target_game, mode="standard"):
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

            def run(self):
                def stream_callback(res):
                    if self.cancel:
                        return

                    move_num = res['move_num']
                    is_white = res['is_white']
                    curr_eval = res['eval_after']

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