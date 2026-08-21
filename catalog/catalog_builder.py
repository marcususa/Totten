import json
from pathlib import Path
import chess.pgn


def catalog_pgns(pgn_path, catalog_path="personal_catalog.json", pgn_out_path="personal_catalog.pgn",
                 tag_mappings=None):
    """
    Parses a PGN file, updates opening frequencies in the catalog JSON,
    and accumulates parsed games into personal_catalog.pgn using project-root relative paths.
    """
    # Determine the project root (parent directory of the 'catalog' folder)
    project_root = Path(__file__).resolve().parent.parent

    pgn_file = Path(pgn_path).resolve()
    cat_file = (project_root / catalog_path).resolve() if not Path(catalog_path).is_absolute() else Path(catalog_path)
    pgn_out = (project_root / pgn_out_path).resolve() if not Path(pgn_out_path).is_absolute() else Path(pgn_out_path)
    tag_mappings = tag_mappings or {}

    # Prevent importing the catalog's own output file into itself
    if pgn_file == pgn_out:
        print("[Catalog Error]: Cannot import the catalog's output file into itself.")
        return 0

    # Convert incoming pgn path to a relative path string compared to project root for clean storage
    try:
        rel_pgn_str = str(pgn_file.relative_to(project_root))
    except ValueError:
        rel_pgn_str = str(pgn_file)

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

    # GUARD CLAUSE: Stop duplicates using relative path matching
    if rel_pgn_str in existing_files:
        print(f"[Catalog Info]: File {Path(pgn_file).name} has already been cataloged.")
        return 0

    existing_files.append(rel_pgn_str)
    catalog["cataloged_files"] = existing_files

    if not pgn_file.exists():
        return 0

    game_count = 0

    # Open the input PGN file and append to the persistent personal_catalog.pgn at project root
    with open(pgn_file, "r", encoding="utf-8", errors="ignore") as f, \
            open(pgn_out, "a", encoding="utf-8") as out_f:

        while True:
            game = chess.pgn.read_game(f)
            if game is None:
                break

            game_count += 1

            # Export game cleanly without hard line wraps in movetext
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
            clean_game_str = game.accept(exporter)

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