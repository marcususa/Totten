import json
import os
from pathlib import Path
import gui.app_state as state


def clear_catalog():
    """Completely deletes personal_catalog.json, personal_catalog.pgn, and personal_catalog.duckdb off disk, resets memory, clears UI treeviews, and resets status bar."""

    current_file = Path(__file__).resolve()
    print(f"[DEBUG] catalog_manager.py location: {current_file}")

    root_candidate_1 = current_file.parent.parent.parent
    root_candidate_2 = current_file.parent.parent
    root_candidate_3 = Path.cwd()

    print(f"[DEBUG] Candidate 1 (.parent.parent.parent): {root_candidate_1}")
    print(f"[DEBUG] Candidate 2 (.parent.parent): {root_candidate_2}")
    print(f"[DEBUG] Candidate 3 (cwd): {root_candidate_3}")

    target_root = root_candidate_1 if (root_candidate_1 / "main.py").exists() else (
        root_candidate_2 if (root_candidate_2 / "main.py").exists() else root_candidate_3
    )
    print(f"[DEBUG] Resolved active root directory: {target_root}")

    catalog_duckdb_path = target_root / "personal_catalog.duckdb"
    catalog_pgn_path = target_root / "personal_catalog.pgn"
    catalog_json_path = target_root / "personal_catalog.json"

    targets = [
        (catalog_duckdb_path, "DuckDB file"),
        (catalog_json_path, "JSON metadata"),
        (catalog_pgn_path, "PGN file")
    ]

    for file_path, label in targets:
        print(f"[DEBUG] Checking {label} at {file_path} -> Exists: {file_path.exists()}")

    try:
        import duckdb
        try:
            duckdb.sql("CLOSE DATABASE").fetchall()
        except Exception:
            pass
        if hasattr(duckdb, "default_connection") and duckdb.default_connection:
            duckdb.default_connection.close()
        import gc
        gc.collect()
    except Exception as e:
        print(f"[DEBUG] DuckDB close note: {e}")

    for file_path, label in targets:
        if file_path.exists():
            try:
                os.remove(file_path)
                print(f"[{label}] Successfully deleted: {file_path}")
            except Exception as e:
                print(f"Error deleting [{label}] {file_path}: {e}")
                if "pgn" in str(file_path):
                    try:
                        with open(file_path, "w", encoding="utf-8") as f:
                            f.write("")
                    except Exception:
                        pass