import chess
from core.patterns_db import get_patterns

class PatternsSearchMixin:
    """Mixin class to handle database pattern searching, piece convergence analysis, and text rendering."""

    def _extract_player_first_word(self, header_val: str) -> str:
        """Extracts the first clean word/token from a PGN White/Black player header."""
        if not header_val:
            return "Unknown"
        cleaned = str(header_val).replace(",", " ").strip()
        parts = cleaned.split()
        return parts[0] if parts else "Unknown"

    def _find_two_piece_convergences(self, game_node, color_filter: str):
        """
        Scans a game's mainline for true, unobstructed 2-piece attacks on an OPPONENT'S piece
        by the target side (`W` or `B`) involving the currently selected piece (`self.target_piece`).
        Excludes empty squares, friendly pieces (self-defense), and squares the opponent can move to in 1 ply.
        """
        resolved = self._resolve_game_obj(game_node) if hasattr(self, "_resolve_game_obj") else game_node
        if not resolved or not hasattr(resolved, "board"):
            return []

        target_color = chess.WHITE if color_filter == "W" else chess.BLACK
        opponent_color = not target_color

        raw_piece = str(getattr(self, "target_piece", "N")).strip().lower()
        piece_char = raw_piece[-1] if raw_piece else "n"
        piece_map = {
            "p": chess.PAWN,
            "n": chess.KNIGHT,
            "b": chess.BISHOP,
            "r": chess.ROOK,
            "q": chess.QUEEN,
            "k": chess.KING,
        }
        selected_piece_type = piece_map.get(piece_char, chess.KNIGHT)

        board = resolved.board()
        square_last_move = {}
        seen_constellations = set()
        matches = []

        for move in resolved.mainline_moves():
            mover_color = board.turn
            move_num = board.fullmove_number
            san = board.san(move)
            move_label = f"{move_num}. {san}" if mover_color == chess.WHITE else f"{move_num}... {san}"

            is_castling = board.is_castling(move)
            is_ep = board.is_en_passant(move)

            # Update piece-move tracking before pushing
            square_last_move.pop(move.from_square, None)
            if is_ep:
                ep_cap_sq = move.to_square - 8 if mover_color == chess.WHITE else move.to_square + 8
                square_last_move.pop(ep_cap_sq, None)

            if is_castling:
                # Track both King and Rook landing squares during castling
                if move.to_square == chess.G1:
                    square_last_move.pop(chess.H1, None)
                    square_last_move[chess.F1] = move_label
                elif move.to_square == chess.C1:
                    square_last_move.pop(chess.A1, None)
                    square_last_move[chess.D1] = move_label
                elif move.to_square == chess.G8:
                    square_last_move.pop(chess.H8, None)
                    square_last_move[chess.F8] = move_label
                elif move.to_square == chess.C8:
                    square_last_move.pop(chess.A8, None)
                    square_last_move[chess.D8] = move_label

            square_last_move[move.to_square] = move_label

            board.push(move)

            if mover_color != target_color:
                continue

            active_squares = [move.to_square]
            if is_castling:
                if move.to_square == chess.G1:
                    active_squares.append(chess.F1)
                elif move.to_square == chess.C1:
                    active_squares.append(chess.D1)
                elif move.to_square == chess.G8:
                    active_squares.append(chess.F8)
                elif move.to_square == chess.C8:
                    active_squares.append(chess.D8)

            opponent_reachable_squares = {m.to_square for m in board.legal_moves}

            for active_sq in active_squares:
                moved_piece = board.piece_at(active_sq)
                if not moved_piece:
                    continue

                for target_sq in board.attacks(active_sq):
                    if board.color_at(target_sq) != opponent_color:
                        continue

                    if target_sq in opponent_reachable_squares:
                        continue

                    attackers = board.attackers(target_color, target_sq)
                    if len(attackers) < 2:
                        continue

                    attacker_types = {board.piece_type_at(sq) for sq in attackers}
                    if selected_piece_type not in attacker_types:
                        continue

                    for partner_sq in attackers:
                        if partner_sq == active_sq:
                            continue

                        partner_piece = board.piece_at(partner_sq)
                        if not partner_piece:
                            continue

                        if moved_piece.piece_type != selected_piece_type and partner_piece.piece_type != selected_piece_type:
                            continue

                        partner_move_label = square_last_move.get(partner_sq)
                        if not partner_move_label:
                            continue

                        sorted_moves = tuple(sorted([partner_move_label, move_label]))
                        constellation_sig = (target_sq, sorted_moves)

                        if constellation_sig not in seen_constellations:
                            seen_constellations.add(constellation_sig)
                            sq_label = chess.square_name(target_sq)
                            matches.append(f"{partner_move_label}, {move_label} attacking the {sq_label} square")

        return matches

    def trigger_engine_mode(self, mode):
        """
        Renders continuous PGN stream on the left with `{Move}` brackets,
        followed by cross-game 2-piece attack matches in `{ECO Player: Move1, Move2 attacking the sq square}` format.
        """
        if not hasattr(self, "pv_textbox"):
            return

        self.pv_textbox.delete("1.0", "end")

        try:
            color_filter = None
            if mode == "white_patterns_mode":
                color_filter = "W"
            elif mode == "black_patterns_mode":
                color_filter = "B"
            elif mode == "opening_pattern_mode":
                from gui.openings import OpeningsManager
                manager = OpeningsManager()
                manager.attach_to_workspace(self, mode_key=mode)
                return
            elif mode == "calculation_pattern_mode":
                return
            else:
                return

            stored_singles, _ = get_patterns(color_filter)
            target_game = getattr(self, "current_game", None)

            if target_game:
                all_moves = []
                for idx, node in enumerate(target_game.mainline(), start=1):
                    is_white = (idx % 2 != 0)
                    san = node.san()
                    clean_san = san.replace("+", "").replace("#", "").lower()
                    move_num = (idx + 1) // 2

                    is_target_side = (color_filter == "W" and is_white) or (color_filter == "B" and not is_white)
                    match_found = is_target_side and clean_san in stored_singles

                    all_moves.append({
                        "move_num": move_num,
                        "is_white": is_white,
                        "san": san,
                        "matched": match_found
                    })

                paired_moves = {}
                for m in all_moves:
                    m_num = m["move_num"]
                    if m_num not in paired_moves:
                        paired_moves[m_num] = {"W": None, "B": None}
                    if m["is_white"]:
                        paired_moves[m_num]["W"] = m
                    else:
                        paired_moves[m_num]["B"] = m

                first_item = True
                for m_num in sorted(paired_moves.keys()):
                    w_move = paired_moves[m_num]["W"]
                    b_move = paired_moves[m_num]["B"]

                    prefix = "" if first_item else " "
                    first_item = False

                    if w_move:
                        self.pv_textbox.insert("end", f"{prefix}{m_num}. ")
                        is_w_match = (color_filter == "W" and w_move["matched"])
                        w_text = f"{{{w_move['san']}}}" if is_w_match else w_move['san']
                        self.pv_textbox.insert("end", f"{w_text} ")
                        prefix = ""

                    if b_move:
                        if not w_move:
                            self.pv_textbox.insert("end", f"{prefix}{m_num}... ")
                        else:
                            self.pv_textbox.insert("end", " ")
                        is_b_match = (color_filter == "B" and b_move["matched"])
                        b_text = f"{{{b_move['san']}}}" if is_b_match else b_move['san']
                        self.pv_textbox.insert("end", f"{b_text}")

                # --- Cross-Reference Active Game List for 2-Piece Attacks ---
                active_games = getattr(self, "game_list", []) or []
                header_key = "White" if color_filter == "W" else "Black"
                cross_game_comments = []

                for game_item in active_games:
                    resolved_item = self._resolve_game_obj(game_item) if hasattr(
                        self, "_resolve_game_obj") else game_item
                    if not resolved_item or resolved_item == target_game:
                        continue

                    convergences = self._find_two_piece_convergences(resolved_item, color_filter)
                    if not convergences:
                        continue

                    headers = getattr(resolved_item, "headers", {})
                    eco_code = headers.get("ECO", "???")
                    player_first = self._extract_player_first_word(headers.get(header_key, ""))

                    for conv_desc in convergences:
                        cross_game_comments.append(f"{{{eco_code} {player_first}: {conv_desc}}}")

                if cross_game_comments:
                    self.pv_textbox.insert("end", " " + " ".join(cross_game_comments))

                self.pv_textbox.insert("end", "\n")

        except Exception as e:
            print(f"[ERROR in trigger_engine_mode]: {e}")