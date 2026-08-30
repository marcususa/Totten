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

        self._init_ui()

    def _handle_global_analysis_callback(self, game_obj, category_source=None):
        """Automatically navigates to the respective workspace when a collection is pushed."""
        if category_source == "patterns":
            self.show_workspace("patterns_analysis", initial_games=state.patterns_state.get("active_games"),
                                target_game=game_obj)

    def _init_ui(self):
        self.menu_bar = create_menu(self)

        self.sidebar = create_sidebar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        state.left_frame = self.sidebar

        # Pre-initialize workspaces so they persist safely across navigation switches
        from gui.catalog_analysis import create_workspace
        from gui.mixed_analysis import MixedAnalysis
        from gui.patterns_analysis import create_patterns_analysis_workspace
        from gui.patterns_workspace import PatternsWorkspace

        # 1. Default Catalog Workspace
        self.catalog_workspace = create_workspace(self)
        self.catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        # 2. Mixed Analysis Workspace
        self.mixed_workspace = MixedAnalysis(self)
        self.mixed_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.mixed_workspace.grid_remove()  # Hide initially

        # 3. Standard Analysis Workspace
        self.analysis_workspace = MixedAnalysis(self)
        self.analysis_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.analysis_workspace.grid_remove()  # Hide initially

        # 4. Patterns Analysis Workspace (from patterns_analysis.py)
        self.patterns_analysis_workspace = create_patterns_analysis_workspace(self)
        self.patterns_analysis_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.patterns_analysis_workspace.grid_remove()  # Hide initially

        # 5. Patterns Workspace (from patterns_workspace.py)
        self.patterns_workspace = PatternsWorkspace(self)
        self.patterns_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.patterns_workspace.grid_remove()  # Hide initially

        # Register references in state
        state.workspace = self.catalog_workspace
        state.catalog_workspace = self.catalog_workspace
        state.mixed_workspace = self.mixed_workspace
        state.analysis_workspace = self.analysis_workspace
        state.patterns_analysis_workspace = self.patterns_analysis_workspace
        state.patterns_workspace = self.patterns_workspace
        state.app_root = self
        state.show_workspace = self.show_workspace

        # Register global analysis callback once on startup
        state.register_analysis_callback(self._handle_global_analysis_callback)

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

        elif target == "catalog" or target == "catalog_analysis":
            initial_games = kwargs.get("initial_games") or state.catalog_state.get("active_games")

            if initial_games:
                if hasattr(state, "catalog_workspace") and state.catalog_workspace:
                    state.catalog_workspace.destroy()

                from gui.catalog_analysis import create_workspace
                state.catalog_workspace = create_workspace(self, initial_games=initial_games)
                state.catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
                state.catalog_state["active_games"] = None

            state.catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.catalog_workspace.tkraise()
            state.workspace = state.catalog_workspace

        elif target == "mixed" or target == "mixed_analysis":
            initial_games = kwargs.get("initial_games") or state.mixed_state.get("active_games")
            filename = kwargs.get("filename") or state.mixed_state.get("current_filename")

            if initial_games or filename:
                if hasattr(state, "mixed_workspace") and state.mixed_workspace:
                    state.mixed_workspace.destroy()

                from gui.mixed_analysis import MixedAnalysis
                state.mixed_workspace = MixedAnalysis(self)
                state.mixed_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

                if initial_games and hasattr(state.mixed_workspace, "load_games_list"):
                    state.mixed_workspace.load_games_list(initial_games)
                elif filename and hasattr(state.mixed_workspace, "load_catalog_data"):
                    state.mixed_workspace.filename = filename
                    state.mixed_workspace.load_catalog_data()

                state.mixed_state["active_games"] = None

            state.mixed_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.mixed_workspace.tkraise()
            state.workspace = state.mixed_workspace

        elif target == "analysis":
            state.analysis_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
            state.analysis_workspace.tkraise()
            state.workspace = state.analysis_workspace


        elif target == "patterns":

            state.patterns_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

            state.patterns_workspace.tkraise()

            state.workspace = state.patterns_workspace

            if hasattr(state.patterns_workspace, "refresh_view"):
                state.patterns_workspace.refresh_view()


        elif target == "patterns_analysis":

            initial_games = kwargs.get("initial_games") or state.patterns_state.get("active_games")

            target_game = kwargs.get("target_game") or state.patterns_state.get("active_focus")

            if initial_games and hasattr(state.patterns_analysis_workspace, "load_patterns_collection"):
                state.patterns_analysis_workspace.load_patterns_collection(initial_games, target_game=target_game)

            state.patterns_analysis_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

            state.patterns_analysis_workspace.tkraise()

            state.workspace = state.patterns_analysis_workspace


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = Totten()
    app.mainloop()