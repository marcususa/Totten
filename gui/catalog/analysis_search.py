import io
import json
import re
import threading
from pathlib import Path
import chess
import chess.pgn
import customtkinter as ctk
from core.chess_engine import ChessEngine
from core.constants import THEME
from core.db_backend import USE_DUCKDB, connect_db, table_exists

# Opening to early middlegame scan cap (in plies / half-moves; 50 plies = 25 full moves)
MAX_SCAN_PLIES = 50
# Window around Move 2 (in plies / half-moves; 10 plies = +/- 5 moves)
MOVE_WINDOW_PLIES = 10
# Engine evaluation depth for ranking Move 2 occurrences
ENGINE_RANK_DEPTH = 15


def _strip_move_prefix(move_str: str) -> str:
    s = (move_str or "").strip()
    s = re.sub(r"^\d+\s*\.\.\.", "", s)
    s = re.sub(r"^\d+\s*\.", "", s)
    return s.strip()


def _normalize_san(move_str: str) -> str:
    s = _strip_move_prefix(move_str)
    return s.rstrip("+!?#").lower()


def _tokenize_pgn_moves_fast(pgn_text: str, max_plies: int = MAX_SCAN_PLIES) -> list[str]:
    """
    Fast text-based move extractor without full board/SAN conversion.
    Strips headers, comments, variations, NAGs, move numbers, and result tokens.
    """
    if not pgn_text:
        return []

    body = re.sub(r"^\[[^\]]*\]\s*", "", pgn_text, flags=re.MULTILINE)
    body = re.sub(r"\{[^}]*\}", " ", body)

    while "(" in body and ")" in body:
        updated = re.sub(r"\([^()]*\)", " ", body)
        if updated == body:
            break
        body = updated

    body = re.sub(r"\$\d+", " ", body)
    body = re.sub(r"\b(?:1-0|0-1|1/2-1/2|\*)\s*$", "", body.strip())

    moves: list[str] = []
    for tok in body.split():
        cleaned = _normalize_san(tok)
        if cleaned and cleaned not in {"1-0", "0-1", "1/2-1/2", "*"}:
            moves.append(cleaned)
            if len(moves) >= max_plies:
                break
    return moves


def _matching_move2_indices(
    moves: list[str],
    move1: str,
    move2: str,
    window_plies: int = MOVE_WINDOW_PLIES,
) -> list[int]:
    """
    Prioritizes Move 2 (the better move) and returns ply indices of Move 2
    occurrences that have Move 1 within +/- window_plies half-moves.
    If Move 1 is empty, returns all Move 2 indices.
    """
    m1 = _normalize_san(move1)
    m2 = _normalize_san(move2)

    if not moves:
        return []

    if not m2:
        if not m1:
            return [0]
        return [idx for idx, m in enumerate(moves) if m == m1]

    move2_positions = [idx for idx, m in enumerate(moves) if m == m2]
    if not move2_positions:
        return []

    if not m1:
        return move2_positions

    move1_positions = [idx for idx, m in enumerate(moves) if m == m1]
    if not move1_positions:
        return []

    valid_m2 = []
    for i2 in move2_positions:
        if any(abs(i1 - i2) <= window_plies for i1 in move1_positions):
            valid_m2.append(i2)
    return valid_m2


def _matches_move2_priority_window(
    moves: list[str],
    move1: str,
    move2: str,
    window_plies: int = MOVE_WINDOW_PLIES,
) -> bool:
    m1 = _normalize_san(move1)
    m2 = _normalize_san(move2)
    if not m1 and not m2:
        return True
    return len(_matching_move2_indices(moves, move1, move2, window_plies)) > 0


def _parse_eval_to_float(raw_eval) -> float | None:
    if raw_eval is None:
        return None
    if isinstance(raw_eval, (int, float)):
        return float(raw_eval)
    s = str(raw_eval).strip().upper()
    if not s:
        return None
    if s.startswith("M") or s.startswith("#") or "MATE" in s:
        neg = "-" in s
        digits = re.sub(r"[^0-9]", "", s)
        mate_in = int(digits) if digits else 1
        val = 100.0 - min(mate_in, 50) * 0.1
        return -val if neg else val
    try:
        return float(s.lstrip("+"))
    except ValueError:
        return None


class AnalysisSearchMixin:
    """Mixin class for game loading into analysis and two-move search."""

    def get_active_tracker_move_notation(self) -> str:
        node = getattr(self, "board_node", None) or getattr(self, "current_node", None)
        if node is None:
            return ""

        variations = getattr(node, "variations", None)
        if not variations:
            return ""

        try:
            next_node = node.variation(0)
        except Exception:
            next_node = variations[0] if len(variations) > 0 else None

        if next_node is None or getattr(next_node, "move", None) is None:
            return ""

        if hasattr(node, "board"):
            try:
                return _strip_move_prefix(node.board().san(next_node.move))
            except Exception:
                pass

        if hasattr(next_node, "san"):
            try:
                san_val = next_node.san()
                if san_val:
                    return _strip_move_prefix(str(san_val))
            except Exception:
                pass

        try:
            return next_node.move.uci()
        except Exception:
            return ""

    def sync_move1_from_tracker(self, force: bool = False):
        entry = getattr(self, "entry_search_move1", None)
        if entry is None:
            return
        try:
            if not entry.winfo_exists():
                return
        except Exception:
            return

        node = getattr(self, "board_node", None) or getattr(self, "current_node", None)
        at_start = node is None or getattr(node, "parent", None) is None

        san_only = "" if at_start else self.get_active_tracker_move_notation()
        target_text = "Move 1" if at_start else san_only

        placeholder_color = entry.cget("placeholder_text_color")
        normal_color = THEME.get("text_primary")

        current_val = entry.get().strip()
        last_auto = getattr(self, "_last_auto_move1", "")
        user_edited = getattr(self, "_move1_user_edited", False)

        if user_edited and current_val:
            entry.configure(text_color=normal_color)
            return

        if force or not user_edited or not current_val or current_val == last_auto:
            entry.delete(0, "end")
            if target_text:
                entry.insert(0, target_text)
                entry.configure(
                    text_color=placeholder_color if target_text == "Move 1" else normal_color
                )
            self._last_auto_move1 = target_text
            self._move1_user_edited = False

    def _safe_load_game(self, game_node, category_source=None):
        if category_source and category_source != "catalog":
            return

        if isinstance(game_node, int):
            import gui.app_state as state
            active_games = state.catalog_state.get("active_games", [])
            if 0 <= game_node < len(active_games):
                game_node = active_games[game_node]

        if hasattr(game_node, "root") and callable(game_node.root):
            game_node = game_node.root()

        self.current_game = game_node
        self.active_game = game_node
        self.root_game_node = game_node
        self.current_node = game_node
        self.board_node = game_node
        self._move1_user_edited = False

        import gui.app_state as state
        if hasattr(state, "catalog_state") and isinstance(state.catalog_state, dict):
            state.catalog_state["active_focus"] = game_node

        if hasattr(self, "_update_active_boards") and hasattr(self.current_node, "board"):
            self.current_board = self.current_node.board()
            self._update_active_boards(self.current_board)

        self._render_game_pgn_tree(game_node)
        self.sync_move1_from_tracker(force=True)

    def _resolve_catalog_db_path(self):
        db_path = getattr(self, "db_path", None)
        if db_path:
            return Path(db_path)
        root_dir = getattr(self, "root_dir", None) or Path(__file__).resolve().parent.parent.parent
        return Path(root_dir) / ("catalog.duckdb" if USE_DUCKDB else "catalog.sqlite")

    def _resolve_pgn_file_path(self):
        fname = getattr(self, "filename", None) or "personal_catalog.pgn"
        p = Path(fname)
        if p.exists():
            return p
        root_dir = getattr(self, "root_dir", None) or Path(__file__).resolve().parent.parent.parent
        candidate = Path(root_dir) / p.name
        return candidate if candidate.exists() else None

    def _split_pgn_blocks(self, raw_pgn: str):
        if not raw_pgn:
            return []
        blocks = []
        current_lines = []
        seen_moves_in_block = False

        for line in raw_pgn.splitlines():
            stripped = line.strip()
            if stripped.startswith("[Event ") and seen_moves_in_block and current_lines:
                blocks.append("\n".join(current_lines))
                current_lines = [line]
                seen_moves_in_block = False
            else:
                current_lines.append(line)
                if stripped and not stripped.startswith("["):
                    seen_moves_in_block = True

        if current_lines:
            blocks.append("\n".join(current_lines))
        return blocks

    def _parse_header_tags_fast(self, pgn_block: str) -> dict:
        headers = {}
        for line in pgn_block.splitlines():
            s = line.strip()
            if not s.startswith("["):
                if headers:
                    break
                continue
            m = re.match(r'^\[([A-Za-z0-9_]+)\s+"(.*)"\]$', s)
            if m:
                headers[m.group(1)] = m.group(2)
        return headers

    def _collect_candidate_games(self):
        candidates = []
        seen_signatures = set()

        def _add_candidate(eco, opening, variation, white, black, game_index, headers, pgn_text, game_obj, moves):
            eco_val = (eco or (headers or {}).get("ECO") or "A00").strip() or "A00"
            opening_val = (opening or (headers or {}).get("Opening") or "Unknown Opening").strip() or "Unknown Opening"
            variation_val = (variation or (headers or {}).get("Variation") or "Main Line").strip() or "Main Line"
            white_val = white or (headers or {}).get("White", "Unknown")
            black_val = black or (headers or {}).get("Black", "Unknown")
            sig = (eco_val, opening_val, variation_val, white_val, black_val, tuple(moves))
            if sig in seen_signatures:
                return
            seen_signatures.add(sig)
            candidates.append({
                "eco": eco_val,
                "opening": opening_val,
                "variation": variation_val,
                "white": white_val,
                "black": black_val,
                "game_index": game_index,
                "headers": headers or {},
                "pgn_text": pgn_text or "",
                "game_object": game_obj,
                "moves": moves,
            })

        db_path = self._resolve_catalog_db_path()
        if db_path.exists():
            try:
                con = connect_db(db_path, read_only=True)
                if table_exists(con, "catalog_headers"):
                    rows = con.execute(
                        "SELECT eco, opening, variation, white, black, game_index, headers_json, pgn_text FROM catalog_headers"
                    ).fetchall()
                    for eco, opening, variation, white, black, game_index, headers_json, pgn_text in rows:
                        if not pgn_text:
                            continue
                        moves = _tokenize_pgn_moves_fast(pgn_text)
                        if not moves:
                            continue
                        try:
                            headers = json.loads(headers_json) if headers_json else {}
                        except Exception:
                            headers = {}
                        _add_candidate(eco, opening, variation, white, black, game_index, headers, pgn_text, None, moves)
                con.close()
            except Exception as e:
                print(f"[TWO-MOVE SEARCH DB ERROR] {e}")

        in_memory_games = []
        for g in (getattr(self, "game_list", None) or []):
            in_memory_games.append(g)
        try:
            import gui.app_state as state
            if hasattr(state, "catalog_state") and isinstance(state.catalog_state, dict):
                for g in (state.catalog_state.get("active_games") or []):
                    in_memory_games.append(g)
            for g in (getattr(state, "all_games", None) or []):
                in_memory_games.append(g)
        except Exception:
            pass

        for idx, g in enumerate(in_memory_games, start=1):
            if g is None or not hasattr(g, "headers"):
                continue
            pgn_str = str(g)
            moves = _tokenize_pgn_moves_fast(pgn_str)
            if not moves:
                continue
            h = dict(g.headers)
            _add_candidate(
                h.get("ECO"),
                h.get("Opening"),
                h.get("Variation"),
                h.get("White"),
                h.get("Black"),
                idx,
                h,
                pgn_str,
                g,
                moves,
            )

        pgn_path = self._resolve_pgn_file_path()
        if pgn_path and pgn_path.exists():
            try:
                raw_text = pgn_path.read_text(encoding="utf-8", errors="replace")
                for idx, block in enumerate(self._split_pgn_blocks(raw_text), start=1):
                    moves = _tokenize_pgn_moves_fast(block)
                    if not moves:
                        continue
                    h = self._parse_header_tags_fast(block)
                    _add_candidate(
                        h.get("ECO"),
                        h.get("Opening"),
                        h.get("Variation"),
                        h.get("White"),
                        h.get("Black"),
                        idx,
                        h,
                        block,
                        None,
                        moves,
                    )
            except Exception as e:
                print(f"[TWO-MOVE SEARCH PGN ERROR] {e}")

        return candidates

    def _ensure_game_object(self, record: dict):
        game_obj = record.get("game_object")
        if game_obj is not None:
            return game_obj
        pgn_text = record.get("pgn_text")
        if not pgn_text:
            return None
        try:
            game_obj = chess.pgn.read_game(io.StringIO(pgn_text))
            record["game_object"] = game_obj
            return game_obj
        except Exception as e:
            print(f"[TWO-MOVE SEARCH PARSE ERROR] {e}")
            return None

    def _eval_position_at_depth(self, engine: ChessEngine, board: chess.Board, depth: int, cache: dict) -> float | None:
        fen_key = (board.fen(), depth)
        if fen_key in cache:
            return cache[fen_key]

        result_holder = {}

        def on_eval(res):
            result_holder["latest"] = res

        engine.analyze_position(
            board.copy(),
            depths=(depth,),
            multipv=1,
            callback=on_eval,
            max_depth=depth,
        )

        res = result_holder.get("latest") or {}
        raw_val = res.get("eval")
        if raw_val is None and res.get("lines"):
            raw_val = res["lines"][0].get("eval")

        score = _parse_eval_to_float(raw_val)
        if score is not None:
            # Normalize relative to White so highest evaluation sorts consistently
            if board.turn == chess.BLACK:
                score = -score
            cache[fen_key] = score
        return score

    def _score_record_move2_at_depth(
        self,
        engine: ChessEngine,
        record: dict,
        move2_target: str,
        target_indices: list[int],
        depth: int,
        cache: dict,
    ) -> float | None:
        game_obj = self._ensure_game_object(record)
        if game_obj is None:
            return None

        m2_norm = _normalize_san(move2_target)
        target_set = set(target_indices)
        best_score = None

        board = game_obj.board()
        ply_idx = 0
        node = game_obj

        while node.variations and ply_idx <= MAX_SCAN_PLIES:
            node = node.variation(0)
            mv = node.move
            if mv is None:
                break

            san_norm = _normalize_san(board.san(mv))
            board.push(mv)

            if not m2_norm or (san_norm == m2_norm and (not target_set or ply_idx in target_set)):
                score = self._eval_position_at_depth(engine, board, depth, cache)
                if score is not None:
                    if best_score is None or score > best_score:
                        best_score = score

            ply_idx += 1

        return best_score

    def _sort_grouped_by_eval(self, grouped: dict) -> dict:
        sorted_grouped = {}
        for eco_code in sorted(grouped.keys()):
            openings_map = grouped[eco_code]
            sorted_openings = {}
            for opening_name in sorted(openings_map.keys()):
                vars_map = openings_map[opening_name]
                sorted_vars = {}
                for var_name in sorted(vars_map.keys()):
                    games = list(vars_map[var_name])
                    games.sort(
                        key=lambda r: (
                            r.get("move2_eval") is not None,
                            r.get("move2_eval") if r.get("move2_eval") is not None else float("-inf"),
                        ),
                        reverse=True,
                    )
                    sorted_vars[var_name] = games
                sorted_openings[opening_name] = sorted_vars
            sorted_grouped[eco_code] = sorted_openings
        return sorted_grouped

    def _query_two_move_search_games(self, move1: str, move2: str):
        grouped = {}
        for cand in self._collect_candidate_games():
            matched_indices = _matching_move2_indices(cand["moves"], move1, move2)
            if not _matches_move2_priority_window(cand["moves"], move1, move2):
                continue

            record = {
                "eco": cand["eco"],
                "opening": cand["opening"],
                "variation": cand["variation"],
                "white": cand["white"],
                "black": cand["black"],
                "game_index": cand["game_index"],
                "headers": cand["headers"],
                "pgn_text": cand["pgn_text"],
                "game_object": cand["game_object"],
                "matched_move2_indices": matched_indices,
                "move2_eval": None,
            }
            grouped.setdefault(cand["eco"], {}).setdefault(cand["opening"], {}).setdefault(cand["variation"], []).append(record)

        return grouped

    def _start_depth_ranking_worker(self, move1: str, move2: str, grouped: dict, depth: int = ENGINE_RANK_DEPTH):
        self._rank_search_gen = getattr(self, "_rank_search_gen", 0) + 1
        gen_token = self._rank_search_gen

        all_records = [
            rec
            for openings_map in grouped.values()
            for vars_map in openings_map.values()
            for games in vars_map.values()
            for rec in games
        ]
        if not all_records or not _normalize_san(move2):
            return

        def worker_fn():
            cache = getattr(self, "_search_eval_cache", None)
            if cache is None:
                cache = {}
                self._search_eval_cache = cache

            engine = None
            try:
                engine = ChessEngine()
                for idx, rec in enumerate(all_records, start=1):
                    if getattr(self, "_rank_search_gen", gen_token) != gen_token:
                        return
                    score = self._score_record_move2_at_depth(
                        engine=engine,
                        record=rec,
                        move2_target=move2,
                        target_indices=rec.get("matched_move2_indices") or [],
                        depth=depth,
                        cache=cache,
                    )
                    rec["move2_eval"] = score

                    if idx % 5 == 0 or idx == len(all_records):
                        sorted_copy = self._sort_grouped_by_eval(grouped)
                        status_txt = f"Engine depth {depth}: scored {idx}/{len(all_records)} games"
                        self.after(
                            0,
                            lambda g=gen_token, sg=sorted_copy, st=status_txt: self._apply_ranked_update(g, move1, move2, sg, st),
                        )
            except Exception as e:
                print(f"[TWO-MOVE ENGINE RANK ERROR] {e}")
            finally:
                if engine is not None and hasattr(engine, "stop_active_engine"):
                    try:
                        engine.stop_active_engine()
                    except Exception:
                        pass

        threading.Thread(target=worker_fn, daemon=True).start()

    def _apply_ranked_update(self, gen_token: int, move1: str, move2: str, sorted_grouped: dict, status_text: str):
        if getattr(self, "_rank_search_gen", gen_token) != gen_token:
            return
        win = getattr(self, "_two_move_search_win", None)
        if win is None:
            return
        try:
            if not win.winfo_exists():
                return
        except Exception:
            return
        self._render_two_move_search_popup(move1, move2, sorted_grouped, status_text=status_text)

    def _load_search_game_record(self, record: dict):
        if not record:
            return
        game_obj = self._ensure_game_object(record)
        if game_obj is None:
            return

        self.current_game = game_obj
        self.active_game = game_obj
        self._last_tracked_node = None

        if hasattr(self, "load_game") and callable(self.load_game):
            self.load_game(game_obj)
        else:
            self._safe_load_game(game_obj, category_source="catalog")

    def _get_or_create_search_results_window(self, move1: str, move2: str):
        win = getattr(self, "_two_move_search_win", None)
        if win is not None:
            try:
                if win.winfo_exists():
                    win.title(f"Search Results: {move1 or '*'} / {move2 or '*'}")
                    win.deiconify()
                    win.lift()
                    win.focus_force()
                    return win, getattr(self, "_two_move_search_scroll", None)
            except Exception:
                pass

        win = ctk.CTkToplevel(self)
        win.title(f"Search Results: {move1 or '*'} / {move2 or '*'}")
        win.geometry("540x580")
        win.configure(fg_color=THEME.get("bg_panel"))
        win.grid_rowconfigure(0, weight=1)
        win.grid_columnconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(
            win,
            fg_color=THEME.get("bg_surface"),
            corner_radius=6,
        )
        scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        scroll.grid_columnconfigure(0, weight=1)

        self._two_move_search_win = win
        self._two_move_search_scroll = scroll
        win.lift()
        win.focus_force()
        return win, scroll

    def _render_two_move_search_popup(self, move1: str, move2: str, grouped: dict, status_text: str = ""):
        _, results_scroll = self._get_or_create_search_results_window(move1, move2)
        if results_scroll is None:
            return

        for widget in results_scroll.winfo_children():
            widget.destroy()

        total_games = sum(
            len(games)
            for openings_map in grouped.values()
            for vars_map in openings_map.values()
            for games in vars_map.values()
        )

        header_msg = f"Search: {move1 or '*'} / {move2 or '*'} ({total_games})"
        if status_text:
            header_msg = f"{header_msg} — {status_text}"

        ctk.CTkLabel(
            results_scroll,
            text=header_msg,
            anchor="w",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.get("text_primary"),
        ).pack(fill="x", padx=6, pady=(4, 8))

        if not grouped:
            ctk.CTkLabel(
                results_scroll,
                text="No matching games found.",
                anchor="w",
                font=ctk.CTkFont(size=11),
                text_color=THEME.get("text_primary"),
            ).pack(fill="x", padx=6, pady=8)
            return

        for eco_code in sorted(grouped.keys()):
            openings_map = grouped[eco_code]
            eco_total = sum(
                len(games)
                for vars_map in openings_map.values()
                for games in vars_map.values()
            )

            eco_frame = ctk.CTkFrame(
                results_scroll,
                fg_color=THEME.get("bg_panel"),
                border_color=THEME.get("border_ring", THEME.get("bg_surface")),
                border_width=1,
                corner_radius=6,
            )
            eco_frame.pack(fill="x", padx=4, pady=4)
            eco_frame.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                eco_frame,
                text=f"ECO {eco_code} ({eco_total})",
                anchor="w",
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=THEME.get("text_primary"),
            ).grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 2))

            next_eco_row = 1
            for opening_name in sorted(openings_map.keys()):
                vars_map = openings_map[opening_name]
                op_total = sum(len(games) for games in vars_map.values())

                op_frame = ctk.CTkFrame(
                    eco_frame,
                    fg_color=THEME.get("bg_surface"),
                    corner_radius=6,
                )
                op_frame.grid(row=next_eco_row, column=0, sticky="ew", padx=8, pady=3)
                op_frame.grid_columnconfigure(0, weight=1)
                next_eco_row += 1

                ctk.CTkLabel(
                    op_frame,
                    text=f"{opening_name} ({op_total})",
                    anchor="w",
                    font=ctk.CTkFont(size=11, weight="bold"),
                    text_color=THEME.get("text_primary"),
                ).grid(row=0, column=0, sticky="ew", padx=6, pady=(4, 2))

                next_op_row = 1
                for var_name in sorted(vars_map.keys()):
                    games = vars_map[var_name]

                    ctk.CTkLabel(
                        op_frame,
                        text=f"{var_name} ({len(games)})",
                        anchor="w",
                        font=ctk.CTkFont(size=10, weight="bold"),
                        text_color=THEME.get("text_primary"),
                    ).grid(row=next_op_row, column=0, sticky="ew", padx=10, pady=(2, 1))
                    next_op_row += 1

                    for rec in games:
                        ev = rec.get("move2_eval")
                        ev_str = f" [{ev:+.2f}]" if isinstance(ev, (int, float)) else " [...]"
                        ctk.CTkButton(
                            op_frame,
                            text=f"{rec['white']} vs {rec['black']}{ev_str}",
                            anchor="w",
                            height=22,
                            font=ctk.CTkFont(size=10),
                            fg_color=THEME.get("bg_panel"),
                            hover_color=THEME.get("btn_hover"),
                            text_color=THEME.get("text_primary"),
                            command=lambda r=rec: self._load_search_game_record(r),
                        ).grid(row=next_op_row, column=0, sticky="ew", padx=16, pady=1)
                        next_op_row += 1

    def run_two_move_search(self):
        move1 = _strip_move_prefix(self.entry_search_move1.get()) if hasattr(self, "entry_search_move1") else ""
        move2 = _strip_move_prefix(self.entry_search_move2.get()) if hasattr(self, "entry_search_move2") else ""
        grouped = self._query_two_move_search_games(move1, move2)
        self._render_two_move_search_popup(move1, move2, grouped, status_text="Queueing depth 15...")
        self._start_depth_ranking_worker(move1, move2, grouped, depth=ENGINE_RANK_DEPTH)