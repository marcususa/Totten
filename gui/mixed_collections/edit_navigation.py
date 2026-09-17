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

    def _select_pgn_files(self):
        base_dir = Path(__file__).resolve().parent.parent.parent / "pgn"
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)

        mapping = CATEGORY_FOLDER_MAP.get(cat)
        sub = mapping[0] if mapping else ""
        init_dir = base_dir / sub if sub else base_dir

        files = filedialog.askopenfilenames(
            title="Select PGN Files",
            initialdir=str(init_dir) if init_dir.exists() else str(base_dir),
            filetypes=[("PGN Files", "*.pgn"), ("All Files", "*.*")]
        )
        if files:
            self.selected_files.extend(list(files))
            self.lbl_selected_files.configure(text=f"{len(self.selected_files)} PGN file(s) selected.")
            if not self.btn_undo_pgn.winfo_ismapped():
                self.btn_undo_pgn.pack(side="left", padx=(0, 3), before=self.btn_select_pgns)

    def _undo_last_pgn(self):
        if self.selected_files:
            self.selected_files.pop()
            if self.selected_files:
                self.lbl_selected_files.configure(text=f"{len(self.selected_files)} PGN file(s) selected.")
            else:
                self.lbl_selected_files.configure(text="No PGN files selected.")
                self.btn_undo_pgn.pack_forget()

    def _add_category(self):
        dialog = AddCategoryDialog(self)
        self.wait_window(dialog)
        if dialog.category_name and dialog.category_name not in self.categories:
            cat = dialog.category_name
            self.categories.append(cat)

            # Ensure custom categories always get a dedicated subfolder slug and entry mapping
            slug = "".join(c.lower() if c.isalnum() else "_" for c in cat).strip("_")
            if not slug:
                slug = "custom_cat"

            CATEGORY_FOLDER_MAP[cat] = (slug, f"{slug}.pgn")

            save_categories_config(self.categories)

            # Refresh the categories tree view list on the UI
            if hasattr(self, "_refresh_categories_list"):
                self._refresh_categories_list()

            numbered_cats = self._get_numbered_categories()
            for nc in numbered_cats:
                if self._unnumber_category(nc) == cat:
                    self.opt_category.set(nc)
                    break

            self._load_category_files(cat)
            self._refresh_treeview()

    def _delete_category(self):
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        if not cat: return
        dialog = ConfirmationDialog(self, "Delete Category",
                                    f"Are you sure you want to delete category '{cat}' and its physical files?")
        self.wait_window(dialog)
        if dialog.confirmed and cat in self.categories:
            self.categories.remove(cat)
            save_categories_config(self.categories)

            # Physically remove the subfolder and its PGN files
            try:
                base_dir = Path(__file__).resolve().parent.parent.parent / "pgn"
                mapping = CATEGORY_FOLDER_MAP.get(cat)
                slug = mapping[0] if mapping else "".join(c.lower() if c.isalnum() else "_" for c in cat).strip("_")
                cat_dir = base_dir / slug

                if cat_dir.exists() and cat_dir != base_dir:
                    for f in cat_dir.glob("*.*"):
                        f.unlink()
                    cat_dir.rmdir()
                    print(f"[DEBUG] Successfully removed physical category folder: {cat_dir}")
            except Exception as e:
                print(f"[DEBUG] Error removing category directory: {e}")

            if hasattr(self, "_refresh_categories_list"):
                self._refresh_categories_list()

            numbered_cats = self._get_numbered_categories()
            self.opt_category.set(numbered_cats[0] if numbered_cats else "")
            self._load_category_files(self._unnumber_category(numbered_cats[0]) if numbered_cats else "")
            self._refresh_treeview()

    def _delete_selected_pgn_file(self):
        set_status_message("Individual PGN game deletion is deferred to a future update.")

    def _move_category(self, direction):
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        if not cat or cat not in self.categories: return
        idx = self.categories.index(cat)
        new_idx = idx + direction
        if 0 <= new_idx < len(self.categories):
            self.categories.insert(new_idx, self.categories.pop(idx))
            save_categories_config(self.categories)

            if hasattr(self, "_refresh_categories_list"):
                self._refresh_categories_list()

            numbered_cats = self._get_numbered_categories()
            for nc in numbered_cats:
                if self._unnumber_category(nc) == cat:
                    self.opt_category.set(nc)
                    break
            self._refresh_treeview()

    def _create_collection(self):
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        if not cat:
            set_status_message("No category selected.")
            return

        if not self.selected_files:
            set_status_message(f"No PGNs selected to append to {cat}.")
            return

        try:
            games_to_append = []
            total_selected = len(self.selected_files)

            start_progress()
            set_status_message(f"Reading and analyzing {total_selected} selected PGN file(s)...")

            for idx, fpath in enumerate(self.selected_files):
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if not game:
                            break
                        games_to_append.append(game)
                update_progress((idx + 1) / total_selected * 0.5)

            stop_progress()

            if len(games_to_append) > 1000:
                limit_dialog = CollectionLimitDialog(self, len(games_to_append))
                self.wait_window(limit_dialog)
                set_status_message("Import halted: Collection exceeds performance recommendation limits.")
                return

            base_dir = Path(__file__).resolve().parent.parent.parent / "pgn"
            mapping = CATEGORY_FOLDER_MAP.get(cat, ("", "collection.pgn"))
            subfolder, default_filename = mapping if mapping else ("", "collection.pgn")
            target_dir = base_dir / subfolder if subfolder else base_dir
            target_dir.mkdir(parents=True, exist_ok=True)
            target_file = target_dir / default_filename

            start_progress()
            set_status_message(f"Appending games to {target_file.name}...")
            with open(target_file, "a", encoding="utf-8") as out_f:
                out_f.seek(0, os.SEEK_END)
                if out_f.tell() > 0:
                    out_f.write("\n\n")
                for i, game in enumerate(games_to_append):
                    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
                    out_f.write(str(game.accept(exporter)) + "\n\n")
                    if len(games_to_append) > 0 and i % max(1, len(games_to_append) // 10) == 0:
                        update_progress(0.5 + (i + 1) / len(games_to_append) * 0.5)

            stop_progress()
            set_status_message(
                f"Successfully appended {len(games_to_append)} game(s) to {target_file.name} under {cat}.")
            self.selected_files.clear()
            self.lbl_selected_files.configure(text="No PGN files selected.")
            self.btn_undo_pgn.pack_forget()

            self._load_category_files(cat)
            self._refresh_treeview()
        except Exception as e:
            stop_progress()
            set_status_message(f"Error appending collection: {e}")

    def _repair_eco_tags(self):
        raw_cat = self.opt_category.get()
        cat = self._unnumber_category(raw_cat)
        if not cat:
            set_status_message("No category selected for ECO repair.")
            return

        base_dir = Path(__file__).resolve().parent.parent.parent / "pgn"
        mapping = CATEGORY_FOLDER_MAP.get(cat, ("", f"{cat}.pgn"))
        subfolder, default_filename = mapping if mapping else ("", f"{cat}.pgn")
        target_dir = base_dir / subfolder if subfolder else base_dir
        target_file = target_dir / default_filename

        if not target_file.exists():
            set_status_message(f"Category PGN file not found: {target_file}")
            return

        parent_root = base_dir.parent
        eco_path = parent_root / "pgn" / "eco" / "eco.pgn"
        if not eco_path.exists():
            eco_path = base_dir / "eco.pgn"

        if not eco_path.exists():
            set_status_message("eco.pgn database not found.")
            return

        def extract_tags(text):
            eco_match = re.search(r'ECO\s*["\']?([A-E]\d{2})["\']?', text, re.IGNORECASE)
            open_match = re.search(r'Opening\s*["\']([^"\']+)["\']', text, re.IGNORECASE)
            var_match = re.search(r'Variation\s*["\']([^"\']+)["\']', text, re.IGNORECASE)

            eco = eco_match.group(1).upper() if eco_match else None
            opening = open_match.group(1).strip() if open_match else None
            variation = var_match.group(1).strip() if var_match else None
            return eco, opening, variation

        eco_map = {}
        try:
            start_progress()
            set_status_message("Loading ECO database...")
            with open(eco_path, "r", encoding="utf-8", errors="ignore") as f:
                eco_content = f.read()

            blocks = re.split(r'\n\s*\n', eco_content)
            total_blocks = len(blocks)
            for idx, block in enumerate(blocks):
                eco, opening, variation = extract_tags(block)
                if eco and opening:
                    eco_map[eco] = (opening, variation)
                if total_blocks > 0 and idx % 100 == 0:
                    update_progress((idx + 1) / total_blocks * 0.3)
        except Exception as e:
            print(f"[DEBUG] Error reading eco.pgn: {e}")

        def lookup_eco(target_eco, available_ecos):
            if not target_eco:
                return None, None
            if target_eco in eco_map:
                return eco_map[target_eco]

            m = re.match(r'([A-E])(\d{2})', target_eco)
            if not m:
                return None, None

            prefix, num_str = m.groups()
            target_num = int(num_str)

            for d in range(1, 10):
                test_code = f"{prefix}{target_num + d:02d}"
                if test_code in eco_map:
                    return eco_map[test_code]

            for d in range(1, 10):
                test_code = f"{prefix}{target_num - d:02d}"
                if test_code in eco_map:
                    return eco_map[test_code]

            return None, None

        repaired_count = 0
        try:
            set_status_message(f"Scanning & repairing ECO tags in {target_file.name}...")
            with open(target_file, "r", encoding="utf-8", errors="ignore") as f:
                target_content = f.read()

            game_blocks = re.split(r'\n\s*\n(?=\[)', target_content)
            total_games = len(game_blocks)
            modified_blocks = []
            file_modified = False

            for idx, block in enumerate(game_blocks):
                eco, current_opening, current_variation = extract_tags(block)

                if eco:
                    db_opening, db_variation = lookup_eco(eco, eco_map)

                    if db_opening:
                        block_modified_local = False

                        if not current_opening or current_opening in ("", "?"):
                            if 'Opening' in block:
                                block = re.sub(r'(Opening\s*["\'])[^\"\']*(["\'])', rf'\1{db_opening}\2', block,
                                               flags=re.IGNORECASE)
                            else:
                                block = f'[Opening "{db_opening}"]\n' + block
                            block_modified_local = True

                        if db_variation and (not current_variation or current_variation in ("", "?")):
                            if 'Variation' in block:
                                block = re.sub(r'(Variation\s*["\'])[^\"\']*(["\'])', rf'\1{db_variation}\2', block,
                                               flags=re.IGNORECASE)
                            else:
                                block = f'[Variation "{db_variation}"]\n' + block
                            block_modified_local = True

                        if block_modified_local:
                            file_modified = True
                            repaired_count += 1

                modified_blocks.append(block)
                if total_games > 0:
                    update_progress(0.3 + (idx + 1) / total_games * 0.7)

            if file_modified:
                with open(target_file, "w", encoding="utf-8") as out_f:
                    out_f.write("\n\n".join(modified_blocks))

            self._load_category_files(cat)
            self._refresh_treeview()
            stop_progress()
            set_status_message(f"ECO scan complete. Repaired/updated {repaired_count} tag(s) in {target_file.name}.")
        except Exception as e:
            stop_progress()
            set_status_message(f"Error during ECO repair: {e}")

    def _browse_engine(self):
        set_status_message("Browse Engine clicked.")

    def _save_engine_settings(self):
        set_status_message("Engine settings saved.")