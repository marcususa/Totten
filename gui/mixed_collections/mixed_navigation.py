from core.constants import THEME
import customtkinter as ctk
from tkinter import ttk


class MixedAnalysisNavigation:
    """Manages node jumping, move tagging, board navigation steps, and flipping."""

    def init_layout(self):
        """Standard layout hook override to inject the treeview container and vertical scrollbar."""
        if hasattr(super(), "init_layout"):
            super().init_layout()

        if hasattr(self, "pgn_tree") and self.pgn_tree:
            try:
                # Find the current manager (pack or grid) of the pgn_tree
                info = self.pgn_tree.info()
                parent = self.pgn_tree.master

                # Create a visible container frame in the exact same spot/parent
                tree_container = ctk.CTkFrame(parent, fg_color="transparent")

                if info.get("in"):
                    # If packed, replicate pack options
                    self.pgn_tree.pack_forget()
                    tree_container.pack(
                        side=info.get("side", "top"),
                        fill=info.get("fill", "both"),
                        expand=info.get("expand", True),
                        padx=int(info.get("padx", 0)),
                        pady=int(info.get("pady", 0))
                    )
                else:
                    # Fallback to grid or general fill
                    self.pgn_tree.grid_forget()
                    tree_container.pack(fill="both", expand=True)

                # Reparent treeview into container
                self.pgn_tree.master = tree_container

                # Create CustomTkinter scrollbar explicitly packed on the right
                tree_scroll = ctk.CTkScrollbar(tree_container, orientation="vertical")
                tree_scroll.pack(side="right", fill="y", padx=(2, 0), pady=0)

                # Pack treeview on the left filling remaining space
                self.pgn_tree.pack(side="left", fill="both", expand=True)

                # Link scrolling commands
                self.pgn_tree.configure(yscrollcommand=tree_scroll.set)
                tree_scroll.configure(command=self.pgn_tree.yview)
            except Exception as e:
                print(f"[MIXED NAVIGATION SCROLLBAR ERROR] {e}")

    def jump_to_node(self, target_node):
        """Jumps directly to a specific game node when clicked in the move list."""
        if not target_node:
            return

        self.current_node = target_node
        self.board_node = target_node
        if hasattr(self, "board_widget") and self.board_widget:
            try:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            except Exception:
                pass
        self.update_active_move_highlight()

    def _highlight_current_move_tag(self, target_node):
        """Highlights the active node token in the moves text box with a red/accent color."""
        if not hasattr(self, "moves_textbox") or not self.moves_textbox:
            return

        try:
            box = self.moves_textbox
            moves_box = getattr(box, "_textbox", getattr(box, "textbox", box))

            moves_box.tag_remove("current_move", "1.0", "end")
            moves_box.tag_config("current_move", foreground=THEME.get("accent", "#eab308"), underline=True)

            target_tag = str(id(target_node))
            ranges = moves_box.tag_ranges(target_tag)
            if ranges:
                moves_box.tag_add("current_move", ranges[0], ranges[1])
                moves_box.see(ranges[0])
        except Exception as e:
            print(f"[HIGHLIGHT ERROR] {e}")

    def update_active_move_highlight(self):
        """Updates the active background highlight ('red tracker') in the moves textbox corresponding to self.board_node."""
        if not hasattr(self, "moves_textbox") or not self.moves_textbox:
            return

        try:
            box = self.moves_textbox
            box.configure(fg_color=THEME["bg_surface"])
            moves_box = getattr(box, "_textbox", getattr(box, "textbox", box))
            moves_box.configure(state="normal")
            moves_box.tag_remove("active_move", "1.0", "end")

            if self.board_node and self.board_node != self.current_game:
                current_tag = str(id(self.board_node))
                ranges = moves_box.tag_ranges(current_tag)
                if ranges:
                    moves_box.tag_add("active_move", ranges[0], ranges[1])
                    moves_box.see(ranges[0])

            moves_box.configure(state="disabled")
        except Exception:
            pass

        if hasattr(self, "_sync_analysis_selection"):
            try:
                self._sync_analysis_selection()
            except Exception:
                pass

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
        return "break"

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
        return "break"

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self.board_widget, "flip_board"):
                self.board_widget.flip_board()
            elif hasattr(self.board_widget, "toggle_flip"):
                self.board_widget.toggle_flip()
        return "break"