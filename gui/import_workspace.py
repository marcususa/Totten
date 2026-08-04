import os
import threading
from pathlib import Path
from tkinter import ttk

import chess.pgn
import customtkinter as ctk

import gui.app_state as state
from gui.statusbar import set_status_message
from catalog.catalog_builder import catalog_pgns

STANDARD_TAG_BANK = {
    "essential": {"ECO", "Opening", "Variation"},
    "common": {
        "Event", "Site", "Date", "Round", "White", "Black", "Result",
        "WhiteElo", "BlackElo", "TimeControl", "Termination", "Annotator",
        "PlyCount", "EventDate", "WhiteTitle", "BlackTitle", "WhiteFideId",
        "BlackFideId", "SetUp", "FEN", "Mode", "Variant"
    }
}


class ImportWorkspace(ctk.CTkFrame):
    def __init__(self, master, app_state=None, filename=None):
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.app_state = app_state or state
        self.filename = filename or getattr(state, "current_filename", None)

        self.all_data = []
        self.unknown_tags = []
        self.mapping_vars = {}

        self._configure_styles()
        self._build_ui()
        self.refresh_view()

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
        self.grid_columnconfigure(1, weight=0)

        self.left_panel = ctk.CTkFrame(self, fg_color="#172134", corner_radius=0)
        self.left_panel.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.left_panel.grid_rowconfigure(0, weight=1)
        self.left_panel.grid_columnconfigure(0, weight=1)

        self.table_frame = ctk.CTkFrame(self.left_panel, fg_color="#172134")
        self.table_frame.grid(row=0, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        # Hardwired mandatory first-level order: ECO, Games, Opening, Variation
        columns = ("ECO", "Games", "Opening", "Variation")
        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")

        self.tree.heading("ECO", text="ECO", anchor="w")
        self.tree.column("ECO", width=65, minwidth=50, anchor="w", stretch=False)
        self.tree.heading("Games", text="Games", anchor="w")
        self.tree.column("Games", width=65, minwidth=50, anchor="w", stretch=False)
        self.tree.heading("Opening", text="Opening", anchor="w")
        self.tree.column("Opening", width=220, minwidth=140, anchor="w", stretch=True)
        self.tree.heading("Variation", text="Variation", anchor="w")
        self.tree.column("Variation", width=250, minwidth=140, anchor="w", stretch=True)

        scrollbar = ttk.Scrollbar(self.table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self.right_panel = ctk.CTkFrame(self, fg_color="#0f172a", width=310, corner_radius=8)
        self.right_panel.grid(row=0, column=1, sticky="nsew", padx=(0, 15), pady=15)
        self.right_panel.grid_propagate(False)

        self.lbl_filename = ctk.CTkLabel(
            self.right_panel, text="No File Selected", font=("Arial", 15, "bold"), text_color="white", anchor="w",
            wraplength=280
        )
        self.lbl_filename.pack(anchor="w", padx=15, pady=(15, 2))

        self.lbl_game_count = ctk.CTkLabel(
            self.right_panel, text="0 Games Detected", font=("Arial", 12), text_color="#94a3b8", anchor="w"
        )
        self.lbl_game_count.pack(anchor="w", padx=15, pady=(0, 15))

        self.health_frame = ctk.CTkFrame(self.right_panel, fg_color="#1e293b", corner_radius=6)
        self.health_frame.pack(fill="x", padx=15, pady=(0, 15))

        self.lbl_essential = ctk.CTkLabel(self.health_frame, text="■ Blue (Essential) : 0%", text_color="#3b82f6",
                                          anchor="w")
        self.lbl_essential.pack(anchor="w", padx=12, pady=(10, 2))

        self.lbl_common = ctk.CTkLabel(self.health_frame, text="■ Green (Common)   : 0%", text_color="#22c55e",
                                       anchor="w")
        self.lbl_common.pack(anchor="w", padx=12, pady=(0, 2))

        self.lbl_unknown = ctk.CTkLabel(self.health_frame, text="■ Orange (Unrecognized) : 0 found",
                                        text_color="#f97316", anchor="w")
        self.lbl_unknown.pack(anchor="w", padx=12, pady=(0, 10))

        self.mapping_frame = ctk.CTkFrame(self.right_panel, fg_color="transparent")
        self.mapping_frame.pack(fill="x", padx=15, pady=(0, 15))

    def refresh_view(self):
        self.filename = getattr(state, "current_filename", self.filename)

        if not self.filename or not os.path.exists(self.filename):
            self.lbl_filename.configure(text="No File Loaded")
            self.lbl_game_count.configure(text="0 Games Detected")
            set_status_message("No PGN file loaded.")
            self.clear_table()
            return

        file_path = Path(self.filename)
        self.lbl_filename.configure(text=file_path.name)
        self._scan_and_process_pgn()

    def _scan_and_process_pgn(self):
        if not self.filename or not os.path.exists(self.filename):
            return

        def _scan():
            file_path_name = Path(self.filename).name
            total_games = 0
            essential_complete_count = 0
            all_detected_tags = set()
            grouped_data = {}

            try:
                with open(self.filename, encoding="utf-8", errors="replace") as pgn_file:
                    while True:
                        headers = chess.pgn.read_headers(pgn_file)
                        if headers is None:
                            break

                        total_games += 1
                        all_detected_tags.update(headers.keys())

                        eco = headers.get("ECO", "").strip()
                        opening = headers.get("Opening", "").strip()

                        if eco or opening:
                            essential_complete_count += 1

                        raw_eco = eco.upper() if eco else "UNKNOWN"
                        raw_opening = opening
                        raw_variation = headers.get("Variation", "").strip()

                        key = (raw_eco, raw_opening, raw_variation)
                        grouped_data[key] = grouped_data.get(key, 0) + 1

                tag_mappings = {tag: var.get() for tag, var in self.mapping_vars.items()}
                try:
                    catalog_pgns(self.filename, tag_mappings=tag_mappings)
                except Exception as imp_err:
                    print(f"Automatic import execution note: {imp_err}")

                def _update_ui():
                    self.lbl_game_count.configure(text=f"{total_games:,} Games Detected")
                    set_status_message(f"Inspected & imported {file_path_name} ({total_games:,} games)")

                    essential_pct = (essential_complete_count / total_games * 100) if total_games > 0 else 0
                    self.lbl_essential.configure(text=f"■ Blue (Essential) : {essential_pct:.0f}% complete")

                    common_tags_found = set()
                    unknown_tags_found = set()

                    for tag in all_detected_tags:
                        if tag in STANDARD_TAG_BANK["essential"]:
                            continue
                        elif tag in STANDARD_TAG_BANK["common"]:
                            common_tags_found.add(tag)
                        else:
                            unknown_tags_found.add(tag)

                    self.lbl_common.configure(text=f"■ Green (Common)   : {len(common_tags_found)} tags present")
                    self.lbl_unknown.configure(text=f"■ Orange (Unrecognized) : {len(unknown_tags_found)} found")

                    self._build_tag_mapping_ui(unknown_tags_found)

                    # Strictly ordered mapping: [ECO, Games (count), Opening, Variation]
                    imported_rows = [
                        [key[0], count, key[1], key[2]]
                        for key, count in grouped_data.items()
                    ]
                    imported_rows.sort(key=lambda x: (x[0], x[2], x[3]))

                    self.all_data = imported_rows
                    self.update_table(self.all_data)

                self.after(0, _update_ui)

            except Exception as e:
                print(f"Error scanning PGN file: {e}")
                self.after(0, lambda: set_status_message(f"Error scanning file: {e}"))
                self.after(0, self.clear_table)

        set_status_message("Scanning PGN health and tags...")
        threading.Thread(target=_scan, daemon=True).start()

    def _build_tag_mapping_ui(self, unknown_tags):
        for widget in self.mapping_frame.winfo_children():
            widget.destroy()

        self.mapping_vars.clear()
        self.unknown_tags = sorted(list(unknown_tags))

        if not self.unknown_tags:
            return

        lbl_title = ctk.CTkLabel(
            self.mapping_frame, text="NON-STANDARD TAGS DETECTED", font=("Arial", 11, "bold"), text_color="#f97316",
            anchor="w"
        )
        lbl_title.pack(anchor="w", pady=(0, 6))

        target_options = ["(Ignore)", "ECO", "Opening", "Variation", "Event", "Site", "Date", "Round", "Annotator"]

        for tag in self.unknown_tags:
            row = ctk.CTkFrame(self.mapping_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)

            ctk.CTkLabel(row, text=f'"{tag}"', font=("Arial", 12), text_color="#f97316", anchor="w", width=95).pack(
                side="left")
            ctk.CTkLabel(row, text="─►", font=("Arial", 10), text_color="#64748b").pack(side="left", padx=2)

            var = ctk.StringVar(value="(Ignore)")
            self.mapping_vars[tag] = var

            dropdown = ctk.CTkOptionMenu(
                row, values=target_options, variable=var, width=110, height=24, font=("Arial", 11)
            )
            dropdown.pack(side="right")

    def clear_table(self):
        self.all_data = []
        for item in self.tree.get_children():
            self.tree.delete(item)

    def update_table(self, data):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for row in data:
            self.tree.insert("", "end", values=row)