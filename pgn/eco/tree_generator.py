import json
from pathlib import Path
import chess.pgn

def generate_list():
    eco_pgn_path = Path("eco.pgn")
    if not eco_pgn_path.exists():
        # Fallback check relative to root/core/eco
        eco_pgn_path = Path(__file__).resolve().parent / "eco.pgn"
    
    output_json_path = Path("eco_list.json")

    if not eco_pgn_path.exists():
        print(f"[Error] Could not locate eco.pgn at {eco_pgn_path}")
        return

    eco_tree = {}
    print(f"Parsing {eco_pgn_path}...")

    try:
        with open(eco_pgn_path, "r", encoding="utf-8", errors="replace") as f:
            while True:
                game = chess.pgn.read_game(f)
                if game is None:
                    break
                
                headers = game.headers
                eco = headers.get("ECO", "A00").strip()
                opening = headers.get("Opening", "Unknown Opening").strip()
                variation = headers.get("Variation", "").strip()

                if opening not in eco_tree:
                    eco_tree[opening] = {}

                var_key = variation if variation else "Main Line"
                if var_key not in eco_tree[opening]:
                    eco_tree[opening][var_key] = []

                if eco not in eco_tree[opening][var_key]:
                    eco_tree[opening][var_key].append(eco)

        with open(output_json_path, "w", encoding="utf-8") as out:
            json.dump(eco_tree, out, indent=2)

        print(f"Successfully generated ECO list with {len(eco_tree)} openings at {output_json_path.resolve()}")

    except Exception as e:
        print(f"[Error] Failed to generate ECO list: {e}")

if __name__ == "__main__":
    generate_list()