import customtkinter as ctk
import io
import chess.pgn
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
        self.master_container.grid_columnconfigure(0, weight=1)

        # 1. Search Toolbar, Search Button, & ECO Quick Filters (A, B, C, D, E)
        self.toolbar_wrapper = ctk.CTkFrame(self.master_container, fg_color="transparent")
        self.toolbar_wrapper.grid(row=0, column=0, sticky="ew", padx=(12, 12), pady=(10, 4))
        self.toolbar_wrapper.grid_columnconfigure(0, weight=1)

        self.toolbar = ctk.CTkFrame(self.toolbar_wrapper, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew")
        self.toolbar.grid_columnconfigure(3, weight=1)

        self.entry_filter = ctk.CTkEntry(
            self.toolbar,
            placeholder_text="Type search words...",
            width=220,
            height=34,
            font=("Arial", 12),
            fg_color=THEME.get("bg_surface"),
            text_color=THEME.get("text_primary"),
            placeholder_text_color=THEME.get("text_secondary"),
            border_color=THEME.get("border_color"),
            border_width=1,
            corner_radius=6
        )
        self.entry_filter.grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.entry_filter.bind("<Return>", self.apply_filter)

        # Dedicated Search Button
        self.btn_search = ctk.CTkButton(
            self.toolbar,
            text="Search",
            width=70,
            height=32,
            font=("Arial", 11, "bold"),
            fg_color=THEME.get("btn_initial"),
            hover_color=THEME.get("btn_hover"),
            text_color=THEME.get("text_primary"),
            corner_radius=6,
            command=self.apply_filter
        )
        self.btn_search.grid(row=0, column=1, sticky="w", padx=(0, 10))

        # ECO Quick-Filter Button Group (A, B, C, D, E)
        self.eco_filter_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        self.eco_filter_frame.grid(row=0, column=2, sticky="w", padx=5)

        ctk.CTkLabel(
            self.eco_filter_frame,
            text="ECO:",
            font=("Arial", 11, "bold"),
            text_color=THEME.get("text_secondary")
        ).pack(side="left", padx=(0, 4))

        for eco_letter in ["A", "B", "C", "D", "E"]:
            btn_color = THEME.get("btn_active") if getattr(self, "active_eco_letter", None) == eco_letter else THEME.get("btn_initial")
            eco_btn = ctk.CTkButton(
                self.eco_filter_frame,
                text=eco_letter,
                width=32,
                height=28,
                font=("Arial", 11, "bold"),
                fg_color=btn_color,
                hover_color=THEME.get("btn_hover"),
                text_color=THEME.get("text_primary"),
                corner_radius=4,
                command=lambda l=eco_letter: self.filter_by_eco_letter(l)
            )
            eco_btn.pack(side="left", padx=2)

        self.lbl_tag_count = ctk.CTkLabel(
            self.toolbar,
            text="",
            font=("Arial", 11, "bold"),
            text_color=THEME.get("text_primary")
        )
        self.lbl_tag_count.grid(row=0, column=3, sticky="e", padx=(10, 3))

        # 2. Dynamic Opening Buttons Grid
        self.opening_grid_frame = ctk.CTkFrame(
            self.master_container,
            fg_color="transparent",
            corner_radius=0,
            border_width=0
        )
        self.opening_grid_frame.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 6))

        # 3. Main Results Display Area (Full Width)
        self.cards_scroll_frame = ctk.CTkScrollableFrame(
            self.master_container,
            fg_color=THEME.get("bg_surface"),
            scrollbar_button_color=THEME.get("btn_initial"),
            scrollbar_button_hover_color=THEME.get("btn_initial"),
            corner_radius=6,
            border_width=0
        )
        self.cards_scroll_frame.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 10))
        self.cards_scroll_frame.grid_columnconfigure(0, weight=1)

    def _rebuild_eco_filter_buttons(self):
        for widget in self.eco_filter_frame.winfo_children():
            if isinstance(widget, ctk.CTkButton):
                eco_letter = widget.cget("text")
                is_active = (getattr(self, "active_eco_letter", None) == eco_letter)
                widget.configure(
                    fg_color=THEME.get("btn_active") if is_active else THEME.get("btn_initial")
                )

    def _rebuild_opening_grid(self):
        for widget in self.opening_grid_frame.winfo_children():
            widget.destroy()

        opening_counts = {}
        if not self.aggregated_games_data and self.db_path.exists():
            self.load_catalog_summary_from_duckdb()

        active_letter = getattr(self, "active_eco_letter", None)
        is_ae = getattr(self, "is_ae_search", False)

        for item in self.aggregated_games_data:
            eco = item.get("eco", "A00").upper()
            if active_letter and not eco.startswith(active_letter.upper()):
                continue
            elif is_ae and not any(eco.startswith(l) for l in ["A", "B", "C", "D", "E"]):
                continue

            op_name = item.get("opening", "Unknown Opening").strip()
            opening_counts[op_name] = opening_counts.get(op_name, 0) + len(item.get("instances", []))

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

        if self.active_opening_filter not in current_batch:
            self.active_opening_filter = current_batch[0] if current_batch else None

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
                font=("Arial", 11, "bold"),
                fg_color=THEME.get("btn_active") if is_active else THEME.get("btn_initial"),
                hover_color=THEME.get("btn_hover"),
                text_color=THEME.get("text_primary"),
                height=30,
                corner_radius=6,
                command=lambda o=op_name: self.select_opening_filter(o)
            )
            btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)

    def refresh_current_view(self):
        if not self.aggregated_games_data and self.db_path.exists():
            self.load_catalog_summary_from_duckdb()

        self._rebuild_opening_grid()
        self._rebuild_eco_filter_buttons()

        for widget in self.cards_scroll_frame.winfo_children():
            widget.destroy()

        query_str = ""
        if hasattr(self, "entry_filter") and self.entry_filter is not None:
            try:
                query_str = self.entry_filter.get().strip()
            except Exception:
                pass

        active_letter = getattr(self, "active_eco_letter", None)
        is_ae = getattr(self, "is_ae_search", False)

        grouped_by_opening = {}

        for item_data in self.aggregated_games_data:
            eco = item_data.get("eco", "A00").upper()
            if active_letter and not eco.startswith(active_letter.upper()):
                continue
            elif is_ae and not any(eco.startswith(l) for l in ["A", "B", "C", "D", "E"]):
                continue

            op_name = item_data.get("opening", "Unknown Opening").strip()

            if self.active_opening_filter and op_name != self.active_opening_filter:
                continue

            if op_name not in grouped_by_opening:
                grouped_by_opening[op_name] = []
            grouped_by_opening[op_name].append(item_data)

        if not grouped_by_opening:
            empty_msg = f"No catalog entries found matching '{query_str}'." if query_str else "No catalog entries matching the selected criteria."
            lbl_empty = ctk.CTkLabel(
                self.cards_scroll_frame,
                text=empty_msg,
                font=("Arial", 13, "bold"),
                text_color=THEME.get("text_primary")
            )
            lbl_empty.pack(anchor="center", pady=20)
            self.lbl_tag_count.configure(text=f"Opening: {self.active_opening_filter or 'All'}")
            return

        for op_name, items in grouped_by_opening.items():
            total_opening_games = sum(len(it.get("instances", [])) for it in items)

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
                font=("Arial", 11, "bold"),
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
                instances = item_data.get("instances", [])

                if not instances:
                    continue

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
                    text=f" {sub_expand} {variation} ({len(instances)} games)",
                    anchor="w",
                    fg_color="transparent",
                    hover_color=THEME.get("btn_hover"),
                    text_color=THEME.get("text_primary"),
                    font=("Arial", 12, "bold"),
                    height=30,
                    corner_radius=6
                )
                row_btn.grid(row=0, column=0, sticky="nsew", padx=2)

                eco_chip = ctk.CTkLabel(
                    row_container,
                    text=f"ECO {eco}",
                    font=("Arial", 11, "bold"),
                    text_color=THEME.get("text_primary"),
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
                        white_p = inst_headers.get("White", "Unknown")
                        black_p = inst_headers.get("Black", "Unknown")
                        white_e = inst_headers.get("WhiteElo", "")
                        black_e = inst_headers.get("BlackElo", "")

                        elo_str = f"({white_e} vs {black_e})" if white_e or black_e else ""
                        matchup_text = f"{white_p} {elo_str} vs {black_p}"

                        game_btn = ctk.CTkButton(
                            sub_container,
                            text=f"• {matchup_text}",
                            anchor="w",
                            fg_color="transparent",
                            hover_color=THEME.get("bg_surface"),
                            text_color=THEME.get("text_primary"),
                            font=("Arial", 11, "bold"),
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

                self.lbl_tag_count.configure(text=f"Opening: {self.active_opening_filter or 'All'}")