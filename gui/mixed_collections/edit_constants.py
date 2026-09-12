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

CONFIG_FILE = Path(__file__).resolve().parent.parent / "pgn" / "categories_config.json"


def load_categories_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                cats = data.get("categories", DEFAULT_COLLECTION_CATEGORIES)
                custom_map = data.get("custom_map", {})
                for k, v in custom_map.items():
                    CATEGORY_FOLDER_MAP[k] = (v[0], v[1])
                return cats
        except Exception:
            pass
    return list(DEFAULT_COLLECTION_CATEGORIES)


def save_categories_config(categories):
    custom_map = {cat: CATEGORY_FOLDER_MAP[cat] for cat in categories if cat not in DEFAULT_COLLECTION_CATEGORIES}
    data = {
        "categories": categories,
        "custom_map": custom_map
    }
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error saving category config: {e}")