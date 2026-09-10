import json
from pathlib import Path
import customtkinter as ctk
import chess
import chess.pgn
import gui.app_state as state

from core.constants import CONFIG_FILE, THEME
from gui.catalog_init_mixin import CatalogInitMixin
from gui.engine_mixins.engine_review_mixin import EngineReviewMixin
from gui.engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from gui.engine_mixins.engine_standard_mixin import EngineStandardMixin


class PatternsAnalysis(ctk.CTkFrame, CatalogInitMixin, EngineReviewMixin, EngineCandidateMixin, EngineStandardMixin):
    """
    Dedicated self-contained workspace controller for Patterns Analysis.
    Absorbs the complete layout grid, tree view navigation, board management, PGN state handling, and engine analysis modes.
    """

    def __init__(self, parent, filename=None, initial_games=None, target_game=None, active_index=None, *args, **kwargs):
        kwargs.pop('target_game', None)
        kwargs.pop('active_index', None)

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
        self.active_engine_mode = "standard"
        self.analysis_rows = {}
        self._cached_analysis_box = None

        self.init_layout()
        self._find_and_cache_analysis_box()
        self.load_catalog_data()
        self._bind_engine_buttons()
        self._bind_global_shortcuts()

        if active_index is not None and 0 <= active_index < len(self.game_list):
            target_game = self.game_list[active_index]

        if target_game and hasattr(self, "load_game"):
            self.load_game(target_game)

        if hasattr(self, "board_widget") and self.board_widget:
            self.board_widget.on_step_back = self.on_prev_move
            self.board_widget.on_step_forward = self.on_next_move
            self.board_widget.on_jump_start = self.on_first_move
            self.board_widget.on_jump_end = self.on_last_move

        self.after(50, self.focus_force)

    def _resolve_game_obj(self, item):
        if item is None:
            return None
        if hasattr(item, "board") and hasattr(item, "headers"):
            return item
        if isinstance(item, dict):
            for k in ("game_object", "game", "game_obj", "node", "pgn", "item", "target_game"):
                if k in item and item[k] is not None:
                    res = self._resolve_game_obj(item[k])
                    if res is not None:
                        return res
        return item

    def _find_and_cache_analysis_box(self):
        found_boxes = {}
        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                val = getattr(self, attr_name, None)
                if val is not None and hasattr(val, "insert") and hasattr(val, "delete"):
                    found_boxes[attr_name] = val

        if "analysis_textbox" in found_boxes:
            self._cached_analysis_box = found_boxes["analysis_textbox"]
            return

        for attr_name in dir(self):
            if not attr_name.startswith("_"):
                val = getattr(self, attr_name, None)
                if val is not None and hasattr(val, "insert") and hasattr(val, "delete"):
                    self._cached_analysis_box = val
                    return

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

            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.bind("<Left>", lambda e: self._safe_handle_shortcut(self.on_prev_move, e))
                self.board_widget.bind("<Right>", lambda e: self._safe_handle_shortcut(self.on_next_move, e))
        except Exception as e:
            print(f"[SHORTCUT BIND ERROR] {e}")

    def _safe_handle_shortcut(self, callback, event):
        try:
            focused = self.winfo_toplevel().focus_get()
            if focused and type(focused).__name__ in ("CTkTextbox", "CTkEntry", "Text", "Entry"):
                return

            if callable(callback):
                callback(event)
                return "break"
        except Exception as e:
            print(f"[SHORTCUT EXECUTION ERROR] {e}")

    def _bind_engine_buttons(self):
        for btn_name in ("btn_review", "btn_review_mode"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    command=lambda: self.trigger_engine_mode("review"),
                    hover_color=THEME["btn_hover"]
                )

        for btn_name in ("btn_candidates", "btn_candidate_moves"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    command=lambda: self.trigger_engine_mode("candidates"),
                    hover_color=THEME["btn_hover"]
                )

        for btn_name in ("btn_standard", "btn_standard_mode"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(
                    command=lambda: self.trigger_engine_mode("standard"),
                    hover_color=THEME["btn_hover"]
                )

        for btn_name in ("btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                btn.configure(hover_color=THEME["btn_hover"])

        self.trigger_engine_mode(self.active_engine_mode)

    def update_engine_display(self, text):
        target_box = getattr(self, "analysis_textbox", None)
        if not target_box and hasattr(self, "_cached_analysis_box"):
            target_box = self._cached_analysis_box

        if target_box:
            try:
                target_box.configure(state="normal", fg_color=THEME["bg_surface"])
                target_box.delete("1.0", "end")
                target_box.insert("end", text)
                target_box.configure(state="disabled")
            except Exception as e:
                print(f"[ENGINE DISPLAY ERROR] {e}")

    def write_analysis(self, text):
        self.update_engine_display(text)

    def write(self, text):
        self.update_engine_display(text)

    def append(self, text):
        self.update_engine_display(text)

    def load_games_list(self, games_list, focused_game=None):
        if not games_list:
            return

        self.game_list = games_list
        if hasattr(self, "populate_catalog_tree"):
            self.populate_catalog_tree(self.game_list)

        target_game = focused_game if focused_game else games_list[0]
        if hasattr(self, "load_game"):
            self.load_game(target_game)

    def pop_out_board(self, *args, **kwargs):
        if hasattr(self, "board_widget") and self.board_widget and hasattr(self.board_widget, "toggle_popout"):
            self.board_widget.toggle_popout()

    def load_game(self, game_node, category_source=None):
        resolved = self._resolve_game_obj(game_node)
        if hasattr(self, "load_game_hardwired"):
            return self.load_game_hardwired(resolved, category_source=category_source)
        return self.load_game_from_state(resolved, category_source=category_source)

    def load_catalog_data(self):
        if self.game_list:
            if hasattr(self, "pgn_tree"):
                active_game = None
                if hasattr(state, "catalog_state") and "active_index" in state.catalog_state:
                    idx = state.catalog_state.get("active_index", 0)
                    if 0 <= idx < len(self.game_list):
                        active_game = self.game_list[idx]

                self.populate_catalog_tree(self.game_list, active_game=active_game)
            return

        source_games = []
        catalog_path = self.filename

        if Path(catalog_path).exists():
            try:
                with open(catalog_path, "r", encoding="utf-8", errors="replace") as f:
                    while True:
                        g = chess.pgn.read_game(f)
                        if g is None:
                            break
                        source_games.append(g)
                self.game_list = source_games
                if hasattr(state, "all_games"):
                    state.all_games = source_games
            except Exception as e:
                print(f"[CATALOG ANALYSIS DEBUG] Error reading catalog file: {e}")

        if self.game_list and hasattr(self, "pgn_tree"):
            self.populate_catalog_tree(self.game_list)
            self.load_game(self.game_list[0])

    def populate_catalog_tree(self, games_to_display, active_game=None):
        if not hasattr(self, "pgn_tree") or not hasattr(self, "preview_lookup"):
            return

        self.pgn_tree.delete(*self.pgn_tree.get_children())
        self.preview_lookup.clear()

        if hasattr(self, "lbl_empty_state") and self.lbl_empty_state and games_to_display:
            try:
                self.lbl_empty_state.pack_forget()
            except Exception:
                pass

        resolved_active = self._resolve_game_obj(active_game)
        target = resolved_active or (self._resolve_game_obj(games_to_display[0]) if games_to_display else None)

        for idx, g_raw in enumerate(games_to_display, start=1):
            g_obj = self._resolve_game_obj(g_raw)
            headers = getattr(g_obj, "headers", {})
            white = headers.get("White", "Unknown") if hasattr(headers, "get") else "Unknown"
            black = headers.get("Black", "Unknown") if hasattr(headers, "get") else "Unknown"
            result = headers.get("Result", "*") if hasattr(headers, "get") else "*"

            item_id = self.pgn_tree.insert("", "end", values=(idx, white, black, result))
            self.preview_lookup[item_id] = g_raw

            if target and (g_obj == target or g_raw == active_game):
                self.pgn_tree.selection_set(item_id)
                self.pgn_tree.see(item_id)

        if target:
            self.load_game_from_state(target)
        self.after(50, self.focus_set)

    def load_games_by_eco(self, eco_code, active_game=None):
        if not eco_code:
            return

        eco_clean = str(eco_code).strip().upper()

        if not self.game_list and hasattr(state, "all_games") and state.all_games:
            self.game_list = state.all_games
        elif not self.game_list:
            self.load_catalog_data()

        eco_games = []
        for g in self.game_list:
            g_obj = self._resolve_game_obj(g)
            headers = getattr(g_obj, "headers", {})
            eco_val = headers.get("ECO", "") if hasattr(headers, "get") else ""
            if eco_val.strip().upper() == eco_clean:
                eco_games.append(g)

        target_game = active_game or (eco_games[0] if eco_games else None)

        if eco_games:
            if hasattr(state, "active_category_source"):
                state.active_category_source = eco_games

        self.populate_catalog_tree(eco_games, active_game=target_game)

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

    def trigger_engine_mode(self, mode):
        """Routes engine mode changes and correctly highlights only the active mode's buttons and frames."""
        self.active_engine_mode = mode

        mode_buttons = {
            "review": ("btn_review", "btn_review_mode"),
            "candidates": ("btn_candidates", "btn_candidate_moves"),
            "standard": ("btn_standard", "btn_standard_mode")
        }

        for m, btn_names in mode_buttons.items():
            is_active = (mode == m)
            for name in btn_names:
                btn = getattr(self, name, None)
                if btn is not None:
                    btn.configure(
                        fg_color=THEME["btn_hover"] if is_active else THEME["btn_initial"],
                        hover_color=THEME["btn_hover"],
                        text_color=THEME["text_primary"],
                    )

        if hasattr(self, "frame_review") and self.frame_review:
            self.frame_review.configure(border_width=0 if mode == "review" else 1)
        if hasattr(self, "frame_candidates") and self.frame_candidates:
            self.frame_candidates.configure(border_width=0 if mode == "candidates" else 1)
        if hasattr(self, "frame_standard") and self.frame_standard:
            self.frame_standard.configure(border_width=0 if mode == "standard" else 1)

        if mode == "review":
            EngineReviewMixin.trigger_engine_mode(self, "review")
        elif mode == "candidates":
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")


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

    if initial_games and 0 <= active_index < len(initial_games) and not defocus:
        defocus = initial_games[active_index]

    instance = PatternsAnalysis(master, filename="personal_catalog.pgn", initial_games=initial_games, target_game=defocus,
                                active_index=active_index)
    state_mod.workspace = instance
    return instance


def create_patterns_analysis_workspace(master, initial_games=None, **kwargs):
    return create_workspace(master, initial_games=initial_games, **kwargs)