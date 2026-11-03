# catalog_actions.py
import io
import threading
import chess.pgn
import duckdb
import gui.app_state as state
from gui.statusbar import set_status_message

class CatalogActionsMixin:
    def load_catalog_summary_from_duckdb(self):
        if not self.db_path.exists():
            return

        try:
            con = duckdb.connect(str(self.db_path), read_only=True)
            tables = [t[0] for t in con.execute("SHOW TABLES").fetchall()]
            if "catalog_headers" not in tables:
                con.close()
                return

            rows = con.execute("""
                SELECT eco, opening, variation, COUNT(*) 
                FROM catalog_headers 
                GROUP BY eco, opening, variation
            """).fetchall()
            con.close()

            grouped_map = {}
            for eco, opening, variation, count in rows:
                eco_val = eco or "A00"
                op_val = opening or "Unknown Opening"
                var_val = variation or "Main Line"

                group_key = (eco_val, op_val, var_val)
                grouped_map[group_key] = {
                    "eco": eco_val,
                    "opening": op_val,
                    "variation": var_val,
                    "count": count,
                    "instances": []
                }

            self.aggregated_games_data = list(grouped_map.values())
        except Exception as e:
            print(f"[DuckDB Summary Error] {e}")

    def fetch_group_instances_lazily(self, group_key):
        if group_key in self.lazy_loaded_instances:
            return self.lazy_loaded_instances[group_key]

        eco, opening, variation = group_key
        instances = []

        if self.db_path.exists():
            try:
                con = duckdb.connect(str(self.db_path), read_only=True)
                columns = [c[1] for c in con.execute("PRAGMA table_info(catalog_headers)").fetchall()]
                has_pgn_col = "pgn_text" in columns

                if has_pgn_col:
                    rows = con.execute("""
                        SELECT game_index, white, black, headers_json, pgn_text 
                        FROM catalog_headers 
                        WHERE eco = ? AND opening = ? AND variation = ?
                    """, [eco, opening, variation]).fetchall()
                else:
                    rows = con.execute("""
                        SELECT game_index, white, black, headers_json, NULL 
                        FROM catalog_headers 
                        WHERE eco = ? AND opening = ? AND variation = ?
                    """, [eco, opening, variation]).fetchall()
                con.close()

                for game_index, white, black, headers_json, pgn_text in rows:
                    try:
                        headers = json.loads(headers_json) if headers_json else {}
                    except Exception:
                        headers = {}

                    game_obj = None
                    if pgn_text:
                        try:
                            game_obj = chess.pgn.read_game(io.StringIO(pgn_text))
                        except Exception:
                            pass

                    instances.append({
                        "game_index": game_index,
                        "headers": headers,
                        "game_object": game_obj,
                        "pgn_text": pgn_text
                    })
            except Exception as e:
                print(f"[DuckDB Lazy Load Error] {e}")

        self.lazy_loaded_instances[group_key] = instances
        return instances

    def select_opening_filter(self, opening_name):
        self.active_opening_filter = opening_name
        state.catalog_state["active_opening_filter"] = opening_name
        self._rebuild_opening_grid()
        self._save_preferences()
        set_status_message(f"Selected Opening: {opening_name}")
        self.refresh_current_view()

    def toggle_group_expansion(self, group_key):
        if group_key in self.expanded_groups:
            self.expanded_groups.remove(group_key)
        else:
            self.expanded_groups.add(group_key)

        if group_key in self.expanded_groups and group_key not in self.lazy_loaded_instances:
            threading.Thread(target=lambda: self.fetch_group_instances_lazily(group_key), daemon=True).start()

        self.refresh_current_view()

    def on_game_click(self, item_data, game_data):
        if not item_data or not game_data:
            return

        current_opening = item_data.get("opening", "").strip()
        if current_opening:
            history = state.catalog_state.get("recent_openings", [])
            if current_opening in history:
                history.remove(current_opening)
            history.insert(0, current_opening)
            state.catalog_state["recent_openings"] = history
            self._save_preferences()

        instances = item_data.get("instances", [])
        if not instances:
            group_key = (item_data["eco"], item_data["opening"], item_data["variation"])
            instances = self.fetch_group_instances_lazily(group_key)
            item_data["instances"] = instances

        target_game_obj = game_data.get("game_object")

        for inst in instances:
            if not inst.get("game_object") and inst.get("pgn_text"):
                try:
                    inst["game_object"] = chess.pgn.read_game(io.StringIO(inst["pgn_text"]))
                except Exception:
                    pass

        missing_indices = {
            inst["game_index"] for inst in instances
            if not inst.get("game_object") and inst.get("game_index") is not None
        }

        if missing_indices and self.pgn_path.exists():
            try:
                max_idx = max(missing_indices)
                with open(self.pgn_path, "r", encoding="utf-8", errors="replace") as f:
                    idx = 0
                    while idx <= max_idx:
                        parsed = chess.pgn.read_game(f)
                        if parsed is None:
                            break
                        if idx in missing_indices:
                            for inst in instances:
                                if inst.get("game_index") == idx:
                                    inst["game_object"] = parsed
                                    break
                        idx += 1
            except Exception as e:
                print(f"[Fallback Batch PGN Read Error] {e}")

        game_list = []
        for inst in instances:
            g_obj = inst.get("game_object")
            if g_obj:
                game_list.append(g_obj)
                if inst == game_data and not target_game_obj:
                    target_game_obj = g_obj

        if not target_game_obj and game_list:
            target_game_obj = game_list[0]
        elif not game_list and target_game_obj:
            game_list = [target_game_obj]

        active_index = 0
        if target_game_obj in game_list:
            active_index = game_list.index(target_game_obj)

        state.catalog_state["active_games"] = game_list if game_list else [target_game_obj]
        state.catalog_state["active_focus"] = target_game_obj
        state.catalog_state["active_index"] = active_index

        sw_func = None
        if hasattr(state, "show_workspace") and callable(state.show_workspace):
            sw_func = state.show_workspace
        elif hasattr(self.winfo_toplevel(), "show_workspace") and callable(getattr(self.winfo_toplevel(), "show_workspace")):
            sw_func = self.winfo_toplevel().show_workspace
        elif hasattr(self.master, "show_workspace") and callable(getattr(self.master, "show_workspace")):
            sw_func = self.master.show_workspace

        if sw_func:
            try:
                sw_func("analysis", initial_games=state.catalog_state["active_games"], target_game=target_game_obj, active_index=active_index)
                return
            except Exception:
                pass

        self._navigate_to_analysis()

    def on_group_click(self, item_data):
        if not item_data:
            return
        instances = item_data.get("instances", [])
        if not instances:
            group_key = (item_data["eco"], item_data["opening"], item_data["variation"])
            instances = self.fetch_group_instances_lazily(group_key)
            item_data["instances"] = instances
        if not instances:
            return
        self.on_game_click(item_data, instances[0])