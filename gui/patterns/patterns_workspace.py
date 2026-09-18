# gui/patterns/patterns_workspace.py

import os
from pathlib import Path
import customtkinter as ctk

import gui.app_state as state
from gui.statusbar import set_status_message
from gui.patterns.patterns_colors import WORKSPACE_BG, TOOLBAR_BG, TOOLBAR_BORDER
from gui.patterns.patterns_slider_logic import PatternsSliderLogicMixin
from gui.patterns.patterns_loader import PatternsLoaderMixin


class PatternsWorkspace(ctk.CTkFrame, PatternsSliderLogicMixin, PatternsLoaderMixin):
    def __init__(self, master, app_state=None, stockfish_path=None):
        super().__init__(master, fg_color=WORKSPACE_BG, corner_radius=0)
        self.app_state = app_state or state

        self.db_path = Path("personal_catalog.duckdb")
        self.pgn_path = Path("personal_catalog.pgn")
        self.eco_dir = Path("catalog_eco")

        # Robust Asset Path Resolver
        self.assets_dir = self._find_assets_dir()

        # Retrieve the cross-platform engine path determined by main.py via global state
        available_engines = getattr(state, "available_engines", {})
        self.stockfish_path = stockfish_path or available_engines.get("stockfish")

        self.all_games_cache = []
        self.aggregated_tiers = {}
        self.tier_collapsed = {"tier1": False, "tier2": False, "tier3": False}

        # Starts unselected until the user clicks a piece
        self.selected_piece = None

        self._init_slider_state()
        self._init_db()
        self._build_ui()
        self.after(200, self.check_and_load_catalog)  # Deferred initialization

    def _find_assets_dir(self):
        current = Path(__file__).resolve().parent
        for parent in [current, *current.parents]:
            candidate = parent / "assets" / "pieces"
            if candidate.exists() and candidate.is_dir():
                return str(candidate)

        return os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "assets",
            "pieces",
        )

    def _build_ui(self):
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.panel = ctk.CTkFrame(self, fg_color=WORKSPACE_BG, corner_radius=0)
        self.panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.panel.grid_rowconfigure(0, weight=1)
        self.panel.grid_columnconfigure(0, weight=1)

        self.master_container = ctk.CTkFrame(
            self.panel,
            fg_color=WORKSPACE_BG,
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
            fg_color=TOOLBAR_BG,
            corner_radius=6,
            border_color=TOOLBAR_BORDER,
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
            self.master_container, fg_color=WORKSPACE_BG, corner_radius=0, border_width=0
        )
        self.cards_scroll_frame.grid(
            row=1, column=0, sticky="nsew", padx=6, pady=(0, 5)
        )
        self.cards_scroll_frame.grid_columnconfigure(0, weight=1)

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
                fg_color=WORKSPACE_BG,
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

        # Pass active games, focused game, and active piece selection only if chosen
        selected_piece = getattr(self, "selected_piece", None)

        state.patterns_state["active_games"] = full_tier_games
        state.patterns_state["active_focus"] = target_game
        state.patterns_state["active_index"] = active_index

        if selected_piece:
            state.patterns_state["target_piece"] = selected_piece
        else:
            state.patterns_state.pop("target_piece", None)

        workspace_kwargs = {
            "initial_games": full_tier_games,
            "target_game": target_game,
            "active_index": active_index
        }
        if selected_piece:
            workspace_kwargs["target_piece"] = selected_piece

        if hasattr(state, "show_workspace"):
            state.show_workspace("patterns_analysis", **workspace_kwargs)
        else:
            self.app_state.set_active_patterns_collection(full_tier_games, focused_game=target_game)

    def send_tier_to_analysis(self, tier_key):
        tier_info = self.aggregated_tiers.get(tier_key, {})
        games = tier_info.get("games", [])
        set_status_message(
            f"Sending {len(games)} games from "
            f"{tier_info.get('label', tier_key)} to Analysis Section..."
        )

        selected_piece = getattr(self, "selected_piece", None)

        state.patterns_state["active_games"] = games
        state.patterns_state["active_focus"] = None

        if selected_piece:
            state.patterns_state["target_piece"] = selected_piece
        else:
            state.patterns_state.pop("target_piece", None)

        workspace_kwargs = {"initial_games": games}
        if selected_piece:
            workspace_kwargs["target_piece"] = selected_piece

        if hasattr(state, "show_workspace"):
            state.show_workspace("patterns_analysis", **workspace_kwargs)
        else:
            self.app_state.set_active_patterns_collection(games)


# --- WORKSPACE FACTORY FUNCTION ---

def create_patterns_workspace(master, *args, **kwargs):
    """Factory function to instantiate and grid the PatternsWorkspace."""
    instance = PatternsWorkspace(master, *args, **kwargs)
    instance.grid(row=0, column=0, sticky="nsew")
    return instance