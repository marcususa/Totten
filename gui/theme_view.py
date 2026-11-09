import customtkinter as ctk

def set_tier(window, tier_var, selected_name):
    """Sets the selected tier variable mutually exclusively and updates button appearances."""
    tier_var.set(selected_name)
    if tier_var == window.board_tier_var:
        update_tier_buttons(window.board_tier_var, window.board_tier_btns)
    else:
        update_tier_buttons(window.ui_tier_var, window.ui_tier_btns)
    window.save_mixer_state()


def update_tier_buttons(tier_var, btn_dict):
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


def populate_variable_lists(window):
    """Re-renders grouped variable sections with lock/unlock toggles and swap controls."""
    for widget in window.vars_container_col2.winfo_children():
        widget.destroy()
    for widget in window.vars_container_col3.winfo_children():
        widget.destroy()

    for group_name, variables in window.variable_groups.items():
        g_col = window.group_columns[group_name]
        is_locked = window.group_locked[group_name]
        target_frame = window.vars_container_col2 if g_col == 2 else window.vars_container_col3

        group_frame = ctk.CTkFrame(target_frame, fg_color=("#262626", "#1e1e1e"), corner_radius=6)
        group_frame.pack(fill="x", pady=(4, 6), padx=1)

        g_header = ctk.CTkFrame(group_frame, fg_color="transparent")
        g_header.pack(fill="x", padx=6, pady=4)

        ctk.CTkLabel(
            g_header, text=group_name,
            font=("Arial", 11, "bold"), text_color=("#ffffff", "#e5e7eb")
        ).pack(side="left")

        right_ctrls = ctk.CTkFrame(g_header, fg_color="transparent")
        right_ctrls.pack(side="right")

        lock_text = "+" if is_locked else "X"
        ctk.CTkButton(
            right_ctrls, text=lock_text, width=26, height=26,
            font=("Arial", 11, "bold"),
            fg_color=("#374151", "#2d3748"),
            hover_color=("#4b5563", "#4a5568"),
            text_color=("#9ca3af", "#d1d5db"),
            command=lambda g=group_name: window.toggle_group_lock(g)
        ).pack(side="left", padx=(0, 2))

        if is_locked:
            arrow_text = "▶" if g_col == 2 else "◀"
            ctk.CTkButton(
                right_ctrls, text=arrow_text, width=26, height=26,
                font=("Arial", 11, "bold"),
                fg_color=("#374151", "#2d3748"),
                hover_color=("#4b5563", "#4a5568"),
                text_color=("#9ca3af", "#d1d5db"),
                command=lambda g=group_name: window.swap_group_column(g)
            ).pack(side="left", padx=(2, 0))
        else:
            for var in variables:
                v_col = window.var_columns[var]
                if v_col != g_col:
                    continue

                v_row = ctk.CTkFrame(group_frame, fg_color="transparent")
                v_row.pack(fill="x", padx=6, pady=2)
                ctk.CTkLabel(v_row, text=var, font=("Arial", 9), text_color=("gray80", "gray70")).pack(side="left", padx=(4, 0))

                var_arrow = "▶" if v_col == 2 else "◀"
                ctk.CTkButton(
                    v_row, text=var_arrow, width=26, height=26,
                    font=("Arial", 11, "bold"),
                    fg_color=("#374151", "#2d3748"),
                    hover_color=("#4b5563", "#4a5568"),
                    text_color=("#9ca3af", "#d1d5db"),
                    command=lambda v=var: window.swap_variable_column(v)
                ).pack(side="right", padx=(2, 0))

        if not is_locked:
            for var in variables:
                if window.var_columns[var] != g_col:
                    other_frame = window.vars_container_col2 if window.var_columns[var] == 2 else window.vars_container_col3
                    ind_row = ctk.CTkFrame(other_frame, fg_color=("#262626", "#1e1e1e"), corner_radius=4)
                    ind_row.pack(fill="x", pady=(2, 4), padx=1)

                    inner = ctk.CTkFrame(ind_row, fg_color="transparent")
                    inner.pack(fill="x", padx=6, pady=4)
                    ctk.CTkLabel(inner, text=f"{group_name}: {var}", font=("Arial", 9), text_color=("gray80", "gray70")).pack(side="left", padx=(4, 0))

                    v_col = window.var_columns[var]
                    var_arrow = "▶" if v_col == 2 else "◀"
                    ctk.CTkButton(
                        inner, text=var_arrow, width=26, height=26,
                        font=("Arial", 11, "bold"),
                        fg_color=("#374151", "#2d3748"),
                        hover_color=("#4b5563", "#4a5568"),
                        text_color=("#9ca3af", "#d1d5db"),
                        command=lambda v=var: window.swap_variable_column(v)
                    ).pack(side="right", padx=(2, 0))

    # Inject Board Background controls right under "Status" in Column 1 variable column
    board_container_frame = ctk.CTkFrame(window.vars_container_col2, fg_color="transparent", corner_radius=0)
    board_container_frame.pack(fill="x", pady=(4, 6), padx=1)

    board_row_frame = ctk.CTkFrame(board_container_frame, fg_color="transparent")
    board_row_frame.pack(fill="x", padx=6, pady=4)
    ctk.CTkLabel(
        board_row_frame, text="Board Background",
        font=("Arial", 11, "bold"), text_color=("#ffffff", "#e5e7eb")
    ).pack(side="left")

    right_bg_ctrls = ctk.CTkFrame(board_row_frame, fg_color="transparent")
    right_bg_ctrls.pack(side="right")

    ctk.CTkButton(
        right_bg_ctrls, text="+", width=26, height=26,
        font=("Arial", 11, "bold"),
        fg_color=("#374151", "#2d3748"),
        hover_color=("#4b5563", "#4a5568"),
        text_color=("#9ca3af", "#d1d5db"),
        command=window.select_board_background
    ).pack(side="left", padx=(2, 0))

    ctk.CTkButton(
        right_bg_ctrls, text="X", width=26, height=26,
        font=("Arial", 11, "bold"),
        fg_color=("#374151", "#2d3748"),
        hover_color=("#4b5563", "#4a5568"),
        text_color=("#9ca3af", "#d1d5db"),
        command=window.remove_board_background
    ).pack(side="left", padx=(2, 0))

    # Inject Apply Changes button at the bottom of Column 2 variable column
    apply_btn_frame = ctk.CTkFrame(window.vars_container_col3, fg_color="transparent")
    apply_btn_frame.pack(anchor="w", pady=(8, 0), padx=1)

    ctk.CTkButton(
        apply_btn_frame, text="Apply Changes",
        font=("Arial", 11, "bold"), height=26, width=110,
        fg_color=("#1d4ed8", "#1e3a8a"),
        hover_color=("#3b82f6", "#2563eb"),
        command=window.apply_mixed_theme
    ).pack(anchor="w")