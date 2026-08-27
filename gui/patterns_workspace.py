import io
import json
import os
from pathlib import Path
import threading
import chess
import chess.engine
import chess.pgn
import customtkinter as ctk
import duckdb

# Optional import for rendering SVGs in CustomTkinter via PIL and cairosvg
try:
    from PIL import Image
    from cairosvg import svg2png

    HAS_SVG_SUPPORT = True
except ImportError:
    HAS_SVG_SUPPORT = False

import gui.app_state as state
from gui.statusbar import (
    set_status_message,
)

# 1-3-5 Material Values Setup
PIECE_VALUES = {
    chess.PAWN: 1,
    chess.KNIGHT: 3,
    chess.BISHOP: 3,
    chess.ROOK: 5,
    chess.QUEEN: 9,
    chess.KING: 0,
}


class PatternsWorkspace(ctk.CTkFrame):
    def __init__(self, master, app_state=None, stockfish_path=None):
        super().__init__(master, fg_color="#172134", corner_radius=0)
        self.app_state = app_state or state

        self.db_path = Path("personal_catalog.duckdb")
        self.pgn_path = Path("personal_catalog.pgn")
        self.eco_dir = Path("catalog_eco")

        # Robust Asset Path Resolver with explicit print debugging
        self.assets_dir = self._find_assets_dir()

        root_project_dir = os.path.dirname(os.path.dirname(self.assets_dir))
        self.stockfish_path = (
                stockfish_path
                or os.path.join(root_project_dir, "engines", "stockfish-ubuntu-x86-64-bmi2")
        )

        self.all_games_cache = []
        self.aggregated_tiers = {}

        # State tracking
        self.tier_collapsed = {"tier1": False, "tier2": False, "tier3": False}
        self.selected_piece_filter = None  # Single piece selection
        self.svg_image_cache = {}  # Critical to prevent Garbage Collection of images

        # Three thresholds for 3 tiers (representing the starting move of each tier)
        self.slider_1_val = ctk.IntVar(value=1)
        self.slider_2_val = ctk.IntVar(value=11)
        self.slider_3_val = ctk.IntVar(value=26)

        self._init_db()
        self._build_ui()
        self.after(100, self.check_and_load_catalog)

    def _find_assets_dir(self):
        current = Path(__file__).resolve().parent
        for parent in [current, *current.parents]:
            candidate = parent / "assets" / "pieces"
            if candidate.exists() and candidate.is_dir():
                return str(candidate)

        fallback = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "pieces",
        )
        return fallback

    def _init_db(self):
        """Initializes the DuckDB analytical store for categorized moves and evaluations."""
        try:
            con = duckdb.connect(str(self.db_path))
            con.execute("""
                CREATE TABLE IF NOT EXISTS categorized_moves (
                    game_id VARCHAR,
                    ply INTEGER,
                    fen VARCHAR,
                    move VARCHAR,
                    centipawn_score INTEGER,
                    material_diff INTEGER,
                    phase VARCHAR,
                    material_category VARCHAR
                )
            """)
            con.close()
        except Exception as e:
            print(f"Error connecting to DuckDB at {self.db_path}: {e}")

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.panel = ctk.CTkFrame(self, fg_color="#172134", corner_radius=0)
        self.panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.panel.grid_rowconfigure(0, weight=1)
        self.panel.grid_columnconfigure(0, weight=1)

        self.master_container = ctk.CTkFrame(
            self.panel,
            fg_color="#172134",
            corner_radius=0,
            border_color="#445577",
            border_width=0,
        )
        self.master_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.master_container.grid_propagate(False)

        self.master_container.grid_rowconfigure(0, weight=0)  # Unified Toolbar Area
        self.master_container.grid_rowconfigure(1, weight=1)  # Scrollable Tiers
        self.master_container.grid_columnconfigure(0, weight=1)

        # Unified Toolbar Ring Housing Sliders + Piece Tray Together (Halved padding: 6px / 3px)
        self.unified_toolbar_ring = ctk.CTkFrame(
            self.master_container,
            fg_color="#1e293b",
            corner_radius=6,
            border_color="#334155",
            border_width=1,
        )
        self.unified_toolbar_ring.grid(
            row=0, column=0, sticky="ew", padx=(6, 6), pady=(5, 3)
        )
        self.unified_toolbar_ring.grid_columnconfigure(0, weight=1)

        # Sliders Sub-Container inside unified ring
        self.sliders_frame = ctk.CTkFrame(
            self.unified_toolbar_ring, fg_color="transparent"
        )
        self.sliders_frame.pack(anchor="w", fill="x", padx=6, pady=(6, 2))

        # Slider 1 Container (Opening) - fg_color acts as the right-side fill
        s1_box = ctk.CTkFrame(self.sliders_frame, fg_color="transparent")
        s1_box.pack(side="left", padx=4, pady=2)
        self.lbl_s1 = ctk.CTkLabel(
            s1_box,
            text=f"Opening: {self.slider_1_val.get()}–{self.slider_2_val.get() - 1}",
            font=("Arial", 11, "bold"),
            text_color="#cbd5e1",
        )
        self.lbl_s1.pack(anchor="w", padx=2)
        self.slider_1 = ctk.CTkSlider(
            s1_box,
            from_=1,
            to=20,
            number_of_steps=19,
            variable=self.slider_1_val,
            width=130,
            height=16,
            fg_color="#439462",
            progress_color="#334155",
            button_color="#439462",
            button_hover_color="#34754e",
            command=self.on_slider_changed,
        )
        self.slider_1.pack(anchor="w", padx=2, pady=(2, 0))

        # Slider 2 Container (Middlegame)
        s2_box = ctk.CTkFrame(self.sliders_frame, fg_color="transparent")
        s2_box.pack(side="left", padx=4, pady=2)
        self.lbl_s2 = ctk.CTkLabel(
            s2_box,
            text=f"Middlegame: {self.slider_2_val.get()}–{self.slider_3_val.get() - 1}",
            font=("Arial", 11, "bold"),
            text_color="#cbd5e1",
        )
        self.lbl_s2.pack(anchor="w", padx=2)
        self.slider_2 = ctk.CTkSlider(
            s2_box,
            from_=2,
            to=40,
            number_of_steps=38,
            variable=self.slider_2_val,
            width=130,
            height=16,
            fg_color="#D18228",
            progress_color="#334155",
            button_color="#D18228",
            button_hover_color="#a6661e",
            command=self.on_slider_changed,
        )
        self.slider_2.pack(anchor="w", padx=2, pady=(2, 0))

        # Slider 3 Container (Endgame)
        s3_box = ctk.CTkFrame(self.sliders_frame, fg_color="transparent")
        s3_box.pack(side="left", padx=4, pady=2)
        self.lbl_s3 = ctk.CTkLabel(
            s3_box,
            text=f"Endgame: {self.slider_3_val.get()}+",
            font=("Arial", 11, "bold"),
            text_color="#cbd5e1",
        )
        self.lbl_s3.pack(anchor="w", padx=2)
        self.slider_3 = ctk.CTkSlider(
            s3_box,
            from_=5,
            to=60,
            number_of_steps=55,
            variable=self.slider_3_val,
            width=130,
            height=16,
            fg_color="#C95F5F",
            progress_color="#334155",
            button_color="#C95F5F",
            button_hover_color="#9e4a4a",
            command=self.on_slider_changed,
        )
        self.slider_3.pack(anchor="w", padx=2, pady=(2, 0))

        # SVG Piece Selection Tray (Directly nested underneath sliders inside the same ring)
        self._build_piece_tray()

        # 3. Main Scrollable Tier Results Container (Halved outer side margins to 6px)
        self.cards_scroll_frame = ctk.CTkScrollableFrame(
            self.master_container, fg_color="#172134", corner_radius=0, border_width=0
        )
        self.cards_scroll_frame.grid(
            row=1, column=0, sticky="nsew", padx=6, pady=(0, 5)
        )
        self.cards_scroll_frame.grid_columnconfigure(0, weight=1)

    def _build_piece_tray(self):
        self.tray_frame = ctk.CTkFrame(
            self.unified_toolbar_ring, fg_color="transparent"
        )
        self.tray_frame.pack(anchor="w", fill="x", padx=6, pady=(2, 6))

        tray_inner = ctk.CTkFrame(self.tray_frame, fg_color="transparent")
        tray_inner.pack(anchor="w", padx=2, pady=0)

        pieces = [
            ("wp", "White Pawn"),
            ("wn", "White Knight"),
            ("wb", "White Bishop"),
            ("wr", "White Rook"),
            ("wq", "White Queen"),
            ("wk", "White King"),
            ("bp", "Black Pawn"),
            ("bn", "Black Knight"),
            ("bb", "Black Bishop"),
            ("br", "Black Rook"),
            ("bq", "Black Queen"),
            ("bk", "Black King"),
        ]

        self.piece_buttons = {}
        for code, tooltip in pieces:
            btn = ctk.CTkButton(
                tray_inner,
                text="",
                width=34,
                height=32,
                font=("Arial", 10, "bold"),
                fg_color="#334155",
                hover_color="#2e4a8c",
                command=lambda c=code: self.on_piece_clicked(c),
            )
            btn.pack(side="left", padx=2)
            self.piece_buttons[code] = btn

            svg_path = os.path.join(self.assets_dir, f"{code}.svg")
            if os.path.exists(svg_path) and HAS_SVG_SUPPORT:
                try:
                    png_data = svg2png(url=svg_path, output_width=24, output_height=24)
                    img = Image.open(io.BytesIO(png_data))
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(24, 24))

                    self.svg_image_cache[code] = ctk_img
                    btn.configure(image=ctk_img, text="")
                except Exception as e:
                    print(f"[ERROR] Failed rendering SVG {code}: {e}")
                    btn.configure(text="")
            else:
                btn.configure(text="")

    def on_piece_clicked(self, piece_code):
        if self.selected_piece_filter == piece_code:
            self.selected_piece_filter = None
            self.piece_buttons[piece_code].configure(fg_color="#334155")
        else:
            if (
                    self.selected_piece_filter
                    and self.selected_piece_filter in self.piece_buttons
            ):
                self.piece_buttons[self.selected_piece_filter].configure(
                    fg_color="#334155"
                )
            self.selected_piece_filter = piece_code
            self.piece_buttons[piece_code].configure(fg_color="#2563eb")

        self.recalculate_tiers()

    def on_slider_changed(self, val=None):
        s1 = int(self.slider_1_val.get())
        s2 = int(self.slider_2_val.get())
        s3 = int(self.slider_3_val.get())

        if s1 >= s2:
            s2 = s1 + 1
            self.slider_2_val.set(s2)
        if s2 >= s3:
            s3 = s2 + 1
            self.slider_3_val.set(s3)

        self.lbl_s1.configure(text=f"Opening: {s1}–{s2 - 1}")
        self.lbl_s2.configure(text=f"Middlegame: {s2}–{s3 - 1}")
        self.lbl_s3.configure(text=f"Endgame: {s3}+")
        self.recalculate_tiers()

    def check_and_load_catalog(self):
        eco_exists = self.eco_dir.exists() and any(self.eco_dir.glob("*.pgn"))
        if self.db_path.exists() or self.pgn_path.exists() or eco_exists:
            self.pack_propagate(True)
            self.update_idletasks()
            self.after(50, self.load_catalog_games)
        else:
            self.all_games_cache = []
            self.refresh_ui()

    def load_catalog_games(self):
        set_status_message("Loading games into Patterns Workspace...")

        self.after(
            50,
            lambda: threading.Thread(
                target=self._background_load_worker, daemon=True
            ).start(),
        )

    def _background_load_worker(self):
        loaded_games = []
        try:
            if self.pgn_path.exists():
                with open(self.pgn_path, "r", encoding="utf-8", errors="ignore") as pgn:
                    idx = 0
                    while len(loaded_games) < 300:
                        game = chess.pgn.read_game(pgn)
                        if game is None:
                            break
                        headers = dict(game.headers)
                        ply_count = sum(1 for _ in game.mainline_moves())
                        if ply_count == 0:
                            ply_count = 20 + (idx * 5) % 60

                        loaded_games.append({
                            "headers": headers,
                            "ply_count": ply_count,
                            "game_object": game,
                        })
                        idx += 1
            else:
                con = duckdb.connect(str(self.db_path), read_only=True)
                tables = con.execute("SHOW TABLES").fetchall()
                table_names = [t[0] for t in tables]

                if "catalog_headers" in table_names:
                    rows = con.execute(
                        "SELECT headers_json FROM catalog_headers"
                    ).fetchall()
                    for r in rows:
                        try:
                            h_dict = json.loads(r[0])
                            ply_count_str = h_dict.get(
                                "PlyCount", h_dict.get("TotalPlies", "30")
                            )
                            try:
                                ply_count = int(ply_count_str)
                            except ValueError:
                                ply_count = 30

                            dummy_game = chess.pgn.Game()
                            for k, v in h_dict.items():
                                dummy_game.headers[k] = v

                            loaded_games.append({
                                "headers": h_dict,
                                "ply_count": ply_count,
                                "game_object": dummy_game,
                            })
                        except Exception:
                            pass
                con.close()
        except Exception as e:
            print(f"Error reading pattern games: {e}")

        try:
            self.after(0, lambda: self._finalize_game_load(loaded_games))
        except Exception:
            pass

    def _finalize_game_load(self, loaded_games):
        if not self.winfo_exists():
            return

        self.all_games_cache = loaded_games
        set_status_message(f"Patterns catalog loaded: {len(loaded_games)} games.")

        self.recalculate_tiers()

    def recalculate_tiers(self):
        s1 = int(self.slider_1_val.get())
        s2 = int(self.slider_2_val.get())
        s3 = int(self.slider_3_val.get())

        tier_1, tier_2, tier_3 = [], [], []

        for game in self.all_games_cache:
            game_obj = game.get("game_object")
            if not game_obj:
                continue

            total_moves = int(game["ply_count"] / 2)

            # 1. Determine if game satisfies piece filter criteria per tier window
            if not self.selected_piece_filter:
                # No filter: pure length/phase sorting
                in_t1 = s1 <= total_moves < s2
                in_t2 = s2 <= total_moves < s3
            else:
                # Piece filter active: check which tier windows contain the selected piece move
                color_char = self.selected_piece_filter[0]
                piece_char = self.selected_piece_filter[1].upper()

                board = game_obj.board()
                ply_index = 0
                matched_windows = set()

                for move in game_obj.mainline_moves():
                    piece_moved = board.piece_at(move.from_square)
                    board.push(move)
                    ply_index += 1
                    current_move_num = int((ply_index + 1) / 2)

                    if piece_moved:
                        is_white = piece_moved.color == chess.WHITE
                        p_symbol = piece_moved.symbol().upper()

                        if (color_char == "w" and is_white) or (
                                color_char == "b" and not is_white
                        ):
                            if p_symbol == piece_char:
                                if s1 <= current_move_num < s2:
                                    matched_windows.add(1)
                                elif s2 <= current_move_num < s3:
                                    matched_windows.add(2)
                                elif current_move_num >= s3:
                                    matched_windows.add(3)

                in_t1 = 1 in matched_windows
                in_t2 = 2 in matched_windows
                in_t3_matched = 3 in matched_windows

            # 2. Distribute into tiers ensuring Tier 3 catches the remainder
            assigned_to_t1_or_t2 = False

            if not self.selected_piece_filter:
                if s1 <= total_moves < s2:
                    tier_1.append(game)
                    assigned_to_t1_or_t2 = True
                elif s2 <= total_moves < s3:
                    tier_2.append(game)
                    assigned_to_t1_or_t2 = True
                else:
                    tier_3.append(game)
            else:
                if in_t1:
                    tier_1.append(game)
                    assigned_to_t1_or_t2 = True
                if in_t2:
                    tier_2.append(game)
                    assigned_to_t1_or_t2 = True

                # Tier 3 acts as the catch-all remainder if it didn't fit into T1/T2
                # or if it matched down in the endgame tier window.
                if not assigned_to_t1_or_t2 or in_t3_matched:
                    # Prevent duplicate additions if a game spans multiple rules loosely
                    if game not in tier_3:
                        tier_3.append(game)

        self.aggregated_tiers = {
            "tier1": {
                "label": f"Opening (Moves {s1} – {s2 - 1})",
                "games": tier_1,
                "theme": {"bg": "#1e3324", "fg": "#52B878", "border": "#2D6640"},
            },
            "tier2": {
                "label": f"Middlegame (Moves {s2} – {s3 - 1})",
                "games": tier_2,
                "theme": {"bg": "#2A1F14", "fg": "#FF9F33", "border": "#A6580B"},
            },
            "tier3": {
                "label": f"Endgame / Remainder (Moves {s3}+)",
                "games": tier_3,
                "theme": {"bg": "#331E1E", "fg": "#F87171", "border": "#992D2D"},
            },
        }

        self.refresh_ui()

    def toggle_tier_collapse(self, tier_key):
        self.tier_collapsed[tier_key] = not self.tier_collapsed.get(tier_key, False)
        self.refresh_ui()

    def refresh_ui(self):
        for widget in self.cards_scroll_frame.winfo_children():
            widget.destroy()

        for t_key, t_data in self.aggregated_tiers.items():
            games = t_data["games"]
            theme = t_data["theme"]
            is_collapsed = self.tier_collapsed.get(t_key, False)
            arrow = "▼" if not is_collapsed else "▶"

            tier_frame = ctk.CTkFrame(
                self.cards_scroll_frame,
                fg_color="#172134",
                border_color=theme["border"],
                border_width=2,
                corner_radius=8,
            )
            tier_frame.pack(fill="x", expand=True, padx=2, pady=6)
            tier_frame.grid_columnconfigure(0, weight=1)

            header_btn = ctk.CTkButton(
                tier_frame,
                text=f"{arrow}  {t_data['label']}  ({len(games)} games)",
                anchor="w",
                fg_color=theme["bg"],
                hover_color=theme["border"],
                text_color=theme["fg"],
                font=("Arial", 12, "bold"),
                height=36,
                corner_radius=4,
                command=lambda tk=t_key: self.toggle_tier_collapse(tk),
            )
            header_btn.pack(fill="x", padx=4, pady=4)

            if not is_collapsed:
                preview_container = ctk.CTkFrame(tier_frame, fg_color="transparent")
                preview_container.pack(fill="x", expand=True, padx=8, pady=(0, 6))
                preview_container.grid_columnconfigure(0, weight=1)

                for g in games[:5]:
                    headers = g.get("headers", {})
                    white = headers.get("White", "Unknown")
                    black = headers.get("Black", "Unknown")
                    eco = headers.get("ECO", "A00")

                    game_btn = ctk.CTkButton(
                        preview_container,
                        text=f"    {eco}  |  {white} vs {black}",
                        anchor="w",
                        fg_color="#223049",
                        hover_color="#2d3e5f",
                        text_color="#cbd5e1",
                        font=("Arial", 11),
                        height=28,
                        command=lambda game_item=g: self.send_tier_games_to_analysis(
                            game_item
                        ),
                    )
                    game_btn.pack(fill="x", padx=2, pady=1)

                if len(games) > 5:
                    more_btn = ctk.CTkButton(
                        preview_container,
                        text=f"    ... and {len(games) - 5} more games. Click to open all.",
                        anchor="w",
                        fg_color="transparent",
                        hover_color="#2d3e5f",
                        text_color="#94a3b8",
                        font=("Arial", 10),
                        height=24,
                        command=lambda tk=t_key: self.send_tier_to_analysis(tk),
                    )
                    more_btn.pack(fill="x", padx=2, pady=2)

        spacer = ctk.CTkFrame(
            self.cards_scroll_frame, fg_color="transparent", height=40
        )
        spacer.pack(fill="x", padx=0, pady=0)

    def send_tier_games_to_analysis(self, game_data):
        headers = game_data.get("headers", {})
        white = headers.get("White", "Unknown")
        black = headers.get("Black", "Unknown")
        set_status_message(f"Sending tier to analysis, focused on: {white} vs {black}")

        # Find which tier container holds this game so we can send the full tier list
        full_tier_games = []
        for t_data in self.aggregated_tiers.values():
            if game_data in t_data.get("games", []):
                full_tier_games = t_data["games"]
                break

        # Fallback if it wasn't found in any tier list
        if not full_tier_games:
            full_tier_games = [game_data]

        # Set the active subset to the ENTIRE tier collection
        self.app_state.active_analysis_subset = full_tier_games

        # Store the target game directly on app_state so the analysis side can access it without keyword arguments
        if hasattr(self.app_state, "active_target_game"):
            self.app_state.active_target_game = game_data.get("game_object")

        if hasattr(self.app_state, "patterns_node") and self.app_state.patterns_node:
            self.app_state.current_analysis_node = self.app_state.patterns_node

        if hasattr(self.app_state, "load_games_into_analysis") and callable(
                self.app_state.load_games_into_analysis
        ):
            # Pass the full tier list safely without unexpected keyword arguments
            self.app_state.load_games_into_analysis(full_tier_games)
        elif hasattr(self.app_state, "show_analysis_workspace") and callable(
                self.app_state.show_analysis_workspace
        ):
            self.app_state.show_analysis_workspace()

    def send_tier_to_analysis(self, tier_key):
        tier_info = self.aggregated_tiers.get(tier_key, {})
        games = tier_info.get("games", [])
        set_status_message(
            f"Sending {len(games)} games from"
            f" {tier_info.get('label', tier_key)} to Analysis Section..."
        )

        # Set the active subset to the tier's filtered games list
        self.app_state.active_analysis_subset = games
        if hasattr(self.app_state, "patterns_node") and self.app_state.patterns_node:
            self.app_state.current_analysis_node = self.app_state.patterns_node

        if hasattr(self.app_state, "load_games_into_analysis") and callable(
                self.app_state.load_games_into_analysis
        ):
            self.app_state.load_games_into_analysis(games)
        elif hasattr(self.app_state, "show_analysis_workspace") and callable(
                self.app_state.show_analysis_workspace
        ):
            self.app_state.show_analysis_workspace()