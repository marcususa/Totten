import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "theme_override.json"

# Complete fallback theme containing every required key
DEFAULT_THEME = {
    "bg_panel": "#7f1d1d",
    "bg_surface": "#991b1b",
    "text_primary": "#ef4444",
    "text_secondary": "#fca5a5",
    "status_text": "#ddddff",
    "border_color": "#ef4444",
    "divider": "#ef4444",
    "border_ring": "#ef4444",
    "progress_bg": "#991b1b",
    "progress_fill": "#ffffff",
    "btn_initial": "#ef4444",
    "btn_hover": "#dc2626",
    "btn_active": "#ef4444",
    "btn_bg": "#ef4444",
    "active_tracker_bg": "#dc2626",
    "active_tracker_fg": "#ffffff",
    "eval_red": "#de3d35",
    "eval_red_bg": "#4a1f1f",
    "eval_orange": "#FFA500",
    "eval_orange_bg": "#4a331f",
    "eval_green": "#1fa73b",
    "eval_green_bg": "#00FF00",
    "eval_light_blue": "#7dd3fc",
    "eval_light_blue_bg": "#082f49",
    "eval_default": "#fca5a5",
    "pattern_yellow": "#ffd700"
}

def load_theme():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    merged = DEFAULT_THEME.copy()
                    merged.update(data)
                    return merged
        except Exception:
            pass
    return DEFAULT_THEME

THEME = load_theme()

LAYOUT = {
    "padding": 5,
    "margin": 5,
    "corner_radius": 6,
    "board_width": 480,
    "board_height": 480,
    "square_size": 60,
    "pv_box_height": 150,
    "analysis_box_height": 200
}