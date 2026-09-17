import json
from pathlib import Path

DEFAULT_COLLECTION_CATEGORIES = [
    "Open Events", "Women's Events", "Tournaments", "Matches",
    "Championships", "Openings", "Middlegames", "Endgames",
    "Time Periods / Eras", "Notable People / Players"
]

CATEGORY_FOLDER_MAP = {
    "Open Events": ("open", "open_events.pgn"),
    "Women's Events": ("women", "womens_events.pgn"),
    "Tournaments": ("tournaments", "tournaments.pgn"),
    "Matches": ("matches", "matches.pgn"),
    "Championships": ("championships", "championships.pgn"),
    "Openings": ("openings", "openings.pgn"),
    "Middlegames": ("middlegames", "middlegames.pgn"),
    "Endgames": ("endgames", "endgames.pgn"),
    "Time Periods / Eras": ("era", "era.pgn"),
    "Notable People / Players": ("players", "players.pgn"),
}

# Points directly to the pgn folder sitting next to your main project structure using 2 parents
CONFIG_FILE = Path(__file__).resolve().parent.parent.parent/ "pgn" / "categories_config.json"


def load_categories_config():
    print(f"[DEBUG] Looking for config at: {CONFIG_FILE.resolve()}")
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cats = data.get("categories", DEFAULT_COLLECTION_CATEGORIES)
                custom_map = data.get("custom_map", {})

                # Restore custom mappings so the folder map knows about them
                for k, v in custom_map.items():
                    if isinstance(v, list) and len(v) == 2:
                        CATEGORY_FOLDER_MAP[k] = (v[0], v[1])

                print(f"[DEBUG] Successfully loaded categories: {cats}")
                return cats
        except Exception as e:
            print(f"[DEBUG] Error loading category config: {e}")
    else:
        print("[DEBUG] Config file does not exist yet. Using defaults.")
    return list(DEFAULT_COLLECTION_CATEGORIES)


def save_categories_config(categories):
    # Ensure custom folders are correctly captured
    custom_map = {cat: CATEGORY_FOLDER_MAP[cat] for cat in categories if cat not in DEFAULT_COLLECTION_CATEGORIES}
    data = {
        "categories": categories,
        "custom_map": custom_map
    }
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        print(f"[DEBUG] Successfully saved categories to: {CONFIG_FILE.resolve()}")
    except Exception as e:
        print(f"[DEBUG] Error saving category config: {e}")