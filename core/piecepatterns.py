# core/piecepatterns.py

import os
import duckdb


def get_pattern_catalog_connection():
    """Connects directly to the standalone patterns.duckdb file in the project root."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    db_path = os.path.join(project_root, "patterns.duckdb")

    return duckdb.connect(db_path)


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
            WHERE color = ? OR color = 'BOTH'
            ORDER BY tier ASC, id ASC, sequence_order ASC;
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