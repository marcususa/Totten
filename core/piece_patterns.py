# core/piece_patterns.py

import os
import duckdb

# Raw pattern definitions grouped by color context
RAW_WHITE_PATTERNS = [
    ("f3", 1), ("f4", 1), ("g4", 1),
    ("h3, g4", 1),
    ("Bb4, Bb5", 1), ("Bb5, Bb4", 1), ("Bb5, Ba4", 1),
    ("Bf1", 1), ("Bg5, Bh4", 1), ("Bxh6", 1),
    ("Nb5", 1), ("Nc3, Ne2, Ng3", 1),
    ("Nxd5", 1), ("Nxe5", 1), ("Nh2", 1),
    ("Ra2", 1), ("Rb1", 1),
    ("Qb3", 1), ("Qe2", 1), ("Kf1", 1)
]

RAW_BLACK_PATTERNS = [
    ("f6", 1), ("f5", 1), ("g5", 1),
    ("h6, g5", 1),
    ("Ba6, Ba7", 1), ("Bc5, Bb6", 1),
    ("Bf8", 1), ("Bh3", 1),
    ("Na5", 1), ("Nc6, Ne7, Ng3", 1),
    ("Nxd4", 1), ("Nxe4", 1),
    ("Ra7", 1), ("Rb8", 1),
    ("Qb6", 1), ("Qe7", 1), ("Kf7", 1)
]

RAW_BOTH_PATTERNS = [
    ("Be3, Bc5", 1),
    ("Bc4, Be6", 1)
]


def get_pattern_catalog_connection():
    """Connects directly to the standalone patterns.duckdb file in the project root."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, "patterns.duckdb")
    return duckdb.connect(db_path)


def seed_patterns_database():
    """Automatically creates and seeds the pattern_checklist table."""
    conn = get_pattern_catalog_connection()
    try:
        conn.execute("""
                     CREATE TABLE IF NOT EXISTS pattern_checklist
                     (
                         id
                         INTEGER,
                         color
                         VARCHAR,
                         tier
                         INTEGER,
                         target_square
                         VARCHAR,
                         sequence_order
                         INTEGER
                     );
                     """)

        # Clear existing entries to prevent duplication if run multiple times
        conn.execute("DELETE FROM pattern_checklist;")

        pattern_id = 1

        def insert_group(patterns, color_code):
            nonlocal pattern_id
            for pattern_str, tier in patterns:
                moves = [m.strip() for m in pattern_str.split(",")]
                for seq_idx, move in enumerate(moves, start=1):
                    conn.execute("""
                                 INSERT INTO pattern_checklist (id, color, tier, target_square, sequence_order)
                                 VALUES (?, ?, ?, ?, ?)
                                 """, [pattern_id, color_code, tier, move, seq_idx])
                pattern_id += 1

        insert_group(RAW_WHITE_PATTERNS, 'W')
        insert_group(RAW_BLACK_PATTERNS, 'B')
        insert_group(RAW_BOTH_PATTERNS, 'BOTH')

        print("Successfully initialized and seeded patterns.duckdb!")
    finally:
        conn.close()


def fetch_patterns_by_color(color_code: str, target_piece: str = None):
    """
    Queries the pattern_checklist table from patterns.duckdb.
    Normalizes color input ('white'/'black' -> 'W'/'B') and fetches records
    matching the specified color as well as any universal 'BOTH' records,
    optionally contextualized by the active target piece.
    """
    clean_code = str(color_code).strip().upper()
    if clean_code.startswith("W"):
        db_color = "W"
    elif clean_code.startswith("B"):
        db_color = "B"
    else:
        db_color = clean_code

    conn = get_pattern_catalog_connection()
    try:
        query = """
                SELECT id, color, tier, target_square, sequence_order
                FROM pattern_checklist
                WHERE color = ? \
                   OR color = 'BOTH'
                ORDER BY tier ASC, id ASC, sequence_order ASC; \
                """
        results = conn.execute(query, [db_color]).fetchall()

        if not results:
            return f"No checklist patterns found for {color_code.capitalize()} (Piece: {target_piece or 'All'})\n"

        formatted_lines = [f"=== {color_code.upper()} PATTERNS (Target: {target_piece or 'All'}) ==="]
        for row in results:
            p_id, p_color, tier, target_sq, seq_ord = row
            formatted_lines.append(f"• Pattern {p_id} | Tier {tier} | Square: {target_sq} | Seq: {seq_ord}")

        return "\n".join(formatted_lines) + "\n"
    finally:
        conn.close()