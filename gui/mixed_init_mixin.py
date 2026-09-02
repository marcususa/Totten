import customtkinter as ctk
from tkinter import ttk
from .chess_board import ChessBoardWidget
import gui.app_state as state


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


class MixedInitMixin:
    """Mixin responsible for building the complete UI shell and layout for MixedAnalysis."""

    def init_layout(self):
        if hasattr(state, "register_analysis_callback"):
            state.register_analysis_callback(self.load_game)

        self.preview_lookup = {}
        self.game_lookup = {}
        self.active_game = None

        self.popout_window = None
        self.popout_board = None
        self.popout_container = None
        self.is_board_popped_out = False

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        # Adjusted master weights: Left side locked down/narrower, Right side claims expanded space
        self.main_container.grid_columnconfigure(0, weight=0, minsize=480)
        self.main_container.grid_columnconfigure(1, weight=3)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_pane_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_pane_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        self.left_board_panel = ctk.CTkFrame(
            self.left_pane_container,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.left_board_panel.pack(side="top", anchor="w", fill="none", expand=False, padx=0, pady=(0, 5))

        # Scaled to match the perfected left-aligned board layout (530x450 holder with 70px square size)
        self.board_holder = ctk.CTkFrame(self.left_board_panel, fg_color="#172134", width=530, height=450,
                                         corner_radius=0)
        self.board_holder.pack(side="top", anchor="w", padx=10, pady=10)
        self.board_holder.pack_propagate(False)

        self.board_widget = ChessBoardWidget(self.board_holder, square_size=70)
        self.board_widget.pack(fill="both", expand=True)

        # Wire integrated widget callbacks to parent methods
        self.board_widget.on_step_back = self.on_prev_move
        self.board_widget.on_step_forward = self.on_next_move
        self.board_widget.on_jump_start = self.on_first_move
        self.board_widget.on_jump_end = self.on_last_move

        self.placeholder_lbl = ctk.CTkLabel(
            self.board_holder, text="[ Board Popped Out ]", text_color="#94a3b8"
        )

        self.top_catalog_panel = ctk.CTkFrame(
            self.left_pane_container,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.top_catalog_panel.pack(side="top", fill="both", expand=True, padx=0, pady=0)

        self.lbl_empty_state = ctk.CTkLabel(
            self.top_catalog_panel,
            text="No games loaded in memory.",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            wraplength=250
        )

        self.tree_frame = ctk.CTkFrame(self.top_catalog_panel, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.col_tree = ttk.Treeview(
            self.tree_frame,
            columns=("no", "white", "black", "result"),
            show="headings",
            selectmode="browse",
            height=6,
            takefocus=False,
            style="Borderless.Treeview"
        )
        self.col_tree.heading("no", text="No.")
        self.col_tree.heading("white", text="White Player", anchor="w")
        self.col_tree.heading("black", text="Black Player", anchor="w")
        self.col_tree.heading("result", text="Res")

        # Trimmed column widths to fit cleanly within the slimmer left column footprint
        self.col_tree.column("no", width=30, anchor="center")
        self.col_tree.column("white", width=120, anchor="w")
        self.col_tree.column("black", width=120, anchor="w")
        self.col_tree.column("result", width=40, anchor="center")

        self.pgn_tree = self.col_tree

        self.pgn_scrollbar = ttk.Scrollbar(
            self.tree_frame,
            orient="vertical",
            command=self.col_tree.yview
        )
        self.col_tree.configure(yscrollcommand=self.pgn_scrollbar.set)
        self.col_tree.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        self.pgn_scrollbar.pack(side="right", fill="y", padx=0, pady=0)

        self.right_analysis_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_analysis_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=1)
        self.right_analysis_panel.rowconfigure(2, weight=0)
        self.right_analysis_panel.columnconfigure(0, weight=1)

        self.analysis_container_frame = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.analysis_container_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_analysis_title = ctk.CTkLabel(
            self.analysis_container_frame, text="Analysis", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_analysis_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.analysis_inner_wrapper = ctk.CTkFrame(self.analysis_container_frame, fg_color="transparent")
        self.analysis_inner_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.review_container = ctk.CTkFrame(self.analysis_inner_wrapper, fg_color="transparent")

        # Standard moves textbox layout (used for standard/candidates views)
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

        # Dedicated review tree frame structure mirroring catalog analysis initialization
        self.review_tree_frame = ctk.CTkFrame(self.analysis_inner_wrapper, fg_color="transparent")

        self.review_tree = ttk.Treeview(
            self.review_tree_frame,
            columns=("move_num", "player", "move", "eval", "classification"),
            show="headings",
            selectmode="browse",
            height=6,
            takefocus=False,
            style="Borderless.Treeview"
        )
        self.review_tree.heading("move_num", text="No.")
        self.review_tree.heading("player", text="Clr", anchor="center")
        self.review_tree.heading("move", text="Move", anchor="w")
        self.review_tree.heading("eval", text="Eval", anchor="center")
        self.review_tree.heading("classification", text="Class", anchor="w")

        self.review_tree.column("move_num", width=35, anchor="center")
        self.review_tree.column("player", width=30, anchor="center")
        self.review_tree.column("move", width=65, anchor="w")
        self.review_tree.column("eval", width=55, anchor="center")
        self.review_tree.column("classification", width=110, anchor="w")

        self.review_scrollbar = ttk.Scrollbar(
            self.review_tree_frame,
            orient="vertical",
            command=self.review_tree.yview
        )
        self.review_tree.configure(yscrollcommand=self.review_scrollbar.set)
        self.review_tree.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        self.review_scrollbar.pack(side="right", fill="y", padx=0, pady=0)

        self.review_container.pack(fill="both", expand=True)

        self.pgn_data_panel = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.pgn_data_panel.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_pgn_data_title = ctk.CTkLabel(
            self.pgn_data_panel, text="Game Details", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_data_title = self.lbl_pgn_data_title
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

        # 3. Bottom Panel: Engine Option Mode Controls
        self.controls_panel = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.controls_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.analysis_mode_content = ctk.CTkFrame(self.controls_panel, fg_color="transparent")
        self.analysis_mode_content.pack(fill="x", expand=True, padx=10, pady=10)

        self.row_analysis_layout = ctk.CTkFrame(self.analysis_mode_content, fg_color="transparent")
        self.row_analysis_layout.pack(anchor="w")

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