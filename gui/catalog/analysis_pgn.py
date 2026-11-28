import chess


class AnalysisPgnMixin:
    """Mixin class for rendering PGN moves/variations and tracking the active move node."""

    def _get_analysis_text_widget(self):
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return None
        box = self.analysis_textbox
        return getattr(box, "_textbox", getattr(box, "textbox", box))

    def _render_game_pgn_tree(self, game_obj):
        """Renders mainline moves, comments, and variations into analysis_textbox with click-to-jump tags."""
        target_box = self._get_analysis_text_widget()
        if not target_box:
            return

        if not hasattr(self, "_node_text_ranges"):
            self._node_text_ranges = {}
        self._node_text_ranges.clear()

        if hasattr(game_obj, "root") and callable(game_obj.root):
            root = game_obj.root()
        else:
            root = game_obj

        try:
            target_box.configure(state="normal")
        except Exception:
            pass

        target_box.delete("1.0", "end")

        if not root:
            try:
                target_box.configure(state="disabled")
            except Exception:
                pass
            return

        if getattr(root, "comment", ""):
            comment_str = root.comment.strip()
            if comment_str:
                target_box.insert("end", f"{{{comment_str}}} ", ("comment_tag",))

        def walk_node(node, is_variation=False):
            if not node.variations:
                return

            main_child = node.variation(0)
            self._insert_move_node(node, main_child, is_variation=is_variation)

            for alt_child in node.variations[1:]:
                target_box.insert("end", " (", ("variation_tag",))
                self._insert_alt_line(node, alt_child)
                target_box.insert("end", ") ", ("variation_tag",))

            walk_node(main_child, is_variation=is_variation)

        def _insert_alt_line(parent_node, alt_node):
            self._insert_move_node(parent_node, alt_node, is_variation=True)
            curr = alt_node
            while curr.variations:
                nxt = curr.variation(0)
                self._insert_move_node(curr, nxt, is_variation=True)
                for sub_alt in curr.variations[1:]:
                    target_box.insert("end", " (", ("variation_tag",))
                    _insert_alt_line(curr, sub_alt)
                    target_box.insert("end", ") ", ("variation_tag",))
                curr = nxt

        walk_node(root, is_variation=False)

        try:
            target_box.configure(state="disabled")
        except Exception:
            pass

        self.update_active_move_highlight()

    def _insert_move_node(self, parent_node, child_node, is_variation=False):
        target_box = self._get_analysis_text_widget()
        if not target_box or not child_node or not getattr(child_node, "move", None):
            return

        board_before = parent_node.board()
        move_num = board_before.fullmove_number
        is_white = (board_before.turn == chess.WHITE)
        san = board_before.san(child_node.move)

        if is_white:
            prefix = f"{move_num}. {san}"
        elif is_variation:
            prefix = f"{move_num}... {san}"
        else:
            prefix = f"{san}"

        node_tag = f"node_{id(child_node)}"
        style_tag = "variation_tag" if is_variation else "move_tag"

        start_idx = target_box.index("end-1c")
        target_box.insert("end", f"{prefix} ", (style_tag, node_tag))
        end_idx = target_box.index("end-1c")

        if not hasattr(self, "_node_text_ranges"):
            self._node_text_ranges = {}
        self._node_text_ranges[id(child_node)] = (start_idx, end_idx)

        target_box.tag_bind(
            node_tag,
            "<Button-1>",
            lambda event, n=child_node: self._on_analysis_move_click(n)
        )

        comment_str = (getattr(child_node, "comment", "") or "").strip()
        if comment_str:
            target_box.insert("end", f"{{{comment_str}}} ", ("comment_tag",))

    def _on_analysis_move_click(self, node):
        if not node:
            return
        self.board_node = node
        self.current_node = node
        if hasattr(self, "board_widget") and self.board_widget:
            try:
                self.board_widget.set_position_fen(node.board().fen())
            except Exception:
                pass
        self.update_active_move_highlight()
        if hasattr(self, "notify_live_engine_position_changed"):
            self.notify_live_engine_position_changed()

    def update_active_move_highlight(self, event=None):
        """Highlights the active move node in analysis_textbox and syncs Move 1."""
        if hasattr(self, "sync_move1_from_tracker"):
            self.sync_move1_from_tracker()

        target_box = self._get_analysis_text_widget()
        if not target_box:
            return

        active_node = (
            getattr(self, "board_node", None)
            or getattr(self, "current_node", None)
        )

        try:
            target_box.configure(state="normal")
            target_box.tag_remove("active_tracker", "1.0", "end")

            if active_node is not None:
                node_suffix = f"_{id(active_node)}"
                exact_node_tag = f"node_{id(active_node)}"
                for tag in target_box.tag_names():
                    if tag == exact_node_tag or tag.endswith(node_suffix):
                        ranges = target_box.tag_ranges(tag)
                        if ranges:
                            target_box.tag_add("active_tracker", ranges[0], ranges[1])
                            target_box.see(ranges[0])
                        break
        finally:
            try:
                target_box.configure(state="disabled")
            except Exception:
                pass