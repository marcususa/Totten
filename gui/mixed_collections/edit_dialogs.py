import customtkinter as ctk
from pathlib import Path


class AddCategoryDialog(ctk.CTkToplevel):
    def __init__(self, parent, title="Add Category"):
        super().__init__(parent)
        self.category_name = None

        self.title(title)
        self.geometry("300x150")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.configure(fg_color="#0f172a")

        self.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(
            self, text="Enter new category name:",
            font=("Arial", 12), text_color="#f8fafc"
        )
        self.label.pack(padx=20, pady=(20, 5), anchor="w")

        self.entry = ctk.CTkEntry(
            self, width=260, font=("Arial", 12),
            fg_color="#1e293b", border_color="#344268", text_color="#f8fafc"
        )
        self.entry.pack(padx=20, pady=(0, 15))
        self.entry.focus()
        self.entry.bind("<Return>", lambda e: self._on_ok())

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 15))

        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color="#344268", hover_color="#2e4a8c",
            border_width=1, border_color="#344268", width=90, height=28, command=self.destroy
        )
        cancel_btn.pack(side="right", padx=(5, 0))

        ok_btn = ctk.CTkButton(
            btn_frame, text="Add",
            fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#344268", width=90, height=28, command=self._on_ok
        )
        ok_btn.pack(side="right", padx=(0, 5))

    def _on_ok(self):
        val = self.entry.get().strip()
        if val:
            self.category_name = val
        self.destroy()


class ConfirmationDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message):
        super().__init__(parent)
        self.confirmed = False

        self.title(title)
        self.geometry("350x160")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.configure(fg_color="#0f172a")
        self.grid_columnconfigure(0, weight=1)

        msg_label = ctk.CTkLabel(
            self, text=message, font=("Arial", 12),
            text_color="#f8fafc", wraplength=310, justify="center", anchor="center"
        )
        msg_label.pack(padx=20, pady=(25, 15), fill="x", expand=True)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(0, 20))

        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1)

        confirm_btn = ctk.CTkButton(
            btn_frame, text="Confirm",
            fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#344268", width=100, height=28, command=self._confirm
        )
        confirm_btn.grid(row=0, column=0, sticky="e", padx=(0, 6))

        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color="#344268", hover_color="#2e4a8c",
            border_width=1, border_color="#344268", width=100, height=28, command=self.destroy
        )
        cancel_btn.grid(row=0, column=1, sticky="w", padx=(6, 0))

    def _confirm(self):
        self.confirmed = True
        self.destroy()


class CollectionLimitDialog(ctk.CTkToplevel):
    def __init__(self, parent, count):
        super().__init__(parent)
        self.title("Collection Too Large")
        self.geometry("380x180")
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)
        self.configure(fg_color="#0f172a")

        msg = f"The selected files contain {count} games. Collections are currently recommended to stay under 300 games for optimal performance."
        msg_label = ctk.CTkLabel(
            self, text=msg, font=("Arial", 12),
            text_color="#f8fafc", wraplength=340, justify="left"
        )
        msg_label.pack(padx=20, pady=(20, 15), anchor="w")

        ok_btn = ctk.CTkButton(
            self, text="OK",
            fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#344268", width=100, height=28, command=self.destroy
        )
        ok_btn.pack(pady=(0, 20))


class GameSelectionDialog(ctk.CTkToplevel):
    def __init__(self, parent, games_data):
        super().__init__(parent)
        self.selected_games = [g["game"] for g in games_data]

        self.title("Verify Collection Games")
        self.geometry("500x400")
        self.grab_set()
        self.transient(parent)
        self.configure(fg_color="#0f172a")

        header_label = ctk.CTkLabel(
            self, text=f"Found {len(games_data)} games to include:",
            font=("Arial", 12, "bold"), text_color="#f8fafc"
        )
        header_label.pack(padx=20, pady=(15, 5), anchor="w")

        self.scroll_frame = ctk.CTkScrollableFrame(self, width=460, height=270, fg_color="#1e293b")
        self.scroll_frame.pack(padx=20, pady=5, fill="both", expand=True)

        for idx, item in enumerate(games_data):
            lbl = ctk.CTkLabel(
                self.scroll_frame,
                text=f"{idx + 1}. {item['white']} vs {item['black']} ({item['opening']})",
                font=("Arial", 11), text_color="#f8fafc", anchor="w"
            )
            lbl.pack(fill="x", pady=2)

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)

        cancel_btn = ctk.CTkButton(
            btn_frame, text="Cancel",
            fg_color="#334155", hover_color="#475569",
            border_width=1, border_color="#344268", width=100, height=28, command=self._cancel
        )
        cancel_btn.pack(side="right", padx=(5, 0))

        accept_btn = ctk.CTkButton(
            btn_frame, text="Accept All",
            fg_color="#344268", hover_color="#2e4a8c",
            border_width=2, border_color="#344268", width=100, height=28, command=self._accept
        )
        accept_btn.pack(side="right", padx=(0, 5))

    def _cancel(self):
        self.selected_games = []
        self.destroy()

    def _accept(self):
        self.destroy()