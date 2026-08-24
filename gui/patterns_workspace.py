import os
import sys
import json
from pathlib import Path

# Add parent directory to path so we can import splash from root
sys.path.append(str(Path(__file__).resolve().parent.parent))
from gui.splash import LoadingOverlay

import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import chess.pgn
from io import StringIO
import io
from PIL import Image

try:
    import cairosvg
    HAS_CAIROSVG = True
except ImportError:
    HAS_CAIROSVG = False

# Paths to store/load PGN content and JSON metadata from the parent directory
PATTERNS_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "personal_catalog.pgn"))
METADATA_JSON_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "personal_catalog.json"))


def load_chess_svg_icon(filepath, size=(28, 28)):
    """Loads a chess piece .svg icon as a larger PIL Image safely."""
    try:
        if HAS_CAIROSVG:
            png_data = cairosvg.svg2png(url=filepath, output_width=size[0], output_height=size[1])
            return Image.open(io.BytesIO(png_data)).convert("RGBA")
        else:
            img = Image.new("RGBA", size, (0, 0, 0, 0))
            return img
    except Exception:
        return Image.new("RGBA", size, (0, 0, 0, 0))


class PatternsWorkspace(ctk.CTkFrame):

    def __init__(self, parent, app_state=None):
        super().__init__(parent, fg_color="#172134", corner_radius=0)
        self.app_state = app_state

        self.all_games_data = []
        self.raw_pgn_games = []
        self.parsed_games_cache = {}  # Lazily cache full game objects as they are needed
        self.filtered_indices = []

        # Store categorized data for the 2 tiers
        self.tier1_data = []
        self.tier2_data = []

        # Track selected row state across custom tables
        self.selected_row_frame = None
        self.selected_game_idx = None

        # Load piece icons cache from /assets/pieces
        self.piece_icons = {}
        self.load_piece_icon_cache()

        # Track current selection internal code state
        self.current_piece_code = None
        self.current_piece_desc = None

        # Configure grid layout: Equal 50/50 vertical stack
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1, uniform="group1")
        self.grid_rowconfigure(1, weight=1, uniform="group1")

        # --- Top Pane: Contains Controls & The 2-Tier Stack Catalog ---
        self.top_frame = ctk.CTkFrame(
            self,
            fg_color="#1e293b",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.top_frame.grid(row=0, column=0, sticky="nsew", padx=15, pady=(15, 8))
        self.top_frame.grid_rowconfigure(1, weight=1)
        self.top_frame.grid_columnconfigure(0, weight=1)

        # Form / Attributes Frame
        self.attr_frame = ctk.CTkFrame(self.top_frame, fg_color="transparent")
        self.attr_frame.grid(row=0, column=0, padx=15, pady=(15, 8), sticky="ew")
        self.attr_frame.grid_columnconfigure(0, weight=2)
        self.attr_frame.grid_columnconfigure(1, weight=2)
        self.attr_frame.grid_columnconfigure(2, weight=1)

        self.piece_selector_btn = ctk.CTkButton(
            self.attr_frame,
            text="Click to choose piece",
            fg_color="#344268",
            hover_color="#2e4a8c",
            border_width=1,
            border_color="#344268",
            font=("Arial", 12, "bold"),
            anchor="center",
            command=self.open_fen_matrix_popup
        )
        self.piece_selector_btn.grid(row=0, column=0, padx=(0, 8), pady=5, sticky="ew")

        self.btn_scan_tier = ctk.CTkButton(
            self.attr_frame,
            text="Function 2",
            fg_color="#263147",
            hover_color="#263147",
            state="disabled",
            font=("Arial", 12, "bold"),
            width=140,
        )
        self.btn_scan_tier.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        self.btn_export_pattern = ctk.CTkButton(
            self.attr_frame,
            text="Export Results",
            fg_color="#344268",
            hover_color="#2e4a8c",
            font=("Arial", 12, "bold"),
            command=self.export_filtered_to_new_catalog,
            width=110,
        )
        self.btn_export_pattern.grid(row=0, column=2, padx=(8, 0), pady=5, sticky="ew")

        # Table / Scrollable Container Frame
        self.table_outer_frame = ctk.CTkFrame(
            self.top_frame,
            fg_color="#172134",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.table_outer_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 20))
        self.table_outer_frame.grid_rowconfigure(0, weight=1)
        self.table_outer_frame.grid_columnconfigure(0, weight=1)

        self.scrollable_tree_container = ctk.CTkScrollableFrame(
            self.table_outer_frame,
            fg_color="transparent"
        )
        self.scrollable_tree_container.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
        self.scrollable_tree_container.grid_columnconfigure(0, weight=1)

        # Initialize the 2 Custom Grid Tiers
        self.tier_containers = self.setup_two_custom_tiers(self.scrollable_tree_container)

        self.after(100, self.load_catalog)

        # --- Bottom Pane: Notes & Save ---
        self.bottom_frame = ctk.CTkFrame(
            self,
            fg_color="#1e293b",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.bottom_frame.grid(row=1, column=0, sticky="nsew", padx=15, pady=(8, 15))
        self.bottom_frame.grid_rowconfigure(0, weight=1)
        self.bottom_frame.grid_columnconfigure(0, weight=1)

        self.content_inner = ctk.CTkFrame(self.bottom_frame, fg_color="transparent")
        self.content_inner.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        self.content_inner.grid_rowconfigure(0, weight=1)
        self.content_inner.grid_rowconfigure(1, weight=0)
        self.content_inner.grid_columnconfigure(0, weight=1)

        self.text_rationale = ctk.CTkTextbox(
            self.content_inner,
            wrap="word",
            font=("Arial", 13),
            fg_color="#172134",
            text_color="#DDDDEE"
        )
        self.text_rationale.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 10))

        self.btn_container = ctk.CTkFrame(self.content_inner, fg_color="transparent")
        self.btn_container.grid(row=1, column=0, sticky="ew", pady=(0, 5))
        self.btn_container.grid_columnconfigure(0, weight=1)
        self.btn_container.grid_columnconfigure(2, weight=1)

        self.btn_save_recipe = ctk.CTkButton(
            self.btn_container,
            text="Save Game",
            fg_color="#344268",
            hover_color="#2e4a8c",
            font=("Arial", 12, "bold"),
            command=self.save_recipe_node,
            width=120,
        )
        self.btn_save_recipe.grid(row=0, column=1)

    def load_piece_icon_cache(self):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        assets_dir = os.path.abspath(os.path.join(base_dir, "..", "assets", "pieces"))
        piece_codes = ["br", "bn", "bb", "bq", "bk", "bp", "wr", "wn", "wb", "wq", "wk", "wp"]

        for code in piece_codes:
            svg_path = os.path.join(assets_dir, f"{code}.svg")
            if os.path.exists(svg_path):
                pil_img = load_chess_svg_icon(svg_path, size=(28, 28))
                self.piece_icons[code] = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(28, 28))

    def open_fen_matrix_popup(self):
        popup = ctk.CTkToplevel(self)
        popup.title("Select Piece")

        width, height = 360, 280
        popup.update_idletasks()
        screen_width = popup.winfo_screenwidth()
        screen_height = popup.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2)
        popup.geometry(f"{width}x{height}+{x}+{y}")

        popup.configure(fg_color="#172134")
        popup.grab_set()

        matrix_frame = ctk.CTkFrame(popup, fg_color="transparent")
        matrix_frame.pack(fill="both", expand=True, padx=16, pady=10)

        for col_idx in range(2):
            matrix_frame.grid_columnconfigure(col_idx, weight=1)

        columns_data = [
            (
                ["bp", "bn", "bb", "br", "bq", "bk"],
                ["Black Pawn", "Black Knight", "Black Bishop", "Black Rook", "Black Queen", "Black King"]
            ),
            (
                ["wp", "wn", "wb", "wr", "wq", "wk"],
                ["White Pawn", "White Knight", "White Bishop", "White Rook", "White Queen", "White King"]
            )
        ]

        for col_idx, (p_codes, p_desc) in enumerate(columns_data):
            col_box = ctk.CTkFrame(matrix_frame, fg_color="#1e293b", corner_radius=6, border_width=1,
                                   border_color="#334155")
            col_box.grid(row=0, column=col_idx, sticky="nsew", padx=6, pady=2)

            for i in range(len(p_codes)):
                code = p_codes[i]
                desc_text = p_desc[i]
                icon = self.piece_icons.get(code, None)

                btn = ctk.CTkButton(
                    col_box,
                    text=desc_text,
                    image=icon,
                    compound="left",
                    anchor="w",
                    height=30,
                    font=("Arial", 11),
                    fg_color="#344268",
                    text_color="white",
                    hover_color="#2e4a8c",
                    command=lambda c=code, d=desc_text: self.on_piece_selected(c, d, popup)
                )
                t_pad = 4 if i == 0 else 1
                b_pad = 4 if i == len(p_codes) - 1 else 1
                btn.pack(fill="x", padx=6, pady=(t_pad, b_pad))

    def on_piece_selected(self, piece_code, piece_desc, popup_window):
        popup_window.destroy()
        self.current_piece_code = piece_code
        self.current_piece_desc = piece_desc
        self.piece_selector_btn.configure(text=piece_desc)

        self.loading_overlay = LoadingOverlay(self, title_text="Totten", message="Filtering Patterns...")
        threading.Thread(target=self._background_apply_filter, daemon=True).start()

    def setup_two_custom_tiers(self, parent_container):
        for widget in parent_container.winfo_children():
            widget.destroy()

        tier_names = ["Moves 8-15", "Moves 16-25"]
        tiers = []

        def configure_columns(frame):
            frame.grid_columnconfigure(0, weight=1, minsize=150)  # Move Match Display

        for i, t_name in enumerate(tier_names):
            tier_box = ctk.CTkFrame(
                parent_container,
                fg_color="#172134",
                corner_radius=6,
                border_width=1,
                border_color="#334155"
            )
            tier_box.grid(row=i, column=0, sticky="nsew", pady=(0, 10))
            tier_box.grid_columnconfigure(0, weight=1)
            tier_box.grid_rowconfigure(1, weight=1)

            tier_frame = ctk.CTkFrame(tier_box, fg_color="transparent")
            tier_frame.grid(row=0, column=0, sticky="nsew", padx=6, pady=6)
            tier_frame.grid_columnconfigure(0, weight=1)
            tier_frame.grid_rowconfigure(1, weight=1)

            header_frame = ctk.CTkFrame(tier_frame, fg_color="#1e293b", corner_radius=4)
            header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 2))
            configure_columns(header_frame)

            ctk.CTkLabel(header_frame, text=t_name, font=("Arial", 14, "bold"), text_color="white", anchor="w").grid(
                row=0, column=0, sticky="w", padx=(8, 6), pady=4)

            rows_scroll_frame = ctk.CTkScrollableFrame(tier_frame, fg_color="transparent", height=140)
            rows_scroll_frame.grid(row=1, column=0, sticky="nsew")
            rows_scroll_frame.grid_columnconfigure(0, weight=1)
            configure_columns(rows_scroll_frame)

            tiers.append(rows_scroll_frame)

        return tuple(tiers)

    def load_catalog(self):
        self.loading_overlay = LoadingOverlay(self, title_text="Totten", message="Loading Patterns Catalog...")
        threading.Thread(target=self._background_load_catalog_worker, daemon=True).start()

    def _background_load_catalog_worker(self):
        raw_games = []
        if os.path.exists(PATTERNS_FILE):
            try:
                with open(PATTERNS_FILE, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                    raw_games = [g.strip() for g in content.split("\n\n[Event ") if g.strip()]
                    if raw_games and not raw_games[0].startswith("[Event"):
                        raw_games[0] = "[Event " + raw_games[0]
                    for i in range(1, len(raw_games)):
                        raw_games[i] = "[Event " + raw_games[i]
            except Exception as e:
                print(f"Error reading catalog: {e}")

        self.after(0, lambda: self._finalize_catalog_load(raw_games))

    def _finalize_catalog_load(self, raw_games):
        self.raw_pgn_games = raw_games
        self.parsed_games_cache = {}
        self.all_games_data = [(i, []) for i in range(len(raw_games))]
        self.filtered_indices = [i for i, _ in self.all_games_data]
        self.refresh_tree_view()

        if hasattr(self, "loading_overlay"):
            self.loading_overlay.close()

    def refresh_tree_view(self):
        for container in self.tier_containers:
            for widget in container.winfo_children():
                widget.destroy()

        self.selected_row_frame = None

        self._populate_tier_rows(self.tier_containers[0], self.tier1_data)
        self._populate_tier_rows(self.tier_containers[1], self.tier2_data)

    def _populate_tier_rows(self, container, data_list):
        for row_idx, (real_idx, row_values) in enumerate(data_list):
            row_frame = ctk.CTkFrame(container, fg_color="transparent", corner_radius=4, height=30)
            row_frame.grid(row=row_idx, column=0, sticky="ew", pady=1)
            row_frame.grid_columnconfigure(0, weight=1)
            row_frame.grid_propagate(False)

            val_text = row_values[0] if row_values else ""
            lbl = ctk.CTkLabel(row_frame, text=str(val_text), font=("Arial", 12), anchor="w", text_color="#DDDDEE")
            lbl.grid(row=0, column=0, sticky="w", padx=(8, 6), pady=0)

            for widget in [row_frame, lbl]:
                widget.bind("<Button-1>",
                            lambda e, r_frame=row_frame, idx=real_idx: self.select_custom_row(r_frame, idx))

    def select_custom_row(self, row_frame, real_idx):
        if self.selected_row_frame and self.selected_row_frame.winfo_exists():
            self.selected_row_frame.configure(fg_color="transparent")

        self.selected_row_frame = row_frame
        self.selected_row_frame.configure(fg_color="#344268")
        self.selected_game_idx = real_idx

        if real_idx < len(self.raw_pgn_games):
            pgn_content = self.raw_pgn_games[real_idx]
            self.text_rationale.delete("1.0", "end")
            self.text_rationale.insert("1.0", pgn_content)

    def _background_apply_filter(self):
        if not self.current_piece_code:
            if hasattr(self, "loading_overlay"):
                self.after(0, self.loading_overlay.close)
            return

        target_color = chess.WHITE if self.current_piece_code.startswith("w") else chess.BLACK
        piece_char = self.current_piece_code[1].upper()
        symbol_map = {'P': chess.PAWN, 'N': chess.KNIGHT, 'B': chess.BISHOP, 'R': chess.ROOK, 'Q': chess.QUEEN, 'K': chess.KING}
        target_piece_symbol = symbol_map.get(piece_char)

        t1, t2 = [], []

        for idx, _ in self.all_games_data:
            if idx >= len(self.raw_pgn_games):
                continue

            if idx not in self.parsed_games_cache:
                game_obj = chess.pgn.read_game(StringIO(self.raw_pgn_games[idx]))
                self.parsed_games_cache[idx] = game_obj

            game = self.parsed_games_cache[idx]
            if game is None:
                continue

            board = game.board()
            first_match_move_str = ""
            found_move_number = None

            for ply_idx, move in enumerate(game.mainline_moves()):
                move_number = (ply_idx // 2) + 1
                is_black = (ply_idx % 2 == 1)
                turn_color = chess.BLACK if is_black else chess.WHITE

                if move_number >= 8:
                    piece = board.piece_at(move.from_square)
                    if piece and piece.piece_type == target_piece_symbol and turn_color == target_color:
                        san_str = board.san(move)
                        first_match_move_str = f"{move_number}...{san_str}" if is_black else f"{move_number}. {san_str}"
                        found_move_number = move_number
                        break
                board.push(move)

            if found_move_number is not None:
                new_row = [first_match_move_str]

                if 8 <= found_move_number <= 15:
                    t1.append((idx, new_row))
                elif 16 <= found_move_number <= 25:
                    t2.append((idx, new_row))

        self.tier1_data = t1
        self.tier2_data = t2
        self.filtered_indices = [item[0] for item in t1 + t2]

        self.after(0, self._finish_apply_filter)

    def _finish_apply_filter(self):
        self.refresh_tree_view()
        if hasattr(self, "loading_overlay"):
            self.loading_overlay.close()

    def export_filtered_to_new_catalog(self):
        target_export_indices = self.filtered_indices

        if not target_export_indices:
            messagebox.showwarning("No Data", "There are not any valid filtered games available to export.")
            return

        parent_dir = os.path.dirname(PATTERNS_FILE)
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

    def save_recipe_node(self, event=None):
        pgn_data = self.text_rationale.get("1.0", "end").strip()
        piece_type = self.current_piece_desc if self.current_piece_desc else "General"

        try:
            if self.selected_game_idx is not None:
                idx = self.selected_game_idx
                if idx < len(self.raw_pgn_games):
                    self.raw_pgn_games[idx] = pgn_data
                    if idx in self.parsed_games_cache:
                        new_game_obj = chess.pgn.read_game(StringIO(pgn_data))
                        if new_game_obj:
                            self.parsed_games_cache[idx] = new_game_obj

            with open(PATTERNS_FILE, "w", encoding="utf-8") as f:
                for game_str in self.raw_pgn_games:
                    f.write(game_str + "\n\n")

            messagebox.showinfo(
                "Saved",
                f"Content successfully saved to {os.path.basename(PATTERNS_FILE)} with active piece attribution: {piece_type}.",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Could not save PGN file: {e}")