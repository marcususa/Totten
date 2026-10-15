import chess


class OpeningsManager:
    """
    Modular Opening Explorer component designed to plug into Patterns, Catalog,
    and Mixed Collections workspaces. Extracts ECO codes reliably across various
    data containers and cross-references matching opening games in the active dataset.
    """

    def __init__(self, pgn_database=None):
        self.pgn_database = pgn_database

    def extract_eco(self, game):
        """
        Safely and comprehensively extracts the ECO string across dictionaries,
        sqlite rows, python-chess headers, and custom object attributes.
        """
        if not game:
            return ""

        # 1. Check dict-like or sqlite3 Row mapping keys
        if hasattr(game, "keys") and callable(getattr(game, "keys")):
            for k in ("eco", "ECO", "Eco"):
                try:
                    val = game[k]
                    if val:
                        return str(val).strip().upper()
                except Exception:
                    pass

        # 2. Dictionary representation and common wrappers
        if isinstance(game, dict):
            for k in ("game_object", "game", "game_obj", "node", "target_game"):
                if k in game and game[k] is not None:
                    res = self.extract_eco(game[k])
                    if res:
                        return res
            for k in ("ECO", "eco", "Eco"):
                if k in game and game[k]:
                    return str(game[k]).strip().upper()
            if "headers" in game and isinstance(game["headers"], dict):
                h = game["headers"]
                for k in ("ECO", "eco", "Eco"):
                    if k in h and h[k]:
                        return str(h[k]).strip().upper()

        # 3. python-chess Game / Node or object with headers attribute
        if hasattr(game, "headers"):
            headers = game.headers
            if headers:
                if hasattr(headers, "get"):
                    for k in ("ECO", "eco", "Eco"):
                        val = headers.get(k)
                        if val:
                            return str(val).strip().upper()
                elif isinstance(headers, dict):
                    for k in ("ECO", "eco", "Eco"):
                        if k in headers and headers[k]:
                            return str(headers[k]).strip().upper()

        # 4. Direct attributes
        for attr in ("eco", "ECO", "Eco", "eco_code"):
            if hasattr(game, attr):
                val = getattr(game, attr)
                if val:
                    return str(val).strip().upper()

        # 5. Tuple / List fallback (database rows)
        if isinstance(game, (list, tuple)):
            for item in game:
                if isinstance(item, str) and len(item) >= 2 and item[0] in "ABCDE" and item[1:].lstrip().isdigit():
                    return item.strip().upper()

        return ""

    def lookup_opening(self, game_node):
        """
        Extracts opening metadata (ECO, Name, Variation) using unified extraction logic.
        """
        if not game_node:
            return "---", "Unknown Opening"

        eco = self.extract_eco(game_node)

        opening_name = ""
        variation = ""

        resolved = game_node
        if isinstance(game_node, dict):
            for k in ("game_object", "game", "game_obj", "node"):
                if k in game_node and game_node[k] is not None:
                    resolved = game_node[k]
                    break

        headers = getattr(resolved, "headers", {}) or {}
        if hasattr(headers, "get"):
            opening_name = headers.get("Opening") or headers.get("opening") or ""
            variation = headers.get("Variation") or headers.get("variation") or ""
        elif isinstance(headers, dict):
            opening_name = headers.get("Opening") or headers.get("opening") or ""
            variation = headers.get("Variation") or headers.get("variation") or ""

        if not opening_name and hasattr(resolved, "opening"):
            opening_name = getattr(resolved, "opening", "")
        if not variation and hasattr(resolved, "variation"):
            variation = getattr(resolved, "variation", "")

        opening_name = str(opening_name).strip()
        variation = str(variation).strip()

        if opening_name and variation:
            full_name = f"{opening_name}: {variation}"
        elif opening_name:
            full_name = opening_name
        else:
            full_name = "Custom / Unclassified Opening"

        formatted_eco = eco if eco else "---"
        return formatted_eco, full_name

    def _extract_players(self, game):
        """
        Extracts white and black player names safely across object formats.
        """
        resolved = game
        if isinstance(game, dict):
            for k in ("game_object", "game", "game_obj", "node"):
                if k in game and game[k] is not None:
                    resolved = game[k]
                    break

        white = ""
        black = ""
        if hasattr(game, "keys") and callable(getattr(game, "keys")):
            for k in ("white", "White"):
                try:
                    if game[k]: white = str(game[k])
                except Exception:
                    pass
            for k in ("black", "Black"):
                try:
                    if game[k]: black = str(game[k])
                except Exception:
                    pass

        if not white or not black:
            headers = getattr(resolved, "headers", {}) or {}
            if hasattr(headers, "get"):
                white = headers.get("White") or headers.get("white") or white
                black = headers.get("Black") or headers.get("black") or black
            elif isinstance(headers, dict):
                white = headers.get("White") or headers.get("white") or white
                black = headers.get("Black") or headers.get("black") or black

        return white.strip(), black.strip()

    def find_matching_eco_games(self, game_list, target_eco):
        """
        Finds all games sharing the exact target ECO code or ECO family prefix.
        """
        if not target_eco or target_eco == "---":
            return []

        matched_games = []
        seen_identifiers = set()
        target_prefix = target_eco[:2] if len(target_eco) >= 2 else target_eco

        for game in game_list:
            game_eco = self.extract_eco(game)
            if not game_eco:
                continue

            if game_eco == target_eco or game_eco.startswith(target_prefix):
                white, black = self._extract_players(game)
                # Create a robust unique key based on ECO, players, and object identity
                unique_key = (game_eco, white, black, id(game))

                if unique_key not in seen_identifiers:
                    seen_identifiers.add(unique_key)
                    matched_games.append((game, game_eco))

        return matched_games

    def generate_opening_stream(self, game_node, start_move_index=1):
        """
        Generates clean move stream output.
        """
        if not game_node:
            return "No game selected."

        eco, full_name = self.lookup_opening(game_node)

        moves = list(game_node.mainline_moves()) if hasattr(game_node, "mainline_moves") else []
        if not moves and hasattr(game_node, "mainline"):
            moves = [node.move for node in game_node.mainline() if hasattr(node, "move") and node.move]

        if not moves and isinstance(game_node, dict):
            for k in ("game_object", "game", "game_obj", "node"):
                if k in game_node and hasattr(game_node[k], "mainline_moves"):
                    moves = list(game_node[k].mainline_moves())
                    break

        if not moves:
            return f"{eco} {full_name}\n[No moves recorded]"

        formatted_stream = self._format_move_stream(moves, start_ply=start_move_index)
        return f"{eco} {full_name}\n{formatted_stream}"

    def _format_move_stream(self, moves, start_ply=1):
        """
        Formats move list into a clean PGN stream.
        Black continuation moves use 'N...move' with NO space after ellipsis.
        """
        board = chess.Board() if hasattr(chess, "Board") else None
        stream_parts = []

        for idx, move in enumerate(moves, start=1):
            if idx < start_ply:
                if board:
                    board.push(move)
                continue

            move_num = (idx + 1) // 2
            is_white = (idx % 2 != 0)

            if board:
                san = board.san(move)
                board.push(move)
            else:
                san = str(move)

            if idx == start_ply:
                if is_white:
                    stream_parts.append(f"{move_num}. {san}")
                else:
                    stream_parts.append(f"{move_num}...{san}")
            else:
                if is_white:
                    stream_parts.append(f" {move_num}. {san}")
                else:
                    stream_parts.append(f" {san}")

        return "".join(stream_parts)

    def attach_to_workspace(self, workspace_instance, mode_key="opening_pattern_mode"):
        """
        Plugs into workspace output box, renders active move stream, and lists matching games.
        """
        if not hasattr(workspace_instance, "pv_textbox") or not workspace_instance.pv_textbox:
            print("[OPENINGS ERROR] Target workspace has no pv_textbox output container.")
            return

        target_game = getattr(workspace_instance, "current_game", None)
        game_list = getattr(workspace_instance, "game_list", [])

        if not target_game and game_list:
            target_game = game_list[0]

        result_text = self.generate_opening_stream(target_game, start_move_index=7)

        if target_game and game_list:
            target_eco, _ = self.lookup_opening(target_game)
            matches = self.find_matching_eco_games(game_list, target_eco)

            if matches:
                result_text += f"\n\n--- Matching Opening Games ({len(matches)} / {len(game_list)}) ---"
                for idx, (game_obj, eco_code) in enumerate(matches, 1):
                    white, black = self._extract_players(game_obj)
                    players_str = f" : {white} vs {black}" if white and black else ""
                    result_text += f"\n  [{eco_code}] Game #{idx}{players_str}"

        workspace_instance.pv_textbox.delete("1.0", "end")
        workspace_instance.pv_textbox.insert("end", result_text)