# gui/patterns/patterns_loader.py

import json
import threading
import chess
import chess.pgn
import duckdb
from gui.statusbar import set_status_message


class PatternsLoaderMixin:
    """Manages database connectivity, background PGN parsing, and piece-ply indexing."""

    def _init_db(self):
        try:
            con = duckdb.connect(str(self.db_path))
            con.execute("""
                CREATE TABLE IF NOT EXISTS categorized_moves (
                    game_id VARCHAR,
                    ply INTEGER,
                    fen VARCHAR,
                    move VARCHAR,
                    centipawn_score INTEGER,
                    material_diff INTEGER,
                    phase VARCHAR,
                    material_category VARCHAR
                )
            """)
            con.close()
        except Exception as e:
            print(f"Error connecting to DuckDB at {self.db_path}: {e}")

    def check_and_load_catalog(self):
        eco_exists = self.eco_dir.exists() and any(self.eco_dir.glob("*.pgn"))
        if self.db_path.exists() or self.pgn_path.exists() or eco_exists:
            self.update_idletasks()
            self.after(50, self.load_catalog_games)
        else:
            self.all_games_cache = []
            self.refresh_ui()

    def load_catalog_games(self):
        set_status_message("Loading games into Patterns Workspace...")
        self.after(
            50,
            lambda: threading.Thread(
                target=self._background_load_worker, daemon=True
            ).start(),
        )

    def _background_load_worker(self):
        loaded_games = []
        try:
            if self.pgn_path.exists():
                with open(self.pgn_path, "r", encoding="utf-8", errors="ignore") as pgn:
                    idx = 0
                    while len(loaded_games) < 300:
                        game = chess.pgn.read_game(pgn)
                        if game is None:
                            break
                        headers = dict(game.headers)

                        board = game.board()
                        piece_plies = {}
                        ply_idx = 0
                        for move in game.mainline_moves():
                            piece = board.piece_at(move.from_square)
                            board.push(move)
                            ply_idx += 1
                            if piece:
                                color_char = "w" if piece.color == chess.WHITE else "b"
                                piece_char = piece.symbol().lower()
                                code = f"{color_char}{piece_char}"
                                move_num = (ply_idx + 1) // 2
                                if code not in piece_plies:
                                    piece_plies[code] = set()
                                piece_plies[code].add(move_num)

                        ply_count = ply_idx if ply_idx > 0 else (20 + (idx * 5) % 60)

                        loaded_games.append({
                            "headers": headers,
                            "ply_count": ply_count,
                            "game_object": game,
                            "piece_plies": piece_plies,
                        })
                        idx += 1
            else:
                con = duckdb.connect(str(self.db_path), read_only=True)
                tables = con.execute("SHOW TABLES").fetchall()
                table_names = [t[0] for t in tables]

                if "catalog_headers" in table_names:
                    rows = con.execute("SELECT headers_json FROM catalog_headers").fetchall()
                    for r in rows:
                        try:
                            h_dict = json.loads(r[0])
                            ply_count_str = h_dict.get("PlyCount", h_dict.get("TotalPlies", "30"))
                            try:
                                ply_count = int(ply_count_str)
                            except ValueError:
                                ply_count = 30

                            dummy_game = chess.pgn.Game()
                            for k, v in h_dict.items():
                                dummy_game.headers[k] = v

                            loaded_games.append({
                                "headers": h_dict,
                                "ply_count": ply_count,
                                "game_object": dummy_game,
                                "piece_plies": {},
                            })
                        except Exception:
                            pass
                con.close()
        except Exception as e:
            print(f"Error reading pattern games: {e}")

        try:
            self.after(0, lambda: self._finalize_game_load(loaded_games))
        except Exception:
            pass

    def _finalize_game_load(self, loaded_games):
        if not self.winfo_exists():
            return

        self.all_games_cache = loaded_games
        set_status_message(f"Patterns catalog loaded: {len(loaded_games)} games.")
        self.recalculate_tiers()