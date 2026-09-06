import json
from pathlib import Path
import customtkinter as ctk
from tkinter import ttk
import chess
import chess.pgn

import gui.app_state as state
from gui.statusbar import set_status_message
from gui.chess_board import ChessBoardWidget
from core.constants import CONFIG_FILE
from gui.engine_mixins.engine_review_mixin import EngineReviewMixin
from gui.engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from gui.engine_mixins.engine_standard_mixin import EngineStandardMixin

BASE_PGN_DIR = Path(__file__).resolve().parent.parent / "pgn"


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        try:
            tw.wm_attributes("-disabled", True)
        except Exception:
            pass
        label = ctk.CTkLabel(
            tw,
            text=self.text,
            fg_color="#1e293b",
            text_color="#f8fafc",
            corner_radius=4,
            font=("Arial", 11)
        )
        label.pack(padx=6, pady=4)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            try:
                self.tooltip_window.destroy()
            except Exception:
                pass
            self.tooltip_window = None


class PatternsAnalysis(ctk.CTkFrame, EngineReviewMixin, EngineCandidateMixin, EngineStandardMixin):
    def __init__(self, parent, filename=None, initial_games=None, target_game=None, active_index=None, *args, **kwargs):
        super().__init__(parent, fg_color="#172134", corner_radius=0, *args, **kwargs)
        self.filename = filename or (BASE_PGN_DIR / "patterns_analysis.pgn")
        self.game_list = []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}
        self.game_lookup = {}

        self.active_game = None
        self.root_game_node = None
        self.current_node = None
        self.active_engine_mode = "standard"

        self.popout_window = None
        self.popout_board = None
        self.popout_container = None
        self.is_board_popped_out = False

        self.col_tree = None
        self.pgn_tree = None

        # Inline layout initialization
        self.init_layout()
        self._apply_tree_styles()
        self._bind_analysis_events()
        self._bind_keyboard_events()

        if initial_games is not None:
            self.load_patterns_collection(initial_games, target_game=target_game, active_index=active_index)
        elif hasattr(state, "active_category_source") and state.active_category_source:
            if isinstance(state.active_category_source, list):
                self.load_patterns_collection(state.active_category_source, target_game=target_game, active_index=active_index)
            else:
                self.load_games(filename=state.active_category_source)

    def init_layout(self):
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_container.grid_columnconfigure(0, weight=0, minsize=480)
        self.main_container.grid_columnconfigure(1, weight=3)
        self.main_container.grid_rowconfigure(0, weight=1)

        # Left Pane: Board + Moves
        self.left_pane_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_pane_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        self.left_board_panel = ctk.CTkFrame(
            self.left_pane_container, fg_color="#0f172a", corner_radius=8,
            border_width=1, border_color="#334155"
        )
        self.left_board_panel.pack(side="top", anchor="w", fill="none", expand=False, padx=0, pady=(0, 5))

        self.board_holder = ctk.CTkFrame(
            self.left_board_panel, fg_color="#172134", width=475, height=397,
            corner_radius=0
        )
        self.board_holder.pack(side="top", anchor="w", padx=10, pady=10)
        self.board_holder.pack_propagate(False)

        self.board_widget = ChessBoardWidget(self.board_holder, square_size=58)
        self.board_widget.pack(fill="both", expand=True)

        self.board_widget.on_step_back = self.on_prev_move
        self.board_widget.on_step_forward = self.on_next_move
        self.board_widget.on_jump_start = self.on_first_move
        self.board_widget.on_jump_end = self.on_last_move

        self.moves_container_frame = ctk.CTkFrame(
            self.left_pane_container, fg_color="#0f172a", corner_radius=8,
            border_width=1, border_color="#334155"
        )
        self.moves_container_frame.pack(side="top", fill="both", expand=True, padx=0, pady=0)

        self.moves_header_frame = ctk.CTkFrame(self.moves_container_frame, fg_color="transparent")
        self.moves_header_frame.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_moves_title = ctk.CTkLabel(
            self.moves_header_frame, text="Analysis", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_moves_title.pack(side="left")

        self.row_analysis_btns = ctk.CTkFrame(self.moves_header_frame, fg_color="transparent")
        self.row_analysis_btns.pack(side="left", padx=(15, 0))

        if not hasattr(self, "_active_pattern_mode"):
            self._active_pattern_mode = None

        def update_pattern_ui(mode):
            self._active_pattern_mode = mode

            is_motif = (mode == "motif")
            is_stats = (mode == "stats")

            self.btn_motif.configure(
                fg_color="#2e4a8c" if is_motif else "#1e293b",
                hover_color="#2e4a8c" if is_motif else "#1e293b"
            )
            self.btn_stats.configure(
                fg_color="#2e4a8c" if is_stats else "#1e293b",
                hover_color="#2e4a8c" if is_stats else "#1e293b"
            )

            self.trigger_pattern_mode(mode)

        is_motif = (self._active_pattern_mode == "motif")
        is_stats = (self._active_pattern_mode == "stats")

        self.btn_motif = ctk.CTkButton(
            self.row_analysis_btns,
            text="Motif Match",
            height=24,
            corner_radius=6,
            border_width=0,
            fg_color="#2e4a8c" if is_motif else "#1e293b",
            hover_color="#2e4a8c" if is_motif else "#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(size=11),
            command=lambda: update_pattern_ui("motif")
        )
        self.btn_motif.pack(side="left", padx=3)

        self.btn_stats = ctk.CTkButton(
            self.row_analysis_btns,
            text="Frequency",
            height=24,
            corner_radius=6,
            border_width=0,
            fg_color="#2e4a8c" if is_stats else "#1e293b",
            hover_color="#2e4a8c" if is_stats else "#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(size=11),
            command=lambda: update_pattern_ui("stats")
        )
        self.btn_stats.pack(side="left", padx=3)

        # Right Pane: Tree + Analysis + Game Details
        self.right_analysis_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_analysis_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=3)
        self.right_analysis_panel.rowconfigure(2, weight=1)
        self.right_analysis_panel.columnconfigure(0, weight=1)

        self.top_catalog_panel = ctk.CTkFrame(
            self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
            border_width=1, border_color="#334155"
        )
        self.top_catalog_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_empty_state = ctk.CTkLabel(
            self.top_catalog_panel, text="No games loaded in patterns analysis view.",
            font=ctk.CTkFont(size=11), text_color="gray70", wraplength=250
        )

        self.tree_frame = ctk.CTkFrame(self.top_catalog_panel, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.col_tree = ttk.Treeview(
            self.tree_frame, columns=("no", "white", "black", "result"),
            show="headings", selectmode="browse", height=3, takefocus=False,
            style="Borderless.Treeview"
        )
        self.col_tree.heading("no", text="No.")
        self.col_tree.heading("white", text="White Player", anchor="w")
        self.col_tree.heading("black", text="Black Player", anchor="w")
        self.col_tree.heading("result", text="Res")

        self.col_tree.column("no", width=30, anchor="center")
        self.col_tree.column("white", width=145, anchor="w")
        self.col_tree.column("black", width=145, anchor="w")
        self.col_tree.column("result", width=45, anchor="center")
        self.pgn_tree = self.col_tree

        self.pgn_scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.col_tree.yview)
        self.col_tree.configure(yscrollcommand=self.pgn_scrollbar.set)
        self.col_tree.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        self.pgn_scrollbar.pack(side="right", fill="y", padx=0, pady=0)

        # Analysis Container
        self.analysis_container_frame = ctk.CTkFrame(
            self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
            border_width=1, border_color="#334155"
        )
        self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_analysis_title = ctk.CTkLabel(
            self.analysis_container_frame, text="Analysis", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_analysis_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.analysis_inner_wrapper = ctk.CTkFrame(self.analysis_container_frame, fg_color="transparent")
        self.analysis_inner_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.analysis_textbox = ctk.CTkTextbox(
            self.analysis_inner_wrapper, fg_color="#1e293b", text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11), wrap="word", height=90
        )
        self.analysis_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")
        self.analysis_textbox.tag_config("active_move", background="#660000", foreground="#ffffff")
        self.analysis_textbox.pack(fill="both", expand=True, padx=0, pady=0)

        # PGN Data Panel
        self.pgn_data_panel = ctk.CTkFrame(
            self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
            border_width=1, border_color="#334155"
        )
        self.pgn_data_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.pgn_data_header = ctk.CTkFrame(self.pgn_data_panel, fg_color="transparent")
        self.pgn_data_header.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_pgn_data_title = ctk.CTkLabel(
            self.pgn_data_header, text="Game Details", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_pgn_data_title.pack(side="left")

        self.pgn_data_text = ctk.CTkTextbox(
            self.pgn_data_panel, fg_color="#1e293b", text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11), wrap="word", height=70
        )
        self.pgn_data_text._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0)
        self.pgn_data_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.pgn_data_text.insert("end", "[No game selected. Click a game to load its PGN moves...]\n")

    def pop_out_board(self, *args, **kwargs):
        if self.is_board_popped_out:
            if self.popout_window:
                self.popout_window.focus()
            return

        self.is_board_popped_out = True
        self.board_widget.pack_forget()

        self.popout_window = ctk.CTkToplevel(self)
        self.popout_window.title("Chess Board Analysis - Patterns Pop-out")
        self.popout_window.geometry("400x440")
        self.popout_window.configure(fg_color="#172134")
        self.popout_window.attributes("-topmost", True)
        self.popout_window.protocol("WM_DELETE_WINDOW", self.restore_popped_board)

        popout_container = ctk.CTkFrame(self.popout_window, fg_color="transparent")
        popout_container.pack(fill="both", expand=True, padx=20, pady=20)

        self.popout_board = ChessBoardWidget(popout_container, square_size=55)
        self.popout_board.pack(anchor="w", pady=(10, 10))

        fen_to_set = self.board_node.board().fen() if self.board_node else (
            self.current_game.board().fen() if self.current_game else chess.STARTING_FEN)
        self.popout_board.set_position_fen(fen_to_set)

    def restore_popped_board(self):
        self.is_board_popped_out = False

        if self.popout_window:
            try:
                self.popout_window.destroy()
            except Exception:
                pass
            self.popout_window = None
            self.popout_board = None

        if hasattr(self, "board_widget") and hasattr(self, "board_holder"):
            self.board_widget.pack(in_=self.board_holder, fill="both", expand=True)

        fen_to_set = self.board_node.board().fen() if self.board_node else (
            self.current_game.board().fen() if self.current_game else chess.STARTING_FEN)
        self.board_widget.set_position_fen(fen_to_set)

    def load_games_list(self, games_list):
        self.load_patterns_collection(games_list)

    def trigger_engine_mode(self, mode):
        self.active_engine_mode = mode
        if hasattr(self, "btn_review") and hasattr(self, "btn_candidates") and hasattr(self, "btn_standard"):
            for b in (self.btn_review, self.btn_candidates, self.btn_standard):
                b.configure(fg_color="#1e293b", hover_color="#334155")
            if mode == "review":
                self.btn_review.configure(fg_color="#2e4a8c", hover_color="#4870cd")
                EngineReviewMixin.trigger_engine_mode(self, "review")
            elif mode == "candidates":
                self.btn_candidates.configure(fg_color="#2e4a8c", hover_color="#4870cd")
                EngineCandidateMixin.trigger_engine_mode(self, "candidates")
            elif mode == "standard":
                self.btn_standard.configure(fg_color="#2e4a8c", hover_color="#4870cd")
                EngineStandardMixin.trigger_engine_mode(self, "standard")

    def _apply_tree_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.layout("Borderless.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure(
            "Borderless.Treeview",
            background="#172134",
            foreground="#f8fafc",
            fieldbackground="#172134",
            rowheight=18,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Borderless.Treeview",
            background=[("selected", "#2e4a8c")],
            foreground=[("selected", "#ffffff")]
        )
        style.configure(
            "Borderless.Treeview.Heading",
            background="#0f172a",
            foreground="#f8fafc",
            font=("Arial", 10, "bold"),
            relief="flat",
            borderwidth=0
        )

        target = getattr(self, "col_tree", None) or getattr(self, "pgn_tree", None)
        if target:
            try:
                target.configure(style="Borderless.Treeview", takefocus=False)
            except Exception:
                pass

    def _bind_analysis_events(self):
        target = getattr(self, "col_tree", None) or getattr(self, "pgn_tree", None)
        if target:
            target.bind("<<TreeviewSelect>>", self._on_tree_select, add="+")

    def _bind_keyboard_events(self):
        try:
            top_level = self.winfo_toplevel()
            top_level.bind_all("<Left>", lambda e: self._safe_handle(self.on_prev_move, e))
            top_level.bind_all("<Right>", lambda e: self._safe_handle(self.on_next_move, e))
            top_level.bind_all("<Up>", lambda e: self._safe_handle(self.on_first_move, e))
            top_level.bind_all("<Down>", lambda e: self._safe_handle(self.on_last_move, e))
            top_level.bind_all("f", lambda e: self._safe_handle(self.toggle_board_flip, e))
            top_level.bind_all("F", lambda e: self._safe_handle(self.toggle_board_flip, e))
        except Exception:
            pass

    def toggle_board_flip(self):
        if not self.winfo_ismapped():
            return
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self.board_widget, "toggle_flip"):
                self.board_widget.toggle_flip()
            elif hasattr(self.board_widget, "flip_board"):
                self.board_widget.flip_board()
        if self.is_board_popped_out and hasattr(self, "popout_board") and self.popout_board:
            if hasattr(self.popout_board, "toggle_flip"):
                self.popout_board.toggle_flip()
            elif hasattr(self.popout_board, "flip_board"):
                self.popout_board.flip_board()

    def _safe_handle(self, callback, event=None):
        if not self.winfo_ismapped():
            return
        try:
            focused = self.winfo_toplevel().focus_get()
            if isinstance(focused, (ctk.CTkTextbox, ctk.CTkEntry)):
                return
            callback()
        except Exception:
            pass

    def _on_tree_select(self, event):
        target = event.widget
        selected_items = target.selection()
        if not selected_items:
            return
        item_id = selected_items[0]
        self._handle_item_selection(item_id)

    def _handle_item_selection(self, item_id):
        if not item_id:
            return False

        lookup_dict = getattr(self, "game_lookup", None) or getattr(self, "preview_lookup", None)
        if lookup_dict and item_id in lookup_dict:
            game_data = lookup_dict[item_id]
            game = game_data[0] if isinstance(game_data, tuple) else game_data
            source_data = game_data[1] if isinstance(game_data, tuple) else getattr(self, "filename", None)

            state.active_analysis_game = game
            state.active_category_source = source_data
            self.load_game_from_state(game, category_source=source_data, update_tree_selection=False)
            return True
        return False

    def load_patterns_collection(self, games_list, target_game=None, active_index=None):
        self.game_list = list(games_list)
        self.preview_lookup = {}
        self.game_lookup = {}

        if self.col_tree:
            self.col_tree.delete(*self.col_tree.get_children())

        for idx, game_item in enumerate(self.game_list):
            headers = game_item.get("headers", {})
            white = headers.get("White", "Unknown")
            black = headers.get("Black", "Unknown")
            result = headers.get("Result", "*")
            eco = headers.get("ECO", "")

            node_id = self.col_tree.insert("", "end", values=(str(idx + 1), white, black, result, eco))
            self.preview_lookup[node_id] = game_item
            self.game_lookup[id(game_item)] = node_id

        if self.game_list:
            selected_idx = 0
            if active_index is not None and 0 <= active_index < len(self.game_list):
                selected_idx = active_index
            elif target_game is not None:
                for idx, g in enumerate(self.game_list):
                    if g == target_game or (
                            isinstance(target_game, dict) and g.get("game_object") == target_game.get("game_object")):
                        selected_idx = idx
                        break

            target_item = self.game_list[selected_idx]
            node_ids = list(self.preview_lookup.keys())
            if selected_idx < len(node_ids):
                target_node_id = node_ids[selected_idx]
                self.col_tree.selection_set(target_node_id)
                self.col_tree.see(target_node_id)

            load_func = getattr(self, "load_game", None) or getattr(self, "load_single_game", None) or getattr(self,
                                                                                                               "select_game",
                                                                                                               None)
            if load_func:
                load_func(target_item)

    def load_games(self, filename=None):
        if filename:
            self.filename = filename

        active_load_file = self.filename if self.filename else (BASE_PGN_DIR / "patterns_analysis.pgn")
        target = getattr(self, "col_tree", None) or getattr(self, "pgn_tree", None)
        if target:
            target.delete(*target.get_children())

        self.preview_lookup.clear()
        self.game_lookup.clear()
        game_list = []

        if Path(active_load_file).exists():
            try:
                with open(active_load_file, "r", encoding="utf-8") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        game_list.append(game)
            except Exception as e:
                set_status_message(f"Error loading patterns PGN file: {e}")

        self.game_list = game_list

        if target:
            for idx, game in enumerate(game_list, start=1):
                headers = game.headers
                white = headers.get("White", "Unknown")
                black = headers.get("Black", "Unknown")
                result = headers.get("Result", "*")

                item_id = target.insert("", "end", values=(idx, white, black, result))
                self.preview_lookup[item_id] = game
                self.game_lookup[item_id] = game

            if game_list and target.get_children():
                first_item = target.get_children()[0]
                target.selection_set(first_item)
                self.load_game_from_state(game_list[0], update_tree_selection=False)

        if not game_list and hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
            self.lbl_empty_state.pack(padx=10, pady=25, anchor="w")
        elif hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
            self.lbl_empty_state.pack_forget()

    def load_game_from_state(self, game_obj, category_file=None, category_source=None, update_tree_selection=True):
        if not game_obj:
            return

        self.current_game = game_obj
        self.board_node = game_obj
        self.active_game = game_obj
        self.root_game_node = game_obj
        self.current_node = game_obj

        if hasattr(self, "board_widget") and self.board_widget:
            try:
                fen_str = game_obj.board().fen()
                self.board_widget.set_position_fen(fen_str)
            except Exception:
                pass

        if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
            try:
                fen_str = game_obj.board().fen()
                self.popout_board.set_position_fen(fen_str)
            except Exception:
                pass

        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
                pgn_text_export = game_obj.accept(exporter)

                self.pgn_data_text.configure(state="normal")
                self.pgn_data_text.delete("1.0", "end")
                self.pgn_data_text.insert("end", pgn_text_export)
                self.pgn_data_text.configure(state="disabled")
            except Exception:
                pass

        if hasattr(self, "moves_textbox") and self.moves_textbox:
            try:
                self.moves_textbox.configure(state="normal")
                self.moves_textbox.delete("1.0", "end")

                temp_node = game_obj
                move_num = 1
                while temp_node.variations:
                    next_node = temp_node.variation(0)
                    san_move = temp_node.board().san(next_node.move)

                    if temp_node.board().turn == chess.WHITE:
                        move_str = f"{move_num}. {san_move} "
                    else:
                        move_str = f"{san_move} "
                        move_num += 1

                    tag_name = id(next_node)
                    self.moves_textbox.insert("end", move_str, ("default", str(tag_name)))
                    self.moves_textbox.tag_bind(str(tag_name), "<Button-1>", lambda e, n=next_node: self.jump_to_node(n))

                    temp_node = next_node

                self.moves_textbox.configure(state="disabled")
                self.update_active_move_highlight()
            except Exception:
                pass

        if update_tree_selection:
            target = getattr(self, "col_tree", None) or getattr(self, "pgn_tree", None)
            lookup_dict = getattr(self, "game_lookup", None) or getattr(self, "preview_lookup", None)
            if target and lookup_dict:
                for item_id, g in lookup_dict.items():
                    if g == game_obj:
                        target.selection_set(item_id)
                        target.see(item_id)
                        break

    def jump_to_node(self, target_node):
        self.board_node = target_node
        if hasattr(self, "board_widget") and self.board_widget:
            self.board_widget.set_position_fen(self.board_node.board().fen())
        if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
            try:
                self.popout_board.set_position_fen(self.board_node.board().fen())
            except Exception:
                pass
        self.update_active_move_highlight()

    def update_active_move_highlight(self):
        if not hasattr(self, "moves_textbox") or not self.moves_textbox:
            return

        try:
            self.moves_textbox.configure(state="normal")
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
            fen = self.board_node.board().fen()
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(fen)
            if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
                try:
                    self.popout_board.set_position_fen(fen)
                except Exception:
                    pass
            self.update_active_move_highlight()

    def on_next_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.variations:
            self.board_node = self.board_node.variation(0)
            fen = self.board_node.board().fen()
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(fen)
            if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
                try:
                    self.popout_board.set_position_fen(fen)
                except Exception:
                    pass
            self.update_active_move_highlight()

    def on_first_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            self.board_node = self.current_game
            fen = self.current_game.board().fen()
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(fen)
            if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
                try:
                    self.popout_board.set_position_fen(fen)
                except Exception:
                    pass
            self.update_active_move_highlight()

    def on_last_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game
            while node.variations:
                node = node.variation(0)
            self.board_node = node
            fen = node.board().fen()
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(fen)
            if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
                try:
                    self.popout_board.set_position_fen(fen)
                except Exception:
                    pass
            self.update_active_move_highlight()


def create_patterns_analysis_workspace(master, filename=None, initial_games=None):
    instance = PatternsAnalysis(master, filename=filename, initial_games=initial_games)
    instance.grid(row=0, column=0, sticky="nsew")
    state.analysis_workspace = instance
    return instance