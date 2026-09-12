import customtkinter as ctk
from .constants import STANDARD_TAG_BANK

class CatalogSearchMixin:
    def get_header(self, headers, key, default="Unknown"):
        if not headers:
            return default
        if key in headers:
            return headers[key]
        lower_key = key.lower()
        for k, v in headers.items():
            if k.lower() == lower_key:
                return v
        return default

    def get_first_n_moves_str(self, game_obj, n=10):
        if not game_obj:
            return ""
        try:
            board = game_obj.board()
            moves_san = []
            for node in game_obj.mainline():
                if len(moves_san) >= n * 2:
                    break
                moves_san.append(board.san(node.move))
                board.push(node.move)

            formatted_moves = []
            for i in range(0, len(moves_san), 2):
                move_num = (i // 2) + 1
                white_move = moves_san[i]
                black_move = moves_san[i + 1] if i + 1 < len(moves_san) else ""
                if black_move:
                    formatted_moves.append(f"{move_num}. {white_move} {black_move}")
                else:
                    formatted_moves.append(f"{move_num}. {white_move}")
            return "  ".join(formatted_moves)
        except Exception:
            return ""

    def apply_filter(self):
        self.refresh_current_view()

    def select_primary_tag(self, tag):
        self.active_primary_tag = tag
        self.active_extra_columns.clear()
        self._rebuild_toolbar_buttons()
        self.refresh_current_view()

    def toggle_tag_from_dialog(self, tag, is_checked):
        if is_checked:
            self.active_extra_columns.add(tag)
        else:
            if tag in self.active_extra_columns:
                self.active_extra_columns.remove(tag)
        self.active_primary_tag = None
        self._rebuild_toolbar_buttons()
        self.refresh_current_view()

    def open_all_tags_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("All Available Tags")
        dialog.geometry("340x420")
        dialog.transient(self)
        dialog.grab_set()

        dialog.configure(fg_color="#172134")
        dialog.grid_rowconfigure(0, weight=1)
        dialog.grid_columnconfigure(0, weight=1)

        frame = ctk.CTkFrame(dialog, fg_color="#172134", corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)

        scrollable_frame = ctk.CTkScrollableFrame(
            frame,
            fg_color="#1e293b",
            label_fg_color="#1e293b",
            border_color="#445577",
            border_width=1
        )
        scrollable_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        all_possible_tags = sorted(list(STANDARD_TAG_BANK["common"] | STANDARD_TAG_BANK["essential"]))

        for tag in all_possible_tags:
            if tag in ("ECO", "Opening", "Games"):
                continue

            var = ctk.BooleanVar(value=tag in self.active_extra_columns)
            chk = ctk.CTkCheckBox(
                scrollable_frame,
                text=tag,
                variable=var,
                font=("Arial", 12),
                command=lambda t=tag, v=var: self.toggle_tag_from_dialog(t, v.get()),
                text_color="#f8fafc",
                fg_color="#2e4a8c",
                hover_color="#3b5998",
                checkmark_color="#ffffff",
                border_color="#2e4a8c",
                border_width=2
            )

            def on_enter(e, c=chk, v=var):
                c.configure(hover_color="#3b5998" if v.get() else "#2e4a8c")

            chk.bind("<Enter>", on_enter)
            chk.pack(anchor="w", pady=6, padx=8)

    def _rebuild_toolbar_buttons(self):
        for widget in self.tag_buttons_frame.winfo_children():
            widget.destroy()

        for tag in ["Players", "Elo", "Event", "Variation", "All"]:
            if tag == "All":
                btn_width = 50
            elif tag == "Elo":
                btn_width = 65
            elif tag == "Event":
                btn_width = 65
            else:
                btn_width = 80

            is_active = (tag == self.active_primary_tag) and not self.active_extra_columns
            btn_fg = "#2e4a8c" if is_active else "transparent"
            btn_hover = "#3b5998" if is_active else "#2b3856"
            text_color = "#ffffff" if is_active else "#cbd5e1"

            if tag == "All":
                btn = ctk.CTkButton(
                    self.tag_buttons_frame,
                    text=tag,
                    width=btn_width,
                    height=26,
                    font=("Arial", 11, "bold"),
                    fg_color=btn_fg,
                    text_color=text_color,
                    hover_color=btn_hover,
                    corner_radius=4,
                    command=self.open_all_tags_dialog
                )
            else:
                btn = ctk.CTkButton(
                    self.tag_buttons_frame,
                    text=tag,
                    width=btn_width,
                    height=26,
                    font=("Arial", 11, "bold"),
                    fg_color=btn_fg,
                    text_color=text_color,
                    hover_color=btn_hover,
                    corner_radius=4,
                    command=lambda t=tag: self.select_primary_tag(t)
                )
            btn.pack(side="left", padx=2, pady=2)