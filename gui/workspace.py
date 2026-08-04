# gui/workspace.py

import customtkinter as ctk
import gui.app_state as state
from gui.search_catalog_workspace import SearchCatalogWorkspace
from gui.import_workspace import ImportWorkspace

# Import the 4 analysis mixin modules
from gui.layout_analysis import LayoutAnalysisMixin
from gui.catalog_analysis import CatalogAnalysisMixin
from gui.format_analysis import FormatAnalysisMixin
from gui.engine_analysis import EngineAnalysisMixin


class PgnGamesWorkspace(
    ctk.CTkFrame,
    LayoutAnalysisMixin,
    CatalogAnalysisMixin,
    FormatAnalysisMixin,
    EngineAnalysisMixin
):
    def __init__(self, parent, filename=None):
        super().__init__(parent, fg_color="#172134", corner_radius=0)
        self.filename = filename
        
        # 1. Build the UI layout from layout_analysis.py
        self.init_layout()
        
        # 2. Bind catalog events & load games from catalog_analysis.py
        self.init_catalog_bindings()


def create_notes_workspace(parent):
    """Creates the Notes frame and loads notes.txt directly."""
    frame = ctk.CTkFrame(parent, fg_color="#172134", corner_radius=0)

    notes_box = ctk.CTkTextbox(
        frame,
        fg_color="#0f172a",
        text_color="#f8fafc",
        font=("Arial", 12)
    )
    notes_box.pack(fill="both", expand=True, padx=10, pady=10)

    try:
        with open("notes.txt", "r") as f:
            notes_box.insert("1.0", f.read())
    except FileNotFoundError:
        pass

    return frame


def create_workspace(app):
    state.workspace = ctk.CTkFrame(
        app,
        fg_color="#172134",
        corner_radius=0
    )

    # Register static workspace views
    state.workspaces = {
        "catalog": SearchCatalogWorkspace(state.workspace, state),
        "pgn_games": PgnGamesWorkspace(state.workspace),
        "notes": create_notes_workspace(state.workspace),
        "import": ImportWorkspace(state.workspace, state),
    }

    # Default startup view
    show_workspace("catalog")

    return state.workspace


def show_workspace(key):
    """Switches the active frame displayed in the main workspace."""
    # Hide all views first
    for view in state.workspaces.values():
        view.pack_forget()

    # Show only the requested view
    if key in state.workspaces:
        if key == "import" and hasattr(state.workspaces[key], "refresh_view"):
            state.workspaces[key].refresh_view()

        state.workspaces[key].pack(fill="both", expand=True)
    else:
        print(f"Warning: Key '{key}' not found in state.workspaces!")