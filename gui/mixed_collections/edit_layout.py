import customtkinter as ctk
from tkinter import ttk
from core.constants import THEME
import gui.app_state as state


class CategoryListAdapter:
    """Adapter to mimic get/set and configure behavior for the category list view."""

    def __init__(self, workspace):
        self._workspace = workspace

    def get(self):
        return getattr(self._workspace, "_selected_category", "")

    def set(self, val):
        if hasattr(self._workspace, "_set_category_val"):
            self._workspace._set_category_val(val)

    def configure(self, **kwargs):
        """Intercepts dropdown configuration calls (like values=...) and refreshes the list view."""
        if "values" in kwargs and hasattr(self._workspace, "_refresh_categories_list"):
            self._workspace._refresh_categories_list()


class EditLayoutMixin:
    """Handles UI construction, layout geometry, styling, and tree bindings."""

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.layout("Borderless.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        bg_surface = THEME["bg_surface"]
        text_primary = THEME["text_primary"]
        btn_initial = THEME["btn_initial"]
        bg_panel = THEME["bg_panel"]

        style.configure(
            "Borderless.Treeview",
            background=bg_surface,
            foreground=text_primary,
            fieldbackground=bg_surface,
            rowheight=22,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
            highlightthickness=0
        )
        style.map(
            "Borderless.Treeview",
            background=[("selected", btn_initial), ("focus", bg_surface), ("active", bg_surface)],
            foreground=[("selected", THEME["active_tracker_fg"]), ("focus", text_primary), ("active", text_primary)],
            borderwidth=[("focus", 0), ("active", 0)]
        )
        style.configure(
            "Borderless.Treeview.Heading",
            background=bg_panel,
            foreground=text_primary,
            font=("Arial", 10, "bold"),
            relief="flat",
            borderwidth=0
        )
        style.map(
            "Borderless.Treeview.Heading",
            background=[('active', bg_panel), ('selected', bg_panel)],
            foreground=[('active', text_primary), ('selected', text_primary)]
        )

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)

        # ==========================================================
        # LEFT COLUMN: Split into Top (Table) and Bottom (Online Accounts)
        # ==========================================================
        left_box = ctk.CTkFrame(self, fg_color=THEME["bg_panel"], corner_radius=8, border_color=THEME["border_color"],
                                border_width=1)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)

        left_box.grid_rowconfigure(0, weight=20)
        left_box.grid_rowconfigure(1, weight=0)
        left_box.grid_columnconfigure(0, weight=1)

        # Top Half: Game Table View
        self.tree_frame = ctk.CTkFrame(left_box, fg_color="transparent")
        self.tree_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 2))
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        self.col_tree = ttk.Treeview(
            self.tree_frame,
            columns=("no", "white", "black", "result"),
            show="headings",
            selectmode="browse",
            takefocus=False,
            style="Borderless.Treeview"
        )
        self.col_tree.heading("no", text="No.")
        self.col_tree.heading("white", text="White Player", anchor="w")
        self.col_tree.heading("black", text="Black Player", anchor="w")
        self.col_tree.heading("result", text="Res")

        self.col_tree.column("no", width=35, anchor="center")
        self.col_tree.column("white", width=160, anchor="w")
        self.col_tree.column("black", width=160, anchor="w")
        self.col_tree.column("result", width=45, anchor="center")

        self.col_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.col_tree.bind("<Double-1>", self._on_tree_double_click)

        col_scroll = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.col_tree.yview)
        self.col_tree.configure(yscrollcommand=col_scroll.set)

        self.col_tree.grid(row=0, column=0, sticky="nsew")
        col_scroll.grid(row=0, column=1, sticky="ns", padx=(2, 0))

        # Bottom Half: Online Accounts Panel
        account_box = ctk.CTkFrame(left_box, fg_color=THEME["bg_surface"], corner_radius=6,
                                   border_color=THEME["border_color"], border_width=1)
        account_box.grid(row=1, column=0, sticky="nsew", padx=6, pady=(1, 4))
        account_box.grid_rowconfigure(0, weight=1)
        account_box.grid_columnconfigure(0, weight=1)

        # Main container spanning both columns inside the bottom panel
        accounts_container = ctk.CTkFrame(account_box, fg_color="transparent")
        accounts_container.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        accounts_container.grid_columnconfigure(0, weight=1)

        # Sub-container for Chess.com and Lichess side-by-side columns (expand=False keeps instructions snug below save buttons)
        columns_frame = ctk.CTkFrame(accounts_container, fg_color="transparent")
        columns_frame.pack(fill="x", expand=False)
        columns_frame.grid_columnconfigure((0, 1), weight=1)

        # ------------------- Chess.com Section (Left Column) -------------------
        cc_section = ctk.CTkFrame(columns_frame, fg_color="transparent")
        cc_section.grid(row=0, column=0, sticky="nsew", padx=4, pady=0)
        cc_section.grid_columnconfigure(0, weight=1)

        # Chess.com Header
        ctk.CTkLabel(
            cc_section, text="Chess.com", font=("Arial", 14, "bold"),
            text_color=THEME["text_primary"], anchor="center"
        ).pack(fill="x", pady=(0, 2))

        # Input state frame
        self.cc_input_row = ctk.CTkFrame(cc_section, fg_color="transparent")
        self.cc_input_row.pack(fill="x", pady=0)

        self.entry_cc_username = ctk.CTkEntry(
            self.cc_input_row, placeholder_text="Username...", height=30, width=160, font=("Arial", 12)
        )
        self.entry_cc_username.pack(pady=(0, 6), padx=2)

        ctk.CTkButton(
            self.cc_input_row, text="Save", height=30, width=160, fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"], font=("Arial", 12, "bold"), command=self._save_cc_account
        ).pack(pady=0, padx=2)

        # Active Saved State Frame
        self.cc_active_frame = ctk.CTkFrame(cc_section, fg_color="transparent")

        self.btn_cc_quick = ctk.CTkButton(
            self.cc_active_frame, text="", width=160, fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            height=28, font=("Arial", 11, "bold"), anchor="center", command=self._quick_fetch_cc_last
        )
        self.btn_cc_quick.pack(pady=(0, 2), padx=2)

        # 2-Column Vertical Filter Layout
        cc_filter_container = ctk.CTkFrame(self.cc_active_frame, fg_color="transparent")
        cc_filter_container.pack(anchor="center", padx=(40, 0), pady=0)
        cc_filter_container.grid_columnconfigure(0, weight=1)
        cc_filter_container.grid_columnconfigure(1, weight=1)

        cc_col_left = ctk.CTkFrame(cc_filter_container, fg_color="transparent")
        cc_col_left.grid(row=0, column=0, sticky="n", padx=(0, 4))

        cc_col_right = ctk.CTkFrame(cc_filter_container, fg_color="transparent")
        cc_col_right.grid(row=0, column=1, sticky="n", padx=(4, 0))

        self.cc_box_labels = {}
        for mode in ("Blitz", "Rapid", "Standard"):
            var = ctk.BooleanVar(value=self.cc_filters.get(mode, False))
            chk = ctk.CTkCheckBox(
                cc_col_left,
                text=mode,
                variable=var,
                font=("Arial", 10, "bold"),
                checkbox_width=14,
                checkbox_height=14,
                border_width=1,
                corner_radius=2,
                command=lambda m=mode: self._toggle_cc_filter(m)
            )
            chk.pack(anchor="w", pady=1)
            self.cc_box_labels[mode] = chk

        all_mode = "All"
        all_var = ctk.BooleanVar(value=self.cc_filters.get(all_mode, False))
        all_chk = ctk.CTkCheckBox(
            cc_col_right,
            text=all_mode,
            variable=all_var,
            font=("Arial", 10, "bold"),
            checkbox_width=14,
            checkbox_height=14,
            border_width=1,
            corner_radius=2,
            command=lambda m=all_mode: self._toggle_cc_filter(m)
        )
        all_chk.pack(anchor="w", pady=1)
        self.cc_box_labels[all_mode] = all_chk

        ctk.CTkButton(
            cc_col_right, text="100", width=65, height=24, fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"], font=("Arial", 10, "bold"), command=self._batch_cc_download
        ).pack(anchor="w", pady=(2, 0))

        # Vertical Divider between columns
        ctk.CTkFrame(columns_frame, fg_color=THEME["divider"], width=1).grid(row=0, column=0, sticky="nse", padx=0, pady=2)

        # ------------------- Lichess.org Section (Right Column) -------------------
        lich_section = ctk.CTkFrame(columns_frame, fg_color="transparent")
        lich_section.grid(row=0, column=1, sticky="nsew", padx=4, pady=0)
        lich_section.grid_columnconfigure(0, weight=1)

        # Lichess Header
        ctk.CTkLabel(
            lich_section, text="Lichess.org", font=("Arial", 14, "bold"),
            text_color=THEME["text_primary"], anchor="center"
        ).pack(fill="x", pady=(0, 2))

        # Input state frame
        self.lich_input_row = ctk.CTkFrame(lich_section, fg_color="transparent")
        self.lich_input_row.pack(fill="x", pady=0)

        self.entry_lich_username = ctk.CTkEntry(
            self.lich_input_row, placeholder_text="Username...", height=30, width=160, font=("Arial", 12)
        )
        self.entry_lich_username.pack(pady=(0, 6), padx=2)

        ctk.CTkButton(
            self.lich_input_row, text="Save", height=30, width=160, fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"], font=("Arial", 12, "bold"), command=self._save_lich_account
        ).pack(pady=0, padx=2)

        # Active Saved State Frame
        self.lich_active_frame = ctk.CTkFrame(lich_section, fg_color="transparent")

        self.btn_lich_quick = ctk.CTkButton(
            self.lich_active_frame, text="", width=160, fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            height=28, font=("Arial", 11, "bold"), anchor="center", command=self._quick_fetch_lich_last
        )
        self.btn_lich_quick.pack(pady=(0, 2), padx=2)

        # 2-Column Vertical Filter Layout
        lich_filter_container = ctk.CTkFrame(self.lich_active_frame, fg_color="transparent")
        lich_filter_container.pack(anchor="center", padx=(28, 0), pady=0)
        lich_filter_container.grid_columnconfigure(0, weight=1)
        lich_filter_container.grid_columnconfigure(1, weight=1)

        lich_col_left = ctk.CTkFrame(lich_filter_container, fg_color="transparent")
        lich_col_left.grid(row=0, column=0, sticky="n", padx=(0, 4))

        lich_col_right = ctk.CTkFrame(lich_filter_container, fg_color="transparent")
        lich_col_right.grid(row=0, column=1, sticky="n", padx=(4, 0))

        self.lich_box_labels = {}
        for mode in ("Blitz", "Rapid", "Standard"):
            var = ctk.BooleanVar(value=self.lich_filters.get(mode, False))
            chk = ctk.CTkCheckBox(
                lich_col_left,
                text=mode,
                variable=var,
                font=("Arial", 10, "bold"),
                checkbox_width=14,
                checkbox_height=14,
                border_width=1,
                corner_radius=2,
                command=lambda m=mode: self._toggle_lich_filter(m)
            )
            chk.pack(anchor="w", pady=1)
            self.lich_box_labels[mode] = chk

        all_mode = "All"
        all_var = ctk.BooleanVar(value=self.lich_filters.get(all_mode, False))
        all_chk = ctk.CTkCheckBox(
            lich_col_right,
            text=all_mode,
            variable=all_var,
            font=("Arial", 10, "bold"),
            checkbox_width=14,
            checkbox_height=14,
            border_width=1,
            corner_radius=2,
            command=lambda m=all_mode: self._toggle_lich_filter(m)
        )
        all_chk.pack(anchor="w", pady=1)
        self.lich_box_labels[all_mode] = all_chk

        ctk.CTkButton(
            lich_col_right, text="100", width=65, height=24, fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"], font=("Arial", 10, "bold"), command=self._batch_lich_download
        ).pack(anchor="w", pady=(2, 0))

        # Single unified instruction block positioned snugly right below the Save buttons, once only
        ctk.CTkLabel(
            accounts_container,
            text="1) Type the username and press 'Save'.\n2) Select time controls or 'ALL' and press '100'.\n3) Click Username to just get last game played.",
            font=("Arial", 11, "bold"),
            text_color=THEME["text_secondary"],
            justify="center"
        ).pack(fill="x", pady=(2, 4))

        # ==========================================================
        # RIGHT COLUMN (Kept Standard)
        # ==========================================================
        right_box = ctk.CTkFrame(self, fg_color=THEME["bg_surface"], corner_radius=8,
                                 border_color=THEME["border_color"], border_width=1)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_box.grid_columnconfigure(0, weight=1)

        header_box = ctk.CTkFrame(right_box, fg_color="transparent")
        header_box.pack(fill="x", padx=10, pady=(15, 5))
        ctk.CTkLabel(header_box, text="Mixed Collections", font=("Arial", 14, "bold"),
                     text_color=THEME["text_primary"]).pack(anchor="w")
        ctk.CTkLabel(header_box, text="Select category first.", font=("Arial", 12),
                     text_color=THEME["text_secondary"]).pack(anchor="w")

        self.opt_category = CategoryListAdapter(self)

        def _set_category_val(val):
            self._selected_category = val
            if hasattr(self, "cat_tree"):
                for item_id, cat_name in self.cat_item_map.items():
                    if cat_name == val:
                        self.cat_tree.selection_set(item_id)
                        self.cat_tree.see(item_id)
                        break

        self._set_category_val = _set_category_val

        cat_list_frame = ctk.CTkFrame(right_box, fg_color="transparent")
        cat_list_frame.pack(fill="x", padx=10, pady=5)

        cat_container = ctk.CTkFrame(cat_list_frame, fg_color="transparent")
        cat_container.pack(fill="x", expand=True)
        cat_container.grid_rowconfigure(0, weight=1)
        cat_container.grid_columnconfigure(0, weight=1)

        self.cat_tree = ttk.Treeview(
            cat_container,
            columns=("category",),
            show="headings",
            selectmode="browse",
            takefocus=False,
            style="Borderless.Treeview",
            height=6
        )
        self.cat_tree.heading("category", text="Categories", anchor="w")
        self.cat_tree.column("category", width=220, anchor="w")

        def _on_cat_tree_select(event):
            selection = self.cat_tree.selection()
            if selection:
                item_id = selection[0]
                if item_id in self.cat_item_map:
                    cat_val = self.cat_item_map[item_id]
                    self._selected_category = cat_val
                    self._on_category_changed(cat_val)

        self.cat_tree.bind("<<TreeviewSelect>>", _on_cat_tree_select)

        cat_scroll = ttk.Scrollbar(cat_container, orient="vertical", command=self.cat_tree.yview)
        self.cat_tree.configure(yscrollcommand=cat_scroll.set)

        self.cat_tree.grid(row=0, column=0, sticky="nsew")
        cat_scroll.grid(row=0, column=1, sticky="ns", padx=(2, 0))

        self._refresh_categories_list()

        btn_add_cat = ctk.CTkButton(
            right_box, text="+ Category", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            border_width=0, height=28, font=("Arial", 12), command=self._add_category
        )
        btn_add_cat.pack(fill="x", padx=10, pady=(4, 5))

        move_row = ctk.CTkFrame(right_box, fg_color="transparent")
        move_row.pack(fill="x", padx=10, pady=(5, 2))
        move_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(move_row, text="Up", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
                      border_width=0, height=28, font=("Arial", 12),
                      command=lambda: self._move_category(-1)).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ctk.CTkButton(move_row, text="Down", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
                      border_width=0, height=28, font=("Arial", 12),
                      command=lambda: self._move_category(1)).grid(row=0, column=1, sticky="ew", padx=(2, 0))

        info_row = ctk.CTkFrame(right_box, fg_color="transparent")
        info_row.pack(fill="x", padx=10, pady=(5, 2))
        self.lbl_selected_files = ctk.CTkLabel(info_row, text="No PGN files selected.", font=("Arial", 12),
                                               text_color=THEME["text_secondary"], anchor="w")
        self.lbl_selected_files.pack(side="left", anchor="w")

        action_row = ctk.CTkFrame(right_box, fg_color="transparent")
        action_row.pack(fill="x", padx=10, pady=(2, 10))

        self.btn_undo_pgn = ctk.CTkButton(
            action_row, text="✕", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            border_width=0, width=26, height=30, font=("Arial", 12, "bold"),
            text_color=THEME["text_primary"], command=self._undo_last_pgn
        )
        self.btn_select_pgns = ctk.CTkButton(
            action_row, text="Select PGNs", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            border_width=0, width=95, height=30, font=("Arial", 12), command=self._select_pgn_files
        )
        self.btn_select_pgns.pack(side="left", padx=(0, 3))

        ctk.CTkButton(
            action_row, text="+ Collection", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            border_width=0, width=125, height=30, font=("Arial", 12, "bold"), command=self._create_collection
        ).pack(side="left", padx=(3, 0))

        separator1 = ctk.CTkFrame(right_box, fg_color=THEME["divider"], height=2)
        separator1.pack(fill="x", padx=10, pady=10)

        del_header = ctk.CTkFrame(right_box, fg_color="transparent")
        del_header.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(del_header, text="Use with caution when deleting", font=("Arial", 11, "bold"),
                     text_color=THEME["text_secondary"]).pack(anchor="w")

        del_row = ctk.CTkFrame(right_box, fg_color="transparent")
        del_row.pack(fill="x", padx=10, pady=2)
        del_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            del_row, text="Delete Category", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            border_width=0, height=28, font=("Arial", 12), anchor="center", command=self._delete_category
        ).grid(row=0, column=0, sticky="ew", padx=(0, 2))

        separator2 = ctk.CTkFrame(right_box, fg_color=THEME["divider"], height=2)
        separator2.pack(fill="x", padx=10, pady=10)

        eco_box = ctk.CTkFrame(right_box, fg_color="transparent")
        eco_box.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(eco_box, text="ECO Tag Repair", font=("Arial", 12, "bold"), text_color=THEME["text_primary"]).pack(
            anchor="w")
        ctk.CTkButton(eco_box, text="Scan & Repair ECOs", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
                      border_width=0, height=30, font=("Arial", 12), command=self._repair_eco_tags).pack(fill="x",
                                                                                                         pady=(4, 0))

        engine_box = ctk.CTkFrame(right_box, fg_color="transparent")
        engine_box.pack(fill="x", padx=10, pady=(12, 5))
        ctk.CTkLabel(engine_box, text="Engine Manager", font=("Arial", 12, "bold"),
                     text_color=THEME["text_primary"]).pack(anchor="w")
        eng_row = ctk.CTkFrame(engine_box, fg_color="transparent")
        eng_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(eng_row, text="Browse Engine", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
                      border_width=0, height=30, font=("Arial", 12), command=self._browse_engine).pack(side="left",
                                                                                                       fill="x",
                                                                                                       expand=True,
                                                                                                       padx=(0, 2))
        ctk.CTkButton(eng_row, text="Save Settings", fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
                      border_width=0, height=30, font=("Arial", 12), command=self._save_engine_settings).pack(
            side="right", fill="x",
            expand=True, padx=(2, 0))

    def _refresh_categories_list(self):
        """Populates the category Treeview list to mirror the left column style."""
        if not hasattr(self, "cat_tree"):
            return

        for item in self.cat_tree.get_children():
            self.cat_tree.delete(item)

        self.cat_item_map.clear()
        numbered_cats = self._get_numbered_categories()

        for cat_item in numbered_cats:
            item_id = self.cat_tree.insert("", "end", values=(cat_item,))
            self.cat_item_map[item_id] = cat_item

        if self._selected_category:
            for item_id, cat_name in self.cat_item_map.items():
                if cat_name == self._selected_category:
                    self.cat_tree.selection_set(item_id)
                    self.cat_tree.see(item_id)
                    break
        elif numbered_cats:
            first_id = list(self.cat_item_map.keys())[0]
            self.cat_tree.selection_set(first_id)
            self._selected_category = self.cat_item_map[first_id]

    def _on_tree_select(self, event):
        pass

    def _on_tree_double_click(self, event):
        item_id = self.col_tree.identify_row(event.y)
        if not item_id or not hasattr(self, "tree_map") or item_id not in self.tree_map:
            return

        children = self.col_tree.get_children()
        all_file_games = []
        selected_index = 0

        for idx, child_id in enumerate(children):
            if child_id in self.tree_map:
                game_obj, source_path = self.tree_map[child_id]
                all_file_games.append(game_obj)
                if child_id == item_id:
                    selected_index = idx

        game, source_data = self.tree_map[item_id]

        state.mixed_state["active_index"] = selected_index
        state.mixed_state["active_games"] = all_file_games
        state.mixed_state["active_focus"] = game
        state.mixed_state["current_filename"] = source_data

        top_level = self.winfo_toplevel()
        if hasattr(top_level, "show_workspace"):
            top_level.show_workspace(
                "mixed_analysis",
                initial_games=all_file_games,
                filename=source_data,
                active_focus=game,
                active_index=selected_index
            )
        else:
            print("[DEBUG] Error: top_level window has no show_workspace method.")