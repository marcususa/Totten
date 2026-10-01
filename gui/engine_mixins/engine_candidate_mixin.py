import sys
import threading
import traceback
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
        """Configures CustomTkinter/Tkinter text box tags using central THEME colors, vertical spacing, and wrapping."""
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return

        box = self.analysis_textbox
        target_box = getattr(box, "_textbox", getattr(box, "textbox", box))

        try:
            target_box.configure(wrap="word")
        except Exception:
            pass

        text_primary = THEME.get("text_primary", "#ffffff")
        text_secondary = THEME.get("text_secondary", "#aaaaaa")
        eval_red = THEME.get("eval_red", "#ff6b6b")
        eval_orange = THEME.get("eval_orange", "#ffa94d")
        eval_green = THEME.get("eval_green", "#51cf66")
        eval_light_blue = THEME.get("eval_light_blue", "#33afdc")
        tracker_bg = THEME.get("active_tracker_bg", "#2b3a55")
        tracker_fg = THEME.get("active_tracker_fg", "#ffffff")

        target_box.tag_config("red", foreground=eval_red, spacing3=4)
        target_box.tag_config("orange", foreground=eval_orange, spacing3=4)
        target_box.tag_config("green", foreground=eval_green, spacing3=4)
        target_box.tag_config("light_blue", foreground=eval_light_blue, spacing3=4)
        target_box.tag_config("default", foreground=text_primary, spacing3=4)
        target_box.tag_config("comment_tag", foreground=text_secondary, spacing3=4)
        target_box.tag_config("active_tracker", background=tracker_bg, foreground=tracker_fg)

    def render_candidates_mode(self, game_node=None):
        """Renders candidate moves from the cached data structure without re-triggering analysis."""
        self._sync_candidate_selection()

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
            try:
                self.btn_candidates.configure(fg_color="#2e4a8c")
            except Exception:
                pass

        if hasattr(self, "review_container"):
            try:
                self.review_container.pack_forget()
            except Exception:
                try:
                    self.review_container.grid_forget()
                except Exception:
                    pass

        shown = False
        for c_name in ["candidates_container", "candidates_frame", "engine_container", "analysis_container",
                       "analysis_frame"]:
            if hasattr(self, c_name):
                try:
                    container = getattr(self, c_name)
                    try:
                        manager = container.winfo_manager()
                    except Exception:
                        manager = ""

                    if manager == "grid":
                        container.grid(sticky="nsew")
                    else:
                        container.pack(fill="both", expand=True)
                    shown = True
                    print(f"[UI DEBUG] Successfully displayed container: {c_name} (via {manager or 'pack'})")
                    sys.stdout.flush()
                except Exception as e:
                    print(f"[UI DEBUG] Could not display {c_name}: {e}")
                    sys.stdout.flush()

        if not shown and hasattr(self, "analysis_textbox") and self.analysis_textbox:
            try:
                parent = getattr(self.analysis_textbox, "master", None)
                if parent:
                    try:
                        p_manager = parent.winfo_manager()
                    except Exception:
                        p_manager = ""
                    if p_manager == "grid":
                        parent.grid(sticky="nsew")
                    else:
                        parent.pack(fill="both", expand=True)
                    shown = True
                    print(f"[UI DEBUG] Displayed analysis_textbox master widget.")
                    sys.stdout.flush()
            except Exception as e:
                print(f"[UI DEBUG] Could not display analysis_textbox parent: {e}")
                sys.stdout.flush()

        if hasattr(self, "active_game") and self.active_game:
            self._active_chunk_start = 1
            self._active_chunk_end = 15
            self.start_candidates_analysis(self.active_game, start_move=1, max_chunk=15)

    def trigger_engine_chunk(self, chunk_size):
        """Handles chunk buttons (+10, +20, +30) continuing from the last evaluated chunk end."""
        if hasattr(self, "btn_candidates") and self.btn_candidates:
            try:
                self.btn_candidates.configure(fg_color="#1f538d")
            except Exception:
                pass

        start_move = getattr(self, "_active_chunk_end", 0) + 1
        if start_move <= 1 or not hasattr(self, "candidate_rows") or not self.candidate_rows:
            start_move = 1

        end_move = start_move + chunk_size - 1
        self._active_chunk_start = start_move
        self._active_chunk_end = end_move

        if hasattr(self, "active_game") and self.active_game:
            print(f"[CHUNK BUTTON] Triggering analysis for range {start_move}-{end_move}...")
            sys.stdout.flush()
            self.start_candidates_analysis(self.active_game, start_move=start_move, max_chunk=chunk_size)

    def load_candidate_extension(self, chunk_size):
        """Alias expected by catalog_init_mixin.py buttons to extend analysis chunks."""
        self.trigger_engine_chunk(chunk_size)

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

        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            self.pgn_data_text.configure(state="normal")
            self.pgn_data_text.delete("1.0", "end")
            self.pgn_data_text.insert("end", pgn_text_export)
            self.pgn_data_text.configure(state="disabled")

        self._load_plain_game_moves(game)
        self._active_chunk_start = 1
        self._active_chunk_end = 15
        self.start_candidates_analysis(game, start_move=1, max_chunk=15)

    def _load_plain_game_moves(self, game):
        self.candidate_rows = {}
        self._full_game_move_count = 0

        for node in game.mainline():
            ply = 0
            curr = node
            while curr.parent:
                ply += 1
                curr = curr.parent

            i = ply - 1
            move_num = (i // 2) + 1
            is_white = (i % 2 == 0)
            self._full_game_move_count = max(self._full_game_move_count, move_num)

            parent_board = node.parent.board() if node.parent else game.board()
            played_san = parent_board.san(node.move)

            if move_num not in self.candidate_rows:
                self.candidate_rows[move_num] = {
                    "white_move": "", "white_alts": "", "white_tag": "default", "white_node": None,
                    "black_move": "", "black_alts": "", "black_tag": "default", "black_node": None
                }

            if is_white:
                self.candidate_rows[move_num]["white_move"] = f"{move_num}. {played_san}"
                self.candidate_rows[move_num]["white_node"] = node
            else:
                self.candidate_rows[move_num]["black_move"] = f"{played_san}"
                self.candidate_rows[move_num]["black_node"] = node

        print(f"[LOAD PLAIN] Loaded {len(self.candidate_rows)} base move rows.")
        sys.stdout.flush()
        self._sync_candidate_selection()

    def start_candidates_analysis(self, target_game=None, start_move=1, max_chunk=15):
        if not target_game:
            if hasattr(self, "active_game") and self.active_game:
                target_game = self.active_game
            elif hasattr(self, "root_game_node") and self.root_game_node:
                target_game = self.root_game_node
            elif hasattr(self, "preview_lookup") and self.preview_lookup:
                first_item = next(iter(self.preview_lookup.keys()), None)
                if first_item:
                    target_game = self.preview_lookup.get(first_item)

        if not target_game:
            print(f"[CANDIDATE ERROR] No active game available to analyze. Please select a game from the list first.")
            sys.stdout.flush()
            return

        if not hasattr(self, "candidate_rows") or not self.candidate_rows:
            self._load_plain_game_moves(target_game)

        if not hasattr(self, "_candidate_lock"):
            self._candidate_lock = threading.Lock()

        with self._candidate_lock:
            if hasattr(self, '_current_candidate_worker') and self._current_candidate_worker:
                if self._current_candidate_worker.is_alive():
                    self._current_candidate_worker.cancel = True
                    try:
                        self._current_candidate_worker.join(timeout=0.05)
                    except Exception:
                        pass

        end_move = min(start_move + max_chunk - 1, getattr(self, "_full_game_move_count", 200))
        print(f"[CANDIDATE CHUNK] Starting evaluation for moves {start_move} to {end_move}...")
        sys.stdout.flush()

        class ChunkedCandidateWorker(threading.Thread):
            def __init__(self, game_obj, outer, s_move, e_move):
                super().__init__()
                self.game_obj = game_obj
                self.outer = outer
                self.start_m = s_move
                self.end_m = e_move
                self.cancel = False
                self.daemon = True

            def run(self):
                def stream_callback(res):
                    if self.cancel:
                        return

                    try:
                        move_num = res['move_num']
                        print(
                            f"[STREAM CALLBACK] Received move_num={move_num}, is_white={res.get('is_white')}, eval_diff={res.get('eval_diff')}")
                        sys.stdout.flush()

                        if not (self.start_m <= move_num <= self.end_m):
                            return

                        is_white = res['is_white']
                        played_san = res['played_san']
                        tag = res.get('tag', 'default')
                        recs = res.get('recs', [])
                        top_alt_pv = res.get('top_alt_pv', [])
                        node_obj = res.get('node')

                        eval_diff = res.get('eval_diff', res.get('diff', res.get('score_diff', 0.0)))
                        if abs(eval_diff) > 10:
                            eval_diff = eval_diff / 100.0
                        if eval_diff > 0:
                            eval_diff = -eval_diff

                        filtered_candidates = []
                        if move_num <= 7:
                            if eval_diff <= -3.0:
                                filtered_candidates = [c for c in recs if c != played_san][:3]
                            elif eval_diff <= -1.0:
                                filtered_candidates = [c for c in recs if c != played_san][:1]
                        elif 8 <= move_num <= 15:
                            if eval_diff <= -3.0:
                                filtered_candidates = [c for c in recs if c != played_san][:3]
                            elif eval_diff <= -0.6:
                                filtered_candidates = [c for c in recs if c != played_san][:1]
                        else:
                            if eval_diff <= -3.0:
                                filtered_candidates = [c for c in recs if c != played_san][:3]
                            elif eval_diff <= -0.4:
                                filtered_candidates = [c for c in recs if c != played_san][:2]
                            else:
                                filtered_candidates = [c for c in recs if c != played_san][:1]

                        alts_str = ", ".join(filtered_candidates)
                        rec_block = f" {{{alts_str}}}" if alts_str else ""

                        if not hasattr(self.outer, "candidate_rows") or self.outer.candidate_rows is None:
                            self.outer.candidate_rows = {}

                        if move_num not in self.outer.candidate_rows:
                            self.outer.candidate_rows[move_num] = {
                                "white_move": "", "white_alts": "", "white_tag": "default", "white_node": None,
                                "black_move": "", "black_alts": "", "black_tag": "default", "black_node": None
                            }

                        if is_white and not self.outer.candidate_rows[move_num]["white_move"]:
                            self.outer.candidate_rows[move_num]["white_move"] = f"{move_num}. {played_san}"
                            self.outer.candidate_rows[move_num]["white_node"] = node_obj
                        elif not is_white and not self.outer.candidate_rows[move_num]["black_move"]:
                            self.outer.candidate_rows[move_num]["black_move"] = f"{played_san}"
                            self.outer.candidate_rows[move_num]["black_node"] = node_obj

                        if move_num <= 7:
                            detailed_block = rec_block
                        else:
                            pv_str = " ".join(top_alt_pv) if (top_alt_pv and eval_diff <= -2.5) else ""
                            comment_parts = []
                            if alts_str:
                                comment_parts.append(alts_str)
                            if pv_str:
                                comment_parts.append(f"Line: {pv_str}")
                            detailed_block = f" {{ {' | '.join(comment_parts)} }}" if comment_parts else ""

                        if is_white:
                            self.outer.candidate_rows[move_num]["white_alts"] = detailed_block
                            self.outer.candidate_rows[move_num]["white_tag"] = tag
                        else:
                            self.outer.candidate_rows[move_num]["black_alts"] = detailed_block
                            self.outer.candidate_rows[move_num]["black_tag"] = tag

                        print(f"[STREAM CALLBACK] Scheduling UI sync for move {move_num}...")
                        sys.stdout.flush()
                        self.outer.after(0, self.outer._sync_candidate_selection)

                    except Exception as ex:
                        print(f"[CANDIDATE STREAM ERROR] {ex}")
                        sys.stdout.flush()
                        traceback.print_exc()

                try:
                    print(f"[CANDIDATE WORKER] Instantiating ChessEngine...")
                    sys.stdout.flush()
                    engine_worker = ChessEngine()
                    print(f"[CANDIDATE WORKER] Calling analyze_game for range {self.start_m}-{self.end_m}...")
                    sys.stdout.flush()

                    engine_worker.analyze_game(
                        self.game_obj,
                        mode="candidates",
                        callback=stream_callback,
                        start_move=self.start_m,
                        end_move=self.end_m
                    )
                    print(f"[CANDIDATE WORKER] analyze_game execution completed.")
                    sys.stdout.flush()

                except Exception as e:
                    print(f"[CANDIDATE WORKER CRASH]: {e}")
                    sys.stdout.flush()
                    traceback.print_exc()

        self._current_candidate_worker = ChunkedCandidateWorker(target_game, self, start_move, end_move)
        self._current_candidate_worker.start()

    def jump_to_node(self, node):
        """Handles node jumps and triggers the next evaluation chunk if navigating past the current window."""
        self.current_node = node
        self._update_active_boards(node.board())

        ply = 0
        curr = node
        while curr.parent:
            ply += 1
            curr = curr.parent
        move_num = (ply + 1) // 2

        current_max_chunk = getattr(self, "_active_chunk_end", 15)
        if move_num > current_max_chunk and hasattr(self, "active_game") and self.active_game:
            next_start = current_max_chunk + 1
            self._active_chunk_end = next_start + 9
            self.start_candidates_analysis(self.active_game, start_move=next_start, max_chunk=10)

        self._sync_candidate_selection()

    def _sync_candidate_selection(self):
        """Redraws the candidate analysis textbox flowing continuously like a book from left to right."""
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            print(f"[SYNC WARNING] analysis_textbox attribute missing!")
            sys.stdout.flush()
            return

        box = self.analysis_textbox

        try:
            if not box.winfo_ismapped():
                manager = ""
                try:
                    manager = box.master.winfo_manager()
                except Exception:
                    pass

                if manager == "grid":
                    box.grid(sticky="nsew")
                else:
                    box.pack(fill="both", expand=True)
        except Exception as e:
            print(f"[SYNC LAYOUT WARNING] Could not auto-map analysis_textbox: {e}")
            sys.stdout.flush()

        try:
            box.configure(fg_color=THEME.get("bg_surface", "#1e1e1e"))
        except Exception:
            pass

        target_box = getattr(box, "_textbox", getattr(box, "textbox", box))

        try:
            target_box.configure(state="normal")
            self._init_analysis_tags()
            target_box.delete("1.0", "end")

            if not hasattr(self, "candidate_rows") or not self.candidate_rows:
                target_box.insert("end", "[No candidate moves available]\n", "default")
                target_box.configure(state="disabled")
                print("[SYNC] Inserted fallback: No candidate moves available")
                sys.stdout.flush()
                return

            inserted_chars = 0
            sorted_moves = sorted(self.candidate_rows.keys())
            for m_num in sorted_moves:
                entry = self.candidate_rows[m_num]

                w_move = entry.get("white_move", "")
                w_alts = entry.get("white_alts", "")
                w_tag = entry.get("white_tag", "default")
                w_node = entry.get("white_node")

                b_move = entry.get("black_move", "")
                b_alts = entry.get("black_alts", "")
                b_tag = entry.get("black_tag", "default")
                b_node = entry.get("black_node")

                if w_move:
                    is_active_w = (hasattr(self, "current_node") and self.current_node == w_node)
                    tag_w = "active_tracker" if is_active_w else w_tag
                    w_tag_name = f"cw_{m_num}_{id(w_node)}" if w_node else f"cw_{m_num}"

                    target_box.insert("end", f"{w_move} ", (tag_w, w_tag_name))
                    inserted_chars += len(w_move) + 1

                    if w_node:
                        target_box.tag_bind(w_tag_name, "<Button-1>", lambda e, n=w_node: self.jump_to_node(n))
                    if w_alts:
                        target_box.insert("end", f"{w_alts} ", "comment_tag")
                        inserted_chars += len(w_alts) + 1

                if b_move:
                    is_active_b = (hasattr(self, "current_node") and self.current_node == b_node)
                    tag_b = "active_tracker" if is_active_b else b_tag
                    b_tag_name = f"cb_{m_num}_{id(b_node)}" if b_node else f"cb_{m_num}"

                    target_box.insert("end", f"{b_move} ", (tag_b, b_tag_name))
                    inserted_chars += len(b_move) + 1

                    if b_node:
                        target_box.tag_bind(b_tag_name, "<Button-1>", lambda e, n=b_node: self.jump_to_node(n))
                    if b_alts:
                        target_box.insert("end", f"{b_alts} ", "comment_tag")
                        inserted_chars += len(b_alts) + 1

            target_box.configure(state="disabled")
            print(
                f"[SYNC SUCCESS] Rendered {len(sorted_moves)} rows ({inserted_chars} chars) into analysis_textbox. (Mapped: {box.winfo_ismapped()})")
            sys.stdout.flush()

        except Exception as e:
            print(f"[SYNC CANDIDATE ERROR]: {e}")
            sys.stdout.flush()
            traceback.print_exc()