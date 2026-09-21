import threading
import duckdb
import chess.pgn
from core.chess_engine import ChessEngine
from core.constants import THEME


class CommentDBManager:
    """Embedded database manager handling DuckDB storage for candidate comments."""

    def __init__(self, db_path="catalog_comments.duckdb"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with duckdb.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS position_records (
                    position_id VARCHAR PRIMARY KEY,
                    fen VARCHAR NOT NULL
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candidate_moves (
                    move_id VARCHAR PRIMARY KEY,
                    position_id VARCHAR,
                    candidate_move VARCHAR,
                    depth INTEGER,
                    score_cp INTEGER
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS candidate_comments (
                    comment_id VARCHAR PRIMARY KEY,
                    position_id VARCHAR,
                    move_id VARCHAR,
                    comment_text TEXT NOT NULL
                );
            """)

    def save_comment(self, position_id, fen, move_id, candidate_move, comment_text):
        comment_id = f"{position_id}_{move_id}_{hash(comment_text)}"
        with duckdb.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO position_records (position_id, fen) 
                VALUES (?, ?)
            """, [position_id, fen])

            conn.execute("""
                INSERT OR REPLACE INTO candidate_moves (move_id, position_id, candidate_move) 
                VALUES (?, ?, ?)
            """, [move_id, position_id, candidate_move])

            conn.execute("""
                INSERT OR REPLACE INTO candidate_comments (comment_id, position_id, move_id, comment_text) 
                VALUES (?, ?, ?, ?)
            """, [comment_id, position_id, move_id, comment_text])

    def get_comment(self, move_id):
        with duckdb.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT comment_text FROM candidate_comments WHERE move_id = ?
            """, [move_id]).fetchone()
            return result[0] if result else ""


class EngineCandidateMixin:

    @property
    def db_manager(self):
        if not hasattr(self, "_db_manager"):
            self._db_manager = CommentDBManager()
        return self._db_manager

    def _init_analysis_tags(self):
        """Configures CustomTkinter/Tkinter text box tags using central THEME colors and vertical spacing."""
        if not hasattr(self, "analysis_textbox"):
            return

        # Map evaluation color tags
        self.analysis_textbox.tag_config("red", foreground=THEME["eval_red"], spacing3=6)
        self.analysis_textbox.tag_config("orange", foreground=THEME["eval_orange"], spacing3=6)
        self.analysis_textbox.tag_config("green", foreground=THEME["eval_green"], spacing3=6)
        self.analysis_textbox.tag_config("light_blue", foreground=THEME["eval_light_blue"], spacing3=6)

        # Default moves use text_primary (almost white) instead of muted secondary text
        self.analysis_textbox.tag_config("default", foreground=THEME["text_primary"], spacing3=6)

        # Style comment brackets / alternative variations using secondary theme text
        self.analysis_textbox.tag_config("comment_tag", foreground=THEME["text_secondary"], spacing3=6)

    def render_candidates_mode(self, game_node=None):
        """Clears the analysis box and populates it with candidate moves using color tags."""
        if not hasattr(self, "analysis_textbox"):
            return

        self.analysis_textbox.delete("1.0", "end")

        candidates_data = getattr(self, "current_candidates", [])

        if not candidates_data:
            self.analysis_textbox.insert("end", "[No candidate moves available]\n", "default")
            return

        for move_str, eval_type in candidates_data:
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
                recs = res.get('recs', [])
                top_alt_pv = res.get('top_alt_pv', [])

                filtered_candidates = [c for c in recs if c != played_san][:3]
                alts_str = ", ".join(filtered_candidates)
                rec_block = f" {{{alts_str}}}" if alts_str else ""

                if move_num not in temp_lines_data:
                    temp_lines_data[move_num] = {
                        "white_move": "", "white_alts": "", "white_tag": "default",
                        "black_move": "", "black_alts": "", "black_tag": "default",
                        "pv_text": ""
                    }

                if move_num <= 7:
                    if is_white:
                        temp_lines_data[move_num]["white_move"] = f"{move_num}. {played_san}"
                        temp_lines_data[move_num]["white_alts"] = rec_block
                        temp_lines_data[move_num]["white_tag"] = tag
                    else:
                        temp_lines_data[move_num]["black_move"] = f"{played_san}"
                        temp_lines_data[move_num]["black_alts"] = rec_block
                        temp_lines_data[move_num]["black_tag"] = tag
                else:
                    pv_str = " ".join(top_alt_pv) if top_alt_pv else ""
                    comment_parts = []
                    if alts_str:
                        comment_parts.append(alts_str)
                    if pv_str:
                        comment_parts.append(f"Line: {pv_str}")
                    detailed_block = f" {{ {' | '.join(comment_parts)} }}" if comment_parts else ""

                    if is_white:
                        temp_lines_data[move_num]["white_move"] = f"{move_num}. {played_san}"
                        temp_lines_data[move_num]["white_alts"] = detailed_block
                        temp_lines_data[move_num]["white_tag"] = tag
                    else:
                        temp_lines_data[move_num]["black_move"] = f"{move_num}... {played_san}"
                        temp_lines_data[move_num]["black_alts"] = detailed_block
                        temp_lines_data[move_num]["black_tag"] = tag

                def update_textbox_ui():
                    self.analysis_textbox.configure(state="normal")

                    # Ensure tags are bound properly inside the mixin
                    self._init_analysis_tags()

                    self.analysis_textbox.delete("1.0", "end")

                    for m_num in sorted(temp_lines_data.keys()):
                        entry = temp_lines_data[m_num]

                        if m_num <= 7:
                            w_move = entry["white_move"]
                            w_alts = entry["white_alts"]
                            w_tag = entry["white_tag"]

                            b_move = entry["black_move"]
                            b_alts = entry["black_alts"]
                            b_tag = entry["black_tag"]

                            if w_move:
                                self.analysis_textbox.insert("end", f"{w_move} ", (w_tag,))
                                if w_alts:
                                    self.analysis_textbox.insert("end", f"{w_alts} ", "comment_tag")

                            if b_move:
                                self.analysis_textbox.insert("end", f"{b_move} ", (b_tag,))
                                if b_alts:
                                    self.analysis_textbox.insert("end", f"{b_alts}", "comment_tag")

                            self.analysis_textbox.insert("end", "\n")

                            if m_num == 7:
                                self.analysis_textbox.insert("end", "\n")
                        else:
                            w_move = entry["white_move"]
                            w_alts = entry["white_alts"]
                            w_tag = entry["white_tag"]
                            if w_move:
                                self.analysis_textbox.insert("end", f"{w_move} ", (w_tag,))
                                if w_alts:
                                    self.analysis_textbox.insert("end", f"{w_alts}\n", "comment_tag")

                            b_move = entry["black_move"]
                            b_alts = entry["black_alts"]
                            b_tag = entry["black_tag"]
                            if b_move:
                                self.analysis_textbox.insert("end", f"    {b_move} ", (b_tag,))
                                if b_alts:
                                    self.analysis_textbox.insert("end", f"{b_alts}\n", "comment_tag")

                    self.analysis_textbox.configure(state="disabled")

                self.after(0, update_textbox_ui)

            engine_worker = ChessEngine()
            engine_worker.analyze_game(game_obj, mode="candidates", callback=stream_callback)

        threading.Thread(target=run_candidates_thread, args=(target_game,), daemon=True).start()