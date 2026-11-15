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

        # --- BUILD ANALYSIS ROWS FOR THE NEW GAME ---
        self.analysis_rows = {}
        try:
            curr = resolved
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
            print(f"[ANALYSIS ROWS BUILD ERROR] {e}")

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

                surface_bg = THEME.get("bg_surface", THEME.get("bg_main", "#172134"))
                self.pgn_data_text.configure(state="normal", fg_color=surface_bg)
                self.pgn_data_text.delete("1.0", "end")
                self.pgn_data_text.insert("end", pgn_text_export)
                self.pgn_data_text.configure(state="disabled")
            except Exception:
                pass

        if hasattr(self, "moves_textbox") and self.moves_textbox:
            try:
                surface_bg = THEME.get("bg_surface", THEME.get("bg_main", "#172134"))
                text_primary = THEME.get("text_primary", "#ffffff")
                self.moves_textbox.configure(state="normal", fg_color=surface_bg)
                bg_active = THEME.get("active_tracker_bg", "#660000")
                fg_active = THEME.get("active_tracker_fg", "#ffffff")
                self.moves_textbox.tag_config("active_move", background=bg_active, foreground=fg_active)
                self.moves_textbox.tag_config("default", foreground=text_primary)
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
                    self.moves_textbox.tag_bind(tag_name, "<Button-1>", lambda *args, n=next_node: self.jump_to_node(n))

                    temp_node = next_node

                self.moves_textbox.configure(state="disabled")
                self.update_active_move_highlight()
            except Exception as e:
                print(f"[MOVES POPULATION ERROR] {e}")

        if hasattr(self, "_sync_analysis_selection"):
            try:
                self._sync_analysis_selection()
            except Exception:
                pass

        # --- AUTO-TRIGGER ANALYSIS ---
        if hasattr(self, "trigger_engine_mode"):
            try:
                target_mode = getattr(self, "active_engine_mode", None) or "piece_pattern_mode"
                self.trigger_engine_mode(target_mode)
            except Exception as e:
                print(f"[AUTO-ANALYZE ERROR] {e}")

        if hasattr(self, "_load_plain_game_moves"):
            try:
                self._load_plain_game_moves(resolved)
            except Exception:
                pass

        if hasattr(self, "openings_manager") and self.openings_manager:
            try:
                self.openings_manager.attach_to_workspace(self)
            except Exception as e:
                print(f"[OPENINGS RENDER ERROR] {e}")

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
            surface_bg = THEME.get("bg_surface", THEME.get("bg_main", "#172134"))
            self.moves_textbox.configure(state="normal", fg_color=surface_bg)
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

    def _on_tree_selection_event(self, event):
        if not hasattr(self, "pgn_tree"):
            return
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
        if hasattr(self, "btn_pv") and self.btn_pv:
            self.btn_pv.configure(
                text="Engine",
                command=self.toggle_engine_action,
                hover_color=THEME.get("btn_hover", "#3b82f6")
            )

        for btn_name in ("btn_white", "btn_white_patterns"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(
                    text="White Patterns",
                    command=lambda: (print("[DEBUG CLICK] White Patterns clicked!"),
                                     self.trigger_engine_mode("white_patterns_mode")),
                    hover_color=THEME.get("btn_hover", "#3b82f6")
                )
                break

        for btn_name in ("btn_black", "btn_black_patterns"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(
                    text="Black Patterns",
                    command=lambda: (print("[DEBUG CLICK] Black Patterns clicked!"),
                                     self.trigger_engine_mode("black_patterns_mode")),
                    hover_color=THEME.get("btn_hover", "#3b82f6")
                )
                break

        if hasattr(self, "btn_opening") and self.btn_opening:
            self.btn_opening.configure(
                text="Opening",
                command=lambda: (print("[DEBUG CLICK] Opening clicked!"),
                                 self.trigger_engine_mode("opening_pattern_mode")),
                hover_color=THEME.get("btn_hover", "#3b82f6")
            )

        if hasattr(self, "btn_calculation") and self.btn_calculation:
            self.btn_calculation.configure(
                text="Calculation",
                command=lambda: (print("[DEBUG CLICK] Calculation clicked!"),
                                 self.trigger_engine_mode("calculation_pattern_mode")),
                hover_color=THEME.get("btn_hover", "#3b82f6")
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