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
CONFIG_FILE = ROOT_DIR / "theme_override.json"

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
        self.geometry("520x740")
        self.resizable(True, True)
        self.attributes("-topmost", True)
        self.configure(fg_color="#363636")

        self.update_idletasks()
        x = (self.winfo_screenwidth() - 520) // 2
        y = (self.winfo_screenheight() - 740) // 2
        self.geometry(f"520x740+{x}+{y}")

        self.color_inputs = {}
        self.swatch_buttons = {}
        self.active_entry = None

        self.current_hue = 0.0
        self.current_sat = 1.0
        self.current_val = 1.0

        self.active_themes = json.loads(json.dumps(THEME_DEFAULTS))
        if USER_THEMES_FILE.exists():
            try:
                with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                    u_data = json.load(f)
                    if "custom_themes" in u_data and isinstance(u_data["custom_themes"], dict):
                        self.active_themes.update(u_data["custom_themes"])
            except Exception as e:
                print(f"[THEME EDITOR] Error loading {USER_THEMES_FILE}: {e}")

        detected_hue, detected_tier = self.detect_active_hue()
        self.detected_tier = detected_tier

        self.hue_names = list(self.active_themes.keys())
        initial_hue = detected_hue if detected_hue in self.hue_names else (
            "Red" if "Red" in self.hue_names else self.hue_names[0])
        self.selected_hue_var = ctk.StringVar(value=initial_hue)
        self.last_selected_hue = initial_hue

        main_frame = ctk.CTkFrame(self, fg_color="#363636", corner_radius=0)
        main_frame.pack(fill="both", expand=True, padx=0, pady=0)

        inner_frame = ctk.CTkFrame(main_frame, fg_color="#363636", corner_radius=0)
        inner_frame.pack(fill="both", expand=True, padx=15, pady=15)

        top_bar = ctk.CTkFrame(inner_frame, fg_color="transparent")
        top_bar.pack(fill="x", pady=(0, 10))

        # Option menu packed directly without border frame
        self.hue_menu = ctk.CTkOptionMenu(
            top_bar, values=self.hue_names,
            variable=self.selected_hue_var,
            command=self.on_hue_selected,
            fg_color="#1e3a8a", button_color="#1e3a8a", button_hover_color="#172554",
            dropdown_fg_color="#2b2b2b", dropdown_hover_color="#1e3a8a",
            width=140
        )
        self.hue_menu.pack(side="left", padx=0, pady=0)

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

        brightness_bar = ctk.CTkFrame(bottom_frame, fg_color="transparent")
        brightness_bar.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(brightness_bar, text="Brightness:", font=("Arial", 11)).pack(side="left", padx=(0, 10))

        self.brightness_slider = ctk.CTkSlider(
            brightness_bar, from_=0.0, to=1.0, number_of_steps=100,
            command=self.on_brightness_changed
        )
        self.brightness_slider.set(1.0)
        self.brightness_slider.pack(side="left", fill="x", expand=True)

        self.spectrum_canvas = tk.Canvas(bottom_frame, height=28, bg="#121212", highlightthickness=1,
                                         highlightbackground="#333333")
        self.spectrum_canvas.pack(fill="x", expand=True, padx=2)
        self.spectrum_canvas.bind("<Configure>", self.draw_color_spectrum)
        self.spectrum_canvas.bind("<Button-1>", self.pick_color_from_spectrum)
        self.spectrum_canvas.bind("<B1-Motion>", self.pick_color_from_spectrum)

        self.build_editor_grid(initial_hue)

    def detect_active_hue(self):
        if not CONFIG_FILE.exists():
            return None, "Medium"
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                current_override = json.load(f)
                if not isinstance(current_override, dict):
                    return None, "Medium"
                for hue_name, tiers in self.active_themes.items():
                    for tier_key, tier_data in tiers.items():
                        if isinstance(tier_data, dict):
                            if current_override.get("bg_panel") == tier_data.get("bg_panel"):
                                return hue_name, tier_key
        except Exception as e:
            print(f"[THEME EDITOR] Error detecting active hue: {e}")
        return None, "Medium"

    def draw_color_spectrum(self, event=None):
        self.spectrum_canvas.delete("gradient")
        width = self.spectrum_canvas.winfo_width()
        height = self.spectrum_canvas.winfo_height()
        if width < 10:
            width = 400

        img = Image.new("RGB", (width, height))
        pixels = img.load()

        for x in range(width):
            hue = x / width * 360
            r, g, b = colorsys.hsv_to_rgb(hue / 360.0, 1.0, 1.0)
            rgb_val = (int(r * 255), int(g * 255), int(b * 255))
            for y in range(height):
                pixels[x, y] = rgb_val

        self.spectrum_image = ImageTk.PhotoImage(img)
        self.spectrum_canvas.create_image(0, 0, anchor="nw", image=self.spectrum_image, tags="gradient")

    def pick_color_from_spectrum(self, event):
        width = self.spectrum_canvas.winfo_width()
        if width < 1:
            return
        x = max(0, min(event.x, width - 1))
        self.current_hue = (x / width) * 360
        self.update_preview_from_hsv()

    def on_brightness_changed(self, val):
        self.current_val = float(val)
        self.update_preview_from_hsv()

    def update_preview_from_hsv(self):
        r, g, b = colorsys.hsv_to_rgb(self.current_hue / 360.0, self.current_sat, self.current_val)
        hex_val = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
        self.large_preview.configure(fg_color=hex_val, hover_color=hex_val)
        self.hex_display_lbl.configure(text=f"Hex: {hex_val}")

    def apply_preview_to_active(self):
        if self.active_entry:
            r, g, b = colorsys.hsv_to_rgb(self.current_hue / 360.0, self.current_sat, self.current_val)
            hex_val = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
            try:
                self.active_entry.delete(0, "end")
                self.active_entry.insert(0, hex_val)
                if self.active_entry in self.swatch_buttons:
                    self.swatch_buttons[self.active_entry].configure(fg_color=hex_val, hover_color=hex_val)
            except Exception as e:
                print(f"[THEME EDITOR] Error applying preview: {e}")

    def on_hue_selected(self, hue_name):
        if hue_name == self.last_selected_hue:
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirm Hue Switch")
        dialog.geometry("380x140")
        dialog.resizable(False, False)
        dialog.attributes("-topmost", True)
        dialog.configure(fg_color="#363636")

        dialog.update_idletasks()
        dx = self.winfo_x() + (self.winfo_width() - 380) // 2
        dy = self.winfo_y() + (self.winfo_height() - 140) // 2
        dialog.geometry(f"380x140+{dx}+{dy}")

        msg_lbl = ctk.CTkLabel(
            dialog,
            text=f"You are switching to {hue_name},\nbut you are currently editing {self.last_selected_hue}.\nContinue?",
            font=("Arial", 12),
            justify="center"
        )
        msg_lbl.pack(pady=(15, 15))

        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20)

        def on_cancel():
            self.selected_hue_var.set(self.last_selected_hue)
            dialog.destroy()

        def on_confirm():
            dialog.destroy()
            self.sync_current_view_to_memory()
            self.last_selected_hue = hue_name
            self.write_override_file(hue_name)
            self.build_editor_grid(hue_name)

        ctk.CTkButton(
            btn_frame, text="Cancel", width=100, height=28,
            fg_color="#1e3a8a", hover_color="#172554",
            command=on_cancel
        ).pack(side="left", padx=(10, 20))

        ctk.CTkButton(
            btn_frame, text="Continue", width=100, height=28,
            fg_color="#1e3a8a", hover_color="#172554",
            command=on_confirm
        ).pack(side="right", padx=(20, 10))

    def sync_current_view_to_memory(self):
        current_hue = self.last_selected_hue
        if current_hue in self.active_themes:
            for (tier_key, prop), entry in self.color_inputs.items():
                val = entry.get().strip()
                if not val.startswith("#") and len(val) > 0:
                    val = "#" + val
                if tier_key in self.active_themes[current_hue]:
                    self.active_themes[current_hue][tier_key][prop] = val

    def write_override_file(self, hue_name):
        active_tier = getattr(self, "detected_tier", "Medium")
        palette_to_save = {}
        if hue_name in self.active_themes and active_tier in self.active_themes[hue_name]:
            palette_to_save = dict(self.active_themes[hue_name][active_tier])

        for tier_key in ["Light", "Medium", "Dark"]:
            tier_data = self.active_themes.get(hue_name, {}).get(tier_key, {})
            if isinstance(tier_data, dict):
                for prop, val in tier_data.items():
                    if tier_key == active_tier:
                        palette_to_save[prop] = val
                    else:
                        palette_to_save[f"{tier_key.lower()}_{prop}"] = val

        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(palette_to_save, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            print(f"[THEME EDITOR] Successfully updated override to {CONFIG_FILE} for {hue_name}")
        except Exception as e:
            print(f"[THEME EDITOR] Error saving override to {CONFIG_FILE}: {e}")

    def build_editor_grid(self, hue_name):
        for widget in self.content_container.winfo_children():
            widget.destroy()

        self.color_inputs.clear()
        self.swatch_buttons.clear()
        self.active_entry = None

        scroll_container = ctk.CTkScrollableFrame(self.content_container, fg_color="transparent")
        scroll_container.pack(fill="both", expand=True)

        scroll_container.grid_columnconfigure(0, weight=2)
        scroll_container.grid_columnconfigure(1, weight=1)
        scroll_container.grid_columnconfigure(2, weight=1)
        scroll_container.grid_columnconfigure(3, weight=1)

        tier_keys = ["Light", "Medium", "Dark"]
        row_idx = 0

        ctk.CTkLabel(scroll_container, text="Property", font=("Arial", 11, "bold")).grid(row=row_idx, column=0,
                                                                                         sticky="w", padx=5, pady=4)
        for col_idx, tier_name in enumerate(tier_keys, start=1):
            ctk.CTkLabel(scroll_container, text=tier_name, font=("Arial", 11, "bold")).grid(row=row_idx, column=col_idx,
                                                                                            sticky="w", padx=5, pady=4)
        row_idx += 1

        tiers = self.active_themes.get(hue_name, {})
        all_props = set()
        for tier_key in tier_keys:
            t_data = tiers.get(tier_key, {})
            if isinstance(t_data, dict):
                all_props.update(t_data.keys())

        for prop in sorted(all_props):
            ctk.CTkLabel(
                scroll_container, text=prop,
                font=("Arial", 11)
            ).grid(row=row_idx, column=0, sticky="w", padx=(5, 5), pady=3)

            for col_offset, tier_key in enumerate(tier_keys, start=1):
                tier_data = tiers.get(tier_key, {})
                val = tier_data.get(prop, "") if isinstance(tier_data, dict) else ""

                cell_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
                cell_frame.grid(row=row_idx, column=col_offset, padx=2, pady=3, sticky="w")

                if val:
                    initial_color = val if str(val).startswith("#") else "#3b82f6"

                    swatch_border = ctk.CTkFrame(cell_frame, fg_color="#000000", corner_radius=4)
                    swatch_border.pack(side="left", padx=(0, 4), pady=1)

                    swatch = ctk.CTkButton(
                        swatch_border, text="", width=20, height=16,
                        fg_color=initial_color, hover_color=initial_color, corner_radius=2,
                        state="disabled"
                    )
                    swatch.pack(padx=1, pady=1)

                    vcmd = (self.register(self.validate_hex_input), '%P')
                    entry = ctk.CTkEntry(
                        cell_frame, width=75, height=22,
                        font=("Consolas", 11),
                        validate='key', validatecommand=vcmd
                    )
                    entry.insert(0, str(val))
                    entry.pack(side="left")

                    entry.bind("<FocusIn>", lambda e, en=entry, col=initial_color: self.set_active_entry(en, col))
                    entry.bind("<KeyRelease>", lambda e, s=swatch, en=entry: self.update_swatch_live(s, en))

                    self.color_inputs[(tier_key, prop)] = entry
                    self.swatch_buttons[entry] = swatch

                    if self.active_entry is None:
                        self.active_entry = entry
                        self.set_active_entry(entry, initial_color)
                else:
                    ctk.CTkLabel(cell_frame, text="—", font=("Arial", 10), text_color="gray").pack(side="left")

            row_idx += 1

    def set_active_entry(self, entry_widget, color_val):
        self.active_entry = entry_widget
        current_val = entry_widget.get().strip()
        if not current_val.startswith("#") and len(current_val) > 0:
            current_val = "#" + current_val
        if len(current_val) == 7:
            color_val = current_val

        try:
            hx = color_val.lstrip("#")
            rgb = tuple(int(hx[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
            h, s, v = colorsys.rgb_to_hsv(*rgb)
            self.current_hue = h * 360.0
            self.current_sat = s
            if s > 0.05:
                self.current_val = v
            self.brightness_slider.set(self.current_val)
        except Exception:
            pass

        self.large_preview.configure(fg_color=color_val, hover_color=color_val)
        self.hex_display_lbl.configure(text=f"Hex: {color_val}")

    def validate_hex_input(self, proposed_text):
        if len(proposed_text) > 7:
            return False
        return True

    def update_swatch_live(self, swatch_btn, entry_widget):
        text = entry_widget.get().strip()
        if not text.startswith("#") and len(text) > 0:
            text = "#" + text

        if text.startswith("#") and len(text) == 7:
            try:
                swatch_btn.configure(fg_color=text, hover_color=text)
            except Exception:
                pass

    def save_user_themes(self):
        self.sync_current_view_to_memory()
        current_hue = self.last_selected_hue

        # 1. Save all custom edits to user_themes.json with forced OS disk flush
        try:
            user_data = {}
            if USER_THEMES_FILE.exists():
                with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                    user_data = json.load(f)

            user_data["custom_themes"] = self.active_themes

            with open(USER_THEMES_FILE, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
            print(f"[THEME EDITOR] Saved all custom themes to {USER_THEMES_FILE}")
        except Exception as e:
            print(f"[THEME EDITOR] Error saving to {USER_THEMES_FILE}: {e}")

        # 2. Update theme_override.json with current active settings
        self.write_override_file(current_hue)

        print(f"[THEME EDITOR] Restarting application...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)