import json
import os
from pathlib import Path
from tkinter import ttk, messagebox, filedialog
import threading
import customtkinter as ctk
import chess.pgn

import gui.app_state as state
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
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.app_state = app_state or state

        self.json_path = Path("personal_catalog.json")
        self.pgn_path = Path("personal_catalog.pgn")

        self.eco_dir = Path("catalog_eco")
        self.eco_files = {cat: self.eco_dir / f"{cat.lower()}.pgn" for cat in ["A", "B", "C", "D", "E"]}

        self.catalog = {}
        self.aggregated_games_data = []

        # Track the currently active tag/column explicitly
        self.active_primary_tag = "Variation"
        self.active_extra_columns = set()

        # Sorting tracking variables
        self.sort_column = None
        self.sort_reverse = False

        # Mapping to store exact game instances by Treeview item ID for click-to-analysis
        self.tree_item_game_map = {}

        self._configure_styles()
        self._build_ui()

        self.after(100, self.check_and_load_catalog)

    def _configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure(
            "Treeview",
            background="#222e42",
            fieldbackground="#222e42",
            foreground="white",
            rowheight=26,
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            background="#2a384f",
            foreground="white",
            borderwidth=0,
            padding=(3, 4),
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", "#33445e"), ("!active", "#2a384f")],
            foreground=[("active", "white"), ("!active", "white")],
        )

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.panel = ctk.CTkFrame(self, fg_color="#172134", corner_radius=0)
        self.panel.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.panel.grid_rowconfigure(0, weight=1)
        self.panel.grid_columnconfigure(0, weight=1)

        # 1. Search/Workspace View
        self.search_view = ctk.CTkFrame(self.panel, fg_color="transparent")
        self.search_view.grid_rowconfigure(1, weight=1)
        self.search_view.grid_columnconfigure(0, weight=1)

        self.toolbar = ctk.CTkFrame(self.search_view, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.toolbar.grid_columnconfigure(1, weight=1)

        self.entry_filter = ctk.CTkEntry(
            self.toolbar,
            placeholder_text="Search catalog fields...",
            width=260,
            fg_color="#222e42",
            text_color="white",
            border_color="#33445e"
        )
        self.entry_filter.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.entry_filter.bind("<KeyRelease>", lambda e: self.apply_filter())

        self.tag_buttons_frame = ctk.CTkFrame(self.toolbar, fg_color="transparent")
        self.tag_buttons_frame.grid(row=0, column=1, sticky="w", padx=5)

        for tag in ["Players", "Elo", "Event", "All"]:
            if tag == "All":
                btn = ctk.CTkButton(
                    self.tag_buttons_frame,
                    text=tag,
                    width=65,
                    height=24,
                    font=("Arial", 10),
                    fg_color="#222e42",
                    text_color="white",
                    hover_color="#33445e",
                    command=self.open_all_tags_dialog
                )
            else:
                btn = ctk.CTkButton(
                    self.tag_buttons_frame,
                    text=tag,
                    width=65,
                    height=24,
                    font=("Arial", 10),
                    fg_color="#222e42",
                    text_color="white",
                    hover_color="#33445e",
                    command=lambda t=tag: self.select_primary_tag(t)
                )
            btn.pack(side="left", padx=2)

        self.lbl_tag_count = ctk.CTkLabel(self.toolbar, text="", font=("Arial", 11), text_color="#94a3b8")
        self.lbl_tag_count.grid(row=0, column=2, sticky="e", padx=5)

        self.table_frame = ctk.CTkFrame(self.search_view, fg_color="#172134")
        self.table_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        # 2. Import / Progress View
        self.import_view = ctk.CTkFrame(self.panel, fg_color="#172134")
        self.import_view.grid_rowconfigure(4, weight=1)
        self.import_view.grid_columnconfigure(0, weight=1)

        self.btn_import = ctk.CTkButton(
            self.import_view,
            text="Import PGN",
            command=self.browse_and_import_pgn,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            text_color="white"
        )
        self.btn_import.grid(row=0, column=0, pady=(0, 15), sticky="w")

        lbl_paste_instructions = ctk.CTkLabel(
            self.import_view,
            text="Or paste single / multiple PGN games below:",
            font=("Arial", 12),
            text_color="#94a3b8"
        )
        lbl_paste_instructions.grid(row=1, column=0, pady=(0, 5), sticky="w")

        self.text_paste = ctk.CTkTextbox(
            self.import_view,
            height=180,
            fg_color="#222e42",
            text_color="white",
            border_color="#33445e",
            border_width=1
        )
        self.text_paste.grid(row=2, column=0, sticky="nsew", pady=(0, 10))

        self.btn_process_paste = ctk.CTkButton(
            self.import_view,
            text="Process Pasted PGN",
            command=self.process_pasted_pgn,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            text_color="white"
        )
        self.btn_process_paste.grid(row=3, column=0, pady=(0, 10), sticky="w")

        self.setup_treeview(["ECO", "Games", "Opening", "Variation", ""])

    def open_all_tags_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("All Available Tags")
        dialog.geometry("320x400")
        dialog.transient(self)
        dialog.grab_set()

        dialog.configure(fg_color="#172134")

        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)

        frame = ctk.CTkFrame(dialog, fg_color="#172134")
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        scrollable_frame = ctk.CTkScrollableFrame(frame, fg_color="#222e42", label_fg_color="#222e42")
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        all_possible_tags = sorted(list(STANDARD_TAG_BANK["common"] | STANDARD_TAG_BANK["essential"]))

        for tag in all_possible_tags:
            if tag in ("ECO", "Opening", "Variation", "Games"):
                continue

            var = ctk.BooleanVar(value=tag in self.active_extra_columns)
            chk = ctk.CTkCheckBox(
                scrollable_frame,
                text=tag,
                variable=var,
                command=lambda t=tag, v=var: self.toggle_tag_from_dialog(t, v.get()),
                text_color="white",
                fg_color="#3b82f6",
                hover_color="#2563eb",
                border_color="#33445e"
            )
            chk.pack(anchor="w", pady=4, padx=5)

    def toggle_tag_from_dialog(self, tag, is_checked):
        if is_checked:
            self.active_extra_columns.add(tag)
        else:
            if tag in self.active_extra_columns:
                self.active_extra_columns.remove(tag)
        self.active_primary_tag = None
        self.refresh_current_view()

    def toggle_layout(self, show_search=True):
        if show_search:
            self.import_view.grid_remove()
            self.search_view.grid(row=0, column=0, sticky="nsew")
        else:
            self.search_view.grid_remove()
            self.import_view.grid(row=0, column=0, sticky="nsew")

    def setup_treeview(self, columns):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")

        self.tree.tag_configure("eco_a", background="#222e42", foreground="#e15a5a")
        self.tree.tag_configure("eco_b", background="#222e42", foreground="#7da6f3")
        self.tree.tag_configure("eco_c", background="#222e42", foreground="#86efac")
        self.tree.tag_configure("eco_d", background="#222e42", foreground="#ed861b")
        self.tree.tag_configure("eco_e", background="#222e42", foreground="#af7ce4")

        self.tree.tag_configure("eco_default", background="#222e42", foreground="white")
        self.tree.tag_configure("eco_child", background="#222e42", foreground="#94a3b8")
        self.tree.tag_configure("eco_divider", background="#222e42", foreground="#33445e")

        for col in columns:
            self.tree.heading(col, text=col, anchor="w", command=lambda c=col: self.sort_by_column(c))

            if col == "":
                self.tree.column(col, width=1, minwidth=20, anchor="w", stretch=True)
            elif col in ("ECO", "Games", "Result", "Round", "PlyCount"):
                self.tree.column(col, width=65, minwidth=45, anchor="w", stretch=False)
            elif col in ("White", "Black", "Date", "Site", "Event", "WhiteElo", "BlackElo"):
                self.tree.column(col, width=110, minwidth=80, anchor="w", stretch=False)
            elif col in ("Opening", "Variation"):
                self.tree.column(col, width=180, minwidth=120, anchor="w", stretch=False)
            else:
                self.tree.column(col, width=95, minwidth=60, anchor="w", stretch=False)

        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self.on_game_double_click)

        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

    def sort_by_column(self, col):
        if col == "":
            return
        if self.sort_column == col:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = col
            self.sort_reverse = False
        self.refresh_current_view()

    def on_game_double_click(self, event):
        selected_item = self.tree.focus()
        if selected_item and selected_item in self.tree_item_game_map:
            game_instance = self.tree_item_game_map[selected_item]
            white = game_instance["headers"].get("White", "Unknown")
            black = game_instance["headers"].get("Black", "Unknown")
            event_name = game_instance["headers"].get("Event", "Analysis Game")

            set_status_message(f"Opening analysis for: {white} vs {black} ({event_name})")

            messagebox.showinfo("Navigation",
                                f"Jumping to Analysis Workspace for:\n\n{white} vs {black}\nEvent: {event_name}")

    def on_tree_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            self.tree.selection_remove(selected_items)

    def _get_eco_tag(self, eco_base):
        prefix = eco_base[0].upper() if eco_base else 'A'
        return f"eco_{prefix.lower()}"

    def select_primary_tag(self, tag):
        self.active_primary_tag = tag
        self.active_extra_columns.clear()
        self.refresh_current_view()

    def refresh_current_view(self):
        base_cols = ["ECO", "Games", "Opening"]

        if self.active_primary_tag == "Players":
            dynamic_cols = ["White", "Black"]
        elif self.active_primary_tag == "Elo":
            dynamic_cols = ["WhiteElo", "BlackElo"]
        elif self.active_primary_tag == "Event":
            dynamic_cols = ["Event"]
        elif self.active_extra_columns:
            dynamic_cols = sorted(list(self.active_extra_columns))
        else:
            dynamic_cols = ["Variation"]

        current_cols = base_cols + dynamic_cols
        treeview_cols = current_cols + [""]

        self.setup_treeview(treeview_cols)
        self.tree_item_game_map.clear()

        if self.sort_column:
            try:
                col_idx = current_cols.index(self.sort_column)
                if self.sort_column == "Games":
                    sorted_data = sorted(
                        self.aggregated_games_data,
                        key=lambda x: x["count"],
                        reverse=self.sort_reverse
                    )
                else:
                    sorted_data = sorted(
                        self.aggregated_games_data,
                        key=lambda x: str(
                            x["eco"] if self.sort_column == "ECO" else
                            x["opening"] if self.sort_column == "Opening" else
                            x["variation"] if self.sort_column == "Variation" else
                            x["instances"][0]["headers"].get(self.sort_column, "")
                        ),
                        reverse=self.sort_reverse
                    )
            except Exception:
                sorted_data = self.aggregated_games_data
        else:
            sorted_data = sorted(
                self.aggregated_games_data,
                key=lambda x: (
                    -x["count"],
                    x["eco"],
                    x["opening"],
                    x["variation"]
                )
            )

        query = self.entry_filter.get().lower()
        last_eco_base = None

        for item_data in sorted_data:
            eco = item_data["eco"]
            eco_base = eco[0].upper() if eco else ""
            opening = item_data["opening"]
            variation = item_data["variation"]
            count = item_data["count"]
            instances = item_data["instances"]

            parent_row = []
            for col in treeview_cols:
                if col == "":
                    parent_row.append("")
                elif col == "ECO":
                    parent_row.append(eco)
                elif col == "Games":
                    parent_row.append(str(count))
                elif col == "Opening":
                    parent_row.append(opening)
                elif col == "Variation":
                    parent_row.append(variation)
                else:
                    parent_row.append(instances[0]["headers"].get(col, "") if count == 1 else "")

            if not query or any(query in str(val).lower() for val in parent_row):
                if eco_base != last_eco_base:
                    if last_eco_base is not None:
                        divider_row = ["━━━━━━" if col == "ECO" else ("............" if col != "" else "") for col in
                                       treeview_cols]
                        self.tree.insert("", "end", values=divider_row, tags=("eco_divider",))
                    last_eco_base = eco_base

                row_tag = self._get_eco_tag(eco_base)

                if count > 1:
                    parent_id = self.tree.insert("", "end", values=parent_row, tags=(row_tag,))

                    if count == 1 and instances:
                        self.tree_item_game_map[parent_id] = instances[0]

                    for idx, inst in enumerate(instances, 1):
                        headers = inst["headers"]
                        child_row = []
                        for col in treeview_cols:
                            if col == "":
                                child_row.append("")
                            elif col == "ECO":
                                child_row.append(eco)
                            elif col == "Games":
                                child_row.append(f"#{idx}")
                            elif col == "Opening":
                                child_row.append(opening)
                            elif col == "Variation":
                                child_row.append(variation if col == "Variation" else headers.get(col, ""))
                            else:
                                child_row.append(headers.get(col, ""))

                        child_id = self.tree.insert(parent_id, "end", values=child_row, tags=("eco_child",))
                        self.tree_item_game_map[child_id] = inst
                else:
                    parent_id = self.tree.insert("", "end", values=parent_row, tags=(row_tag,))
                    if instances:
                        self.tree_item_game_map[parent_id] = instances[0]

        self.lbl_tag_count.configure(text=f"Active Columns: {len(current_cols)}")

    def check_and_load_catalog(self):
        eco_exists = self.eco_dir.exists() and any(self.eco_dir.glob("*.pgn"))
        if self.pgn_path.exists() or eco_exists:
            self.load_catalog()
        else:
            self.toggle_layout(show_search=False)

    def browse_and_import_pgn(self):
        file_path = filedialog.askopenfilename(
            title="Select PGN File",
            filetypes=[("PGN Files", "*.pgn"), ("All Files", "*.*")]
        )
        if file_path:
            try:
                content = Path(file_path).read_text(encoding="utf-8", errors="ignore")
                self.pgn_path.write_text(content, encoding="utf-8")
                self.load_catalog()
            except Exception as e:
                messagebox.showerror("Import Error", f"Could not read selected PGN file:\n{e}")

    def process_pasted_pgn(self):
        pasted_content = self.text_paste.get("1.0", "end-1c").strip()
        if not pasted_content:
            messagebox.showwarning("Empty Input", "Please paste PGN text into the text area before processing.")
            return
        try:
            self.pgn_path.write_text(pasted_content, encoding="utf-8")
            self.load_catalog()
        except Exception as e:
            messagebox.showerror("Processing Error", f"Could not save pasted PGN data:\n{e}")

    def load_catalog(self):
        self.toggle_layout(show_search=True)
        set_status_message("Loading catalog in background...")
        threading.Thread(target=self._background_load_catalog_worker, daemon=True).start()

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

        if self.pgn_path.exists():
            try:
                with open(self.pgn_path, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        total_raw_games += 1

                        headers = game.headers
                        cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in headers.items()}

                        eco = cleaned.get("ECO", "A00")
                        opening = cleaned.get("Opening", "Unknown")
                        variation = cleaned.get("Variation", "")

                        key = (eco, opening, variation)

                        if key not in grouped_variations:
                            grouped_variations[key] = {
                                "eco": eco,
                                "opening": opening,
                                "variation": variation,
                                "count": 0,
                                "instances": []
                            }

                        grouped_variations[key]["count"] += 1
                        grouped_variations[key]["instances"].append({
                            "headers": cleaned
                        })
            except Exception as e:
                print(f"Error loading catalog pgn: {e}")

        headers_data = list(grouped_variations.values())
        self.after(0, lambda: self._finalize_catalog_load(headers_data, catalog_data, total_raw_games))

    def _finalize_catalog_load(self, headers_data, catalog_data, total_raw_games):
        self.aggregated_games_data = headers_data
        self.catalog = catalog_data
        self.refresh_current_view()

        set_status_message(
            f"Catalog loaded: {total_raw_games} games structured into {len(self.aggregated_games_data)} variation groups.")

    def apply_filter(self):
        self.refresh_current_view()