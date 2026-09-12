from tkinter import ttk
import customtkinter as ctk

import gui.app_state as state

from gui.mixed_collections.edit_navigation import EditNavigationMixin
from gui.mixed_collections.edit_engine import EditEngineMixin
from gui.mixed_collections.edit_constants import load_categories_config


class EditWorkspace(ctk.CTkFrame, EditNavigationMixin, EditEngineMixin):

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
            self.after(50, self.load_catalog_data)
        elif self.games_list:
            self.after(50, lambda: self.load_games_list(self.games_list))
        else:
            def lazy_load():
                raw_choice = self.opt_category.get()
                cat = self._unnumber_category(raw_choice)
                self._load_category_files(cat)
                self._refresh_treeview()

            self.after(50, lazy_load)

        # Clear out state bucket after consumption
        state.mixed_state["active_games"] = None
        state.mixed_state["active_focus"] = None
        state.mixed_state["current_filename"] = None

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
        ctk.CTkLabel(header_box, text="Mixed Collections", font=("Arial", 14, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkLabel(header_box, text="Select category first.", font=("Arial", 12), text_color="#94a3b8").pack(anchor="w")

        col_ctrl = ctk.CTkFrame(right_box, fg_color="transparent")
        col_ctrl.pack(fill="x", padx=10, pady=5)

        opt_border = ctk.CTkFrame(col_ctrl, fg_color="transparent", border_width=2, border_color="#475569", corner_radius=0)
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
                      border_color="#475569", width=75, height=28, font=("Arial", 12), command=self._add_category).pack(side="right")

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
                      border_color="#64748b", height=28, font=("Arial", 12), command=self._delete_category).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ctk.CTkButton(del_row, text="Delete PGN File", fg_color="#334155", hover_color="#475569", border_width=1,
                      border_color="#64748b", height=28, font=("Arial", 12),
                      command=self._delete_selected_pgn_file).grid(row=0, column=1, sticky="ew", padx=(2, 0))

        separator2 = ctk.CTkFrame(right_box, fg_color="#334155", height=2)
        separator2.pack(fill="x", padx=10, pady=10)

        eco_box = ctk.CTkFrame(right_box, fg_color="transparent")
        eco_box.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(eco_box, text="ECO Tag Repair", font=("Arial", 12, "bold"), text_color="white").pack(anchor="w")
        ctk.CTkButton(eco_box, text="Scan & Repair ECOs", fg_color="#344268", hover_color="#2e4a8c", border_width=2,
                          border_color="#475569", height=30, font=("Arial", 12), command=self._repair_eco_tags).pack(fill="x", pady=(4, 0))

        engine_box = ctk.CTkFrame(right_box, fg_color="transparent")
        engine_box.pack(fill="x", padx=10, pady=(12, 5))
        ctk.CTkLabel(engine_box, text="Engine Manager", font=("Arial", 12, "bold"), text_color="white").pack(anchor="w")
        eng_row = ctk.CTkFrame(engine_box, fg_color="transparent")
        eng_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(eng_row, text="Browse Engine", fg_color="#344268", hover_color="#2e4a8c", border_width=2,
                      border_color="#475569", height=30, font=("Arial", 12), command=self._browse_engine).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(eng_row, text="Save Settings", fg_color="#334155", hover_color="#475569", border_width=1,
                      border_color="#64748b", height=30, font=("Arial", 12), command=self._save_engine_settings).pack(side="right", fill="x", expand=True, padx=(2, 0))

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


def create_workspace(master, *args, **kwargs):
    """Instantiates EditWorkspace for Stage 1 Mixed Collections navigation."""
    return EditWorkspace(master, *args, **kwargs)