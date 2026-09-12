# gui/patterns_workspace.py

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
from gui.statusbar import set_status_message

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

        # Robust Asset Path Resolver
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
        self.svg_image_cache = {}  # Prevent Garbage Collection of images

        # Debounce and update flags
        self._slider_timer = None
        self._updating_sliders = False

        # Three thresholds for 3 tiers (representing the starting move of each tier)
        self.slider_1_val = ctk.IntVar(value=1)
        self.slider_2_val = ctk.IntVar(value=11)
        self.slider_3_val = ctk.IntVar(value=26)

        self._init_db()
        self._build_ui()
        self.after(200, self.check_and_load_catalog)  # Deferred initialization

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

        # Unified Toolbar Ring Housing Sliders + Piece Tray Together
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

        # Slider 1 Container (Opening)
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

        # SVG Piece Selection Tray
        self._build_piece_tray()

        # Main Scrollable Tier Results Container
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
        if self._updating_sliders:
            return

        self._updating_sliders = True
        try:
            s1 = int(self.slider_1_val.get())
            s2 = int(self.slider_2_val.get())
            s3 = int(self.slider_3_val.get())

            if s1 >= s2:
                s2 = s1 + 1
                self.slider_2_val.set(s2)
            if s2 >= s3:
                s3 = s2 + 1
                self.slider_3_val.set(s3)

            # Instantly update textual feedback for smooth dragging feel
            self.lbl_s1.configure(text=f"Opening: {s1}–{s2 - 1}")
            self.lbl_s2.configure(text=f"Middlegame: {s2}–{s3 - 1}")
            self.lbl_s3.configure(text=f"Endgame: {s3}+")
        finally:
            self._updating_sliders = False

        # Debounce the expensive tier recalculation & UI rebuild
        if self._slider_timer:
            self.after_cancel(self._slider_timer)
        self._slider_timer = self.after(150, self.recalculate_tiers)

    def check_and_load_catalog(self):
        eco_exists = self.eco_dir.exists() and any(self.eco_dir.glob("*.pgn"))
        if self.db_path.exists() or self.pgn_path.exists() or eco_exists:
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

                        # Compute piece plies off the main GUI thread for fast indexing
                        board = game.board()
                        piece_plies = {}
                        ply_idx = 0
                        for move in game.mainline_moves():
                            piece = board.piece_at(move.from_square)
                            board.push(move)
                            ply_idx += 1
                            if piece:
                                color_char = "w" if piece.color == chess.WHITE else "b"
                                piece_char = piece.symbol().lower()
                                code = f"{color_char}{piece_char}"
                                move_num = (ply_idx + 1) // 2
                                if code not in piece_plies:
                                    piece_plies[code] = set()
                                piece_plies[code].add(move_num)

                        ply_count = ply_idx if ply_idx > 0 else (20 + (idx * 5) % 60)

                        loaded_games.append({
                            "headers": headers,
                            "ply_count": ply_count,
                            "game_object": game,
                            "piece_plies": piece_plies,
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
                                "piece_plies": {},
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
        self._slider_timer = None

        s1 = int(self.slider_1_val.get())
        s2 = int(self.slider_2_val.get())
        s3 = int(self.slider_3_val.get())

        tier_1, tier_2, tier_3 = [], [], []

        for game in self.all_games_cache:
            total_moves = int(game["ply_count"] / 2)

            if not self.selected_piece_filter:
                in_t1 = s1 <= total_moves < s2
                in_t2 = s2 <= total_moves < s3
                in_t3_matched = total_moves >= s3
            else:
                piece_plies = game.get("piece_plies", {})
                matched_moves = piece_plies.get(self.selected_piece_filter, set())

                in_t1 = any(s1 <= m < s2 for m in matched_moves)
                in_t2 = any(s2 <= m < s3 for m in matched_moves)
                in_t3_matched = any(m >= s3 for m in matched_moves)

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

                if not assigned_to_t1_or_t2 or in_t3_matched:
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

        full_tier_games = []
        for t_data in self.aggregated_tiers.values():
            if game_data in t_data.get("games", []):
                full_tier_games = t_data["games"]
                break

        if not full_tier_games:
            full_tier_games = [game_data]

        target_game = game_data.get("game_object")

        # Find the exact index of the clicked game within the tier list
        active_index = 0
        try:
            active_index = full_tier_games.index(game_data)
        except ValueError:
            for idx, g in enumerate(full_tier_games):
                if g == game_data or (
                        isinstance(g, dict) and isinstance(game_data, dict) and g.get("game_object") == game_data.get(
                        "game_object")):
                    active_index = idx
                    break

        # Explicitly set state and trigger workspace switch with active_index payload
        state.patterns_state["active_games"] = full_tier_games
        state.patterns_state["active_focus"] = target_game
        state.patterns_state["active_index"] = active_index

        if hasattr(state, "show_workspace"):
            state.show_workspace(
                "patterns_analysis",
                initial_games=full_tier_games,
                target_game=target_game,
                active_index=active_index
            )
        else:
            self.app_state.set_active_patterns_collection(full_tier_games, focused_game=target_game)

    def send_tier_to_analysis(self, tier_key):
        tier_info = self.aggregated_tiers.get(tier_key, {})
        games = tier_info.get("games", [])
        set_status_message(
            f"Sending {len(games)} games from "
            f"{tier_info.get('label', tier_key)} to Analysis Section..."
        )

        # Explicitly set state and trigger workspace switch with payload
        state.patterns_state["active_games"] = games
        state.patterns_state["active_focus"] = None
        if hasattr(state, "show_workspace"):
            state.show_workspace("patterns_analysis", initial_games=games)
        else:
            self.app_state.set_active_patterns_collection(games)


# --- WORKSPACE FACTORY FUNCTION ---

def create_patterns_workspace(master, *args, **kwargs):
    """Factory function to instantiate and grid the PatternsWorkspace."""
    instance = PatternsWorkspace(master, *args, **kwargs)
    instance.grid(row=0, column=0, sticky="nsew")
    return instance