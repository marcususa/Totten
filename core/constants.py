import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "theme_override.json"

# Complete fallback theme containing every required key
DEFAULT_THEME = {
    "bg_panel": "#172134",
    "bg_surface": "#1e293b",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "status_text": "#ddddff",
    "border_color": "#344268",
    "divider": "#344268",
    "border_ring": "#344268",
    "progress_bg": "#0f172a",
    "progress_fill": "#ff0000",
    "btn_initial": "#344268",
    "btn_hover": "#2e4a8c",
    "btn_active": "#344268",
    "btn_bg": "#344268",
    "active_tracker_bg": "#2e4a8c",
    "active_tracker_fg": "#ffffff",
    "eval_red": "#de3d35",
    "eval_red_bg": "#4a1f1f",
    "eval_orange": "#FFA500",
    "eval_orange_bg": "#4a331f",
    "eval_green": "#1fa73b",
    "eval_green_bg": "#00FF00",
    "eval_light_blue": "#31a0ef",
    "eval_light_blue_bg": "#1f3852",
    "eval_default": "#adc3dc",
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
    "square_size": 47,
    "board_width": 510,
    "board_height": 425,
    "pv_box_height": 120,
    "analysis_box_height": 90,
}