import customtkinter as ctk

from layout_workspace import LayoutAnalysisMixin
from catalog_analysis import CatalogAnalysisMixin
from format_analysis import FormatAnalysisMixin
from engine_analysis import EngineAnalysisMixin
import app_state as state


class AnalysisWorkspace(
    ctk.CTkFrame,
    LayoutAnalysisMixin,
    CatalogAnalysisMixin,
    FormatAnalysisMixin,
    EngineAnalysisMixin
):
    def __init__(self, master, filename=None, app_state=None):
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.app_state = app_state or state
        self.filename = filename

        # 1. Initialize UI layout and register the global cross-workspace callback
        self.init_layout()

        # 2. Initialize catalog tree bindings and load games into the second workspace tree
        self.init_catalog_bindings()

        # 3. Check if a game was already selected in workspace 1 before loading this view
        self.check_initial_state()

    def check_initial_state(self):
        """Checks if an active game was already selected in workspace 1 before loading."""
        if hasattr(state, "active_analysis_game") and state.active_analysis_game:
            self.load_game_from_state(state.active_analysis_game)