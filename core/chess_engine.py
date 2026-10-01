import io
import platform
import sys
import traceback
from pathlib import Path
import chess
import chess.engine
import chess.pgn


class ChessEngine:
    def __init__(self):
        base_dir = Path(__file__).resolve().parent.parent / "engines"
        system = platform.system()

        if system == "Windows":
            possible_paths = [
                base_dir / "stockfish-windows-x86-64-sse41-popcnt.exe",
                base_dir / "stockfish-windows-x86-64-avx2.exe",
                base_dir / "stockfish.exe",
            ]
        elif system == "Linux":
            possible_paths = [
                base_dir / "stockfish",
                base_dir / "stockfish-ubuntu-x86-64",
                base_dir / "stockfish-ubuntu-x86-64-bmi2",
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
            self.engine_path = possible_paths[0]

    def verify_health(self):
        """Verifies the discovered binary can complete a basic UCI handshake."""
        if not self.engine_path or not Path(self.engine_path).exists():
            return False
        try:
            with chess.engine.SimpleEngine.popen_uci(str(self.engine_path)) as engine:
                return engine.ping()
        except Exception:
            return False

    def analyze_game(self, pgn_input, mode="review", game_index=0, callback=None, start_move=1, end_move=200):
        print(f"[CHESS_ENGINE] analyze_game called: mode={mode}, start_move={start_move}, end_move={end_move}")
        sys.stdout.flush()

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
            sys.stdout.flush()
            return

        if not game:
            print(f"[Engine Error]: Could not find game at index {game_index} in PGN input.")
            sys.stdout.flush()
            return

        board = game.board()
        running_score = None

        try:
            print(f"[CHESS_ENGINE] Spawning engine via popen_uci at: {self.engine_path}")
            sys.stdout.flush()

            with chess.engine.SimpleEngine.popen_uci(str(self.engine_path)) as engine:
                print(f"[CHESS_ENGINE] Engine spawned successfully. Configuring...")
                sys.stdout.flush()
                engine.configure({"Hash": 256, "Threads": 4})

                for i, move in enumerate(game.mainline_moves()):
                    ply = i + 1
                    move_num = (i // 2) + 1
                    is_white = (i % 2 == 0)

                    if move_num < start_move:
                        board.push(move)
                        continue
                    if move_num > end_move:
                        break

                    print(f"[CHESS_ENGINE] Analyzing move {move_num} (Ply {ply}, White={is_white})...")
                    sys.stdout.flush()

                    current_depth = 12

                    if running_score is None:
                        info_before = engine.analyse(board, chess.engine.Limit(depth=current_depth), multipv=1)
                        score_obj_before = info_before[0]["score"].white()
                        if score_obj_before.is_mate():
                            score_before = 100.0 if score_obj_before.mate() > 0 else -100.0
                        else:
                            score_before = (score_obj_before.score() or 0) / 100.0
                    else:
                        score_before = running_score

                    played_san = board.san(move)
                    candidates_data = []
                    recs = []
                    top_alt_pv_san = []

                    if mode == "candidates":
                        info_recs = engine.analyse(board, chess.engine.Limit(depth=current_depth), multipv=4)
                        if info_recs:
                            best_v = info_recs[0]["score"].relative.score(mate_score=10000) / 100.0
                            for alt_idx, v in enumerate(info_recs):
                                if "pv" in v and len(v["pv"]) > 0:
                                    cand = v["pv"][0]
                                    cand_san = board.san(cand)
                                    cand_score = v["score"].relative.score(mate_score=10000) / 100.0
                                    delta = cand_score - best_v
                                    candidates_data.append((cand_san, cand_score, delta))
                                    if cand != move:
                                        recs.append(cand_san)

                                    if alt_idx == 0:
                                        temp_b = board.copy()
                                        for pv_m in v["pv"][:10]:
                                            top_alt_pv_san.append(temp_b.san(pv_m))
                                            temp_b.push(pv_m)

                    pv_line = []
                    if mode == "standard":
                        info_before_pv = engine.analyse(board, chess.engine.Limit(depth=current_depth), multipv=1)
                        if "pv" in info_before_pv[0]:
                            temp_b = board.copy()
                            for pv_move in info_before_pv[0]["pv"][:4]:
                                pv_line.append(temp_b.san(pv_move))
                                temp_b.push(pv_move)

                    board.push(move)
                    info_after = engine.analyse(board, chess.engine.Limit(depth=current_depth), multipv=1)
                    score_obj_after = info_after[0]["score"].white()

                    if score_obj_after.is_mate():
                        score_after = 100.0 if score_obj_after.mate() > 0 else -100.0
                    else:
                        score_after = (score_obj_after.score() or 0) / 100.0

                    running_score = score_after
                    eval_diff = round(score_after - score_before, 2)
                    tag = "default"

                    if mode == "candidates":
                        cand_drop = max(0.0, (-eval_diff if is_white else eval_diff))
                        if cand_drop >= 2.30:
                            tag = "red"
                        elif cand_drop >= 1.00:
                            tag = "orange"
                        elif cand_drop >= 0.30:
                            tag = "light_blue"
                        else:
                            tag = "default"
                    elif mode == "standard":
                        cand_drop = max(0.0, (-eval_diff if is_white else eval_diff))
                        cpl_loss = cand_drop * 100.0
                        if cpl_loss >= 300.0:
                            tag = "red"
                        elif cpl_loss >= 100.0:
                            tag = "orange"
                        elif cpl_loss >= 50.0:
                            tag = "light_blue"
                        else:
                            tag = "default"
                    elif mode == "review":
                        if is_white:
                            if -0.29 <= eval_diff <= 0.29:
                                tag = "default"
                            elif -0.59 <= eval_diff <= -0.30:
                                tag = "light_blue" if move_num >= 7 else "default"
                            elif -0.99 <= eval_diff <= -0.60:
                                tag = "green" if move_num >= 7 else "default"
                            elif -2.30 <= eval_diff <= -1.00:
                                tag = "orange"
                            elif eval_diff < -2.30:
                                tag = "red"
                        else:
                            black_eval_gain = eval_diff
                            if -0.29 <= eval_diff <= 0.29:
                                tag = "default"
                            elif 0.30 <= black_eval_gain <= 0.59:
                                tag = "light_blue" if move_num >= 7 else "default"
                            elif 0.60 <= black_eval_gain <= 0.99:
                                tag = "green" if move_num >= 7 else "default"
                            elif 1.00 <= black_eval_gain <= 2.30:
                                tag = "orange"
                            elif black_eval_gain > 2.30:
                                tag = "red"

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
                        "top_alt_pv": top_alt_pv_san,
                        "pv_line": " ".join(pv_line),
                        "mode": mode,
                        "board": board.copy(),
                    }

                    if callback:
                        callback(result)
                        sys.stdout.flush()

        except Exception as e:
            print(f"[Engine Analysis Error]: {e}")
            sys.stdout.flush()
            traceback.print_exc()

    def generate_review_pgn(self, move_results, max_width=80):
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