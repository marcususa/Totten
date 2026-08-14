import customtkinter as ctk
from tkinter import ttk
import gui.app_state as state
from gui.search_catalog_workspace import SearchCatalogWorkspace
from gui.edit_workspace import EditWorkspace
from gui.calendar_workspace import CalendarWorkspace
from gui.patterns_workspace import PatternsWorkspace

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

    def refresh_view(self):
        """Called by WorkspaceManager every time this workspace is brought into view."""
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # Re-assert explicit styling to prevent theme resets on toggle
        style.configure(
            "Borderless.Treeview.Heading",
            background="#0f172a",
            foreground="#f8fafc",
            font=("Arial", 10, "bold"),
            relief="flat",
            borderwidth=0
        )
        style.map(
            "Borderless.Treeview.Heading",
            background=[('active', '#0f172a'), ('selected', '#0f172a'), ('!active', '#0f172a')],
            foreground=[('active', '#f8fafc'), ('selected', '#f8fafc'), ('!active', '#f8fafc')]
        )


class WorkspaceManager(ctk.CTkFrame):
    """
    Manages the active workspace container and switches between views
    (Analysis, Catalog, Edit, Patterns, Mixed Collections, Calendar) using lazy loading.
    """

    def __init__(self, master, app_state=None):
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.app_state = app_state or state

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.workspaces = {}
        self.current_workspace_key = None

        # Default fallback dictionary references for legacy compatibility
        state.workspaces = self.workspaces

        # Load default view ("analysis") immediately, defer others
        self.show_workspace("analysis")

    def _init_workspace_instance(self, key):
        """Lazy-load individual workspaces only when they are requested for the first time."""
        if key in self.workspaces:
            return

        target_key = key.lower().strip()
        if target_key in ("analysis", "pgn_games"):
            analysis_ws = AnalysisWorkspace(self, app_state=self.app_state)
            self.workspaces["analysis"] = analysis_ws
            self.workspaces["pgn_games"] = analysis_ws  # Legacy alias fallback
        elif target_key == "catalog":
            catalog_ws = SearchCatalogWorkspace(self, self.app_state)
            self.workspaces["catalog"] = catalog_ws
        elif target_key == "edit":
            edit_ws = EditWorkspace(self, self.app_state)
            self.workspaces["edit"] = edit_ws
        elif target_key == "patterns":
            patterns_ws = PatternsWorkspace(self, app_state=self.app_state)
            self.workspaces["patterns"] = patterns_ws
        elif target_key == "mixed_collections":
            mixed_ws = ctk.CTkFrame(self, fg_color="#172134")
            ctk.CTkLabel(mixed_ws, text="Mixed Collections Workspace", font=("Arial", 16), text_color="#94a3b8").pack(
                expand=True)
            self.workspaces["mixed_collections"] = mixed_ws
        elif target_key == "calendar":
            calendar_ws = CalendarWorkspace(self, self.app_state)
            self.workspaces["calendar"] = calendar_ws

        # Grid and hide the newly initialized workspace safely
        if target_key in self.workspaces:
            ws = self.workspaces[target_key]
            ws.grid(row=0, column=0, sticky="nsew")
            ws.grid_remove()

    def show_workspace(self, key):
        target_key = key.lower().strip()
        if target_key == "pgn_games":
            target_key = "analysis"

        if target_key not in ["analysis", "catalog", "edit", "patterns", "mixed_collections", "calendar"]:
            target_key = "analysis"

        # Ensure the target workspace is initialized before trying to show it
        if target_key not in self.workspaces:
            self._init_workspace_instance(target_key)

        # Hide all currently active mapped workspaces gracefully
        for ws in self.workspaces.values():
            ws.grid_remove()

        workspace = self.workspaces[target_key]
        workspace.grid()
        workspace.tkraise()
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
    """Allows sidebar navigation and external modules to switch views."""
    if _workspace_manager_instance:
        _workspace_manager_instance.show_workspace(key)


def show_analysis_workspace():
    """Globally accessible function to programmatically switch to the Analysis workspace."""
    if _workspace_manager_instance:
        _workspace_manager_instance.show_workspace("analysis")

# Register it automatically so app_state can reach it
state.show_analysis_workspace = show_analysis_workspace

