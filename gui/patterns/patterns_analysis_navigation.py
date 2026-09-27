# gui/patterns/patterns_analysis_navigation.py

from collections import Counter
import chess
import chess.pgn
from pathlib import Path
import gui.app_state as state


class PatternsAnalysisNavigationMixin:
    """Encapsulates catalog tree management, game node resolution, and ECO filtering."""

    def load_catalog_data(self):
        if self.game_list:
            if hasattr(self, "pgn_tree"):
                active_game = None
                if hasattr(state, "catalog_state") and "active_index" in state.catalog_state:
                    idx = state.catalog_state.get("active_index", 0)
                    if 0 <= idx < len(self.game_list):
                        active_game = self.game_list[idx]

                self.populate_catalog_tree(self.game_list, active_game=active_game)
            return

        source_games = []
        catalog_path = self.filename

        if Path(catalog_path).exists():
            try:
                with open(catalog_path, "r", encoding="utf-8", errors="replace") as f:
                    while True:
                        g = chess.pgn.read_game(f)
                        if g is None:
                            break
                        source_games.append(g)
                self.game_list = source_games
                if hasattr(state, "all_games"):
                    state.all_games = source_games
            except Exception as e:
                print(f"[CATALOG ANALYSIS DEBUG] Error reading catalog file: {e}")

        if self.game_list and hasattr(self, "pgn_tree"):
            self.populate_catalog_tree(self.game_list)
            self.load_game(self.game_list[0])

    def populate_catalog_tree(self, games_to_display, active_game=None):
        if not hasattr(self, "pgn_tree") or not hasattr(self, "preview_lookup"):
            return

        self.pgn_tree.delete(*self.pgn_tree.get_children())
        self.preview_lookup.clear()

        if hasattr(self, "lbl_empty_state") and self.lbl_empty_state and games_to_display:
            try:
                self.lbl_empty_state.pack_forget()
            except Exception:
                pass

        # Step 1: Count frequency of each ECO code
        eco_counts = Counter(
            (getattr(self._resolve_game_obj(g), "headers", {}) or {}).get("ECO", "Unclassified")
            for g in games_to_display
        )

        # Step 2: Multi-level sort: Primary by frequency (descending), Secondary by ECO string (alphabetical)
        sorted_games = sorted(
            games_to_display,
            key=lambda g: (
                -eco_counts[(getattr(self._resolve_game_obj(g), "headers", {}) or {}).get("ECO", "Unclassified")],
                (getattr(self._resolve_game_obj(g), "headers", {}) or {}).get("ECO", "Unclassified")
            )
        )

        resolved_active = self._resolve_game_obj(active_game)
        target = resolved_active or (self._resolve_game_obj(sorted_games[0]) if sorted_games else None)

        seen_ecos = set()

        for g_raw in sorted_games:
            g_obj = self._resolve_game_obj(g_raw)
            headers = getattr(g_obj, "headers", {})
            white = headers.get("White", "Unknown") if hasattr(headers, "get") else "Unknown"
            black = headers.get("Black", "Unknown") if hasattr(headers, "get") else "Unknown"
            result = headers.get("Result", "*") if hasattr(headers, "get") else "*"
            eco = headers.get("ECO", "???") if hasattr(headers, "get") else "???"

            # First instance shows ECO code; subsequent instances leave the first column blank for easy scanning
            if eco not in seen_ecos:
                seen_ecos.add(eco)
                display_label = eco
            else:
                display_label = ""

            item_id = self.pgn_tree.insert("", "end", values=(display_label, white, black, result))
            self.preview_lookup[item_id] = g_raw

            if target and (g_obj == target or g_raw == active_game):
                self.pgn_tree.selection_set(item_id)
                self.pgn_tree.see(item_id)

        if target:
            self.pgn_tree.yview_moveto(0.0)
            self.after_idle(lambda: self.pgn_tree.yview_moveto(0.0))
            self.after(50, self.focus_set)

    def load_games_by_eco(self, eco_code, active_game=None):
        if not eco_code:
            return

        eco_clean = str(eco_code).strip().upper()

        if not self.game_list and hasattr(state, "all_games") and state.all_games:
            self.game_list = state.all_games
        elif not self.game_list:
            self.load_catalog_data()

        eco_games = []
        for g in self.game_list:
            g_obj = self._resolve_game_obj(g)
            headers = getattr(g_obj, "headers", {})
            eco_val = headers.get("ECO", "") if hasattr(headers, "get") else ""
            if eco_val.strip().upper() == eco_clean:
                eco_games.append(g)

        target_game = active_game or (eco_games[0] if eco_games else None)

        if eco_games:
            if hasattr(state, "active_category_source"):
                state.active_category_source = eco_games

        self.populate_catalog_tree(eco_games, active_game=target_game)