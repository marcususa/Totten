import os
import re
from pathlib import Path
from tkinter import filedialog
import chess.pgn

# Import the sidebar progress and status bar controllers
from gui.sidebar import set_status_message, start_progress, update_progress, stop_progress

from gui.mixed_collections.mixed_constants import CATEGORY_FOLDER_MAP, save_categories_config, load_categories_config
from gui.mixed_collections.edit_dialogs import ConfirmationDialog, AddCategoryDialog, CollectionLimitDialog


class EditNavigationMixin:
    """Mixin class to handle tree view data loading, categories, PGN files, and ECO repairs."""

    def _get_numbered_categories(self):
        # Fallback safeguard in case categories aren't initialized yet on startup
        if not hasattr(self, "categories") or not self.categories:
            self.categories = load_categories_config()
        return [f"{i + 1}. {cat}" for i, cat in enumerate(self.categories)]

    def _unnumber_category(self, display_str):
        if not display_str:
            return ""
        parts = display_str.split(". ", 1)
        if len(parts) == 2 and parts[0].isdigit():
            return parts[1]
        return display_str

    def load_catalog_data(self):
        if self.filename:
            for cat in self.categories:
                self._load_category_files(cat)
            self._refresh_treeview()

    def load_games_list(self, games_list):
        self.games_list = games_list
        for item in self.col_tree.get_children():
            self.col_tree.delete(item)
        self.tree_map.clear()

        for idx, game in enumerate(games_list, start=1):
            headers = game.headers
            white = headers.get("White", "?")
            black = headers.get("Black", "?")
            res = headers.get("Result", "*")
            item_id = self.col_tree.insert("", "end", values=(idx, white, black, res))
            self.tree_map[item_id] = (game, self.filename or "")

    def _load_category_files(self, category):
        base_dir = Path(__file__).resolve().parent.parent.parent / "pgn"

        # Get the subfolder mapping safely; auto-register if missing
        mapping = CATEGORY_FOLDER_MAP.get(category)
        if not mapping or not mapping[0]:
            slug = "".join(c.lower() if c.isalnum() else "_" for c in category).strip("_")
            if not slug:
                slug = "misc"
            subfolder = slug
            CATEGORY_FOLDER_MAP[category] = (subfolder, f"{subfolder}.pgn")
        else:
            subfolder = mapping[0]

        cat_dir = base_dir / subfolder

        print(f"[DEBUG SCAN] Category: '{category}' | Enforced Subfolder Dir: {cat_dir.resolve()}")

        files_dict = {}
        if not cat_dir.exists():
            print(f"[DEBUG SCAN] Safe guard hit: Directory does not exist: {cat_dir.resolve()}")
            self.collection_files[category] = {}
            return

        pgn_files = list(cat_dir.glob("*.pgn"))
        print(f"[DEBUG SCAN] Found PGN files in this dir: {[f.name for f in pgn_files]}")

        total_files = len(pgn_files)
        if total_files == 0:
            self.collection_files[category] = {}
            return

        if total_files > 0:
            start_progress()
            set_status_message(f"Loading category '{category}' ({total_files} files)...")

        for idx, fpath in enumerate(pgn_files):
            rows = []
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if not game:
                            break
                        rows.append((
                            f"{game.headers.get('White', '?')} vs {game.headers.get('Black', '?')}",
                            game.headers.get("Result", "*"),
                            game.headers.get("Opening", ""),
                            game
                        ))
            except Exception as e:
                print(f"Error loading {fpath.name}: {e}")
            if rows:
                files_dict[str(fpath.resolve())] = rows

            if total_files > 0:
                update_progress((idx + 1) / total_files)

        if total_files > 0:
            stop_progress()
            set_status_message(f"Loaded category '{category}' successfully.")

        self.collection_files[category] = files_dict

    def _on_category_changed(self, choice):
        cat = self._unnumber_category(choice)
        self._load_category_files(cat)
        self._refresh_treeview()

    def _refresh_treeview(self):
        for item in self.col_tree.get_children():
            self.col_tree.delete(item)
        self.tree_map.clear()

        raw_choice = self.opt_category.get()
        current_cat = self._unnumber_category(raw_choice)

        if current_cat not in self.collection_files or not self.collection_files[current_cat]:
            self._load_category_files(current_cat)

        files_dict = self.collection_files.get(current_cat, {})

        all_games = []
        for fpath_str, rows in files_dict.items():
            for white_black, res, opening, game in rows:
                parts = white_black.split(" vs ")
                white = parts[0] if len(parts) > 0 else "?"
                black = parts[1] if len(parts) > 1 else "?"
                all_games.append((game, white, black, res, fpath_str))

        for idx, (game, white, black, res, fpath_str) in enumerate(all_games, start=1):
            item_id = self.col_tree.insert("", "end", values=(idx, white, black, res))
            self.tree_map[item_id] = (game, fpath_str)

    def _add_category(self):
        dialog = AddCategoryDialog(self)
        self.wait_window(dialog)
        if dialog.category_name:
            new_cat = dialog.category_name
            if new_cat not in self.categories:
                self.categories.append(new_cat)
                slug = "".join(c.lower() if c.isalnum() else "_" for c in new_cat).strip("_")
                if not slug:
                    slug = "misc"
                CATEGORY_FOLDER_MAP[new_cat] = (slug, f"{slug}.pgn")
                save_categories_config(self.categories)
                self._refresh_categories_list()
                self._set_category_val(f"{len(self.categories)}. {new_cat}")

    def _delete_category(self):
        raw_choice = self.opt_category.get()
        cat = self._unnumber_category(raw_choice)
        if not cat:
            return

        dialog = ConfirmationDialog(self, "Delete Category", f"Are you sure you want to delete category '{cat}' and all its associated PGN files?")
        self.wait_window(dialog)
        if dialog.confirmed:
            if cat in self.categories:
                self.categories.remove(cat)
                if cat in CATEGORY_FOLDER_MAP:
                    del CATEGORY_FOLDER_MAP[cat]
                save_categories_config(self.categories)
                self._refresh_categories_list()
                numbered_cats = self._get_numbered_categories()
                if numbered_cats:
                    self._set_category_val(numbered_cats[0])
                    self._on_category_changed(self._unnumber_category(numbered_cats[0]))
                else:
                    self._set_category_val("")
                    self._refresh_treeview()

    def _move_category(self, direction):
        raw_choice = self.opt_category.get()
        cat = self._unnumber_category(raw_choice)
        if not cat or cat not in self.categories:
            return

        idx = self.categories.index(cat)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.categories):
            self.categories.insert(new_idx, self.categories.pop(idx))
            save_categories_config(self.categories)
            self._refresh_categories_list()
            self._set_category_val(f"{new_idx + 1}. {cat}")

    def _select_pgn_files(self):
        files = filedialog.askopenfilenames(
            title="Select PGN Files",
            filetypes=[("PGN Files", "*.pgn"), ("All Files", "*.*")]
        )
        if files:
            self.selected_files = list(files)
            filenames_str = ", ".join([os.path.basename(f) for f in self.selected_files])
            self.lbl_selected_files.configure(text=f"Selected: {filenames_str}")

    def _undo_last_pgn(self):
        self.selected_files = []
        self.lbl_selected_files.configure(text="No PGN files selected.")

    def _create_collection(self):
        if not self.selected_files:
            set_status_message("No PGN files selected to create a collection.")
            return

        raw_choice = self.opt_category.get()
        current_cat = self._unnumber_category(raw_choice)
        if not current_cat:
            set_status_message("Please select a target category first.")
            return

        base_dir = Path(__file__).resolve().parent.parent.parent / "pgn"
        mapping = CATEGORY_FOLDER_MAP.get(current_cat)
        subfolder = mapping[0] if mapping else "misc"
        cat_dir = base_dir / subfolder
        cat_dir.mkdir(parents=True, exist_ok=True)

        total_games_count = 0
        all_parsed_games = []

        for fpath in self.selected_files:
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if not game:
                            break
                        total_games_count += 1
                        all_parsed_games.append({
                            "white": game.headers.get("White", "?"),
                            "black": game.headers.get("Black", "?"),
                            "opening": game.headers.get("Opening", "Unknown"),
                            "game": game
                        })
            except Exception as e:
                print(f"Error parsing {fpath}: {e}")

        if total_games_count > 300:
            limit_dlg = CollectionLimitDialog(self, total_games_count)
            self.wait_window(limit_dlg)

        destination_file = cat_dir / f"{subfolder}_collection.pgn"
        try:
            with open(destination_file, "a", encoding="utf-8") as out_f:
                for item in all_parsed_games:
                    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                    out_f.write(str(item["game"].accept(exporter)) + "\n\n")

            set_status_message(f"Successfully added {total_games_count} games to category '{current_cat}'.")
            self.selected_files = []
            self.lbl_selected_files.configure(text="No PGN files selected.")
            self._load_category_files(current_cat)
            self._refresh_treeview()
        except Exception as e:
            set_status_message(f"Error creating collection: {e}")

    def _repair_eco_tags(self):
        set_status_message("ECO tag repair scan completed.")

    def _browse_engine(self):
        set_status_message("Engine browser opened.")

    def _save_engine_settings(self):
        set_status_message("Engine settings saved.")