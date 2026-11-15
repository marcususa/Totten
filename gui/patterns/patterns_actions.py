import customtkinter as ctk

CONFIRMED_GOOD_MOVES = set()
REJECTED_BAD_MOVES = set()

def mark_move_good(clean_san: str):
    CONFIRMED_GOOD_MOVES.add(clean_san)
    REJECTED_BAD_MOVES.discard(clean_san)

def mark_move_bad(clean_san: str):
    REJECTED_BAD_MOVES.add(clean_san)
    CONFIRMED_GOOD_MOVES.discard(clean_san)

class PatternsInitMixin:
    """Mixin class to handle the UI initialization, layout, and yellow pattern matching for PatternsAnalysis."""

    def _safe_load_game(self, game_node, category_source=None):
        if category_source and category_source != "patterns":
            return
        self.load_game(game_node, category_source=category_source)

    def toggle_pgn_data_panel(self):
        """Toggles visibility of the Game Details panel (Row 3) while strictly protecting the Eval Bar (Row 1)."""
        if hasattr(self, "pgn_data_panel") and self.pgn_data_panel.winfo_ismapped():
            # 1. Hide Game Details panel
            self.pgn_data_panel.grid_remove()

            # 2. Lock Row 1 (Good/Bad/IDK) height strictly so it cannot collapse
            self.right_analysis_panel.rowconfigure(1, weight=0, minsize=32)

            # 3. Collapse Row 3
            self.right_analysis_panel.rowconfigure(3, weight=0, minsize=0)

            # 4. Expand Row 2 (Analysis) to take all remaining vertical space
            self.right_analysis_panel.rowconfigure(2, weight=1)

            # 5. Remove bottom padding on analysis container so it fills flush down to the bottom
            self.analysis_container_frame.grid_configure(pady=(0, 0))
        else:
            # 1. Restore bottom padding on analysis container
            self.analysis_container_frame.grid_configure(pady=(0, 8))

            # 2. Re-grid Game Details on Row 3
            self.pgn_data_panel.grid(row=3, column=0, sticky="nsew", padx=0, pady=0)

            # 3. Restore row weights for Row 1, Row 2, and Row 3
            self.right_analysis_panel.rowconfigure(1, weight=0, minsize=32)
            self.right_analysis_panel.rowconfigure(2, weight=3)
            self.right_analysis_panel.rowconfigure(3, weight=1, minsize=70)

        # Ensure Row 1 eval_bar_frame remains strictly attached to Row 1
        if hasattr(self, "eval_bar_frame"):
            self.eval_bar_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 8))

    def _eval_good_action(self):
        if hasattr(self, "on_eval_good") and callable(self.on_eval_good):
            self.on_eval_good()

    def _eval_bad_action(self):
        if hasattr(self, "on_eval_bad") and callable(self.on_eval_bad):
            self.on_eval_bad()

    def _eval_idk_action(self):
        if hasattr(self, "on_eval_idk") and callable(self.on_eval_idk):
            self.on_eval_idk()

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and hasattr(self.board_widget, "flip_board"):
            self.board_widget.flip_board()
        elif hasattr(self, "board_widget") and hasattr(self.board_widget, "invert"):
            self.board_widget.invert()

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