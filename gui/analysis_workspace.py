import customtkinter as ctk
import gui.app_state as state
from gui.layout_analysis import LayoutAnalysisMixin


class AnalysisWorkspace(ctk.CTkFrame, LayoutAnalysisMixin):
    """
    Core analysis workspace view for Totten, inheriting layout geometry from LayoutAnalysisMixin
    and providing game state management, move navigation, and engine interaction.
    """

    def __init__(self, master, app_state=None, *args, **kwargs):
        kwargs.pop("app_state", None)
        super().__init__(master, fg_color="#172134", corner_radius=0, *args, **kwargs)
        self.app_state = app_state or state

        # Initialize layout elements from mixin
        self.init_layout()
        self._bind_keys()

    def _bind_keys(self):
        top = self.winfo_toplevel()
        top.bind("<Left>", lambda e: self.on_prev_move())
        top.bind("<Right>", lambda e: self.on_next_move())
        top.bind("<Up>", lambda e: self.on_first_move())
        top.bind("<Down>", lambda e: self.on_last_move())

    def on_prev_move(self):
        if hasattr(self, "current_node") and self.current_node and self.current_node.parent:
            self.current_node = self.current_node.parent
            self.load_game_from_state(self.current_node)

    def on_next_move(self):
        if hasattr(self, "current_node") and self.current_node and self.current_node.variations:
            self.current_node = self.current_node.variation(0)
            self.load_game_from_state(self.current_node)

    def on_first_move(self):
        if hasattr(self, "root_game_node") and self.root_game_node:
            self.current_node = self.root_game_node
            self.load_game_from_state(self.current_node)

    def on_last_move(self):
        if hasattr(self, "root_game_node") and self.root_game_node:
            node = self.root_game_node
            while node.variations:
                node = node.variation(0)
            self.current_node = node
            self.load_game_from_state(self.current_node)

    def load_game(self, game_node, category_source=None):
        """Standardized entry point called when loading a game into analysis."""
        if not game_node:
            return
        self.load_game_from_state(game_node, category_source=category_source)

    def trigger_engine_mode(self, mode):
        """Handles switching between engine analysis views (review, candidates, standard)."""
        self.active_engine_mode = mode

        # Update button visual states if buttons exist
        btns = {
            "review": getattr(self, "btn_review", None),
            "candidates": getattr(self, "btn_candidates", None),
            "standard": getattr(self, "btn_standard", None)
        }

        for m, btn in btns.items():
            if btn:
                if m == mode:
                    btn.configure(fg_color="#2e4a8c", hover_color="#4870cd")
                else:
                    btn.configure(fg_color="#1e293b", hover_color="#334155")

        # Toggle textbox displays based on mode
        if hasattr(self, "review_container") and hasattr(self, "candidates_container"):
            if mode == "review":
                self.candidates_container.pack_forget()
                self.review_container.pack(fill="both", expand=True)
            elif mode == "candidates":
                self.review_container.pack_forget()
                self.candidates_container.pack(fill="both", expand=True)
            else:
                self.candidates_container.pack_forget()
                self.review_container.pack(fill="both", expand=True)


def create_workspace(master):
    """Instantiates the AnalysisWorkspace and registers it in application state."""
    instance = AnalysisWorkspace(master)
    state.workspace = instance
    state.analysis_workspace = instance
    return instance