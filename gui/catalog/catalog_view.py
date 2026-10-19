from pathlib import Path
import customtkinter as ctk
import chess.pgn

import gui.app_state as state
from gui.sidebar import set_status_message
from .constants import SECTION_TITLES, ECO_THEME_CONFIG
from .catalog_loader import CatalogLoaderMixin
from .catalog_search import CatalogSearchMixin


def on_group_selected(self, chosen_games_list):
    state.catalog_state["active_games"] = chosen_games_list
    if hasattr(state, "show_workspace"):
        state.show_workspace("catalog")


class SearchCatalogWorkspace(ctk.CTkFrame, CatalogLoaderMixin, CatalogSearchMixin):
    def __init__(self, master, app_state=None, *args, **kwargs):
        kwargs.pop("app_state", None)
        kwargs.pop("filename", None)
        kwargs.pop("target_game", None)
        kwargs.pop("active_index", None)
        kwargs.pop("initial_games", None)
        super().__init__(master, fg_color="#172134", corner_radius=0, *args, **kwargs)

        self.app_state = app_state or state

        self.json_path = Path("personal_catalog.json")
        self.pgn_path = Path("personal_catalog.pgn")
        self.db_path = Path("personal_catalog.duckdb")

        self.eco_dir = Path("catalog_eco")
        self.eco_files = {cat: self.eco_dir / f"{cat.lower()}.pgn" for cat in ["A", "B", "C", "D", "E"]}

        self.catalog = {}
        self.aggregated_games_data = []

        self.active_primary_tag = "Variation"
        self.active_extra_columns = set()

        self.sort_column = None
        self.sort_reverse = False

        self.expanded_eco_sections = set()
        self.expanded_groups = set()
        self.group_display_limits = {}  # Tracks pagination limits per group key

        self._build_ui()
        self.check_and_load_catalog()

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.panel = ctk.CTkFrame(self, fg_color="#344268", corner_radius=0)
        self.panel.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.panel.grid_rowconfigure(0, weight=1)
        self.panel.grid_columnconfigure(0, weight=1)

        self.master_container = ctk.CTkFrame(
            self.panel,
            fg_color="#172134",
            corner_radius=6,
            border_color="#445577",
            border_width=1
        )
        self.master_container.grid(row=0, column=0, sticky="nsew", padx=1, pady=1)
        self.master_container.grid_rowconfigure(1, weight=1)
        self.master_container.grid_columnconfigure(0, weight=1)

        self.toolbar_wrapper = ctk.CTkFrame(self.master_container, fg_color="transparent")
        self.toolbar_wrapper.grid(row=0, column=0, sticky="ew", padx=(12, 2), pady=(10, 5))
        self.toolbar_wrapper.grid_columnconfigure(1, weight=1)

        self.toolbar = ctk.CTkFrame(self.toolbar_wrapper, fg_color="transparent")
        self.toolbar.pack(fill="x", padx=0, pady=0)
        self.toolbar.grid_columnconfigure(0, weight=0)
        self.toolbar.grid_columnconfigure(1, weight=1)
        self.toolbar.grid_columnconfigure(2, weight=0)

        self.entry_filter = ctk.CTkEntry(
            self.toolbar,
            placeholder_text="Search catalog...",
            width=160,
            height=30,
            font=("Arial", 12),
            fg_color="#1e293b",
            text_color="#f8fafc",
            placeholder_text_color="#94a3b8",
            border_color="#445577",
            border_width=1,
            corner_radius=6
        )
        self.entry_filter.grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.entry_filter.bind("<KeyRelease>", lambda e: self.apply_filter())

        self.tag_buttons_frame = ctk.CTkFrame(
            self.toolbar,
            fg_color="#1e293b",
            corner_radius=6,
            border_color="#334155",
            border_width=1
        )
        self.tag_buttons_frame.grid(row=0, column=1, sticky="w", padx=0)

        self._rebuild_toolbar_buttons()

        self.lbl_tag_count = ctk.CTkLabel(
            self.toolbar,
            text="",
            font=("Arial", 11, "bold"),
            text_color="#93c5fd"
        )
        self.lbl_tag_count.grid(row=0, column=2, sticky="e", padx=(10, 12))

        # Increased bottom padding to prevent border clipping
        self.cards_scroll_frame = ctk.CTkScrollableFrame(
            self.master_container,
            fg_color="#1e293b",
            corner_radius=6,
            border_width=0
        )
        self.cards_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 14))
        self.cards_scroll_frame.grid_columnconfigure(0, weight=1)

    def refresh_current_view(self):
        for widget in self.cards_scroll_frame.winfo_children():
            widget.destroy()

        if self.active_primary_tag:
            active_display_tag = self.active_primary_tag
        elif self.active_extra_columns:
            active_display_tag = ", ".join(sorted(self.active_extra_columns))
        else:
            active_display_tag = "Variation"

        sorted_data = sorted(
            self.aggregated_games_data,
            key=lambda x: (x["eco"][0].upper() if x["eco"] else 'A', -x["count"], x["eco"], x["opening"],
                           x["variation"])
        )

        query = self.entry_filter.get().strip().lower()

        eco_sections = {"A": [], "B": [], "C": [], "D": [], "E": []}
        for item_data in sorted_data:
            eco = item_data["eco"]
            eco_base = eco[0].upper() if eco else "A"
            if eco_base in eco_sections:
                eco_sections[eco_base].append(item_data)
            else:
                eco_sections["A"].append(item_data)

        for cat in ["A", "B", "C", "D", "E"]:
            items = eco_sections[cat]
            theme = ECO_THEME_CONFIG[cat]
            is_eco_expanded = cat in self.expanded_eco_sections

            filtered_items = []
            for item_data in items:
                instances = item_data["instances"]
                if not query:
                    filtered_items.append((item_data, instances))
                else:
                    matching_instances = []
                    group_str = f"{item_data['eco']} {item_data['opening']} {item_data['variation']}".lower()

                    for inst in instances:
                        headers = inst.get("headers", {})
                        white = self.get_header(headers, "White", "").lower()
                        black = self.get_header(headers, "Black", "").lower()

                        if query in white or query in black or query in group_str:
                            matching_instances.append(inst)

                    if matching_instances:
                        item_copy = item_data.copy()
                        item_copy["instances"] = matching_instances
                        item_copy["count"] = len(matching_instances)
                        filtered_items.append((item_copy, matching_instances))

            total_filtered_in_section = sum(it["count"] for it, _ in filtered_items)
            if total_filtered_in_section == 0 and query:
                continue

            # --- 1. MODERN ECO SECTION CARD FRAME ---
            group_frame = ctk.CTkFrame(
                self.cards_scroll_frame,
                fg_color="#10172a",
                border_color=theme["border"],
                border_width=1,
                corner_radius=8
            )
            group_frame.pack(fill="x", padx=6, pady=6)
            group_frame.grid_columnconfigure(0, weight=1)

            header_inner = ctk.CTkFrame(group_frame, fg_color="transparent", height=40)
            header_inner.pack(fill="x", padx=8, pady=6)
            header_inner.grid_columnconfigure(0, weight=1)

            expand_indicator = "▼" if is_eco_expanded else "▶"
            header_btn = ctk.CTkButton(
                header_inner,
                text=f"{expand_indicator}  ECO {cat} — {SECTION_TITLES[cat]}",
                anchor="w",
                fg_color="transparent",
                hover_color="#1e293b",
                text_color=theme["fg"],
                font=("Arial", 12, "bold"),
                height=32,
                command=lambda c=cat: self.toggle_eco_section(c)
            )
            header_btn.grid(row=0, column=0, sticky="ew")

            count_badge = ctk.CTkLabel(
                header_inner,
                text=f"{total_filtered_in_section} games",
                font=("Arial", 10, "bold"),
                text_color="#93c5fd",
                fg_color="#1e3a8a",
                corner_radius=4,
                padx=8,
                pady=2
            )
            count_badge.grid(row=0, column=1, sticky="e", padx=4)

            # --- 2. EXPANDED CONTENT CONTAINER ---
            if is_eco_expanded:
                content_container = ctk.CTkFrame(group_frame, fg_color="transparent")
                content_container.pack(fill="x", padx=8, pady=(0, 8))
                content_container.grid_columnconfigure(0, weight=1)

                if not filtered_items:
                    lbl_empty = ctk.CTkLabel(
                        content_container,
                        text="No games found in this section.",
                        font=("Arial", 11, "italic"),
                        text_color="#64748b"
                    )
                    lbl_empty.pack(anchor="w", padx=8, pady=6)

                for item_data, instances in filtered_items:
                    eco = item_data["eco"]
                    opening = item_data["opening"]
                    variation = item_data["variation"]
                    count = item_data["count"]
                    group_key = (eco, opening, variation)
                    is_expanded = group_key in self.expanded_groups

                    sub_expand = "▼" if is_expanded else "▶"
                    variation_display = f" — {variation}" if variation else ""
                    row_btn = ctk.CTkButton(
                        content_container,
                        text=f"  {sub_expand}  {eco}   |   {opening} ({count} games){variation_display}",
                        anchor="w",
                        fg_color="#1e293b",
                        hover_color="#334155",
                        text_color="#f8fafc",
                        font=("Arial", 11, "bold"),
                        height=32,
                        corner_radius=6
                    )
                    row_btn.pack(fill="x", padx=2, pady=3)

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

                    # --- 3. INDIVIDUAL GAME INSTANCES (WITH PAGINATION) ---
                    if is_expanded and instances:
                        sub_container = ctk.CTkFrame(
                            content_container,
                            fg_color="#0f172a",
                            corner_radius=6,
                            border_color="#334155",
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
                            matchup_text = f"{white_p} {elo_str}  vs  {black_p}"

                            # Extract active extra tags (like Round, Event, etc.) to display
                            extra_info_parts = []
                            active_tags = set(self.active_extra_columns)
                            if self.active_primary_tag:
                                active_tags.add(self.active_primary_tag)

                            for tag in sorted(active_tags):
                                if tag not in ["Players", "Elo", "Variation"]:
                                    val = self.get_header(inst_headers, tag, "")
                                    if val and val != "Unknown":
                                        extra_info_parts.append(f"{tag}: {val}")

                            extra_str = f"[{' | '.join(extra_info_parts)}]  " if extra_info_parts else ""

                            game_btn = ctk.CTkButton(
                                sub_container,
                                text=f"•  {extra_str}{matchup_text}    |    {moves_str}",
                                anchor="w",
                                fg_color="transparent",
                                hover_color="#1e293b",
                                text_color="#cbd5e1",
                                font=("Arial", 11),
                                height=28,
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
                                fg_color="#1e293b",
                                hover_color="#334155",
                                text_color="#93c5fd",
                                font=("Arial", 11, "bold"),
                                height=28,
                                command=load_more_games
                            )
                            more_btn.pack(fill="x", padx=10, pady=6)

        self.lbl_tag_count.configure(text=f"Active View: {active_display_tag}")

    def toggle_eco_section(self, cat):
        if cat in self.expanded_eco_sections:
            self.expanded_eco_sections.remove(cat)
        else:
            self.expanded_eco_sections = {cat}
            self.lazy_load_eco_section(cat)
        self.refresh_current_view()

    def toggle_group_expansion(self, group_key):
        if group_key in self.expanded_groups:
            self.expanded_groups.remove(group_key)
        else:
            self.expanded_groups.add(group_key)
        self.refresh_current_view()

    def _navigate_to_analysis(self):
        sw_func = None
        if hasattr(state, "show_workspace") and callable(state.show_workspace):
            sw_func = state.show_workspace
        elif hasattr(self.winfo_toplevel(), "show_workspace") and callable(
                getattr(self.winfo_toplevel(), "show_workspace")):
            sw_func = self.winfo_toplevel().show_workspace
        elif hasattr(self.master, "show_workspace") and callable(getattr(self.master, "show_workspace")):
            sw_func = self.master.show_workspace

        if sw_func:
            for name in ["catalog_analysis", "analysis", "catalog"]:
                try:
                    sw_func(name)
                    return True
                except Exception:
                    continue
        return False

    def on_game_click(self, item_data, game_data):
        if not item_data or not game_data:
            return

        instances = item_data.get("instances", [])
        eco = item_data.get("eco", "A00")

        headers = game_data.get("headers", {})
        target_white = self.get_header(headers, "White", "").strip()
        target_black = self.get_header(headers, "Black", "").strip()

        set_status_message(f"Loading analysis: {target_white} vs {target_black} ({len(instances)} games in group)")

        game_list = []
        target_game_obj = None

        for inst in instances:
            g_obj = inst.get("game_object")
            inst_headers = inst.get("headers", {})
            w = self.get_header(inst_headers, "White", "").strip()
            b = self.get_header(inst_headers, "Black", "").strip()

            if not g_obj:
                cat = eco[0].upper() if eco else "A"
                eco_pgn = self.eco_files.get(cat)
                candidate_paths = []
                if eco_pgn and eco_pgn.exists():
                    candidate_paths.append(eco_pgn)
                if self.pgn_path.exists() and self.pgn_path not in candidate_paths:
                    candidate_paths.append(self.pgn_path)

                for src_path in candidate_paths:
                    if g_obj:
                        break
                    try:
                        with open(src_path, "r", encoding="utf-8", errors="replace") as f:
                            while True:
                                parsed = chess.pgn.read_game(f)
                                if parsed is None:
                                    break
                                p_w = parsed.headers.get("White", "").strip()
                                p_b = parsed.headers.get("Black", "").strip()
                                if p_w.lower() == w.lower() and p_b.lower() == b.lower():
                                    g_obj = parsed
                                    inst["game_object"] = parsed
                                    break
                    except Exception:
                        pass

            if g_obj:
                game_list.append(g_obj)
                if inst == game_data or g_obj == game_data.get("game_object"):
                    target_game_obj = g_obj

        if not target_game_obj and game_list:
            target_game_obj = game_list[0]

        active_index = 0
        if target_game_obj in game_list:
            active_index = game_list.index(target_game_obj)
        else:
            for idx, g in enumerate(game_list):
                g_headers = g.headers if hasattr(g, "headers") else {}
                if (g_headers.get("White", "").strip().lower() == target_white.lower() and
                        g_headers.get("Black", "").strip().lower() == target_black.lower()):
                    active_index = idx
                    break

        state.catalog_state["active_games"] = game_list
        state.catalog_state["active_focus"] = target_game_obj
        state.catalog_state["active_index"] = active_index

        sw_func = None
        if hasattr(state, "show_workspace") and callable(state.show_workspace):
            sw_func = state.show_workspace
        elif hasattr(self.winfo_toplevel(), "show_workspace") and callable(
                getattr(self.winfo_toplevel(), "show_workspace")):
            sw_func = self.winfo_toplevel().show_workspace
        elif hasattr(self.master, "show_workspace") and callable(getattr(self.master, "show_workspace")):
            sw_func = self.master.show_workspace

        if sw_func:
            try:
                sw_func("analysis", initial_games=game_list, target_game=target_game_obj, active_index=active_index)
                return
            except TypeError:
                try:
                    sw_func("analysis")
                    return
                except Exception:
                    pass
            except Exception:
                pass

        self._navigate_to_analysis()

    def on_group_click(self, item_data):
        if not item_data:
            return
        instances = item_data.get("instances", [])
        if not instances:
            return
        self.on_game_click(item_data, instances[0])