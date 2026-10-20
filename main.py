import sys
import os
import time
from pathlib import Path

# Add the project root directory to Python's module search path to ensure robust absolute imports
ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import tkinter as tk
import customtkinter as ctk
from gui.sidebar import create_sidebar
from gui.catalog import create_workspace
from gui.menus import create_menu
import gui.app_state as state
from gui.chess_board import ChessBoardWidget
from gui.mixed_collections.mixed_core import MixedAnalysis
from gui.mixed_collections.edit_core import EditWorkspace
from gui.mixed_collections.edit_constants import load_categories_config


class LoadingOverlay(ctk.CTkToplevel):
    """Embedded loading overlay with a red progress bar tied directly to startup milestones."""

    def __init__(self, master=None, title_text="Totten", message="Starting up..."):
        super().__init__(master)

        self.withdraw()
        self.overrideredirect(True)

        width = 282
        height = 185

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(fg_color="#172134")
        if master:
            self.transient(master)
        self.grab_set()

        border_ring = ctk.CTkFrame(self, fg_color="#344268", corner_radius=11)
        border_ring.pack(fill="both", expand=True, padx=0, pady=0)

        frame = ctk.CTkFrame(border_ring, fg_color="#222e42", corner_radius=10)
        frame.pack(fill="both", expand=True, padx=1, pady=1)

        self.lbl_title = ctk.CTkLabel(
            frame, text=title_text, font=("Arial", 28, "bold"), text_color="white", fg_color="#222e42"
        )
        self.lbl_title.pack(pady=(15, 2))

        padded_msg = f"{message:^30}"
        self.lbl_message = ctk.CTkLabel(
            frame, text=padded_msg, font=("Arial", 11), text_color="#94a3b8", fg_color="#222e42", width=260
        )
        self.lbl_message.pack(pady=(0, 8))

        # Red startup progress bar matching import style
        self.progress_bar = ctk.CTkProgressBar(
            frame,
            width=230,
            height=10,
            progress_color="#ef4444",
            fg_color="#172134"
        )
        self.progress_bar.pack(pady=(0, 8))
        self.progress_bar.set(0.0)

        self.lbl_wait = ctk.CTkLabel(
            frame, text="", font=("Arial", 10), text_color="#94a3b8", fg_color="#222e42", width=260
        )
        self.lbl_wait.pack(pady=(0, 10))

        self.update_idletasks()
        self.deiconify()

    def update_progress(self, value, message=None):
        """Updates the progress bar (0.0 to 1.0) and optionally the status message."""
        try:
            self.progress_bar.set(max(0.0, min(1.0, value)))
            if message:
                padded_msg = f"{message:^30}"
                self.lbl_message.configure(text=padded_msg)
            self.update_idletasks()
        except Exception:
            pass

    def close(self):
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass


class Totten(ctk.CTk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Totten")

        self.geometry("1200x720")
        self.minsize(900, 600)

        self.resizable(True, True)

        self.configure(fg_color="#172134")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        state.app_root = self
        state.app_master = self
        state.show_workspace = self.show_workspace

        # Show native loading overlay with red progress support
        splash = LoadingOverlay(self, title_text="Totten", message="Starting up...")
        self.update_idletasks()

        # Step-by-step milestone initialization tied to data loading
        self._init_ui_with_synchronized_progress(splash)

        splash.close()

        # Hide the status bar progress bar now that loading is complete
        from gui.statusbar import hide_progress
        hide_progress()

    def _handle_global_navigation(self, target_view):
        """Catches centralized navigation requests broadcasted from app_state hub."""
        if target_view == "catalog_analysis":
            self.show_workspace("analysis", initial_games=state.catalog_state.get("active_games"),
                                target_game=state.catalog_state.get("active_focus"),
                                active_index=state.catalog_state.get("active_index"))
        elif target_view == "mixed_analysis":
            self.show_workspace("mixed_analysis", initial_games=state.mixed_state.get("active_games"),
                                filename=state.mixed_state.get("current_filename"))
        elif target_view == "patterns_analysis":
            self.show_workspace("patterns_analysis", initial_games=state.patterns_state.get("active_games"),
                                target_game=state.patterns_state.get("active_focus"),
                                active_index=state.patterns_state.get("active_index"))

    def _init_ui_with_synchronized_progress(self, splash):
        """Initializes UI elements and scales the red progress bar strictly to data loading milestones (25% -> 50% -> 75% -> 100%)."""

        # Milestone 1: 25% - Interface and Menu Setup
        splash.update_progress(0.25, "Initializing interface...")
        self.update_idletasks()

        self.menu_bar = create_menu(self)
        self.sidebar = create_sidebar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        state.left_frame = self.sidebar

        # Milestone 2: 50% - Catalog State & Game Database Location
        splash.update_progress(0.50, "Locating game catalog...")
        self.update_idletasks()

        initial_games = state.catalog_state.get("active_games")
        target_game = state.catalog_state.get("active_focus")
        active_index = state.catalog_state.get("active_index", 0)

        # Milestone 3: 75% - Parsing PGN Database & Populating Player List
        splash.update_progress(0.75, "Loading games into catalog...")
        self.update_idletasks()

        try:
            self.catalog_workspace = create_workspace(
                self,
                initial_games=initial_games,
                target_game=target_game,
                active_index=active_index
            )
        except TypeError:
            try:
                self.catalog_workspace = create_workspace(self, initial_games=initial_games)
            except TypeError:
                self.catalog_workspace = create_workspace(self)

        self.catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # Actively poll until the catalog data is fully loaded and drawn into the player list
        start_time = time.time()
        while (time.time() - start_time) < 12.0:
            self.update_idletasks()
            self.update()

            # Check if catalog workspace signals completion or games are loaded in state
            is_fully_loaded = False
            if hasattr(self.catalog_workspace, "is_loaded") and self.catalog_workspace.is_loaded:
                is_fully_loaded = True
            elif state.catalog_state.get("active_games") is not None and len(
                    state.catalog_state.get("active_games")) > 0:
                is_fully_loaded = True
            elif (time.time() - start_time) > 1.5:  # fallback safety render window
                is_fully_loaded = True

            if is_fully_loaded:
                break
            time.sleep(0.05)

        # 2-7. Keep other workspaces uninitialized until navigated to
        self.edit_workspace = None
        self.mixed_workspace = None
        self.analysis_workspace = None
        self.patterns_analysis_workspace = None
        self.patterns_workspace = None
        self.calendar_workspace = None

        # Register references in state
        state.workspace = self.catalog_workspace
        state.catalog_workspace = self.catalog_workspace
        state.edit_workspace = None
        state.mixed_workspace = None
        state.analysis_workspace = None
        state.patterns_analysis_workspace = None
        state.patterns_workspace = None
        state.calendar_workspace = None
        state.app_root = self
        state.show_workspace = self.show_workspace

        # Milestone 4: 100% - Fully Loaded & Ready
        splash.update_progress(1.00, "Ready!")
        self.update_idletasks()
        time.sleep(0.2)  # brief beat so user sees 100% filled red bar before closing

        # Defer registering the navigation listener by 300ms to prevent startup event loops and flashing
        self.after(300, lambda: state.register_nav_listener(self._handle_global_navigation))

    def show_workspace(self, target, *args, **kwargs):
        """Persistent switchboard router that toggles or re-creates workspaces based on navigation flow."""
        # Hide all main workspaces first
        if hasattr(state, "catalog_workspace") and state.catalog_workspace:
            state.catalog_workspace.grid_remove()
        if hasattr(state, "edit_workspace") and state.edit_workspace:
            state.edit_workspace.grid_remove()
        if hasattr(state, "mixed_workspace") and state.mixed_workspace:
            state.mixed_workspace.grid_remove()
        if hasattr(state, "analysis_workspace") and state.analysis_workspace:
            state.analysis_workspace.grid_remove()
        if hasattr(state, "patterns_analysis_workspace") and state.patterns_analysis_workspace:
            state.patterns_analysis_workspace.grid_remove()
        if hasattr(state, "patterns_workspace") and state.patterns_workspace:
            state.patterns_workspace.grid_remove()
        if hasattr(state, "calendar_workspace") and state.calendar_workspace:
            state.calendar_workspace.grid_remove()

        if hasattr(state, "transient_workspace") and state.transient_workspace:
            state.transient_workspace.destroy()
            state.transient_workspace = None

        # Route based on target type
        if target == "mixed":
            if not getattr(state, "edit_workspace", None):
                state.edit_workspace = EditWorkspace(self)
            else:
                # Reload categories from disk and refresh UI every time we navigate back here
                state.edit_workspace.categories = load_categories_config()
                if hasattr(state.edit_workspace, "_refresh_categories_list"):
                    state.edit_workspace._refresh_categories_list()

            state.edit_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.edit_workspace.tkraise()
            state.workspace = state.edit_workspace

            if hasattr(state.edit_workspace, "refresh_view"):
                state.edit_workspace.refresh_view()

        elif target in ("search_catalog", "catalog"):
            if hasattr(state, "catalog_workspace") and state.catalog_workspace:
                state.catalog_workspace.destroy()

            try:
                state.catalog_workspace = create_workspace(
                    self,
                    name=target,
                    **kwargs
                )
            except TypeError:
                state.catalog_workspace = create_workspace(self, name=target)

            state.catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.catalog_workspace.tkraise()
            state.workspace = state.catalog_workspace

            from gui.statusbar import set_status_message
            set_status_message("Loaded Catalog Search")

        elif target == "mixed_analysis":
            initial_games = kwargs.get("initial_games") or state.mixed_state.get("active_games")
            filename = kwargs.get("filename") or state.mixed_state.get("current_filename")

            if hasattr(state, "mixed_workspace") and state.mixed_workspace:
                state.mixed_workspace.destroy()

            try:
                state.mixed_workspace = MixedAnalysis(
                    self,
                    initial_games=initial_games,
                    filename=filename
                )
            except TypeError:
                state.mixed_workspace = MixedAnalysis(self)

            state.mixed_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.mixed_workspace.tkraise()
            state.workspace = state.mixed_workspace

        elif target == "analysis":
            initial_games = kwargs.get("initial_games") or state.catalog_state.get("active_games")
            target_game = kwargs.get("target_game") or state.catalog_state.get("active_focus")
            active_index = kwargs.get("active_index")
            if active_index is None:
                active_index = state.catalog_state.get("active_index", 0)

            if hasattr(state, "catalog_workspace") and state.catalog_workspace:
                state.catalog_workspace.destroy()

            try:
                state.catalog_workspace = create_workspace(
                    self,
                    initial_games=initial_games,
                    target_game=target_game,
                    active_index=active_index
                )
            except TypeError:
                try:
                    state.catalog_workspace = create_workspace(self, initial_games=initial_games)
                except TypeError:
                    state.catalog_workspace = create_workspace(self)

            state.catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.catalog_workspace.tkraise()
            state.workspace = state.catalog_workspace

            from gui.statusbar import set_status_message
            if initial_games:
                set_status_message(f"Loaded {len(initial_games)} filtered games into Catalog Analysis")
            else:
                set_status_message("Loaded full personal_catalog.pgn")

        elif target == "patterns":
            if not getattr(state, "patterns_workspace", None):
                from gui.patterns.patterns_workspace import PatternsWorkspace
                state.patterns_workspace = PatternsWorkspace(self)
                self.patterns_workspace = state.patterns_workspace

            state.patterns_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.patterns_workspace.tkraise()
            state.workspace = state.patterns_workspace

            if hasattr(state.patterns_workspace, "refresh_view"):
                state.patterns_workspace.refresh_update() if hasattr(state.patterns_workspace,
                                                                     "refresh_update") else state.patterns_workspace.refresh_view()

        elif target == "patterns_analysis":
            initial_games = kwargs.get("initial_games") or state.patterns_state.get("active_games")
            target_game = kwargs.get("target_game") or state.patterns_state.get("active_focus")
            active_index = kwargs.get("active_index")
            if active_index is None:
                active_index = state.patterns_state.get("active_index", 0)

            if hasattr(state, "patterns_analysis_workspace") and state.patterns_analysis_workspace:
                state.patterns_analysis_workspace.destroy()

            from gui.patterns.patterns_layout import PatternsAnalysis
            try:
                state.patterns_analysis_workspace = PatternsAnalysis(
                    self,
                    initial_games=initial_games,
                    target_game=target_game,
                    active_index=active_index
                )
            except TypeError:
                try:
                    state.patterns_analysis_workspace = PatternsAnalysis(
                        self,
                        initial_games=initial_games,
                        target_game=target_game
                    )
                except TypeError:
                    state.patterns_analysis_workspace = PatternsAnalysis(self)

            state.patterns_analysis_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.patterns_analysis_workspace.tkraise()
            state.workspace = state.patterns_analysis_workspace

        elif target == "calendar":
            if not getattr(state, "calendar_workspace", None):
                from gui.calendar_workspace import CalendarWorkspace
                state.calendar_workspace = CalendarWorkspace(self)
                state.calendar_workspace = state.calendar_workspace

            state.calendar_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.calendar_workspace.tkraise()
            state.workspace = state.calendar_workspace

            if hasattr(state.calendar_workspace, "update_date_display"):
                state.calendar_workspace.update_date_display()


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")

    ctk.set_widget_scaling(1.0)
    ctk.set_window_scaling(1.0)

    app = Totten()
    app.mainloop()