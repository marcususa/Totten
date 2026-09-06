import io
from pathlib import Path
import chess
import chess.pgn
import customtkinter as ctk
import gui.app_state as state


class Sidebar(ctk.CTkFrame):

    def __init__(self, parent):
        super().__init__(parent, width=105, corner_radius=0, fg_color="#172134")

        # --- STATUS DISPLAY ---
        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(side="bottom", fill="x", padx=4, pady=(2, 6))

        self.lbl_status = ctk.CTkLabel(
            self.status_container,
            text="Ready",
            anchor="sw",
            justify="left",
            wraplength=95,
            font=ctk.CTkFont(size=11),
            text_color="#ddddff"
        )
        self.lbl_status.pack(side="bottom", fill="x", anchor="sw")

        state.status = self.lbl_status

        # --- PROGRESS CONTAINER & BAR ---
        self.progress_container = ctk.CTkFrame(self, height=16, fg_color="transparent")
        state.progress_container = self.progress_container

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_container,
            height=8,
            corner_radius=2,
            fg_color="#0f172a",
            progress_color="#ff0000",
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", expand=True, pady=4)
        self.progress_bar.set(0.0)

        state.progress_bar = self.progress_bar

        # Keep the progress bar hidden by default on startup
        self.progress_container.pack_forget()

        # --- NAVIGATION BUTTONS ---
        self.btn_catalog = ctk.CTkButton(
            self, text="Catalog", anchor="w", fg_color="transparent",
            hover_color="#2e4a8c", text_color="white",
            command=lambda: state.show_workspace("search_catalog")
        )
        self.btn_catalog.pack(fill="x", padx=4, pady=(15, 5))

        self.btn_analysis = ctk.CTkButton(
            self, text="Analysis", anchor="w", fg_color="transparent",
            hover_color="#2e4a8c", text_color="white",
            command=lambda: state.show_workspace("analysis")
        )
        self.btn_analysis.pack(fill="x", padx=4, pady=5)

        self.btn_patterns = ctk.CTkButton(
            self, text="Patterns", anchor="w", fg_color="transparent",
            hover_color="#2e4a8c", text_color="white",
            command=lambda: state.show_workspace("patterns")
        )
        self.btn_patterns.pack(fill="x", padx=4, pady=5)

        self.btn_mixed = ctk.CTkButton(
            self, text="Mixed Collections", anchor="w", fg_color="transparent",
            hover_color="#2e4a8c", text_color="white",
            command=lambda: state.show_workspace("mixed_search")
        )
        self.btn_mixed.pack(fill="x", padx=4, pady=5)

        self.btn_calendar = ctk.CTkButton(
            self, text="Calendar", anchor="w", fg_color="transparent",
            hover_color="#2e4a8c", text_color="white",
            command=lambda: state.show_workspace("calendar")
        )
        self.btn_calendar.pack(fill="x", padx=4, pady=5)

        # Start with the analysis workspace on startup
        state.show_workspace("analysis")

        # --- QUICK EVALUATION SECTION ---
        self.placeholder_text = "Paste PGN for quick analysis."

        self.txt_qeval_moves = ctk.CTkTextbox(
            self, height=130, fg_color="#1e293b", text_color="#f8fafc",
            font=ctk.CTkFont(size=10), border_color="#344268", border_width=1, wrap="word"
        )
        self.txt_qeval_moves.pack(fill="x", padx=4, pady=(10, 4))

        self.txt_qeval_moves.insert("1.0", self.placeholder_text)
        self.txt_qeval_moves.configure(text_color="#94a3b8")

        self.txt_qeval_moves.bind("<FocusIn>", self._on_qeval_focus_in)
        self.txt_qeval_moves.bind("<FocusOut>", self._on_qeval_focus_out)
        self.txt_qeval_moves.bind("<Button-3>", self._on_qeval_right_click)
        self.txt_qeval_moves.bind("<Button-2>", self._on_qeval_right_click)

        self.btn_qeval_analysis = ctk.CTkButton(
            self, text="Analyze", height=24, font=ctk.CTkFont(size=10),
            fg_color="#344268", hover_color="#2e4a8c", command=self.handle_qeval_send_analysis
        )
        self.btn_qeval_analysis.pack(fill="x", padx=4, pady=(0, 6))

    def _on_qeval_right_click(self, event):
        """Pasted clipboard text directly on right-click, handling placeholders."""
        try:
            self.txt_qeval_moves.focus_set()
            clipboard_text = self.winfo_toplevel().clipboard_get()
            if not clipboard_text:
                return "break"

            # Clear placeholder text if it's currently showing
            current_text = self.txt_qeval_moves.get("1.0", "end").strip()
            if current_text == self.placeholder_text:
                self.txt_qeval_moves.delete("1.0", "end")
                self.txt_qeval_moves.configure(text_color="#f8fafc")

            # Insert clipboard contents at the current cursor position
            self.txt_qeval_moves.insert("insert", clipboard_text)
        except Exception:
            pass
        return "break"

    def _on_qeval_focus_in(self, event):
        current_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if current_text == self.placeholder_text:
            self.txt_qeval_moves.delete("1.0", "end")
            self.txt_qeval_moves.configure(text_color="#f8fafc")

    def _on_qeval_focus_out(self, event):
        current_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if not current_text:
            self.txt_qeval_moves.insert("1.0", self.placeholder_text)
            self.txt_qeval_moves.configure(text_color="#94a3b8")

    def parse_qeval_pgn(self):
        raw_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if not raw_text or raw_text == self.placeholder_text:
            set_status_message("Error: Quick Evaluation box is empty.")
            return []

        cleaned_lines = [line.strip() for line in raw_text.splitlines()]
        normalized_text = "\n".join(cleaned_lines)

        games_list = []
        try:
            pgn_io = io.StringIO(normalized_text)
            while True:
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break
                games_list.append(game)

            if not games_list:
                set_status_message("Error: No valid PGN games found in Quick Evaluation.")
                return []
            return games_list
        except Exception as e:
            set_status_message(f"Quick Evaluation Parse Error: {e}")
            return []

    def handle_qeval_send_analysis(self):
        games_list = self.parse_qeval_pgn()
        if not games_list:
            return

        state.catalog_state["active_games"] = games_list
        state.catalog_state["active_index"] = 0
        state.catalog_state["active_focus"] = games_list[0]

        self.txt_qeval_moves.delete("1.0", "end")
        self.txt_qeval_moves.insert("1.0", self.placeholder_text)
        self.txt_qeval_moves.configure(text_color="#94a3b8")

        state.show_workspace("analysis")
        set_status_message(f"Loaded {len(games_list)} game(s) for quick analysis.")


# --- LOCALIZED STATUS & PROGRESS BAR CONTROLLERS ---

def set_status_message(message, text_color="#ddddff"):
    """Updates the status bar label in the sidebar safely."""
    try:
        label = getattr(state, "status", None)
        if label:
            label.configure(text=message, text_color=text_color)
            label.update_idletasks()
    except Exception as e:
        print(f"Status Error: {e}")


def start_progress(indeterminate=False):
    """Packs the container and resets progress bar to start."""
    try:
        pc = getattr(state, "progress_container", None)
        pb = getattr(state, "progress_bar", None)

        if pc and pb:
            if not pc.winfo_ismapped():
                status_box = getattr(state, "status", None)
                if status_box and status_box.master:
                    pc.pack(side="bottom", fill="x", padx=6, pady=(2, 2), before=status_box.master)
                else:
                    pc.pack(side="bottom", fill="x", padx=6, pady=(2, 2))

            if indeterminate:
                pb.configure(mode="indeterminate")
                pb.start()
            else:
                pb.configure(mode="determinate")
                pb.set(0.01)

            pc.update_idletasks()
    except Exception as e:
        print(f"Progress Start Error: {e}")


def update_progress(value):
    """Updates progress bar value (0.0 to 1.0) and triggers stop when complete."""
    try:
        pb = getattr(state, "progress_bar", None)
        pc = getattr(state, "progress_container", None)

        if pb and pc:
            if not pc.winfo_ismapped():
                start_progress()

            clamped_val = max(0.0, min(1.0, value))

            if pb.cget("mode") == "indeterminate":
                try:
                    pb.stop()
                except Exception:
                    pass
                pb.configure(mode="determinate")

            pb.set(clamped_val)
            pb.update_idletasks()

            if clamped_val >= 1.0:
                pb.after(300, stop_progress)
    except Exception as e:
        print(f"Progress Update Error: {e}")


def stop_progress():
    """Stops animation and hides the entire progress container frame."""
    try:
        pb = getattr(state, "progress_bar", None)
        pc = getattr(state, "progress_container", None)

        if pb:
            try:
                pb.stop()
            except Exception:
                pass
            pb.set(0.0)

        if pc and pc.winfo_ismapped():
            pc.pack_forget()
            pc.update_idletasks()
    except Exception as e:
        print(f"Progress Stop Error: {e}")


# --- TOP LEVEL FUNCTIONS ---

def create_sidebar(app, on_navigate_callback=None):
    sidebar = Sidebar(app)
    state.left_frame = sidebar
    state.sidebar_visible = True

    if hasattr(app, "grid_columnconfigure"):
        app.grid_columnconfigure(0, minsize=105, weight=0)

    return sidebar


def toggle_sidebar():
    sidebar = getattr(state, "left_frame", None)
    if sidebar is None:
        return

    app = sidebar.master

    if getattr(state, "sidebar_visible", True):
        sidebar.grid_remove()
        if hasattr(app, "grid_columnconfigure"):
            app.grid_columnconfigure(0, minsize=0, weight=0)
        state.sidebar_visible = False
    else:
        if hasattr(app, "grid_columnconfigure"):
            app.grid_columnconfigure(0, minsize=105, weight=0)

        sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        state.sidebar_visible = True