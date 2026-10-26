import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "theme_override.json"

# Layout & Dimension Constants
LAYOUT = {
    "square_size": 47,
    "board_width": 510,
    "board_height": 425,
    "pv_box_height": 120,
    "analysis_box_height": 90,
}

# Default Theme Template
DEFAULT_THEME = {
    "bg_panel": "#172134",
    "bg_surface": "#1e293b",
    "btn_hover": "#2e4a8c",
    "btn_initial": "#344268",
    "btn_bg": "#344268",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "status_text": "#ddddff",
    "border_color": "#344268",
    "divider": "#344268",
    "border_ring": "#334155",
    "progress_bg": "#0f172a",
    "progress_fill": "#ff0000",
    "eval_red": "#de3d35",
    "eval_red_bg": "#4a1f1f",
    "eval_orange": "#FFA500",
    "eval_orange_bg": "#4a331f",
    "eval_green": "#1fa73b",
    "eval_green_bg": "#00FF00",
    "eval_light_blue": "#31a0ef",
    "eval_light_blue_bg": "#1f3852",
    "eval_default": "#adc3dc",
    "pattern_yellow": "#ffd700",
    "active_tracker_bg": "#2e4a8c",
    "active_tracker_fg": "#ffffff"
}

# Load saved overrides if they exist, otherwise fallback to default
if CONFIG_FILE.exists():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            THEME = json.load(f)
            # Ensure border_ring is never blindingly bright/yellow if loaded from an old config
            if THEME.get("border_ring") in ["#ffd700", "#fef08a", "#facc15"]:
                THEME["border_ring"] = "#334155"
    except Exception:
        THEME = DEFAULT_THEME.copy()
else:
    THEME = DEFAULT_THEME.copy()