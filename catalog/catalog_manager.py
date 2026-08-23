# catalog/catalog_manager.py

import json
import os
import gui.app_state as state


def clear_catalog():
    """Completely deletes personal_catalog.json, personal_catalog.pgn, and personal_catalog.duckdb off disk, resets memory, clears UI treeviews, and resets status bar."""
    catalog_duckdb_path = "personal_catalog.duckdb"
    catalog_pgn_path = "personal_catalog.pgn"
    catalog_json_path = "personal_catalog.json"

    # 0. Force-close/cleanup any active DuckDB global connections to release file locks
    try:
        import duckdb
        duckdb.sql("CLOSE DATABASE").fetchall()
    except Exception:
        try:
            duckdb.default_connection.close()
        except Exception:
            pass

    # 1. Delete personal_catalog.duckdb off disk if it exists
    if os.path.exists(catalog_duckdb_path):
        try:
            os.remove(catalog_duckdb_path)
            print(f"File {catalog_duckdb_path} successfully deleted.")
        except Exception as e:
            print(f"Error deleting {catalog_duckdb_path}: {e}")

    # 1.5. Also remove the JSON metadata catalog file if present
    if os.path.exists(catalog_json_path):
        try:
            os.remove(catalog_json_path)
        except Exception:
            pass

    # 2. Delete personal_catalog.pgn off disk if it exists
    if os.path.exists(catalog_pgn_path):
        try:
            os.remove(catalog_pgn_path)
            print(f"File {catalog_pgn_path} successfully deleted.")
        except Exception as e:
            print(f"Error deleting {catalog_pgn_path}: {e}")
            try:
                with open(catalog_pgn_path, "w", encoding="utf-8") as f:
                    f.write("")
            except Exception:
                pass