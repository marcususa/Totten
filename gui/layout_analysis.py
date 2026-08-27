import json
import gui.app_state as state
from pathlib import Path
from tkinter import ttk
import customtkinter as ctk
import chess
import chess.pgn
from gui.statusbar import set_status_message
from core.constants import CONFIG_FILE
from gui.chess_board import ChessBoardWidget


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


class LayoutAnalysisMixin:
    def __init__(self, parent, filename=None):
        pass

    def pop_out_board(self, *args, **kwargs):
        """Alias for popout_board to maintain compatibility across workspaces."""
        if hasattr(self, "popout_board_window"):
            return self.popout_board_window(*args, **kwargs)
        elif hasattr(self, "popout_board"):
            return self.popout_board(*args, **kwargs)

    def load_game(self, game_node, category_source=None):
        """Universal entry point. Delegates to specialized hardwired methods if available."""
        if hasattr(self, "load_game_hardwired"):
            return self.load_game_hardwired(game_node, category_source=category_source)
        return self.load_game_from_state(game_node, category_source=category_source)

    def load_game_from_state(self, game_node, category_source=None):
        """Base UI updater for board, text pane, and move traversal."""
        if game_node is None:
            return

        self.active_game = game_node
        self.root_game_node = game_node
        self.current_node = game_node

        # 1. Update main chessboard
        if hasattr(self, "board_widget") and self.board_widget:
            try:
                fen_str = game_node.board().fen()
                self.board_widget.set_position_fen(fen_str)
            except Exception:
                pass

        # 1b. Update popped-out board if active
        if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
            try:
                fen_str = game_node.board().fen()
                self.popout_board.set_position_fen(fen_str)
            except Exception:
                pass

        # 2. Display full PGN text
        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
                pgn_text_export = game_node.accept(exporter)

                self.pgn_data_text.configure(state="normal")
                self.pgn_data_text.delete("1.0", "end")
                self.pgn_data_text.insert("end", pgn_text_export)
                self.pgn_data_text.configure(state="disabled")
            except Exception:
                pass

        # 3. Load move list for analysis view navigation
        if hasattr(self, "_load_plain_game_moves"):
            try:
                self._load_plain_game_moves(game_node)
            except Exception:
                pass

    def init_layout(self):
        # Register the callback right when the layout builds
        if hasattr(state, "register_analysis_callback"):
            state.register_analysis_callback(self.load_game)

        self.preview_lookup = {}
        self.active_game = None
        self.active_engine_mode = "standard"

        # Pop-out Board Tracking
        self.popout_window = None
        self.popout_board = None
        self.popout_container = None
        self.is_board_popped_out = False

        # --- ROOT CONTAINER ---
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_container.grid_columnconfigure(0, weight=3)
        self.main_container.grid_columnconfigure(1, weight=2)
        self.main_container.grid_rowconfigure(0, weight=1)

        # =========================================================================
        # LEFT PANE CONTAINER (Chessboard on top, Hardwired Tree underneath)
        # =========================================================================
        self.left_pane_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_pane_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        # 1. Board Panel (Top Left)
        self.left_board_panel = ctk.CTkFrame(self.left_pane_container, fg_color="#0f172a", corner_radius=8,
                                             border_width=1, border_color="#334155")
        self.left_board_panel.pack(side="top", fill="both", expand=False, padx=0, pady=(0, 5))

        self.board_holder = ctk.CTkFrame(self.left_board_panel, fg_color="transparent")
        self.board_holder.pack(side="top", padx=10, pady=(10, 2))

        self.board_widget = ChessBoardWidget(self.board_holder, square_size=50)
        self.board_widget.pack()

        self.placeholder_lbl = ctk.CTkLabel(
            self.board_holder, text="[ Board Popped Out ]", text_color="#94a3b8"
        )

        self.board_controls = ctk.CTkFrame(self.left_board_panel, fg_color="transparent")
        self.board_controls.pack(side="top", fill="x", padx=10, pady=(2, 10))

        self.row_controls_layout = ctk.CTkFrame(self.board_controls, fg_color="transparent")
        self.row_controls_layout.pack(anchor="center")

        self.btn_prev = ctk.CTkButton(
            self.row_controls_layout,
            text="◀ Prev",
            width=80,
            height=26,
            fg_color="#2e4a8c",
            hover_color="#4870cd",
            command=self.on_prev_move
        )
        self.btn_prev.pack(side="left", padx=(0, 4))

        self.btn_popout = ctk.CTkButton(
            self.row_controls_layout,
            text="Pop Out ↗",
            width=85,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self.pop_out_board
        )
        self.btn_popout.pack(side="left", padx=4)

        self.btn_next = ctk.CTkButton(
            self.row_controls_layout,
            text="Next ▶",
            width=80,
            height=26,
            fg_color="#2e4a8c",
            hover_color="#4870cd",
            command=self.on_next_move
        )
        self.btn_next.pack(side="left", padx=(4, 0))

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
        self.controls_panel = ctk.CTkFrame(self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
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