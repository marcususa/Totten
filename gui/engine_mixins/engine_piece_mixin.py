# gui/patterns/engine_piece_mixin.py

import threading
import chess.pgn
import gui.app_state as state
from core.chess_engine import ChessEngine


class EnginePieceMixin:
    def trigger_engine_mode(self, mode_name):
        self.active_engine_mode = mode_name

        if hasattr(self, "btn_standard") and self.btn_standard:
            try:
                self.btn_standard.configure(fg_color="#2e4a8c")
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

        if self.active_game:
            self.start_piece_pattern_analysis(self.active_game)

    def toggle_game(self, event):
        if not hasattr(self, "pgn_tree") or not self.pgn_tree:
            return

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

        if hasattr(self, "_update_active_boards"):
            self._update_active_boards(self.current_node.board())

        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
                pgn_text_export = game.accept(exporter)

                self.pgn_data_text.configure(state="normal")
                self.pgn_data_text.delete("1.0", "end")
                self.pgn_data_text.insert("end", pgn_text_export)
                self.pgn_data_text.configure(state="disabled")
            except Exception as e:
                print(f"[PGN EXPORT ERROR] {e}")

        self._load_piece_pattern_moves(game)

    def _load_piece_pattern_moves(self, game):
        self.analysis_rows = {}

        # Resolve target piece dynamically from state or instance
        if hasattr(state, "patterns_state") and isinstance(state.patterns_state, dict):
            p_val = state.patterns_state.get("target_piece")
            if p_val:
                self.target_piece = p_val
        elif hasattr(state, "selected_piece") and state.selected_piece:
            self.target_piece = state.selected_piece
        elif not hasattr(self, "target_piece") or not self.target_piece:
            self.target_piece = "wp"

        temp_board = game.board()

        # Parse two-letter code (e.g. 'wb' -> color=WHITE, type=BISHOP) or single letter fallback
        p_id = str(self.target_piece).strip().lower()
        target_color = None
        target_type_char = None

        if len(p_id) == 2:
            target_color = chess.WHITE if p_id[0] == 'w' else chess.BLACK
            target_type_char = p_id[1]
        elif len(p_id) == 1:
            target_type_char = p_id
            target_color = None

        expected_type = {
            "p": chess.PAWN,
            "n": chess.KNIGHT,
            "b": chess.BISHOP,
            "r": chess.ROOK,
            "q": chess.QUEEN,
            "k": chess.KING
        }.get(target_type_char, chess.PAWN)

        for i, move in enumerate(game.mainline_moves()):
            move_num = (i // 2) + 1
            is_white = (i % 2 == 0)
            played_san = temp_board.san(move)

            piece_type = temp_board.piece_type_at(move.from_square)
            piece_color = temp_board.color_at(move.from_square)

            # Check if this move matches our target piece pattern and color
            type_matches = (piece_type == expected_type)
            color_matches = (target_color is None) or (piece_color == target_color)
            is_match = (type_matches and color_matches)

            temp_board.push(move)

            if move_num not in self.analysis_rows:
                self.analysis_rows[move_num] = {
                    "white": "", "black": "",
                    "white_tag": "default", "black_tag": "default"
                }

            display_san = f"[{played_san}]" if is_match else played_san
            tag_val = "green" if is_match else "default"

            if is_white:
                self.analysis_rows[move_num]["white"] = display_san
                self.analysis_rows[move_num]["white_tag"] = tag_val
            else:
                self.analysis_rows[move_num]["black"] = display_san
                self.analysis_rows[move_num]["black_tag"] = tag_val

        if hasattr(self, "_sync_analysis_selection"):
            self._sync_analysis_selection()

    def start_piece_pattern_analysis(self, target_game):
        self._run_piece_analysis_worker(target_game)

    def _run_piece_analysis_worker(self, target_game):
        self._load_piece_pattern_moves(target_game)

        if hasattr(self, '_current_analysis_worker') and self._current_analysis_worker:
            self._current_analysis_worker.cancel = True

        class PieceWorkerThread(threading.Thread):
            def __init__(self, game_obj, outer):
                super().__init__()
                self.game_obj = game_obj
                self.outer = outer
                self.cancel = False
                self.daemon = True

            def run(self):
                # Placeholder for background pattern evaluations if needed
                pass

        self._current_analysis_worker = PieceWorkerThread(target_game, self)
        self._current_analysis_worker.start()