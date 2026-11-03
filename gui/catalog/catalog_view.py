# catalog_view.py
from pathlib import Path
import io
import threading
import customtkinter as ctk
import chess
import chess.pgn
import json
import duckdb

import gui.app_state as state
from gui.statusbar import set_status_message
from core.constants import THEME
from .catalog_loader import CatalogLoaderMixin
from .catalog_search import CatalogSearchMixin
from .catalog_ui_layout import CatalogUIMixin
from .catalog_actions import CatalogActionsMixin


def on_group_selected(self, chosen_games_list):
    state.catalog_state["active_games"] = chosen_games_list
    if hasattr(state, "show_workspace"):
        state.show_workspace("catalog")


class SearchCatalogWorkspace(ctk.CTkFrame, CatalogLoaderMixin, CatalogSearchMixin, CatalogUIMixin, CatalogActionsMixin):
    def __init__(self, master, app_state=None, *args, **kwargs):
        kwargs.pop("app_state", None)
        kwargs.pop("filename", None)
        kwargs.pop("target_game", None)
        kwargs.pop("active_index", None)
        kwargs.pop("initial_games", None)
        super().__init__(master, fg_color=THEME.get("bg_panel"), corner_radius=0, *args, **kwargs)

        self.app_state = app_state or state
        self.root_dir = Path(__file__).resolve().parent.parent.parent

        self.json_path = self.root_dir / "personal_catalog.json"
        self.pgn_path = self.root_dir / "personal_catalog.pgn"
        self.db_path = self.root_dir / "personal_catalog.duckdb"
        self._load_preferences()

        self.eco_list_path = self.root_dir / "pgn" / "eco" / "eco_list.json"
        self.eco_list_fallback = self.root_dir / "eco_list.json"

        self.catalog = {}
        self.aggregated_games_data = []
        self.eco_tree_data = self._load_eco_list_json()

        self.page_size = 12

        if "recent_openings" not in state.catalog_state:
            state.catalog_state["recent_openings"] = []

        self.active_opening_filter = state.catalog_state.get("active_opening_filter", None)

        self.active_primary_tag = "Variation"
        self.active_extra_columns = set()

        self.expanded_groups = set()
        self.group_display_limits = {}
        self.expanded_tree_openings = set()
        self.lazy_loaded_instances = {}

        self._build_ui()

        # 1. Instantly pull the full opening summary via DuckDB GROUP BY
        self.load_catalog_summary_from_duckdb()

        # 2. Rebuild the 12-button grid and tree using the loaded summary
        self._rebuild_opening_grid()

        # 3. Paint the initial view
        self.refresh_current_view()

        # 4. Run secondary checks in background, then refresh counts on the main thread
        def _background_load_wrapper():
            if hasattr(self, "check_and_load_catalog"):
                self.check_and_load_catalog()
            self.after(0, self.load_catalog)

        threading.Thread(target=_background_load_wrapper, daemon=True).start()

    def _load_eco_list_json(self):
        target_path = self.eco_list_path if self.eco_list_path.exists() else self.eco_list_fallback
        if not target_path.exists():
            return {}
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception as e:
            print(f"[ECO List Error] {e}")
        return {}

    def _load_preferences(self):
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    prefs = data.get("preferences", {})
                    if "recent_openings" in prefs:
                        state.catalog_state["recent_openings"] = prefs["recent_openings"]
                    if "active_opening_filter" in prefs:
                        self.active_opening_filter = prefs["active_opening_filter"]
                        state.catalog_state["active_opening_filter"] = self.active_opening_filter
            except Exception as e:
                print(f"[Catalog Prefs Load Error] {e}")

    def _save_preferences(self):
        try:
            data = {}
            if self.json_path.exists():
                try:
                    with open(self.json_path, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            data = loaded
                except Exception:
                    pass

            data["preferences"] = {
                "recent_openings": state.catalog_state.get("recent_openings", []),
                "active_opening_filter": self.active_opening_filter
            }

            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Catalog Prefs Save Error] {e}")

    def load_catalog(self):
        self.aggregated_games_data = []
        self.lazy_loaded_instances.clear()
        self.load_catalog_summary_from_duckdb()
        self._rebuild_opening_grid()
        self.refresh_current_view()

    def load_data(self):
        self.load_catalog()

    def _navigate_to_analysis(self):
        sw_func = None
        if hasattr(state, "show_workspace") and callable(state.show_workspace):
            sw_func = state.show_workspace
        elif hasattr(self.winfo_toplevel(), "show_workspace") and callable(getattr(self.winfo_toplevel(), "show_workspace")):
            sw_func = self.winfo_toplevel().show_workspace
        elif hasattr(self.master, "show_workspace") and callable(getattr(self.master, "show_workspace")):
            sw_func = self.master.show_workspace

        if sw_func:
            for name in ["catalog_analysis", "analysis", "catalog"]:
                try:
                    sw_func(name)
                    return True
                except Exception:
                    continue
        return False