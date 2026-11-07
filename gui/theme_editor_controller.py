# theme_editor_controller.py
import json
import os
import sys
import colorsys
from gui.theme_editor_layout import USER_THEMES_FILE, THEME_DEFAULTS


def detect_active_hue(self):
    if not USER_THEMES_FILE.exists():
        return None, "Medium"
    try:
        with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
            user_data = json.load(f)
            if isinstance(user_data, dict) and "last_active_hue" in user_data:
                return user_data["last_active_hue"], user_data.get("last_active_tier", "Medium")
    except Exception as e:
        print(f"[THEME EDITOR] Error detecting active hue: {e}")
    return None, "Medium"


def apply_preview_to_active(self):
    if not self.active_entry:
        return
    r, g, b = colorsys.hsv_to_rgb(self.current_hue / 360.0, self.current_sat, self.current_val)
    hex_color = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    # 1. Update the active entry box text
    try:
        self.active_entry.delete(0, "end")
        self.active_entry.insert(0, hex_color)
    except Exception:
        pass

    # 2. Match the entry to its grid coordinate key and update the swatch button directly
    hue = self.selected_hue_var.get()
    tier = self.selected_tier_var.get()

    if hue not in self.active_themes:
        self.active_themes[hue] = {}
    if tier not in self.active_themes[hue]:
        self.active_themes[hue][tier] = {}

    target_key = None
    for coord_key, entry_widget in self.color_inputs.items():
        if entry_widget == self.active_entry:
            target_key = coord_key
            break

    if target_key:
        # coord_key is (tier_key, prop)
        _, prop = target_key
        self.active_themes[hue][tier][prop] = hex_color

        if target_key in self.swatch_buttons:
            try:
                self.swatch_buttons[target_key].configure(fg_color=hex_color, hover_color=hex_color)
            except Exception:
                pass

    self.sync_current_view_to_memory()


def on_hue_selected(self, new_hue):
    self.sync_current_view_to_memory()
    self.last_selected_hue = new_hue
    self.build_editor_grid(new_hue)


def on_tier_selected(self, new_tier):
    self.sync_current_view_to_memory()
    self.last_selected_tier = new_tier
    self.build_editor_grid(self.selected_hue_var.get())


def sync_current_view_to_memory(self):
    hue = self.selected_hue_var.get()

    if hue not in self.active_themes:
        self.active_themes[hue] = {}

    for coord_key, entry in self.color_inputs.items():
        if isinstance(coord_key, tuple) and len(coord_key) == 2:
            tier_key, key = coord_key
        else:
            tier_key = self.selected_tier_var.get()
            key = coord_key

        if tier_key not in self.active_themes[hue]:
            self.active_themes[hue][tier_key] = {}

        if entry and hasattr(entry, "get"):
            try:
                val = entry.get().strip()
                if val.startswith("#") and len(val) in (4, 7):
                    self.active_themes[hue][tier_key][key] = val
            except Exception:
                pass


def save_user_themes(self):
    """Saves current theme customizations to user_themes.json and restarts the app to apply changes instantly."""
    self.sync_current_view_to_memory()

    # Load existing user_themes.json first to avoid wiping out mixer_state or current_themes
    existing_data = {}
    if USER_THEMES_FILE.exists():
        try:
            with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            pass

    # Update or merge fields safely
    existing_data["custom_themes"] = self.active_themes
    existing_data["last_active_hue"] = self.selected_hue_var.get() if hasattr(self, "selected_hue_var") else "Red"
    existing_data["last_active_tier"] = self.selected_tier_var.get() if hasattr(self, "selected_tier_var") else "Medium"

    try:
        with open(USER_THEMES_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        print(f"[THEME EDITOR] Successfully saved user themes to {USER_THEMES_FILE}")
    except Exception as e:
        print(f"[THEME EDITOR] Error saving to {USER_THEMES_FILE}: {e}")

    # Close the editor window
    try:
        self.destroy()
    except Exception:
        pass

    # Trigger application restart to instantly apply updated themes everywhere
    print("[THEME] Restarting application to apply theme edits...")
    os.execv(sys.executable, [sys.executable] + sys.argv)