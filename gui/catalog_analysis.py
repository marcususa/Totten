import json
from pathlib import Path
from tkinter import ttk
import customtkinter as ctk
import chess
import chess.pgn

import gui.app_state as state
from gui.statusbar import set_status_message
from core.constants import CONFIG_FILE
from .chess_board import ChessBoardWidget


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
            self.tooltip_window.destroy()
            self.tooltip_window = None


def get_saved_pgn_filename():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("current_pgn_filename")
        except Exception:
            pass
    return None


class CatalogAnalysis(ctk.CTkFrame):
    """
    Dedicated self-contained workspace controller for Catalog Analysis.
    Absorbs the complete layout grid, tree view navigation, board management, and PGN state handling.
    """

    def __init__(self, parent, filename=None, initial_games=None, *args, **kwargs):
        super().__init__(parent, fg_color="#172134", corner_radius=0, *args, **kwargs)
        self.filename = filename or "personal_catalog.pgn"

        # Pull from isolated state immediately if initial_games is empty
        if not initial_games and hasattr(state, "catalog_state"):
            initial_games = state.catalog_state.get("active_games")

        self.game_list = list(initial_games) if initial_games else []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}

        # State tracking fields absorbed from layout mixin
        self.active_game = None
        self.root_game_node = None
        self.current_node = None
        self.active_engine_mode = "standard"

        # Initialize the full UI shell layout
        self.init_layout()

        # Initial load of catalog data (will skip file load if initial_games were provided)
        self.load_catalog_data()

    def load_games_list(self, games_list, focused_game=None):
        """Populates the analysis view with a filtered subset of games and loads the board."""
        if not games_list:
            return

        self.game_list = games_list

        # 1. Populate the sidebar game tree with the filtered list
        if hasattr(self, "populate_catalog_tree"):
            self.populate_catalog_tree(self.game_list)

        # 2. Load the target game onto the active analysis board
        target_game = focused_game if focused_game else games_list[0]
        if hasattr(self, "load_game"):
            self.load_game(target_game)

    def pop_out_board(self, *args, **kwargs):
        """Triggers the built-in chessboard widget popout mechanism."""
        if hasattr(self, "board_widget") and self.board_widget and hasattr(self.board_widget, "toggle_popout"):
            self.board_widget.toggle_popout()

    def load_game(self, game_node, category_source=None):
        """Universal entry point. Delegates to specialized hardwired methods if available."""
        if hasattr(self, "load_game_hardwired"):
            return self.load_game_hardwired(game_node, category_source=category_source)
        return self.load_game_from_state(game_node, category_source=category_source)

    def load_catalog_data(self):
        """Loads games from the target catalog PGN file into memory silently if no subset is active."""
        # ABSOLUTE GUARD: If self.game_list already contains games (like our 5-game subset),
        # do not touch the hard drive or reload the master catalog under any circumstances.
        if self.game_list:
            if hasattr(self, "pgn_tree"):
                self.populate_catalog_tree(self.game_list)
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

    def populate_catalog_tree(self, games_to_display, active_game=None):
        """Populates the tree view with the provided list of catalog games."""
        if not hasattr(self, "pgn_tree") or not hasattr(self, "preview_lookup"):
            return

        self.pgn_tree.delete(*self.pgn_tree.get_children())
        self.preview_lookup.clear()

        if hasattr(self, "lbl_empty_state") and self.lbl_empty_state and games_to_display:
            try:
                self.lbl_empty_state.pack_forget()
            except Exception:
                pass

        target = active_game or (games_to_display[0] if games_to_display else None)

        for idx, g in enumerate(games_to_display, start=1):
            headers = g.headers
            white = headers.get("White", "Unknown")
            black = headers.get("Black", "Unknown")
            result = headers.get("Result", "*")

            item_id = self.pgn_tree.insert("", "end", values=(idx, white, black, result))
            self.preview_lookup[item_id] = g

            if target and g == target:
                self.pgn_tree.selection_set(item_id)
                self.pgn_tree.see(item_id)

        if target:
            self.load_game_from_state(target)

    def load_games_by_eco(self, eco_code, active_game=None):
        """Filters and displays catalog games by ECO code."""
        if not eco_code:
            return

        eco_clean = str(eco_code).strip().upper()

        if not self.game_list and hasattr(state, "all_games") and state.all_games:
            self.game_list = state.all_games
        elif not self.game_list:
            self.load_catalog_data()

        eco_games = [
            g for g in self.game_list
            if hasattr(g, "headers") and g.headers.get("ECO", "").strip().upper() == eco_clean
        ]

        target_game = active_game or (eco_games[0] if eco_games else None)

        if eco_games:
            if hasattr(state, "active_category_source"):
                state.active_category_source = eco_games

        self.populate_catalog_tree(eco_games, active_game=target_game)

    def load_game_hardwired(self, game_node, category_source=None):
        """Hardwired highway entry point for Catalog Analysis view updates."""
        if isinstance(category_source, list):
            self.game_list = category_source
            self.populate_catalog_tree(self.game_list, active_game=game_node)
        else:
            self.load_game_from_state(game_node)

    def on_hardwired_tree_select(self, game):
        """Catalog-specific tree row selection action."""
        self.load_game_from_state(game)

    def load_game_from_state(self, game_obj, category_source=None):
        """Loads a game object into the analysis board, notation view, and header metadata."""
        if not game_obj:
            return

        self.current_game = game_obj
        self.board_node = game_obj
        self.active_game = game_obj
        self.root_game_node = game_obj
        self.current_node = game_obj

        # 1. Update main chessboard
        if hasattr(self, "board_widget") and self.board_widget:
            try:
                fen_str = game_obj.board().fen()
                self.board_widget.set_position_fen(fen_str)
            except Exception:
                pass

        headers = game_obj.headers
        white = headers.get("White", "Unknown")
        black = headers.get("Black", "Unknown")
        result = headers.get("Result", "*")

        # 2. Update full PGN text details
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

        # 3. Update main moves view textbox notation with clean movement tracking and interactive highlighting tags
        if hasattr(self, "moves_textbox") and self.moves_textbox:
            try:
                self.moves_textbox.configure(state="normal")
                self.moves_textbox.delete("1.0", "end")

                # Reconstruct mainline moves with explicit move numbers and insert them as separate tagged chunks
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

                    # Insert the move linked directly to its target node object via a unique tag name
                    tag_name = id(next_node)
                    self.moves_textbox.insert("end", move_str, ("default", str(tag_name)))

                    # Bind click event on this specific move token's tag range
                    self.moves_textbox.tag_bind(str(tag_name), "<Button-1>",
                                                lambda e, n=next_node: self.jump_to_node(n))

                    temp_node = next_node

                self.moves_textbox.configure(state="disabled")
                self.update_active_move_highlight()
            except Exception:
                pass

        # 4. Fallback plain moves loader integration if referenced
        if hasattr(self, "_load_plain_game_moves"):
            try:
                self._load_plain_game_moves(game_obj)
            except Exception:
                pass

    def jump_to_node(self, target_node):
        """Jumps directly to a specific game node when clicked in the move list."""
        self.board_node = target_node
        if hasattr(self, "board_widget") and self.board_widget:
            self.board_widget.set_position_fen(self.board_node.board().fen())
        self.update_active_move_highlight()

    def update_active_move_highlight(self):
        """Updates the active background highlight in the moves textbox corresponding to self.board_node."""
        if not hasattr(self, "moves_textbox") or not self.moves_textbox:
            return

        try:
            self.moves_textbox.configure(state="normal")
            self.moves_textbox.tag_remove("active_move", "1.0", "end")

            # If we are past the root, highlight the current board_node's tag
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
                self.board_widget.set_position_fen(self.board_node.board().fen())
            self.update_active_move_highlight()

    def on_next_move(self, event=None):
        if hasattr(self, "board_node") and self.board_node and self.board_node.variations:
            self.board_node = self.board_node.variation(0)
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.board_node.board().fen())
            self.update_active_move_highlight()

    def on_first_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            self.board_node = self.current_game
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(self.current_game.board().fen())
            self.update_active_move_highlight()

    def on_last_move(self, event=None):
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game
            while node.variations:
                node = node.variation(0)
            self.board_node = node
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(node.board().fen())
            self.update_active_move_highlight()

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and self.board_widget:
            if hasattr(self.board_widget, "flip_board"):
                self.board_widget.flip_board()
            elif hasattr(self.board_widget, "toggle_flip"):
                self.board_widget.toggle_flip()

    def trigger_engine_mode(self, mode):
        self.active_engine_mode = mode
        if hasattr(self, "btn_review") and hasattr(self, "btn_candidates") and hasattr(self, "btn_standard"):
            for b in (self.btn_review, self.btn_candidates, self.btn_standard):
                b.configure(fg_color="#1e293b", hover_color="#334155")
            if mode == "review":
                self.btn_review.configure(fg_color="#2e4a8c", hover_color="#4870cd")
            elif mode == "candidates":
                self.btn_candidates.configure(fg_color="#2e4a8c", hover_color="#4870cd")
            elif mode == "standard":
                self.btn_standard.configure(fg_color="#2e4a8c", hover_color="#4870cd")

    def init_layout(self):
        # Register the callback right when the layout builds
        if hasattr(state, "register_analysis_callback"):
            state.register_analysis_callback(self.load_game)

        # --- ROOT CONTAINER ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_container.grid_columnconfigure(0, weight=0, minsize=480)
        self.main_container.grid_columnconfigure(1, weight=3)
        self.main_container.grid_rowconfigure(0, weight=1)

        # =========================================================================
        # LEFT PANE CONTAINER (Chessboard on top, Hardwired Tree underneath)
        # =========================================================================
        self.left_pane_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_pane_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        # 1. Board Panel (Top Left) - Aligned to the left using anchor="w"
        self.left_board_panel = ctk.CTkFrame(self.left_pane_container, fg_color="#0f172a", corner_radius=8,
                                             border_width=1, border_color="#334155")
        self.left_board_panel.pack(side="top", anchor="w", fill="none", expand=False, padx=0, pady=(0, 5))

        # Initial board and piece sizing
        self.board_holder = ctk.CTkFrame(self.left_board_panel, fg_color="#172134", width=475, height=400,
                                         corner_radius=0)
        self.board_holder.pack(side="top", anchor="w", padx=10, pady=10)
        self.board_holder.pack_propagate(False)

        self.board_widget = ChessBoardWidget(self.board_holder, square_size=58)
        self.board_widget.pack(fill="both", expand=True)

        # Wire integrated widget callbacks to parent methods
        self.board_widget.on_step_back = self.on_prev_move
        self.board_widget.on_step_forward = self.on_next_move
        self.board_widget.on_jump_start = self.on_first_move
        self.board_widget.on_jump_end = self.on_last_move

        # 2. Hardwired Tree Panel (Directly beneath board)
        self.top_catalog_panel = ctk.CTkFrame(self.left_pane_container, fg_color="#0f172a", corner_radius=8,
                                              border_width=1, border_color="#334155")
        self.top_catalog_panel.pack(side="top", fill="both", expand=True, padx=0, pady=0)

        self.lbl_empty_state = ctk.CTkLabel(
            self.top_catalog_panel,
            text="No games loaded in memory.",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            wraplength=250
        )

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
            rowheight=22,
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
        style.map(
            "Borderless.Treeview.Heading",
            background=[('active', '#0f172a'), ('selected', '#0f172a')],
            foreground=[('active', '#f8fafc'), ('selected', '#f8fafc')]
        )

        self.tree_frame = ctk.CTkFrame(self.top_catalog_panel, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.pgn_tree = ttk.Treeview(
            self.tree_frame,
            columns=("no", "white", "black", "result"),
            show="headings",
            selectmode="browse",
            height=6,
            takefocus=False,
            style="Borderless.Treeview"
        )
        self.pgn_tree.heading("no", text="No.")
        self.pgn_tree.heading("white", text="White Player", anchor="w")
        self.pgn_tree.heading("black", text="Black Player", anchor="w")
        self.pgn_tree.heading("result", text="Res")

        self.pgn_tree.column("no", width=30, anchor="center")
        self.pgn_tree.column("white", width=145, anchor="w")
        self.pgn_tree.column("black", width=145, anchor="w")
        self.pgn_tree.column("result", width=45, anchor="center")

        def _on_tree_selection(event):
            selected_items = self.pgn_tree.selection()
            if not selected_items:
                return
            item_id = selected_items[0]
            if hasattr(self, "preview_lookup") and item_id in self.preview_lookup:
                game = self.preview_lookup[item_id]
                if hasattr(self, "on_hardwired_tree_select"):
                    self.on_hardwired_tree_select(game)
                else:
                    self.load_game_from_state(game)

        self.pgn_tree.bind("<<TreeviewSelect>>", _on_tree_selection)

        self.pgn_scrollbar = ttk.Scrollbar(
            self.tree_frame,
            orient="vertical",
            command=self.pgn_tree.yview
        )
        self.pgn_tree.configure(yscrollcommand=self.pgn_scrollbar.set)
        self.pgn_tree.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        self.pgn_scrollbar.pack(side="right", fill="y", padx=0, pady=0)

        # =========================================================================
        # RIGHT SIDE: ANALYSIS, GAME DETAILS, & ENGINE CONTROLS
        # =========================================================================
        self.right_analysis_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_analysis_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=1)
        self.right_analysis_panel.rowconfigure(2, weight=0)
        self.right_analysis_panel.columnconfigure(0, weight=1)

        # 1. Analysis Frame (Top Right)
        self.analysis_container_frame = ctk.CTkFrame(self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
                                                     border_width=1, border_color="#334155")
        self.analysis_container_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_analysis_title = ctk.CTkLabel(
            self.analysis_container_frame, text="Analysis", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_analysis_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.analysis_inner_wrapper = ctk.CTkFrame(self.analysis_container_frame, fg_color="transparent")
        self.analysis_inner_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.review_container = ctk.CTkFrame(self.analysis_inner_wrapper, fg_color="transparent")

        self.moves_textbox = ctk.CTkTextbox(
            self.review_container,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=110
        )
        self.moves_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")

        self.moves_textbox.tag_config("red", foreground="#FF4444")
        self.moves_textbox.tag_config("orange", foreground="#FFA500")
        self.moves_textbox.tag_config("green", foreground="#00C851")
        self.moves_textbox.tag_config("light_blue", foreground="#33b5e5")
        self.moves_textbox.tag_config("default", foreground="#f8fafc")
        self.moves_textbox.tag_config("active_move", background="#660000", foreground="#ffffff")

        self.moves_textbox.pack(fill="both", expand=True, padx=0, pady=0)
        self.review_container.pack(fill="both", expand=True)

        self.candidates_container = ctk.CTkFrame(self.analysis_inner_wrapper, fg_color="transparent")

        self.candidates_textbox = ctk.CTkTextbox(
            self.candidates_container,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            height=80,
            wrap="none"
        )
        self.candidates_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0)

        self.candidates_textbox.tag_config("red", foreground="#FF4444")
        self.candidates_textbox.tag_config("orange", foreground="#FFA500")
        self.candidates_textbox.tag_config("green", foreground="#00C851")
        self.candidates_textbox.tag_config("light_blue", foreground="#33b5e5")
        self.candidates_textbox.tag_config("default", foreground="#f8fafc")
        self.candidates_textbox.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # 2. Game Details Panel (Middle Right)
        self.pgn_data_panel = ctk.CTkFrame(self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
                                           border_width=1, border_color="#334155")
        self.pgn_data_panel.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_pgn_data_title = ctk.CTkLabel(
            self.pgn_data_panel, text="Game Details", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_pgn_data_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.pgn_data_text = ctk.CTkTextbox(
            self.pgn_data_panel,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=80
        )
        self.pgn_data_text._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0)
        self.pgn_data_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.pgn_data_text.insert("end", "[No game selected. Click a game to load its PGN moves...]\n")

        # 3. Engine Modes Frame (Bottom Right)
        self.controls_panel = ctk.CTkFrame(self.right_analysis_panel,fg_color="#0f172a", corner_radius=8,
                                           border_width=1, border_color="#334155")
        self.controls_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.analysis_mode_content = ctk.CTkFrame(self.controls_panel, fg_color="transparent")
        self.analysis_mode_content.pack(fill="x", expand=True, padx=10, pady=10)

        self.row_analysis_layout = ctk.CTkFrame(self.analysis_mode_content, fg_color="transparent")
        self.row_analysis_layout.pack(anchor="center")

        self.lbl_engine_title = ctk.CTkLabel(
            self.row_analysis_layout, text="Engine", font=ctk.CTkFont(size=11), text_color="#94a3b8"
        )
        self.lbl_engine_title.pack(side="left", padx=(0, 8))

        self.row_analysis_btns = ctk.CTkFrame(self.row_analysis_layout, fg_color="transparent")
        self.row_analysis_btns.pack(side="left")

        self.btn_review = ctk.CTkButton(
            self.row_analysis_btns,
            text="1",
            width=24,
            height=24,
            fg_color="#2e4a8c",
            hover_color="#4870cd",
            command=lambda: self.trigger_engine_mode("review")
        )
        self.btn_review.pack(side="left", padx=2)
        ToolTip(self.btn_review, "Game Review")

        self.btn_candidates = ctk.CTkButton(
            self.row_analysis_btns,
            text="2",
            width=24,
            height=24,
            fg_color="#1e293b",
            hover_color="#334155",
            command=lambda: self.trigger_engine_mode("candidates")
        )
        self.btn_candidates.pack(side="left", padx=2)
        ToolTip(self.btn_candidates, "Candidate Moves")

        self.btn_standard = ctk.CTkButton(
            self.row_analysis_btns,
            text="3",
            width=24,
            height=24,
            fg_color="#1e293b",
            hover_color="#334155",
            command=lambda: self.trigger_engine_mode("standard")
        )
        self.btn_standard.pack(side="left", padx=2)
        ToolTip(self.btn_standard, "Standard")

        # --- BIND KEYBOARD SHORTCUTS AT APPLICATION LEVEL & ROBUST FOCUS CAPTURE ---
        def _bind_keys(event=None):
            top = self.winfo_toplevel()
            top.bind("<f>", self.on_flip_board)
            top.bind("<F>", self.on_flip_board)
            top.bind("<Left>", self.on_prev_move)
            top.bind("<Right>", self.on_next_move)
            top.bind("<Up>", self.on_first_move)
            top.bind("<Down>", self.on_last_move)

        self.bind("<Map>", _bind_keys)
        self.after(100, _bind_keys)


def create_workspace(master, initial_games=None, **kwargs):
    """Instantiates CatalogAnalysis, utilizing filtered games from search or group selection."""
    import gui.app_state as state_mod

    # 1. Capture from state if not explicitly passed, checking all potential search/filter sources
    if initial_games is None:
        initial_games = (
            getattr(state_mod, "active_group_games", None) or
            getattr(state_mod, "active_search_results", None) or
            getattr(state_mod, "active_category_source", None)
        )

    focus = getattr(state_mod, "active_focus_game", None)

    # 2. Instantiate with the captured subset
    instance = CatalogAnalysis(master, filename="personal_catalog.pgn", initial_games=initial_games)

    # 3. Apply focus or initial selection
    if focus and hasattr(instance, "load_game"):
        instance.load_game(focus)
    elif initial_games and hasattr(instance, "load_game"):
        instance.load_game(initial_games[0])

    # 4. Clear transient state variables after consumption
    if hasattr(state_mod, "active_group_games"):
        state_mod.active_group_games = None
    if hasattr(state_mod, "active_search_results"):
        state_mod.active_search_results = None
    if hasattr(state_mod, "active_focus_game"):
        state_mod.active_focus_game = None

    state_mod.workspace = instance
    return instance