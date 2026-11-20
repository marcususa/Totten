from tkinter import ttk
import customtkinter as ctk
from core.constants import THEME


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


class EditRightMixin:
    """Handles right column UI: categories, PGN selection, ECO repair, and engine controls."""

    def _build_right_column(self):
        btn_text_color = self._theme_color("text_primary", "text_secondary")

        right_box = ctk.CTkFrame(
            self,
            fg_color=THEME["bg_surface"],
            corner_radius=8,
            border_color=THEME["border_color"],
            border_width=1,
        )
        right_box.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        right_box.grid_columnconfigure(0, weight=1)

        header_box = ctk.CTkFrame(right_box, fg_color="transparent")
        header_box.pack(fill="x", padx=10, pady=(15, 5))
        ctk.CTkLabel(
            header_box, text="Mixed Collections", font=("Arial", 14, "bold"), text_color=btn_text_color
        ).pack(anchor="w")
        ctk.CTkLabel(
            header_box, text="Select category first.", font=("Arial", 12), text_color=THEME["text_secondary"]
        ).pack(anchor="w")

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
            height=6,
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
            right_box,
            text="+ Category",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            height=28,
            font=("Arial", 12),
            command=self._add_category,
        )
        self._apply_button_theme(btn_add_cat)
        btn_add_cat.pack(fill="x", padx=10, pady=(4, 5))

        move_row = ctk.CTkFrame(right_box, fg_color="transparent")
        move_row.pack(fill="x", padx=10, pady=(5, 2))
        move_row.grid_columnconfigure((0, 1), weight=1)
        btn_up = ctk.CTkButton(
            move_row,
            text="Up",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            height=28,
            font=("Arial", 12),
            command=lambda: self._move_category(-1),
        )
        self._apply_button_theme(btn_up)
        btn_up.grid(row=0, column=0, sticky="ew", padx=(0, 2))

        btn_down = ctk.CTkButton(
            move_row,
            text="Down",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            height=28,
            font=("Arial", 12),
            command=lambda: self._move_category(1),
        )
        self._apply_button_theme(btn_down)
        btn_down.grid(row=0, column=1, sticky="ew", padx=(2, 0))

        info_row = ctk.CTkFrame(right_box, fg_color="transparent")
        info_row.pack(fill="x", padx=10, pady=(5, 2))
        self.lbl_selected_files = ctk.CTkLabel(
            info_row, text="No PGN files selected.", font=("Arial", 12), text_color=THEME["text_secondary"], anchor="w"
        )
        self.lbl_selected_files.pack(side="left", anchor="w")

        action_row = ctk.CTkFrame(right_box, fg_color="transparent")
        action_row.pack(fill="x", padx=10, pady=(2, 10))

        self.btn_undo_pgn = ctk.CTkButton(
            action_row,
            text="✕",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            border_width=0,
            width=26,
            height=30,
            font=("Arial", 12, "bold"),
            text_color=btn_text_color,
            command=self._undo_last_pgn,
        )
        self._apply_button_theme(self.btn_undo_pgn)

        self.btn_select_pgns = ctk.CTkButton(
            action_row,
            text="Select PGNs",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            width=95,
            height=30,
            font=("Arial", 12),
            command=self._select_pgn_files,
        )
        self._apply_button_theme(self.btn_select_pgns)
        self.btn_select_pgns.pack(side="left", padx=(0, 3))

        btn_add_col = ctk.CTkButton(
            action_row,
            text="+ Collection",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            width=125,
            height=30,
            font=("Arial", 12),
            command=self._create_collection,
        )
        self._apply_button_theme(btn_add_col)
        btn_add_col.pack(side="left", padx=(3, 0))

        separator1 = ctk.CTkFrame(right_box, fg_color=THEME["divider"], height=2)
        separator1.pack(fill="x", padx=10, pady=10)

        del_header = ctk.CTkFrame(right_box, fg_color="transparent")
        del_header.pack(fill="x", padx=10, pady=(0, 4))
        ctk.CTkLabel(
            del_header, text="Use with caution when deleting", font=("Arial", 11, "bold"), text_color=THEME["text_secondary"]
        ).pack(anchor="w")

        del_row = ctk.CTkFrame(right_box, fg_color="transparent")
        del_row.pack(fill="x", padx=10, pady=2)
        del_row.grid_columnconfigure((0, 1), weight=1)
        btn_del_cat = ctk.CTkButton(
            del_row,
            text="Delete Category",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            height=28,
            font=("Arial", 12),
            anchor="center",
            command=self._delete_category,
        )
        self._apply_button_theme(btn_del_cat)
        btn_del_cat.grid(row=0, column=0, sticky="ew", padx=(0, 2))

        separator2 = ctk.CTkFrame(right_box, fg_color=THEME["divider"], height=2)
        separator2.pack(fill="x", padx=10, pady=10)

        eco_box = ctk.CTkFrame(right_box, fg_color="transparent")
        eco_box.pack(fill="x", padx=10, pady=2)
        ctk.CTkLabel(eco_box, text="ECO Tag Repair", font=("Arial", 12, "bold"), text_color=btn_text_color).pack(
            anchor="w"
        )
        btn_eco = ctk.CTkButton(
            eco_box,
            text="Scan & Repair ECOs",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            height=30,
            font=("Arial", 12),
            command=self._repair_eco_tags,
        )
        self._apply_button_theme(btn_eco)
        btn_eco.pack(fill="x", pady=(4, 0))

        engine_box = ctk.CTkFrame(right_box, fg_color="transparent")
        engine_box.pack(fill="x", padx=10, pady=(12, 5))
        ctk.CTkLabel(
            engine_box, text="Engine Manager", font=("Arial", 12, "bold"), text_color=btn_text_color
        ).pack(anchor="w")
        eng_row = ctk.CTkFrame(engine_box, fg_color="transparent")
        eng_row.pack(fill="x", pady=(4, 0))
        btn_browse_eng = ctk.CTkButton(
            eng_row,
            text="Browse Engine",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            height=30,
            font=("Arial", 12),
            command=self._browse_engine,
        )
        self._apply_button_theme(btn_browse_eng)
        btn_browse_eng.pack(side="left", fill="x", expand=True, padx=(0, 2))

        btn_save_eng = ctk.CTkButton(
            eng_row,
            text="Save Settings",
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            border_width=0,
            height=30,
            font=("Arial", 12),
            command=self._save_engine_settings,
        )
        self._apply_button_theme(btn_save_eng)
        btn_save_eng.pack(side="right", fill="x", expand=True, padx=(2, 0))

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