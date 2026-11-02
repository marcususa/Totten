import json
import os
import threading
import urllib.request
import urllib.error
import io
import chess
import chess.pgn
import customtkinter as ctk

import gui.app_state as state
from core.constants import THEME

from gui.mixed_collections.edit_navigation import EditNavigationMixin
from gui.mixed_collections.edit_engine import EditEngineMixin
from gui.mixed_collections.edit_constants import load_categories_config

from .edit_layout import EditLayoutMixin
from .edit_data import EditDataMixin


class EditWorkspace(ctk.CTkFrame, EditNavigationMixin, EditEngineMixin, EditLayoutMixin, EditDataMixin):

    CONFIG_FILE = "chess_accounts.json"

    def __init__(self, master, initial_games=None, filename=None, *args, **kwargs):
        super().__init__(master, fg_color=THEME["bg_panel"], corner_radius=0)

        self.categories = load_categories_config()
        print(f"[DEBUG INIT] EditWorkspace loaded categories: {self.categories}")

        self.collection_files = {}
        self.selected_files = []
        self.tree_map = {}
        self.cat_item_map = {}

        # Load saved account configuration from disk
        saved_accounts = self._load_saved_accounts()
        self.cc_saved_username = saved_accounts.get("chess_com", None)
        self.lich_saved_username = saved_accounts.get("lichess", None)

        # Filter box selection states (tracking filled square status for B, R, S, ALL)
        self.cc_filters = {"B": False, "R": False, "S": False, "ALL": True}
        self.lich_filters = {"B": False, "R": False, "S": False, "ALL": True}

        # Initialize base state values before UI building
        numbered_cats = self._get_numbered_categories()
        self._selected_category = numbered_cats[0] if numbered_cats else ""

        # Build all UI components first so attributes exist
        self._configure_styles()
        self._build_ui()

        # Grab from parameters or fallback to state bucket
        self.games_list = initial_games or state.mixed_state.get("active_games") or []
        self.filename = filename or state.mixed_state.get("current_filename")

        if self.filename:
            self.after(50, self.load_catalog_data)
        elif self.games_list:
            self.after(50, lambda: self.load_games_list(self.games_list))
        else:
            def lazy_load():
                raw_choice = self.opt_category.get()
                cat = self._unnumber_category(raw_choice)
                self._load_category_files(cat)
                self._refresh_treeview()

            self.after(50, lazy_load)

        # Clear out state bucket after consumption
        state.mixed_state["active_games"] = None
        state.mixed_state["active_focus"] = None
        state.mixed_state["current_filename"] = None

    def _load_saved_accounts(self):
        """Loads saved usernames from the local JSON config file."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[DEBUG] Error loading accounts config: {e}")
        return {"chess_com": None, "lichess": None}

    def save_account_to_disk(self, platform, username):
        """Saves a platform username to the local JSON config file."""
        accounts = self._load_saved_accounts()
        accounts[platform] = username
        try:
            with open(self.CONFIG_FILE, "w") as f:
                json.dump(accounts, f, indent=4)
        except Exception as e:
            print(f"[DEBUG] Error saving accounts config: {e}")

    def refresh_view(self):
        self._refresh_treeview()


def create_workspace(master, *args, **kwargs):
    """Instantiates EditWorkspace for Stage 1 Mixed Collections navigation."""
    return EditWorkspace(master, *args, **kwargs)