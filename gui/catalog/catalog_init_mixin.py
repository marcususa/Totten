import customtkinter as ctk
from tkinter import ttk
from gui.chess_board import ChessBoardWidget
from core.constants import THEME, LAYOUT


class CatalogInitMixin:
    """Mixin class to handle the UI initialization and layout for CatalogAnalysis and MixedAnalysis."""

    def _safe_load_game(self, game_node, category_source=None):
        if category_source and category_source != "catalog":
            return

        # If the analysis textbox already contains text, do not wipe it out
        if hasattr(self, "analysis_textbox") and self.analysis_textbox:
            current_text = self.analysis_textbox.get("1.0", "end").strip()
            if current_text and current_text != "[No game selected...]" and not current_text.startswith("[No"):
                return

        self.load_game(game_node, category_source=category_source)
        import gui.app_state as state
        if hasattr(state, "catalog_state") and isinstance(state.catalog_state, dict):
            state.catalog_state["active_focus"] = game_node
        if hasattr(state, "catalog_state") and state.catalog_state.get("active_focus"):
            self.current_node = state.catalog_state["active_focus"]
            if hasattr(self, "_update_active_boards"):
                self._update_active_boards(self.current_node.board())

        if hasattr(self, "analysis_data") and self.analysis_data:
            self.render_catalog_analysis_moves(self.analysis_data)
        elif hasattr(self, "_last_catalog_analysis_data") and self._last_catalog_analysis_data:
            self.render_catalog_analysis_moves(self._last_catalog_analysis_data)

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

    def _init_analysis_tags(self):
        """Configures CustomTkinter/Tkinter text box tags using central THEME colors and vertical spacing."""
        if not hasattr(self, "analysis_textbox") or not self.analysis_textbox:
            return

        box = self.analysis_textbox
        target_box = getattr(box, "_textbox", getattr(box, "textbox", box))

        target_box.tag_config("red", foreground=THEME.get("eval_red", "#c92a2a"), spacing3=6)
        target_box.tag_config("orange", foreground=THEME.get("eval_orange", "#f59f00"), spacing3=6)
        target_box.tag_config("green", foreground=THEME.get("eval_green", "#2b8a3e"), spacing3=6)
        target_box.tag_config("light_blue", foreground=THEME.get("eval_light_blue", "#1c7ed6"), spacing3=6)
        target_box.tag_config("default", foreground=THEME["text_primary"], spacing3=6)
        target_box.tag_config("comment_tag", foreground=THEME.get("text_secondary", "#94a3b8"), spacing3=6)
        target_box.tag_config("header_tag", foreground=THEME.get("text_secondary", "#94a3b8"), spacing3=6)
        target_box.tag_config("move_tag", foreground=THEME["text_primary"], spacing3=6)
        target_box.tag_config("active_tracker", background=THEME["active_tracker_bg"],
                              foreground=THEME["active_tracker_fg"])

    def render_catalog_analysis_moves(self, analysis_data):
        """Bridges catalog analysis data into self.analysis_rows and uses _sync_analysis_selection to prevent wiping on click."""
        if not hasattr(self, "analysis_textbox"):
            return

        self.analysis_data = analysis_data
        self._last_catalog_analysis_data = analysis_data

        if not hasattr(self, "analysis_rows"):
            self.analysis_rows = {}

        for m_num in sorted(analysis_data.keys()):
            entry = analysis_data[m_num]

            w_txt = entry.get("white_text", entry.get("white", ""))
            b_txt = entry.get("black_text", entry.get("black", ""))
            w_tag = entry.get("white_tag", "default")
            b_tag = entry.get("black_tag", "default")
            w_node = entry.get("white_node")
            b_node = entry.get("black_node")

            self.analysis_rows[m_num] = {
                "white": w_txt,
                "black": b_txt,
                "white_tag": w_tag,
                "black_tag": b_tag,
                "white_node": w_node,
                "black_node": b_node
            }

        if hasattr(self, "_sync_analysis_selection"):
            self._sync_analysis_selection()

    def _update_analysis_buttons_state(self):
        """Updates the visual selection state of all engine and mode buttons."""
        is_running = getattr(self, "_engine_running", False)

        if hasattr(self, "btn_engine_action") and self.btn_engine_action:
            try:
                self.btn_engine_action.configure(
                    fg_color=THEME["btn_hover"] if is_running else THEME["btn_initial"],
                    text="Stop" if is_running else "Engine"
                )
                if not is_running and hasattr(self.btn_engine_action, "_on_leave"):
                    self.btn_engine_action._on_leave(None)
            except Exception:
                pass
        if hasattr(self, "frame_engine_action") and self.frame_engine_action:
            try:
                self.frame_engine_action.configure(border_width=0 if is_running else 1)
            except Exception:
                pass

        selected_mode = getattr(self, "active_engine_mode", getattr(self, "_selected_mode_button", None))
        self._selected_mode_button = selected_mode

        buttons_map = {
            "review": (getattr(self, "btn_review", None), getattr(self, "frame_review", None)),
            "candidates": (getattr(self, "btn_candidates", None), getattr(self, "frame_candidates", None)),
            "standard": (getattr(self, "btn_standard", None), getattr(self, "frame_standard", None))
        }

        for m, (btn, frm) in buttons_map.items():
            is_selected = (selected_mode == m)
            if btn is not None:
                try:
                    btn.configure(
                        fg_color=THEME["btn_hover"] if is_selected else THEME["btn_initial"]
                    )
                    # Force CTkButton to drop internal hover state if deselected under the cursor
                    if not is_selected and hasattr(btn, "_on_leave"):
                        btn._on_leave(None)
                except Exception:
                    pass
            if frm is not None:
                try:
                    frm.configure(border_width=0 if is_selected else 1)
                except Exception:
                    pass

    def init_layout(self):
        import gui.app_state as state

        if hasattr(state, "register_analysis_callback"):
            state.register_analysis_callback(self._safe_load_game)

        if hasattr(state, "catalog_state") and state.catalog_state.get("active_focus"):
            self.current_node = state.catalog_state["active_focus"]
            if hasattr(self, "_update_active_boards"):
                self._update_active_boards(self.current_node.board())

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

        if not hasattr(self, "active_engine_mode"):
            self.active_engine_mode = None

        if not hasattr(self, "_engine_running"):
            self._engine_running = False

        self._selected_mode_button = self.active_engine_mode

        def toggle_engine_state():
            if hasattr(self, "toggle_engine_action"):
                self.toggle_engine_action()
            self._engine_running = getattr(self, "_engine_running", False)
            self._update_analysis_buttons_state()

        def set_analysis_mode(mode):
            current_mode = getattr(self, "active_engine_mode", None)
            if current_mode == mode:
                mode_to_trigger = None
            else:
                mode_to_trigger = mode

            self.active_engine_mode = mode_to_trigger
            self._selected_mode_button = mode_to_trigger
            self._update_analysis_buttons_state()

            if hasattr(self, "trigger_engine_mode"):
                self.trigger_engine_mode(mode_to_trigger)

        def on_btn_enter(btn, mode, frm):
            current_selected = getattr(self, "active_engine_mode", getattr(self, "_selected_mode_button", None))
            if current_selected != mode:
                frm.configure(border_width=0)

        def on_btn_leave(btn, mode, frm):
            current_selected = getattr(self, "active_engine_mode", getattr(self, "_selected_mode_button", None))
            if current_selected != mode:
                frm.configure(border_width=1)

        def init_buttons_ui():
            for widget in self.row_analysis_btns.winfo_children():
                widget.destroy()

            self.row_analysis_btns.pack_configure(side="left", fill="none", expand=False)

            btn_height = 20
            btn_corner = 6
            btn_font = ctk.CTkFont(size=11)
            btn_hover = THEME["btn_hover"]
            btn_initial = THEME["btn_initial"]
            text_color = THEME["text_primary"]
            border_color = THEME.get("border_color", THEME["bg_surface"])

            def create_compact_mode_button(text, mode_key=None, is_action=False):
                frm = ctk.CTkFrame(
                    self.row_analysis_btns, fg_color="transparent", corner_radius=btn_corner,
                    border_width=0 if is_action and self._engine_running else 1, border_color=border_color
                )
                frm.pack(side="left", padx=2, pady=0)

                if is_action:
                    btn = ctk.CTkButton(
                        frm, text="Stop" if self._engine_running else text, width=65, height=btn_height,
                        corner_radius=btn_corner, border_width=0,
                        fg_color=btn_hover if self._engine_running else btn_initial,
                        hover_color=btn_hover, text_color=text_color, font=btn_font,
                        command=toggle_engine_state
                    )
                    self.btn_engine_action = btn
                    self.frame_engine_action = frm
                else:
                    current_selected = getattr(self, "active_engine_mode", getattr(self, "_selected_mode_button", None))
                    is_selected = (current_selected == mode_key)
                    btn = ctk.CTkButton(
                        frm, text=text, width=80, height=btn_height, corner_radius=btn_corner,
                        border_width=0, fg_color=btn_hover if is_selected else btn_initial,
                        hover_color=btn_hover, text_color=text_color, font=btn_font,
                        command=lambda m=mode_key: set_analysis_mode(m)
                    )
                    btn.bind("<Enter>", lambda e, b=btn, m=mode_key, f=frm: on_btn_enter(b, m, f))
                    btn.bind("<Leave>", lambda e, b=btn, m=mode_key, f=frm: on_btn_leave(b, m, f))

                    if mode_key == "review":
                        self.btn_review, self.frame_review = btn, frm
                    elif mode_key == "candidates":
                        self.btn_candidates, self.frame_candidates = btn, frm
                    elif mode_key == "standard":
                        self.btn_standard, self.frame_standard = btn, frm

                btn.pack(fill="both", expand=True)
                return btn

            create_compact_mode_button("Engine", is_action=True)
            create_compact_mode_button("Review", mode_key="review")
            create_compact_mode_button("Candidates", mode_key="candidates")
            create_compact_mode_button("Standard", mode_key="standard")

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

        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=3)
        self.right_analysis_panel.rowconfigure(2, weight=1)
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

        self.pgn_scrollbar = ttk.Scrollbar(
            self.tree_frame,
            orient="vertical"
        )
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
        self.pgn_tree.heading("no", text="No.")
        self.pgn_tree.heading("white", text="White Player", anchor="w")
        self.pgn_tree.heading("black", text="Black Player", anchor="w")
        self.pgn_tree.heading("result", text="Res")

        self.pgn_tree.column("no", width=30, anchor="center")
        self.pgn_tree.column("white", width=135, anchor="w")
        self.pgn_tree.column("black", width=135, anchor="w")
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
                    self.load_game(game)

        self.pgn_tree.bind("<<TreeviewSelect>>", _on_tree_selection)

        self.pgn_scrollbar.configure(command=self.pgn_tree.yview)
        self.pgn_tree.configure(yscrollcommand=self.pgn_scrollbar.set)

        self.pgn_tree.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        self.analysis_container_frame = ctk.CTkFrame(self.right_analysis_panel, fg_color=THEME["bg_panel"],
                                                     corner_radius=8,
                                                     border_width=1,
                                                     border_color=THEME.get("border_color", THEME["bg_surface"]))
        self.analysis_container_frame.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.analysis_header_frame = ctk.CTkFrame(self.analysis_container_frame, fg_color="transparent")
        self.analysis_header_frame.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_analysis_title = ctk.CTkLabel(
            self.analysis_header_frame, text="Analysis", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.get("text_secondary", "#94a3b8")
        )
        self.lbl_analysis_title.pack(side="left", anchor="w")

        self.chunk_btn_frame = ctk.CTkFrame(self.analysis_header_frame, fg_color="transparent")
        self.chunk_btn_frame.pack(side="left", padx=(10, 0))

        btn_height = 20
        btn_corner = 6
        btn_font = ctk.CTkFont(size=10, weight="bold")
        btn_hover = THEME["btn_hover"]
        btn_initial = THEME["btn_initial"]
        text_color = THEME["text_primary"]
        border_color = THEME.get("border_color", THEME["bg_surface"])

        def create_chunk_mode_button(text, command_func):
            frm = ctk.CTkFrame(
                self.chunk_btn_frame, fg_color="transparent", corner_radius=btn_corner,
                border_width=1, border_color=border_color
            )
            frm.pack(side="left", padx=2, pady=0)

            btn = ctk.CTkButton(
                frm, text=text, width=36, height=btn_height, corner_radius=btn_corner,
                border_width=0, fg_color=btn_initial,
                hover_color=btn_hover, text_color=text_color, font=btn_font,
                command=command_func
            )
            btn.bind("<Enter>", lambda e, b=btn, f=frm: b.configure(fg_color=btn_hover))
            btn.bind("<Leave>", lambda e, b=btn, f=frm: b.configure(fg_color=btn_initial))
            btn.pack(fill="both", expand=True)
            return btn

        self.btn_plus_10 = create_chunk_mode_button("+10", lambda: self.load_candidate_extension(10))
        self.btn_plus_20 = create_chunk_mode_button("+20", lambda: self.load_candidate_extension(20))
        self.btn_plus_30 = create_chunk_mode_button("+30", lambda: self.load_candidate_extension(30))

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
        self._init_analysis_tags()
        self.analysis_textbox.pack(fill="both", expand=True, padx=0, pady=0)

        self.pgn_data_panel = ctk.CTkFrame(self.right_analysis_panel, fg_color=THEME["bg_panel"], corner_radius=8,
                                           border_width=1, border_color=THEME.get("border_color", THEME["bg_surface"]))
        self.pgn_data_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.pgn_data_header = ctk.CTkFrame(self.pgn_data_panel, fg_color="transparent")
        self.pgn_data_header.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_pgn_data_title = ctk.CTkLabel(
            self.pgn_data_header, text="Game Details", font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.get("text_secondary", "#94a3b8")
        )
        self.lbl_pgn_data_title.pack(side="left")

        self.btn_close_pgn_data = ctk.CTkButton(
            self.pgn_data_header, text="X", width=26, height=26,
            fg_color="transparent", text_color=THEME.get("text_secondary", "#94a3b8"),
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

        self.bind("<Map>", _bind_keys)
        self.after(100, _bind_keys)