import customtkinter as ctk
import chess
import chess.pgn
from core.constants import THEME
from gui.patterns.patterns_init_mixin import PatternsInitMixin
from gui.engine_mixins.engine_piece_mixin import EnginePieceMixin
from gui.patterns.patterns_analysis_navigation import PatternsAnalysisNavigationMixin
from gui.patterns.patterns_evaluation import PatternsEvaluation


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

        # Ensure the analysis panel syncs its view with the newly loaded game data
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

        # --- RENDER OPENING EXPLORER STREAM ---
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


class PatternsAnalysis(
    ctk.CTkFrame,
    PatternsInitMixin,
    PatternsAnalysisNavigationMixin,
    PatternsAnalysisBoardMixin,
    EnginePieceMixin,
    PatternsEvaluation,
):
    """Concrete workspace controller for Patterns Analysis UI layout, shortcuts, and bindings."""

    def __init__(self, parent, filename=None, initial_games=None, target_game=None, active_index=None,
                 target_piece=None, *args, **kwargs):
        kwargs.pop('target_game', None)
        kwargs.pop('active_index', None)
        kwargs.pop('target_piece', None)

        super().__init__(parent, fg_color=THEME.get("bg_panel", "#172134"), corner_radius=0, *args, **kwargs)

        import gui.app_state as state
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

        if hasattr(self, "init_layout"):
            self.init_layout()
        if hasattr(self, "_find_and_cache_analysis_box"):
            self._find_and_cache_analysis_box()
        if hasattr(self, "load_catalog_data"):
            self.load_catalog_data()
        if hasattr(self, "_bind_engine_buttons"):
            self._bind_engine_buttons()
        if hasattr(self, "_bind_global_shortcuts"):
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
        if hasattr(self, "pgn_data_panel") and self.pgn_data_panel.winfo_ismapped():
            self.pgn_data_panel.grid_remove()
            if hasattr(self, "right_analysis_panel"):
                self.right_analysis_panel.rowconfigure(2, weight=0, minsize=0)
                self.right_analysis_panel.rowconfigure(1, weight=4)
            if hasattr(self, "analysis_container_frame"):
                self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 0))
        else:
            if hasattr(self, "analysis_container_frame"):
                self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))
            if hasattr(self, "right_analysis_panel"):
                self.right_analysis_panel.rowconfigure(1, weight=3)
                self.right_analysis_panel.rowconfigure(2, weight=1, minsize=0)
            if hasattr(self, "pgn_data_panel"):
                self.pgn_data_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

    def on_flip_board(self, event=None):
        """Explicitly calls toggle_flip() on the board widget when 'f' or 'F' is pressed."""
        try:
            if hasattr(self, "board_widget") and self.board_widget:
                if hasattr(self.board_widget, "toggle_flip") and callable(self.board_widget.toggle_flip):
                    self.board_widget.toggle_flip()
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
        # --- Standalone Engine Comparison Button ---
        if hasattr(self, "btn_pv") and self.btn_pv:
            self.btn_pv.configure(
                text="Engine",
                command=self.toggle_engine_action,
                hover_color=THEME.get("btn_hover", "#3b82f6")
            )

        # --- White Patterns ---
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

        # --- Black Patterns ---
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

        # --- Opening ---
        if hasattr(self, "btn_opening") and self.btn_opening:
            self.btn_opening.configure(
                text="Opening",
                command=lambda: (print("[DEBUG CLICK] Opening clicked!"),
                                 self.trigger_engine_mode("opening_pattern_mode")),
                hover_color=THEME.get("btn_hover", "#3b82f6")
            )

        # --- Calculation ---
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