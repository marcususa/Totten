import json
import sys
import os
from pathlib import Path
import customtkinter as ctk

# Robustly locate the actual project root directory
ROOT_DIR = Path(__file__).resolve().parent
while ROOT_DIR != ROOT_DIR.parent:
    if (ROOT_DIR / "main.py").exists() or (ROOT_DIR / "core").exists():
        break
    ROOT_DIR = ROOT_DIR.parent

DEFAULTS_FILE = ROOT_DIR / "theme_defaults.json"
CONFIG_FILE = ROOT_DIR / "theme_override.json"

# Load static defaults directly from JSON
try:
    with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
        THEME_DEFAULTS = json.load(f)
except Exception as e:
    print(f"[THEME] Error loading {DEFAULTS_FILE}: {e}")
    THEME_DEFAULTS = {}


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
        tier_keys = ["Light", "Medium", "Dark"]

        for hue_name, tiers in THEME_DEFAULTS.items():
            ctk.CTkLabel(
                grid_container, text=hue_name,
                font=("Arial", 12, "bold")
            ).grid(row=row_idx, column=0, sticky="w", padx=5, pady=4)

            for col_offset, tier_key in enumerate(tier_keys, start=1):
                tier_data = tiers.get(tier_key)

                if tier_data and isinstance(tier_data, dict):
                    # Use btn_initial color for the swatch preview button
                    swatch_color = tier_data.get("btn_initial", "#3b82f6")

                    swatch = ctk.CTkButton(
                        grid_container, text="", width=45, height=24,
                        fg_color=swatch_color,
                        hover_color=swatch_color,
                        corner_radius=4,
                        command=lambda h=hue_name, t=tier_key, d=tier_data: self.apply_theme_live(h, t, d)
                    )
                    swatch.grid(row=row_idx, column=col_offset, padx=4, pady=4)
                else:
                    lbl = ctk.CTkLabel(
                        grid_container, text="—",
                        font=("Arial", 11), text_color="gray"
                    )
                    lbl.grid(row=row_idx, column=col_offset, padx=4, pady=4)

            row_idx += 1

    def apply_theme_live(self, hue, tier, palette_dict):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(palette_dict, f, indent=4)
            print(f"[THEME] Saved static palette for {hue} ({tier}) to {CONFIG_FILE}")
        except Exception as e:
            print(f"[THEME] Error saving theme override: {e}")
            return

        print(f"[THEME] Restarting application...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)