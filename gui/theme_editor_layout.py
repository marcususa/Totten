# theme_editor_layout.py
import json
import sys
import os
from pathlib import Path
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import colorsys

ROOT_DIR = Path(__file__).resolve().parent
while ROOT_DIR != ROOT_DIR.parent:
    if (ROOT_DIR / "main.py").exists() or (ROOT_DIR / "core").exists():
        break
    ROOT_DIR = ROOT_DIR.parent

DEFAULTS_FILE = ROOT_DIR / "theme_defaults.json"
USER_THEMES_FILE = ROOT_DIR / "user_themes.json"

try:
    with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
        THEME_DEFAULTS = json.load(f)
except Exception as e:
    print(f"[THEME EDITOR] Error loading {DEFAULTS_FILE}: {e}")
    THEME_DEFAULTS = {}


class ThemeEditorWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Theme Editor")
        self.geometry("520x780")
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#363636")

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 780) // 2
        self.geometry(f"520x780+{x}+{y}")

        self.color_inputs = {}
        self.swatch_buttons = {}
        self.active_entry = None

        self.current_hue = 0.0
        self.current_sat = 0.85
        self.current_val = 0.95

        # 1. Start with clean defaults
        self.active_themes = json.loads(json.dumps(THEME_DEFAULTS))
        self.last_active_hue_loaded = None
        self.last_active_tier_loaded = "Medium"

        # 2. Immediately overlay user_themes.json so saved edits appear on startup/refresh
        if USER_THEMES_FILE.exists():
            try:
                with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                    u_data = json.load(f)
                    if isinstance(u_data, dict):
                        if "custom_themes" in u_data and isinstance(u_data["custom_themes"], dict):
                            for hue_key, hue_val in u_data["custom_themes"].items():
                                self.active_themes[hue_key] = hue_val

                        if "last_active_hue" in u_data:
                            self.last_active_hue_loaded = u_data["last_active_hue"]
                        if "last_active_tier" in u_data:
                            self.last_active_tier_loaded = u_data["last_active_tier"]
            except Exception as e:
                print(f"[THEME EDITOR] Error loading {USER_THEMES_FILE}: {e}")

        detected_hue, detected_tier = self.detect_active_hue()
        self.detected_tier = detected_tier

        self.hue_names = list(self.active_themes.keys())
        initial_hue = detected_hue if detected_hue in self.hue_names else (
            self.last_active_hue_loaded if self.last_active_hue_loaded in self.hue_names else (
                "Red" if "Red" in self.hue_names else self.hue_names[0]
            )
        )
        self.selected_hue_var = ctk.StringVar(value=initial_hue)
        self.last_selected_hue = initial_hue

        initial_tier = detected_tier if detected_tier in ["Light", "Medium", "Dark"] else (
            self.last_active_tier_loaded if self.last_active_tier_loaded in ["Light", "Medium", "Dark"] else "Medium"
        )
        self.selected_tier_var = ctk.StringVar(value=initial_tier)
        self.last_selected_tier = initial_tier

        main_frame = ctk.CTkFrame(self, fg_color="#363636", corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        inner_frame = ctk.CTkFrame(main_frame, fg_color="#363636", corner_radius=0)
        inner_frame.pack(fill="both", expand=True, padx=15, pady=15)

        top_bar = ctk.CTkFrame(inner_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        self.hue_menu = ctk.CTkOptionMenu(
            top_bar, values=self.hue_names,
            variable=self.selected_hue_var,
            command=self.on_hue_selected,
            fg_color="#1e3a8a", button_color="#1e3a8a", button_hover_color="#172554",
            dropdown_fg_color="#2b2b2b", dropdown_hover_color="#1e3a8a",
            width=130
        )
        self.hue_menu.pack(side="left", padx=(0, 6), pady=0)

        self.tier_menu = ctk.CTkOptionMenu(
            top_bar, values=["Light", "Medium", "Dark"],
            variable=self.selected_tier_var,
            command=self.on_tier_selected,
            fg_color="#1e3a8a", button_color="#1e3a8a", button_hover_color="#172554",
            dropdown_fg_color="#2b2b2b", dropdown_hover_color="#1e3a8a",
            width=100
        )
        self.tier_menu.pack(side="left", padx=0, pady=0)

        ctk.CTkButton(
            top_bar, text="Cancel", width=70, height=28,
            fg_color="#1e3a8a", hover_color="#172554",
            command=self.destroy
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            top_bar, text="Save", width=70, height=28,
            fg_color="#1e3a8a", hover_color="#172554",
            command=self.save_user_themes
        ).pack(side="right")

        self.content_container = ctk.CTkFrame(inner_frame, fg_color="transparent")
        self.content_container.pack(fill="both", expand=True, pady=(0, 10))

        bottom_frame = ctk.CTkFrame(inner_frame, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(0, 0))

        preview_bar = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        preview_bar.pack(fill="x", pady=(0, 8))

        preview_border = ctk.CTkFrame(preview_bar, fg_color="#000000", corner_radius=6, width=38, height=38)
        preview_border.pack(side="left", padx=(0, 8))
        preview_border.pack_propagate(False)

        self.large_preview = ctk.CTkButton(
            preview_border, text="", width=32, height=32,
            fg_color="#3b82f6", hover_color="#3b82f6", corner_radius=4,
            state="disabled"
        )
        self.large_preview.pack(padx=3, pady=3)

        self.hex_display_lbl = ctk.CTkLabel(
            preview_bar, text="Hex: #3b82f6",
            font=("Consolas", 12, "bold")
        )
        self.hex_display_lbl.pack(side="left", padx=(0, 15))

        ctk.CTkButton(
            preview_bar, text="Change", width=80, height=26,
            fg_color="#1e3a8a", hover_color="#172554",
            command=self.apply_preview_to_active
        ).pack(side="left")

        # Saturation Slider Bar
        saturation_bar = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        saturation_bar.pack(fill="x", pady=(0, 4))

        ctk.CTkLabel(saturation_bar, text="Saturation:", font=("Arial", 11)).pack(side="left", padx=(0, 10))

        self.saturation_slider = ctk.CTkSlider(
            saturation_bar, from_=0.0, to=1.0, number_of_steps=100,
            command=self.on_saturation_changed
        )
        self.saturation_slider.set(self.current_sat)
        self.saturation_slider.pack(side="left", fill="x", expand=True)

        # Brightness Slider Bar
        brightness_bar = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        brightness_bar.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(brightness_bar, text="Brightness:", font=("Arial", 11)).pack(side="left", padx=(0, 10))

        self.brightness_slider = ctk.CTkSlider(
            brightness_bar, from_=0.1, to=1.0, number_of_steps=100,
            command=self.on_brightness_changed
        )
        self.brightness_slider.set(self.current_val)
        self.brightness_slider.pack(side="left", fill="x", expand=True)

        self.spectrum_canvas = tk.Canvas(bottom_frame, height=28, bg="#121212", highlightthickness=1,
                                         highlightbackground="#333333")
        self.spectrum_canvas.pack(fill="x", expand=True, padx=2)
        self.spectrum_canvas.bind("<Configure>", self.draw_color_spectrum)
        self.spectrum_canvas.bind("<Button-1>", self.pick_color_from_spectrum)
        self.spectrum_canvas.bind("<B1-Motion>", self.pick_color_from_spectrum)

        self.build_editor_grid(initial_hue)

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


# Bind view and controller methods to ThemeEditorWindow
from gui.theme_editor_view import (
    draw_color_spectrum, pick_color_from_spectrum, on_saturation_changed,
    on_brightness_changed, update_preview_from_hsv, set_active_entry,
    validate_hex_input, update_swatch_live, build_editor_grid
)
from gui.theme_editor_controller import (
    apply_preview_to_active, on_hue_selected,
    on_tier_selected, sync_current_view_to_memory, save_user_themes
)

for method in [
    draw_color_spectrum, pick_color_from_spectrum, on_saturation_changed,
    on_brightness_changed, update_preview_from_hsv, set_active_entry,
    validate_hex_input, update_swatch_live, build_editor_grid,
    apply_preview_to_active, on_hue_selected,
    on_tier_selected, sync_current_view_to_memory, save_user_themes
]:
    setattr(ThemeEditorWindow, method.__name__, method)