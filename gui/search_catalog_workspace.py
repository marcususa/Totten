import json
import os
from pathlib import Path
from tkinter import messagebox, filedialog
from .splash import LoadingOverlay
import threading
import random
import customtkinter as ctk
import chess.pgn
import duckdb

import gui.app_state as state
import chess
from gui.statusbar import set_status_message

STANDARD_TAG_BANK = {
    "essential": {"ECO", "Opening", "Variation", "Games"},
    "common": {
        "White", "Black", "Result", "Event", "Site", "Date", "Round",
        "WhiteElo", "BlackElo", "TimeControl", "Termination", "Annotator", "PlyCount"
    }
}


class SearchCatalogWorkspace(ctk.CTkFrame):
    def __init__(self, master, app_state=None):
        super().__init__(master, fg_color="#344268", corner_radius=0)
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

        self.session_representative_cache = {}
        self.expanded_eco_sections = set()
        self.expanded_groups = set()

        self._build_ui()
        self.after(100, self.check_and_load_catalog)

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

        self.tag_buttons_frame = ctk.CTkFrame(self.toolbar, fg_color="#1e293b", corner_radius=6, border_color="#334155",
                                              border_width=1)
        self.tag_buttons_frame.grid(row=0, column=1, sticky="w", padx=0)

        for tag in ["Players", "Elo", "Event", "Variation", "All"]:
            if tag == "All":
                btn_width = 50
            elif tag == "Elo":
                btn_width = 65
            elif tag == "Event":
                btn_width = 65
            else:
                btn_width = 80

            is_active = (tag == self.active_primary_tag)
            btn_fg = "#2e4a8c" if is_active else "transparent"
            btn_hover = "#3b5998" if is_active else "#2b3856"
            text_color = "#ffffff" if is_active else "#cbd5e1"

            if tag == "All":
                btn = ctk.CTkButton(
                    self.tag_buttons_frame,
                    text=tag,
                    width=btn_width,
                    height=26,
                    font=("Arial", 11, "bold"),
                    fg_color=btn_fg,
                    text_color=text_color,
                    hover_color=btn_hover,
                    corner_radius=4,
                    command=self.open_all_tags_dialog
                )
            else:
                btn = ctk.CTkButton(
                    self.tag_buttons_frame,
                    text=tag,
                    width=btn_width,
                    height=26,
                    font=("Arial", 11, "bold"),
                    fg_color=btn_fg,
                    text_color=text_color,
                    hover_color=btn_hover,
                    corner_radius=4,
                    command=lambda t=tag: self.select_primary_tag(t)
                )
            btn.pack(side="left", padx=2, pady=2)

        self.lbl_tag_count = ctk.CTkLabel(
            self.toolbar,
            text="",
            font=("Arial", 11, "bold"),
            text_color="#93c5fd"
        )
        self.lbl_tag_count.grid(row=0, column=2, sticky="e", padx=(10, 12))

        self.cards_scroll_frame = ctk.CTkScrollableFrame(
            self.master_container,
            fg_color="#1e293b",
            corner_radius=6,
            border_width=0
        )
        self.cards_scroll_frame.grid(row=1, column=0, sticky="nsew", padx=1, pady=(0, 1))
        self.cards_scroll_frame.grid_columnconfigure(0, weight=1)

    def get_header(self, headers, key, default="Unknown"):
        if not headers:
            return default
        if key in headers:
            return headers[key]
        lower_key = key.lower()
        for k, v in headers.items():
            if k.lower() == lower_key:
                return v
        return default

    def get_first_n_moves_str(self, game_obj, n=10):
        if not game_obj:
            return ""
        board = game_obj.board()
        moves_san = []
        for node in game_obj.mainline():
            if len(moves_san) >= n * 2:
                break
            moves_san.append(board.san(node.move))
            board.push(node.move)

        formatted_moves = []
        for i in range(0, len(moves_san), 2):
            move_num = (i // 2) + 1
            white_move = moves_san[i]
            black_move = moves_san[i + 1] if i + 1 < len(moves_san) else ""
            if black_move:
                formatted_moves.append(f"{move_num}. {white_move} {black_move}")
            else:
                formatted_moves.append(f"{move_num}. {white_move}")
        return "  ".join(formatted_moves)

    def open_all_tags_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("All Available Tags")
        dialog.geometry("340x420")
        dialog.transient(self)
        dialog.grab_set()

        dialog.configure(fg_color="#172134")
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)

        frame = ctk.CTkFrame(dialog, fg_color="#172134", corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        scrollable_frame = ctk.CTkScrollableFrame(
            frame,
            fg_color="#1e293b",
            label_fg_color="#1e293b",
            border_color="#445577",
            border_width=1
        )
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        all_possible_tags = sorted(list(STANDARD_TAG_BANK["common"] | STANDARD_TAG_BANK["essential"]))

        for tag in all_possible_tags:
            if tag in ("ECO", "Opening", "Games"):
                continue

            var = ctk.BooleanVar(value=tag in self.active_extra_columns)
            chk = ctk.CTkCheckBox(
                scrollable_frame,
                text=tag,
                variable=var,
                font=("Arial", 12),
                command=lambda t=tag, v=var: self.toggle_tag_from_dialog(t, v.get()),
                text_color="#f8fafc",
                fg_color="#2e4a8c",
                hover_color="#3b5998",
                checkmark_color="#ffffff",
                border_color="#2e4a8c",
                border_width=2
            )

            # Dynamic hover color adjustment based on check state
            def on_enter(e, c=chk, v=var):
                c.configure(hover_color="#3b5998" if v.get() else "#2e4a8c")

            chk.bind("<Enter>", on_enter)
            chk.pack(anchor="w", pady=6, padx=8)

    def toggle_tag_from_dialog(self, tag, is_checked):
        if is_checked:
            self.active_extra_columns.add(tag)
        else:
            if tag in self.active_extra_columns:
                self.active_extra_columns.remove(tag)
        self.active_primary_tag = None
        self._rebuild_toolbar_buttons()
        self.refresh_current_view()

    def select_primary_tag(self, tag):
        self.active_primary_tag = tag
        self.active_extra_columns.clear()
        self._rebuild_toolbar_buttons()
        self.refresh_current_view()

    def _rebuild_toolbar_buttons(self):
        for widget in self.tag_buttons_frame.winfo_children():
            widget.destroy()

        for tag in ["Players", "Elo", "Event", "Variation", "All"]:
            if tag == "All":
                btn_width = 50
            elif tag == "Elo":
                btn_width = 65
            elif tag == "Event":
                btn_width = 65
            else:
                btn_width = 80

            is_active = (tag == self.active_primary_tag) and not self.active_extra_columns
            btn_fg = "#2e4a8c" if is_active else "transparent"
            btn_hover = "#3b5998" if is_active else "#2b3856"
            text_color = "#ffffff" if is_active else "#cbd5e1"

            if tag == "All":
                btn = ctk.CTkButton(
                    self.tag_buttons_frame,
                    text=tag,
                    width=btn_width,
                    height=26,
                    font=("Arial", 11, "bold"),
                    fg_color=btn_fg,
                    text_color=text_color,
                    hover_color=btn_hover,
                    corner_radius=4,
                    command=self.open_all_tags_dialog
                )
            else:
                btn = ctk.CTkButton(
                    self.tag_buttons_frame,
                    text=tag,
                    width=btn_width,
                    height=26,
                    font=("Arial", 11, "bold"),
                    fg_color=btn_fg,
                    text_color=text_color,
                    hover_color=btn_hover,
                    corner_radius=4,
                    command=lambda t=tag: self.select_primary_tag(t)
                )
            btn.pack(side="left", padx=2, pady=2)

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

        section_titles = {
            "A": "1. c4 / Nf3",
            "B": "1. e4 c5 / e6",
            "C": "1. e4 e5",
            "D": "1. d4 d5",
            "E": "1. d4 Nf6"
        }

        eco_theme_config = {
            "A": {"bg": "#2A1F14", "fg": "#FF9F33", "border": "#FF8800", "hover": "#A6580B"},
            "B": {"bg": "#1E3324", "fg": "#52B878", "border": "#2D6640", "hover": "#2D6640"},
            "C": {"bg": "#144075", "fg": "#5196E0", "border": "#285282", "hover": "#285282"},
            "D": {"bg": "#421C1C", "fg": "#E05151", "border": "#822828", "hover": "#822828"},
            "E": {"bg": "#331C42", "fg": "#B051E0", "border": "#622882", "hover": "#622882"}
        }

        for cat in ["A", "B", "C", "D", "E"]:
            items = eco_sections[cat]
            if not items:
                continue

            theme = eco_theme_config[cat]
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

            if not filtered_items:
                continue

            unique_openings = sorted(list(
                {item["opening"] for item, _ in filtered_items if item["opening"] and item["opening"] != "Unknown"}))
            openings_str = ", ".join(unique_openings) if unique_openings else ""

            group_frame = ctk.CTkFrame(
                self.cards_scroll_frame,
                fg_color="#172134",
                border_color=theme["border"],
                border_width=2,
                corner_radius=8
            )
            group_frame.pack(fill="x", padx=1, pady=4)
            group_frame.grid_columnconfigure(0, weight=1)

            total_filtered_in_section = sum(it["count"] for it, _ in filtered_items)
            expand_indicator = "▼  " if is_eco_expanded else "▶  "
            base_header_text = f"{expand_indicator}ECO {cat} {section_titles[cat]} ({total_filtered_in_section} matches)"

            full_header_text = f"{base_header_text}"
            if openings_str:
                full_header_text += f"   {openings_str}"

            header_btn = ctk.CTkButton(
                group_frame,
                text=full_header_text,
                anchor="w",
                fg_color=theme["bg"],
                hover_color=theme["hover"],
                text_color=theme["fg"],
                font=("Arial", 12, "bold"),
                height=36,
                corner_radius=4,
                command=lambda c=cat: self.toggle_eco_section(c)
            )
            header_btn.pack(fill="x", padx=4, pady=4)

            if is_eco_expanded:
                content_container = ctk.CTkFrame(group_frame, fg_color="transparent")
                content_container.pack(fill="x", padx=4, pady=(0, 4))
                content_container.grid_columnconfigure(0, weight=1)

                for item_data, instances in filtered_items:
                    eco = item_data["eco"]
                    opening = item_data["opening"]
                    variation = item_data["variation"]
                    count = item_data["count"]

                    group_key = (eco, opening, variation)
                    is_expanded = group_key in self.expanded_groups

                    sub_expand_indicator = "▼  " if is_expanded else "▶  "
                    row_text = f"    {sub_expand_indicator}{eco}  |  Games: {count}  |  {opening}"

                    row_btn = ctk.CTkButton(
                        content_container,
                        text=row_text,
                        anchor="w",
                        fg_color="#223049",
                        hover_color="#2d3e5f",
                        text_color="#e2e8f0",
                        font=("Arial", 12),
                        height=32,
                        command=lambda gk=group_key: self.toggle_group_expansion(gk)
                    )
                    row_btn.pack(fill="x", padx=2, pady=2)

                    if is_expanded and instances:
                        sub_container = ctk.CTkFrame(content_container, fg_color="#1b263b", corner_radius=4)
                        sub_container.pack(fill="x", padx=12, pady=(0, 2))
                        sub_container.grid_columnconfigure(0, weight=1)

                        for inst_idx, inst in enumerate(instances):
                            inst_headers = inst.get("headers", {})
                            inst_game = inst.get("game_object")

                            tag_val = ""
                            if self.active_primary_tag:
                                if self.active_primary_tag == "Variation":
                                    tag_val = variation
                                elif self.active_primary_tag == "Players":
                                    w_p = self.get_header(inst_headers, "White", "Unknown")
                                    b_p = self.get_header(inst_headers, "Black", "Unknown")
                                    tag_val = f"{w_p} vs {b_p}"
                                elif self.active_primary_tag == "Elo":
                                    w_e = self.get_header(inst_headers, "WhiteElo", "?")
                                    b_e = self.get_header(inst_headers, "BlackElo", "?")
                                    tag_val = f"{w_e} vs {b_e}"
                                else:
                                    tag_val = self.get_header(inst_headers, self.active_primary_tag, "")
                            elif self.active_extra_columns:
                                extra_parts = []
                                for col in sorted(self.active_extra_columns):
                                    val = self.get_header(inst_headers, col, "-")
                                    extra_parts.append(f"{col}: {val}")
                                tag_val = "  |  ".join(extra_parts)

                            moves_str = self.get_first_n_moves_str(inst_game, n=10)

                            if tag_val.strip() and tag_val != variation:
                                sub_text = f"    {tag_val}   |   {moves_str}"
                            else:
                                sub_text = f"    {moves_str}"

                            sub_btn = ctk.CTkButton(
                                sub_container,
                                text=sub_text,
                                anchor="w",
                                fg_color="transparent",
                                hover_color="#2d3e5f",
                                text_color="#cbd5e1",
                                font=("Arial", 11),
                                height=28,
                                command=lambda game_inst=inst: self.on_game_click(game_inst)
                            )
                            sub_btn.pack(fill="x", padx=2, pady=1)

        self.lbl_tag_count.configure(text=f"Active View: {active_display_tag}")

    def toggle_eco_section(self, cat):
        if cat in self.expanded_eco_sections:
            self.expanded_eco_sections.remove(cat)
        else:
            self.expanded_eco_sections = {cat}
            self.lazy_load_eco_section(cat)
        self.refresh_current_view()

    def lazy_load_eco_section(self, cat):
        unloaded_count = 0
        for item in self.aggregated_games_data:
            eco = item["eco"]
            eco_base = eco[0].upper() if eco else "A"
            if eco_base == cat:
                for inst in item["instances"]:
                    if inst.get("game_object") is None:
                        unloaded_count += 1

        if unloaded_count == 0:
            return

        overlay = None
        try:
            overlay = LoadingOverlay(self, title_text="Totten", message=f"Loading ECO {cat} games... (0/{unloaded_count})")
            self.update_idletasks()
        except Exception:
            pass

        set_status_message(f"Loading games for ECO {cat} ({unloaded_count} games)...")
        threading.Thread(target=self._background_load_eco_section_worker, args=(cat, overlay), daemon=True).start()

    def _background_load_eco_section_worker(self, target_cat, overlay):
        if not self.pgn_path.exists():
            if overlay:
                try:
                    overlay.close()
                except Exception:
                    pass
            return

        updated_items = {}
        try:
            with open(self.pgn_path, "r", encoding="utf-8", errors="replace") as f:
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break

                    headers = game.headers
                    cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in headers.items()}
                    eco = self.get_header(cleaned, "ECO", "A00")
                    eco_base = eco[0].upper() if eco else "A"

                    if eco_base == target_cat:
                        opening = self.get_header(cleaned, "Opening", "Unknown")
                        variation = self.get_header(cleaned, "Variation", "")
                        key = (eco, opening, variation)
                        if key not in updated_items:
                            updated_items[key] = []
                        updated_items[key].append({
                            "headers": cleaned,
                            "game_object": game
                        })
        except Exception as e:
            print(f"Error lazy loading ECO {target_cat}: {e}")

        self.after(0, lambda: self._merge_lazy_eco_section(target_cat, updated_items, overlay))

    def _merge_lazy_eco_section(self, target_cat, updated_items, overlay):
        for item in self.aggregated_games_data:
            eco = item["eco"]
            eco_base = eco[0].upper() if eco else "A"
            if eco_base == target_cat:
                key = (eco, item["opening"], item["variation"])
                if key in updated_items:
                    item["instances"] = updated_items[key]

        if overlay:
            try:
                overlay.close()
            except Exception:
                pass

        self.refresh_current_view()
        set_status_message(f"ECO {target_cat} loaded.")

    def toggle_group_expansion(self, group_key):
        if group_key in self.expanded_groups:
            self.expanded_groups.remove(group_key)
        else:
            self.expanded_groups.add(group_key)
        self.refresh_current_view()

    def on_game_click(self, game_data):
        if not game_data:
            return
        game_obj = game_data.get("game_object")
        headers = game_data.get("headers", {})
        white = self.get_header(headers, "White", "Unknown")
        black = self.get_header(headers, "Black", "Unknown")

        set_status_message(f"Loading analysis: {white} vs {black}")

        if game_obj:
            if hasattr(self.app_state, "set_active_analysis_game"):
                self.app_state.set_active_analysis_game(game_obj)
            elif hasattr(self.app_state, "load_analysis_game"):
                self.app_state.load_analysis_game(game_obj)

            if hasattr(self.app_state, "show_analysis_workspace") and self.app_state.show_analysis_workspace:
                self.app_state.show_analysis_workspace()

    def check_and_load_catalog(self):
        eco_exists = self.eco_dir.exists() and any(self.eco_dir.glob("*.pgn"))
        if self.db_path.exists() or self.pgn_path.exists() or eco_exists:
            self.pack_propagate(True)
            self.update_idletasks()
            self.after(50, self.load_catalog)
        else:
            self.aggregated_games_data = []
            self.refresh_current_view()

    def load_catalog(self):
        set_status_message("Loading catalog via DuckDB...")

        if hasattr(self, "loading_overlay") and self.loading_overlay:
            try:
                self.loading_overlay.close()
            except Exception:
                pass

        self.loading_overlay = LoadingOverlay(self, title_text="Totten", message="Initializing catalog...")

        self.aggregated_games_data = []
        self.refresh_current_view()

        self.after(50, lambda: threading.Thread(target=self._background_load_catalog_worker, daemon=True).start())

    def _background_load_catalog_worker(self):
        catalog_data = {}
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    catalog_data = json.load(f)
            except Exception as e:
                print(f"Error loading catalog json: {e}")

        grouped_variations = {}
        total_raw_games = 0

        try:
            con = duckdb.connect(str(self.db_path))

            con.execute("""
                CREATE TABLE IF NOT EXISTS catalog_headers (
                    game_index INTEGER,
                    eco VARCHAR,
                    opening VARCHAR,
                    variation VARCHAR,
                    white VARCHAR,
                    black VARCHAR,
                    headers_json VARCHAR
                )
            """)

            existing_count = con.execute("SELECT COUNT(*) FROM catalog_headers").fetchone()[0]
            print(f"[Catalog Import] Existing games in DuckDB: {existing_count}")

            self.after(0, lambda: self.loading_overlay.update_message("Building and querying variation groups..."))

            query_res = con.execute("""
                SELECT eco, opening, variation, COUNT(*), json_group_array(headers_json)
                FROM catalog_headers
                GROUP BY eco, opening, variation
            """).fetchall()

            total_raw_games = con.execute("SELECT COUNT(*) FROM catalog_headers").fetchone()[0]
            con.close()

            print(f"[Catalog Import] Total catalog size: {total_raw_games} games across {len(query_res)} variation groups.")

            for row in query_res:
                eco, opening, variation, count, headers_json_list = row
                key = (eco, opening, variation)

                instances = []
                try:
                    parsed_list = json.loads(headers_json_list)
                    for h_dict in parsed_list:
                        instances.append({
                            "headers": h_dict,
                            "game_object": None
                        })
                except Exception:
                    pass

                grouped_variations[key] = {
                    "eco": eco,
                    "opening": opening,
                    "variation": variation,
                    "count": count,
                    "instances": instances
                }

        except Exception as e:
            print(f"Error indexing catalog with DuckDB: {e}")

        final_headers_data = list(grouped_variations.values())
        self.after(0, lambda: self._finalize_catalog_load(final_headers_data, catalog_data, total_raw_games))

    def _finalize_catalog_load(self, headers_data, catalog_data, total_raw_games):
        self.aggregated_games_data = headers_data
        self.catalog = catalog_data

        self.session_representative_cache.clear()
        self.refresh_current_view()

        if hasattr(self, "loading_overlay") and self.loading_overlay:
            try:
                self.loading_overlay.close()
            except Exception:
                pass

        set_status_message(
            f"Catalog indexed via DuckDB: {total_raw_games} games structured into {len(self.aggregated_games_data)} variation groups across A–E sections.")

    def apply_filter(self):
        self.refresh_current_view()