import io
from pathlib import Path
import chess
import chess.pgn
import customtkinter as ctk
import gui.app_state as state


class Sidebar(ctk.CTkFrame):

    def __init__(self, parent, on_navigate_callback=None):
        super().__init__(parent, width=105, corner_radius=0, fg_color="#172134")
        self.on_navigate = on_navigate_callback or self._default_navigate

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

        # --- NAVIGATION BUTTONS ---
        self.btn_catalog = ctk.CTkButton(
            self, text="Catalog", anchor="w", fg_color="transparent",
            hover_color="#2e4a8c", text_color="white",
            command=lambda: self.on_navigate("search_catalog")
        )
        self.btn_catalog.pack(fill="x", padx=4, pady=(15, 5))
        state.show_workspace("search_catalog")

        self.btn_analysis = ctk.CTkButton(
            self, text="Analysis", anchor="w", fg_color="transparent",
            hover_color="#2e4a8c", text_color="white",
            command=lambda: self.on_navigate("analysis")
        )
        self.btn_analysis.pack(fill="x", padx=4, pady=5)

        self.btn_patterns = ctk.CTkButton(
            self, text="Patterns", anchor="w", fg_color="transparent",
            hover_color="#2e4a8c", text_color="white",
            command=lambda: self.on_navigate("patterns")
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
            command=lambda: self.on_navigate("calendar")
        )
        self.btn_calendar.pack(fill="x", padx=4, pady=5)

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

        self.btn_qeval_analysis = ctk.CTkButton(
            self, text="Analyze", height=24, font=ctk.CTkFont(size=10),
            fg_color="#344268", hover_color="#2e4a8c", command=self.handle_qeval_send_analysis
        )
        self.btn_qeval_analysis.pack(fill="x", padx=4, pady=(0, 6))

    def _default_navigate(self, target):
        """Switchboard navigation router handling workspace switching directly via state."""
        if hasattr(state, "show_workspace") and callable(state.show_workspace):
            if target == "analysis":
                state.show_workspace("catalog", initial_games=None)
            elif target == "patterns":
                state.show_workspace("patterns")
            else:
                state.show_workspace(target)
        else:
            # Fallback block...
            parent = self.master
            if target == "search_catalog":
                state.active_group_games = None
                state.active_focus_game = None

                if not hasattr(state,
                               "search_catalog_workspace") or not state.search_catalog_workspace or not state.search_catalog_workspace.winfo_exists():
                    from gui.search_catalog_workspace import SearchCatalogWorkspace
                    state.search_catalog_workspace = SearchCatalogWorkspace(parent)
                    state.search_catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

                state.search_catalog_workspace.tkraise()
                state.workspace = state.search_catalog_workspace
                if hasattr(state.search_catalog_workspace, "refresh_view"):
                    state.search_catalog_workspace.refresh_view()

            elif target == "analysis":
                state.active_group_games = None
                state.active_focus_game = None

                if not hasattr(state,
                               "catalog_workspace") or not state.catalog_workspace or not state.catalog_workspace.winfo_exists():
                    from gui.catalog_analysis import create_workspace
                    state.catalog_workspace = create_workspace(parent)
                    state.catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

                state.catalog_workspace.tkraise()
                state.workspace = state.catalog_workspace
                if hasattr(state.catalog_workspace, "refresh_view"):
                    state.catalog_workspace.refresh_view()

            elif target == "patterns":
                state.show_workspace("patterns")

            elif target == "mixed":
                if not hasattr(state,
                               "edit_workspace") or not state.edit_workspace or not state.edit_workspace.winfo_exists():
                    from gui.edit_workspace import EditWorkspace
                    state.edit_workspace = EditWorkspace(parent)
                    state.edit_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
                state.edit_workspace.tkraise()
                state.workspace = state.edit_workspace
                if hasattr(state.edit_workspace, "refresh_view"):
                    state.edit_workspace.refresh_view()

            elif target == "calendar":
                if not hasattr(state,
                               "calendar_workspace") or not state.calendar_workspace or not state.calendar_workspace.winfo_exists():
                    from gui.calendar_workspace import CalendarWorkspace
                    state.calendar_workspace = CalendarWorkspace(parent)
                    state.calendar_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
                state.calendar_workspace.tkraise()
                state.workspace = state.calendar_workspace
                if hasattr(state.calendar_workspace, "refresh_view"):
                    state.calendar_workspace.refresh_view()

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
            return None

        cleaned_lines = []
        for line in raw_text.splitlines():
            cleaned_lines.append(line.strip())
        normalized_text = "\n".join(cleaned_lines)

        try:
            pgn_io = io.StringIO(normalized_text)
            game_node = chess.pgn.read_game(pgn_io)
            if not game_node:
                set_status_message("Error: Invalid PGN format in Quick Evaluation.")
                return None
            return game_node
        except Exception as e:
            set_status_message(f"Quick Evaluation Parse Error: {e}")
            return None

    def handle_qeval_send_analysis(self):
        game_node = self.parse_qeval_pgn()
        if not game_node:
            return

        state.set_active_analysis_game(game_node)

        self.txt_qeval_moves.delete("1.0", "end")
        self.txt_qeval_moves.insert("1.0", self.placeholder_text)
        self.txt_qeval_moves.configure(text_color="#94a3b8")

        self.on_navigate("analysis")
        set_status_message("Quick Evaluation sent to Analysis.")


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
    sidebar = Sidebar(app, on_navigate_callback)
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