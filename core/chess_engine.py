import io
import os
import platform
import shutil
import sys
import traceback
from pathlib import Path
import chess
import chess.engine
import chess.pgn


IGNORED_SUFFIXES = {".nnue", ".txt", ".md", ".json", ".log", ".bin", ".pdb", ".py"}


def classify_move_evaluation(
    move_num: int,
    is_white: bool,
    eval_before: float,
    eval_after: float,
    white_streak: int = 0,
    black_streak: int = 0,
    board_before: chess.Board | None = None,
    move: chess.Move | None = None,
):
    """
    Shared move evaluation classifier (session-only, never persisted).
    Preserves numeric evaluations, applies opening leniency before move 8,
    and maps to light_blue, green, orange, red, or default.
    Returns: (tag, next_white_streak, next_black_streak, note)
    """
    w_streak = white_streak
    b_streak = black_streak
    note = ""

    if move_num < 8:
        return "default", w_streak, b_streak, note

    if is_white:
        loss = round(eval_before - eval_after, 2)
    else:
        loss = round(eval_after - eval_before, 2)

    minor_trade_nuance = False
    if board_before is not None and move is not None and board_before.is_capture(move):
        moved_piece = board_before.piece_type_at(move.from_square)
        captured_piece = board_before.piece_type_at(move.to_square)
        if moved_piece == chess.BISHOP and captured_piece in (chess.KNIGHT, chess.BISHOP):
            minor_trade_nuance = True
            note = "bishop trade"

    if loss >= 2.6:
        return "red", 0, 0, note
    if loss >= 1.0:
        return "orange", 0, 0, note
    if loss >= 0.3:
        if is_white:
            if b_streak > 0:
                b_streak -= 1
            else:
                w_streak += 1
            if minor_trade_nuance and loss >= 0.45 and w_streak < 3:
                w_streak += 1
            tag = "green" if w_streak >= 3 else "light_blue"
        else:
            if w_streak > 0:
                w_streak -= 1
            else:
                b_streak += 1
            if minor_trade_nuance and loss >= 0.45 and b_streak < 3:
                b_streak += 1
            tag = "green" if b_streak >= 3 else "light_blue"
        return tag, w_streak, b_streak, note

    if is_white and b_streak > 0:
        b_streak -= 1
    elif not is_white and w_streak > 0:
        w_streak -= 1

    return "default", w_streak, b_streak, note


class ChessEngine:
    def __init__(self, current_engine="Stockfish"):
        self.app_root = Path(__file__).resolve().parent.parent
        self.engines_dir = self.app_root / "engines"
        self.engines_dir.mkdir(parents=True, exist_ok=True)
        self.current_engine = current_engine or "Stockfish"
        self.engine_path = self._resolve_engine_path(self.current_engine)
        self._active_engine = None

    def _is_engine_executable(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if path.suffix.lower() in IGNORED_SUFFIXES:
            return False
        if platform.system() == "Windows":
            return path.suffix.lower() == ".exe"
        return os.access(path, os.X_OK) or path.suffix == ""

    def _find_engine_in_folder(self, name_query: str):
        if not name_query:
            return None
        needle = str(name_query).strip().lower()
        if not needle or not self.engines_dir.exists():
            return None

        matches = [
            p for p in self.engines_dir.iterdir()
            if self._is_engine_executable(p) and needle in p.name.lower()
        ]
        if not matches:
            return None

        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return matches[0]

    def _resolve_engine_path(self, engine_name: str) -> Path:
        cleaned = (engine_name or "").strip()

        if cleaned and cleaned.lower() != "stockfish":
            custom_match = self._find_engine_in_folder(cleaned)
            if custom_match is not None:
                return custom_match

        stockfish_match = self._find_engine_in_folder("stockfish")
        if stockfish_match is not None:
            return stockfish_match

        if platform.system() == "Windows":
            return self.engines_dir / "stockfish.exe"
        return self.engines_dir / "stockfish"

    def set_current_engine(self, engine_name: str) -> Path:
        self.current_engine = (engine_name or "Stockfish").strip() or "Stockfish"
        self.engine_path = self._resolve_engine_path(self.current_engine)
        return self.engine_path

    def add_engine_file(self, source_file_path: str, select_engine: bool = False) -> Path:
        src = Path(source_file_path)
        if not src.exists() or not src.is_file():
            raise FileNotFoundError(f"Engine file not found: {source_file_path}")

        self.engines_dir.mkdir(parents=True, exist_ok=True)
        dest = self.engines_dir / src.name

        if src.resolve() != dest.resolve():
            if dest.exists():
                counter = 1
                while dest.exists():
                    dest = self.engines_dir / f"{src.stem}_{counter}{src.suffix}"
                    counter += 1
            shutil.copy2(src, dest)

        if select_engine:
            self.current_engine = dest.stem
            self.engine_path = dest

        return dest

    def verify_health(self):
        if not self.engine_path or not Path(self.engine_path).exists():
            return False
        try:
            with chess.engine.SimpleEngine.popen_uci(str(self.engine_path)) as engine:
                return engine.ping()
        except Exception:
            return False

    def stop_active_engine(self):
        eng = self._active_engine
        self._active_engine = None
        if eng is not None:
            try:
                eng.quit()
            except (chess.engine.EngineTerminatedError, ProcessLookupError, ChildProcessError, OSError):
                pass

    @staticmethod
    def _format_score(score_obj: chess.engine.PovScore) -> tuple[str, float]:
        white_score = score_obj.white()
        if white_score.is_mate():
            mate_val = white_score.mate() or 0
            sign = "-" if mate_val < 0 else "+"
            label = f"{sign}M{abs(mate_val)}"
            numeric = 100.0 if mate_val > 0 else -100.0
            return label, numeric
        cp = white_score.score()
        numeric = (cp if cp is not None else 0) / 100.0
        return f"{numeric:+.2f}", numeric

    def analyze_position(
        self,
        board: chess.Board,
        depths=(1, 5, 10, 15, 20, 25),
        multipv=5,
        callback=None,
        worker_ref=None,
        max_depth: int = 30,
    ):
        """
        Streams live MultiPV analysis up to max_depth and exits immediately when
        worker_ref.cancel is set or worker_ref.generation no longer matches.
        Never reports elapsed/millisecond timing.
        """
        target_depths = set(depths) if depths else set()
        effective_max_depth = max([max_depth] + list(target_depths)) if target_depths else max_depth
        lines_by_pv = {}

        def _is_stale():
            if not worker_ref:
                return False
            if getattr(worker_ref, "cancel", False):
                return True
            gen = getattr(worker_ref, "generation", None)
            expected_gen = getattr(worker_ref, "expected_generation", None)
            if gen is not None and expected_gen is not None and gen != expected_gen:
                return True
            return False

        try:
            with chess.engine.SimpleEngine.popen_uci(str(self.engine_path)) as engine:
                self._active_engine = engine
                try:
                    engine.configure({"Hash": 64, "Threads": 2})
                except Exception:
                    pass

                with engine.analysis(board, chess.engine.Limit(depth=effective_max_depth), multipv=multipv) as analysis:
                    for info in analysis:
                        if _is_stale():
                            break

                        pv_idx = info.get("multipv", 1)
                        depth_val = info.get("depth", 0)
                        score = info.get("score")
                        pv = info.get("pv", [])

                        if score is None or not pv:
                            continue

                        eval_str, _ = self._format_score(score)
                        temp_b = board.copy()
                        san_moves = []
                        for m in pv[:18]:
                            try:
                                san_moves.append(temp_b.san(m))
                                temp_b.push(m)
                            except Exception:
                                break

                        lines_by_pv[pv_idx] = {
                            "pv_index": pv_idx,
                            "depth": depth_val,
                            "eval": eval_str,
                            "moves_san": san_moves,
                            "pv_line": " ".join(san_moves),
                        }

                        if target_depths and depth_val not in target_depths and depth_val < effective_max_depth:
                            continue

                        ordered_lines = [lines_by_pv[k] for k in sorted(lines_by_pv.keys())]
                        primary_eval = ordered_lines[0]["eval"] if ordered_lines else "+0.00"
                        pv_strings = [item["pv_line"] for item in ordered_lines]

                        if callback and not _is_stale():
                            callback({
                                "depth": depth_val,
                                "eval": primary_eval,
                                "lines": ordered_lines,
                                "pv_lines": pv_strings,
                            })

                        if getattr(worker_ref, "pausing_to_depth_30", False) and depth_val >= 30:
                            break
        except Exception as e:
            if not _is_stale():
                print(f"[Position Engine Error]: {e}")
                sys.stdout.flush()
        finally:
            self._active_engine = None

    def analyze_game(self, pgn_input, mode="review", game_index=0, callback=None, start_move=1, end_move=200, worker_ref=None):
        game = None
        if isinstance(pgn_input, str):
            pgn_io = io.StringIO(pgn_input)
            for _ in range(game_index + 1):
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
        white_streak = 0
        black_streak = 0

        def _cancelled():
            return bool(worker_ref and getattr(worker_ref, "cancel", False))

        try:
            with chess.engine.SimpleEngine.popen_uci(str(self.engine_path)) as engine:
                self._active_engine = engine
                try:
                    engine.configure({"Hash": 256, "Threads": 4})
                except Exception:
                    pass

                current_depth = 12

                for i, move in enumerate(game.mainline_moves()):
                    if _cancelled():
                        break

                    ply = i + 1
                    move_num = (i // 2) + 1
                    is_white = (i % 2 == 0)

                    if move_num < start_move:
                        board.push(move)
                        continue
                    if move_num > end_move:
                        break

                    if running_score is None:
                        info_before = engine.analyse(board, chess.engine.Limit(depth=current_depth), multipv=1)
                        _, score_before = self._format_score(info_before[0]["score"])
                    else:
                        score_before = running_score

                    if _cancelled():
                        break

                    board_before_move = board.copy()
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

                    if _cancelled():
                        break

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
                    _, score_after = self._format_score(info_after[0]["score"])

                    running_score = score_after
                    eval_diff = round(score_after - score_before, 2)

                    tag, white_streak, black_streak, note = classify_move_evaluation(
                        move_num=move_num,
                        is_white=is_white,
                        eval_before=score_before,
                        eval_after=score_after,
                        white_streak=white_streak,
                        black_streak=black_streak,
                        board_before=board_before_move,
                        move=move,
                    )

                    result = {
                        "ply": ply,
                        "move_num": move_num,
                        "is_white": is_white,
                        "played_san": played_san,
                        "eval_after": score_after,
                        "eval_diff": eval_diff,
                        "tag": tag,
                        "note": note,
                        "white_streak": white_streak,
                        "black_streak": black_streak,
                        "candidates": candidates_data,
                        "recs": recs,
                        "top_alt_pv": top_alt_pv_san,
                        "pv_line": " ".join(pv_line),
                        "mode": mode,
                        "board": board.copy(),
                    }

                    if callback and not _cancelled():
                        callback(result)
                        sys.stdout.flush()

        except Exception as e:
            if not _cancelled():
                print(f"[Engine Analysis Error]: {e}")
                sys.stdout.flush()
                traceback.print_exc()
        finally:
            self._active_engine = None

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
