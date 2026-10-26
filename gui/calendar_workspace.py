import json
from datetime import datetime
import os
import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
import customtkinter as ctk

from core.constants import THEME

# Path to store timeline notes locally
NOTES_FILE = "calendar_notes.json"


def _get_balanced_button_color(hex_str, factor=0.82):
    """Returns a rich, saturated darker variant that avoids looking gray for light purple/pastels."""
    clean_hex = hex_str.lstrip('#')
    try:
        r, g, b = int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16)
        nr, ng, nb = int(r * factor), int(g * factor), int(b * factor)
        return f"#{max(0, min(255, nr)):02x}{max(0, min(255, ng)):02x}{max(0, min(255, nb)):02x}"
    except Exception:
        return hex_str


def _get_darker_shade(hex_str, factor=0.50):
    """Returns a deep rich shade for calendar selection background so it is never too bright."""
    clean_hex = hex_str.lstrip('#')
    try:
        r, g, b = int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16)
        nr, ng, nb = int(r * factor), int(g * factor), int(b * factor)
        return f"#{max(0, min(255, nr)):02x}{max(0, min(255, ng)):02x}{max(0, min(255, nb)):02x}"
    except Exception:
        return hex_str


def _get_dynamic_text_color(hex_str):
    """Computes high-contrast text color (dark or white) based on button background luminance."""
    clean_hex = hex_str.lstrip('#')
    try:
        r, g, b = int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        return "#0f172a" if luminance > 0.5 else "#ffffff"
    except Exception:
        return THEME.get("text_primary", "#ffffff")


class CalendarWorkspace(ctk.CTkFrame):

    def __init__(self, parent, app_state=None):
        super().__init__(
            parent,
            fg_color=THEME.get("bg_panel", "#172134"),
            corner_radius=0
        )
        self.app_state = app_state

        self.notes_data = self.load_notes()

        # Configure grid layout: Left side Calendar, Right side Timeline/Journal Entry
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- Left Pane: Calendar Widget & Navigation ---
        self.left_frame = ctk.CTkFrame(
            self,
            fg_color=THEME.get("bg_surface", "#1f2c42"),
            corner_radius=8,
            border_width=1,
            border_color=THEME.get("border_color", "#2a3b59")
        )
        self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.left_frame.grid_rowconfigure(1, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        self.title_label = ctk.CTkLabel(
            self.left_frame,
            text="Timeline Chronicle",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME.get("text_primary", "#ffffff"),
        )
        self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Calendar widget using tkcalendar styled with active theme colors
        cal_bg = THEME.get("bg_panel", "#172134")
        cal_fg = THEME.get("text_primary", "#ffffff")
        cal_surface = THEME.get("bg_surface", "#1f2c42")

        base_btn_color = THEME.get("btn_initial", "#1f538d")
        cal_select_bg = _get_darker_shade(base_btn_color, 0.50)
        cal_muted = THEME.get("text_secondary", "#94a3b8")

        self.cal = Calendar(
            self.left_frame,
            selectmode="day",
            year=datetime.now().year,
            month=datetime.now().month,
            day=datetime.now().day,
            font=("Arial", 12),
            background=cal_bg,
            foreground=cal_fg,
            selectbackground=cal_select_bg,
            selectforeground="#ffffff",
            bordercolor=cal_surface,
            headersbackground=cal_surface,
            headersforeground=cal_fg,
            normalbackground=cal_bg,
            normalforeground=cal_fg,
            weekendbackground=cal_bg,
            weekendforeground=cal_fg,
            othermonthbackground=cal_surface,
            othermonthforeground=cal_muted,
            othermonthwebackground=cal_surface,
            othermonthweforeground=cal_muted,
        )
        self.cal.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
        self.cal.bind("<<CalendarSelected>>", self.on_date_select)

        # Quick Jump Bar
        self.jump_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
        self.jump_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")

        balanced_btn = _get_balanced_button_color(base_btn_color, 0.82)
        balanced_hover = _get_balanced_button_color(base_btn_color, 0.70)

        self.btn_today = ctk.CTkButton(
            self.jump_frame,
            text="Jump to Today",
            command=self.jump_to_today,
            fg_color=balanced_btn,
            hover_color=balanced_hover,
            text_color=_get_dynamic_text_color(balanced_btn)
        )
        self.btn_today.pack(fill="x", pady=(0, 5))

        # --- Right Pane: Entry & Context View ---
        self.right_frame = ctk.CTkFrame(
            self,
            fg_color=THEME.get("bg_surface", "#1f2c42"),
            corner_radius=8,
            border_width=1,
            border_color=THEME.get("border_color", "#2a3b59")
        )
        self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.right_frame.grid_rowconfigure(2, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)

        # Selected Date Header
        self.date_header = ctk.CTkLabel(
            self.right_frame,
            text="",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=THEME.get("text_primary", "#ffffff"),
            anchor="w",
        )
        self.date_header.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")

        self.sub_header = ctk.CTkLabel(
            self.right_frame,
            text=(
                "Note the past, live the present, map the future. (Add food,"
                " music, or thoughts here...)"
            ),
            font=ctk.CTkFont(size=12, slant="italic"),
            text_color=THEME.get("text_secondary", "#94a3b8"),
            anchor="w",
        )
        self.sub_header.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        # Text Area for Free-form Timeline Notes
        self.text_entry = ctk.CTkTextbox(
            self.right_frame,
            wrap="word",
            font=("Arial", 14),
            fg_color=THEME.get("bg_panel", "#172134"),
            text_color=THEME.get("text_primary", "#ffffff"),
            border_color=THEME.get("border_color", "#2a3b59"),
            border_width=1
        )
        self.text_entry.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")

        # Save Button
        self.btn_save = ctk.CTkButton(
            self.right_frame,
            text="Save Timeline Entry",
            fg_color=balanced_btn,
            hover_color=balanced_hover,
            text_color=_get_dynamic_text_color(balanced_btn),
            command=self.save_current_entry,
        )
        self.btn_save.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="e")

        # Initialize view with today's date selection
        self.update_date_display()

    def load_notes(self):
        if os.path.exists(NOTES_FILE):
            try:
                with open(NOTES_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_notes_to_disk(self):
        try:
            with open(NOTES_FILE, "w") as f:
                json.dump(self.notes_data, f, indent=4)
        except Exception as e:
            messagebox.showerror("Error", f"Could not save timeline data: {e}")

    def get_selected_date_str(self):
        date_obj = self.cal.selection_get()
        return date_obj.strftime("%Y-%m-%d")

    def on_date_select(self, event=None):
        self.update_date_display()

    def update_date_display(self):
        date_str = self.get_selected_date_str()
        display_title = (
            f"Timeline Entry: {self.cal.selection_get().strftime('%B %d, %Y')}"
        )
        self.date_header.configure(text=display_title)

        self.text_entry.delete("1.0", "end")
        if date_str in self.notes_data:
            self.text_entry.insert("1.0", self.notes_data[date_str])

    def save_current_entry(self):
        date_str = self.get_selected_date_str()
        content = self.text_entry.get("1.0", "end").strip()

        if content:
            self.notes_data[date_str] = content
        else:
            if date_str in self.notes_data:
                del self.notes_data[date_str]

        self.save_notes_to_disk()
        messagebox.showinfo(
            "Saved", f"Timeline updated for {self.cal.selection_get()}!"
        )

    def jump_to_today(self):
        today = datetime.now().date()
        self.cal.selection_set(today)
        self.update_date_display()