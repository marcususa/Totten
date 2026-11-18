# ==========================================
# FILE: gui/patterns/patterns_layout.py
# ==========================================

import customtkinter as ctk
from tkinter import ttk
from gui.chess_board import ChessBoardWidget
from core.constants import THEME, LAYOUT
from gui.statusbar import set_status_message


class PatternsAnalysisLayoutMixin:
    """Mixin class to handle the complete CustomTkinter layout and widget instantiation for analysis views."""

    def init_layout(self):
        import gui.app_state as state

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

        # --- Dynamic Engine Button Creation in Header ---
        self.btn_pv = ctk.CTkButton(
            self.engine_results_header_frame,
            text="Engine",
            width=70,
            height=20,
            corner_radius=6,
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=11),
            command=self.toggle_engine_action
        )
        self.btn_pv.pack(side="right", padx=4)

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

        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=0, minsize=32)
        self.right_analysis_panel.rowconfigure(2, weight=3)
        self.right_analysis_panel.rowconfigure(3, weight=1)
        self.right_analysis_panel.columnconfigure(0, weight=1)

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

        self.eval_bar_frame = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color=THEME["bg_panel"],
            corner_radius=6,
            border_width=1,
            border_color=THEME.get("border_color", THEME["bg_surface"]),
            height=32
        )
        self.eval_bar_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 8))

    def _bind_engine_buttons(self):
        """Binds the standalone engine comparison button and handles mode selection."""
        if hasattr(self, "btn_pv") and self.btn_pv:
            self.btn_pv.configure(
                text="Engine",
                command=self.toggle_engine_action,
                hover_color=THEME["btn_hover"]
            )

        # --- White Patterns ---
        for btn_name in ("btn_white", "btn_white_patterns"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(
                    text="White Patterns",
                    command=lambda: (
                        print("[DEBUG CLICK] White Patterns clicked!"),
                        self.open_patterns_pgn_window(
                            [g for g in self.game_list if getattr(self, "_is_white_pattern", lambda x: True)(g)],
                            title="White Patterns - PGN Export"
                        )
                    ),
                    hover_color=THEME["btn_hover"]
                )
                break

        # --- Black Patterns ---
        for btn_name in ("btn_black", "btn_black_patterns"):
            btn = getattr(self, btn_name, None)
            if btn:
                btn.configure(
                    text="Black Patterns",
                    command=lambda: (
                        print("[DEBUG CLICK] Black Patterns clicked!"),
                        self.open_patterns_pgn_window(
                            [g for g in self.game_list if getattr(self, "_is_black_pattern", lambda x: True)(g)],
                            title="Black Patterns - PGN Export"
                        )
                    ),
                    hover_color=THEME["btn_hover"]
                )
                break

    def toggle_engine_action(self):
        """Toggles the evaluation engine analysis state securely in the Patterns section."""
        if not hasattr(self, "_engine_running"):
            self._engine_running = False

        self._engine_running = not self._engine_running

        if self._engine_running:
            if hasattr(self, "start_engine") and callable(self.start_engine):
                self.start_engine()
            elif hasattr(self, "run_evaluation") and callable(self.run_evaluation):
                self.run_evaluation()

            if hasattr(self, "btn_pv") and self.btn_pv:
                self.btn_pv.configure(fg_color=THEME["btn_hover"])
            set_status_message("Engine analysis started")
        else:
            if hasattr(self, "stop_engine") and callable(self.stop_engine):
                self.stop_engine()
            elif hasattr(self, "stop_evaluation") and callable(self.stop_evaluation):
                self.stop_evaluation()

            if hasattr(self, "btn_pv") and self.btn_pv:
                self.btn_pv.configure(fg_color=THEME["btn_initial"])
            set_status_message("Engine analysis stopped")