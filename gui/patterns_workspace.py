# gui/patterns_workspace.py

import os
import tkinter as tk
from tkinter import messagebox, ttk
import customtkinter as ctk
import chess.pgn

# Path to store/load PGN content from the parent directory
PATTERNS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "personal_catalog.pgn"))


class PatternsWorkspace(ctk.CTkFrame):

    def __init__(self, parent, app_state=None):
        super().__init__(parent, fg_color="#172134", corner_radius=0)
        self.app_state = app_state

        self.all_games_headers = []
        self.all_games_data = []
        self.raw_pgn_games = []
        self.parsed_games_objects = []
        self.filtered_indices = []

        # Progressive Scan Tier Tracker (1 = Initial 4-ply, 2 = Second scan, 3 = Third scan)
        self.current_scan_tier = 1

        # Track the last valid indices that yielded results before a tier wiped them out
        self.last_valid_indices = []

        self._configure_styles()

        # Configure grid layout: Equal 50/50 vertical stack (Top sections, Notes window below)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1, uniform="group1")
        self.grid_rowconfigure(1, weight=1, uniform="group1")

        # --- Top Pane: Contains Controls & The Tree Catalog ---
        self.top_frame = ctk.CTkFrame(
            self,
            fg_color="#1f2c42",
            corner_radius=8,
            border_width=1,
            border_color="#2a3b59"
        )
        self.top_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=(5, 3))
        self.top_frame.grid_rowconfigure(1, weight=1)
        self.top_frame.grid_columnconfigure(0, weight=1)

        # Form / Attributes Frame for Piece Pull-down Menu and Scan Progression Controls
        self.attr_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.attr_frame.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")
        self.attr_frame.grid_columnconfigure(0, weight=2)
        self.attr_frame.grid_columnconfigure(1, weight=2)
        self.attr_frame.grid_columnconfigure(2, weight=1)

        self.piece_menu = ctk.CTkComboBox(
            self.attr_frame,
            values=[
                # Black Pieces (Back rank: Rook to Rook)
                "Black Queen's Rook",
                "Black Queen's Knight",
                "Black Queen's Bishop",
                "Black Queen",
                "Black King",
                "Black King's Bishop",
                "Black King's Knight",
                "Black King's Rook",
                # Black Pawns (a through h)
                "Black Pawn a6",
                "Black Pawn b6",
                "Black Pawn c6",
                "Black Pawn d6",
                "Black Pawn e6",
                "Black Pawn f6",
                "Black Pawn g6",
                "Black Pawn h6",
                # White Pawns (a through h)
                "White Pawn a3",
                "White Pawn b3",
                "White Pawn c3",
                "White Pawn d3",
                "White Pawn e3",
                "White Pawn f3",
                "White Pawn g3",
                "White Pawn h3",
                # White Pieces (Back rank: Rook to Rook)
                "White Queen's Rook",
                "White Queen's Knight",
                "White Queen's Bishop",
                "White Queen",
                "White King",
                "White King's Bishop",
                "White King's Knight",
                "White King's Rook",
            ],
            fg_color="#172134",
            button_color="#1f538d",
            button_hover_color="#14375f",
            dropdown_fg_color="#172134",
            command=lambda choice: self.reset_and_apply_filter()
        )
        self.piece_menu.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="ew")
        self.piece_menu.set("Black Queen's Rook")

        # Progressive Scan Action Button
        self.btn_scan_tier = ctk.CTkButton(
            self.attr_frame,
            text="Scan Deeper (Tier 1)",
            fg_color="#1f538d",
            hover_color="#14375f",
            command=self.progress_scan_tier,
            width=140,
        )
        self.btn_scan_tier.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        # Export Filtered Results to New Pattern PGN Button
        self.btn_export_pattern = ctk.CTkButton(
            self.attr_frame,
            text="Export Results",
            fg_color="#2b7a4b",
            hover_color="#1e5631",
            command=self.export_filtered_to_new_catalog,
            width=110,
        )
        self.btn_export_pattern.grid(row=0, column=2, padx=(5, 0), pady=5, sticky="ew")

        # Table / Treeview Frame
        self.table_frame = ctk.CTkFrame(self.top_frame, fg_color="#172134")
        self.table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        self.setup_treeview(("ECO", "Opening", "Variation", "White", "Black", "Result"))
        self.load_catalog()

        # --- Bottom Pane: Notes & Save ---
        self.bottom_frame = ctk.CTkFrame(
            self,
            fg_color="#1f2c42",
            corner_radius=8,
            border_width=1,
            border_color="#2a3b59"
        )
        self.bottom_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=(3, 5))
        self.bottom_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        # Content Inner Container to properly layout Textbox and Centered Button
        self.content_inner = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.content_inner.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.content_inner.grid_rowconfigure(0, weight=1)
        self.content_inner.grid_rowconfigure(1, weight=0)
        self.content_inner.grid_columnconfigure(0, weight=1)

        # PGN Content Textbox with word wrap enabled
        self.text_rationale = ctk.CTkTextbox(
            self.content_inner,
            wrap="word",
            font=("Arial", 13),
            fg_color="#172134",
            text_color="#ffffff"
        )
        self.text_rationale.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 10))

        # Save Button Container for precise horizontal centering
        self.btn_container = ctk.CTkFrame(self.content_inner, fg_color="transparent")
        self.btn_container.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.btn_container.grid_columnconfigure(0, weight=1)
        self.btn_container.grid_columnconfigure(2, weight=1)

        # Save Button (Centered, Blue theme)
        self.btn_save_recipe = ctk.CTkButton(
            self.btn_container,
            text="Save Game",
            fg_color="#1f538d",
            hover_color="#14375f",
            command=self.save_recipe_node,
            width=120,
        )
        self.btn_save_recipe.grid(row=0, column=1)

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
        self.style.map("Treeview", background=[("selected", "#1f538d")])

    def setup_treeview(self, columns):
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        self.tree = ttk.Treeview(self.table_frame, columns=columns, show="headings")

        for col in columns:
            self.tree.heading(col, text=col, anchor="w")
            if col in ("ECO", "Result", "Round", "PlyCount"):
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

        self.tree.bind("<<TreeviewSelect>>", self.on_catalog_select)

    def load_catalog(self):
        all_games_headers = []
        raw_games = []
        parsed_games = []

        if os.path.exists(PATTERNS_FILE):
            try:
                with open(PATTERNS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break

                        parsed_games.append(game)
                        exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                        pgn_str = game.accept(exporter)
                        raw_games.append(pgn_str)

                        cleaned_headers = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in
                                           game.headers.items()}
                        all_games_headers.append(cleaned_headers)
            except Exception as e:
                print(f"Error loading catalog pgn: {e}")

        self.raw_pgn_games = raw_games
        self.parsed_games_objects = parsed_games

        headers_set = set()
        for h in all_games_headers:
            headers_set.update(h.keys())

        priority_order = [
            "ECO", "Opening", "Variation",
            "White", "Black",
            "Event", "Site", "Date", "Round", "Result",
            "WhiteElo", "BlackElo", "TimeControl", "Termination", "Annotator", "PlyCount"
        ]

        ordered_cols = [c for c in priority_order if c in headers_set]
        for c in sorted(headers_set):
            if c not in ordered_cols:
                ordered_cols.append(c)

        if not ordered_cols:
            ordered_cols = ["ECO", "Opening", "Variation", "White", "Black", "Result"]

        self.all_games_headers_columns = ordered_cols
        self.setup_treeview(self.all_games_headers_columns)

        self.all_games_data = []
        for i, h in enumerate(all_games_headers):
            row = [h.get(col, "") for col in self.all_games_headers_columns]
            self.all_games_data.append((i, row))

        self.filtered_indices = [i for i, _ in self.all_games_data]
        self.last_valid_indices = list(self.filtered_indices)
        self.current_scan_tier = 1
        self.update_tier_button_text()
        self.refresh_tree_view()

    def refresh_tree_view(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        for real_idx in self.filtered_indices:
            _, row = self.all_games_data[real_idx]
            self.tree.insert("", "end", values=row, iid=str(real_idx))

    def reset_and_apply_filter(self):
        """Resets the progressive tier back to Tier 1 when a new piece/filter type is chosen."""
        self.current_scan_tier = 1
        self.filtered_indices = [i for i, _ in self.all_games_data]
        self.last_valid_indices = list(self.filtered_indices)
        self.apply_filter()

    def progress_scan_tier(self):
        """Advances to the next progressive scan tier using the current filtered subset."""
        if self.current_scan_tier < 3:
            self.current_scan_tier += 1
        else:
            self.current_scan_tier = 1
            self.filtered_indices = [i for i, _ in self.all_games_data]
            self.last_valid_indices = list(self.filtered_indices)

        self.apply_filter()

    def update_tier_button_text(self):
        if self.current_scan_tier == 1:
            self.btn_scan_tier.configure(text="Scan Deeper (Tier 1: Plies 1-4)")
        elif self.current_scan_tier == 2:
            self.btn_scan_tier.configure(text="Scan Deeper (Tier 2: Plies 5-14)")
        else:
            self.btn_scan_tier.configure(text="Scan Deeper (Tier 3: Plies 15-30)")

    def apply_filter(self):
        selected_piece_desc = self.piece_menu.get()

        target_piece_symbol = None
        target_squares = []

        # Map FEN-ordered dropdown selections
        if "Pawn" in selected_piece_desc:
            target_piece_symbol = chess.PAWN
            if "a3" in selected_piece_desc or "a6" in selected_piece_desc:
                target_squares = [chess.A3, chess.A6]
            elif "b3" in selected_piece_desc or "b6" in selected_piece_desc:
                target_squares = [chess.B3, chess.B6]
            elif "c3" in selected_piece_desc or "c6" in selected_piece_desc:
                target_squares = [chess.C3, chess.C6]
            elif "d3" in selected_piece_desc or "d6" in selected_piece_desc:
                target_squares = [chess.D3, chess.D6]
            elif "e3" in selected_piece_desc or "e6" in selected_piece_desc:
                target_squares = [chess.E3, chess.E6]
            elif "f3" in selected_piece_desc or "f6" in selected_piece_desc:
                target_squares = [chess.F3, chess.F6]
            elif "g3" in selected_piece_desc or "g6" in selected_piece_desc:
                target_squares = [chess.G3, chess.G6]
            elif "h3" in selected_piece_desc or "h6" in selected_piece_desc:
                target_squares = [chess.H3, chess.H6]
        elif "Knight" in selected_piece_desc:
            target_piece_symbol = chess.KNIGHT
            if "Queen's Knight" in selected_piece_desc:
                target_squares = [chess.B1, chess.B8]
            elif "King's Knight" in selected_piece_desc:
                target_squares = [chess.G1, chess.G8]
        elif "Bishop" in selected_piece_desc:
            target_piece_symbol = chess.BISHOP
            if "Queen's Bishop" in selected_piece_desc:
                target_squares = [chess.C1, chess.C8]
            elif "King's Bishop" in selected_piece_desc:
                target_squares = [chess.F1, chess.F8]
        elif "Rook" in selected_piece_desc:
            target_piece_symbol = chess.ROOK
            if "Queen's Rook" in selected_piece_desc:
                target_squares = [chess.A1, chess.A8]
            elif "King's Rook" in selected_piece_desc:
                target_squares = [chess.H1, chess.H8]
        elif "Queen" in selected_piece_desc:
            target_piece_symbol = chess.QUEEN
            target_squares = [chess.D1, chess.D8]
        elif "King" in selected_piece_desc:
            target_piece_symbol = chess.KING
            target_squares = [chess.E1, chess.E8]

        # Determine ply boundaries based on active progressive tier
        if self.current_scan_tier == 1:
            min_ply, max_ply = 0, 3
        elif self.current_scan_tier == 2:
            min_ply, max_ply = 4, 13
        else:
            min_ply, max_ply = 14, 29

        source_indices = self.filtered_indices if self.current_scan_tier > 1 else [i for i, _ in self.all_games_data]
        new_filtered_indices = []

        for idx in source_indices:
            game = self.parsed_games_objects[idx]
            if game is None:
                continue

            matched = False
            board = game.board()

            for ply_idx, move in enumerate(game.mainline_moves()):
                if min_ply <= ply_idx <= max_ply:
                    piece = board.piece_at(move.from_square)
                    if piece and piece.piece_type == target_piece_symbol:
                        if not target_squares or move.from_square in target_squares:
                            matched = True
                            break
                board.push(move)
                if ply_idx > max_ply:
                    break

            if matched:
                new_filtered_indices.append(idx)

        # Handle zero-match cases gracefully by preserving the previous successful pool
        if not new_filtered_indices and self.current_scan_tier > 1:
            messagebox.showwarning(
                "No Further Matches",
                f"Scan Tier {self.current_scan_tier} returned 0 results.\nExport will use the results from the previous valid tier."
            )
        else:
            self.filtered_indices = new_filtered_indices
            self.last_valid_indices = list(self.filtered_indices)

        self.update_tier_button_text()
        self.refresh_tree_view()

    def export_filtered_to_new_catalog(self):
        """Finds the next sequential patterns{N}.pgn file and exports from the last valid results pool."""
        target_export_indices = self.filtered_indices if self.filtered_indices else self.last_valid_indices

        if not target_export_indices:
            messagebox.showwarning("No Data", "There are no valid filtered games available to export.")
            return

        parent_dir = os.path.dirname(PATTERNS_FILE)

        # Determine next sequential filename (patterns1.pgn, patterns2.pgn, etc.)
        counter = 1
        while True:
            new_file_name = f"patterns{counter}.pgn"
            new_file_path = os.path.join(parent_dir, new_file_name)
            if not os.path.exists(new_file_path):
                break
            counter += 1

        try:
            exported_count = 0
            with open(new_file_path, "w", encoding="utf-8") as f:
                for idx in target_export_indices:
                    if idx < len(self.raw_pgn_games):
                        f.write(self.raw_pgn_games[idx] + "\n\n")
                        exported_count += 1

            messagebox.showinfo(
                "Export Successful",
                f"Successfully exported {exported_count} games to:\n{new_file_name}"
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Could not write new pattern catalog: {e}")

    def on_catalog_select(self, event):
        selection = self.tree.selection()
        if selection:
            idx = int(selection[0])
            if idx < len(self.raw_pgn_games):
                pgn_content = self.raw_pgn_games[idx]
                self.text_rationale.delete("1.0", "end")
                self.text_rationale.insert("1.0", pgn_content)

    def save_recipe_node(self):
        pgn_data = self.text_rationale.get("1.0", "end").strip()
        selection = self.tree.selection()
        piece_type = self.piece_menu.get()

        try:
            if selection:
                idx = int(selection[0])
                if idx < len(self.raw_pgn_games):
                    self.raw_pgn_games[idx] = pgn_data

                    from io import StringIO
                    new_game_obj = chess.pgn.read_game(StringIO(pgn_data))
                    if new_game_obj:
                        self.parsed_games_objects[idx] = new_game_obj

            with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
                for game_str in self.raw_pgn_games:
                    f.write(game_str + "\n\n")

            messagebox.showinfo(
                "Saved",
                f"Content successfully saved to {os.path.basename(PATTERNS_FILE)} with active piece attribution: {piece_type}.",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Could not save PGN file: {e}")