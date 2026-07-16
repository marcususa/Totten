import os
import json
import chess.pgn
import gui.app_state as state
from pathlib import Path

def catalog_pgns(add_catalog_button, import_button, catalog_button, imported_files, status, workspace):
    add_catalog_button.configure(text="Add to Catalog")
    add_catalog_button.configure(state="disabled")
    import_button.configure(state="normal")
    catalog_button.configure(state="normal")
    selected_games = set()

    if not imported_files:
        status.configure(
            text="No PGNs imported to catalog."
        )
        return

    print("Game Data selections:")
    for name, var in state.game_data_vars.items():
        print(name, var.get())

    print("Other Data selections:")
    for name, var in state.other_data_vars.items():
        print(name, var.get())

    add_catalog_button.configure(text="Please Wait...")
    workspace.update()

    new_files = []

    total_games = 0

    if os.path.exists("personal_catalog.json"):
        with open("personal_catalog.json", "r", encoding="utf-8") as f:
            catalog = json.load(f)

        cataloged_files = catalog.get("cataloged_files", [])
    else:
        catalog = {
            "cataloged_files": [],
            "A": {},
            "B": {},
            "C": {},
            "D": {},
            "E": {}
        }

        cataloged_files = []

    for filename in imported_files:

        short_name = Path(filename).name

        if filename in cataloged_files:
            continue

        with open(filename, encoding="utf-8") as pgn:
            filtered_games = []
            while True:

                game = chess.pgn.read_game(pgn)

                if game is None:
                    break
                rating_setting = state.rating_filter.get()

                white_elo = game.headers.get("WhiteElo", "")
                black_elo = game.headers.get("BlackElo", "")

                if rating_setting != "All":

                    minimum_rating = int(rating_setting.replace("+", ""))

                    white_rating = int(white_elo) if white_elo.isdigit() else 0
                    black_rating = int(black_elo) if black_elo.isdigit() else 0

                    if white_rating < minimum_rating and black_rating < minimum_rating:
                        continue


                total_games += 1

                eco = game.headers.get("ECO", "").strip()
                opening = game.headers.get("Opening", "").strip()
                variation = game.headers.get("Variation", "").strip()

                if eco and opening:

                    game_info = {
                        "ECO": eco,
                        "Opening": opening,
                        "Variation": variation,
                        "White": game.headers.get("White", "White"),
                        "Black": game.headers.get("Black", "Black")
                    }

                    if state.game_data_vars["Event"].get():
                        game_info["Event"] = game.headers.get("Event", "")

                    if state.game_data_vars["Round"].get():
                        game_info["Round"] = game.headers.get("Round", "")

                    if state.game_data_vars["Result"].get():
                        game_info["Result"] = game.headers.get("Result", "")


# for the unknowns, code below

                    for tag, var in state.other_data_vars.items():
                        print(tag, game.headers.get(tag))
                        if var.get():
                            value = game.headers.get(tag, "").strip()
                            if value:
                                game_info[tag] = value

# for the unknowns, code above

                    depth_setting = state.depth_menu.get()

                    if depth_setting != "All Moves":

                        max_plies = int(depth_setting.split()[0]) * 2

                        moves = []
                        board = game.board()

                        for move in game.mainline_moves():
                            if len(moves) >= max_plies:
                                break

                            moves.append(board.san(move))
                            board.push(move)

                        game_info["Moves"] = " ".join(moves)

                    move_text = []

                    for i in range(0, len(moves), 2):
                        move_number = (i // 2) + 1

                        if i + 1 < len(moves):
                            move_text.append(f"{move_number}. {moves[i]} {moves[i + 1]}")
                        else:
                            move_text.append(f"{move_number}. {moves[i]}")

                    game_info["Moves"] = " ".join(move_text)

                    print(game_info)

                    filtered_games.append(game_info)


                    group = eco[0]

                    if eco not in catalog[group]:
                        catalog[group][eco] = {
                            "opening": opening,
                            "variation": variation,
                            "frequency": 0
                        }

                    catalog[group][eco]["frequency"] += 1

        state.pgn_games_lookup[short_name] = filtered_games

        cataloged_files.append(filename)
        new_files.append(filename)

        games_file_node = state.sidebar.insert(
            state.pgn_games_node,
            "end",
            text=short_name,
            open=True
        )

        state.sidebar.insert(
            games_file_node,
            "end",
            text="Game Data"
        )

        state.sidebar.delete(
            state.pgn_item_lookup[filename]
        )

        del state.pgn_item_lookup[filename]
        del state.pgn_lookup[short_name]

    if not new_files:
        add_catalog_button.configure(text="Add to Catalog")
        status.configure(
            text="PGNs already cataloged. Import new games to catalog more."
        )
        return

    print(catalog)

    catalog["cataloged_files"] = cataloged_files
    with open("personal_catalog.json", "w", encoding="utf-8") as f:
        json.dump(catalog, f, indent=4, sort_keys=True)

    print("JSON written.")

    status.configure(
        text=f"Cataloged {total_games} game(s) from {len(new_files)} PGN(s)."
    )
    add_catalog_button.configure(text="Add to Catalog")