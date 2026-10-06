import chess
import chess.pgn
from core.constants import THEME


class AnalysisPanelMixin:
    """
    Shared mixin for unified game loading, move parsing, and analysis panel synchronization
    across Catalog and Mixed Collections workspaces.
    """

    def load_game(self, game_node, category_source=None):
        """Unified game loader that parses moves, updates the board, game details, and syncs the analysis panel."""
        if isinstance(category_source, list):
            self.game_list = category_source
            if hasattr(self, "populate_catalog_tree"):
                self.populate_catalog_tree(self.game_list, active_game=game_node)
            return

        if isinstance(game_node, int):
            if hasattr(self, "game_list") and self.game_list and 0 <= game_node < len(self.game_list):
                game_node = self.game_list[game_node]

        if hasattr(game_node, "root") and callable(game_node.root):
            game_node = game_node.root()

        self.current_game = game_node
        self.active_game = game_node
        self.root_game_node = game_node
        self.current_node = game_node
        self.board_node = game_node

        self.analysis_rows = {}

        if game_node:
            try:
                curr = game_node
                while curr.variations:
                    next_node = curr.variation(0)
                    next_node.comment = ""
                    if hasattr(next_node, "nags"):
                        next_node.nags.clear()

                    board_at_curr = curr.board()
                    move = next_node.move
                    san = board_at_curr.san(move)
                    move_num = board_at_curr.fullmove_number
                    is_white = (board_at_curr.turn == chess.WHITE)

                    if move_num not in self.analysis_rows:
                        self.analysis_rows[move_num] = {}

                    if is_white:
                        self.analysis_rows[move_num]["white"] = san
                        self.analysis_rows[move_num]["white_node"] = next_node
                    else:
                        self.analysis_rows[move_num]["black"] = san
                        self.analysis_rows[move_num]["black_node"] = next_node

                    curr = next_node
            except Exception as e:
                print(f"[PARSE ERROR] {e}")

        # Update board view
        if hasattr(self, "board_widget") and self.board_widget and game_node:
            try:
                self.board_widget.set_position(game_node.board())
            except Exception as e:
                print(f"[BOARD POSITION ERROR] {e}")

        # Update Game Details panel
        if game_node and hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=False, columns=None)
                pgn_text_export = game_node.accept(exporter)

                self.pgn_data_text.configure(fg_color=THEME["bg_surface"])
                inner_pgn = getattr(self.pgn_data_text, "_textbox",
                                    getattr(self.pgn_data_text, "textbox", self.pgn_data_text))
                inner_pgn.configure(state="normal")
                inner_pgn.delete("1.0", "end")
                inner_pgn.insert("end", pgn_text_export)
                inner_pgn.configure(state="disabled")
            except Exception as e:
                print(f"[PGN EXPORT ERROR] {e}")

        # Sync the analysis box
        self._sync_analysis_selection()

        if getattr(self, "active_engine_mode", None) == "review" and hasattr(self, "start_game_review"):
            try:
                self.start_game_review(game_node)
            except Exception as e:
                print(f"[REVIEW START ERROR] {e}")

    def jump_to_node(self, node):
        """Safely navigates to a specific move node when clicked and updates the active tracker."""
        if not node:
            return

        self.board_node = node
        self.current_node = node

        if hasattr(self, "board_widget") and self.board_widget:
            try:
                self.board_widget.set_position(node.board())
            except Exception as e:
                print(f"[JUMP BOARD ERROR] {e}")

        self._sync_analysis_selection()

    def _sync_analysis_selection(self):
        """Renders the analysis panel move list into analysis_textbox and highlights the active move tracker."""
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return

        try:
            target_box = self.analysis_textbox
            inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
            inner_box.configure(state="normal")
            inner_box.delete("1.0", "end")

            # Configure tags
            inner_box.tag_config("active_tracker", background=THEME["active_tracker_bg"],
                                 foreground=THEME["active_tracker_fg"])
            inner_box.tag_config("default", foreground=THEME["text_primary"])

            sorted_moves = sorted(self.analysis_rows.keys()) if hasattr(self,
                                                                        "analysis_rows") and self.analysis_rows else []

            if not sorted_moves:
                inner_box.insert("end", "[No moves available for this game...]", "default")
                inner_box.configure(state="disabled")
                return

            for move_num in sorted_moves:
                row = self.analysis_rows[move_num]
                inner_box.insert("end", f"{move_num}. ", "default")

                # White Move
                w_text = row.get("white", "")
                w_node = row.get("white_node")
                if w_text:
                    w_tag_name = f"w_{move_num}_{id(w_node)}" if w_node else f"w_{move_num}"
                    is_active_white = (
                            (hasattr(self, "current_node") and self.current_node == w_node) or
                            (hasattr(self, "board_node") and self.board_node == w_node)
                    )
                    applied_tag = "active_tracker" if is_active_white else "default"

                    inner_box.insert("end", f"{w_text} ", (applied_tag, w_tag_name))
                    if w_node:
                        inner_box.tag_bind(w_tag_name, "<Button-1>", lambda e, n=w_node: self.jump_to_node(n))
                else:
                    inner_box.insert("end", "... ", "default")

                # Black Move
                b_text = row.get("black", "")
                b_node = row.get("black_node")
                if b_text:
                    b_tag_name = f"b_{move_num}_{id(b_node)}" if b_node else f"b_{move_num}"
                    is_active_black = (
                            (hasattr(self, "current_node") and self.current_node == b_node) or
                            (hasattr(self, "board_node") and self.board_node == b_node)
                    )
                    applied_tag = "active_tracker" if is_active_black else "default"

                    inner_box.insert("end", f"{b_text} ", (applied_tag, b_tag_name))
                    if b_node:
                        inner_box.tag_bind(b_tag_name, "<Button-1>", lambda e, n=b_node: self.jump_to_node(n))

                inner_box.insert("end", "    ", "default")

            inner_box.configure(state="disabled")
        except Exception as e:
            print(f"[SYNC ANALYSIS ERROR] {e}")

    def update_active_move_highlight(self):
        """Delegates position updates and ensures arrow/step navigation updates the UI highlight."""
        if hasattr(self, "board_node") and self.board_node and not getattr(self, "current_node", None):
            self.current_node = self.board_node
        self._sync_analysis_selection()

    def load_game_from_state(self, game_obj, category_source=None):
        """Compatibility wrapper pointing to load_game."""
        self.load_game(game_obj, category_source=category_source)