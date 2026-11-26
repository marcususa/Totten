from core.constants import THEME
from gui.engine_mixins.engine_review_mixin import EngineReviewMixin
from gui.engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from gui.engine_mixins.engine_standard_mixin import EngineStandardMixin


class CatalogNavigationMixin:
    """Mixin class to handle board traversal steps and node jumps cleanly."""

    def _ensure_valid_game(self):
        import gui.app_state as state_mod

        if not hasattr(self, "active_games") or not self.active_games:
            if hasattr(state_mod, "catalog_state") and state_mod.catalog_state.get("active_games"):
                self.active_games = state_mod.catalog_state["active_games"]

        if isinstance(getattr(self, "current_game", None), int):
            if hasattr(self, "active_games") and self.active_games:
                idx = max(0, min(self.current_game, len(self.active_games) - 1))
                self.current_game = self.active_games[idx]

        if isinstance(getattr(self, "board_node", None), int) or not getattr(self, "board_node", None):
            if hasattr(self, "current_game") and self.current_game:
                self.board_node = self.current_game.root() if hasattr(self.current_game, "root") else self.current_game
            elif hasattr(self, "active_games") and self.active_games:
                self.current_game = self.active_games[0]
                self.board_node = self.current_game.root() if hasattr(self.current_game, "root") else self.current_game

    def _apply_node_position(self, node):
        if not node:
            return
        self.board_node = node
        self.current_node = node
        if hasattr(self, "board_widget") and self.board_widget:
            try:
                self.board_widget.set_position_fen(node.board().fen())
            except Exception:
                pass
        if hasattr(self, "update_active_move_highlight"):
            self.update_active_move_highlight()
        if hasattr(self, "notify_live_engine_position_changed"):
            self.notify_live_engine_position_changed()

    def on_prev_move(self, event=None):
        self._ensure_valid_game()
        if hasattr(self, "board_node") and self.board_node and hasattr(self.board_node, "parent") and self.board_node.parent:
            self._apply_node_position(self.board_node.parent)
        return "break"

    def on_next_move(self, event=None):
        self._ensure_valid_game()
        if hasattr(self, "board_node") and self.board_node and hasattr(self.board_node, "variations") and self.board_node.variations:
            self._apply_node_position(self.board_node.variation(0))
        return "break"

    def on_first_move(self, event=None):
        self._ensure_valid_game()
        if hasattr(self, "current_game") and self.current_game:
            root = self.current_game.root() if hasattr(self.current_game, "root") else self.current_game
            self._apply_node_position(root)

    def on_last_move(self, event=None):
        self._ensure_valid_game()
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game.root() if hasattr(self.current_game, "root") else self.current_game
            while hasattr(node, "variations") and node.variations:
                node = node.variation(0)
            self._apply_node_position(node)

    def jump_to_node(self, node):
        self._apply_node_position(node)

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self.board_widget, "flip_board"):
                self.board_widget.flip_board()
            elif hasattr(self.board_widget, "invert"):
                self.board_widget.invert()
            elif hasattr(self.board_widget, "toggle_flip"):
                self.board_widget.toggle_flip()

    def trigger_engine_mode(self, mode):
        self.active_engine_mode = mode
        self._selected_mode_button = mode
        self._last_tracked_node = None

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
            if getattr(self, "_engine_running", False) and hasattr(self, "stop_raw_engine_analysis"):
                self.stop_raw_engine_analysis()
            if hasattr(self, "update_engine_display"):
                self.update_engine_display("")
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")


def create_workspace(master, initial_games=None, **kwargs):
    import gui.app_state as state_mod
    from .core import CatalogAnalysis
    from .catalog_view import SearchCatalogWorkspace

    workspace_name = kwargs.get("name") or kwargs.get("workspace_name")

    if workspace_name in ("search_catalog", "catalog") or initial_games in ("search_catalog", "catalog"):
        clean_kwargs = kwargs.copy()
        for k in ("target_game", "active_index", "initial_games", "name", "workspace_name"):
            clean_kwargs.pop(k, None)
        instance = SearchCatalogWorkspace(master, **clean_kwargs)
        state_mod.workspace = instance
        return instance

    if initial_games is None:
        initial_games = (
            getattr(state_mod, "catalog_state", {}).get("active_games")
            or getattr(state_mod, "active_group_games", None)
            or getattr(state_mod, "active_search_results", None)
            or getattr(state_mod, "active_category_source", None)
        )

    instance = CatalogAnalysis(master, filename="personal_catalog.pgn", initial_games=initial_games)
    state_mod.workspace = instance
    return instance