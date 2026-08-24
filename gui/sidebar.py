import io
from pathlib import Path
import chess
import chess.pgn
import customtkinter as ctk
import gui.app_state as state


class Sidebar(ctk.CTkFrame):

    def __init__(self, parent, on_navigate_callback):
        # Reduce sidebar width from 150 to ~105 to reclaim ~50-75px for the analysis view
        super().__init__(parent, width=105, corner_radius=0, fg_color="#172134")
        self.on_navigate = on_navigate_callback

        # --- STATUS DISPLAY (Anchored at the very bottom, text fixed at bottom) ---
        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(side="bottom", fill="x", padx=4, pady=(2, 6))

        # Status Label (At the bottom, soft blue/white color #ddddff)
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

        # Save reference for global management
        state.status = self.lbl_status

        # --- NAVIGATION TREE / BUTTONS (Packed sequentially from top) ---

        # 1. Catalog
        self.btn_catalog = ctk.CTkButton(
            self,
            text="Catalog",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("catalog")
        )
        self.btn_catalog.pack(fill="x", padx=4, pady=(15, 5))

        # 2. Analysis
        self.btn_analysis = ctk.CTkButton(
            self,
            text="Analysis",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("analysis")
        )
        self.btn_analysis.pack(fill="x", padx=4, pady=5)

        # 3. Patterns
        self.btn_patterns = ctk.CTkButton(
            self,
            text="Patterns",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("patterns")
        )
        self.btn_patterns.pack(fill="x", padx=4, pady=5)

        # 4. Mixed Collections
        self.btn_mixed = ctk.CTkButton(
            self,
            text="Mixed Collections",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("edit_workspace")
        )
        self.btn_mixed.pack(fill="x", padx=4, pady=5)

        # 5. Calendar
        self.btn_calendar = ctk.CTkButton(
            self,
            text="Calendar",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("calendar")
        )
        self.btn_calendar.pack(fill="x", padx=4, pady=(5, 8))

        # --- QUICK EVALUATION SECTION ---

        self.placeholder_text = "Paste PGN for quick analysis."

        # Text box placed closer to Calendar with standard text attributes
        self.txt_qeval_moves = ctk.CTkTextbox(
            self,
            height=130,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(size=10),
            border_color="#344268",
            border_width=1,
            wrap="word"
        )
        self.txt_qeval_moves.pack(fill="x", padx=4, pady=(0, 4))

        # Insert initial placeholder text and set color dimmer for placeholder appearance
        self.txt_qeval_moves.insert("1.0", self.placeholder_text)
        self.txt_qeval_moves.configure(text_color="#94a3b8")

        # Bind focus events to handle placeholder behavior cleanly
        self.txt_qeval_moves.bind("<FocusIn>", self._on_qeval_focus_in)
        self.txt_qeval_moves.bind("<FocusOut>", self._on_qeval_focus_out)

        # Analyze Button placed below the text area
        self.btn_qeval_analysis = ctk.CTkButton(
            self,
            text="Analyze",
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color="#344268",
            hover_color="#2e4a8c",
            command=self.handle_qeval_send_analysis
        )
        self.btn_qeval_analysis.pack(fill="x", padx=4, pady=(0, 6))

        # --- PROGRESS BAR (Always visible in layout, red and ready) ---
        self.progress_bar = ctk.CTkProgressBar(
            self,
            height=4,
            corner_radius=0,
            fg_color="#172134",
            progress_color="#DD0000",
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", padx=6, pady=(4, 4))
        self.progress_bar.set(0.0)

        # Save reference for global management
        state.progress_bar = self.progress_bar

    def _on_qeval_focus_in(self, event):
        """Clears placeholder text when user clicks into the box."""
        current_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if current_text == self.placeholder_text:
            self.txt_qeval_moves.delete("1.0", "end")
            self.txt_qeval_moves.configure(text_color="#f8fafc")

    def _on_qeval_focus_out(self, event):
        """Restores placeholder text if box is left empty."""
        current_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if not current_text:
            self.txt_qeval_moves.insert("1.0", self.placeholder_text)
            self.txt_qeval_moves.configure(text_color="#94a3b8")

    def parse_qeval_pgn(self):
        """Helper to parse sidebar quick eval text box."""
        raw_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if not raw_text or raw_text == self.placeholder_text:
            set_status_message("Error: Quick Evaluation box is empty.")
            return None
        try:
            pgn_io = io.StringIO(raw_text)
            game_node = chess.pgn.read_game(pgn_io)
            if not game_node:
                set_status_message("Error: Invalid PGN format in Quick Evaluation.")
                return None
            return game_node
        except Exception as e:
            set_status_message(f"Quick Evaluation Parse Error: {e}")
            return None

    def handle_qeval_send_analysis(self):
        """Sends quick evaluation moves directly to the analysis view and resets state."""
        game_node = self.parse_qeval_pgn()
        if not game_node:
            return

        state.set_active_analysis_game(game_node)

        # Revert text box back to initial placeholder state after successful send
        self.txt_qeval_moves.delete("1.0", "end")
        self.txt_qeval_moves.insert("1.0", self.placeholder_text)
        self.txt_qeval_moves.configure(text_color="#94a3b8")

        self.on_navigate("analysis")
        set_status_message("Quick Evaluation sent to Analysis.")


# --- LOCALIZED STATUS & PROGRESS BAR CONTROLLERS ---

def set_status_message(message, text_color="#ddddff"):
    """Updates the status bar label in the sidebar safely with #ddddff default."""
    print(f"[DEBUG STATUS]: {message}")
    try:
        label = getattr(state, "status", None)
        if label:
            label.configure(text=message, text_color=text_color)
            if hasattr(label, "update_idletasks"):
                label.update_idletasks()
    except Exception as e:
        print(f"Status Error: {e}")


def start_progress(indeterminate=False):
    """Prepares the progress bar to run."""
    try:
        pb = getattr(state, "progress_bar", None)
        if pb:
            pb.configure(progress_color="#DD0000")
            if indeterminate:
                pb.configure(mode="indeterminate")
                pb.start()
            else:
                pb.configure(mode="determinate")
                pb.set(0.0)

            master_root = pb.winfo_toplevel()
            if master_root:
                master_root.update_idletasks()
    except Exception as e:
        print(f"Progress Start Error: {e}")


def update_progress(value):
    """Grows the red bar from left to right (value between 0.0 and 1.0)."""
    try:
        pb = getattr(state, "progress_bar", None)
        if pb:
            clamped_val = max(0.0, min(1.0, value))
            pb.set(clamped_val)

            if clamped_val >= 1.0:
                stop_progress()
                return

            master_root = pb.winfo_toplevel()
            if master_root:
                master_root.update_idletasks()
    except Exception as e:
        print(f"Progress Update Error: {e}")


def stop_progress():
    """Resets the progress bar back to empty (0.0)."""
    try:
        pb = getattr(state, "progress_bar", None)
        if pb:
            try:
                pb.stop()
            except Exception:
                pass

            pb.set(0.0)

            master_root = pb.winfo_toplevel()
            if master_root:
                master_root.update_idletasks()
    except Exception as e:
        print(f"Progress Stop Error: {e}")


# --- TOP LEVEL FUNCTIONS ---

def create_sidebar(app, on_navigate_callback=None):
    """Factory function to initialize and return the Sidebar frame."""
    if on_navigate_callback is None:
        from gui.workspace import show_workspace
        on_navigate_callback = show_workspace

    sidebar = Sidebar(app, on_navigate_callback)
    state.left_frame = sidebar
    state.sidebar_visible = True

    if hasattr(app, "grid_columnconfigure"):
        app.grid_columnconfigure(0, minsize=105, weight=0)

    return sidebar


def toggle_sidebar():
    """Toggles the visibility of the sidebar frame and keeps column 0 locked at 105px."""
    sidebar = getattr(state, "left_frame", None)

    if sidebar is None:
        print("Notice: Sidebar frame reference (state.left_frame) not found.")
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