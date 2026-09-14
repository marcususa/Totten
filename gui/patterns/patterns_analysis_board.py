# gui/patterns/patterns_analysis_board.py

import chess
import chess.pgn
from core.constants import THEME


class PatternsAnalysisBoardMixin:
    """Encapsulates board traversal, FEN rendering, move list highlighting, and global shortcuts."""

    def load_game_hardwired(self, game_node, category_source=None):
        resolved = self._resolve_game_obj(game_node)
        if isinstance(category_source, list):
            self.game_list = category_source
            self.populate_catalog_tree(self.game_list, active_game=resolved)
        else:
            self.load_game_from_state(resolved)

    def on_hardwired_tree_select(self, game):
        resolved = self._resolve_game_obj(game)
        self.load_game_from_state(resolved)

    def load_game_from_state(self, game_obj, category_source=None):
        resolved = self._resolve_game_obj(game_obj)
        if not resolved or not hasattr(resolved, "board"):
            return

        self.current_game = resolved
        self.board_node = resolved
        self.active_game = resolved
        self.root_game_node = resolved
        self.current_node = resolved

        if hasattr(self, "board_widget") and self.board_widget:
            try:
                fen_str = resolved.board().fen()
                self.board_widget.set_position_fen(fen_str)
            except Exception:
                pass

        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
                pgn_text_export = resolved.accept(exporter)

                self.pgn_data_text.configure(state="normal", fg_color=THEME["bg_surface"])
                self.pgn_data_text.delete("1.0", "end")
                self.pgn_data_text.insert("end", pgn_text_export)
                self.pgn_data_text.configure(state="disabled")
            except Exception:
                pass

        if hasattr(self, "moves_textbox") and self.moves_textbox:
            try:
                self.moves_textbox.configure(state="normal", fg_color=THEME["bg_surface"])
                bg_active = THEME.get("active_tracker_bg", "#660000")
                fg_active = THEME.get("active_tracker_fg", "#ffffff")
                self.moves_textbox.tag_config("active_move", background=bg_active, foreground=fg_active)
                self.moves_textbox.tag_config("default", foreground=THEME["text_primary"])
                self.moves_textbox.delete("1.0", "end")

                temp_node = resolved
                move_num = 1
                while temp_node.variations:
                    next_node = temp_node.variation(0)
                    san_move = temp_node.board().san(next_node.move)

                    if temp_node.board().turn == chess.WHITE:
                        move_str = f"{move_num}. {san_move} "
                    else:
                        move_str = f"{san_move} "
                        move_num += 1

                    tag_name = str(id(next_node))
                    self.moves_textbox.insert("end", move_str, ("default", tag_name))
                    self.moves_textbox.tag_bind(tag_name, "<Button-1>", lambda e, n=next_node: self.jump_to_node(n))

                    temp_node = next_node

                self.moves_textbox.configure(state="disabled")
                self.update_active_move_highlight()
            except Exception as e:
                print(f"[MOVES POPULATION ERROR] {e}")

        if hasattr(self, "_load_plain_game_moves"):
            try:
                self._load_plain_game_moves(resolved)
            except Exception:
                pass

    def jump_to_node(self, target_node):
        self.board_node = target_node
        if hasattr(self, "board_widget") and self.board_widget:
            try:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            except Exception:
                pass
        self.update_active_move_highlight()

    def update_active_move_highlight(self):
        if not hasattr(self, "moves_textbox") or not self.moves_textbox:
            return

        try:
            self.moves_textbox.configure(state="normal", fg_color=THEME["bg_surface"])
            bg_active = THEME.get("active_tracker_bg", "#660000")
            fg_active = THEME.get("active_tracker_fg", "#ffffff")
            self.moves_textbox.tag_config("active_move", background=bg_active, foreground=fg_active)
            self.moves_textbox.tag_remove("active_move", "1.0", "end")

            if self.board_node and self.board_node != self.current_game:
                current_tag = str(id(self.board_node))
                ranges = self.moves_textbox.tag_ranges(current_tag)
                if ranges:
                    self.moves_textbox.tag_add("active_move", ranges[0], ranges[1])
                    self.moves_textbox.see(ranges[0])

            self.moves_textbox.configure(state="disabled")
        except Exception:
            pass

    def on_prev_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.parent:
            self.board_node = self.board_node.parent
            if hasattr(self, "board_widget") and self.board_widget:
                try:
                    self.board_widget.set_position_fen(self.board_node.board().fen())
                except Exception:
                    pass
            self.update_active_move_highlight()
        return "break"

    def on_next_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.variations:
            self.board_node = self.board_node.variation(0)
            if hasattr(self, "board_widget") and self.board_widget:
                try:
                    self.board_widget.set_position_fen(self.board_node.board().fen())
                except Exception:
                    pass
            self.update_active_move_highlight()
        return "break"

    def on_first_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            self.board_node = self.current_game
            if hasattr(self, "board_widget") and self.board_widget:
                try:
                    self.board_widget.set_position_fen(self.current_game.board().fen())
                except Exception:
                    pass
            self.update_active_move_highlight()
        return "break"

    def on_last_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game
            while node.variations:
                node = node.variation(0)
            self.board_node = node
            if hasattr(self, "board_widget") and self.board_widget:
                try:
                    self.board_widget.set_position_fen(node.board().fen())
                except Exception:
                    pass
            self.update_active_move_highlight()
        return "break"

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self.board_widget, "flip_board"):
                self.board_widget.flip_board()
            elif hasattr(self.board_widget, "toggle_flip"):
                self.board_widget.toggle_flip()
        return "break"