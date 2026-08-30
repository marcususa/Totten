import os
import json
from pathlib import Path
from tkinter import ttk, filedialog
import tkinter as tk

import chess.pgn
import customtkinter as ctk

import gui.app_state as state
from gui.statusbar import set_status_message
from gui.splash import LoadingOverlay
from gui.edit_dialogs import (
    ConfirmationDialog, GameSelectionDialog, CollectionLimitDialog, AddCategoryDialog
)

DEFAULT_COLLECTION_CATEGORIES = [
    "Open Events", "Women's Events", "Tournaments", "Matches",
    "Championships", "Openings", "Middlegames", "Endgames",
    "Time Periods / Eras", "Notable People / Players"
]

CATEGORY_FOLDER_MAP = {
    "Open Events": ("open", "open_events.pgn"),
    "Women's Events": ("women", "womens_events.pgn"),
    "Tournaments": ("tournaments", "tournaments.pgn"),
    "Matches": ("matches", "matches.pgn"),
    "Championships": ("championships", "championships.pgn"),
    "Openings": ("openings", "openings.pgn"),
    "Middlegames": ("middlegames", "middlegames.pgn"),
    "Endgames": ("endgames", "endgames.pgn"),
    "Time Periods / Eras": ("era", "era.pgn"),
    "Notable People / Players": ("players", "players.pgn"),
}

CONFIG_FILE = Path(__file__).resolve().parent.parent / "pgn" / "categories_config.json"


def load_categories_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cats = data.get("categories", DEFAULT_COLLECTION_CATEGORIES)
                custom_map = data.get("custom_map", {})
                for k, v in custom_map.items():
                    CATEGORY_FOLDER_MAP[k] = (v[0], v[1])
                return cats
        except Exception:
            pass
    return list(DEFAULT_COLLECTION_CATEGORIES)


def save_categories_config(categories):
    custom_map = {cat: CATEGORY_FOLDER_MAP[cat] for cat in categories if cat not in DEFAULT_COLLECTION_CATEGORIES}
    data = {
        "categories": categories,
        "custom_map": custom_map
    }
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving category config: {e}")


class EditWorkspace(ctk.CTkFrame):

    def __init__(self, master, initial_games=None, filename=None, *args, **kwargs):
        super().__init__(master, fg_color="#172134", corner_radius=0)

        self.categories = load_categories_config()
        self.collection_files = {}
        self.selected_files = []
        self.tree_map = {}

        # Build all UI components first so attributes exist
        self._configure_styles()
        self._build_ui()

        # Grab from parameters or fallback to state bucket
        self.games_list = initial_games or state.mixed_state.get("active_games") or []
        self.filename = filename or state.mixed_state.get("current_filename")

        if self.filename:
            self.load_catalog_data()
        elif self.games_list:
            self.load_games_list(self.games_list)
        else:
            # Default load first category view so the table is never blank
            raw_choice = self.opt_category.get()
            cat = self._unnumber_category(raw_choice)
            self._load_category_files(cat)
            self._refresh_treeview()

        # Clear out state bucket after consumption so it doesn't stale-lock
        state.mixed_state["active_games"] = None
        state.mixed_state["current_filename"] = None

    def load_catalog_data(self):
        """Loads data when initialized with a specific filename."""
        if self.filename:
            for cat in self.categories:
                self._load_category_files(cat)
            self._refresh_treeview()

    def load_games_list(self, games_list):
        """Loads a direct list of games into the tree view."""
        self.games_list = games_list
        for item in self.col_tree.get_children():
            self.col_tree.delete(item)
        self.tree_map.clear()

        for idx, game in enumerate(games_list, start=1):
            headers = game.headers
            white = headers.get("White", "?")
            black = headers.get("Black", "?")
            res = headers.get("Result", "*")
            item_id = self.col_tree.insert("", "end", values=(idx, white, black, res))
            self.tree_map[item_id] = (game, self.filename or "")

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.layout("Borderless.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        style.configure(
            "Borderless.Treeview",
            background="#1e293b",
            foreground="#f8fafc",
            fieldbackground="#1e293b",
            rowheight=22,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
            highlightthickness=0
        )
        style.map(
            "Borderless.Treeview",
            background=[("selected", "#334155"), ("focus", "#1e293b"), ("active", "#1e293b")],
            foreground=[("selected", "#ffffff"), ("focus", "#f8fafc"), ("active", "#f8fafc")],
            borderwidth=[("focus", 0), ("active", 0)]
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

    def refresh_view(self):
        self._refresh_treeview()

    def _get_numbered_categories(self):
        return [f"{i + 1}. {cat}" for i, cat in enumerate(self.categories)]

    def _unnumber_category(self, display_str):
        if not display_str:
            return ""
        parts = display_str.split(". ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            return parts[1]
        return display_str

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=2)

        # Left Column: Structured Game Table View
        left_box = ctk.CTkFrame(self, fg_color="#172134", corner_radius=8, border_color="#334155", border_width=1)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left_box.grid_rowconfigure(0, weight=1)
        left_box.grid_columnconfigure(0, weight=1)

        self.tree_frame = ctk.CTkFrame(left_box, fg_color="transparent")
        self.tree_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
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

        # Right Column: Control Panel
        right_box = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8, border_color="#334155", border_width=1)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_box.grid_columnconfigure(0, weight=1)

        header_box = ctk.CTkFrame(right_box, fg_color="transparent")
        header_box.pack(fill="x", padx=10, pady=(15, 5))
        ctk.CTkLabel(header_box, text="Mixed Collections", font=("Arial", 14, "bold"), text_color="white").pack(
            anchor="w")
        ctk.CTkLabel(header_box, text="Select category first.", font=("Arial", 12), text_color="#94a3b8").pack(
            anchor="w")

        col_ctrl = ctk.CTkFrame(right_box, fg_color="transparent")
        col_ctrl.pack(fill="x", padx=10, pady=5)

        opt_border = ctk.CTkFrame(col_ctrl, fg_color="transparent", border_width=2, border_color="#475569",
                                  corner_radius=0)
        opt_border.pack(side="left", padx=(0, 4))

        numbered_cats = self._get_numbered_categories()
        default_cat = numbered_cats[0] if numbered_cats else ""
        self.opt_category = ctk.CTkOptionMenu(
            opt_border, values=numbered_cats, width=130, corner_radius=0,
            fg_color="#344268", button_color="#344268", button_hover_color="#2e4a8c",
            dropdown_hover_color="#2e4a8c", dropdown_fg_color="#344268", command=self._on_category_changed
        )
        self.opt_category.set(default_cat)
        self.opt_category.pack(padx=1, pady=1)

        ctk.CTkButton(col_ctrl, text="+ Category", fg_color="#344268", hover_color="#2e4a8c", border_width=2,
                      border_color="#475569", width=75, height=28, font=("Arial", 12), command=self._add_category).pack(
            side="right")

        move_row = ctk.CTkFrame(right_box, fg_color="transparent")
        move_row.pack(fill="x", padx=10, pady=(5, 2))
        move_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(move_row, text="Up", fg_color="#334155", hover_color="#475569", border_width=1,
                      border_color="#64748b", height=28, font=("Arial", 12),
                      command=lambda: self._move_category(-1)).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ctk.CTkButton(move_row, text="Down", fg_color="#334155", hover_color="#475569", border_width=1,
                      border_color="#64748b", height=28, font=("Arial", 12),
                      command=lambda: self._move_category(1)).grid(row=0, column=1, sticky="ew", padx=(2, 0))

        info_row = ctk.CTkFrame(right_box, fg_color="transparent")
        info_row.pack(fill="x", padx=10, pady=(5, 2))
        self.lbl_selected_files = ctk.CTkLabel(info_row, text="No PGN files selected.", font=("Arial", 12),
                                               text_color="#94a3b8", anchor="w")
        self.lbl_selected_files.pack(side="left", anchor="w")

        action_row = ctk.CTkFrame(right_box, fg_color="transparent")
        action_row.pack(fill="x", padx=10, pady=(2, 10))

        self.btn_undo_pgn = ctk.CTkButton(
            action_row, text="✕", fg_color="#dd0000", hover_color="#b91c1c",
            border_width=2, border_color="#660000", width=26, height=30, font=("Arial", 12, "bold"),
            text_color="white", command=self._undo_last_pgn
        )

        self.btn_select_pgns = ctk.CTkButton(
            action_row, text="Select PGNs", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", width=95, height=30, font=("Arial", 12),
            command=self._select_pgn_files
        )
        self.btn_select_pgns.pack(side="left", padx=(0, 3))

        ctk.CTkButton(
            action_row, text="+ Collection", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", width=125, height=30, font=("Arial", 12, "bold"),
            command=self._create_collection
        ).pack(side="left", padx=(3, 0))

        separator1 = ctk.CTkFrame(right_box, fg_color="#334155", height=2)
        separator1.pack(fill="x", padx=10, pady=10)

        del_header = ctk.CTkFrame(right_box, fg_color="transparent")
        del_header.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(del_header, text="Use with caution when deleting", font=("Arial", 11, "bold"),
                     text_color="#f87171").pack(anchor="w")

        del_row = ctk.CTkFrame(right_box, fg_color="transparent")
        del_row.pack(fill="x", padx=10, pady=2)
        del_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(del_row, text="Delete Category", fg_color="#334155", hover_color="#475569", border_width=1,
                      border_color="#64748b", height=28, font=("Arial", 12), command=self._delete_category).grid(row=0,
                                                                                                                 column=0,
                                                                                                                 sticky="ew",
                                                                                                                 padx=(
                                                                                                                     0,
                                                                                                                     2))
        ctk.CTkButton(del_row, text="Delete PGN File", fg_color="#334155", hover_color="#475569", border_width=1,
                      border_color="#64748b", height=28, font=("Arial", 12),
                      command=self._delete_selected_pgn_file).grid(row=0, column=1, sticky="ew", padx=(2, 0))

        separator2 = ctk.CTkFrame(right_box, fg_color="#334155", height=2)
        separator2.pack(fill="x", padx=10, pady=10)

        eco_box = ctk.CTkFrame(right_box, fg_color="transparent")
        eco_box.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(eco_box, text="ECO Tag Repair", font=("Arial", 12, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkButton(eco_box, text="Scan & Repair ECOs", fg_color="#344268", hover_color="#2e4a8c", border_width=2,
                      border_color="#475569", height=30, font=("Arial", 12), command=self._repair_eco_tags).pack(
            fill="x", pady=(4, 0))

        engine_box = ctk.CTkFrame(right_box, fg_color="transparent")
        engine_box.pack(fill="x", padx=10, pady=(12, 5))
        ctk.CTkLabel(engine_box, text="Engine Manager", font=("Arial", 12, "bold"), text_color="white").pack(anchor="w")
        eng_row = ctk.CTkFrame(engine_box, fg_color="transparent")
        eng_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(eng_row, text="Browse Engine", fg_color="#344268", hover_color="#2e4a8c", border_width=2,
                      border_color="#475569", height=30, font=("Arial", 12), command=self._browse_engine).pack(
            side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(eng_row, text="Save Settings", fg_color="#334155", hover_color="#475569", border_width=1,
                      border_color="#64748b", height=30, font=("Arial", 12), command=self._save_engine_settings).pack(
            side="right", fill="x", expand=True, padx=(2, 0))

    def _load_category_files(self, category):
        base_dir = Path(__file__).resolve().parent.parent / "pgn"
        subfolder = CATEGORY_FOLDER_MAP.get(category, ("", ""))[0]
        cat_dir = base_dir / subfolder if subfolder else base_dir

        files_dict = {}
        if cat_dir.exists():
            for fpath in cat_dir.glob("*.pgn"):
                rows = []
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        while True:
                            game = chess.pgn.read_game(f)
                            if not game:
                                break
                            rows.append((
                                f"{game.headers.get('White', '?')} vs {game.headers.get('Black', '?')}",
                                game.headers.get("Result", "*"),
                                game.headers.get("Opening", ""),
                                game
                            ))
                except Exception as e:
                    print(f"Error loading {fpath.name}: {e}")
                if rows:
                    files_dict[str(fpath.resolve())] = rows

        self.collection_files[category] = files_dict

    def _on_category_changed(self, choice):
        cat = self._unnumber_category(choice)
        self._load_category_files(cat)
        self._refresh_treeview()

    def _refresh_treeview(self):
        for item in self.col_tree.get_children():
            self.col_tree.delete(item)
        self.tree_map.clear()

        raw_choice = self.opt_category.get()
        current_cat = self._unnumber_category(raw_choice)

        # Ensure category files are loaded before populating tree
        if current_cat not in self.collection_files or not self.collection_files[current_cat]:
            self._load_category_files(current_cat)

        files_dict = self.collection_files.get(current_cat, {})

        all_games = []
        for fpath_str, rows in files_dict.items():
            for white_black, res, opening, game in rows:
                parts = white_black.split(" vs ")
                white = parts[0] if len(parts) > 0 else "?"
                black = parts[1] if len(parts) > 1 else "?"
                all_games.append((game, white, black, res, fpath_str))

        for idx, (game, white, black, res, fpath_str) in enumerate(all_games, start=1):
            item_id = self.col_tree.insert("", "end", values=(idx, white, black, res))
            self.tree_map[item_id] = (game, fpath_str)

    def _on_tree_select(self, event):
        pass

    def _on_tree_double_click(self, event):
        item_id = self.col_tree.identify_row(event.y)
        if not item_id or item_id not in self.tree_map:
            return

        game, source_data = self.tree_map[item_id]
        print(f"[DEBUG] Double click fired! Selected game source file: {source_data}")

        # Directly search all cached category file dictionaries using absolute resolved path
        target_file_games = []
        resolved_source = str(Path(source_data).resolve())

        for cat, files_dict in self.collection_files.items():
            for fpath_str, rows in files_dict.items():
                if str(Path(fpath_str).resolve()) == resolved_source:
                    target_file_games = [row[3] for row in rows]
                    break
            if target_file_games:
                break

        # Fallback to single game if file lookup fails
        all_file_games = target_file_games if target_file_games else [game]

        # Populate state with the correct collection file and games
        state.mixed_state["active_games"] = all_file_games
        state.mixed_state["current_filename"] = source_data

        # Traverse up to the main application window and trigger Stage 2 switchboard safely
        top_level = self.winfo_toplevel()
        if hasattr(top_level, "show_workspace"):
            top_level.show_workspace("mixed_analysis", initial_games=all_file_games, filename=source_data)
        else:
            print("[DEBUG] Error: top_level window has no show_workspace method.")

    def _select_pgn_files(self):
        base_dir = Path(__file__).resolve().parent.parent / "pgn"
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        sub = CATEGORY_FOLDER_MAP.get(cat, ("", ""))[0]
        init_dir = base_dir / sub if sub else base_dir

        files = filedialog.askopenfilenames(
            title="Select PGN Files",
            initialdir=str(init_dir) if init_dir.exists() else str(base_dir),
            filetypes=[("PGN Files", "*.pgn"), ("All Files", "*.*")]
        )
        if files:
            self.selected_files.extend(list(files))
            self.lbl_selected_files.configure(text=f"{len(self.selected_files)} PGN file(s) selected.")
            if not self.btn_undo_pgn.winfo_ismapped():
                self.btn_undo_pgn.pack(side="left", padx=(0, 3), before=self.btn_select_pgns)

    def _undo_last_pgn(self):
        if self.selected_files:
            self.selected_files.pop()
            if self.selected_files:
                self.lbl_selected_files.configure(text=f"{len(self.selected_files)} PGN file(s) selected.")
            else:
                self.lbl_selected_files.configure(text="No PGN files selected.")
                self.btn_undo_pgn.pack_forget()

    def _add_category(self):
        dialog = AddCategoryDialog(self)
        self.wait_window(dialog)
        if dialog.category_name and dialog.category_name not in self.categories:
            cat = dialog.category_name
            self.categories.append(cat)
            slug = "".join(c.lower() if c.isalnum() else "_" for c in cat).strip("_")
            CATEGORY_FOLDER_MAP[cat] = (slug, f"{slug}.pgn")
            save_categories_config(self.categories)

            numbered_cats = self._get_numbered_categories()
            self.opt_category.configure(values=numbered_cats)
            for nc in numbered_cats:
                if self._unnumber_category(nc) == cat:
                    self.opt_category.set(nc)
                    break

            self._load_category_files(cat)
            self._refresh_treeview()

    def _delete_category(self):
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        if not cat: return
        dialog = ConfirmationDialog(self, "Delete Category", f"Are you sure you want to delete category '{cat}'?")
        self.wait_window(dialog)
        if dialog.confirmed and cat in self.categories:
            self.categories.remove(cat)
            save_categories_config(self.categories)
            numbered_cats = self._get_numbered_categories()
            self.opt_category.configure(values=numbered_cats if numbered_cats else [""])
            self.opt_category.set(numbered_cats[0] if numbered_cats else "")
            self._refresh_treeview()

    def _move_category(self, direction):
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        if not cat or cat not in self.categories: return
        idx = self.categories.index(cat)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.categories):
            self.categories.insert(new_idx, self.categories.pop(idx))
            save_categories_config(self.categories)

            numbered_cats = self._get_numbered_categories()
            self.opt_category.configure(values=numbered_cats)
            for nc in numbered_cats:
                if self._unnumber_category(nc) == cat:
                    self.opt_category.set(nc)
                    break
            self._refresh_treeview()

    def _create_collection(self):
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        if not cat:
            set_status_message("No category selected.")
            return

        base_dir = Path(__file__).resolve().parent.parent / "pgn"
        subfolder, default_filename = CATEGORY_FOLDER_MAP.get(cat, ("", "collection.pgn"))
        target_dir = base_dir / subfolder if subfolder else base_dir
        target_dir.mkdir(parents=True, exist_ok=True)
        target_file = target_dir / default_filename

        if not self.selected_files:
            set_status_message(f"No PGNs selected to append to {cat}.")
            return

        try:
            games_to_append = []
            for fpath in self.selected_files:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if not game:
                            break
                        games_to_append.append(game)

            with open(target_file, "a", encoding="utf-8") as out_f:
                out_f.seek(0, os.SEEK_END)
                if out_f.tell() > 0:
                    out_f.write("\n\n")
                for i, game in enumerate(games_to_append):
                    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                    out_f.write(str(game.accept(exporter)) + "\n\n")

            set_status_message(
                f"Successfully appended {len(games_to_append)} game(s) to {target_file.name} under {cat}.")
            self.selected_files.clear()
            self.lbl_selected_files.configure(text="No PGN files selected.")
            self.btn_undo_pgn.pack_forget()

            self._load_category_files(cat)
            self._refresh_treeview()
        except Exception as e:
            set_status_message(f"Error appending collection: {e}")

    def _delete_selected_pgn_file(self):
        set_status_message("Select a PGN game in the tree to delete.")

    def _repair_eco_tags(self):
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        if not cat:
            set_status_message("No category selected for ECO repair.")
            return

        base_dir = Path(__file__).resolve().parent.parent / "pgn"
        subfolder, default_filename = CATEGORY_FOLDER_MAP.get(cat, ("", f"{cat}.pgn"))
        target_dir = base_dir / subfolder if subfolder else base_dir
        target_file = target_dir / default_filename

        if not target_file.exists():
            set_status_message(f"Category PGN file not found: {target_file}")
            return

        parent_root = base_dir.parent
        eco_path = parent_root / "pgn" / "eco" / "eco.pgn"
        if not eco_path.exists():
            eco_path = base_dir / "eco.pgn"

        if not eco_path.exists():
            set_status_message("eco.pgn database not found.")
            return

        import re

        def extract_tags(text):
            eco_match = re.search(r'ECO\s*["\']?([A-E]\d{2})["\']?', text, re.IGNORECASE)
            open_match = re.search(r'Opening\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
            var_match = re.search(r'Variation\s*["\']([^"\']+)["\']', text, re.IGNORECASE)

            eco = eco_match.group(1).upper() if eco_match else None
            opening = open_match.group(1).strip() if open_match else None
            variation = var_match.group(1).strip() if var_match else None
            return eco, opening, variation

        eco_map = {}
        try:
            with open(eco_path, "r", encoding="utf-8", errors="ignore") as f:
                eco_content = f.read()

            blocks = re.split(r'\n\s*\n', eco_content)
            for block in blocks:
                eco, opening, variation = extract_tags(block)
                if eco and opening:
                    eco_map[eco] = (opening, variation)
        except Exception as e:
            print(f"[DEBUG] Error reading eco.pgn: {e}")

        def lookup_eco(target_eco, available_ecos):
            if not target_eco:
                return None, None
            if target_eco in eco_map:
                return eco_map[target_eco]

            m = re.match(r'([A-E])(\d{2})', target_eco)
            if not m:
                return None, None

            prefix, num_str = m.groups()
            target_num = int(num_str)

            for d in range(1, 10):
                test_code = f"{prefix}{target_num + d:02d}"
                if test_code in eco_map:
                    return eco_map[test_code]

            for d in range(1, 10):
                test_code = f"{prefix}{target_num - d:02d}"
                if test_code in eco_map:
                    return eco_map[test_code]

            return None, None

        repaired_count = 0
        try:
            with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
                target_content = f.read()

            game_blocks = re.split(r'\n\s*\n(?=\[)', target_content)
            modified_blocks = []
            file_modified = False

            for block in game_blocks:
                eco, current_opening, current_variation = extract_tags(block)

                if eco:
                    db_opening, db_variation = lookup_eco(eco, eco_map)

                    if db_opening:
                        block_modified_local = False

                        if not current_opening or current_opening in ("", "?"):
                            if 'Opening' in block:
                                block = re.sub(r'(Opening\s*["\'])[^\"\']*(["\'])', rf'\1{db_opening}\2', block,
                                               flags=re.IGNORECASE)
                            else:
                                block = f'[Opening "{db_opening}"]\n' + block
                            block_modified_local = True

                        if db_variation and (not current_variation or current_variation in ("", "?")):
                            if 'Variation' in block:
                                block = re.sub(r'(Variation\s*["\'])[^\"\']*(["\'])', rf'\1{db_variation}\2', block,
                                               flags=re.IGNORECASE)
                            else:
                                block = f'[Variation "{db_variation}"]\n' + block
                            block_modified_local = True

                        if block_modified_local:
                            file_modified = True
                            repaired_count += 1

                modified_blocks.append(block)

            if file_modified:
                with open(target_file, "w", encoding="utf-8") as out_f:
                    out_f.write("\n\n".join(modified_blocks))

            self._load_category_files(cat)
            self._refresh_treeview()
            set_status_message(f"ECO scan complete. Repaired/updated {repaired_count} tag(s) in {target_file.name}.")
        except Exception as e:
            set_status_message(f"Error during ECO repair: {e}")

    def _browse_engine(self):
        set_status_message("Browse Engine clicked.")

    def _save_engine_settings(self):
        set_status_message("Engine settings saved.")


# Standalone factory function to support standard main.py workspace loader pattern
def create_workspace(master, *args, **kwargs):
    """Instantiates EditWorkspace for Stage 1 Mixed Collections navigation."""
    return EditWorkspace(master, *args, **kwargs)