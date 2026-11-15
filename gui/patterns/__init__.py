import customtkinter as ctk
from core.constants import THEME, LAYOUT

from .patterns_actions import PatternsInitMixin, mark_move_good, mark_move_bad
from .patterns_search import PatternsSearchMixin
from .patterns_analysis_layout import PatternsAnalysisLayoutMixin
from .patterns_analysis_navigation import PatternsAnalysisNavigationMixin
from .patterns_analysis_board import PatternsAnalysisBoardMixin
from gui.engine_mixins.engine_piece_mixin import EnginePieceMixin
from .patterns_evaluation import PatternsEvaluation


class PatternsAnalysis(
    ctk.CTkFrame,
    PatternsInitMixin,
    PatternsSearchMixin,
    PatternsAnalysisLayoutMixin,
    PatternsAnalysisNavigationMixin,
    PatternsAnalysisBoardMixin,
    EnginePieceMixin,
    PatternsEvaluation,
):
    """
    Unified workspace controller combining actions, search, layout, navigation, and board mixins.
    """
    def __init__(self, parent, filename=None, initial_games=None, target_game=None, active_index=None, target_piece=None, *args, **kwargs):
        kwargs.pop('target_game', None)
        kwargs.pop('active_index', None)
        kwargs.pop('target_piece', None)

        super().__init__(parent, fg_color=THEME["bg_panel"], corner_radius=0, *args, **kwargs)

        import gui.app_state as state
        self.filename = filename or "personal_catalog.pgn"

        if not initial_games and hasattr(state, "catalog_state"):
            initial_games = state.catalog_state.get("active_games")

        if not initial_games and hasattr(state, "all_games"):
            initial_games = state.all_games

        self.game_list = list(initial_games) if initial_games else []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}

        self.active_game = None
        self.root_game_node = None
        self.current_node = None
        self.active_engine_mode = None
        self.analysis_rows = {}
        self._cached_analysis_box = None

        resolved_piece = (
            target_piece or
            (state.patterns_state.get("target_piece") if hasattr(state, "patterns_state") and isinstance(state.patterns_state, dict) else None) or
            getattr(state, "selected_piece", None) or
            "N"
        )
        self.target_piece = resolved_piece
        self.active_sequence = []

        # 1. Initialize Layout
        if hasattr(self, "init_layout"):
            self.init_layout()

        # 2. Caches and bindings
        if hasattr(self, "_find_and_cache_analysis_box"):
            self._find_and_cache_analysis_box()
        if hasattr(self, "load_catalog_data"):
            self.load_catalog_data()
        if hasattr(self, "_bind_engine_buttons"):
            self._bind_engine_buttons()
        if hasattr(self, "_bind_global_shortcuts"):
            self._bind_global_shortcuts()

        # 3. Load initial game
        if self.game_list and hasattr(self, "load_game"):
            self.load_game(self.game_list[0])

        # 4. Board widget bindings
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self, "on_prev_move"):
                self.board_widget.on_step_back = self.on_prev_move
            if hasattr(self, "on_next_move"):
                self.board_widget.on_step_forward = self.on_next_move
            if hasattr(self, "on_first_move"):
                self.board_widget.on_jump_start = self.on_first_move
            if hasattr(self, "on_last_move"):
                self.board_widget.on_jump_end = self.on_last_move

        self.after(50, self.focus_force)

    def _safe_load_game(self, game_node, category_source=None):
        if category_source and category_source != "patterns":
            return
        import gui.app_state as state_ref
        if hasattr(state_ref, "patterns_state"):
            state_ref.patterns_state["active_index"] = 0
            state_ref.patterns_state["active_focus"] = None
        self._auto_select_first_game(retries=10)

    def _auto_select_first_game(self, retries=10):
        if hasattr(self, "pgn_tree") and self.pgn_tree:
            children = self.pgn_tree.get_children()
            if children:
                first_item = children[0]
                self.pgn_tree.selection_set(first_item)
                self.pgn_tree.focus(first_item)
                self.pgn_tree.yview_moveto(0.0)
                self.after_idle(lambda: self.pgn_tree.yview_moveto(0.0))
                self._on_tree_selection_event(None)
                return
        if retries > 0:
            self.after(50, lambda: self._auto_select_first_game(retries - 1))

    def toggle_pgn_data_panel(self):
        if hasattr(self, "pgn_data_panel") and self.pgn_data_panel.winfo_ismapped():
            self.pgn_data_panel.grid_remove()
            if hasattr(self, "right_analysis_panel"):
                self.right_analysis_panel.rowconfigure(2, weight=0, minsize=0)
                self.right_analysis_panel.rowconfigure(1, weight=4)
            if hasattr(self, "analysis_container_frame"):
                self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 0))
        else:
            if hasattr(self, "analysis_container_frame"):
                self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))
            if hasattr(self, "right_analysis_panel"):
                self.right_analysis_panel.rowconfigure(1, weight=3)
                self.right_analysis_panel.rowconfigure(2, weight=1, minsize=0)
            if hasattr(self, "pgn_data_panel"):
                self.pgn_data_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)


def create_workspace(master, initial_games=None, **kwargs):
    import gui.app_state as state_mod

    if initial_games is None:
        initial_games = (
            getattr(state_mod, "catalog_state", {}).get("active_games") or
            getattr(state_mod, "active_group_games", None) or
            getattr(state_mod, "active_search_results", None) or
            getattr(state_mod, "active_category_source", None) or
            getattr(state_mod, "all_games", None)
        )

    active_index = kwargs.get("active_index", getattr(state_mod, "catalog_state", {}).get("active_index", 0))

    defocus = (
        kwargs.get("target_game") or
        getattr(state_mod, "catalog_state", {}).get("active_focus") or
        getattr(state_mod, "active_focus_game", None)
    )

    target_piece = (
        kwargs.get("target_piece") or
        (state_mod.patterns_state.get("target_piece") if hasattr(state_mod, "patterns_state") and isinstance(state_mod.patterns_state, dict) else None) or
        getattr(state_mod, "selected_piece", None) or
        "N"
    )

    instance = PatternsAnalysis(
        master,
        filename="personal_catalog.pgn",
        initial_games=initial_games,
        target_game=defocus,
        active_index=active_index,
        target_piece=target_piece
    )
    state_mod.workspace = instance
    return instance


def create_patterns_analysis_workspace(master, initial_games=None, **kwargs):
    return create_workspace(master, initial_games=initial_games, **kwargs)


PatternsWorkspace = PatternsAnalysis