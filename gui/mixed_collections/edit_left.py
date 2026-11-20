from tkinter import ttk
import customtkinter as ctk
import gui.app_state as state
from core.constants import THEME


class EditLeftMixin:
    """Handles left column UI: game table, online accounts, quick fetch, and time-control filters."""

    def _save_cc_account(self):
        username = self.entry_cc_username.get().strip()
        if not username:
            return
        self.cc_saved_username = username
        self.save_account_to_disk("chess_com", username)

        self.cc_input_row.pack_forget()
        self.btn_cc_quick.configure(text=username)
        self.cc_active_frame.pack(fill="x", pady=0)

    def _save_lich_account(self):
        username = self.entry_lich_username.get().strip()
        if not username:
            return
        self.lich_saved_username = username
        self.save_account_to_disk("lichess", username)

        self.lich_input_row.pack_forget()
        self.btn_lich_quick.configure(text=username)
        self.lich_active_frame.pack(fill="x", pady=0)

    def _build_left_column(self):
        btn_text_color = self._theme_color("text_primary", "text_secondary")

        left_box = ctk.CTkFrame(
            self,
            fg_color=THEME["bg_panel"],
            corner_radius=8,
            border_color=THEME["border_color"],
            border_width=1,
        )
        left_box.grid(row=0, column=0, sticky="nsew", padx=(8, 4), pady=8)

        left_box.grid_rowconfigure(0, weight=20)
        left_box.grid_rowconfigure(1, weight=0)
        left_box.grid_columnconfigure(0, weight=1)

        # Top Half: Game Table View
        self.tree_frame = ctk.CTkFrame(left_box, fg_color="transparent")
        self.tree_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=(6, 2))
        self.tree_frame.grid_rowconfigure(0, weight=1)
        self.tree_frame.grid_columnconfigure(0, weight=1)

        self.col_tree = ttk.Treeview(
            self.tree_frame,
            columns=("no", "white", "black", "result"),
            show="headings",
            selectmode="browse",
            takefocus=False,
            style="Borderless.Treeview",
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

        # Bottom Half: Online Accounts Panel
        account_box = ctk.CTkFrame(
            left_box,
            fg_color=THEME["bg_surface"],
            corner_radius=6,
            border_color=THEME["border_color"],
            border_width=1,
        )
        account_box.grid(row=1, column=0, sticky="nsew", padx=6, pady=(1, 4))
        account_box.grid_rowconfigure(0, weight=1)
        account_box.grid_columnconfigure(0, weight=1)

        accounts_container = ctk.CTkFrame(account_box, fg_color="transparent")
        accounts_container.grid(row=0, column=0, sticky="nsew", padx=6, pady=4)
        accounts_container.grid_columnconfigure(0, weight=1)

        columns_frame = ctk.CTkFrame(accounts_container, fg_color="transparent")
        columns_frame.pack(fill="x", expand=False)
        columns_frame.grid_columnconfigure((0, 1), weight=1)

        # ------------------- Chess.com Section (Left Column) -------------------
        cc_section = ctk.CTkFrame(columns_frame, fg_color="transparent")
        cc_section.grid(row=0, column=0, sticky="nsew", padx=4, pady=0)
        cc_section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            cc_section,
            text="Chess.com",
            font=("Arial", 14, "bold"),
            text_color=btn_text_color,
            anchor="center",
        ).pack(fill="x", pady=(0, 2))

        self.cc_input_row = ctk.CTkFrame(cc_section, fg_color="transparent")

        self.entry_cc_username = ctk.CTkEntry(
            self.cc_input_row, placeholder_text="Username...", height=30, width=160, font=("Arial", 12)
        )
        self._apply_entry_theme(self.entry_cc_username)
        self.entry_cc_username.pack(pady=(0, 6), padx=2)

        btn_cc_save = ctk.CTkButton(
            self.cc_input_row,
            text="Save",
            height=30,
            width=160,
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            font=("Arial", 12, "bold"),
            command=self._save_cc_account,
        )
        self._apply_button_theme(btn_cc_save)
        btn_cc_save.pack(pady=0, padx=2)

        self.cc_active_frame = ctk.CTkFrame(cc_section, fg_color="transparent")

        self.btn_cc_quick = ctk.CTkButton(
            self.cc_active_frame,
            text="",
            width=160,
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            height=28,
            font=("Arial", 11, "bold"),
            anchor="center",
            command=self._quick_fetch_cc_last,
        )
        self._apply_button_theme(self.btn_cc_quick)
        self.btn_cc_quick.pack(pady=(0, 2), padx=2)

        cc_filter_container = ctk.CTkFrame(self.cc_active_frame, fg_color="transparent")
        cc_filter_container.pack(anchor="center", padx=(40, 0), pady=0)
        cc_filter_container.grid_columnconfigure(0, weight=1)
        cc_filter_container.grid_columnconfigure(1, weight=1)

        cc_col_left = ctk.CTkFrame(cc_filter_container, fg_color="transparent")
        cc_col_left.grid(row=0, column=0, sticky="n", padx=(0, 4))

        cc_col_right = ctk.CTkFrame(cc_filter_container, fg_color="transparent")
        cc_col_right.grid(row=0, column=1, sticky="n", padx=(4, 0))

        self.cc_box_labels = {}
        for mode in ("Blitz", "Rapid", "Standard"):
            var = ctk.BooleanVar(value=self.cc_filters.get(mode, False))
            chk = ctk.CTkCheckBox(
                cc_col_left,
                text=mode,
                variable=var,
                font=("Arial", 10, "bold"),
                checkbox_width=14,
                checkbox_height=14,
                border_width=1,
                corner_radius=2,
                command=lambda m=mode: self._toggle_cc_filter(m),
            )
            self._apply_checkbox_theme(chk)
            chk.pack(anchor="w", pady=1)
            self.cc_box_labels[mode] = chk

        all_mode = "All"
        all_var = ctk.BooleanVar(value=self.cc_filters.get(all_mode, False))
        all_chk = ctk.CTkCheckBox(
            cc_col_right,
            text=all_mode,
            variable=all_var,
            font=("Arial", 10, "bold"),
            checkbox_width=14,
            checkbox_height=14,
            border_width=1,
            corner_radius=2,
            command=lambda m=all_mode: self._toggle_cc_filter(m),
        )
        self._apply_checkbox_theme(all_chk)
        all_chk.pack(anchor="w", pady=1)
        self.cc_box_labels[all_mode] = all_chk

        btn_cc_100 = ctk.CTkButton(
            cc_col_right,
            text="100",
            width=65,
            height=24,
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            font=("Arial", 10, "bold"),
            command=self._batch_cc_download,
        )
        self._apply_button_theme(btn_cc_100)
        btn_cc_100.pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(columns_frame, fg_color=THEME["divider"], width=1).grid(
            row=0, column=0, sticky="nse", padx=0, pady=2
        )

        # ------------------- Lichess.org Section (Right Column) -------------------
        lich_section = ctk.CTkFrame(columns_frame, fg_color="transparent")
        lich_section.grid(row=0, column=1, sticky="nsew", padx=4, pady=0)
        lich_section.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            lich_section,
            text="Lichess.org",
            font=("Arial", 14, "bold"),
            text_color=btn_text_color,
            anchor="center",
        ).pack(fill="x", pady=(0, 2))

        self.lich_input_row = ctk.CTkFrame(lich_section, fg_color="transparent")

        self.entry_lich_username = ctk.CTkEntry(
            self.lich_input_row, placeholder_text="Username...", height=30, width=160, font=("Arial", 12)
        )
        self._apply_entry_theme(self.entry_lich_username)
        self.entry_lich_username.pack(pady=(0, 6), padx=2)

        btn_lich_save = ctk.CTkButton(
            self.lich_input_row,
            text="Save",
            height=30,
            width=160,
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            font=("Arial", 12, "bold"),
            command=self._save_lich_account,
        )
        self._apply_button_theme(btn_lich_save)
        btn_lich_save.pack(pady=0, padx=2)

        self.lich_active_frame = ctk.CTkFrame(lich_section, fg_color="transparent")

        self.btn_lich_quick = ctk.CTkButton(
            self.lich_active_frame,
            text="",
            width=160,
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            height=28,
            font=("Arial", 11, "bold"),
            anchor="center",
            command=self._quick_fetch_lich_last,
        )
        self._apply_button_theme(self.btn_lich_quick)
        self.btn_lich_quick.pack(pady=(0, 2), padx=2)

        lich_filter_container = ctk.CTkFrame(self.lich_active_frame, fg_color="transparent")
        lich_filter_container.pack(anchor="center", padx=(28, 0), pady=0)
        lich_filter_container.grid_columnconfigure(0, weight=1)
        lich_filter_container.grid_columnconfigure(1, weight=1)

        lich_col_left = ctk.CTkFrame(lich_filter_container, fg_color="transparent")
        lich_col_left.grid(row=0, column=0, sticky="n", padx=(0, 4))

        lich_col_right = ctk.CTkFrame(lich_filter_container, fg_color="transparent")
        lich_col_right.grid(row=0, column=1, sticky="n", padx=(4, 0))

        self.lich_box_labels = {}
        for mode in ("Blitz", "Rapid", "Standard"):
            var = ctk.BooleanVar(value=self.lich_filters.get(mode, False))
            chk = ctk.CTkCheckBox(
                lich_col_left,
                text=mode,
                variable=var,
                font=("Arial", 10, "bold"),
                checkbox_width=14,
                checkbox_height=14,
                border_width=1,
                corner_radius=2,
                command=lambda m=mode: self._toggle_lich_filter(m),
            )
            self._apply_checkbox_theme(chk)
            chk.pack(anchor="w", pady=1)
            self.lich_box_labels[mode] = chk

        all_mode = "All"
        all_var = ctk.BooleanVar(value=self.lich_filters.get(all_mode, False))
        all_chk = ctk.CTkCheckBox(
            lich_col_right,
            text=all_mode,
            variable=all_var,
            font=("Arial", 10, "bold"),
            checkbox_width=14,
            checkbox_height=14,
            border_width=1,
            corner_radius=2,
            command=lambda m=all_mode: self._toggle_lich_filter(m),
        )
        self._apply_checkbox_theme(all_chk)
        all_chk.pack(anchor="w", pady=1)
        self.lich_box_labels[all_mode] = all_chk

        btn_lich_100 = ctk.CTkButton(
            lich_col_right,
            text="100",
            width=65,
            height=24,
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=btn_text_color,
            font=("Arial", 10, "bold"),
            command=self._batch_lich_download,
        )
        self._apply_button_theme(btn_lich_100)
        btn_lich_100.pack(anchor="w", pady=(2, 0))

        if getattr(self, "cc_saved_username", None):
            self.btn_cc_quick.configure(text=self.cc_saved_username)
            self.cc_active_frame.pack(fill="x", pady=0)
        else:
            self.cc_input_row.pack(fill="x", pady=0)

        if getattr(self, "lich_saved_username", None):
            self.btn_lich_quick.configure(text=self.lich_saved_username)
            self.lich_active_frame.pack(fill="x", pady=0)
        else:
            self.lich_input_row.pack(fill="x", pady=0)

        ctk.CTkLabel(
            accounts_container,
            text="1) Type the username and press 'Save'.\n2) Select time controls or 'ALL' and press '100'.\n3) Click Username to just get last game played.",
            font=("Arial", 11, "bold"),
            text_color=THEME["text_secondary"],
            justify="center",
        ).pack(fill="x", pady=(2, 4))

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
                active_index=selected_index,
            )
        else:
            print("[DEBUG] Error: top_level window has no show_workspace method.")