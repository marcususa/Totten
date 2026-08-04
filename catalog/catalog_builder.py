import json
from pathlib import Path
import chess.pgn


def catalog_pgns(pgn_path, catalog_path="personal_catalog.json", pgn_out_path="personal_catalog.pgn",
                 tag_mappings=None):
    """
    Parses a PGN file, updates the opening frequencies in the catalog JSON,
    and accumulates all parsed games into personal_catalog.pgn with clean movetext formatting.
    """
    pgn_file = Path(pgn_path)
    cat_file = Path(catalog_path)
    pgn_out = Path(pgn_out_path)
    tag_mappings = tag_mappings or {}

    # Load existing catalog data if the json already exists
    existing_files = []
    catalog = {}
    if cat_file.exists():
        try:
            with open(cat_file, "r", encoding="utf-8") as f:
                old_data = json.load(f)
                if isinstance(old_data, dict):
                    catalog = old_data
                    if "cataloged_files" in catalog:
                        existing_files = catalog["cataloged_files"]
        except Exception:
            pass

    file_str = str(pgn_file.resolve())
    if file_str not in existing_files:
        existing_files.append(file_str)

    catalog["cataloged_files"] = existing_files

    if not pgn_file.exists():
        return 0

    game_count = 0

    # Open the cumulative PGN output file in append mode to preserve previously added games
    with open(pgn_file, "r", encoding="utf-8", errors="ignore") as f, \
            open(pgn_out, "a", encoding="utf-8") as out_f:

        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            game_count += 1

            # Export game cleanly: columns=None removes hard line wraps in movetext
            # to prevent ugly gaps and spacing artifacts downstream.
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
            clean_game_str = game.accept(exporter)

            # Write the clean game string to the persistent personal_catalog.pgn file
            out_f.write(clean_game_str + "\n\n")

            headers = dict(game.headers)

            for raw_tag, target_tag in tag_mappings.items():
                if raw_tag in headers:
                    val = headers.pop(raw_tag)
                    if target_tag != "(Ignore)" and target_tag:
                        headers[target_tag] = val

            eco = str(headers.get("ECO", "UNKNOWN")).strip().upper() or "UNKNOWN"
            opening = str(headers.get("Opening", "")).strip()
            variation = str(headers.get("Variation", "")).strip()

            if eco not in catalog:
                catalog[eco] = {}

            var_key = f"{opening} - {variation}".strip(" -")
            if not var_key:
                var_key = "General"

            if var_key in catalog[eco]:
                if isinstance(catalog[eco][var_key], dict):
                    catalog[eco][var_key]["frequency"] = catalog[eco][var_key].get("frequency", 0) + 1
                else:
                    catalog[eco][var_key] += 1
            else:
                catalog[eco][var_key] = {
                    "eco": eco,
                    "opening": opening,
                    "variation": variation,
                    "frequency": 1
                }

    sorted_catalog = {
        "cataloged_files": sorted(list(set(catalog["cataloged_files"])))
    }

    for eco in sorted(k for k in catalog.keys() if k != "cataloged_files"):
        sorted_catalog[eco] = dict(sorted(
            catalog[eco].items(),
            key=lambda item: (item[1].get("opening", ""), item[1].get("variation", "")) if isinstance(item[1],
                                                                                                      dict) else ("",
                                                                                                                  "")
        ))

    with open(cat_file, "w", encoding="utf-8") as f:
        json.dump(sorted_catalog, f, indent=4)

    return game_count