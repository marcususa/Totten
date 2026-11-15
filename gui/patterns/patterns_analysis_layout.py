import customtkinter as ctk
from tkinter import ttk
from gui.chess_board import ChessBoardWidget
from core.constants import THEME, LAYOUT

class PatternsAnalysisLayoutMixin:
    """Mixin class to handle the complete CustomTkinter layout and widget instantiation for analysis views."""

    def init_layout(self):
        import gui.app_state as state

        if hasattr(state, "register_analysis_callback"):
            state.register_analysis_callback(self._safe_load_game)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_container.grid_columnconfigure(0, weight=0, minsize=LAYOUT["board_width"])
        self.main_container.grid_columnconfigure(1, weight=3)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_pane_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_pane_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        self.left_board_panel = ctk.CTkFrame(self.left_pane_container, fg_color=THEME["bg_panel"], corner_radius=8,
                                             border_width=1,
                                             border_color=THEME.get("border_color", THEME["bg_surface"]))
        self.left_board_panel.pack(side="top", anchor="w", fill="none", expand=False, padx=0, pady=(0, 5))

        self.board_holder = ctk.CTkFrame(self.left_board_panel, fg_color=THEME["bg_surface"],
                                         width=LAYOUT["board_width"], height=LAYOUT["board_height"],
                                         corner_radius=0)
        self.board_holder.pack(side="top", anchor="w", padx=10, pady=10)
        self.board_holder.pack_propagate(False)

        self.board_widget = ChessBoardWidget(self.board_holder, square_size=LAYOUT["square_size"])
        self.board_widget.pack(fill="both", expand=True)

        if hasattr(self, "on_prev_move"):
            self.board_widget.on_step_back = self.on_prev_move
        if hasattr(self, "on_next_move"):
            self.board_widget.on_step_forward = self.on_next_move
        if hasattr(self, "on_first_move"):
            self.board_widget.on_jump_start = self.on_first_move
        if hasattr(self, "on_last_move"):
            self.board_widget.on_jump_end = self.on_last_move

        self.engine_results_container_frame = ctk.CTkFrame(self.left_pane_container, fg_color=THEME["bg_panel"],
                                                           corner_radius=8,
                                                           border_width=1,
                                                           border_color=THEME.get("border_color", THEME["bg_surface"]))
        self.engine_results_container_frame.pack(side="top", fill="both", expand=True, padx=0, pady=0)

        self.engine_results_header_frame = ctk.CTkFrame(self.engine_results_container_frame, fg_color="transparent")
        self.engine_results_header_frame.pack(fill="x", padx=10, pady=(6, 2))

        self.row_analysis_btns = ctk.CTkFrame(self.engine_results_header_frame, fg_color="transparent")
        self.row_analysis_btns.pack(side="left", padx=0)

        if hasattr(self, "active_engine_mode"):
            self._active_engine_mode = self.active_engine_mode
        elif not hasattr(self, "_active_engine_mode"):
            self._active_engine_mode = None

        if not hasattr(self, "_engine_running"):
            self._engine_running = False

        if not hasattr(self, "_selected_mode_button"):
            self._selected_mode_button = None

        def toggle_engine_state():
            self._engine_running = not self._engine_running
            if hasattr(self, "btn_pv"):
                self.btn_pv.configure(
                    fg_color=THEME["btn_hover"] if self._engine_running else THEME["btn_initial"],
                    text="Stop" if self._engine_running else "PV Engine"
                )
            if hasattr(self, "toggle_engine_action"):
                self.toggle_engine_action()

        def set_analysis_mode(mode):
            self._selected_mode_button = mode
            self._active_engine_mode = mode
            self.active_engine_mode = mode
            update_analysis_buttons_state()
            if hasattr(self, "trigger_engine_mode"):
                self.trigger_engine_mode(mode)

        def update_analysis_buttons_state():
            buttons_map = {
                "white_patterns_mode": (self.btn_white, self.frame_white),
                "black_patterns_mode": (self.btn_black, self.frame_black),
                "opening_pattern_mode": (self.btn_opening, self.frame_opening),
                "calculation_pattern_mode": (self.btn_calculation, self.frame_calculation)
            }
            for m, (btn, frm) in buttons_map.items():
                is_selected = (self._selected_mode_button == m)
                btn.configure(
                    fg_color=THEME["btn_hover"] if is_selected else THEME["btn_initial"]
                )
                frm.configure(border_width=0 if is_selected else 1)

        def on_btn_enter(btn, mode, frm):
            if self._selected_mode_button != mode:
                btn.configure(fg_color=THEME["btn_hover"])
                frm.configure(border_width=0)

        def on_btn_leave(btn, mode, frm):
            if self._selected_mode_button != mode:
                btn.configure(fg_color=THEME["btn_initial"])
                frm.configure(border_width=1)

        def init_buttons_ui():
            for widget in self.row_analysis_btns.winfo_children():
                widget.destroy()

            btn_height = 20
            btn_corner = 6
            btn_font = ctk.CTkFont(size=11)
            btn_hover = THEME["btn_hover"]
            btn_initial = THEME["btn_initial"]
            text_color = THEME["text_primary"]
            border_color = THEME.get("border_color", THEME["bg_surface"])

            self.frame_pv = ctk.CTkFrame(
                self.row_analysis_btns, fg_color="transparent", corner_radius=btn_corner,
                border_width=0, border_color=border_color
            )
            self.frame_pv.pack(side="left", padx=(2, 4))

            self.btn_pv = ctk.CTkButton(
                self.frame_pv, text="Stop" if self._engine_running else "PV Engine", width=70,
                height=btn_height, corner_radius=btn_corner, border_width=0,
                fg_color=btn_hover if self._engine_running else btn_initial,
                hover_color=btn_hover, text_color=text_color, font=btn_font,
                command=toggle_engine_state
            )
            self.btn_pv.pack()

            def create_mode_button(text, width, mode_key):
                frm = ctk.CTkFrame(
                    self.row_analysis_btns, fg_color="transparent", corner_radius=btn_corner,
                    border_width=1, border_color=border_color
                )
                frm.pack(side="left", padx=2)
                btn = ctk.CTkButton(
                    frm, text=text, width=width, height=btn_height, corner_radius=btn_corner,
                    border_width=0, fg_color=btn_initial, hover_color=btn_hover,
                    text_color=text_color, font=btn_font,
                    command=lambda: set_analysis_mode(mode_key)
                )
                btn.bind("<Enter>", lambda e, b=btn, m=mode_key, f=frm: on_btn_enter(b, m, f))
                btn.bind("<Leave>", lambda e, b=btn, m=mode_key, f=frm: on_btn_leave(b, m, f))
                btn.pack()
                return btn, frm

            self.btn_white, self.frame_white = create_mode_button("White Patterns", 95, "white_patterns_mode")
            self.btn_black, self.frame_black = create_mode_button("Black Patterns", 95, "black_patterns_mode")
            self.btn_opening, self.frame_opening = create_mode_button("Opening", 75, "opening_pattern_mode")
            self.btn_calculation, self.frame_calculation = create_mode_button("Calculation", 80,
                                                                              "calculation_pattern_mode")

        init_buttons_ui()

        self.pv_inner_wrapper = ctk.CTkFrame(self.engine_results_container_frame, fg_color="transparent")
        self.pv_inner_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.pv_textbox = ctk.CTkTextbox(
            self.pv_inner_wrapper,
            fg_color=THEME["bg_surface"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=LAYOUT["pv_box_height"]
        )

        self.pv_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")
        self.pv_textbox.tag_config("active_move", background=THEME["active_tracker_bg"],
                                   foreground=THEME["active_tracker_fg"])
        self.pv_textbox.pack(fill="both", expand=True, padx=0, pady=2)

        self.right_analysis_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_analysis_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # 4-Row Configuration (Row 1 protected with minsize=32):
        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=0, minsize=32)
        self.right_analysis_panel.rowconfigure(2, weight=3)
        self.right_analysis_panel.rowconfigure(3, weight=1)
        self.right_analysis_panel.columnconfigure(0, weight=1)

        # --- Row 0: Top Catalog Panel ---
        self.top_catalog_panel = ctk.CTkFrame(self.right_analysis_panel, fg_color=THEME["bg_panel"], corner_radius=8,
                                              border_width=1,
                                              border_color=THEME.get("border_color", THEME["bg_surface"]))
        self.top_catalog_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.layout("Borderless.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure(
            "Borderless.Treeview",
            background=THEME["bg_surface"],
            foreground=THEME["text_primary"],
            fieldbackground=THEME["bg_surface"],
            rowheight=18,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Borderless.Treeview",
            background=[("selected", THEME["btn_hover"])],
            foreground=[("selected", "#ffffff")]
        )
        style.configure(
            "Borderless.Treeview.Heading",
            background=THEME["bg_panel"],
            foreground=THEME["text_primary"],
            font=("Arial", 10, "bold"),
            relief="flat",
            borderwidth=0
        )
        style.map(
            "Borderless.Treeview.Heading",
            background=[('active', THEME["bg_panel"]), ('selected', THEME["bg_panel"])],
            foreground=[('active', THEME["text_primary"]), ('selected', THEME["text_primary"])]
        )

        self.tree_frame = ctk.CTkFrame(self.top_catalog_panel, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.pgn_scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical")
        self.pgn_scrollbar.pack(side="right", fill="y", padx=(2, 0), pady=0)

        self.pgn_tree = ttk.Treeview(
            self.tree_frame,
            columns=("no", "white", "black", "result"),
            show="headings",
            selectmode="browse",
            height=3,
            takefocus=False,
            style="Borderless.Treeview"
        )
        self.pgn_tree.heading("no", text=" ")
        self.pgn_tree.heading("white", text="White Player", anchor="w")
        self.pgn_tree.heading("black", text="Black Player", anchor="w")
        self.pgn_tree.heading("result", text="Res")

        self.pgn_tree.column("no", width=30, anchor="center")
        self.pgn_tree.column("white", width=135, anchor="w")
        self.pgn_tree.column("black", width=135, anchor="w")
        self.pgn_tree.column("result", width=45, anchor="center")

        def _on_tree_selection(event):
            self._on_tree_selection_event(event)

        self.pgn_tree.bind("<<TreeviewSelect>>", _on_tree_selection)

        self.pgn_scrollbar.configure(command=self.pgn_tree.yview)
        self.pgn_tree.configure(yscrollcommand=self.pgn_scrollbar.set)
        self.pgn_tree.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # --- Row 1: Thin Evaluation Bar Panel (Good, Bad, IDK) ---
        self.eval_bar_frame = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color=THEME["bg_panel"],
            corner_radius=6,
            border_width=1,
            border_color=THEME.get("border_color", THEME["bg_surface"]),
            height=32
        )
        self.eval_bar_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 8))
        self.eval_bar_frame.grid_propagate(False)

        self.eval_bar_frame.grid_rowconfigure(0, weight=1)
        self.eval_bar_frame.grid_columnconfigure((0, 1, 2), weight=1)

        eval_btn_height = 20
        eval_btn_corner = 6
        eval_btn_font = ctk.CTkFont(size=11)
        eval_btn_hover = THEME["btn_hover"]
        eval_btn_initial = THEME["btn_initial"]
        eval_text_color = THEME["text_primary"]

        self.btn_eval_good = ctk.CTkButton(
            self.eval_bar_frame,
            text="Good",
            height=eval_btn_height,
            corner_radius=eval_btn_corner,
            border_width=0,
            fg_color=eval_btn_initial,
            hover_color=eval_btn_hover,
            text_color=eval_text_color,
            font=eval_btn_font,
            command=self._eval_good_action
        )
        self.btn_eval_good.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self.btn_eval_bad = ctk.CTkButton(
            self.eval_bar_frame,
            text="Bad",
            height=eval_btn_height,
            corner_radius=eval_btn_corner,
            border_width=0,
            fg_color=eval_btn_initial,
            hover_color=eval_btn_hover,
            text_color=eval_text_color,
            font=eval_btn_font,
            command=self._eval_bad_action
        )
        self.btn_eval_bad.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self.btn_eval_idk = ctk.CTkButton(
            self.eval_bar_frame,
            text="IDK",
            height=eval_btn_height,
            corner_radius=eval_btn_corner,
            border_width=0,
            fg_color=eval_btn_initial,
            hover_color=eval_btn_hover,
            text_color=eval_text_color,
            font=eval_btn_font,
            command=self._eval_idk_action
        )
        self.btn_eval_idk.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        # --- Row 2: Analysis Panel ---
        self.analysis_container_frame = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color=THEME["bg_panel"],
            corner_radius=8,
            border_width=1,
            border_color=THEME.get("border_color", THEME["bg_surface"])
        )
        self.analysis_container_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_analysis_title = ctk.CTkLabel(
            self.analysis_container_frame,
            text="Analysis",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.get("text_secondary", "#94a3b8")
        )
        self.lbl_analysis_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.analysis_wrapper = ctk.CTkFrame(self.analysis_container_frame, fg_color="transparent")
        self.analysis_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.analysis_textbox = ctk.CTkTextbox(
            self.analysis_wrapper,
            fg_color=THEME["bg_surface"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=LAYOUT["analysis_box_height"]
        )

        self.analysis_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")
        self.analysis_textbox.pack(fill="both", expand=True, padx=0, pady=0)

        # --- Row 3: Game Details Panel ---
        self.pgn_data_panel = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color=THEME["bg_panel"],
            corner_radius=8,
            border_width=1,
            border_color=THEME.get("border_color", THEME["bg_surface"])
        )
        self.pgn_data_panel.grid(row=3, column=0, sticky="nsew", padx=0, pady=0)

        self.pgn_data_header = ctk.CTkFrame(self.pgn_data_panel, fg_color="transparent")
        self.pgn_data_header.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_pgn_data_title = ctk.CTkLabel(
            self.pgn_data_header,
            text="Game Details",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.get("text_secondary", "#94a3b8")
        )
        self.lbl_pgn_data_title.pack(side="left")

        self.btn_close_pgn_data = ctk.CTkButton(
            self.pgn_data_header,
            text="X",
            width=26,
            height=26,
            fg_color="transparent",
            text_color=THEME.get("text_secondary", "#94a3b8"),
            hover_color=THEME.get("border_color", THEME["bg_surface"]),
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.toggle_pgn_data_panel
        )
        self.btn_close_pgn_data.pack(side="right")

        self.pgn_data_text = ctk.CTkTextbox(
            self.pgn_data_panel,
            fg_color=THEME["bg_surface"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=70
        )
        self.pgn_data_text._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0)
        self.pgn_data_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.pgn_data_text.insert("end", "[No game selected. Click a game to load its details...]\n")

        def _bind_keys(event=None):
            top = self.winfo_toplevel()
            top.bind_all("<Key-f>", self._handle_keypress)
            top.bind_all("<Key-F>", self._handle_keypress)
            top.bind_all("<Left>", self._handle_left)
            top.bind_all("<Right>", self._handle_right)
            top.bind_all("<Up>", self._handle_up)
            top.bind_all("<Down>", self._handle_down)

        self.bind("<Configure>", _bind_keys)
        self.after(100, _bind_keys)