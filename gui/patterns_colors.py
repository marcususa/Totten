# gui/patterns/patterns_colors.py

import chess

# 1-3-5 Material Values Setup
PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}

# Workspace Theme & Color Assignments
WORKSPACE_BG = "#172134"
TOOLBAR_BG = "#1e293b"
TOOLBAR_BORDER = "#334155"

TIER_THEMES = {
    "tier1": {
        "bg": "#143322",
        "border": "#22543d",
        "fg": "#6ee7b7",
    },
    "tier2": {
        "bg": "#38250d",
        "border": "#78350f",
        "fg": "#fcd34d",
    },
    "tier3": {
        "bg": "#3a1c1c",
        "border": "#7f1d1d",
        "fg": "#fca5a5",
    },
}