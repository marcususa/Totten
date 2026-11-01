import json
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
while ROOT_DIR != ROOT_DIR.parent:
    if (ROOT_DIR / "main.py").exists() or (ROOT_DIR / "core").exists():
        break
    ROOT_DIR = ROOT_DIR.parent

USER_THEMES_FILE = ROOT_DIR / "user_themes.json"
DEFAULTS_FILE = ROOT_DIR / "theme_defaults.json"

DEFAULT_THEME = {
    "bg_panel": "#591010",
    "bg_surface": "#7f1d1d",
    "text_primary": "#ffffff",
    "text_secondary": "#aa4e58",
    "status_text": "#ddddff",
    "border_color": "#ef4444",
    "divider": "#ef4444",
    "border_ring": "#ef4444",
    "progress_bg": "#7f1d1d",
    "progress_fill": "#ffffff",
    "btn_initial": "#951f1f",
    "btn_hover": "#d52020",
    "btn_active": "#dc2626",
    "active_tracker_bg": "#b91c1c",
    "active_tracker_fg": "#ffffff",
    "eval_red": "#de3d35",
    "eval_red_bg": "#4a1f1f",
    "eval_orange": "#FFA500",
    "eval_orange_bg": "#4a331f",
    "eval_green": "#1fa73b",
    "eval_green_bg": "#00FF00",
    "eval_light_blue": "#31a0ef",
    "eval_light_blue_bg": "#1f3852",
    "eval_default": "#fca5a5",
    "pattern_yellow": "#ffd700",
    "light_square": "#993333",
    "dark_square": "#591010"
}


def load_theme():
    theme_data = DEFAULT_THEME.copy()

    if USER_THEMES_FILE.exists():
        try:
            with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                user_data = json.load(f)
                if isinstance(user_data, dict):
                    active_block = user_data.get("active_theme")
                    if active_block and isinstance(active_block, dict):
                        theme_data.update(active_block)
                        return theme_data

                    legacy_block = user_data.get("custom_mixed_theme")
                    if legacy_block and isinstance(legacy_block, dict):
                        theme_data.update(legacy_block)
                        return theme_data
        except Exception as e:
            print(f"[THEME] Error reading user_themes: {e}")

    if DEFAULTS_FILE.exists():
        try:
            with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
                all_defaults = json.load(f)
                if "Yellow" in all_defaults and "Dark" in all_defaults["Yellow"]:
                    theme_data.update(all_defaults["Yellow"]["Dark"])
        except Exception as e:
            print(f"[THEME] Error loading defaults from {DEFAULTS_FILE}: {e}")

    return theme_data


THEME = load_theme()

LAYOUT = {
    "square_size": 47,
    "board_width": 510,
    "board_height": 425,
    "pv_box_height": 120,
    "analysis_box_height": 90,
}