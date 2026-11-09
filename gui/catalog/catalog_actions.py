import io
import threading
import json
import chess.pgn
import duckdb
import gui.app_state as state
from gui.statusbar import set_status_message

# Python-defined collection for all standard ECO categories
ALL_ECO_LETTERS = ("A", "B", "C", "D", "E")


class CatalogActionsMixin:
    def filter_by_eco_letter(self, letter):
        if getattr(self, "active_eco_letter", None) == letter:
            self.active_eco_letter = None
        else:
            self.active_eco_letter = letter

        self.is_ae_search = False
        self.active_opening_filter = None
        state.catalog_state["active_opening_filter"] = None

        if hasattr(self, "_rebuild_eco_filter_buttons"):
            self._rebuild_eco_filter_buttons()
        if hasattr(self, "_rebuild_opening_grid"):
            self._rebuild_opening_grid()

        self.load_catalog_summary_from_duckdb()
        self._safe_refresh_view()
        set_status_message(f"ECO Filter: {self.active_eco_letter or 'All'}")

    def apply_filter(self, *args, **kwargs):
        """Completely clears the slate, resets all caches, and runs a fresh A-E search."""
        query_text = ""
        if hasattr(self, "entry_filter") and self.entry_filter is not None:
            try:
                query_text = self.entry_filter.get().strip()
            except Exception as e:
                print(f"[DEBUG apply_filter Error] {e}")

        # --- CLEAN THE SLATE ---
        self.aggregated_games_data = []
        if hasattr(self, "lazy_loaded_instances"):
            self.lazy_loaded_instances.clear()
        self.search_flat_results = None
        self.active_opening_filter = None
        state.catalog_state["active_opening_filter"] = None
        self.active_eco_letter = None
        self.is_ae_search = True
        # -----------------------

        required, excluded, optional = self._parse_search_query(query_text)

        if hasattr(self, "_rebuild_eco_filter_buttons"):
            try:
                self._rebuild_eco_filter_buttons()
            except Exception as e:
                print(f"[DEBUG rebuild eco buttons error]: {e}")

        self.load_catalog_summary_from_duckdb()

        if hasattr(self, "_rebuild_opening_grid"):
            try:
                self._rebuild_opening_grid()
            except Exception as e:
                print(f"[DEBUG rebuild opening grid error]: {e}")

        if hasattr(self, "refresh_current_view"):
            try:
                self.refresh_current_view()
            except Exception as e:
                print(f"[DEBUG refresh current view error]: {e}")

        if hasattr(self, "update_idletasks") and callable(self.update_idletasks):
            try:
                self.update_idletasks()
            except Exception:
                pass

        set_status_message(f"Search Applied (A-E): {query_text if query_text else 'All'}")

    def _safe_refresh_view(self):
        """Thread-safe view refresh dispatcher using a strict state lock to prevent Tcl canvas crashes."""
        if getattr(self, "_is_refreshing", False):
            return

        self._is_refreshing = True

        def _execute_safe():
            try:
                if self.winfo_exists():
                    self.refresh_current_view()
            except Exception as e:
                print(f"[UI Refresh Warning] {e}")
            finally:
                self._is_refreshing = False

        if hasattr(self, "after") and callable(self.after):
            self.after(50, _execute_safe)
        else:
            _execute_safe()

    def _parse_search_query(self, query_str):
        if not query_str:
            return [], [], []

        tokens = query_str.split()
        required = []
        excluded = []
        optional = []

        for token in tokens:
            if token.startswith("+") and len(token) > 1:
                required.append(token[1:].lower())
            elif token.startswith("-") and len(token) > 1:
                excluded.append(token[1:].lower())
            else:
                optional.append(token.lower())

        return required, excluded, optional

    def load_catalog(self):
        """Thread-safe wrapper for background catalog reloads."""
        if getattr(self, "_is_loading", False):
            return
        self._is_loading = True
        try:
            self.aggregated_games_data = []
            self.lazy_loaded_instances.clear()
            self.load_catalog_summary_from_duckdb()
            self._safe_refresh_view()
        finally:
            self._is_loading = False

    def load_catalog_summary_from_duckdb(self):
        if not self.db_path.exists():
            print("[DUCKDB ERROR] Database file path does not exist:", self.db_path)
            return

        try:
            con = duckdb.connect(str(self.db_path), read_only=True)
            tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
            if "catalog_headers" not in tables:
                print("[DUCKDB ERROR] 'catalog_headers' table not found in base tables:", tables)
                con.close()
                return

            eco_filter = getattr(self, "active_eco_letter", None)
            is_ae_search = getattr(self, "is_ae_search", False)

            query_str = ""
            if hasattr(self, "entry_filter") and self.entry_filter is not None:
                try:
                    query_str = self.entry_filter.get().strip()
                except Exception as ex:
                    print(f"[DEBUG DuckDB LOAD] Error reading entry_filter: {ex}")

            required, excluded, optional = self._parse_search_query(query_str)
            search_terms = required + optional

            sql = "SELECT eco, opening, variation, white, black, game_index, headers_json, pgn_text FROM catalog_headers"
            conditions = []
            params = []

            if search_terms:
                term_conditions = []
                for term in search_terms:
                    term_pattern = f"%{term}%"
                    term_conditions.append(
                        "(LOWER(COALESCE(white, '')) LIKE LOWER(?) OR "
                        "LOWER(COALESCE(black, '')) LIKE LOWER(?) OR "
                        "LOWER(COALESCE(opening, '')) LIKE LOWER(?) OR "
                        "LOWER(COALESCE(variation, '')) LIKE LOWER(?) OR "
                        "LOWER(COALESCE(eco, '')) LIKE LOWER(?) OR "
                        "LOWER(COALESCE(headers_json, '')) LIKE LOWER(?))"
                    )
                    params.extend([term_pattern, term_pattern, term_pattern, term_pattern, term_pattern, term_pattern])

                if term_conditions:
                    conditions.append(" AND ".join(term_conditions))

            if excluded:
                for ex in excluded:
                    ex_pattern = f"%{ex}%"
                    conditions.append(
                        "NOT (LOWER(COALESCE(white, '')) LIKE LOWER(?) OR "
                        "LOWER(COALESCE(black, '')) LIKE LOWER(?) OR "
                        "LOWER(COALESCE(opening, '')) LIKE LOWER(?))"
                    )
                    params.extend([ex_pattern, ex_pattern, ex_pattern])

            if eco_filter:
                conditions.append("UPPER(eco) LIKE ?")
                params.append(f"{eco_filter.upper()}%")

            if conditions:
                sql += " WHERE " + " AND ".join(conditions)

            if not search_terms and not eco_filter and not is_ae_search:
                sql += " LIMIT 500"
            else:
                sql += " LIMIT 2000"

            rows = con.execute(sql, params).fetchall()
            con.close()

            self.search_flat_results = None
            grouped_map = {}

            for eco, opening, variation, white, black, game_index, headers_json, pgn_text in rows:
                eco_val = eco or "A00"
                clean_eco = eco_val.strip().upper()

                if is_ae_search:
                    if not clean_eco or clean_eco[0] not in ALL_ECO_LETTERS:
                        continue

                op_val = opening or "Unknown Opening"
                var_val = variation or "Main Line"

                try:
                    headers = json.loads(headers_json) if headers_json else {}
                except Exception:
                    headers = {}

                if "White" not in headers and white:
                    headers["White"] = white
                if "Black" not in headers and black:
                    headers["Black"] = black

                group_key = (eco_val, op_val, var_val)
                if group_key not in grouped_map:
                    grouped_map[group_key] = {
                        "eco": eco_val,
                        "opening": op_val,
                        "variation": var_val,
                        "count": 0,
                        "instances": []
                    }

                grouped_map[group_key]["count"] += 1
                grouped_map[group_key]["instances"].append({
                    "game_index": game_index,
                    "headers": headers,
                    "game_object": None,
                    "pgn_text": pgn_text
                })

            self.aggregated_games_data = list(grouped_map.values())

        except Exception as e:
            print(f"[DuckDB Summary Error] {e}")

    def fetch_group_instances_lazily(self, group_key):
        """Strictly queries DuckDB for ALL games matching this exact ECO, Opening, and Variation subset."""
        if group_key in self.lazy_loaded_instances:
            cached = self.lazy_loaded_instances[group_key]
            if cached:
                return cached

        eco, opening, variation = group_key
        instances = []

        if self.db_path.exists():
            try:
                con = duckdb.connect(str(self.db_path), read_only=True)
                rows = con.execute("""
                    SELECT game_index, white, black, headers_json, pgn_text 
                    FROM catalog_headers 
                    WHERE UPPER(TRIM(eco)) = UPPER(TRIM(?)) 
                      AND LOWER(TRIM(opening)) = LOWER(TRIM(?)) 
                      AND LOWER(TRIM(variation)) = LOWER(TRIM(?))
                """, [eco, opening, variation]).fetchall()
                con.close()

                for game_index, white, black, headers_json, pgn_text in rows:
                    try:
                        headers = json.loads(headers_json) if headers_json else {}
                    except Exception:
                        headers = {}

                    if "White" not in headers and white:
                        headers["White"] = white
                    if "Black" not in headers and black:
                        headers["Black"] = black

                    instances.append({
                        "game_index": game_index,
                        "headers": headers,
                        "game_object": None,
                        "pgn_text": pgn_text
                    })
            except Exception as e:
                print(f"[DuckDB Subset Query Error]: {e}")

        if instances:
            self.lazy_loaded_instances[group_key] = instances
        return instances

    def select_opening_filter(self, opening_name):
        self.active_opening_filter = opening_name
        state.catalog_state["active_opening_filter"] = opening_name
        if hasattr(self, "_rebuild_opening_grid"):
            self._rebuild_opening_grid()
        self._save_preferences()
        set_status_message(f"Selected Opening: {opening_name}")
        self._safe_refresh_view()

    def toggle_group_expansion(self, group_key):
        if group_key in self.expanded_groups:
            self.expanded_groups.remove(group_key)
        else:
            self.expanded_groups.add(group_key)

        if group_key in self.expanded_groups and group_key not in self.lazy_loaded_instances:
            threading.Thread(target=lambda: self.fetch_group_instances_lazily(group_key), daemon=True).start()

        self._safe_refresh_view()

    def on_game_click(self, item_data, game_data):
        if not item_data or not game_data:
            return

        # 1. Strictly query DuckDB for all games matching this exact ECO, Opening, and Variation
        group_key = (item_data.get("eco"), item_data.get("opening"), item_data.get("variation"))
        instances = self.fetch_group_instances_lazily(group_key)
        if not instances:
            instances = item_data.get("instances", [])

        # 2. Parse game objects for the exact variation subset
        subset_games = []
        target_game_obj = game_data.get("game_object")

        for inst in instances:
            g_obj = inst.get("game_object")
            if not g_obj and inst.get("pgn_text"):
                try:
                    g_obj = chess.pgn.read_game(io.StringIO(inst["pgn_text"]))
                    inst["game_object"] = g_obj
                except Exception:
                    pass
            if g_obj:
                subset_games.append(g_obj)
                if inst == game_data and not target_game_obj:
                    target_game_obj = g_obj

        if not target_game_obj and game_data.get("pgn_text"):
            try:
                target_game_obj = chess.pgn.read_game(io.StringIO(game_data["pgn_text"]))
                game_data["game_object"] = target_game_obj
                if target_game_obj not in subset_games:
                    subset_games.insert(0, target_game_obj)
            except Exception:
                pass

        if not subset_games and target_game_obj:
            subset_games = [target_game_obj]

        target_index = 0
        if target_game_obj in subset_games:
            target_index = subset_games.index(target_game_obj)

        # 3. Save subset to state
        state.catalog_state["active_games"] = subset_games
        state.catalog_state["active_focus"] = target_game_obj
        state.catalog_state["active_index"] = target_index
        self._save_preferences()

        # 4. Trigger seamless transition to analysis workspace
        if hasattr(state, "show_workspace") and callable(state.show_workspace):
            try:
                state.show_workspace(
                    "analysis",
                    initial_games=subset_games,
                    target_game=target_game_obj,
                    active_index=target_index
                )
                return
            except Exception as e:
                print(f"[Catalog Actions Nav Error]: {e}")

        if hasattr(state, "register_nav_listener"):
            state.trigger_nav_listener("catalog_analysis")

    def on_group_click(self, item_data):
        if not item_data:
            return
        group_key = (item_data.get("eco"), item_data.get("opening"), item_data.get("variation"))
        instances = self.fetch_group_instances_lazily(group_key)
        if not instances:
            instances = item_data.get("instances", [])
        if not instances:
            return
        self.on_game_click(item_data, instances[0])