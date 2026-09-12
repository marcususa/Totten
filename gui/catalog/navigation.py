from core.constants import THEME
from gui.engine_mixins.engine_review_mixin import EngineReviewMixin
from gui.engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from gui.engine_mixins.engine_standard_mixin import EngineStandardMixin


class CatalogNavigationMixin:
    """Mixin class to handle board traversal steps, node jumps, and engine mode switching UI updates."""

    def on_prev_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.parent:
            self.board_node = self.board_node.parent
            self.current_node = self.board_node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            self.update_active_move_highlight()
        return "break"

    def on_next_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.variations:
            self.board_node = self.board_node.variation(0)
            self.current_node = self.board_node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            self.update_active_move_highlight()
        return "break"

    def on_first_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            self.board_node = self.current_game
            self.current_node = self.board_node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.current_game.board().fen())
            self.update_active_move_highlight()

    def on_last_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game
            while node.variations:
                node = node.variation(0)
            self.board_node = node
            self.current_node = self.board_node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(node.board().fen())
            self.update_active_move_highlight()

    def jump_to_node(self, node):
        if node:
            self.board_node = node
            self.current_node = node
            if hasattr(self, "board_widget") and self.board_widget:
                try:
                    self.board_widget.set_position_fen(node.board().fen())
                except Exception:
                    pass
            self.update_active_move_highlight()

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self.board_widget, "flip_board"):
                self.board_widget.flip_board()
            elif hasattr(self, "board_widget", "toggle_flip"):
                self.board_widget.toggle_flip()

    def trigger_engine_mode(self, mode):
        self.active_engine_mode = mode
        self._selected_mode_button = mode

        mode_buttons = {
            "review": ("btn_review", "btn_review_mode"),
            "candidates": ("btn_candidates", "btn_candidate_moves"),
            "standard": ("btn_standard", "btn_standard_mode", "btn_engines")
        }

        for m, btn_names in mode_buttons.items():
            is_active = (mode == m)
            for name in btn_names:
                btn = getattr(self, name, None)
                if btn is not None:
                    btn.configure(
                        fg_color=THEME["btn_hover"] if is_active else THEME["btn_initial"],
                        hover_color=THEME["btn_hover"],
                        text_color=THEME["text_primary"],
                    )

        if hasattr(self, "frame_review") and self.frame_review:
            self.frame_review.configure(border_width=0 if mode == "review" else 1)
        if hasattr(self, "frame_candidates") and self.frame_candidates:
            self.frame_candidates.configure(border_width=0 if mode == "candidates" else 1)
        if hasattr(self, "frame_standard") and self.frame_standard:
            self.frame_standard.configure(border_width=0 if mode == "standard" else 1)

        if mode == "review":
            EngineReviewMixin.trigger_engine_mode(self, "review")
        elif mode == "candidates":
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")


def create_workspace(master, initial_games=None, **kwargs):
    import gui.app_state as state_mod
    from .core import CatalogAnalysis
    from .catalog_view import SearchCatalogWorkspace

    workspace_name = kwargs.get("name") or kwargs.get("workspace_name")

    # If explicitly requested via sidebar or router
    if workspace_name in ("search_catalog", "catalog") or initial_games in ("search_catalog", "catalog"):
        clean_kwargs = kwargs.copy()
        for k in ["target_game", "active_index", "initial_games", "name", "workspace_name"]:
            clean_kwargs.pop(k, None)
        instance = SearchCatalogWorkspace(master, **clean_kwargs)
        state_mod.workspace = instance
        return instance

    if initial_games is None:
        initial_games = (
            getattr(state_mod, "catalog_state", {}).get("active_games") or
            getattr(state_mod, "active_group_games", None) or
            getattr(state_mod, "active_search_results", None) or
            getattr(state_mod, "active_category_source", None)
        )

    active_index = kwargs.get("active_index") or getattr(state_mod, "catalog_state", {}).get("active_index", 0)

    focus = (
        kwargs.get("target_game") or
        getattr(state_mod, "catalog_state", {}).get("active_focus") or
        getattr(state_mod, "active_focus_game", None)
    )

    if initial_games and 0 <= active_index < len(initial_games) and not focus:
        focus = initial_games[active_index]

    instance = CatalogAnalysis(master, filename="personal_catalog.pgn", initial_games=initial_games)

    if focus and hasattr(instance, "load_game"):
        instance.load_game(focus)
    elif initial_games and hasattr(instance, "load_game"):
        instance.load_game(initial_games[0])

    state_mod.workspace = instance
    return instance