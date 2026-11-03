# catalog_ui_layout.py
import customtkinter as ctk
from core.constants import THEME
import gui.app_state as state

class CatalogUIMixin:
    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.panel = ctk.CTkFrame(self, fg_color=THEME.get("bg_panel"), corner_radius=0)
        self.panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.panel.grid_rowconfigure(0, weight=1)
        self.panel.grid_columnconfigure(0, weight=1)

        self.master_container = ctk.CTkFrame(
            self.panel,
            fg_color=THEME.get("bg_panel"),
            corner_radius=6,
            border_color=THEME.get("border_color"),
            border_width=1
        )
        self.master_container.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.master_container.grid_rowconfigure(2, weight=1)
        self.master_container.grid_columnconfigure(1, weight=1)
        self.master_container.grid_columnconfigure(0, weight=0)

        # 1. Search Toolbar
        self.toolbar_wrapper = ctk.CTkFrame(self.master_container, fg_color="transparent")
        self.toolbar_wrapper.grid(row=0, column=0, columnspan=2, sticky="ew", padx=(12, 2), pady=(10, 4))
        self.toolbar_wrapper.grid_columnconfigure(1, weight=1)

        self.toolbar = ctk.CTkFrame(self.toolbar_wrapper, fg_color="transparent")
        self.toolbar.pack(fill="x", padx=0, pady=0)
        self.toolbar.grid_columnconfigure(0, weight=0)
        self.toolbar.grid_columnconfigure(1, weight=1)
        self.toolbar.grid_columnconfigure(2, weight=0)

        self.entry_filter = ctk.CTkEntry(
            self.toolbar,
            placeholder_text="Search catalog name (e.g., 'Scotch', 'Najdorf')...",
            width=180,
            height=34,
            font=("Arial", 12),
            fg_color=THEME.get("bg_surface"),
            text_color=THEME.get("text_primary"),
            placeholder_text_color=THEME.get("text_secondary"),
            border_color=THEME.get("border_color"),
            border_width=1,
            corner_radius=6
        )
        self.entry_filter.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.entry_filter.bind("<KeyRelease>", lambda e: self.apply_filter())

        self.tag_buttons_frame = ctk.CTkFrame(
            self.toolbar,
            fg_color=THEME.get("bg_surface"),
            corner_radius=6,
            border_color=THEME.get("border_color"),
            border_width=1
        )
        self.tag_buttons_frame.grid(row=0, column=1, sticky="w", padx=0)
        self._rebuild_toolbar_buttons()

        self.lbl_tag_count = ctk.CTkLabel(
            self.toolbar,
            text="",
            font=("Arial", 11, "bold"),
            text_color=THEME.get("text_primary")
        )
        self.lbl_tag_count.grid(row=0, column=2, sticky="e", padx=(10, 12))

        # 2. Dynamic Opening Buttons 2x6 Grid
        self.opening_grid_frame = ctk.CTkFrame(
            self.master_container,
            fg_color="transparent",
            corner_radius=0,
            border_width=0
        )
        self.opening_grid_frame.grid(row=1, column=0, columnspan=2, sticky="ew", padx=6, pady=(0, 6))

        # 3. Sidebar Tree Navigator
        self.tree_sidebar = ctk.CTkScrollableFrame(
            self.master_container,
            fg_color=THEME.get("bg_surface"),
            scrollbar_button_color=THEME.get("btn_initial"),
            scrollbar_button_hover_color=THEME.get("btn_initial"),
            width=250,
            corner_radius=6,
            border_width=0
        )
        self.tree_sidebar.grid(row=2, column=0, sticky="nsew", padx=(6, 3), pady=(0, 10))
        self._build_eco_tree_widget()

        # 4. Main Results Display Area
        self.cards_scroll_frame = ctk.CTkScrollableFrame(
            self.master_container,
            fg_color=THEME.get("bg_surface"),
            scrollbar_button_color=THEME.get("btn_initial"),
            scrollbar_button_hover_color=THEME.get("btn_initial"),
            corner_radius=6,
            border_width=0
        )
        self.cards_scroll_frame.grid(row=2, column=1, sticky="nsew", padx=(3, 6), pady=(0, 10))
        self.cards_scroll_frame.grid_columnconfigure(0, weight=1)

    def _build_eco_tree_widget(self):
        for widget in self.tree_sidebar.winfo_children():
            widget.destroy()

        ctk.CTkLabel(
            self.tree_sidebar,
            text="ECO Tree Directory",
            font=("Arial", 13, "bold"),
            text_color=THEME.get("text_primary")
        ).pack(anchor="w", padx=4, pady=(8, 6))

        if not self.eco_tree_data:
            ctk.CTkLabel(
                self.tree_sidebar,
                text="eco_list.json not found",
                font=("Arial", 11, "italic"),
                text_color=THEME.get("text_secondary")
            ).pack(anchor="w", padx=4, pady=4)
            return

        for opening_name in sorted(self.eco_tree_data.keys()):
            is_expanded = opening_name in self.expanded_tree_openings
            indicator = "▼" if is_expanded else "▶"

            op_btn = ctk.CTkButton(
                self.tree_sidebar,
                text=f"{indicator} {opening_name}",
                anchor="w",
                fg_color="transparent",
                hover_color=THEME.get("btn_hover"),
                text_color=THEME.get("text_primary"),
                font=("Arial", 12, "bold"),
                height=30,
                command=lambda op=opening_name: self.toggle_tree_opening(op)
            )
            op_btn.pack(fill="x", padx=2, pady=1)

            if is_expanded:
                variations = self.eco_tree_data[opening_name]
                for var_name, ecos in variations.items():
                    eco_str = f"[{', '.join(ecos)}]"
                    var_btn = ctk.CTkButton(
                        self.tree_sidebar,
                        text=f"   • {var_name} {eco_str}",
                        anchor="w",
                        fg_color="transparent",
                        hover_color=THEME.get("btn_hover"),
                        text_color=THEME.get("text_secondary"),
                        font=("Arial", 11),
                        height=26,
                        command=lambda op=opening_name: self.select_opening_filter(op)
                    )
                    var_btn.pack(fill="x", padx=4, pady=1)

    def toggle_tree_opening(self, opening_name):
        if opening_name in self.expanded_tree_openings:
            self.expanded_tree_openings.remove(opening_name)
        else:
            self.expanded_tree_openings.add(opening_name)
        self._build_eco_tree_widget()

    def _rebuild_opening_grid(self):
        for widget in self.opening_grid_frame.winfo_children():
            widget.destroy()

        opening_counts = {}
        if not self.aggregated_games_data and self.db_path.exists():
            self.load_catalog_summary_from_duckdb()

        for item in self.aggregated_games_data:
            op_name = item.get("opening", "Unknown Opening").strip()
            opening_counts[op_name] = opening_counts.get(op_name, 0) + item.get("count", 1)

        sorted_by_count = [op for op, _ in sorted(opening_counts.items(), key=lambda x: -x[1])]

        recent_list = state.catalog_state.get("recent_openings", [])
        ordered_openings = []

        for op in recent_list:
            if op in opening_counts and op not in ordered_openings:
                ordered_openings.append(op)

        for op in sorted_by_count:
            if op not in ordered_openings:
                ordered_openings.append(op)

        current_batch = ordered_openings[:self.page_size]

        if self.active_opening_filter is None and current_batch:
            self.active_opening_filter = current_batch[0]

        cols = 6
        for i, op_name in enumerate(current_batch):
            r = i // cols
            c = i % cols
            self.opening_grid_frame.grid_columnconfigure(c, weight=1)

            count = opening_counts.get(op_name, 0)
            is_active = op_name == self.active_opening_filter
            display_label = f"{op_name} ({count})"

            btn = ctk.CTkButton(
                self.opening_grid_frame,
                text=display_label,
                font=("Arial", 10, "bold" if is_active else "normal"),
                fg_color=THEME.get("btn_active") if is_active else THEME.get("btn_initial"),
                hover_color=THEME.get("btn_hover"),
                text_color=THEME.get("text_primary"),
                height=28,
                corner_radius=6,
                command=lambda o=op_name: self.select_opening_filter(o)
            )
            btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)

    def refresh_current_view(self):
        if not self.aggregated_games_data and self.db_path.exists():
            self.load_catalog_summary_from_duckdb()

        self._rebuild_opening_grid()
        self._build_eco_tree_widget()

        for widget in self.cards_scroll_frame.winfo_children():
            widget.destroy()

        grouped_by_opening = {}
        for item_data in self.aggregated_games_data:
            op_name = item_data.get("opening", "Unknown Opening").strip()
            if self.active_opening_filter and op_name != self.active_opening_filter:
                continue
            if op_name not in grouped_by_opening:
                grouped_by_opening[op_name] = []
            grouped_by_opening[op_name].append(item_data)

        if not grouped_by_opening:
            lbl_empty = ctk.CTkLabel(
                self.cards_scroll_frame,
                text="No catalog entries matching the selected opening.",
                font=("Arial", 12, "italic"),
                text_color=THEME.get("text_secondary")
            )
            lbl_empty.pack(anchor="center", pady=20)
            return

        for op_name, items in grouped_by_opening.items():
            total_opening_games = sum(it["count"] for it in items)

            op_frame = ctk.CTkFrame(
                self.cards_scroll_frame,
                fg_color=THEME.get("progress_bg"),
                border_color=THEME.get("border_color"),
                border_width=1,
                corner_radius=8
            )
            op_frame.pack(fill="x", padx=6, pady=6)
            op_frame.grid_columnconfigure(0, weight=1)

            header_inner = ctk.CTkFrame(op_frame, fg_color="transparent", height=38)
            header_inner.pack(fill="x", padx=10, pady=4)
            header_inner.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                header_inner,
                text=op_name,
                anchor="w",
                font=("Arial", 13, "bold"),
                text_color=THEME.get("text_primary")
            ).grid(row=0, column=0, sticky="w")

            ctk.CTkLabel(
                header_inner,
                text=f"{total_opening_games} games",
                font=("Arial", 10, "bold"),
                text_color=THEME.get("text_primary"),
                fg_color=THEME.get("bg_surface"),
                corner_radius=4,
                padx=8,
                pady=2
            ).grid(row=0, column=1, sticky="e")

            content_container = ctk.CTkFrame(op_frame, fg_color="transparent")
            content_container.pack(fill="x", padx=8, pady=(0, 6))
            content_container.grid_columnconfigure(0, weight=1)

            for item_data in items:
                eco = item_data["eco"]
                variation = item_data.get("variation", "").strip() or "Main Line"
                count = item_data["count"]
                group_key = (eco, op_name, variation)
                is_expanded = group_key in self.expanded_groups

                sub_expand = "▼" if is_expanded else "▶"

                row_container = ctk.CTkFrame(
                    content_container,
                    fg_color=THEME.get("bg_surface"),
                    corner_radius=6,
                    height=32
                )
                row_container.pack(fill="x", padx=2, pady=2)
                row_container.grid_columnconfigure(0, weight=1)

                row_btn = ctk.CTkButton(
                    row_container,
                    text=f" {sub_expand} {variation} ({count} games)",
                    anchor="w",
                    fg_color="transparent",
                    hover_color=THEME.get("btn_hover"),
                    text_color=THEME.get("text_primary"),
                    font=("Arial", 11, "bold"),
                    height=30,
                    corner_radius=6
                )
                row_btn.grid(row=0, column=0, sticky="nsew", padx=2)

                eco_chip = ctk.CTkLabel(
                    row_container,
                    text=f"ECO {eco}",
                    font=("Arial", 9),
                    text_color=THEME.get("text_secondary"),
                    fg_color=THEME.get("bg_panel"),
                    corner_radius=3,
                    padx=6,
                    pady=1
                )
                eco_chip.grid(row=0, column=1, padx=8, sticky="e")

                def handle_single_click(e, gk=group_key):
                    if hasattr(self, "_click_timer") and self._click_timer:
                        self.after_cancel(self._click_timer)
                    self._click_timer = self.after(250, lambda: self.toggle_group_expansion(gk))

                def handle_double_click(e, idata=item_data):
                    if hasattr(self, "_click_timer") and self._click_timer:
                        self.after_cancel(self._click_timer)
                        self._click_timer = None
                    self.on_group_click(idata)

                row_btn.bind("<Button-1>", handle_single_click)
                row_btn.bind("<Double-Button-1>", handle_double_click)

                if is_expanded:
                    instances = self.fetch_group_instances_lazily(group_key)
                    item_data["instances"] = instances

                    sub_container = ctk.CTkFrame(
                        content_container,
                        fg_color=THEME.get("progress_bg"),
                        corner_radius=6,
                        border_color=THEME.get("border_color"),
                        border_width=1
                    )
                    sub_container.pack(fill="x", padx=16, pady=(2, 6))
                    sub_container.grid_columnconfigure(0, weight=1)

                    current_limit = self.group_display_limits.get(group_key, 15)
                    visible_instances = instances[:current_limit]

                    for inst in visible_instances:
                        inst_headers = inst.get("headers", {})
                        inst_game = inst.get("game_object")
                        moves_str = self.get_first_n_moves_str(inst_game, n=8)

                        white_p = self.get_header(inst_headers, "White", "Unknown")
                        black_p = self.get_header(inst_headers, "Black", "Unknown")
                        white_e = self.get_header(inst_headers, "WhiteElo", "")
                        black_e = self.get_header(inst_headers, "BlackElo", "")

                        elo_str = f"({white_e} vs {black_e})" if white_e or black_e else ""
                        matchup_text = f"{white_p} {elo_str} vs {black_p}"

                        game_btn = ctk.CTkButton(
                            sub_container,
                            text=f"• {matchup_text} | {moves_str}",
                            anchor="w",
                            fg_color="transparent",
                            hover_color=THEME.get("bg_surface"),
                            text_color=THEME.get("text_secondary"),
                            font=("Arial", 11),
                            height=26,
                            command=lambda idata=item_data, game_inst=inst: self.on_game_click(idata, game_inst)
                        )
                        game_btn.pack(fill="x", padx=6, pady=2)

                    if len(instances) > current_limit:
                        remaining = len(instances) - current_limit

                        def load_more_games(gk=group_key):
                            current = self.group_display_limits.get(gk, 15)
                            self.group_display_limits[gk] = current + 20
                            self.refresh_current_view()

                        more_btn = ctk.CTkButton(
                            sub_container,
                            text=f"↓ Load More ({remaining} remaining)...",
                            anchor="center",
                            fg_color=THEME.get("bg_surface"),
                            hover_color=THEME.get("btn_hover"),
                            text_color=THEME.get("text_primary"),
                            font=("Arial", 11, "bold"),
                            height=26,
                            command=load_more_games
                        )
                        more_btn.pack(fill="x", padx=10, pady=6)

        self.lbl_tag_count.configure(text=f"Opening: {self.active_opening_filter or 'None'}")