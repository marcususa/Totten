import customtkinter as ctk
from tkinter import ttk
import gui.app_state as state
from .chess_board import ChessBoardWidget

# Configuration and Theme Constants
KEY_MAPPINGS = {
    "left": "Left",
    "right": "Right",
    "up": "Up",
    "down": "Down",
    "flip": "f",
    "flip_upper": "F"
}

THEME_CONFIG = {
    "current_move_bg": "#660000",
    "fallback_text": "#f8fafc",
    "eval_styles": {
        "blunder": {"bg": "#8B0000", "fg": "#ffffff"},
        "mistake": {"bg": "#CC6600", "fg": "#ffffff"},
        "good": {"bg": "transparent", "fg": "#00AA00"},
        "best": {"bg": "transparent", "fg": "#0000AA"}
    }
}


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
        tw.configure(fg_color="#0f172a")

        try:
            tw.wm_attributes("-disabled", True)
        except Exception:
            pass

        label = ctk.CTkLabel(
            tw,
            text=self.text,
            fg_color="#0f172a",
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


class CatalogInitMixin:
    """Mixin class to handle the UI initialization and layout for CatalogAnalysis."""

    def __init__(self, *args, **kwargs):
        self.theme_config = THEME_CONFIG
        self.key_mappings = KEY_MAPPINGS
        super().__init__(*args, **kwargs)

    def _safe_load_game(self, game_node, category_source=None):
        if category_source and category_source != "catalog":
            return
        self.load_game(game_node, category_source=category_source)

    def toggle_pgn_data_panel(self):
        if self.pgn_data_panel.winfo_ismapped():
            self.pgn_data_panel.grid_remove()
            self.right_analysis_panel.rowconfigure(2, weight=0, minsize=0)
            self.right_analysis_panel.rowconfigure(1, weight=4)
            self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 0))
        else:
            self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))
            self.right_analysis_panel.rowconfigure(1, weight=3)
            self.right_analysis_panel.rowconfigure(2, weight=1, minsize=0)
            self.pgn_data_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and hasattr(self.board_widget, "flip_board"):
            self.board_widget.flip_board()
        elif hasattr(self, "board_widget") and hasattr(self.board_widget, "invert"):
            self.board_widget.invert()

    def _handle_keypress(self, event=None):
        print("DEBUG: 'f' or 'F' pressed")
        if event and event.keysym in ("f", "F"):
            self.on_flip_board()
            return "break"

    def _handle_left(self, event=None):
        print("DEBUG: Left arrow pressed. Has on_prev_move:", hasattr(self, "on_prev_move"))
        if hasattr(self, "on_prev_move") and callable(self.on_prev_move):
            try:
                self.on_prev_move(event)
            except TypeError:
                self.on_prev_move()
        return "break"

    def _handle_right(self, event=None):
        print("DEBUG: Right arrow pressed. Has on_next_move:", hasattr(self, "on_next_move"))
        if hasattr(self, "on_next_move") and callable(self.on_next_move):
            try:
                self.on_next_move(event)
            except TypeError:
                self.on_next_move()
        return "break"

    def _handle_up(self, event=None):
        print("DEBUG: Up arrow pressed. Has on_first_move:", hasattr(self, "on_first_move"))
        if hasattr(self, "on_first_move") and callable(self.on_first_move):
            try:
                self.on_first_move(event)
            except TypeError:
                self.on_first_move()
        return "break"

    def _handle_down(self, event=None):
        print("DEBUG: Down arrow pressed. Has on_last_move:", hasattr(self, "on_last_move"))
        if hasattr(self, "on_last_move") and callable(self.on_last_move):
            try:
                self.on_last_move(event)
            except TypeError:
                self.on_last_move()
        return "break"

    def init_layout(self):
        if hasattr(state, "register_analysis_callback"):
            state.register_analysis_callback(self._safe_load_game)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_container.grid_columnconfigure(0, weight=0, minsize=480)
        self.main_container.grid_columnconfigure(1, weight=3)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_pane_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_pane_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        self.left_board_panel = ctk.CTkFrame(self.left_pane_container, fg_color="#0f172a", corner_radius=8,
                                             border_width=1, border_color="#334155")
        self.left_board_panel.pack(side="top", anchor="w", fill="none", expand=False, padx=0, pady=(0, 5))

        self.board_holder = ctk.CTkFrame(self.left_board_panel, fg_color="#172134", width=475, height=397,
                                         corner_radius=0)
        self.board_holder.pack(side="top", anchor="w", padx=10, pady=10)
        self.board_holder.pack_propagate(False)

        self.board_widget = ChessBoardWidget(self.board_holder, square_size=58)
        self.board_widget.pack(fill="both", expand=True)

        self.board_widget.on_step_back = self.on_prev_move
        self.board_widget.on_step_forward = self.on_next_move
        self.board_widget.on_jump_start = self.on_first_move
        self.board_widget.on_jump_end = self.on_last_move

        self.moves_container_frame = ctk.CTkFrame(self.left_pane_container, fg_color="#0f172a", corner_radius=8,
                                                  border_width=1, border_color="#334155")
        self.moves_container_frame.pack(side="top", fill="both", expand=True, padx=0, pady=0)

        self.moves_header_frame = ctk.CTkFrame(self.moves_container_frame, fg_color="transparent")
        self.moves_header_frame.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_moves_title = ctk.CTkLabel(
            self.moves_header_frame, text="Engine", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_moves_title.pack(side="left")

        self.row_analysis_btns = ctk.CTkFrame(self.moves_header_frame, fg_color="transparent")
        self.row_analysis_btns.pack(side="left", padx=(10, 0))

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

        self.moves_textbox = ctk.CTkTextbox(
            self.moves_container_frame,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word"
        )
        self.moves_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")
        self.moves_textbox.tag_config("active_move", background="#660000", foreground="#ffffff")
        self.moves_textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.right_analysis_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_analysis_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=3)
        self.right_analysis_panel.rowconfigure(2, weight=1)
        self.right_analysis_panel.columnconfigure(0, weight=1)

        self.top_catalog_panel = ctk.CTkFrame(self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
                                              border_width=1, border_color="#334155")
        self.top_catalog_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))

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
            height=3,
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

        self.analysis_container_frame = ctk.CTkFrame(self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
                                                     border_width=1, border_color="#334155")
        self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_analysis_title = ctk.CTkLabel(
            self.analysis_container_frame, text="Analysis", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_analysis_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.analysis_inner_wrapper = ctk.CTkFrame(self.analysis_container_frame, fg_color="transparent")
        self.analysis_inner_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.analysis_textbox = ctk.CTkTextbox(
            self.analysis_inner_wrapper,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=90
        )
        self.analysis_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")
        self.analysis_textbox.tag_config("active_move", background="#660000", foreground="#ffffff")
        self.analysis_textbox.pack(fill="both", expand=True, padx=0, pady=0)

        self.pgn_data_panel = ctk.CTkFrame(self.right_analysis_panel, fg_color="#0f172a", corner_radius=8,
                                           border_width=1, border_color="#334155")
        self.pgn_data_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.pgn_data_header = ctk.CTkFrame(self.pgn_data_panel, fg_color="transparent")
        self.pgn_data_header.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_pgn_data_title = ctk.CTkLabel(
            self.pgn_data_header, text="Game Details", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_pgn_data_title.pack(side="left")

        self.btn_close_pgn_data = ctk.CTkButton(
            self.pgn_data_header, text="X", width=26, height=26,
            fg_color="transparent", text_color="#94a3b8", hover_color="#334155",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.toggle_pgn_data_panel
        )
        self.btn_close_pgn_data.pack(side="right")

        self.pgn_data_text = ctk.CTkTextbox(
            self.pgn_data_panel,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=70
        )
        self.pgn_data_text._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0)
        self.pgn_data_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.pgn_data_text.insert("end", "[No game selected. Click a game to load its PGN moves...]\n")

        def _bind_keys(event=None):
            top = self.winfo_toplevel()
            top.bind_all("<Key-f>", self._handle_keypress)
            top.bind_all("<Key-F>", self._handle_keypress)
            top.bind_all("<Left>", self._handle_left)
            top.bind_all("<Right>", self._handle_right)
            top.bind_all("<Up>", self._handle_up)
            top.bind_all("<Down>", self._handle_down)

        self.bind("<Map>", _bind_keys)
        self.after(100, _bind_keys)