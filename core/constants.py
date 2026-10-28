import json
from pathlib import Path

# Robust root directory detection
ROOT_DIR = Path(__file__).resolve().parent
while ROOT_DIR != ROOT_DIR.parent:
    if (ROOT_DIR / "main.py").exists() or (ROOT_DIR / "core").exists():
        break
    ROOT_DIR = ROOT_DIR.parent

USER_THEMES_FILE = ROOT_DIR / "user_themes.json"
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
    "pattern_yellow": "#ffd700",
    "light_square": "#f0d9b5",
    "dark_square": "#b58863"
}


def load_theme():
    theme_data = DEFAULT_THEME.copy()

    last_hue = "Red"
    last_tier = "Medium"
    custom_themes = {}

    if USER_THEMES_FILE.exists():
        try:
            with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                user_data = json.load(f)
                if isinstance(user_data, dict):
                    last_hue = user_data.get("last_active_hue", "Red")
                    last_tier = user_data.get("last_active_tier", "Medium")
                    custom_themes = user_data.get("custom_themes", {})
        except Exception as e:
            print(f"[THEME] Error reading user_themes metadata: {e}")

    # 1. Load absolute base defaults from theme_defaults.json first
    defaults_tier_dict = {}
    if DEFAULTS_FILE.exists():
        try:
            with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
                all_defaults = json.load(f)
                if last_hue in all_defaults and last_tier in all_defaults[last_hue]:
                    defaults_tier_dict = all_defaults[last_hue][last_tier]
                    if isinstance(defaults_tier_dict, dict):
                        for k, v in defaults_tier_dict.items():
                            if v is not None and str(v).strip() != "":
                                theme_data[k] = v
        except Exception as e:
            print(f"[THEME] Error loading defaults from {DEFAULTS_FILE}: {e}")

    # 2. Overlay user customs key-by-key; if a key is explicitly blank/empty, fall back to theme_defaults.json
    if last_hue in custom_themes and last_tier in custom_themes[last_hue]:
        user_tier_data = custom_themes[last_hue][last_tier]
        if isinstance(user_tier_data, dict):
            for k in theme_data.keys():
                if k in user_tier_data:
                    val = user_tier_data[k]
                    if val is not None and str(val).strip() != "":
                        theme_data[k] = val
                    elif k in defaults_tier_dict and defaults_tier_dict[k]:
                        theme_data[k] = defaults_tier_dict[k]

    return theme_data


THEME = load_theme()

LAYOUT = {
    "square_size": 47,
    "board_width": 510,
    "board_height": 425,
    "pv_box_height": 120,
    "analysis_box_height": 90,
}