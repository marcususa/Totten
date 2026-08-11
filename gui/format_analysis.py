import gui.app_state as state

# File 3 module titled "format_analysis.py"

def set_status_message(text: str):
    if hasattr(state, "status") and state.status:
        state.status.configure(text=text)

class FormatAnalysisMixin:
    def _sync_analysis_selection(self):
        """Redraws the analysis text in standard flowing PGN format with word-wrapping, comments in {}, and active move highlight."""
        if not hasattr(self, "current_node") or not self.current_node or not hasattr(self, "analysis_rows"):
            return

        board = self.current_node.board()
        fullmove_number = board.fullmove_number
        is_white_turn = board.turn  # True if white's turn next, meaning black just moved

        if is_white_turn:
            target_move_num = fullmove_number - 1
            active_side = "black"
        else:
            target_move_num = fullmove_number
            active_side = "white"

        self.moves_textbox.configure(state="normal")
        self.moves_textbox.delete("1.0", "end")

        # Clear any tab stops so text flows and wraps naturally across the block
        self.moves_textbox._textbox.config(tabs=())

        active_line_index = None

        for m_num in sorted(self.analysis_rows.keys()):
            data = self.analysis_rows[m_num]
            w_text = data["white"]
            b_text = data["black"]
            w_tag = data.get("white_tag", "default")
            b_tag = data.get("black_tag", "default")

            w_comment = data.get("white_comment", "").strip()
            b_comment = data.get("black_comment", "").strip()

            # Move number prefix (no leading spaces on the very first move)
            self.moves_textbox.insert("end", f"{m_num}. ")

            # --- WHITE MOVE ---
            w_display = f" {w_text} "
            if m_num == target_move_num and active_side == "white":
                self.moves_textbox.insert("end", w_display, ("active_move", w_tag))
                active_line_index = self.moves_textbox.index("end-1c")
            else:
                self.moves_textbox.insert("end", w_display, (w_tag,))

            if w_comment:
                self.moves_textbox.insert("end", f" {{{w_comment}}} ")

            # Space between white and black
            self.moves_textbox.insert("end", " ")

            # --- BLACK MOVE ---
            b_display = f" {b_text} "
            if m_num == target_move_num and active_side == "black":
                self.moves_textbox.insert("end", b_display, ("active_move", b_tag))
                active_line_index = self.moves_textbox.index("end-1c")
            else:
                self.moves_textbox.insert("end", b_display, (b_tag,))

            if b_comment:
                self.moves_textbox.insert("end", f" {{{b_comment}}} ")

            # Space between move pairs
            self.moves_textbox.insert("end", "   ")

        if active_line_index:
            self.moves_textbox.see(active_line_index)

        self.moves_textbox.configure(state="disabled")

    def on_prev_move(self):
        if hasattr(self, "current_node") and self.current_node and self.current_node.parent:
            self.current_node = self.current_node.parent
            self._update_active_boards(self.current_node.board())
            self._sync_analysis_selection()
            if hasattr(state, "status") and state.status:
                state.status.configure(text="Moved to previous position.")

    def on_next_move(self):
        if hasattr(self, "current_node") and self.current_node and self.current_node.variations:
            self.current_node = self.current_node.variations[0]
            self._update_active_boards(self.current_node.board())
            self._sync_analysis_selection()
            if hasattr(state, "status") and state.status:
                state.status.configure(text="Moved to next position.")

    def on_first_move(self):
        if hasattr(self, "root_game_node") and self.root_game_node:
            self.current_node = self.root_game_node
            self._update_active_boards(self.current_node.board())
            self._sync_analysis_selection()
            if hasattr(state, "status") and state.status:
                state.status.configure(text="Jumped to start of game.")

    def on_last_move(self):
        if hasattr(self, "root_game_node") and self.root_game_node:
            node = self.root_game_node
            while node.variations:
                node = node.variations[0]
            self.current_node = node
            self._update_active_boards(self.current_node.board())
            self._sync_analysis_selection()
            if hasattr(state, "status") and state.status:
                state.status.configure(text="Jumped to end of game.")