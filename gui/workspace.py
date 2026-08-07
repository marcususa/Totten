# gui/workspace.py

import customtkinter as ctk
import gui.app_state as state
from gui.search_catalog_workspace import SearchCatalogWorkspace
from gui.edit_workspace import EditWorkspace
from gui.calendar_workspace import CalendarWorkspace

# Import your 4 modular analysis pieces
from gui.layout_analysis import LayoutAnalysisMixin
from gui.catalog_analysis import CatalogAnalysisMixin
from gui.engine_analysis import EngineAnalysisMixin
from gui.format_analysis import FormatAnalysisMixin


class AnalysisWorkspace(
    ctk.CTkFrame,
    LayoutAnalysisMixin,
    CatalogAnalysisMixin,
    EngineAnalysisMixin,
    FormatAnalysisMixin
):
    """Combined workspace class uniting the UI layout, catalog bindings, engine worker, and move formatting."""

    def __init__(self, master, filename=None, app_state=None):
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.filename = filename
        self.app_state = app_state or state

        # 1. Build the visual elements (board, textboxes, treeview, engine buttons 1, 2, 3)
        self.init_layout()

        # 2. Hook up catalog bindings and load PGN games into the tree
        self.init_catalog_bindings()


class WorkspaceManager(ctk.CTkFrame):
    """
    Manages the active workspace container and switches between views
    (Analysis, Catalog, Edit, Mixed Collections, Calendar).
    """

    def __init__(self, master, app_state=None):
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.app_state = app_state or state

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.workspaces = {}
        self.current_workspace_key = None

        self._init_workspaces()

    def _init_workspaces(self):
        # 1. Analysis Workspace (Board, Catalog tree, Move textboxes, and 3 Engine modes)
        analysis_ws = AnalysisWorkspace(self, app_state=self.app_state)
        self.workspaces["analysis"] = analysis_ws
        self.workspaces["pgn_games"] = analysis_ws  # Legacy alias fallback

        # 2. Catalog
        catalog_ws = SearchCatalogWorkspace(self, self.app_state)
        self.workspaces["catalog"] = catalog_ws

        # 3. Edit Workspace
        edit_ws = EditWorkspace(self, self.app_state)
        self.workspaces["edit"] = edit_ws

        # 4. Mixed Collections (Placeholder)
        mixed_ws = ctk.CTkFrame(self, fg_color="#172134")
        ctk.CTkLabel(mixed_ws, text="Mixed Collections Workspace", font=("Arial", 16), text_color="#94a3b8").pack(
            expand=True)
        self.workspaces["mixed_collections"] = mixed_ws

        # 5. Calendar & Historical Notes Workspace (Replacing old notes section)
        calendar_ws = CalendarWorkspace(self, app_state=self.app_state)
        self.workspaces["calendar"] = calendar_ws

        # Grid all workspaces on top of each other; hide by default
        for ws in self.workspaces.values():
            ws.grid(row=0, column=0, sticky="nsew")
            ws.grid_remove()

    def show_workspace(self, key):
        target_key = key.lower().strip()
        if target_key not in self.workspaces:
            target_key = "analysis"

        workspace = self.workspaces[target_key]
        workspace.tkraise()
        workspace.grid()
        self.current_workspace_key = target_key

        if hasattr(workspace, "refresh_view"):
            workspace.refresh_view()


# Global hook references
_workspace_manager_instance = None


def create_workspace(master, app_state=None):
    global _workspace_manager_instance
    _workspace_manager_instance = WorkspaceManager(master, app_state)
    state.workspace = _workspace_manager_instance
    state.workspaces = _workspace_manager_instance.workspaces
    return _workspace_manager_instance


def show_workspace(key):
    if _workspace_manager_instance:
        _workspace_manager_instance.show_workspace(key)