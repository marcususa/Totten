import json
from pathlib import Path
import chess.pgn
import duckdb

DB_Path = Path("personal_catalog.duckdb")
PGN_Path = Path("personal_catalog.pgn")
JSON_Path = Path("personal_catalog.json")


def get_header(headers, key, default="Unknown"):
    if not headers:
        return default
    if key in headers:
        return headers[key]
    lower_key = key.lower()
    for k, v in headers.items():
        if k.lower() == lower_key:
            return v
    return default


def catalog_pgns(filename):
    """
    Parses a PGN file and appends its games directly into DuckDB and personal_catalog.pgn.
    """
    path_to_import = Path(filename)
    if not path_to_import.exists():
        return 0

    con = duckdb.connect(str(DB_Path))
    con.execute("""
                CREATE TABLE IF NOT EXISTS catalog_headers
                (
                    game_index
                    INTEGER,
                    eco
                    VARCHAR,
                    opening
                    VARCHAR,
                    variation
                    VARCHAR,
                    white
                    VARCHAR,
                    black
                    VARCHAR,
                    headers_json
                    VARCHAR
                )
                """)

    # Get current max index to append properly
    max_idx_res = con.execute("SELECT MAX(game_index) FROM catalog_headers").fetchone()
    start_idx = (max_idx_res[0] + 1) if max_idx_res and max_idx_res[0] is not None else 0

    added_count = 0
    games_to_insert = []

    with open(path_to_import, "r", encoding="utf-8", errors="replace") as f_in, \
            open(PGN_Path, "a", encoding="utf-8") as f_out:

        while True:
            game = chess.pgn.read_game(f_in)
            if game is None:
                break

            # Export game string back to permanent pgn file for lazy-loading boards later if needed
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
            pgn_string = game.accept(exporter)
            f_out.write(pgn_string + "\n\n")

            headers = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in game.headers.items()}
            eco = get_header(headers, "ECO", "A00")
            opening = get_header(headers, "Opening", "Unknown")
            variation = get_header(headers, "Variation", "")
            white = get_header(headers, "White", "Unknown")
            black = get_header(headers, "Black", "Unknown")

            current_idx = start_idx + added_count
            games_to_insert.append((
                current_idx,
                eco,
                opening,
                variation,
                white,
                black,
                json.dumps(headers)
            ))
            added_count += 1

    # Batch insert into DuckDB
    if games_to_insert:
        con.executemany("""
                        INSERT INTO catalog_headers (game_index, eco, opening, variation, white, black, headers_json)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, games_to_insert)

    con.close()
    print(f"[Catalog Builder] Successfully ingested {added_count} games into DuckDB.")
    return added_count