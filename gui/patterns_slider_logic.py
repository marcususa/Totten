# gui/patterns/patterns_slider_logic.py

import os
import io
import customtkinter as ctk
from .patterns_colors import TIER_THEMES

# Optional import for rendering SVGs in CustomTkinter via PIL and cairosvg
try:
    from PIL import Image
    from cairosvg import svg2png
    HAS_SVG_SUPPORT = True
except ImportError:
    HAS_SVG_SUPPORT = False


class PatternsSliderLogicMixin:
    """Encapsulates piece tray selection, slider throttling, and tier calculation mechanics."""

    def _init_slider_state(self):
        self.selected_piece_filter = None
        self.svg_image_cache = {}

        self._slider_timer = None
        self._updating_sliders = False

        self.slider_1_val = ctk.IntVar(value=1)
        self.slider_2_val = ctk.IntVar(value=11)
        self.slider_3_val = ctk.IntVar(value=26)
        self.piece_buttons = {}

    def _build_piece_tray(self):
        self.tray_frame = ctk.CTkFrame(self.unified_toolbar_ring, fg_color="transparent")
        self.tray_frame.pack(anchor="w", fill="x", padx=6, pady=(2, 6))

        tray_inner = ctk.CTkFrame(self.tray_frame, fg_color="transparent")
        tray_inner.pack(anchor="w", padx=2, pady=0)

        pieces = [
            ("wp", "White Pawn"), ("wn", "White Knight"), ("wb", "White Bishop"),
            ("wr", "White Rook"), ("wq", "White Queen"), ("wk", "White King"),
            ("bp", "Black Pawn"), ("bn", "Black Knight"), ("bb", "Black Bishop"),
            ("br", "Black Rook"), ("bq", "Black Queen"), ("bk", "Black King"),
        ]

        for code, tooltip in pieces:
            btn = ctk.CTkButton(
                tray_inner, text="", width=34, height=32,
                font=("Arial", 10, "bold"), fg_color="#334155",
                hover_color="#2e4a8c",
                command=lambda c=code: self.on_piece_clicked(c)
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
            if self.selected_piece_filter and self.selected_piece_filter in self.piece_buttons:
                self.piece_buttons[self.selected_piece_filter].configure(fg_color="#334155")
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

            self.lbl_s1.configure(text=f"Opening: {s1}–{s2 - 1}")
            self.lbl_s2.configure(text=f"Middlegame: {s2}–{s3 - 1}")
            self.lbl_s3.configure(text=f"Endgame: {s3}+")
        finally:
            self._updating_sliders = False

        if self._slider_timer:
            self.after_cancel(self._slider_timer)
        self._slider_timer = self.after(150, self.recalculate_tiers)

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
                "theme": TIER_THEMES["tier1"],
            },
            "tier2": {
                "label": f"Middlegame (Moves {s2} – {s3 - 1})",
                "games": tier_2,
                "theme": TIER_THEMES["tier2"],
            },
            "tier3": {
                "label": f"Endgame / Remainder (Moves {s3}+)",
                "games": tier_3,
                "theme": TIER_THEMES["tier3"],
            },
        }

        self.refresh_ui()