import json
from datetime import datetime
import os
import tkinter as tk
from tkinter import messagebox
from tkcalendar import Calendar
import customtkinter as ctk

# Path to store timeline notes locally
NOTES_FILE = "calendar_notes.json"


class CalendarWorkspace(ctk.CTkFrame):

  def __init__(self, parent, app_state=None):
    super().__init__(parent, fg_color="#172134", corner_radius=0)
    self.app_state = app_state

    self.notes_data = self.load_notes()

    # Configure grid layout: Left side Calendar, Right side Timeline/Journal Entry
    self.grid_columnconfigure(1, weight=1)
    self.grid_rowconfigure(0, weight=1)

    # --- Left Pane: Calendar Widget & Navigation ---
    self.left_frame = ctk.CTkFrame(
        self,
        fg_color="#1f2c42",
        corner_radius=8,
        border_width=1,
        border_color="#2a3b59"
    )
    self.left_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
    self.left_frame.grid_rowconfigure(1, weight=1)
    self.left_frame.grid_columnconfigure(0, weight=1)

    self.title_label = ctk.CTkLabel(
        self.left_frame,
        text="Timeline Chronicle",
        font=ctk.CTkFont(size=18, weight="bold"),
        text_color="#ffffff",
    )
    self.title_label.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

    # Calendar widget using tkcalendar
    self.cal = Calendar(
        self.left_frame,
        selectmode="day",
        year=datetime.now().year,
        month=datetime.now().month,
        day=datetime.now().day,
        font=("Arial", 12),
        background="#172134",
        foreground="white",
        selectbackground="#1f538d",
        bordercolor="#1f2c42",
        headersbackground="#1f2c42",
        headersforeground="white",
        normalbackground="#172134",
        normalforeground="white",
        weekendbackground="#172134",
        weekendforeground="white",
        othermonthbackground="#121926",
        othermonthforeground="#56657a",
        othermonthwebackground="#121926",
        othermonthweforeground="#56657a",
    )
    self.cal.grid(row=1, column=0, padx=20, pady=10, sticky="nsew")
    self.cal.bind("<<CalendarSelected>>", self.on_date_select)

    # Quick Jump Bar
    self.jump_frame = ctk.CTkFrame(self.left_frame, fg_color="transparent")
    self.jump_frame.grid(row=2, column=0, padx=20, pady=(10, 20), sticky="ew")

    self.btn_today = ctk.CTkButton(
        self.jump_frame,
        text="Jump to Today",
        command=self.jump_to_today,
        fg_color="#1f538d",
        hover_color="#14375f"
    )
    self.btn_today.pack(fill="x", pady=(0, 5))

    # --- Right Pane: Entry & Context View ---
    self.right_frame = ctk.CTkFrame(
        self,
        fg_color="#1f2c42",
        corner_radius=8,
        border_width=1,
        border_color="#2a3b59"
    )
    self.right_frame.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
    self.right_frame.grid_rowconfigure(2, weight=1)
    self.right_frame.grid_columnconfigure(0, weight=1)

    # Selected Date Header
    self.date_header = ctk.CTkLabel(
        self.right_frame,
        text="",
        font=ctk.CTkFont(size=16, weight="bold"),
        text_color="#ffffff",
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
        text_color="#94a3b8",
        anchor="w",
    )
    self.sub_header.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

    # Text Area for Free-form Timeline Notes
    self.text_entry = ctk.CTkTextbox(
        self.right_frame,
        wrap="word",
        font=("Arial", 14),
        fg_color="#172134",
        text_color="#ffffff"
    )
    self.text_entry.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="nsew")

    # Save Button
    self.btn_save = ctk.CTkButton(
        self.right_frame,
        text="Save Timeline Entry",
        fg_color="#28a745",
        hover_color="#218838",
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