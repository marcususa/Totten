import threading
import chess.pgn
from core.chess_engine import ChessEngine


class EngineCandidateMixin:

    def render_candidates_mode(self, game_node=None):
        """Clears the analysis box and populates it with candidate moves using color tags."""
        if not hasattr(self, "analysis_textbox"):
            return

        self.analysis_textbox.delete("1.0", "end")

        # Pull or calculate your candidate lines/evaluations here
        # Example structure of adding colored text:
        candidates_data = getattr(self, "current_candidates", [])

        if not candidates_data:
            self.analysis_textbox.insert("end", "[No candidate moves available]\n", "default")
            return

        for move_str, eval_type in candidates_data:
            # Map eval_type or score to your configured tags ("green", "orange", "red", etc.)
            tag = self._get_candidate_tag(eval_type)
            self.analysis_textbox.insert("end", f"{move_str}\n", tag)

    def _get_candidate_tag(self, eval_type):
        """Helper to map evaluation types to text tags."""
        if eval_type == "best":
            return "green"
        elif eval_type == "good":
            return "light_blue"
        elif eval_type == "inaccuracy":
            return "orange"
        elif eval_type in ("mistake", "blunder"):
            return "red"
        return "default"

    def trigger_engine_mode(self, mode_name):
        self.active_engine_mode = mode_name

        if hasattr(self, "btn_candidates") and self.btn_candidates:
            self.btn_candidates.configure(fg_color="#2e4a8c")
        if hasattr(self, "review_container"):
            self.review_container.pack_forget()
        if hasattr(self, "candidates_container"):
            self.candidates_container.pack(fill="both", expand=True)
        if self.active_game:
            self.start_candidates_analysis(self.active_game)

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

        if hasattr(self, "analysis_textbox"):
            self.analysis_textbox.configure(state="normal")
            self.analysis_textbox.delete("1.0", "end")
            self.analysis_textbox.configure(state="disabled")

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
                    temp_lines_data[move_num] = {
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
                    self.analysis_textbox.configure(state="normal")
                    self.analysis_textbox.delete("1.0", "end")

                    for m_num in sorted(temp_lines_data.keys()):
                        entry = temp_lines_data[m_num]
                        w_txt = entry["white_text"]
                        w_tag = entry["white_tag"]
                        if w_txt:
                            self.analysis_textbox.insert("end", w_txt + "\n", (w_tag,))

                        b_txt = entry["black_text"]
                        b_tag = entry["black_tag"]
                        if b_txt:
                            self.analysis_textbox.insert("end", f"    {b_txt}\n", (b_tag,))

                self.after(0, update_textbox_ui)

            engine_worker = ChessEngine()
            engine_worker.analyze_game(game_obj, mode="candidates", callback=stream_callback)

        threading.Thread(target=run_candidates_thread, args=(target_game,), daemon=True).start()