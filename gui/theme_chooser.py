import sys
import os
import customtkinter as ctk
from pathlib import Path

from .theme_data import (
    load_all_themes,
    load_user_data,
    save_user_data,
    apply_and_save_theme,
    handle_board_background_upload,
    handle_remove_board_background
)
from . import theme_view

AVAILABLE_THEMES = load_all_themes()


class ThemeChooserWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Theme Chooser & Mixer")

        self.resizable(True, True)
        self.attributes("-topmost", True)

        self.variable_groups = {
            "Background": ["bg_panel", "bg_surface"],
            "Layout": ["border_ring", "divider", "shadow_color"],
            "Text": ["text_primary"],
            "Status": ["status_text", "error_color", "success_color"],
            "Board": ["dark_square", "light_square", "highlight_square"],
            "Board Elements": ["valid_move_dot", "check_indicator", "border_color", "active_tracker_fg"],
            "Buttons": ["btn_initial", "btn_hover", "btn_active", "btn_disabled"],
            "Extras": [
                "accent_color", "link_color",
                "progress_bg", "progress_fill", "text_secondary", "eval_default"
            ]
        }

        default_group_columns = {
            "Background": 2, "Layout": 2, "Text": 2, "Status": 2,
            "Board": 3, "Board Elements": 3, "Buttons": 3, "Extras": 3
        }

        user_data = load_user_data()
        mixer_state = user_data.get("mixer_state", {})
        current_themes_list = user_data.get("current_themes", [])
        latest_theme = current_themes_list[0] if current_themes_list else mixer_state

        saved_hue1 = latest_theme.get("color1_hue") or mixer_state.get("color1_hue")
        saved_hue2 = latest_theme.get("color2_hue") or mixer_state.get("color2_hue")
        saved_tier1 = latest_theme.get("color1_tier") or mixer_state.get("color1_tier", "Medium")
        saved_tier2 = latest_theme.get("color2_tier") or mixer_state.get("color2_tier", "Medium")
        saved_group_cols = latest_theme.get("group_columns") or mixer_state.get("group_columns", {})
        saved_group_locks = latest_theme.get("group_locks") or mixer_state.get("group_locks", {})
        saved_var_cols = latest_theme.get("var_columns") or mixer_state.get("var_columns", {})

        hue_choices = list(AVAILABLE_THEMES.keys())
        default_hue = hue_choices[0] if hue_choices else "Red"

        self.group_columns = dict(default_group_columns)
        for g, col in saved_group_cols.items():
            if g in self.group_columns:
                self.group_columns[g] = col

        self.group_locked = {g: True for g in self.variable_groups}
        for g, locked in saved_group_locks.items():
            if g in self.group_locked:
                self.group_locked[g] = locked

        self.var_columns = {}
        for group_name, variables in self.variable_groups.items():
            g_col = self.group_columns[group_name]
            for var in variables:
                if not self.group_locked[group_name] and var in saved_var_cols:
                    self.var_columns[var] = saved_var_cols[var]
                else:
                    self.var_columns[var] = g_col

        self.board_tier_var = ctk.StringVar(value=saved_tier1 if saved_tier1 in ["Light", "Medium", "Dark"] else "Medium")
        self.ui_tier_var = ctk.StringVar(value=saved_tier2 if saved_tier2 in ["Light", "Medium", "Dark"] else "Medium")

        # Main Layout Container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # LEFT COLUMN: Theme Swatches Grid
        left_column = ctk.CTkFrame(main_frame, fg_color="transparent")
        left_column.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        header_frame = ctk.CTkFrame(left_column, fg_color="transparent")
        header_frame.pack(anchor="w", pady=(0, 4))
        ctk.CTkLabel(header_frame, text="Theme Colors", font=("Arial", 16, "bold")).pack(side="left")

        instruction_frame = ctk.CTkFrame(left_column, fg_color="transparent")
        instruction_frame.pack(anchor="w", pady=(0, 8))
        ctk.CTkLabel(
            instruction_frame, text="Select a theme color below, or mix combinations on the right.",
            font=("Arial", 11), text_color=("gray60", "gray70")
        ).pack(anchor="w")

        grid_container = ctk.CTkFrame(left_column, fg_color="transparent")
        grid_container.pack(fill="both", expand=False)
        for i in range(4):
            grid_container.grid_columnconfigure(i, weight=2 if i == 0 else 1)

        row_idx = 0
        tier_keys = ["Light", "Medium", "Dark"]
        for hue_name, tiers in AVAILABLE_THEMES.items():
            ctk.CTkLabel(grid_container, text=hue_name, font=("Arial", 12, "bold")).grid(row=row_idx, column=0, sticky="w", padx=5, pady=4)
            for col_offset, tier_key in enumerate(tier_keys, start=1):
                tier_data = tiers.get(tier_key)
                if tier_data and isinstance(tier_data, dict):
                    swatch_color = tier_data.get("dark_square") or tier_data.get("light_square") or "#3b82f6"
                    swatch = ctk.CTkButton(
                        grid_container, text="", width=45, height=24,
                        fg_color=swatch_color, hover_color=swatch_color,
                        border_width=2, border_color="#000000", corner_radius=4,
                        command=lambda h=hue_name, t=tier_key: self.apply_theme_live(h, t)
                    )
                    swatch.grid(row=row_idx, column=col_offset, padx=4, pady=4)
                else:
                    ctk.CTkLabel(grid_container, text="—", font=("Arial", 11), text_color="gray").grid(row=row_idx, column=col_offset, padx=4, pady=4)
            row_idx += 1

        # RIGHT COLUMN: Mixer Controls & Variables
        right_column = ctk.CTkFrame(main_frame, fg_color="transparent")
        right_column.grid(row=0, column=1, sticky="nsew", padx=(10, 0), pady=0)
        right_column.grid_columnconfigure(0, weight=1)
        right_column.grid_columnconfigure(1, weight=1)
        right_column.grid_rowconfigure(2, weight=1)

        dropdowns_container = ctk.CTkFrame(right_column, fg_color="transparent")
        dropdowns_container.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        dropdowns_container.grid_columnconfigure(0, weight=1)
        dropdowns_container.grid_columnconfigure(1, weight=1)

        # Color 1 Dropdown & Tiers
        col2_sub = ctk.CTkFrame(dropdowns_container, fg_color="transparent")
        col2_sub.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=0)
        ctk.CTkLabel(col2_sub, text="Color 1", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 4))
        ctrl_col2 = ctk.CTkFrame(col2_sub, fg_color="transparent")
        ctrl_col2.pack(fill="x")

        self.board_combo_var = ctk.StringVar(value=saved_hue1 if saved_hue1 in hue_choices else default_hue)
        self.board_dropdown = ctk.CTkComboBox(
            ctrl_col2, values=hue_choices, variable=self.board_combo_var,
            font=("Arial", 11), height=26, width=95, command=lambda _: self.save_mixer_state()
        )
        self.board_dropdown.pack(side="left", padx=(0, 4))

        tiers_frame_col2 = ctk.CTkFrame(ctrl_col2, fg_color="transparent")
        tiers_frame_col2.pack(side="left", fill="x", expand=True)
        self.board_tier_btns = {}
        for t_code, t_name in [("L", "Light"), ("M", "Medium"), ("D", "Dark")]:
            btn = ctk.CTkButton(
                tiers_frame_col2, text=t_code, width=22, height=22, corner_radius=3,
                font=("Arial", 10, "bold"), border_width=1.5, border_color="#555555",
                command=lambda name=t_name: theme_view.set_tier(self, self.board_tier_var, name)
            )
            btn.pack(side="left", padx=2)
            self.board_tier_btns[t_name] = btn
        theme_view.update_tier_buttons(self.board_tier_var, self.board_tier_btns)

        # Color 2 Dropdown & Tiers
        col3_sub = ctk.CTkFrame(dropdowns_container, fg_color="transparent")
        col3_sub.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=0)
        ctk.CTkLabel(col3_sub, text="Color 2", font=("Arial", 14, "bold")).pack(anchor="w", pady=(0, 4))
        ctrl_col3 = ctk.CTkFrame(col3_sub, fg_color="transparent")
        ctrl_col3.pack(fill="x")

        self.ui_combo_var = ctk.StringVar(value=saved_hue2 if saved_hue2 in hue_choices else default_hue)
        self.ui_dropdown = ctk.CTkComboBox(
            ctrl_col3, values=hue_choices, variable=self.ui_combo_var,
            font=("Arial", 11), height=26, width=95, command=lambda _: self.save_mixer_state()
        )
        self.ui_dropdown.pack(side="left", padx=(0, 4))

        tiers_frame_col3 = ctk.CTkFrame(ctrl_col3, fg_color="transparent")
        tiers_frame_col3.pack(side="left", fill="x", expand=True)
        self.ui_tier_btns = {}
        for t_code, t_name in [("L", "Light"), ("M", "Medium"), ("D", "Dark")]:
            btn = ctk.CTkButton(
                tiers_frame_col3, text=t_code, width=22, height=22, corner_radius=3,
                font=("Arial", 10, "bold"), border_width=1.5, border_color="#555555",
                command=lambda name=t_name: theme_view.set_tier(self, self.ui_tier_var, name)
            )
            btn.pack(side="left", padx=2)
            self.ui_tier_btns[t_name] = btn
        theme_view.update_tier_buttons(self.ui_tier_var, self.ui_tier_btns)

        # Variable Headers & Containers
        var_headers_frame = ctk.CTkFrame(right_column, fg_color="transparent")
        var_headers_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(4, 4))
        var_headers_frame.grid_columnconfigure(0, weight=1)
        var_headers_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(var_headers_frame, text="Column 1 Variables:", font=("Arial", 11, "bold")).grid(row=0, column=0, sticky="w", padx=(0, 5))
        ctk.CTkLabel(var_headers_frame, text="Column 2 Variables:", font=("Arial", 11, "bold")).grid(row=0, column=1, sticky="w", padx=(5, 0))

        var_containers_frame = ctk.CTkFrame(right_column, fg_color="transparent")
        var_containers_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=0)
        var_containers_frame.grid_columnconfigure(0, weight=1)
        var_containers_frame.grid_columnconfigure(1, weight=1)
        var_containers_frame.grid_rowconfigure(0, weight=1)

        self.vars_container_col2 = ctk.CTkFrame(var_containers_frame, fg_color="transparent")
        self.vars_container_col2.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)
        self.vars_container_col2.grid_columnconfigure(0, weight=1)

        self.vars_container_col3 = ctk.CTkFrame(var_containers_frame, fg_color="transparent")
        self.vars_container_col3.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)
        self.vars_container_col3.grid_columnconfigure(0, weight=1)

        theme_view.populate_variable_lists(self)

        self.update_idletasks()
        window_width = self.winfo_reqwidth() + 40
        window_height = self.winfo_reqheight() + 40
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.minsize(window_width, window_height)

    def select_board_background(self):
        self.attributes("-topmost", False)
        try:
            file_path = ctk.filedialog.askopenfilename(
                title="Select Board Background Image",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")],
                parent=self
            )
        finally:
            self.attributes("-topmost", True)
        if file_path:
            handle_board_background_upload(file_path)
            python = sys.executable
            os.execv(python, [python] + sys.argv)

    def remove_board_background(self):
        handle_remove_board_background()
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def save_mixer_state(self):
        try:
            user_data = load_user_data()
            user_data["mixer_state"] = {
                "color1_hue": self.board_combo_var.get(),
                "color2_hue": self.ui_combo_var.get(),
                "color1_tier": self.board_tier_var.get(),
                "color2_tier": self.ui_tier_var.get(),
                "group_columns": self.group_columns,
                "group_locks": self.group_locked,
                "var_columns": self.var_columns
            }
            save_user_data(user_data)
        except Exception as e:
            print(f"[THEME] Error saving mixer state: {e}")

    def toggle_group_lock(self, group_name):
        self.group_locked[group_name] = not self.group_locked[group_name]
        if self.group_locked[group_name]:
            g_col = self.group_columns[group_name]
            for var in self.variable_groups[group_name]:
                self.var_columns[var] = g_col
        theme_view.populate_variable_lists(self)
        self.save_mixer_state()

    def swap_group_column(self, group_name):
        current_col = self.group_columns[group_name]
        new_col = 3 if current_col == 2 else 2
        self.group_columns[group_name] = new_col
        for var in self.variable_groups[group_name]:
            self.var_columns[var] = new_col
        theme_view.populate_variable_lists(self)
        self.save_mixer_state()

    def swap_variable_column(self, var_name):
        current_col = self.var_columns[var_name]
        self.var_columns[var_name] = 3 if current_col == 2 else 2
        theme_view.populate_variable_lists(self)
        self.save_mixer_state()

    def apply_theme_live(self, hue, tier):
        try:
            tiers = AVAILABLE_THEMES.get(hue, {})
            tier_data = tiers.get(tier, {})
            if not tier_data:
                for k, v in tiers.items():
                    if k.lower() == tier.lower():
                        tier_data = v
                        break
            if not tier_data and tiers:
                tier_data = list(tiers.values())[0]

            user_data = load_user_data()
            user_data["active_theme"] = tier_data
            if "custom_mixed_theme" in user_data:
                del user_data["custom_mixed_theme"]
            user_data["last_active_hue"] = hue
            user_data["last_active_tier"] = tier
            user_data["mixer_state"] = {
                "color1_hue": hue,
                "color2_hue": hue,
                "color1_tier": tier,
                "color2_tier": tier,
                "group_columns": self.group_columns,
                "group_locks": self.group_locked,
                "var_columns": self.var_columns
            }
            save_user_data(user_data)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"[THEME] Error applying standard theme: {e}")

    def apply_mixed_theme(self):
        color1_hue = self.board_combo_var.get()
        color2_hue = self.ui_combo_var.get()
        c1_tier = self.board_tier_var.get()
        c2_tier = self.ui_tier_var.get()

        try:
            def get_tier_dict(hue, tier_name):
                tiers = AVAILABLE_THEMES.get(hue, {})
                for k, v in tiers.items():
                    if k.lower() == tier_name.lower():
                        return v
                return list(tiers.values())[0] if tiers else {}

            c1_base = get_tier_dict(color1_hue, c1_tier)
            c2_base = get_tier_dict(color2_hue, c2_tier)

            mixed_tier = {}
            for var, col in self.var_columns.items():
                if col == 2:
                    val = c1_base.get(var)
                    if val is None:
                        val = c2_base.get(var)
                else:
                    val = c2_base.get(var)
                    if val is None:
                        val = c1_base.get(var)

                if val is not None:
                    mixed_tier[var] = val
                else:
                    mixed_tier[var] = "#000000"

            theme_entry = {
                "label": f"{color1_hue} ({c1_tier}) + {color2_hue} ({c2_tier}) [Mixed]",
                "type": "mixed",
                "color1_hue": color1_hue, "color1_tier": c1_tier,
                "color2_hue": color2_hue, "color2_tier": c2_tier,
                "group_columns": self.group_columns,
                "group_locks": self.group_locked,
                "var_columns": self.var_columns
            }
            apply_and_save_theme(mixed_tier, entry_metadata=theme_entry)
        except Exception as e:
            print(f"[THEME] Error applying mixed theme: {e}")