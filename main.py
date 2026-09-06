import customtkinter as ctk
from gui.sidebar import create_sidebar
from gui.catalog_analysis import create_workspace
from gui.menus import create_menu
import gui.app_state as state


class Totten(ctk.CTk):
    """
    Main application window for Totten, initializing the core root container,
    top-level application menus, sidebar switchboard, and default startup catalog analysis view.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Totten")
        self.geometry("1200x800")
        self.configure(fg_color="#172134")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        state.app_root = self
        state.app_master = self
        state.show_workspace = self.show_workspace

        # Show native loading overlay before heavy UI initialization
        from gui.splash import LoadingOverlay
        splash = LoadingOverlay(self, "Totten", "Loading...")
        self.update_idletasks()

        self._init_ui()

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
            self.show_workspace("mixed", initial_games=state.mixed_state.get("active_games"),
                                filename=state.mixed_state.get("current_filename"))
        elif target_view == "patterns_analysis":
            self.show_workspace("patterns_analysis", initial_games=state.patterns_state.get("active_games"),
                                target_game=state.patterns_state.get("active_focus"),
                                active_index=state.patterns_state.get("active_index"))

    def _init_ui(self):
        self.menu_bar = create_menu(self)

        self.sidebar = create_sidebar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        state.left_frame = self.sidebar

        # Pre-initialize workspaces so they persist safely across navigation switches
        from gui.catalog_analysis import create_workspace
        from gui.mixed_analysis import MixedAnalysis
        from gui.patterns_analysis import create_patterns_analysis_workspace

        # 1. Default Catalog Workspace
        initial_games = state.catalog_state.get("active_games")
        target_game = state.catalog_state.get("active_focus")
        active_index = state.catalog_state.get("active_index", 0)

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

        # 2. Mixed Analysis Workspace
        self.mixed_workspace = MixedAnalysis(self)
        self.mixed_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.mixed_workspace.grid_remove()

        # 3. Standard Analysis Workspace
        self.analysis_workspace = MixedAnalysis(self)
        self.analysis_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.analysis_workspace.grid_remove()

        # 4. Patterns Analysis Workspace
        patterns_games = state.patterns_state.get("active_games")
        patterns_target = state.patterns_state.get("active_focus")
        patterns_index = state.patterns_state.get("active_index", 0)

        try:
            self.patterns_analysis_workspace = create_patterns_analysis_workspace(
                self,
                initial_games=patterns_games,
                target_game=patterns_target,
                active_index=patterns_index
            )
        except TypeError:
            try:
                self.patterns_analysis_workspace = create_patterns_analysis_workspace(self, initial_games=patterns_games)
            except TypeError:
                self.patterns_analysis_workspace = create_patterns_analysis_workspace(self)

        self.patterns_analysis_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.patterns_analysis_workspace.grid_remove()

        # 5. Patterns Workspace
        self.patterns_workspace = None

        # Register references in state
        state.workspace = self.catalog_workspace
        state.catalog_workspace = self.catalog_workspace
        state.mixed_workspace = self.mixed_workspace
        state.analysis_workspace = self.analysis_workspace
        state.patterns_analysis_workspace = self.patterns_analysis_workspace
        state.patterns_workspace = None
        state.app_root = self
        state.show_workspace = self.show_workspace

        state.register_nav_listener(self._handle_global_navigation)

    def show_workspace(self, target, *args, **kwargs):
        """Persistent switchboard router that toggles or re-creates workspaces based on navigation flow."""
        # Hide all main workspaces first
        if hasattr(state, "catalog_workspace") and state.catalog_workspace:
            state.catalog_workspace.grid_remove()
        if hasattr(state, "mixed_workspace") and state.mixed_workspace:
            state.mixed_workspace.grid_remove()
        if hasattr(state, "analysis_workspace") and state.analysis_workspace:
            state.analysis_workspace.grid_remove()
        if hasattr(state, "patterns_analysis_workspace") and state.patterns_analysis_workspace:
            state.patterns_analysis_workspace.grid_remove()
        if hasattr(state, "patterns_workspace") and state.patterns_workspace:
            state.patterns_workspace.grid_remove()

        # Also clean up any transient search/selector workspace frame if active
        if hasattr(state, "transient_workspace") and state.transient_workspace:
            state.transient_workspace.destroy()
            state.transient_workspace = None

        # Route based on target type
        if target == "search_catalog" or target == "catalog_search":
            from gui.search_catalog_workspace import SearchCatalogWorkspace
            try:
                self.transient_workspace = SearchCatalogWorkspace(self)
            except TypeError:
                from gui.search_catalog_workspace import create_workspace
                self.transient_workspace = create_workspace(self)

            self.transient_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            self.transient_workspace.tkraise()
            state.workspace = self.transient_workspace

        elif target == "mixed_search" or target == "edit_workspace":
            from gui.edit_workspace import EditWorkspace
            try:
                self.transient_workspace = EditWorkspace(self)
            except TypeError:
                from gui.edit_workspace import create_workspace
                self.transient_workspace = create_workspace(self)

            self.transient_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            self.transient_workspace.tkraise()
            state.workspace = self.transient_workspace

        elif target == "mixed" or target == "mixed_analysis":
            initial_games = kwargs.get("initial_games") or state.mixed_state.get("active_games")
            filename = kwargs.get("filename") or state.mixed_state.get("current_filename")

            if hasattr(state, "mixed_workspace") and state.mixed_workspace:
                state.mixed_workspace.destroy()

            from gui.mixed_analysis import MixedAnalysis
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

            from gui.catalog_analysis import create_workspace
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

            # Use an after() callback to ensure the widget is drawn before selecting the row index
            def _deferred_focus():
                if hasattr(state.catalog_workspace, "load_game_from_state"):
                    try:
                        state.catalog_workspace.load_game_from_state(active_index)
                    except Exception:
                        pass
                elif hasattr(state.catalog_workspace, "select_game_by_index"):
                    try:
                        state.catalog_workspace.select_game_by_index(active_index)
                    except Exception:
                        pass

            self.after(50, _deferred_focus)

            from gui.statusbar import set_status_message
            if initial_games:
                set_status_message(f"Loaded {len(initial_games)} filtered games into Catalog Analysis")
            else:
                set_status_message("Loaded full personal_catalog.pgn")

        elif target == "patterns":
            if not getattr(state, "patterns_workspace", None):
                from gui.patterns_workspace import PatternsWorkspace
                state.patterns_workspace = PatternsWorkspace(self)
                self.patterns_workspace = state.patterns_workspace

            state.patterns_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.patterns_workspace.tkraise()
            state.workspace = state.patterns_workspace

            if hasattr(state.patterns_workspace, "refresh_view"):
                state.patterns_workspace.refresh_view()

        elif target == "patterns_analysis":
            initial_games = kwargs.get("initial_games") or state.patterns_state.get("active_games")
            target_game = kwargs.get("target_game") or state.patterns_state.get("active_focus")
            active_index = kwargs.get("active_index")
            if active_index is None:
                active_index = state.patterns_state.get("active_index", 0)

            if hasattr(state, "patterns_analysis_workspace") and state.patterns_analysis_workspace:
                state.patterns_analysis_workspace.destroy()

            from gui.patterns_analysis import PatternsAnalysis
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


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = Totten()
    app.mainloop()