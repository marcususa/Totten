import customtkinter as ctk
import gui.app_state as state

from core.constants import THEME
from gui.patterns.patterns_init_mixin import PatternsInitMixin
from gui.engine_mixins.engine_piece_mixin import EnginePieceMixin
from gui.patterns.patterns_analysis_navigation import PatternsAnalysisNavigationMixin
from gui.patterns.patterns_analysis_board import PatternsAnalysisBoardMixin
from gui.patterns.patterns_evaluation import PatternsEvaluation


class PatternsAnalysis(
    ctk.CTkFrame,
    PatternsInitMixin,
    PatternsAnalysisNavigationMixin,
    PatternsAnalysisBoardMixin,
    EnginePieceMixin,
    PatternsEvaluation,
):
    """
    Dedicated workspace controller for Patterns Analysis UI layout, shortcuts, and bindings.
    Inherits evaluation and comparison engine logic from PatternsEvaluation.
    """

    def __init__(self, parent, filename=None, initial_games=None, target_game=None, active_index=None,
                 target_piece=None, *args, **kwargs):
        kwargs.pop('target_game', None)
        kwargs.pop('active_index', None)
        kwargs.pop('target_piece', None)

        super().__init__(parent, fg_color=THEME["bg_panel"], corner_radius=0, *args, **kwargs)

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
            (state.patterns_state.get("target_piece") if hasattr(state, "patterns_state") and isinstance(
                state.patterns_state, dict) else None) or
            getattr(state, "selected_piece", None) or
            "N"
        )
        self.target_piece = resolved_piece
        self.active_sequence = []

        self.init_layout()
        self._find_and_cache_analysis_box()
        self.load_catalog_data()
        self._bind_engine_buttons()
        self._bind_global_shortcuts()

        # FORCE ALWAYS STARTING AT THE TOP (Index 0)
        if self.game_list and hasattr(self, "load_game"):
            self.load_game(self.game_list[0])

        if hasattr(self, "board_widget") and self.board_widget:
            self.board_widget.on_step_back = self.on_prev_move
            self.board_widget.on_step_forward = self.on_next_move
            self.board_widget.on_jump_start = self.on_first_move
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
        if self.pgn_data_panel.winfo_ismapped():
            self.pgn_data_panel.grid_remove()
            self.right_analysis_panel.rowconfigure(2, weight=0, minsize=0)
            self.right_analysis_panel.rowconfigure(1, weight=4)
            self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 0))
        else:
            self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))
            self.right_analysis_panel.rowconfigure(1, weight=3)
            self.right_analysis_panel.rowconfigure(2, weight=1, minsize=0)
            self.pgn_data_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

    def on_flip_board(self, event=None):
        """Explicitly calls toggle_flip() on the board widget when 'f' or 'F' is pressed."""
        try:
            if hasattr(self, "board_widget") and self.board_widget:
                if hasattr(self.board_widget, "toggle_flip") and callable(self.board_widget.toggle_flip):
                    self.board_widget.toggle_flip()
                    print("[BOARD DEBUG] Board widget toggle_flip() executed successfully.")
                elif hasattr(self.board_widget, "flip_board"):
                    self.board_widget.flip_board()
                elif hasattr(self.board_widget, "invert"):
                    self.board_widget.invert()
        except Exception as e:
            print(f"[BOARD FLIP ERROR] {e}")

    def _handle_keypress(self, event=None):
        if event and event.keysym in ("f", "F"):
            self.on_flip_board()
            return "break"

    def _handle_left(self, event=None):
        if hasattr(self, "on_prev_move") and callable(self.on_prev_move):
            try:
                self.on_prev_move(event)
            except TypeError:
                self.on_prev_move()
        return "break"

    def _handle_right(self, event=None):
        if hasattr(self, "on_next_move") and callable(self.on_next_move):
            try:
                self.on_next_move(event)
            except TypeError:
                self.on_next_move()
        return "break"

    def _handle_up(self, event=None):
        if hasattr(self, "on_first_move") and callable(self.on_first_move):
            try:
                self.on_first_move(event)
            except TypeError:
                self.on_first_move()
        return "break"

    def _handle_down(self, event=None):
        if hasattr(self, "on_last_move") and callable(self.on_last_move):
            try:
                self.on_last_move(event)
            except TypeError:
                self.on_last_move()
        return "break"

    def _on_tree_selection_event(self, event):
        selected_items = self.pgn_tree.selection()
        if not selected_items:
            return
        item_id = selected_items[0]
        if hasattr(self, "preview_lookup") and item_id in self.preview_lookup:
            game = self.preview_lookup[item_id]

            if hasattr(self, "analysis_textbox"):
                self.analysis_textbox.delete("1.0", "end")
            if hasattr(self, "pgn_data_text"):
                self.pgn_data_text.delete("1.0", "end")

            if hasattr(self, "on_hardwired_tree_select"):
                self.on_hardwired_tree_select(game)
            else:
                self.load_game(game)

    def _bind_engine_buttons(self):
        # --- Standalone Engine Comparison Button ---
        if hasattr(self, "btn_pv") and self.btn_pv:
            self.btn_pv.configure(
                text="Engine",
                command=self.toggle_engine_action,
                hover_color=THEME["btn_hover"]
            )

        # --- White Patterns ---
        for btn_name in ("btn_white", "btn_white_patterns"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(
                    text="White Patterns",
                    command=lambda: (print("[DEBUG CLICK] White Patterns clicked!"),
                                     self.trigger_engine_mode("white_patterns_mode")),
                    hover_color=THEME["btn_hover"]
                )
                break

        # --- Black Patterns ---
        for btn_name in ("btn_black", "btn_black_patterns"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(
                    text="Black Patterns",
                    command=lambda: (print("[DEBUG CLICK] Black Patterns clicked!"),
                                     self.trigger_engine_mode("black_patterns_mode")),
                    hover_color=THEME["btn_hover"]
                )
                break

        # --- Opening ---
        if hasattr(self, "btn_opening") and self.btn_opening:
            self.btn_opening.configure(
                text="Opening",
                command=lambda: (print("[DEBUG CLICK] Opening clicked!"),
                                 self.trigger_engine_mode("opening_pattern_mode")),
                hover_color=THEME["btn_hover"]
            )

        # --- Calculation ---
        if hasattr(self, "btn_calculation") and self.btn_calculation:
            self.btn_calculation.configure(
                text="Calculation",
                command=lambda: (print("[DEBUG CLICK] Calculation clicked!"),
                                 self.trigger_engine_mode("calculation_pattern_mode")),
                hover_color=THEME["btn_hover"]
            )

    def _bind_global_shortcuts(self):
        try:
            top_level = self.winfo_toplevel()

            for key, callback in [
                ("<Left>", self.on_prev_move),
                ("<Right>", self.on_next_move),
                ("<Up>", self.on_first_move),
                ("<Down>", self.on_last_move),
                ("f", self.on_flip_board),
                ("F", self.on_flip_board)
            ]:
                top_level.bind(key, lambda e, cb=callback: self._safe_handle_shortcut(cb, e))
                self.bind(key, lambda e, cb=callback: self._safe_handle_shortcut(cb, e))

            if hasattr(self, "pgn_tree") and self.pgn_tree:
                self.pgn_tree.bind("<Left>", lambda e: self._safe_handle_shortcut(self.on_prev_move, e))
                self.pgn_tree.bind("<Right>", lambda e: self._safe_handle_shortcut(self.on_next_move, e))
                self.pgn_tree.bind("<Up>", lambda e: self._safe_handle_shortcut(self.on_first_move, e))
                self.pgn_tree.bind("<Down>", lambda e: self._safe_handle_shortcut(self.on_last_move, e))
                self.pgn_tree.bind("f", lambda e: self._safe_handle_shortcut(self.on_flip_board, e))
                self.pgn_tree.bind("F", lambda e: self._safe_handle_shortcut(self.on_flip_board, e))

            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.bind("<Left>", lambda e: self._safe_handle_shortcut(self.on_prev_move, e))
                self.board_widget.bind("<Right>", lambda e: self._safe_handle_shortcut(self.on_next_move, e))
                self.board_widget.bind("f", lambda e: self._safe_handle_shortcut(self.on_flip_board, e))
                self.board_widget.bind("F", lambda e: self._safe_handle_shortcut(self.on_flip_board, e))
        except Exception as e:
            print(f"[SHORTCUT BIND ERROR] {e}")

    def _safe_handle_shortcut(self, callback, event):
        try:
            focused = self.winfo_toplevel().focus_get()
            if focused and type(focused).__name__ in ("CTkTextbox", "CTkEntry", "Text", "Entry"):
                return

            if callable(callback):
                try:
                    callback(event)
                except TypeError:
                    callback()
                return "break"
        except Exception as e:
            print(f"[SHORTCUT EXECUTION ERROR] {e}")


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
        (state_mod.patterns_state.get("target_piece") if hasattr(state_mod, "patterns_state") and isinstance(
            state_mod.patterns_state, dict) else None) or
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