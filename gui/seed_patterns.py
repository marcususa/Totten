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

def seed_patterns_database():
    db_path = "patterns.duckdb"
    conn = duckdb.connect(db_path)
    
    # Ensure the table schema matches our optimized structure
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pattern_checklist (
            id INTEGER,
            color VARCHAR,
            tier INTEGER,
            target_square VARCHAR,
            sequence_order INTEGER
        );
    """)
    
    # Clear existing entries to prevent duplication if run multiple times
    conn.execute("DELETE FROM pattern_checklist;")
    
    pattern_id = 1
    
    def insert_group(patterns, color_code):
        nonlocal pattern_id
        for pattern_str, tier in patterns:
            # Split comma-separated multi-move sequences into distinct steps
            moves = [m.strip() for m in pattern_str.split(",")]
            for seq_idx, move in enumerate(moves, start=1):
                conn.execute("""
                    INSERT INTO pattern_checklist (id, color, tier, target_square, sequence_order)
                    VALUES (?, ?, ?, ?, ?)
                """, [pattern_id, color_code, tier, move, seq_idx])
            pattern_id += 1

    # Insert groups with corresponding color codes ('W', 'B', 'BOTH')
    insert_group(RAW_WHITE_PATTERNS, 'W')
    insert_group(RAW_BLACK_PATTERNS, 'B')
    insert_group(RAW_BOTH_PATTERNS, 'BOTH')
    
    conn.close()
    print("Successfully initialized and seeded patterns.duckdb!")

if __name__ == "__main__":
    seed_patterns_database()