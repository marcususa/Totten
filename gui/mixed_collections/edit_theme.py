from tkinter import ttk
from core.constants import THEME


class EditThemeMixin:
    """Handles ttk Treeview styling and strict THEME-driven widget styling helpers."""

    def _theme_color(self, key, fallback_key="text_secondary"):
        """Looks up a color strictly from THEME without hardcoded hex fallbacks."""
        val = THEME.get(key)
        if val:
            return val
        return THEME.get(fallback_key)

    def _configure_styles(self):
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.layout("Borderless.Treeview", [("Treeview.treearea", {"sticky": "nswe"})])

        bg_surface = self._theme_color("bg_surface", "bg_panel")
        text_primary = self._theme_color("text_primary", "text_secondary")
        btn_initial = self._theme_color("btn_initial", "bg_surface")
        bg_panel = self._theme_color("bg_panel", "bg_surface")

        style.configure(
            "Borderless.Treeview",
            background=bg_surface,
            foreground=text_primary,
            fieldbackground=bg_surface,
            rowheight=22,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
            highlightthickness=0,
        )
        style.map(
            "Borderless.Treeview",
            background=[("selected", btn_initial), ("focus", bg_surface), ("active", bg_surface)],
            foreground=[
                ("selected", self._theme_color("active_tracker_fg", "text_primary")),
                ("focus", text_primary),
                ("active", text_primary),
            ],
            borderwidth=[("focus", 0), ("active", 0)],
        )
        style.configure(
            "Borderless.Treeview.Heading",
            background=bg_panel,
            foreground=text_primary,
            font=("Arial", 10, "bold"),
            relief="flat",
            borderwidth=0,
        )
        style.map(
            "Borderless.Treeview.Heading",
            background=[("active", bg_panel), ("selected", bg_panel)],
            foreground=[("active", text_primary), ("selected", text_primary)],
        )

    def _apply_button_theme(self, button):
        """Applies explicit THEME colors to a CTkButton widget (text_primary -> text_secondary fallback)."""
        button.configure(
            fg_color=self._theme_color("btn_initial"),
            hover_color=self._theme_color("btn_hover"),
            text_color=self._theme_color("text_primary", "text_secondary"),
            border_color=self._theme_color("border_color"),
        )

    def _apply_checkbox_theme(self, checkbox):
        """Applies explicit THEME colors to a CTkCheckBox widget."""
        checkbox.configure(
            text_color=self._theme_color("text_primary", "text_secondary"),
            fg_color=self._theme_color("btn_initial"),
            hover_color=self._theme_color("btn_hover"),
            border_color=self._theme_color("border_color"),
            checkmark_color=self._theme_color("active_tracker_fg", "text_primary"),
        )

    def _apply_entry_theme(self, entry):
        """Applies explicit THEME colors to a CTkEntry widget."""
        entry.configure(
            fg_color=self._theme_color("bg_panel", "bg_surface"),
            text_color=self._theme_color("text_primary", "text_secondary"),
            placeholder_text_color=self._theme_color("text_secondary", "text_primary"),
            border_color=self._theme_color("border_color"),
        )