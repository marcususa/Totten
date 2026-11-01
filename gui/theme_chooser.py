import json
import sys
import os
from pathlib import Path
import shutil
import customtkinter as ctk
from tkinter import filedialog

# Robustly locate the actual project root directory
ROOT_DIR = Path(__file__).resolve().parent
while ROOT_DIR != ROOT_DIR.parent:
    if (ROOT_DIR / "main.py").exists() or (ROOT_DIR / "core").exists():
        break
    ROOT_DIR = ROOT_DIR.parent

DEFAULTS_FILE = ROOT_DIR / "theme_defaults.json"
USER_THEMES_FILE = ROOT_DIR / "user_themes.json"

# Load static defaults directly from JSON
try:
    with open(DEFAULTS_FILE, "r", encoding="utf-8") as f:
        THEME_DEFAULTS = json.load(f)
except Exception as e:
    print(f"[THEME] Error loading {DEFAULTS_FILE}: {e}")
    THEME_DEFAULTS = {}


class ThemeChooserWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Theme Chooser & Mixer")

        # Make window resizable
        self.resizable(True, True)
        self.attributes("-topmost", True)

        # Define the 8 independent variable groups with updated names and correctly organized variables
        self.variable_groups = {
            "Background": [
                "bg_panel", "bg_surface"
            ],
            "Layout": [
                "border_ring", "divider", "shadow_color"
            ],
            "Text": [
                "text_primary"
            ],
            "Status": [
                "status_text", "error_color", "success_color"
            ],
            "Board": [
                "dark_square", "light_square", "highlight_square"
            ],
            "Board Elements": [
                "valid_move_dot", "check_indicator", "border_color", "active_tracker_fg"
            ],
            "Buttons": [
                "btn_initial", "btn_hover", "btn_active", "btn_disabled"
            ],
            "Extras": [
                "accent_color", "link_color",
                "progress_bg", "progress_fill", "text_secondary", "eval_default"
            ]
        }

        # Default group column assignments split evenly across 8 groups
        default_group_columns = {
            "Background": 2,
            "Layout": 2,
            "Text": 2,
            "Status": 2,
            "Board": 3,
            "Board Elements": 3,
            "Buttons": 3,
            "Extras": 3
        }

        # Load persisted state from user_themes.json if available
        user_data = {}
        if USER_THEMES_FILE.exists():
            try:
                with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                    user_data = json.load(f)
            except Exception:
                pass

        # Pull state from mixer_state or latest current_themes entry
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

        hue_choices = list(THEME_DEFAULTS.keys())
        default_hue = hue_choices[0] if hue_choices else "Red"

        # Initialize group columns and lock states
        self.group_columns = dict(default_group_columns)
        for g, col in saved_group_cols.items():
            if g in self.group_columns:
                self.group_columns[g] = col

        self.group_locked = {g: True for g in self.variable_groups}
        for g, locked in saved_group_locks.items():
            if g in self.group_locked:
                self.group_locked[g] = locked

        # Initialize individual variable columns (syncing with group if locked)
        self.var_columns = {}
        for group_name, variables in self.variable_groups.items():
            g_col = self.group_columns[group_name]
            for var in variables:
                if not self.group_locked[group_name] and var in saved_var_cols:
                    self.var_columns[var] = saved_var_cols[var]
                else:
                    self.var_columns[var] = g_col

        # Single-selection tier variables (Mutually exclusive: Light, Medium, or Dark)
        self.board_tier_var = ctk.StringVar(
            value=saved_tier1 if saved_tier1 in ["Light", "Medium", "Dark"] else "Medium")
        self.ui_tier_var = ctk.StringVar(
            value=saved_tier2 if saved_tier2 in ["Light", "Medium", "Dark"] else "Medium")

        # Main background container
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)
        main_frame.grid_columnconfigure(0, weight=3)  # Column 1: Theme Colors Grid
        main_frame.grid_columnconfigure(1, weight=2)  # Column 2: Color 1
        main_frame.grid_columnconfigure(2, weight=2)  # Column 3: Color 2
        main_frame.grid_rowconfigure(0, weight=1)  # Allow content area to expand vertically
        main_frame.grid_rowconfigure(1, weight=0)  # Apply button row

        # =========================================================================
        # COLUMN 1: Theme Colors Grid & Swatches
        # =========================================================================
        col1_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        col1_frame.grid(row=0, column=0, rowspan=2, sticky="nsew", padx=(0, 10), pady=0)

        header_frame = ctk.CTkFrame(col1_frame, fg_color="transparent")
        header_frame.pack(anchor="w", pady=(0, 6))

        ctk.CTkLabel(
            header_frame, text="Theme Colors",
            font=("Arial", 16, "bold")
        ).pack(side="left")

        # + board background button positioned below Theme Colors
        existing_bg = any(
            (ROOT_DIR / f"board_background{ext}").exists() for ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"])
        btn_bg_text = "Change Board Background" if existing_bg else "+ Board Background"

        self.board_bg_btn = ctk.CTkButton(
            col1_frame, text=btn_bg_text,
            font=("Arial", 11, "bold"), height=26,
            fg_color=("#374151", "#2d3748"),
            hover_color=("#4b5563", "#4a5568"),
            command=self.select_board_background
        )
        self.board_bg_btn.pack(anchor="w", pady=(0, 8))

        instruction_frame = ctk.CTkFrame(col1_frame, fg_color="transparent")
        instruction_frame.pack(anchor="w", pady=(0, 12))

        ctk.CTkLabel(
            instruction_frame,
            text="Select a theme color below, or mix combinations on the right.",
            font=("Arial", 11),
            text_color=("gray60", "gray70")
        ).pack(anchor="w")

        grid_container = ctk.CTkFrame(col1_frame, fg_color="transparent")
        grid_container.pack(fill="both", expand=True)

        grid_container.grid_columnconfigure(0, weight=2)
        grid_container.grid_columnconfigure(1, weight=1)
        grid_container.grid_columnconfigure(2, weight=1)
        grid_container.grid_columnconfigure(3, weight=1)

        row_idx = 0
        tier_keys = ["Light", "Medium", "Dark"]

        for hue_name, tiers in THEME_DEFAULTS.items():
            ctk.CTkLabel(
                grid_container, text=hue_name,
                font=("Arial", 12, "bold")
            ).grid(row=row_idx, column=0, sticky="w", padx=5, pady=4)

            for col_offset, tier_key in enumerate(tier_keys, start=1):
                tier_data = tiers.get(tier_key)

                if tier_data and isinstance(tier_data, dict):
                    swatch_color = tier_data.get("dark_square", tier_data.get("btn_initial", "#3b82f6"))

                    swatch = ctk.CTkButton(
                        grid_container, text="", width=45, height=24,
                        fg_color=swatch_color,
                        hover_color=swatch_color,
                        border_width=2,
                        border_color="#000000",
                        corner_radius=4,
                        command=lambda h=hue_name, t=tier_key: self.apply_theme_live(h, t)
                    )
                    swatch.grid(row=row_idx, column=col_offset, padx=4, pady=4)
                else:
                    lbl = ctk.CTkLabel(
                        grid_container, text="—",
                        font=("Arial", 11), text_color="gray"
                    )
                    lbl.grid(row=row_idx, column=col_offset, padx=4, pady=4)

            row_idx += 1

        # =========================================================================
        # COLUMN 2: Color 1
        # =========================================================================
        self.col2_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.col2_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            self.col2_frame, text="Color 1",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(5, 6))

        top_ctrl_col2 = ctk.CTkFrame(self.col2_frame, fg_color="transparent")
        top_ctrl_col2.pack(fill="x", pady=(2, 10))

        initial_hue1 = saved_hue1 if saved_hue1 in hue_choices else default_hue
        self.board_combo_var = ctk.StringVar(value=initial_hue1)
        self.board_dropdown = ctk.CTkComboBox(
            top_ctrl_col2, values=hue_choices, variable=self.board_combo_var,
            font=("Arial", 11), height=26, width=95,
            command=lambda _: self.save_mixer_state()
        )
        self.board_dropdown.pack(side="left", padx=(0, 4))

        tiers_frame_col2 = ctk.CTkFrame(top_ctrl_col2, fg_color="transparent")
        tiers_frame_col2.pack(side="left", fill="x", expand=True)

        self.board_tier_btns = {}
        for t_code, t_name in [("L", "Light"), ("M", "Medium"), ("D", "Dark")]:
            btn = ctk.CTkButton(
                tiers_frame_col2, text=t_code, width=22, height=22, corner_radius=3,
                font=("Arial", 10, "bold"), border_width=1.5, border_color="#555555",
                command=lambda name=t_name: self.set_tier(self.board_tier_var, name)
            )
            btn.pack(side="left", padx=2)
            self.board_tier_btns[t_name] = btn
        self.update_tier_buttons(self.board_tier_var, self.board_tier_btns)

        ctk.CTkLabel(
            self.col2_frame, text="Variables:",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(2, 4))

        self.vars_container_col2 = ctk.CTkFrame(self.col2_frame, fg_color="transparent")
        self.vars_container_col2.pack(fill="both", expand=True)

        # =========================================================================
        # COLUMN 3: Color 2
        # =========================================================================
        self.col3_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.col3_frame.grid(row=0, column=2, sticky="nsew", padx=(10, 0), pady=(0, 10))

        ctk.CTkLabel(
            self.col3_frame, text="Color 2",
            font=("Arial", 14, "bold")
        ).pack(anchor="w", pady=(5, 6))

        top_ctrl_col3 = ctk.CTkFrame(self.col3_frame, fg_color="transparent")
        top_ctrl_col3.pack(fill="x", pady=(2, 10))

        initial_hue2 = saved_hue2 if saved_hue2 in hue_choices else default_hue
        self.ui_combo_var = ctk.StringVar(value=initial_hue2)
        self.ui_dropdown = ctk.CTkComboBox(
            top_ctrl_col3, values=hue_choices, variable=self.ui_combo_var,
            font=("Arial", 11), height=26, width=95,
            command=lambda _: self.save_mixer_state()
        )
        self.ui_dropdown.pack(side="left", padx=(0, 4))

        tiers_frame_col3 = ctk.CTkFrame(top_ctrl_col3, fg_color="transparent")
        tiers_frame_col3.pack(side="left", fill="x", expand=True)

        self.ui_tier_btns = {}
        for t_code, t_name in [("L", "Light"), ("M", "Medium"), ("D", "Dark")]:
            btn = ctk.CTkButton(
                tiers_frame_col3, text=t_code, width=22, height=22, corner_radius=3,
                font=("Arial", 10, "bold"), border_width=1.5, border_color="#555555",
                command=lambda name=t_name: self.set_tier(self.ui_tier_var, name)
            )
            btn.pack(side="left", padx=2)
            self.ui_tier_btns[t_name] = btn
        self.update_tier_buttons(self.ui_tier_var, self.ui_tier_btns)

        ctk.CTkLabel(
            self.col3_frame, text="Variables:",
            font=("Arial", 11, "bold")
        ).pack(anchor="w", pady=(2, 4))

        self.vars_container_col3 = ctk.CTkFrame(self.col3_frame, fg_color="transparent")
        self.vars_container_col3.pack(fill="both", expand=True)

        # Populate grouped variable lists initially on the spot
        self.populate_variable_lists()

        # =========================================================================
        # BOTTOM: Apply Button aligned with the bottom of Column 1
        # =========================================================================
        apply_mix_btn = ctk.CTkButton(
            main_frame, text="Apply Mixed Theme",
            font=("Arial", 12, "bold"), height=32,
            fg_color=("#1d4ed8", "#1e3a8a"),
            hover_color=("#3b82f6", "#2563eb"),
            command=self.apply_mixed_theme
        )
        apply_mix_btn.grid(row=1, column=1, columnspan=2, sticky="s", pady=(10, 0))

        # Set an optimal initial size while allowing free resizing by the user
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
        """Copies selected image to project root as 'board_background.[ext]' and saves reference."""
        # Temporarily drop topmost attribute so file dialog is not hidden behind ThemeChooserWindow
        self.attributes("-topmost", False)
        try:
            file_path = filedialog.askopenfilename(
                title="Select Board Background Image",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif")],
                parent=self
            )
        finally:
            self.attributes("-topmost", True)

        if not file_path:
            return

        try:
            src_path = Path(file_path)
            ext = src_path.suffix.lower()

            # Remove any existing board_background files with different extensions
            for existing_ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
                old_file = ROOT_DIR / f"board_background{existing_ext}"
                if old_file.exists():
                    old_file.unlink()

            dest_path = ROOT_DIR / f"board_background{ext}"
            shutil.copy2(src_path, dest_path)

            user_data = {}
            if USER_THEMES_FILE.exists():
                with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                    user_data = json.load(f)

            user_data["board_bg_image"] = str(dest_path.name)

            with open(USER_THEMES_FILE, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())

            print(f"[THEME] Successfully copied background to root: {dest_path.name}")

            # Close the theme chooser window after selection
            self.destroy()

        except Exception as e:
            print(f"[THEME] Error copying board background image: {e}")

    def save_mixer_state(self):
        """Saves current mixer state to mixer_state for compatibility."""
        try:
            user_data = {}
            if USER_THEMES_FILE.exists():
                with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                    user_data = json.load(f)

            user_data["mixer_state"] = {
                "color1_hue": self.board_combo_var.get(),
                "color2_hue": self.ui_combo_var.get(),
                "color1_tier": self.board_tier_var.get(),
                "color2_tier": self.ui_tier_var.get(),
                "group_columns": self.group_columns,
                "group_locks": self.group_locked,
                "var_columns": self.var_columns
            }

            with open(USER_THEMES_FILE, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            print(f"[THEME] Error saving mixer state: {e}")

    def _push_current_theme(self, new_theme):
        """Maintains the rolling list of up to 10 current_themes entries (variable strings without hexcodes)."""
        try:
            user_data = {}
            if USER_THEMES_FILE.exists():
                try:
                    with open(USER_THEMES_FILE, "r", encoding="utf-8") as f:
                        user_data = json.load(f)
                except Exception:
                    pass

            themes_list = user_data.get("current_themes", [])
            themes_list.insert(0, new_theme)
            if len(themes_list) > 10:
                themes_list = themes_list[:10]

            user_data["current_themes"] = themes_list
            user_data["mixer_state"] = {
                "color1_hue": new_theme.get("color1_hue"),
                "color2_hue": new_theme.get("color2_hue"),
                "color1_tier": new_theme.get("color1_tier"),
                "color2_tier": new_theme.get("color2_tier"),
                "group_columns": self.group_columns,
                "group_locks": self.group_locked,
                "var_columns": self.var_columns
            }
            return user_data
        except Exception as e:
            print(f"[THEME] Error updating current_themes list: {e}")
            return {}

    def set_tier(self, tier_var, selected_name):
        """Sets the selected tier variable mutually exclusively and updates button appearances."""
        tier_var.set(selected_name)
        if tier_var == self.board_tier_var:
            self.update_tier_buttons(self.board_tier_var, self.board_tier_btns)
        else:
            self.update_tier_buttons(self.ui_tier_var, self.ui_tier_btns)
        self.save_mixer_state()

    def update_tier_buttons(self, tier_var, btn_dict):
        """Styles the square tier buttons: solid blue when selected, subtle dark gray when unselected."""
        current = tier_var.get()
        for t_name, btn in btn_dict.items():
            if t_name == current:
                btn.configure(
                    fg_color=("#2563eb", "#1d4ed8"),
                    hover_color=("#3b82f6", "#2563eb"),
                    text_color="#ffffff",
                    border_color="#1e40af"
                )
            else:
                btn.configure(
                    fg_color=("#374151", "#2d3748"),
                    hover_color=("#4b5563", "#4a5568"),
                    text_color=("#d1d5db", "#9ca3af"),
                    border_color="#555555"
                )

    def populate_variable_lists(self):
        """Re-renders grouped variable sections with lock/unlock toggles and swap controls."""
        for widget in self.vars_container_col2.winfo_children():
            widget.destroy()
        for widget in self.vars_container_col3.winfo_children():
            widget.destroy()

        for group_name, variables in self.variable_groups.items():
            g_col = self.group_columns[group_name]
            is_locked = self.group_locked[group_name]
            target_frame = self.vars_container_col2 if g_col == 2 else self.vars_container_col3

            # Group Container Frame
            group_frame = ctk.CTkFrame(target_frame, fg_color=("#262626", "#1e1e1e"), corner_radius=6)
            group_frame.pack(fill="x", pady=2, padx=1)

            # Group Header Row
            g_header = ctk.CTkFrame(group_frame, fg_color="transparent")
            g_header.pack(fill="x", padx=4, pady=3)

            ctk.CTkLabel(
                g_header, text=group_name,
                font=("Arial", 11, "bold"), text_color=("#ffffff", "#e5e7eb")
            ).pack(side="left")

            # Right-side controls for group header (Swap & Lock buttons)
            right_ctrls = ctk.CTkFrame(g_header, fg_color="transparent")
            right_ctrls.pack(side="right")

            # Expand/Collapse Toggle Button ('+' when locked, '-' when unlocked)
            lock_text = "+" if is_locked else "-"
            lock_btn = ctk.CTkButton(
                right_ctrls, text=lock_text, width=24, height=18,
                font=("Arial", 10),
                fg_color=("#374151", "#2d3748"),
                hover_color=("#4b5563", "#4a5568"),
                text_color=("#9ca3af", "#d1d5db"),
                command=lambda g=group_name: self.toggle_group_lock(g)
            )
            lock_btn.pack(side="left", padx=(0, 2))

            if is_locked:
                arrow_text = "▶" if g_col == 2 else "◀"
                swap_group_btn = ctk.CTkButton(
                    right_ctrls, text=arrow_text, width=28, height=18,
                    font=("Arial", 10, "bold"),
                    fg_color=("#374151", "#2d3748"),
                    hover_color=("#4b5563", "#4a5568"),
                    text_color=("#9ca3af", "#d1d5db"),
                    command=lambda g=group_name: self.swap_group_column(g)
                )
                swap_group_btn.pack(side="left")
            else:
                for var in variables:
                    v_col = self.var_columns[var]
                    if v_col != g_col:
                        continue

                    v_row = ctk.CTkFrame(group_frame, fg_color="transparent")
                    v_row.pack(fill="x", padx=6, pady=1)

                    ctk.CTkLabel(v_row, text=var, font=("Arial", 9), text_color=("gray80", "gray70")).pack(side="left")

                    var_arrow = "▶" if v_col == 2 else "◀"
                    var_swap_btn = ctk.CTkButton(
                        v_row, text=var_arrow, width=26, height=16,
                        font=("Arial", 9, "bold"),
                        fg_color=("#374151", "#2d3748"),
                        hover_color=("#4b5563", "#4a5568"),
                        text_color=("#9ca3af", "#d1d5db"),
                        command=lambda v=var: self.swap_variable_column(v)
                    )
                    var_swap_btn.pack(side="right")

            if not is_locked:
                for var in variables:
                    if self.var_columns[var] != g_col:
                        other_frame = self.vars_container_col2 if self.var_columns[
                                                                      var] == 2 else self.vars_container_col3
                        ind_row = ctk.CTkFrame(other_frame, fg_color=("#262626", "#1e1e1e"), corner_radius=4)
                        ind_row.pack(fill="x", pady=1, padx=1)

                        inner = ctk.CTkFrame(ind_row, fg_color="transparent")
                        inner.pack(fill="x", padx=6, pady=3)

                        ctk.CTkLabel(inner, text=f"{group_name}: {var}", font=("Arial", 9),
                                     text_color=("gray80", "gray70")).pack(side="left")

                        v_col = self.var_columns[var]
                        var_arrow = "▶" if v_col == 2 else "◀"
                        var_swap_btn = ctk.CTkButton(
                            inner, text=var_arrow, width=26, height=16,
                            font=("Arial", 9, "bold"),
                            fg_color=("#374151", "#2d3748"),
                            hover_color=("#4b5563", "#4a5568"),
                            text_color=("#9ca3af", "#d1d5db"),
                            command=lambda v=var: self.swap_variable_column(v)
                        )
                        var_swap_btn.pack(side="right")

    def toggle_group_lock(self, group_name):
        """Toggles lock/unlock state for a variable group."""
        self.group_locked[group_name] = not self.group_locked[group_name]
        if self.group_locked[group_name]:
            g_col = self.group_columns[group_name]
            for var in self.variable_groups[group_name]:
                self.var_columns[var] = g_col
        self.populate_variable_lists()
        self.save_mixer_state()

    def swap_group_column(self, group_name):
        """Swaps the entire group column assignment when locked."""
        current_col = self.group_columns[group_name]
        new_col = 3 if current_col == 2 else 2
        self.group_columns[group_name] = new_col
        for var in self.variable_groups[group_name]:
            self.var_columns[var] = new_col
        self.populate_variable_lists()
        self.save_mixer_state()

    def swap_variable_column(self, var_name):
        """Swaps an individual variable's column when its group is unlocked."""
        current_col = self.var_columns[var_name]
        self.var_columns[var_name] = 3 if current_col == 2 else 2
        self.populate_variable_lists()
        self.save_mixer_state()

    def apply_theme_live(self, hue, tier):
        """Applies a standard theme, writing active_theme, last_active keys, and current_themes."""
        try:
            tier_data = THEME_DEFAULTS.get(hue, {}).get(tier, {})

            theme_entry = {
                "label": f"{hue} ({tier})",
                "type": "standard",
                "color1_hue": hue,
                "color1_tier": tier,
                "color2_hue": hue,
                "color2_tier": tier,
                "group_columns": self.group_columns,
                "group_locks": self.group_locked,
                "var_columns": self.var_columns
            }

            user_data = self._push_current_theme(theme_entry)
            user_data["active_theme"] = tier_data
            user_data["custom_mixed_theme"] = tier_data
            user_data["last_active_hue"] = hue
            user_data["last_active_tier"] = tier

            with open(USER_THEMES_FILE, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())

            print(f"[THEME] Applied active standard theme '{hue}' ({tier})")
        except Exception as e:
            print(f"[THEME] Error saving theme state: {e}")
            return

        print(f"[THEME] Restarting application...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)

    def apply_mixed_theme(self):
        """Applies a mixed theme, writing active_theme, last_active keys, and current_themes."""
        color1_hue = self.board_combo_var.get()
        color2_hue = self.ui_combo_var.get()
        c1_tier = self.board_tier_var.get()
        c2_tier = self.ui_tier_var.get()

        try:
            c1_base = THEME_DEFAULTS.get(color1_hue, {})
            c2_base = THEME_DEFAULTS.get(color2_hue, {})

            mixed_tier = {}
            for var, col in self.var_columns.items():
                if col == 2:
                    found_val = c1_base.get(c1_tier, {}).get(var)
                    if found_val is None:
                        found_val = c2_base.get(c2_tier, {}).get(var)
                    if found_val is not None:
                        mixed_tier[var] = found_val
                else:  # col == 3
                    found_val = c2_base.get(c2_tier, {}).get(var)
                    if found_val is None:
                        found_val = c1_base.get(c1_tier, {}).get(var)
                    if found_val is not None:
                        mixed_tier[var] = found_val

            theme_entry = {
                "label": f"{color1_hue} ({c1_tier}) + {color2_hue} ({c2_tier}) [Mixed]",
                "type": "mixed",
                "color1_hue": color1_hue,
                "color1_tier": c1_tier,
                "color2_hue": color2_hue,
                "color2_tier": c2_tier,
                "group_columns": self.group_columns,
                "group_locks": self.group_locked,
                "var_columns": self.var_columns
            }

            user_data = self._push_current_theme(theme_entry)
            user_data["active_theme"] = mixed_tier
            user_data["custom_mixed_theme"] = mixed_tier
            user_data["last_active_hue"] = f"{color1_hue} + {color2_hue} (Mixed)"
            user_data["last_active_tier"] = f"{c1_tier}/{c2_tier}"

            with open(USER_THEMES_FILE, "w", encoding="utf-8") as f:
                json.dump(user_data, f, indent=4)
                f.flush()
                os.fsync(f.fileno())

            print(f"[THEME] Successfully applied mixed theme.")

        except Exception as e:
            print(f"[THEME] Applied mixed theme error: {e}")
            return

        print(f"[THEME] Restarting application...")
        python = sys.executable
        os.execv(python, [python] + sys.argv)