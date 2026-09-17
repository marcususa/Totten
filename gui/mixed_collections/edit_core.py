from tkinter import ttk
import customtkinter as ctk

import gui.app_state as state

from gui.mixed_collections.edit_navigation import EditNavigationMixin
from gui.mixed_collections.edit_engine import EditEngineMixin
from gui.mixed_collections.edit_constants import load_categories_config


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


class EditWorkspace(ctk.CTkFrame, EditNavigationMixin, EditEngineMixin):

    def __init__(self, master, initial_games=None, filename=None, *args, **kwargs):
        super().__init__(master, fg_color="#0f172a", corner_radius=0)

        self.categories = load_categories_config()
        print(f"[DEBUG INIT] EditWorkspace loaded categories: {self.categories}")

        self.collection_files = {}
        self.selected_files = []
        self.tree_map = {}
        self.cat_item_map = {}

        # Initialize base state values before UI building
        numbered_cats = self._get_numbered_categories()
        self._selected_category = numbered_cats[0] if numbered_cats else ""

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
            background=[("selected", "#344268"), ("focus", "#1e293b"), ("active", "#1e293b")],
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
        left_box = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=8, border_color="#344268", border_width=1)
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
        right_box = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=8, border_color="#344268", border_width=1)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_box.grid_columnconfigure(0, weight=1)

        header_box = ctk.CTkFrame(right_box, fg_color="transparent")
        header_box.pack(fill="x", padx=10, pady=(15, 5))
        ctk.CTkLabel(header_box, text="Mixed Collections", font=("Arial", 14, "bold"), text_color="#f8fafc").pack(anchor="w")
        ctk.CTkLabel(header_box, text="Select category first.", font=("Arial", 12), text_color="#94a3b8").pack(anchor="w")

        # Adapter setup for category selection compatibility
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

        # Category List Box
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

        # Populate categories tree view
        self._refresh_categories_list()

        btn_add_cat = ctk.CTkButton(
            right_box,
            text="+ Category",
            fg_color="#344268",
            hover_color="#2e4a8c",
            border_width=0,
            height=28,
            font=("Arial", 12),
            command=self._add_category
        )
        btn_add_cat.pack(fill="x", padx=10, pady=(4, 5))

        move_row = ctk.CTkFrame(right_box, fg_color="transparent")
        move_row.pack(fill="x", padx=10, pady=(5, 2))
        move_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(move_row, text="Up", fg_color="#344268", hover_color="#2e4a8c", border_width=0,
                      height=28, font=("Arial", 12),
                      command=lambda: self._move_category(-1)).grid(row=0, column=0, sticky="ew", padx=(0, 2))
        ctk.CTkButton(move_row, text="Down", fg_color="#344268", hover_color="#2e4a8c", border_width=0,
                      height=28, font=("Arial", 12),
                      command=lambda: self._move_category(1)).grid(row=0, column=1, sticky="ew", padx=(2, 0))

        info_row = ctk.CTkFrame(right_box, fg_color="transparent")
        info_row.pack(fill="x", padx=10, pady=(5, 2))
        self.lbl_selected_files = ctk.CTkLabel(info_row, text="No PGN files selected.", font=("Arial", 12),
                                               text_color="#94a3b8", anchor="w")
        self.lbl_selected_files.pack(side="left", anchor="w")

        action_row = ctk.CTkFrame(right_box, fg_color="transparent")
        action_row.pack(fill="x", padx=10, pady=(2, 10))

        self.btn_undo_pgn = ctk.CTkButton(
            action_row, text="✕", fg_color="#344268", hover_color="#2e4a8c",
            border_width=0, width=26, height=30, font=("Arial", 12, "bold"),
            text_color="#f8fafc", command=self._undo_last_pgn
        )

        self.btn_select_pgns = ctk.CTkButton(
            action_row, text="Select PGNs", fg_color="#344268", hover_color="#2e4a8c",
            border_width=0, width=95, height=30, font=("Arial", 12),
            command=self._select_pgn_files
        )
        self.btn_select_pgns.pack(side="left", padx=(0, 3))

        ctk.CTkButton(
            action_row, text="+ Collection", fg_color="#344268", hover_color="#2e4a8c",
            border_width=0, width=125, height=30, font=("Arial", 12, "bold"),
            command=self._create_collection
        ).pack(side="left", padx=(3, 0))

        separator1 = ctk.CTkFrame(right_box, fg_color="#344268", height=2)
        separator1.pack(fill="x", padx=10, pady=10)

        del_header = ctk.CTkFrame(right_box, fg_color="transparent")
        del_header.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(del_header, text="Use with caution when deleting", font=("Arial", 11, "bold"),
                     text_color="#94a3b8").pack(anchor="w")

        del_row = ctk.CTkFrame(right_box, fg_color="transparent")
        del_row.pack(fill="x", padx=10, pady=2)
        del_row.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(
            del_row,
            text="Delete Category",
            fg_color="#344268",
            hover_color="#2e4a8c",
            border_width=0,
            height=28,
            font=("Arial", 12),
            anchor="center",
            command=self._delete_category
        ).grid(row=0, column=0, sticky="ew", padx=(0, 2))

        separator2 = ctk.CTkFrame(right_box, fg_color="#344268", height=2)
        separator2.pack(fill="x", padx=10, pady=10)

        eco_box = ctk.CTkFrame(right_box, fg_color="transparent")
        eco_box.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(eco_box, text="ECO Tag Repair", font=("Arial", 12, "bold"), text_color="#f8fafc").pack(anchor="w")
        ctk.CTkButton(eco_box, text="Scan & Repair ECOs", fg_color="#344268", hover_color="#2e4a8c", border_width=0,
                      height=30, font=("Arial", 12), command=self._repair_eco_tags).pack(fill="x", pady=(4, 0))

        engine_box = ctk.CTkFrame(right_box, fg_color="transparent")
        engine_box.pack(fill="x", padx=10, pady=(12, 5))
        ctk.CTkLabel(engine_box, text="Engine Manager", font=("Arial", 12, "bold"), text_color="#f8fafc").pack(anchor="w")
        eng_row = ctk.CTkFrame(engine_box, fg_color="transparent")
        eng_row.pack(fill="x", pady=(4, 0))
        ctk.CTkButton(eng_row, text="Browse Engine", fg_color="#344268", hover_color="#2e4a8c", border_width=0,
                      height=30, font=("Arial", 12), command=self._browse_engine).pack(side="left", fill="x", expand=True, padx=(0, 2))
        ctk.CTkButton(eng_row, text="Save Settings", fg_color="#344268", hover_color="#2e4a8c", border_width=0,
                      height=30, font=("Arial", 12), command=self._save_engine_settings).pack(side="right", fill="x", expand=True, padx=(2, 0))

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


def create_workspace(master, *args, **kwargs):
    """Instantiates EditWorkspace for Stage 1 Mixed Collections navigation."""
    return EditWorkspace(master, *args, **kwargs)