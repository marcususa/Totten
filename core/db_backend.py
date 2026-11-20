from pathlib import Path
import sqlite3
import subprocess
import sys


def _can_import_duckdb() -> bool:
    try:
        res = subprocess.run(
            [sys.executable, "-c", "import duckdb"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
        return res.returncode == 0
    except Exception:
        return False


USE_DUCKDB = _can_import_duckdb()

if USE_DUCKDB:
    import duckdb  # type: ignore


class _SQLiteConnWrapper:
    """Makes sqlite3 connections behave identically to duckdb connections."""
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is None:
            self._conn.commit()
        else:
            self._conn.rollback()
        self._conn.close()

    def execute(self, sql: str, params=()):
        return self._conn.execute(sql, params)

    def executemany(self, sql: str, seq_of_params):
        return self._conn.executemany(sql, seq_of_params)

    def close(self):
        self._conn.commit()
        self._conn.close()


def get_db_path(root_dir: Path | str = ".") -> Path:
    ext = "duckdb" if USE_DUCKDB else "sqlite3"
    return Path(root_dir) / f"personal_catalog.{ext}"


def connect_db(db_path: Path | str, read_only: bool = False):
    path_str = str(db_path)
    if USE_DUCKDB:
        return duckdb.connect(path_str, read_only=read_only)
    if read_only:
        uri = f"{Path(path_str).resolve().as_uri()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    else:
        conn = sqlite3.connect(path_str, check_same_thread=False)
    return _SQLiteConnWrapper(conn)


def table_exists(conn, table_name: str) -> bool:
    if USE_DUCKDB:
        res = conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()
    else:
        res = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name = ?",
            (table_name,),
        ).fetchone()
    return res is not None
