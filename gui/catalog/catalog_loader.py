import json
import threading
import chess.pgn
from gui.sidebar import set_status_message, start_progress, update_progress, stop_progress

class CatalogLoaderMixin:
    def check_and_load_catalog(self):
        if self.json_path.exists():
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    self.aggregated_games_data = json.load(f)
                    self.refresh_current_view()
                    return
            except Exception as e:
                print(f"Error loading JSON catalog: {e}")

        if self.pgn_path.exists():
            set_status_message("Loading personal catalog...")
            start_progress(indeterminate=True)
            threading.Thread(target=self._background_load_catalog, daemon=True).start()
        else:
            self.refresh_current_view()

    def _background_load_catalog(self):
        aggregated = {}
        try:
            with open(self.pgn_path, "r", encoding="utf-8", errors="replace") as f:
                while True:
                    game = chess.pgn.read_game(f)
                    if game is None:
                        break
                    headers = {k.strip(): (v.strip() if isinstance(v, str) else v) for k, v in game.headers.items()}
                    eco = self.get_header(headers, "ECO", "A00")
                    opening = self.get_header(headers, "Opening", "Unknown")
                    variation = self.get_header(headers, "Variation", "")

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
                        "game_object": game
                    })

            self.aggregated_games_data = list(aggregated.values())
            try:
                cache_data = []
                for item in self.aggregated_games_data:
                    cache_item = {
                        "eco": item["eco"],
                        "opening": item["opening"],
                        "variation": item["variation"],
                        "count": item["count"],
                        "instances": [{"headers": inst["headers"], "game_object": None} for inst in item["instances"]]
                    }
                    cache_data.append(cache_item)
                with open(self.json_path, "w", encoding="utf-8") as jf:
                    json.dump(cache_data, jf)
            except Exception as ex:
                print(f"Error saving JSON cache: {ex}")

        except Exception as e:
            print(f"Error loading PGN catalog: {e}")

        self.after(0, lambda: [stop_progress(), self.refresh_current_view(), set_status_message("Catalog loaded.")])

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