import customtkinter as ctk
import gui.app_state as state
from gui.search_catalog_workspace import SearchCatalogWorkspace
from gui.analysis_workspace import AnalysisWorkspace


class WorkspaceManager(ctk.CTkFrame):
    """
    Manages switching between the catalog view and the catalog analysis workspace.
    """

    def __init__(self, master, *args, **kwargs):
        super().__init__(master, fg_color="#172134", corner_radius=0, *args, **kwargs)

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.workspaces = {}

        # Initialize Catalog Search View
        self.catalog_workspace = SearchCatalogWorkspace(self, app_state=state)
        self.catalog_workspace.grid(row=0, column=0, sticky="nsew")
        self.workspaces["catalog_workspace"] = self.catalog_workspace
        self.workspaces["catalog"] = self.catalog_workspace

        # Initialize Catalog Analysis View
        self.analysis_workspace = AnalysisWorkspace(self, app_state=state)
        self.analysis_workspace.grid(row=0, column=0, sticky="nsew")
        self.workspaces["analysis"] = self.analysis_workspace
        self.workspaces["analysis_workspace"] = self.analysis_workspace

        # Hide analysis initially
        self.analysis_workspace.grid_remove()

        # Expose references on app_state for global accessibility
        state.workspace = self
        state.catalog_workspace = self.catalog_workspace
        state.analysis_workspace = self.analysis_workspace

    def show_workspace(self, name):
        """Switches the active workspace view."""
        ws = self.workspaces.get(name)
        if ws:
            ws.tkraise()
            if hasattr(ws, "refresh_current_view"):
                ws.refresh_current_view()

    def load_game_and_switch(self, game_obj, target_workspace="analysis"):
        """Loads a game object into analysis and switches view."""
        if target_workspace in ("analysis", "analysis_workspace"):
            if hasattr(self.analysis_workspace, "load_game"):
                self.analysis_workspace.load_game(game_obj)
            self.show_workspace("analysis")


def create_workspace(master):
    """Factory function to instantiate and return the workspace manager."""
    manager = WorkspaceManager(master)
    state.workspace = manager
    return manager


def show_workspace(name):
    """Global helper to switch workspaces via the active manager instance."""
    if hasattr(state, "workspace") and state.workspace:
        if hasattr(state.workspace, "show_workspace"):
            state.workspace.show_workspace(name)