# theme_editor_view.py
import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import colorsys

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
        r, g, b = colorsys.hsv_to_rgb(hue / 360.0, 0.75, 0.90)
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

def on_saturation_changed(self, val):
    self.current_sat = float(val)
    self.update_preview_from_hsv()

def on_brightness_changed(self, val):
    self.current_val = float(val)
    self.update_preview_from_hsv()

def update_preview_from_hsv(self):
    r, g, b = colorsys.hsv_to_rgb(self.current_hue / 360.0, self.current_sat, self.current_val)
    hex_val = f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"
    self.large_preview.configure(fg_color=hex_val, hover_color=hex_val)
    self.hex_display_lbl.configure(text=f"Hex: {hex_val}")

def set_active_entry(self, entry_widget, color_val):
    self.active_entry = entry_widget
    current_val = entry_widget.get().strip()
    if not current_val and hasattr(entry_widget, "cget") and entry_widget.cget("placeholder_text"):
        current_val = entry_widget.cget("placeholder_text")
    if current_val and not current_val.startswith("#"):
        current_val = "#" + current_val
    if len(current_val) == 7:
        color_val = current_val

    try:
        hx = color_val.lstrip("#")
        rgb = tuple(int(hx[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
        h, s, v = colorsys.rgb_to_hsv(*rgb)
        self.current_hue = h * 360.0
        self.current_sat = s
        self.current_val = v
        self.saturation_slider.set(self.current_sat)
        self.brightness_slider.set(self.current_val)
    except Exception:
        pass

    self.large_preview.configure(fg_color=color_val, hover_color=color_val)
    self.hex_display_lbl.configure(text=f"Hex: {color_val}")

def validate_hex_input(self, proposed_text):
    if len(proposed_text) > 7:
        return False
    return True

def update_swatch_live(self, swatch_btn, entry_widget, default_val):
    text = entry_widget.get().strip()
    if text and not text.startswith("#"):
        text = "#" + text

    if not text:
        swatch_btn.configure(fg_color=default_val, hover_color=default_val)
    elif text.startswith("#") and len(text) == 7:
        try:
            swatch_btn.configure(fg_color=text, hover_color=text)
        except Exception:
            pass

def build_editor_grid(self, hue_name):
    for widget in self.content_container.winfo_children():
        widget.destroy()

    self.color_inputs.clear()
    self.swatch_buttons.clear()
    self.active_entry = None

    active_tier = self.selected_tier_var.get()

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

            default_val = self.THEME_DEFAULTS.get(hue_name, {}).get(tier_key, {}).get(prop, "#3b82f6") if hasattr(self, 'THEME_DEFAULTS') else "#3b82f6"
            display_val = val if val is not None and str(val).strip() != "" else ""
            initial_color = display_val if display_val.startswith("#") else default_val

            swatch_border = ctk.CTkFrame(cell_frame, fg_color="#000000", corner_radius=4)
            swatch_border.pack(side="left", padx=(0, 4), pady=1)

            swatch = ctk.CTkButton(
                swatch_border, text="", width=20, height=16,
                fg_color=initial_color,
                hover_color=initial_color,
                corner_radius=2,
                state="disabled"
            )
            swatch.pack(padx=1, pady=1)

            is_active_tier = (tier_key == active_tier)

            vcmd = (self.register(self.validate_hex_input), '%P') if is_active_tier else None
            entry = ctk.CTkEntry(
                cell_frame, width=75, height=22,
                font=("Consolas", 11),
                validate='key' if is_active_tier else 'none',
                validatecommand=vcmd,
                placeholder_text=str(default_val)
            )
            entry.insert(0, str(display_val))
            entry.pack(side="left")

            if is_active_tier:
                entry.bind("<FocusIn>", lambda e, en=entry, col=initial_color: self.set_active_entry(en, col))
                entry.bind("<KeyRelease>", lambda e, s=swatch, en=entry, d_val=default_val: self.update_swatch_live(s, en, d_val))
            else:
                entry.bind("<Key>", lambda e: "break")

            # Store mappings using standard keys so controller lookups succeed cleanly
            self.color_inputs[(tier_key, prop)] = entry
            self.swatch_buttons[(tier_key, prop)] = swatch

            if is_active_tier and self.active_entry is None:
                self.active_entry = entry
                self.set_active_entry(entry, initial_color)

        row_idx += 1