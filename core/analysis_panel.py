import chess
import chess.pgn
from core.constants import THEME


class AnalysisPanelMixin:
    """
    Shared mixin for unified game loading, move parsing, comment/variation rendering,
    node-span move tracking, and analysis panel synchronization.
    """

    def _ensure_node_registry(self):
        if not hasattr(self, "_node_ranges") or self._node_ranges is None:
            self._node_ranges = {}
        if not hasattr(self, "_node_tag_names") or self._node_tag_names is None:
            self._node_tag_names = {}
        if not hasattr(self, "_last_tracked_node"):
            self._last_tracked_node = None

    def _get_inner_analysis_box(self):
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return None
        box = self.analysis_textbox
        return getattr(box, "_textbox", getattr(box, "textbox", box))

    def load_game(self, game_node, category_source=None):
        """Unified game loader that preserves comments/variations, updates the board, and syncs the panel."""
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

        if hasattr(self, "_reset_candidates_panel_on_game_change") and callable(self._reset_candidates_panel_on_game_change):
            try:
                self._reset_candidates_panel_on_game_change()
            except Exception as e:
                print(f"[CANDIDATE RESET ERROR] {e}")

        self.current_game = game_node
        self.active_game = game_node
        self.root_game_node = game_node
        self.current_node = game_node
        self.board_node = game_node
        self._last_tracked_node = None

        self.analysis_rows = {}

        if game_node:
            try:
                curr = game_node
                while curr.variations:
                    next_node = curr.variation(0)
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

        # Update Game Details panel (preserving comments and variations)
        if game_node and hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
                pgn_text_export = game_node.accept(exporter)

                self.pgn_data_text.configure(fg_color=THEME["bg_surface"])
                inner_pgn = getattr(
                    self.pgn_data_text,
                    "_textbox",
                    getattr(self.pgn_data_text, "textbox", self.pgn_data_text),
                )
                inner_pgn.configure(state="normal")
                inner_pgn.delete("1.0", "end")
                inner_pgn.insert("end", pgn_text_export)
                inner_pgn.configure(state="disabled")
            except Exception as e:
                print(f"[PGN EXPORT ERROR] {e}")

        self._sync_analysis_selection()

        if getattr(self, "active_engine_mode", None) == "review" and hasattr(self, "start_game_review"):
            try:
                self.start_game_review(game_node)
            except Exception as e:
                print(f"[REVIEW START ERROR] {e}")

    def jump_to_node(self, node):
        """Safely navigates to a specific move or variation node and updates the active tracker."""
        if not node:
            return

        self.board_node = node
        self.current_node = node

        if hasattr(self, "board_widget") and self.board_widget:
            try:
                self.board_widget.set_position(node.board())
            except Exception as e:
                print(f"[JUMP BOARD ERROR] {e}")

        if hasattr(self, "_active_chunk_end") and hasattr(self, "active_game") and self.active_game:
            ply = 0
            curr = node
            while curr.parent:
                ply += 1
                curr = curr.parent
            move_num = (ply + 1) // 2
            current_max_chunk = getattr(self, "_active_chunk_end", 15)
            if move_num > current_max_chunk and hasattr(self, "start_candidates_analysis"):
                next_start = current_max_chunk + 1
                self._active_chunk_end = next_start + 9
                self.start_candidates_analysis(self.active_game, start_move=next_start, max_chunk=10)

        self._apply_active_tracker()

    def _configure_tags(self, inner_box):
        primary = THEME.get("text_primary", "#ffffff")
        secondary = THEME.get("text_secondary", "#94a3b8")
        accent = THEME.get("btn_hover", primary)

        inner_box.tag_config(
            "active_tracker",
            background=THEME.get("active_tracker_bg", accent),
            foreground=THEME.get("active_tracker_fg", "#ffffff"),
        )
        inner_box.tag_config("default", foreground=primary)
        inner_box.tag_config("comment_tag", foreground=secondary)
        inner_box.tag_config("variation_tag", foreground=secondary)
        eval_font = ("Arial", 11, "bold")
        inner_box.tag_config("green", foreground=THEME.get("eval_green", "#1fa73b"))
        inner_box.tag_config("orange", foreground=THEME.get("eval_orange", "#FFA500"))
        inner_box.tag_config("red", foreground=THEME.get("eval_red", "#de3d35"))
        inner_box.tag_config("light_blue", foreground=THEME.get("eval_default", secondary))

    def _insert_move_node(self, inner_box, parent_board, node, style_tag="default", prefix="", include_comment=True):
        """Inserts a single move token, binds click-to-jump to its exact GameNode, and records its span."""
        self._ensure_node_registry()
        move = node.move
        san = parent_board.san(move)
        label = f"{prefix}{san}"

        start_idx = inner_box.index("end-1c")
        unique_tag = f"node_{id(node)}_{len(self._node_ranges)}"
        inner_box.insert("end", label, (style_tag, unique_tag))
        end_idx = inner_box.index("end-1c")

        self._node_ranges[node] = (start_idx, end_idx)
        self._node_tag_names[node] = unique_tag
        inner_box.tag_bind(unique_tag, "<Button-1>", lambda e, n=node: self.jump_to_node(n))
        inner_box.insert("end", " ", "default")

        if include_comment:
            comment = (node.comment or "").strip()
            if comment:
                inner_box.insert("end", f"{{{comment}}} ", "comment_tag")

    def _render_variation_line(self, inner_box, start_parent_board, start_node):
        """Recursively renders a side variation branch in parentheses with clickable nodes."""
        inner_box.insert("end", "(", "variation_tag")
        curr_board = start_parent_board.copy()
        curr_node = start_node

        first_move = True
        while curr_node is not None and curr_node.move is not None:
            move_num = curr_board.fullmove_number
            is_white = (curr_board.turn == chess.WHITE)

            if is_white:
                prefix = f"{move_num}. "
            elif first_move:
                prefix = f"{move_num}... "
            else:
                prefix = ""

            self._insert_move_node(
                inner_box,
                curr_board,
                curr_node,
                style_tag="variation_tag",
                prefix=prefix,
                include_comment=True,
            )

            # Nested sidesteps branching off this variation node
            if len(curr_node.variations) > 1:
                for alt_node in curr_node.variations[1:]:
                    self._render_variation_line(inner_box, curr_board, alt_node)

            curr_board.push(curr_node.move)
            curr_node = curr_node.variations[0] if curr_node.variations else None
            first_move = False

        inner_box.insert("end", ") ", "variation_tag")

    def _render_game_tree(self, inner_box, root_game):
        """Walks the mainline and all side variations from root_game."""
        curr = root_game
        while curr and curr.variations:
            main_next = curr.variation(0)
            board_before = curr.board()
            move_num = board_before.fullmove_number
            is_white = (board_before.turn == chess.WHITE)

            row_extra = self.analysis_rows.get(move_num, {}) if hasattr(self, "analysis_rows") else {}
            if is_white:
                prefix = f"{move_num}. "
                custom_tag = row_extra.get("white_tag", "default")
                extra_note = row_extra.get("white_alts", "")
            else:
                prefix = ""
                custom_tag = row_extra.get("black_tag", "default")
                extra_note = row_extra.get("black_alts", "")

            self._insert_move_node(
                inner_box,
                board_before,
                main_next,
                style_tag=custom_tag,
                prefix=prefix,
                include_comment=True,
            )

            if extra_note:
                inner_box.insert("end", f"{extra_note} ", "comment_tag")

            if len(curr.variations) > 1:
                for alt_node in curr.variations[1:]:
                    self._render_variation_line(inner_box, board_before, alt_node)

            curr = main_next

    def _sync_analysis_selection(self):
        """Renders moves, comments, and variations into analysis_textbox and updates the active tracker."""
        inner_box = self._get_inner_analysis_box()
        if not inner_box:
            return

        self._ensure_node_registry()
        self._node_ranges.clear()
        self._node_tag_names.clear()

        try:
            inner_box.configure(state="normal")
            inner_box.delete("1.0", "end")
            self._configure_tags(inner_box)

            root_game = getattr(self, "root_game_node", None) or getattr(self, "current_game", None)
            if root_game and hasattr(root_game, "variations"):
                self._render_game_tree(inner_box, root_game)
            elif hasattr(self, "analysis_rows") and self.analysis_rows:
                for move_num in sorted(self.analysis_rows.keys()):
                    row = self.analysis_rows[move_num]
                    inner_box.insert("end", f"{move_num}. ", "default")
                    for side in ("white", "black"):
                        txt = row.get(side, "")
                        node = row.get(f"{side}_node")
                        tag = row.get(f"{side}_tag", "default")
                        if txt:
                            start_idx = inner_box.index("end-1c")
                            t_name = f"{side}_{move_num}_{id(node)}" if node else f"{side}_{move_num}"
                            inner_box.insert("end", f"{txt} ", (tag, t_name))
                            end_idx = inner_box.index("end-1c")
                            if node:
                                self._node_ranges[node] = (start_idx, end_idx)
                                self._node_tag_names[node] = t_name
                                inner_box.tag_bind(t_name, "<Button-1>", lambda e, n=node: self.jump_to_node(n))
            else:
                inner_box.insert("end", "[No moves available for this game...]", "default")

            inner_box.configure(state="disabled")
            self._apply_active_tracker()
        except Exception as e:
            print(f"[SYNC ANALYSIS ERROR] {e}")

    def _apply_active_tracker(self):
        """Highlights self.current_node's recorded span without wiping comments or variations."""
        inner_box = self._get_inner_analysis_box()
        if not inner_box:
            return

        self._ensure_node_registry()
        active = getattr(self, "current_node", None) or getattr(self, "board_node", None)

        try:
            inner_box.configure(state="normal")
            inner_box.tag_remove("active_tracker", "1.0", "end")

            if active and active in self._node_ranges:
                start_idx, end_idx = self._node_ranges[active]
                inner_box.tag_add("active_tracker", start_idx, end_idx)
                inner_box.see(start_idx)

            self._last_tracked_node = active
            inner_box.configure(state="disabled")
        except Exception as e:
            print(f"[ACTIVE TRACKER ERROR] {e}")

    def update_active_move_highlight(self):
        """Delegates position updates and ensures arrow/step navigation updates the UI highlight."""
        if hasattr(self, "board_node") and self.board_node and not getattr(self, "current_node", None):
            self.current_node = self.board_node
        self._apply_active_tracker()

    def load_game_from_state(self, game_obj, category_source=None):
        """Compatibility wrapper pointing to load_game."""
        self.load_game(game_obj, category_source=category_source)