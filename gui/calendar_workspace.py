import json
from pathlib import Path
import customtkinter as ctk
from tkcalendar import Calendar
from gui.statusbar import set_status_message

CALENDAR_DATA_FILE = Path("historical_calendar_notes.json")

class CalendarWorkspace(ctk.CTkFrame):
    """
    Historical Calendar & To-Do Workspace (Replacing the traditional notes section).
    Supports navigating far back into history (pre-1900 years) for tracking 
    historical chess matches, tournament schedules, and date-anchored notes.
    """
    def __init__(self, master, app_state=None):
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.app_state = app_state
        
        self.notes_store = self._load_notes()

        # Grid setup for main split: Calendar on Left, Notes/Editor on Right
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)

        # --- LEFT PANEL: Calendar & Historical Jump ---
        self.left_panel = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#334155")
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.lbl_cal_title = ctk.CTkLabel(
            self.left_panel, text="Historical Calendar", font=ctk.CTkFont(size=14, weight="bold"), text_color="#f8fafc"
        )
        self.lbl_cal_title.pack(anchor="w", padx=15, pady=(15, 10))

        # Tkcalendar widget (supports pre-1900 years seamlessly)
        self.cal = Calendar(
            self.left_panel,
            selectmode="day",
            year=2026, month=8, day=7,
            background="#1e293b",
            foreground="#f8fafc",
            selectbackground="#2e4a8c",
            selectforeground="#ffffff",
            normalbackground="#0f172a",
            normalforeground="#f8fafc",
            weekendbackground="#0f172a",
            weekendforeground="#94a3b8",
            othermonthbackground="#090d16",
            othermonthforeground="#475569",
            headersbackground="#1e293b",
            headersforeground="#94a3b8",
            font=("Arial", 10)
        )
        self.cal.pack(padx=15, pady=10, fill="x")
        self.cal.bind("<<CalendarSelected>>", self._on_date_selected)

        # Quick Historical Jump Controls (Pre-1900 support)
        self.history_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        self.history_frame.pack(fill="x", padx=15, pady=15)

        self.lbl_jump = ctk.CTkLabel(self.history_frame, text="Historical Jump:", font=ctk.CTkFont(size=11), text_color="#94a3b8")
        self.lbl_jump.pack(anchor="w", pady=(0, 5))

        self.btn_1886 = ctk.CTkButton(
            self.history_frame, text="1886 (Steinitz vs Zukertort)", height=26,
            fg_color="#334155", hover_color="#475569", font=("Arial", 10),
            command=lambda: self.jump_to_date(1886, 1, 1)
        )
        self.btn_1886.pack(fill="x", pady=2)

        self.btn_1851 = ctk.CTkButton(
            self.history_frame, text="1851 (London Tournament)", height=26,
            fg_color="#334155", hover_color="#475569", font=("Arial", 10),
            command=lambda: self.jump_to_date(1851, 5, 1)
        )
        self.btn_1851.pack(fill="x", pady=2)

        # --- RIGHT PANEL: Date-Anchored Notes & Tournament Info ---
        self.right_panel = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=8, border_width=1, border_color="#334155")
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)

        self.lbl_date_header = ctk.CTkLabel(
            self.right_panel, text="Selected Date: N/A", font=ctk.CTkFont(size=13, weight="bold"), text_color="#33b5e5"
        )
        self.lbl_date_header.pack(anchor="w", padx=15, pady=(15, 5))

        self.notes_textbox = ctk.CTkTextbox(
            self.right_panel,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word"
        )
        self.notes_textbox.pack(fill="both", expand=True, padx=15, pady=10)

        self.btn_save_note = ctk.CTkButton(
            self.right_panel, text="Save Notes for Date", height=30,
            fg_color="#2e4a8c", hover_color="#4870cd",
            command=self._save_current_note
        )
        self.btn_save_note.pack(anchor="e", padx=15, pady=(0, 15))

        # Select today or initial date on boot
        self._load_selected_date_note()

    def _on_date_selected(self, event=None):
        self._load_selected_date_note()

    def get_selected_date_string(self):
        # tkcalendar returns date object or string depending on setup; get_date() gives formatted string or date
        return str(self.cal.selection_get())

    def _load_selected_date_note(self):
        date_str = self.get_selected_date_string()
        self.lbl_date_header.configure(text=f"Selected Date: {date_str}")
        
        note_content = self.notes_store.get(date_str, "")
        self.notes_textbox.delete("1.0", "end")
        self.notes_textbox.insert("end", note_content)

    def _save_current_note(self):
        date_str = self.get_selected_date_string()
        content = self.notes_textbox.get("1.0", "end-1c")
        
        self.notes_store[date_str] = content
        self._save_notes_to_disk()
        set_status_message(f"Saved calendar notes for {date_str}.")

    def jump_to_date(self, year, month, day):
        self.cal.selection_set(datetime_val := f"{year:04d}-{month:02d}-{day:02d}")
        # Update calendar view to target year
        self.cal.calevent_remove('all')
        self._load_selected_date_note()
        set_status_message(f"Jumped calendar view to historical year {year}.")

    def _load_notes(self):
        if CALENDAR_DATA_FILE.exists():
            try:
                with open(CALENDAR_DATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_notes_to_disk(self):
        try:
            with open(CALENDAR_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.notes_store, f, indent=2)
        except Exception as e:
            print(f"Error saving calendar notes: {e}")

    def refresh_view(self):
        pass