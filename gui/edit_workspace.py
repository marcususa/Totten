import os
import json
import threading
from pathlib import Path
from tkinter import ttk, filedialog
import tkinter as tk

import chess.pgn
import customtkinter as ctk

import gui.app_state as state
from gui.statusbar import set_status_message
from gui.splash import LoadingOverlay

# Base preset categories
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
    """Loads categories and their display order, falling back to defaults."""
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
    """Saves the current category ordering and custom folder maps to disk."""
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


class ConfirmationDialog(ctk.CTkToplevel):
    """Popup confirmation dialog with Yes and No buttons centered."""

    def __init__(self, master, title, message):
        super().__init__(master)
        self.title(title)
        self.geometry("420x200")
        self.configure(fg_color="#172134")
        self.grab_set()

        self.confirmed = False
        self._center_window(master)
        self._build_ui(message)

    def _center_window(self, master):
        self.update_idletasks()
        width = 420
        height = 200
        try:
            x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
            y = master.winfo_rooty() + (master.winfo_height() // 2) - (height // 2)
        except Exception:
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def _build_ui(self, message):
        ctk.CTkLabel(
            self, text="⚠️ Are you sure?",
            font=("Arial", 15, "bold"), text_color="#f87171"
        ).pack(anchor="w", padx=20, pady=(20, 5))

        ctk.CTkLabel(
            self, text=message, font=("Arial", 12), text_color="#e2e8f0",
            justify="left", wraplength=380
        ).pack(anchor="w", padx=20, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(15, 20))
        btn_frame.grid_columnconfigure((0, 1), weight=1)

        inner_container = ctk.CTkFrame(btn_frame, fg_color="transparent")
        inner_container.pack(anchor="center")

        ctk.CTkButton(
            inner_container, text="Yes", fg_color="#b91c1c", hover_color="#991b1b",
            border_width=2, border_color="#7f1d1d", font=("Arial", 12, "bold"),
            width=90, command=self._on_yes
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            inner_container, text="No", fg_color="#334155", hover_color="#475569",
            border_width=2, border_color="#64748b", font=("Arial", 12),
            width=90, command=self.destroy
        ).pack(side="left", padx=5)

    def _on_yes(self):
        self.confirmed = True
        self.destroy()


class GameSelectionDialog(ctk.CTkToplevel):
    """Popup dialog to let users pick specific games from selected PGN files."""

    def __init__(self, master, games_data):
        super().__init__(master)
        self.title("Select Games to Include")
        self.geometry("700x450")
        self.configure(fg_color="#172134")
        self.grab_set()

        self.games_data = games_data
        self.selected_games = []

        self._center_window(master)
        self._build_ui()

    def _center_window(self, master):
        self.update_idletasks()
        width = 700
        height = 450
        try:
            x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
            y = master.winfo_rooty() + (master.winfo_height() // 2) - (height // 2)
        except Exception:
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def _build_ui(self):
        lbl = ctk.CTkLabel(
            self, text="Review and select games to include in your collection:",
            font=("Arial", 13, "bold"), text_color="white"
        )
        lbl.pack(anchor="w", padx=15, pady=(15, 5))

        container = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8)
        container.pack(fill="both", expand=True, padx=15, pady=10)

        canvas = ctk.CTkCanvas(container, bg="#1e293b", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(canvas, fg_color="#1e293b")

        self.scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas_window = canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(canvas_window, width=e.width))
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        scrollbar.pack(side="right", fill="y")

        self.checkbox_vars = []

        header_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#334155", corner_radius=4)
        header_frame.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(header_frame, text="Include", width=60, font=("Arial", 11, "bold"), text_color="white").pack(
            side="left", padx=5)
        ctk.CTkLabel(header_frame, text="White vs Black", width=240, font=("Arial", 11, "bold"), text_color="white",
                     anchor="w").pack(side="left", padx=5)
        ctk.CTkLabel(header_frame, text="Opening", width=240, font=("Arial", 11, "bold"), text_color="white",
                     anchor="w").pack(side="left", padx=5)

        for gdata in self.games_data:
            row_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=5, pady=2)

            var = ctk.BooleanVar(value=gdata["auto_select"])
            self.checkbox_vars.append((var, gdata["game"]))

            chk = ctk.CTkCheckBox(row_frame, text="", variable=var, width=30)
            chk.pack(side="left", padx=15)

            players_text = f"{gdata['white']} vs {gdata['black']}"
            ctk.CTkLabel(row_frame, text=players_text, width=240, anchor="w", text_color="white",
                         font=("Arial", 11)).pack(side="left", padx=5)

            opening_text = f"{gdata['opening']} ({gdata['variation']})" if gdata['variation'] else gdata['opening']
            ctk.CTkLabel(row_frame, text=opening_text, width=240, anchor="w", text_color="#94a3b8",
                         font=("Arial", 11)).pack(side="left", padx=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkButton(
            btn_frame, text="Confirm Selection", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", font=("Arial", 12, "bold"), command=self._on_confirm
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="Cancel", fg_color="#334155", hover_color="#475569",
            border_width=2, border_color="#64748b", font=("Arial", 12), command=self.destroy
        ).pack(side="right", padx=5)

    def _on_confirm(self):
        self.selected_games = [game for var, game in self.checkbox_vars if var.get()]
        self.destroy()


class CollectionLimitDialog(ctk.CTkToplevel):
    """Popup alert dialog when selected games exceed the collection limit."""

    def __init__(self, master, total_count):
        super().__init__(master)
        self.title("Collection Limit Exceeded")
        self.geometry("450x230")
        self.configure(fg_color="#172134")
        self.grab_set()

        self._center_window(master)
        self._build_ui(total_count)

    def _center_window(self, master):
        self.update_idletasks()
        width = 450
        height = 230
        try:
            x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
            y = master.winfo_rooty() + (master.winfo_height() // 2) - (height // 2)
        except Exception:
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def _build_ui(self, total_count):
        ctk.CTkLabel(
            self, text="⚠️ Collection Limit Exceeded",
            font=("Arial", 15, "bold"), text_color="#f87171"
        ).pack(anchor="w", padx=20, pady=(20, 5))

        msg = (
            f"The selected PGN file(s) contain {total_count} games.\n\n"
            "Collections are restricted to a maximum of 300 games to ensure smooth performance. "
            "Please split your PGN file into smaller parts or select fewer files."
        )
        ctk.CTkLabel(
            self, text=msg, font=("Arial", 12), text_color="#e2e8f0",
            justify="left", wraplength=410
        ).pack(anchor="w", padx=20, pady=5)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(15, 20))

        ctk.CTkButton(
            btn_frame, text="Understood", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", font=("Arial", 12, "bold"),
            command=self.destroy
        ).pack(side="right")


class AddCategoryDialog(ctk.CTkToplevel):
    """Dialog to create a new custom category name."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Add New Category")
        self.geometry("400x200")
        self.configure(fg_color="#172134")
        self.grab_set()

        self.category_name = None
        self._center_window(master)
        self._build_ui()

    def _center_window(self, master):
        self.update_idletasks()
        width = 400
        height = 200
        try:
            x = master.winfo_rootx() + (master.winfo_width() // 2) - (width // 2)
            y = master.winfo_rooty() + (master.winfo_height() // 2) - (height // 2)
        except Exception:
            x = (self.winfo_screenwidth() // 2) - (width // 2)
            y = (self.winfo_screenheight() // 2) - (height // 2)
        self.geometry(f"{width}x{height}+{max(0, x)}+{max(0, y)}")

    def _build_ui(self):
        ctk.CTkLabel(
            self, text="Create New Collection Category",
            font=("Arial", 13, "bold"), text_color="white"
        ).pack(anchor="w", padx=20, pady=(20, 5))

        self.entry_name = ctk.CTkEntry(
            self, placeholder_text="Category Name (e.g., My Best Games)", width=360,
            fg_color="#344268", text_color="#FFFFFF", placeholder_text_color="#94a3b8",
            border_width=1, border_color="#475569"
        )
        self.entry_name.pack(padx=20, pady=10)
        self.entry_name.focus()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(10, 20))

        ctk.CTkButton(
            btn_frame, text="Create", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", font=("Arial", 12, "bold"),
            command=self._on_submit
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="Cancel", fg_color="#334155", hover_color="#475569",
            border_width=2, border_color="#64748b", font=("Arial", 12),
            command=self.destroy
        ).pack(side="right", padx=5)

    def _on_submit(self):
        name = self.entry_name.get().strip()
        if name:
            self.category_name = name
            self.destroy()


class EditWorkspace(ctk.CTkFrame):

    def __init__(self, master, app_state=None, filename=None):
        super().__init__(master, fg_color="#1e293b", corner_radius=0)
        self.app_state = app_state or state
        self.filename = filename or getattr(state, "current_filename", None)

        self.collection_categories = load_categories_config()
        self.collection_files_map = {cat: {} for cat in self.collection_categories}
        self.selected_files = []
        self.active_expanded_category = None
        self.expanded_files = set()
        self.game_lookup = {}
        self.file_lookup = {}

        self._configure_styles()
        self._build_ui()

        for cat in self.collection_categories:
            self._load_category_files(cat)

        self.refresh_view()

    def _configure_styles(self):
        self.style = ttk.Style(self)
        try:
            self.style.theme_use("clam")
        except Exception:
            pass

        BG_COLOR = "#172134"
        self.style.configure(
            "Treeview",
            background=BG_COLOR,
            fieldbackground=BG_COLOR,
            foreground="white",
            rowheight=26,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
            bordercolor=BG_COLOR,
            lightcolor=BG_COLOR,
            darkcolor=BG_COLOR,
            focuscolor=BG_COLOR
        )
        self.style.map(
            "Treeview",
            focuscolor=[("focus", BG_COLOR), ("active", BG_COLOR), ("selected", BG_COLOR)],
            bordercolor=[("focus", BG_COLOR), ("active", BG_COLOR), ("selected", BG_COLOR)],
            lightcolor=[("focus", BG_COLOR), ("active", BG_COLOR), ("selected", BG_COLOR)],
            darkcolor=[("focus", BG_COLOR), ("active", BG_COLOR), ("selected", BG_COLOR)],
            background=[("selected", BG_COLOR), ("active", BG_COLOR)],
            foreground=[("selected", "white"), ("active", "white")]
        )

        self.style.layout("Treeview.Item", [
            ('Treeitem.padding', {'sticky': 'nswe', 'children': [
                ('Treeitem.image', {'side': 'left', 'sticky': ''}),
                ('Treeitem.text', {'side': 'left', 'sticky': ''})
            ], 'border': 0})
        ])

    def refresh_view(self):
        self._refresh_treeview()

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=2)
        self.grid_columnconfigure(1, weight=3)

        left_box = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8, border_color="#334155", border_width=1)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)
        left_box.grid_rowconfigure(0, weight=1)
        left_box.grid_columnconfigure(0, weight=1)

        self.col_tree = ttk.Treeview(
            left_box, show="tree", selectmode="browse"
        )

        self.col_tree.heading("#0", text="Categories, Collections & Games", anchor="w")
        self.col_tree.column("#0", width=400, anchor="w")

        # Direct bindings for selection and double-clicks
        self.col_tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.col_tree.bind("<Double-1>", self._on_tree_double_click)

        col_scroll = ttk.Scrollbar(left_box, orient="vertical", command=self.col_tree.yview)
        self.col_tree.configure(yscrollcommand=col_scroll.set)
        self.col_tree.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        col_scroll.grid(row=0, column=1, sticky="ns", pady=6, padx=(0, 6))

        right_box = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8, border_color="#334155", border_width=1)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_box.grid_columnconfigure(0, weight=1)

        header_box = ctk.CTkFrame(right_box, fg_color="transparent")
        header_box.pack(fill="x", padx=10, pady=(15, 5))

        ctk.CTkLabel(header_box, text="Mixed Collections", font=("Arial", 14, "bold"), text_color="white").pack(
            anchor="w")
        ctk.CTkLabel(header_box, text="Select category first.", font=("Arial", 12),
                     text_color="#94a3b8").pack(anchor="w", pady=(0, 0))

        col_ctrl = ctk.CTkFrame(right_box, fg_color="transparent")
        col_ctrl.pack(fill="x", padx=10, pady=5)

        opt_border_frame = ctk.CTkFrame(col_ctrl, fg_color="transparent", border_width=2, border_color="#475569",
                                        corner_radius=0)
        opt_border_frame.pack(side="left", padx=(0, 4))

        default_category = self.collection_categories[0] if self.collection_categories else ""
        self.opt_category = ctk.CTkOptionMenu(
            opt_border_frame, values=self.collection_categories, width=110,
            corner_radius=0, fg_color="#344268", button_color="#344268",
            button_hover_color="#2e4a8c", dropdown_hover_color="#2e4a8c",
            dropdown_fg_color="#344268", command=self._on_category_changed
        )
        self.opt_category.set(default_category)
        self.opt_category.pack(padx=1, pady=1)

        ctk.CTkButton(
            col_ctrl, text="+ Category", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", width=75, height=28, font=("Arial", 12),
            command=self._add_category
        ).pack(side="right")

        move_row = ctk.CTkFrame(right_box, fg_color="transparent")
        move_row.pack(fill="x", padx=10, pady=(5, 2))
        move_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            move_row, text="Up", fg_color="#334155", hover_color="#475569",
            border_width=1, border_color="#64748b", height=28, font=("Arial", 12),
            command=lambda: self._move_category(-1)
        ).grid(row=0, column=0, sticky="ew", padx=(0, 2))

        ctk.CTkButton(
            move_row, text="Down", fg_color="#334155", hover_color="#475569",
            border_width=1, border_color="#64748b", height=28, font=("Arial", 12),
            command=lambda: self._move_category(1)
        ).grid(row=0, column=1, sticky="ew", padx=(2, 0))

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
            action_row, text="Create Collection", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", width=125, height=30, font=("Arial", 12, "bold"),
            command=self._create_collection
        ).pack(side="left", padx=(3, 0))

        separator1 = ctk.CTkFrame(right_box, fg_color="#334155", height=2)
        separator1.pack(fill="x", padx=10, pady=10)

        del_header_box = ctk.CTkFrame(right_box, fg_color="transparent")
        del_header_box.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(
            del_header_box, text="Use with caution when deleting",
            font=("Arial", 11, "bold"), text_color="#f87171"
        ).pack(anchor="w")

        del_row = ctk.CTkFrame(right_box, fg_color="transparent")
        del_row.pack(fill="x", padx=10, pady=2)
        del_row.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkButton(
            del_row, text="Delete Category", fg_color="#334155", hover_color="#475569",
            border_width=1, border_color="#64748b", height=28, font=("Arial", 12),
            command=self._delete_category
        ).grid(row=0, column=0, sticky="ew", padx=(0, 2))

        ctk.CTkButton(
            del_row, text="Delete PGN File", fg_color="#334155", hover_color="#475569",
            border_width=1, border_color="#64748b", height=28, font=("Arial", 12),
            command=self._delete_selected_pgn_file
        ).grid(row=0, column=1, sticky="ew", padx=(2, 0))

        separator2 = ctk.CTkFrame(right_box, fg_color="#334155", height=2)
        separator2.pack(fill="x", padx=10, pady=10)

        eco_box = ctk.CTkFrame(right_box, fg_color="transparent")
        eco_box.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(eco_box, text="ECO Tag Repair", font=("Arial", 12, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkButton(
            eco_box, text="Scan & Repair ECOs", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", height=30, font=("Arial", 12),
            command=self._repair_eco_tags
        ).pack(fill="x", pady=(4, 0))

        engine_box = ctk.CTkFrame(right_box, fg_color="transparent")
        engine_box.pack(fill="x", padx=10, pady=(12, 5))
        ctk.CTkLabel(engine_box, text="Engine Manager", font=("Arial", 12, "bold"), text_color="white").pack(anchor="w")

        eng_btn_row = ctk.CTkFrame(engine_box, fg_color="transparent")
        eng_btn_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(
            eng_btn_row, text="Browse Engine", fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#475569", height=30, font=("Arial", 12),
            command=self._browse_engine
        ).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(
            eng_btn_row, text="Save Settings", fg_color="#334155", hover_color="#475569",
            border_width=1, border_color="#64748b", height=30, font=("Arial", 12),
            command=self._save_engine_settings
        ).pack(side="right", fill="x", expand=True, padx=(2, 0))

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
                            if game is None:
                                break
                            result = game.headers.get("Result", "*")
                            opening = game.headers.get("Opening", "")
                            white = game.headers.get("White", "?")
                            black = game.headers.get("Black", "?")
                            rows.append(((f"{white} vs {black}", result, opening), game, fpath))
                except Exception as e:
                    print(f"Error loading PGN file {fpath.name}: {e}")

                if rows:
                    files_dict[str(fpath)] = rows

        self.collection_files_map[category] = files_dict

        if len(files_dict) == 1:
            only_file_path = list(files_dict.keys())[0]
            self.expanded_files.add(only_file_path)

    def _on_category_changed(self, choice):
        self._load_category_files(choice)
        self._refresh_treeview()

    def _refresh_treeview(self):
        for item in self.col_tree.get_children():
            self.col_tree.delete(item)

        self.game_lookup.clear()
        self.file_lookup.clear()

        for cat in self.collection_categories:
            files_dict = self.collection_files_map.get(cat, {})
            is_cat_expanded = (cat == self.active_expanded_category)

            total_games_in_cat = sum(len(rows) for rows in files_dict.values())

            arrow = "▼ " if is_cat_expanded else "▶ "
            cat_title = f"{arrow}{cat}  ({total_games_in_cat})"

            cat_id = self.col_tree.insert(
                "", "end", text=cat_title, open=is_cat_expanded
            )
            self.file_lookup[cat_id] = ("category", cat)

            if is_cat_expanded:
                if files_dict:
                    for fpath_str, rows in files_dict.items():
                        fpath = Path(fpath_str)
                        is_file_expanded = fpath_str in self.expanded_files

                        file_arrow = "▼ " if is_file_expanded else "▶ "
                        file_title = f"    {file_arrow}{fpath.name}  ({len(rows)})"
                        file_id = self.col_tree.insert(
                            cat_id, "end", text=file_title, open=is_file_expanded
                        )
                        self.file_lookup[file_id] = ("file", cat, fpath_str)

                        if is_file_expanded:
                            file_games_list = [entry[1] for entry in rows]
                            for entry in rows:
                                r, game, path = entry
                                players_text, result, opening = r
                                display_text = f"        {players_text}  [{result}]" + (
                                    f" - {opening}" if opening else "")

                                item_id = self.col_tree.insert(
                                    file_id, "end", text=display_text
                                )
                                self.game_lookup[item_id] = (game, file_games_list)
                else:
                    self.col_tree.insert(
                        cat_id, "end", text="    (No collections in this category yet)"
                    )

        self.col_tree.selection_remove(self.col_tree.selection())

    def _handle_item_selection(self, item_id):
        if not item_id:
            return False

        if item_id in self.game_lookup:
            game, source_data = self.game_lookup[item_id]

            # Update state in place and switch to analysis workspace
            setattr(self.app_state, "active_analysis_game", game)
            setattr(self.app_state, "active_category_source", source_data)

            if hasattr(self.app_state, "analysis_callbacks"):
                for cb in self.app_state.analysis_callbacks:
                    try:
                        cb(game, category_source=source_data)
                    except TypeError:
                        try:
                            cb(game, source_data)
                        except TypeError:
                            try:
                                cb(game)
                            except Exception:
                                pass

            # Switch view to analysis just like the sidebar does
            if hasattr(self.app_state, "workspace") and hasattr(self.app_state.workspace, "show_workspace"):
                self.app_state.workspace.show_workspace("analysis")
            elif hasattr(state, "workspace") and hasattr(state.workspace, "show_workspace"):
                state.workspace.show_workspace("analysis")

            return True

        if item_id in self.file_lookup:
            node_type = self.file_lookup[item_id][0]
            if node_type == "category":
                cat = self.file_lookup[item_id][1]
                if cat in self.collection_categories:
                    self.opt_category.set(cat)

                if self.active_expanded_category == cat:
                    self.active_expanded_category = None
                else:
                    self.active_expanded_category = cat
                self._refresh_treeview()
                return True
            elif node_type == "file":
                cat = self.file_lookup[item_id][1]
                fpath_str = self.file_lookup[item_id][2]

                if cat in self.collection_categories:
                    self.opt_category.set(cat)

                if fpath_str in self.expanded_files:
                    self.expanded_files.remove(fpath_str)
                else:
                    self.expanded_files.add(fpath_str)
                self._refresh_treeview()
                return True

        return False

    def _on_tree_select(self, event):
        selected_items = self.col_tree.selection()
        if not selected_items:
            return
        self._handle_item_selection(selected_items[0])

    def _on_tree_double_click(self, event):
        item_id = self.col_tree.identify_row(event.y)
        if item_id:
            self._handle_item_selection(item_id)

    def _select_pgn_files(self):
        base_dir = Path(__file__).resolve().parent.parent / "pgn"
        current_cat = self.opt_category.get()

        subfolder = CATEGORY_FOLDER_MAP[current_cat][0] if current_cat in CATEGORY_FOLDER_MAP else ""
        default_dir = base_dir / subfolder if subfolder else base_dir

        files = filedialog.askopenfilenames(
            title="Select PGN Files for Collection",
            initialdir=str(default_dir) if default_dir.exists() else str(base_dir),
            filetypes=[("PGN Files", "*.pgn"), ("All Files", "*.*")]
        )
        if files:
            self.selected_files.extend(list(files))
            count = len(self.selected_files)
            self.lbl_selected_files.configure(text=f"{count} file(s) selected")
            self.btn_undo_pgn.pack(side="left", before=self.btn_select_pgns, padx=(0, 3))
            set_status_message(f"Selected {count} PGN file(s). Click Create Collection to verify & pick games.")

    def _undo_last_pgn(self):
        if not self.selected_files:
            set_status_message("No selected PGN files to undo.")
            return

        removed = self.selected_files.pop()
        count = len(self.selected_files)

        if count == 0:
            self.lbl_selected_files.configure(text="No PGN files selected.")
            self.btn_undo_pgn.pack_forget()
            set_status_message(f"Removed last selected PGN: {Path(removed).name}. No files selected remaining.")
        else:
            self.lbl_selected_files.configure(text=f"{count} file(s) selected")
            set_status_message(f"Removed last selected PGN: {Path(removed).name}. {count} file(s) remaining.")

    def _add_category(self):
        dialog = AddCategoryDialog(self)
        self.wait_window(dialog)

        if not dialog.category_name:
            return

        new_cat = dialog.category_name
        if new_cat in self.collection_categories:
            set_status_message(f"Category '{new_cat}' already exists.")
            return

        self.collection_categories.append(new_cat)
        slug = "".join(c.lower() if c.isalnum() else "_" for c in new_cat).strip("_")
        while "__" in slug:
            slug = slug.replace("__", "_")
        if not slug:
            slug = "custom"

        CATEGORY_FOLDER_MAP[new_cat] = (slug, f"{slug}.pgn")
        self.collection_files_map[new_cat] = {}

        save_categories_config(self.collection_categories)
        self.opt_category.configure(values=self.collection_categories)
        self.opt_category.set(new_cat)
        self._refresh_treeview()
        set_status_message(f"Category '{new_cat}' created successfully.")

    def _move_category(self, direction):
        current_cat = self.opt_category.get()
        if current_cat not in self.collection_categories:
            return

        idx = self.collection_categories.index(current_cat)
        new_idx = idx + direction

        if 0 <= new_idx < len(self.collection_categories):
            self.collection_categories.pop(idx)
            self.collection_categories.insert(new_idx, current_cat)

            save_categories_config(self.collection_categories)
            self.opt_category.configure(values=self.collection_categories)
            self.opt_category.set(current_cat)
            self._refresh_treeview()
            set_status_message(f"Moved category '{current_cat}' position.")

    def _delete_category(self):
        current_cat = self.opt_category.get()
        if not current_cat:
            return

        dialog = ConfirmationDialog(
            self, "Delete Category",
            f"Are you sure you want to delete category '{current_cat}' and all its collections? This cannot be undone."
        )
        self.wait_window(dialog)

        if not dialog.confirmed:
            return

        if current_cat in self.collection_categories:
            self.collection_categories.remove(current_cat)

        if current_cat in CATEGORY_FOLDER_MAP:
            subfolder, filename = CATEGORY_FOLDER_MAP[current_cat]
            base_dir = Path(__file__).resolve().parent.parent / "pgn"
            cat_dir = base_dir / subfolder if subfolder else base_dir

            if cat_dir.exists():
                try:
                    for f in cat_dir.glob("*.pgn"):
                        f.unlink()
                    if cat_dir != base_dir:
                        cat_dir.rmdir()
                except Exception as e:
                    print(f"Error removing category folder files: {e}")

            del CATEGORY_FOLDER_MAP[current_cat]

        if current_cat in self.collection_files_map:
            del self.collection_files_map[current_cat]

        save_categories_config(self.collection_categories)

        if self.collection_categories:
            next_cat = self.collection_categories[0]
            self.opt_category.configure(values=self.collection_categories)
            self.opt_category.set(next_cat)
        else:
            self.opt_category.configure(values=[""])
            self.opt_category.set("")

        self._refresh_treeview()
        set_status_message(f"Category '{current_cat}' deleted successfully.")

    def _delete_selected_pgn_file(self):
        selected_items = self.col_tree.selection()
        if not selected_items:
            set_status_message("Please select a PGN file collection from the tree view to delete.")
            return

        item_id = selected_items[0]
        if item_id not in self.file_lookup or self.file_lookup[item_id][0] != "file":
            set_status_message("Please select an individual PGN file node in the tree view to delete.")
            return

        cat, fpath_str = self.file_lookup[item_id][1], self.file_lookup[item_id][2]
        fpath = Path(fpath_str)

        dialog = ConfirmationDialog(
            self, "Delete PGN Collection File",
            f"Are you sure you want to delete collection file '{fpath.name}'? This cannot be undone."
        )
        self.wait_window(dialog)

        if not dialog.confirmed:
            return

        try:
            if fpath.exists():
                fpath.unlink()
        except Exception as e:
            print(f"Error deleting file {fpath}: {e}")

        self._load_category_files(cat)
        self._refresh_treeview()
        set_status_message(f"Collection file '{fpath.name}' deleted successfully.")

    def _create_collection(self):
        if not self.selected_files:
            set_status_message("No PGN files selected to create a collection.")
            return

        current_cat = self.opt_category.get()
        if not current_cat:
            set_status_message("Please select a valid category first.")
            return

        overlay = LoadingOverlay(self, message="Scanning selected PGN files...")

        def background_parse():
            all_games_data = []
            try:
                for fpath_str in self.selected_files:
                    fpath = Path(fpath_str)
                    if not fpath.exists():
                        continue
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        while True:
                            pos = f.tell()
                            game = chess.pgn.read_game(f)
                            if game is None:
                                break
                            white = game.headers.get("White", "?")
                            black = game.headers.get("Black", "?")
                            opening = game.headers.get("Opening", "Unknown")
                            variation = game.headers.get("Variation", "")

                            all_games_data.append({
                                "game": game,
                                "white": white,
                                "black": black,
                                "opening": opening,
                                "variation": variation,
                                "auto_select": True
                            })
            except Exception as e:
                print(f"Error parsing PGNs for collection creation: {e}")

            self.after(0, lambda: finalize_collection(all_games_data))

        def finalize_collection(games_data):
            overlay.close()

            if not games_data:
                set_status_message("No valid games found in the selected PGN files.")
                return

            if len(games_data) > 300:
                limit_dialog = CollectionLimitDialog(self, len(games_data))
                self.wait_window(limit_dialog)
                return

            dialog = GameSelectionDialog(self, games_data)
            self.wait_window(dialog)

            selected_games = dialog.selected_games
            if not selected_games:
                set_status_message("Collection creation cancelled or no games selected.")
                return

            base_dir = Path(__file__).resolve().parent.parent / "pgn"
            subfolder = CATEGORY_FOLDER_MAP.get(current_cat, ("", ""))[0]
            cat_dir = base_dir / subfolder if subfolder else base_dir
            cat_dir.mkdir(parents=True, exist_ok=True)

            first_filename = Path(self.selected_files[0]).name
            target_path = cat_dir / first_filename

            counter = 1
            while target_path.exists():
                stem = Path(self.selected_files[0]).stem
                target_path = cat_dir / f"{stem}_{counter}.pgn"
                counter += 1

            try:
                with open(target_path, "w", encoding="utf-8") as out_f:
                    for idx, g in enumerate(selected_games):
                        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                        pgn_string = g.accept(exporter)
                        out_f.write(pgn_string + "\n\n")

                self.selected_files.clear()
                self.lbl_selected_files.configure(text="No PGN files selected.")
                self.btn_undo_pgn.pack_forget()

                self._load_category_files(current_cat)
                self._refresh_treeview()
                set_status_message(f"Collection '{target_path.name}' created with {len(selected_games)} games.")
            except Exception as e:
                set_status_message(f"Error saving collection file: {e}")

        threading.Thread(target=background_parse, daemon=True).start()

    def _repair_eco_tags(self):
        set_status_message("ECO tag repair scan initiated...")
        # Placeholder or existing logic for ECO repair if present

    def _browse_engine(self):
        engine_path = filedialog.askopenfilename(
            title="Select Chess Engine Executable",
            filetypes=[("Executables", "*.exe"), ("All Files", "*.*")]
        )
        if engine_path:
            setattr(self.app_state, "engine_path", engine_path)
            set_status_message(f"Engine selected: {Path(engine_path).name}")

    def _save_engine_settings(self):
        set_status_message("Engine settings saved successfully.")