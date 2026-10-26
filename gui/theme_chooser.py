import colorsys
import json
import sys
import os
from pathlib import Path
import customtkinter as ctk

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = ROOT_DIR / "theme_override.json"

try:
    from core.constants import THEME
except ImportError:
    THEME = {}

THEME_GRID_DATA = {
    "Red": {"Light": "#fca5a5", "Medium": "#ef4444", "Dark": "#991b1b"},
    "Orange": {"Light": "#fed7aa", "Medium": "#f97316", "Dark": None},
    "Green": {"Light": "#bbf7d0", "Medium": "#22c55e", "Dark": "#166534"},
    "Blue": {"Light": "#bae6fd", "Medium": "#3b82f6", "Dark": "#1e3a8a"},
    "Purple": {"Light": "#e9d5ff", "Medium": "#a855f7", "Dark": "#581c87"},
    "Brown": {"Light": "#f5d0fe", "Medium": "#b45309", "Dark": "#451a03"},
    "Black": {"Light": "#cbd5e1", "Medium": "#475569", "Dark": "#0f172a"},
    "Pink": {"Light": "#fbcfe8", "Medium": "#ec4899", "Dark": None},
    "Yellow": {"Light": "#fef08a", "Medium": "#eab308", "Dark": None}
}


def hex_to_rgb(hex_str):
    hex_str = hex_str.lstrip('#')
    return tuple(int(hex_str[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(rgb):
    return '#{:02x}{:02x}{:02x}'.format(
        max(0, min(255, int(rgb[0] * 255))),
        max(0, min(255, int(rgb[1] * 255))),
        max(0, min(255, int(rgb[2] * 255)))
    )


def generate_complete_palette(hue_name, tier_key, base_hex):
    r, g, b = hex_to_rgb(base_hex)
    h, l, s = colorsys.rgb_to_hls(r, g, b)

    if tier_key == "Light":
        bg_panel = rgb_to_hex(colorsys.hls_to_rgb(h, min(0.96, l * 1.25), s * 0.4))
        bg_surface = rgb_to_hex(colorsys.hls_to_rgb(h, min(0.92, l * 1.15), s * 0.5))
        text_primary = "#0f172a"
        text_secondary = "#334155"
        status_text = "#1e293b"
        border_color = rgb_to_hex(colorsys.hls_to_rgb(h, max(0.70, l * 0.85), s))
    elif tier_key == "Medium":
        if hue_name in ["Orange", "Yellow"]:
            text_primary = "#0f172a"
            text_secondary = "#334155"
        else:
            text_primary = "#ffffff"
            text_secondary = "#cbd5e1"
        bg_panel = rgb_to_hex(colorsys.hls_to_rgb(h, max(0.20, l * 0.5), s))
        bg_surface = rgb_to_hex(colorsys.hls_to_rgb(h, max(0.26, l * 0.6), s))
        status_text = "#ddddff"
        border_color = base_hex
    else:
        text_primary = "#ffffff"
        text_secondary = "#94a3b8"
        status_text = "#ddddff"
        bg_panel = rgb_to_hex(colorsys.hls_to_rgb(h, max(0.10, l * 0.35), s))
        bg_surface = rgb_to_hex(colorsys.hls_to_rgb(h, max(0.15, l * 0.45), s))
        border_color = base_hex

    btn_initial = base_hex
    btn_hover = rgb_to_hex(colorsys.hls_to_rgb(h, min(1.0, l * 1.15), s))

    return {
        "bg_panel": bg_panel,
        "bg_surface": bg_surface,
        "btn_hover": btn_hover,
        "btn_initial": btn_initial,
        "btn_bg": btn_initial,
        "text_primary": text_primary,
        "text_secondary": text_secondary,
        "status_text": status_text,
        "border_color": border_color,
        "divider": border_color,
        "border_ring": border_color,
        "progress_bg": bg_surface,
        "progress_fill": base_hex,
        "eval_red": "#de3d35",
        "eval_red_bg": "#4a1f1f",
        "eval_orange": "#FFA500",
        "eval_orange_bg": "#4a331f",
        "eval_green": "#1fa73b",
        "eval_green_bg": "#00FF00",
        "eval_light_blue": "#31a0ef",
        "eval_light_blue_bg": "#1f3852",
        "eval_default": "#adc3dc",
        "pattern_yellow": base_hex if hue_name == "Yellow" else "#ffd700",
        "active_tracker_bg": btn_hover,
        "active_tracker_fg": text_primary
    }


class ThemeChooserWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Theme Chooser")
        self.geometry("360x420")
        self.resizable(False, False)
        self.attributes("-topmost", True)

        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(anchor="w", pady=(0, 10))

        ctk.CTkLabel(
            header_frame, text="Theme Chooser ",
            font=("Arial", 16, "bold")
        ).pack(side="left")

        ctk.CTkLabel(
            header_frame, text="(click color)",
            font=("Arial", 13, "normal")
        ).pack(side="left")

        grid_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        grid_container.pack(fill="both", expand=True)

        grid_container.grid_columnconfigure(0, weight=2)
        grid_container.grid_columnconfigure(1, weight=1)
        grid_container.grid_columnconfigure(2, weight=1)
        grid_container.grid_columnconfigure(3, weight=1)

        row_idx = 0
        for hue_name, tiers in THEME_GRID_DATA.items():
            ctk.CTkLabel(
                grid_container, text=hue_name,
                font=("Arial", 12, "bold")
            ).grid(row=row_idx, column=0, sticky="w", padx=5, pady=4)

            for col_offset, tier_key in enumerate(["Light", "Medium", "Dark"], start=1):
                hex_val = tiers.get(tier_key)

                if hex_val:
                    swatch = ctk.CTkButton(
                        grid_container, text="", width=45, height=24,
                        fg_color=hex_val,
                        hover_color=hex_val,
                        corner_radius=4,
                        command=lambda h=hue_name, t=tier_key, v=hex_val: self.apply_theme_live(h, t, v)
                    )
                    swatch.grid(row=row_idx, column=col_offset, padx=4, pady=4)
                else:
                    lbl = ctk.CTkLabel(
                        grid_container, text="—",
                        font=("Arial", 11), text_color="gray"
                    )
                    lbl.grid(row=row_idx, column=col_offset, padx=4, pady=4)

            row_idx += 1

    def apply_theme_live(self, hue, tier, hex_val):
        # 1. Generate new palette
        new_palette = generate_complete_palette(hue, tier, hex_val)

        # 2. Save to persistent override json file
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_palette, f, indent=4)
        except Exception as e:
            print(f"[THEME] Error saving theme override: {e}")

        print(f"[THEME] Applied {hue} ({tier}). Restarting application...")

        # 3. Cleanly restart the Python process to refresh all modules, variables, and lists instantly
        python = sys.executable
        os.execv(python, [python] + sys.argv)