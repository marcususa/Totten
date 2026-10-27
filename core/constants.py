import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "theme_override.json"
DEFAULTS_FILE = ROOT_DIR / "theme_defaults.json"

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
    "btn_hover": "#475569",
    "btn_active": "#344268",
    "btn_bg": "#344268",
    "active_tracker_bg": "#475569",
    "active_tracker_fg": "#ffffff",
    "eval_red": "#de3d35",
    "eval_red_bg": "#4a1f1f",
    "eval_orange": "#FFA500",
    "eval_orange_bg": "#4a331f",
    "eval_green": "#1fa73b",
    "eval_green_bg": "#00FF00",
    "eval_light_blue": "#fed7aa",
    "eval_light_blue_bg": "#4a331f",
    "eval_default": "#ffedd5",
    "pattern_yellow": "#ffd700"
}


def load_theme():
    theme_data = DEFAULT_THEME.copy()

    # 1. Try loading override config first
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    theme_data.update(data)
        except Exception:
            pass
    elif DEFAULTS_FILE.exists():
        # Fallback to checking defaults if override doesn't exist
        try:
            with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
                all_defaults = json.load(f)
                if "Orange" in all_defaults:
                    theme_data.update(all_defaults["Orange"].get("Medium", {}))
        except Exception:
            pass

    return theme_data


THEME = load_theme()

LAYOUT = {
    "square_size": 47,
    "board_width": 510,
    "board_height": 425,
    "pv_box_height": 120,
    "analysis_box_height": 90,
}