import json
import os
from pathlib import Path
from tkinter import ttk
import customtkinter as ctk
import chess.pgn

import gui.app_state as state
from gui.statusbar import set_status_message

STANDARD_TAG_BANK = {
    "essential": {"ECO", "Opening", "Variation"},
    "common": {
        "Event", "Site", "Date", "Round", "White", "Black", "Result",
        "WhiteElo", "BlackElo", "TimeControl", "Termination", "Annotator",
        "PlyCount", "EventDate", "WhiteTitle", "BlackTitle", "WhiteFideId",
        "BlackFideId", "SetUp", "FEN", "Mode", "Variant"
    }
}


class SearchCatalogWorkspace(ctk.CTkFrame):
    def __init__(self, master, app_state=None):
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.app_state = app_state or state

        self.json_path = Path("personal_catalog.json")
        self.pgn_path = Path("personal_catalog.pgn")

        self.catalog = {}
        self.all_data = []
        self.all_games_data = []
        self.all_games_columns = []

        self._configure_styles()
        self._build_ui()

        # Safely schedule the catalog loading on the main Tkinter thread
        self.after(100, self.load_catalog)

    def _configure_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("default")
        self.style.configure(
            "Treeview",
            background="#172134",
            fieldbackground="#172134",
            foreground="white",
            rowheight=26,
            borderwidth=0,
        )
        self.style.configure(
            "Treeview.Heading",
            background="#1e293b",
            foreground="white",
            borderwidth=0,
        )
        self.style.map(
            "Treeview.Heading",
            background=[("active", "#1e293b"), ("!active", "#1e293b")],
            foreground=[("active", "white"), ("!active", "white")],
        )
        self.style.map("Treeview", background=[("selected", "#3b82f6")])

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.panel = ctk.CTkFrame(self, fg_color="#172134", corner_radius=0)
        self.panel.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.panel.grid_rowconfigure(1, weight=1)
        self.panel.grid_columnconfigure(0, weight=1)

        self.toolbar = ctk.CTkFrame(self.panel, fg_color="transparent")
        self.toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 10))

        self.entry_filter = ctk.CTkEntry(self.toolbar, placeholder_text="Search all catalog game fields...", width=320)
        self.entry_filter.pack(side="left", padx=(0, 8))
        self.entry_filter.bind("<KeyRelease>", lambda e: self.apply_filter())

        self.lbl_tag_count = ctk.CTkLabel(self.toolbar, text="", font=("Arial", 11), text_color="#94a3b8")
        self.lbl_tag_count.pack(side="right", padx=5)

        self.table_frame = ctk.CTkFrame(self.panel, fg_color="#172134")
        self.table_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        # Temporary initial layout before full headers are computed
        self.setup_treeview(("ECO", "Games", "Opening", "Variation", "White", "Black", "Result"))

    def setup_treeview(self, columns):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col, anchor="w")
            if col in ("ECO", "Games", "Result", "Round", "PlyCount"):
                self.tree.column(col, width=65, minwidth=45, anchor="w", stretch=False)
            elif col in ("White", "Black", "Date", "Site", "Event"):
                self.tree.column(col, width=120, minwidth=80, anchor="w", stretch=False)
            elif col in ("Opening", "Variation"):
                self.tree.column(col, width=190, minwidth=120, anchor="w", stretch=True)
            else:
                self.tree.column(col, width=95, minwidth=60, anchor="w", stretch=False)

        vsb = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.table_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

    def load_catalog(self):
        catalog_data = {}
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    catalog_data = json.load(f)
            except Exception as e:
                print(f"Error loading catalog json: {e}")

        all_games = []
        headers_set = set()
        if self.pgn_path.exists():
            try:
                with open(self.pgn_path, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        headers = chess.pgn.read_headers(f)
                        if headers is None:
                            break

                        cleaned_headers = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in
                                           headers.items()}
                        headers_set.update(cleaned_headers.keys())
                        all_games.append(cleaned_headers)
            except Exception as e:
                print(f"Error loading catalog pgn: {e}")

        headers_set.update(STANDARD_TAG_BANK["common"])
        headers_set.update(STANDARD_TAG_BANK["essential"])

        self.catalog = catalog_data
        self.all_games_columns = list(headers_set)

        priority_order = [
            "ECO", "Games", "Opening", "Variation",
            "White", "Black",
            "Event", "Site", "Date", "Round", "Result",
            "WhiteElo", "BlackElo", "TimeControl", "Termination", "Annotator", "PlyCount"
        ]

        ordered_cols = [c for c in priority_order if c in self.all_games_columns or c == "Games"]

        for c in sorted(self.all_games_columns):
            if c not in ordered_cols and c != "Games":
                ordered_cols.append(c)

        self.all_games_columns = ordered_cols

        self.all_games_data = []
        for h in all_games:
            row = []
            for col in self.all_games_columns:
                if col == "Games":
                    row.append("1")
                else:
                    row.append(h.get(col, ""))
            self.all_games_data.append(row)

        self.setup_treeview(self.all_games_columns)
        for row in self.all_games_data:
            self.tree.insert("", "end", values=row)

        self.lbl_tag_count.configure(text=f"Loaded Tags: {len(self.all_games_columns)}")
        set_status_message(
            f"Catalog loaded instantly with full hierarchical dataset ({len(self.all_games_data):,} games).")

    def refresh_tree(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for row in self.all_games_data:
            self.tree.insert("", "end", values=row)

    def apply_filter(self):
        query = self.entry_filter.get().lower()
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in self.all_games_data:
            if any(query in str(val).lower() for val in row):
                self.tree.insert("", "end", values=row)