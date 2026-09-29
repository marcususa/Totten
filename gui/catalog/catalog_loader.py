import json
import threading
import chess.pgn
import duckdb
from gui.sidebar import set_status_message, start_progress, update_progress, stop_progress


class CatalogLoaderMixin:
    def check_and_load_catalog(self, is_startup=True):
        """
        Loads catalog data directly from DuckDB.
        On startup, fetches a fast random sample of 500 games from DuckDB.
        """
        # Enforce strict boolean value
        is_startup = True if not isinstance(is_startup, bool) else is_startup

        if self.db_path.exists():
            try:
                conn = duckdb.connect(str(self.db_path), read_only=True)

                # Check if table exists
                table_check = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='catalog_headers' "
                    "UNION ALL SELECT table_name FROM information_schema.tables WHERE table_name='catalog_headers'"
                ).fetchone()

                if not table_check:
                    conn.close()
                    print("[Catalog Loader] Table 'catalog_headers' not found in DuckDB.")
                    self.aggregated_games_data = []
                    self.refresh_current_view()
                    set_status_message("Catalog is empty. Import a PGN to begin.")
                    return

                if is_startup:
                    print("[Catalog Loader] Fetching 500 random games from DuckDB...")
                    query = """
                        SELECT eco, opening, variation, white, black, headers_json 
                        FROM catalog_headers 
                        ORDER BY RANDOM() 
                        LIMIT 500;
                    """
                else:
                    print("[Catalog Loader] Fetching full catalog from DuckDB...")
                    query = """
                        SELECT eco, opening, variation, white, black, headers_json 
                        FROM catalog_headers;
                    """

                rows = conn.execute(query.strip()).fetchall()
                conn.close()

                print(f"[Catalog Loader] Successfully retrieved {len(rows)} records from DuckDB.")

                # Aggregate rows into view structure
                aggregated = {}
                for eco, opening, variation, white, black, headers_json in rows:
                    eco = eco or "A00"
                    opening = opening or "Unknown"
                    variation = variation or ""

                    try:
                        headers = json.loads(headers_json) if headers_json else {}
                    except Exception:
                        headers = {"White": white, "Black": black, "ECO": eco}

                    key = (eco, opening, variation)
                    if key not in aggregated:
                        aggregated[key] = {
                            "eco": eco,
                            "opening": opening,
                            "variation": variation,
                            "count": 0,
                            "instances": []
                        }

                    aggregated[key]["count"] += 1
                    aggregated[key]["instances"].append({
                        "headers": headers,
                        "game_object": None  # Lazy-loaded on demand
                    })

                self.aggregated_games_data = list(aggregated.values())
                self.refresh_current_view()

                if is_startup:
                    set_status_message("Catalog loaded (Startup Sample - 500 games).")
                else:
                    set_status_message("Full catalog loaded from database.")
                return

            except Exception as e:
                print(f"[Catalog Loader Error] Failed to query DuckDB: {e}")

        # If DuckDB file doesn't exist yet
        print("[Catalog Loader] DuckDB file not found. Initializing empty view.")
        self.aggregated_games_data = []
        self.refresh_current_view()
        set_status_message("Catalog database not found. Import a PGN.")

    def load_catalog(self):
        """Alias for compatibility with importer.py (Forces full load)"""
        self.check_and_load_catalog(is_startup=False)

    def load_data(self):
        """Alias for compatibility with importer.py (Forces full load)"""
        self.check_and_load_catalog(is_startup=False)

    def lazy_load_eco_section(self, cat):
        unloaded_count = 0
        for item in self.aggregated_games_data:
            eco = item["eco"]
            eco_base = eco[0].upper() if eco else "A"
            if eco_base == cat:
                for inst in item["instances"]:
                    if inst.get("game_object") is None:
                        unloaded_count += 1

        if unloaded_count == 0 and any(item["eco"].startswith(cat) for item in self.aggregated_games_data):
            return

        set_status_message(f"Loading games for ECO {cat}...")
        start_progress(indeterminate=False)
        update_progress(0.0)

        threading.Thread(target=self._background_load_eco_section_worker, args=(cat,), daemon=True).start()

    def _background_load_eco_section_worker(self, target_cat):
        eco_pgn = self.eco_files.get(target_cat)
        source_pgn = eco_pgn if (eco_pgn and eco_pgn.exists()) else self.pgn_path

        if not source_pgn.exists():
            self.after(0, stop_progress)
            return

        file_size = source_pgn.stat().st_size if source_pgn.exists() else 1
        if file_size == 0:
            file_size = 1

        updated_items = {}
        processed_count = 0

        try:
            with open(source_pgn, "r", encoding="utf-8", errors="replace") as f:
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break

                    headers = game.headers
                    cleaned = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in headers.items()}
                    eco = self.get_header(cleaned, "ECO", "A00")
                    eco_base = eco[0].upper() if eco else "A"

                    if eco_base == target_cat:
                        opening = self.get_header(cleaned, "Opening", "Unknown")
                        variation = self.get_header(cleaned, "Variation", "")
                        key = (eco, opening, variation)
                        if key not in updated_items:
                            updated_items[key] = []
                        updated_items[key].append({
                            "headers": cleaned,
                            "game_object": game
                        })
                        processed_count += 1

                        if processed_count % 10 == 0:
                            current_pos = f.tell()
                            fraction = min(0.95, current_pos / file_size)
                            self.after(0, lambda p=fraction: update_progress(p))

        except Exception as e:
            print(f"Error lazy loading ECO {target_cat}: {e}")

        self.after(0, lambda: self._merge_lazy_eco_section(target_cat, updated_items))

    def _merge_lazy_eco_section(self, target_cat, updated_items):
        existing_keys = set()
        for item in self.aggregated_games_data:
            eco = item["eco"]
            eco_base = eco[0].upper() if eco else "A"
            if eco_base == target_cat:
                key = (eco, item["opening"], item["variation"])
                existing_keys.add(key)
                if key in updated_items:
                    item["instances"] = updated_items[key]
                    item["count"] = len(updated_items[key])

        for key, instances in updated_items.items():
            if key not in existing_keys:
                eco, opening, variation = key
                self.aggregated_games_data.append({
                    "eco": eco,
                    "opening": opening,
                    "variation": variation,
                    "count": len(instances),
                    "instances": instances
                })

        self.refresh_current_view()
        set_status_message(f"ECO {target_cat} loaded.")
        update_progress(1.0)