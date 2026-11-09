import sys
import json
import os
import shutil
from pathlib import Path
import core.constants as const

ROOT_DIR = Path(__file__).resolve().parent.parent

DEFAULTS_FILE = ROOT_DIR / "theme_defaults.json"
USER_THEMES_FILE = ROOT_DIR / "user_themes.json"


def load_all_themes():
    """Loads master defaults from theme_defaults.json and overlays custom editor themes."""
    defaults = {}
    if DEFAULTS_FILE.exists():
        try:
            with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
                defaults = json.load(f)
        except Exception as e:
            print(f"[THEME] Error loading {DEFAULTS_FILE}: {e}")

    themes = json.loads(json.dumps(defaults))

    if USER_THEMES_FILE.exists():
        try:
            with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                u_data = json.load(f)
                if isinstance(u_data, dict):
                    custom_dict = u_data.get("custom_themes", {})
                    if isinstance(custom_dict, dict) and custom_dict:
                        for hue_key, hue_val in custom_dict.items():
                            themes[hue_key] = hue_val
        except Exception as e:
            print(f"[THEME] Error loading custom themes from {USER_THEMES_FILE}: {e}")

    return themes


def load_user_data():
    """Loads user_themes.json safely."""
    if USER_THEMES_FILE.exists():
        try:
            with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_user_data(data):
    """Safely writes dictionary data to user_themes.json while preserving existing keys."""
    existing = load_user_data()
    if isinstance(existing, dict) and isinstance(data, dict):
        existing.update(data)
        data_to_save = existing
    else:
        data_to_save = data

    try:
        with open(USER_THEMES_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        print(f"[THEME] Error saving user data: {e}")


def get_active_theme_dict():
    """Single source of truth for the active 26-variable theme dictionary."""
    user_data = load_user_data()
    if "active_theme" in user_data and isinstance(user_data["active_theme"], dict):
        return user_data["active_theme"]

    defaults = load_all_themes()
    return defaults.get("Purple", {}).get("Medium", {})


def apply_and_save_theme(theme_dict, entry_metadata=None):
    """
    Centralized function used by BOTH chooser and editor.
    Saves the 26-var dictionary as active and triggers an app restart.
    """
    user_data = load_user_data()
    user_data["active_theme"] = theme_dict

    if entry_metadata:
        themes_list = user_data.get("current_themes", [])
        themes_list.insert(0, entry_metadata)
        if len(themes_list) > 10:
            themes_list = themes_list[:10]
        user_data["current_themes"] = themes_list

    save_user_data(user_data)
    os.execv(sys.executable, [sys.executable] + sys.argv)


def reload_global_theme():
    """Updates core.constants.THEME in-place with the current active theme."""
    active_dict = get_active_theme_dict()
    if active_dict:
        const.THEME.update(active_dict)


def handle_board_background_upload(file_path):
    if not file_path:
        return
    try:
        src_path = Path(file_path)
        ext = src_path.suffix.lower()
        for existing_ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
            old_file = ROOT_DIR / f"board_background{existing_ext}"
            if old_file.exists():
                old_file.unlink()
        dest_path = ROOT_DIR / f"board_background{ext}"
        shutil.copy2(src_path, dest_path)
        user_data = load_user_data()
        user_data["board_bg_image"] = str(dest_path.name)
        save_user_data(user_data)
    except Exception as e:
        print(f"[THEME] Error copying board background image: {e}")


def handle_remove_board_background():
    try:
        for existing_ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
            old_file = ROOT_DIR / f"board_background{existing_ext}"
            if old_file.exists():
                old_file.unlink()
        user_data = load_user_data()
        if "board_bg_image" in user_data:
            del user_data["board_bg_image"]
        save_user_data(user_data)
    except Exception as e:
        print(f"[THEME] Error removing board background: {e}")