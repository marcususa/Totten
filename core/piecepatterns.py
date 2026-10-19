# core/piecepatterns.py

from core.patterns_db import WHITE_PATTERNS, BLACK_PATTERNS, BOTH_PATTERNS


def fetch_patterns_by_color(color_code: str, target_piece: str = None):
    """
    Returns a formatted string of patterns for the specified color
    pulled directly from the hardcoded core.patterns_db lists.
    """
    clean_code = str(color_code).strip().upper()

    if clean_code.startswith("W"):
        raw_list = WHITE_PATTERNS + BOTH_PATTERNS
        display_color = "WHITE"
    elif clean_code.startswith("B"):
        raw_list = BLACK_PATTERNS + BOTH_PATTERNS
        display_color = "BLACK"
    else:
        raw_list = WHITE_PATTERNS + BLACK_PATTERNS + BOTH_PATTERNS
        display_color = clean_code

    formatted_lines = [f"=== {display_color} PATTERNS (Target: {target_piece or 'All'}) ==="]

    pattern_id = 1
    for pattern_str, tier in raw_list:
        # Optional filter if a target piece is specified (e.g. 'N' for knight, 'B' for bishop)
        if target_piece:
            if not pattern_str.lower().startswith(target_piece.lower()):
                continue

        formatted_lines.append(f"• Pattern {pattern_id} | Tier {tier} | Sequence: {pattern_str}")
        pattern_id += 1

    if len(formatted_lines) == 1:
        return f"No checklist patterns found for {display_color} (Piece: {target_piece or 'All'})\n"

    return "\n".join(formatted_lines) + "\n"