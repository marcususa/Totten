from core.constants import THEME


class AnalysisDataMixin:
    """Mixin class for analysis text tags, Multi-PV rendering, and mode button states."""

    def _init_analysis_tags(self):
        """Configures CustomTkinter/Tkinter text box tags using central THEME colors, bold evals, and vertical spacing."""
        target_box = self._get_analysis_text_widget()
        if not target_box:
            return

        primary = THEME.get("text_primary", "#ffffff")
        secondary = THEME.get("text_secondary", "#94a3b8")
        accent = THEME.get("btn_hover", primary)
        eval_font = ("Arial", 11, "bold")

        target_box.tag_config("red", foreground=THEME.get("eval_red", "#de3d35"), font=eval_font, spacing3=6)
        target_box.tag_config("orange", foreground=THEME.get("eval_orange", "#FFA500"), font=eval_font, spacing3=6)
        target_box.tag_config("green", foreground=THEME.get("eval_green", "#1fa73b"), font=eval_font, spacing3=6)
        target_box.tag_config("light_blue", foreground=THEME.get("eval_light_blue", "#31a0ef"), font=eval_font, spacing3=6)
        target_box.tag_config("default", foreground=primary, font=eval_font, spacing3=6)
        target_box.tag_config("comment_tag", foreground=secondary, spacing3=6)
        target_box.tag_config("variation_tag", foreground=secondary, spacing3=6)
        target_box.tag_config("header_tag", foreground=secondary, spacing3=6)
        target_box.tag_config("move_tag", foreground=primary, spacing3=6)
        target_box.tag_config(
            "active_tracker",
            background=THEME.get("active_tracker_bg", accent),
            foreground=THEME.get("active_tracker_fg", "#ffffff"),
        )

    def render_pv_lines(self, pv_data):
        """Renders up to 4 Multi-PV engine lines into self.pv_textbox."""
        if not hasattr(self, "pv_textbox") or not self.pv_textbox:
            return

        target_box = getattr(self.pv_textbox, "_textbox", getattr(self.pv_textbox, "textbox", self.pv_textbox))
        target_box.delete("1.0", "end")

        max_lines = 4
        for i in range(1, max_lines + 1):
            line = pv_data.get(i) if isinstance(pv_data, dict) else None
            if not line and isinstance(pv_data, list) and (i - 1) < len(pv_data):
                line = pv_data[i - 1]

            if line:
                score = line.get("score_str", line.get("score", ""))
                moves = line.get("pv_str", " ".join(line.get("pv", [])))
                text = f"{i}. {score} {moves}\n"
                target_box.insert("end", text)

    def render_catalog_analysis_moves(self, analysis_data):
        """Renders the PGN tree with moves, comments, and variations, then syncs the tracker."""
        game_obj = (
            getattr(self, "current_game", None)
            or getattr(self, "active_game", None)
            or getattr(self, "root_game_node", None)
        )
        if game_obj:
            self._render_game_pgn_tree(game_obj)
        else:
            self.update_active_move_highlight()

    def _update_analysis_buttons_state(self):
        """Updates the visual selection state of all engine and mode buttons."""
        is_running = getattr(self, "_engine_running", False)

        if hasattr(self, "btn_engine_action") and self.btn_engine_action:
            try:
                self.btn_engine_action.configure(
                    fg_color=THEME["btn_hover"] if is_running else THEME["btn_initial"],
                    text="Stop" if is_running else "Engine"
                )
                if not is_running and hasattr(self.btn_engine_action, "_on_leave"):
                    self.btn_engine_action._on_leave(None)
            except Exception:
                pass
        if hasattr(self, "frame_engine_action") and self.frame_engine_action:
            try:
                self.frame_engine_action.configure(border_width=0 if is_running else 1)
            except Exception:
                pass

        selected_mode = getattr(self, "active_engine_mode", getattr(self, "_selected_mode_button", None))
        self._selected_mode_button = selected_mode

        buttons_map = {
            "review": (getattr(self, "btn_review", None), getattr(self, "frame_review", None)),
            "candidates": (getattr(self, "btn_candidates", None), getattr(self, "frame_candidates", None)),
            "standard": (getattr(self, "btn_standard", None), getattr(self, "frame_standard", None))
        }

        for m, (btn, frm) in buttons_map.items():
            is_selected = (selected_mode == m)
            if btn is not None:
                try:
                    btn.configure(
                        fg_color=THEME["btn_hover"] if is_selected else THEME["btn_initial"]
                    )
                    if not is_selected and hasattr(btn, "_on_leave"):
                        btn._on_leave(None)
                except Exception:
                    pass
            if frm is not None:
                try:
                    frm.configure(border_width=0 if is_selected else 1)
                except Exception:
                    pass
