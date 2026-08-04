import io
import platform
from pathlib import Path
import chess
import chess.engine
import chess.pgn


class ChessEngine:
    def __init__(self):
        base_dir = Path(__file__).parent.parent / "engines"

        # Detect the current operating system to set the correct candidate binaries
        system = platform.system()

        if system == "Windows":
            possible_paths = [
                base_dir / "stockfish-windows-x86-64-sse41-popcnt.exe",
                base_dir / "stockfish-windows-x86-64-avx2.exe",
                base_dir / "stockfish.exe",
            ]
        elif system == "Linux":
            possible_paths = [
                base_dir / "stockfish",  # Generic fallback link/name
                base_dir / "stockfish-ubuntu-x86-64",  # Generic/Baseline compatible
                base_dir / "stockfish-ubuntu-x86-64-bmi2",  # Advanced (fails on old CPUs)
            ]
        else:
            possible_paths = [
                base_dir / "stockfish",
                base_dir / "stockfish.exe",
            ]

        self.engine_path = None
        for p in possible_paths:
            if p.exists():
                self.engine_path = p
                break

        if not self.engine_path:
            # Ultimate fallback if none of the specific candidates are found
            self.engine_path = possible_paths[0]

    def analyze_game(self, pgn_input, mode="review", game_index=0, callback=None):
        """
        Analyzes a game based on mode ('review', 'candidates', 'standard')
        and streams results move-by-move via callback. Supports multi-game PGN files via game_index.
        """
        game = None
        if isinstance(pgn_input, str):
            pgn_io = io.StringIO(pgn_input)
            for idx in range(game_index + 1):
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break
        elif isinstance(pgn_input, chess.pgn.Game):
            game = pgn_input
        else:
            print("[Engine Error]: Invalid PGN input type provided.")
            return

        if not game:
            print(f"[Engine Error]: Could not find game at index {game_index} in PGN input.")
            return

        board = game.board()
        white_inacc = 0
        black_inacc = 0

        try:
            with chess.engine.SimpleEngine.popen_uci(str(self.engine_path)) as engine:
                for i, move in enumerate(game.mainline_moves()):
                    ply = i + 1
                    move_num = (i // 2) + 1
                    is_white = (i % 2 == 0)

                    # Dynamic depth scaling: Depth 15 for moves 1-10, Depth 20 for move 11+
                    current_depth = 15 if move_num <= 10 else 20

                    # 1. Evaluate position before move (passing 'game' flushes engine state automatically)
                    info_before = engine.analyse(board, chess.engine.Limit(depth=current_depth), multipv=1, game=game)
                    score_obj = info_before[0]["score"].white()
                    if score_obj.is_mate():
                        score_before = 100.0 if score_obj.mate() > 0 else -100.0
                    else:
                        score_before = (score_obj.score() or 0) / 100.0

                    played_san = board.san(move)

                    # --- MODE 1: CANDIDATE MOVES (Engine 2) ---
                    candidates_data = []
                    recs = []
                    if mode == "candidates":
                        info_recs = engine.analyse(board, chess.engine.Limit(depth=current_depth), multipv=4, game=game)

                        if info_recs:
                            best_v = info_recs[0]["score"].relative.score(mate_score=10000) / 100.0

                            for v in info_recs:
                                if "pv" in v and len(v["pv"]) > 0:
                                    cand = v["pv"][0]
                                    cand_san = board.san(cand)
                                    cand_score = v["score"].relative.score(mate_score=10000) / 100.0

                                    delta = cand_score - best_v

                                    candidates_data.append((cand_san, cand_score, delta))
                                    if cand != move:
                                        recs.append(cand_san)

                    # --- MODE 2: STANDARD PV LINE (Engine 3) ---
                    pv_line = []
                    if mode == "standard" and "pv" in info_before[0]:
                        temp_b = board.copy()
                        for pv_move in info_before[0]["pv"][:4]:
                            pv_line.append(temp_b.san(pv_move))
                            temp_b.push(pv_move)

                    # --- 2. MAKE MOVE & EVALUATE POST-MOVE POSITION ---
                    board.push(move)
                    info_after = engine.analyse(board, chess.engine.Limit(depth=current_depth), multipv=1, game=game)

                    score_after_obj = info_after[0]["score"].white()
                    if score_after_obj.is_mate():
                        score_after = 100.0 if score_after_obj.mate() > 0 else -100.0
                    else:
                        score_after = (score_after_obj.score() or 0) / 100.0

                    # Calculate evaluation loss (centipawn drop)
                    if is_white:
                        eval_diff = max(0.0, score_before - score_after)
                    else:
                        eval_diff = max(0.0, score_after - score_before)

                    tag = "default"

                    # --------------------------------------------------
                    # ISOLATED MODE TAG LOGIC
                    # --------------------------------------------------
                    # --- CANDIDATES MODE (Engine 2) ---
                    if mode == "candidates":
                        if eval_diff >= 2.30:
                            tag = "red"
                        elif eval_diff >= 1.00:
                            tag = "orange"
                        elif eval_diff >= 0.30:
                            tag = "light_blue"
                        else:
                            tag = "default"

                    # --- STANDARD MODE (Engine 3) ---
                    elif mode == "standard":
                        cpl_loss = eval_diff * 100.0

                        if score_before >= 10.0 or score_before <= -10.0:
                            if cpl_loss >= 400.0:
                                tag = "red"
                            else:
                                tag = "default"
                        else:
                            if cpl_loss >= 300.0:
                                tag = "red"        # Blunder
                            elif cpl_loss >= 100.0:
                                tag = "orange"     # Mistake
                            elif cpl_loss >= 50.0:
                                tag = "light_blue" # Inaccuracy
                            else:
                                tag = "default"    # Good / Best

                    # --- GAME REVIEW MODE (Engine 1) ---
                    elif mode == "review":
                        if eval_diff >= 2.30:
                            tag = "red"
                            if is_white:
                                white_inacc = 0
                            else:
                                black_inacc = 0

                        elif eval_diff >= 1.00:
                            tag = "orange"
                            if is_white:
                                white_inacc = 0
                            else:
                                black_inacc = 0

                        elif 0.30 <= eval_diff <= 0.90:
                            if move_num <= 7:
                                tag = "default"
                            else:
                                if is_white:
                                    if black_inacc > 0:
                                        black_inacc -= 1
                                        tag = "light_blue"
                                    else:
                                        white_inacc += 1
                                        if white_inacc == 3:
                                            tag = "green"
                                            white_inacc = 0
                                        else:
                                            tag = "light_blue"
                                else:
                                    if white_inacc > 0:
                                        white_inacc -= 1
                                        tag = "light_blue"
                                    else:
                                        black_inacc += 1
                                        if black_inacc == 3:
                                            tag = "green"
                                            black_inacc = 0
                                        else:
                                            tag = "light_blue"
                        else:
                            tag = "default"

                    result = {
                        "ply": ply,
                        "move_num": move_num,
                        "is_white": is_white,
                        "played_san": played_san,
                        "eval_after": score_after,
                        "eval_diff": eval_diff,
                        "tag": tag,
                        "candidates": candidates_data,
                        "recs": recs,
                        "pv_line": " ".join(pv_line),
                        "mode": mode,
                        "board": board.copy(),
                    }

                    if callback:
                        callback(result)

        except Exception as e:
            print(f"[Engine Analysis Error]: {e}")

    def generate_review_pgn(self, move_results, max_width=80):
        """Generates clean PGN string with numeric evaluations for copy/paste."""
        tokens = []
        for res in move_results:
            eval_str = f"{res['eval_after']:+.2f}"
            if res["is_white"]:
                tokens.append(f"{res['move_num']}. {res['played_san']} {{{eval_str}}}")
            else:
                tokens.append(f"{res['played_san']} {{{eval_str}}}")

        lines = []
        current_line = ""
        for token in tokens:
            if not current_line:
                current_line = token
            elif len(current_line) + 1 + len(token) <= max_width:
                current_line += " " + token
            else:
                lines.append(current_line)
                current_line = token

        if current_line:
            lines.append(current_line)

        return "\n".join(lines)