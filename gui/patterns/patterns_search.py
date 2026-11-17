# ==========================================
# FILE: gui/patterns/patterns_search.py
# ==========================================

from collections import Counter
import chess
import chess.pgn
from pathlib import Path
import gui.app_state as state
from core.patterns_db import get_patterns
from core.constants import THEME


class PatternsSearchMixin:
    """Mixin class to handle database pattern searching, piece convergence analysis, and text rendering."""

    def display_pattern_results(self, text_content):
        """Injects pattern analysis text into the middle-right analysis panel and caches it."""
        self._last_analysis_content = text_content
        box = getattr(self, "analysis_textbox", None) or getattr(self, "pv_textbox", None) or getattr(self,
                                                                                                      "_cached_analysis_box",
                                                                                                      None)
        if box:
            try:
                box.configure(state="normal")
                box.delete("1.0", "end")
                box.insert("end", text_content)
                box.configure(state="disabled")
            except Exception:
                pass

    def _extract_player_first_word(self, header_val: str) -> str:
        """Extracts the first clean word/token from a PGN White/Black player header."""
        if not header_val:
            return "Unknown"
        cleaned = str(header_val).replace(",", " ").strip()
        parts = cleaned.split()
        return parts[0] if parts else "Unknown"

    def _find_two_piece_convergences(self, game_node, color_filter: str):
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

        # Static piece values for Level 2 cascading evaluations
        piece_vals = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9, chess.KING: 0}

        for move in resolved.mainline_moves():
            mover_color = board.turn
            move_num = board.fullmove_number
            san = board.san(move)
            move_label = f"{move_num}. {san}" if mover_color == chess.WHITE else f"{move_num}... {san}"

            is_castling = board.is_castling(move)
            is_ep = board.is_en_passant(move)

            square_last_move.pop(move.from_square, None)
            if is_ep:
                ep_cap_sq = move.to_square - 8 if mover_color == chess.WHITE else move.to_square + 8
                square_last_move.pop(ep_cap_sq, None)

            if is_castling:
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
                            base_desc = f"{partner_move_label}, {move_label} attacking the {sq_label} square"

                            # --- LEVEL 2 STATIC CASCADING THREAT CHECK ---
                            cascading_notes = []
                            for atk_sq in [active_sq, partner_sq]:
                                p_obj = board.piece_at(atk_sq)
                                if p_obj and p_obj.piece_type in (chess.QUEEN, chess.ROOK, chess.BISHOP):
                                    for secondary_target in board.attacks(atk_sq):
                                        if secondary_target == target_sq:
                                            continue
                                        sec_piece = board.piece_at(secondary_target)
                                        if sec_piece and sec_piece.color == opponent_color:
                                            sec_val = piece_vals.get(sec_piece.piece_type, 1)
                                            atk_val = piece_vals.get(p_obj.piece_type, 1)
                                            if sec_val >= 3 or sec_val >= atk_val:
                                                sec_sq_name = chess.square_name(secondary_target)
                                                cascading_notes.append(f"Unlocks secondary pressure on {sec_sq_name}")
                                                break

                            if cascading_notes:
                                base_desc += f" (Cascade: {'; '.join(cascading_notes)})"

                            matches.append(base_desc)

        return matches

    def trigger_engine_mode(self, mode):
        if mode in ("white_patterns_mode", "black_patterns_mode"):
            import io
            import chess.pgn
            import customtkinter as ctk

            color_filter = "W" if mode == "white_patterns_mode" else "B"
            title_str = "White Patterns - PGN Export" if color_filter == "W" else "Black Patterns - PGN Export"

            target_game = getattr(self, "current_game", None)
            raw_active_games = getattr(self, "game_list", []) or []

            # Strict Filtering: Only keep games with valid two-piece convergences
            active_games = []
            for g_item in raw_active_games:
                resolved_g = self._resolve_game_obj(g_item)
                if resolved_g and resolved_g != target_game:
                    convs = self._find_two_piece_convergences(resolved_g, color_filter)
                    if convs:
                        active_games.append(resolved_g)

            pgn_io = io.StringIO()
            resolved_target_game = self._resolve_game_obj(target_game) if (
                        target_game and hasattr(self, "_resolve_game_obj")) else target_game

            if resolved_target_game:
                headers = getattr(resolved_target_game, "headers", {})
                tag_keys = list(headers.keys()) if hasattr(headers, "keys") else []
                standard_tags = ["Event", "Site", "Date", "Round", "White", "Black", "Result", "ECO"]
                ordered_tags = [t for t in standard_tags if t in tag_keys] + [t for t in tag_keys if
                                                                              t not in standard_tags]

                for tag in ordered_tags:
                    pgn_io.write(f"[{tag} \"{headers.get(tag, '?')}\"]\n")
                if not ordered_tags:
                    pgn_io.write(
                        "[Event \"Unknown\"]\n[Site \"Unknown\"]\n[Date \"????.??.??\"]\n[Round \"?\"]\n[White \"?\"]\n[Black \"?\"]\n[Result \"*\"]\n")
                pgn_io.write("\n")

                header_key = "White" if color_filter == "W" else "Black"
                cross_game_comments = []

                for resolved_item in active_games:
                    convergences = self._find_two_piece_convergences(resolved_item, color_filter)
                    if not convergences:
                        continue

                    item_headers = getattr(resolved_item, "headers", {})
                    eco_code = item_headers.get("ECO", "???")
                    player_first = self._extract_player_first_word(item_headers.get(header_key, ""))

                    for conv_desc in convergences:
                        cross_game_comments.append(f"{eco_code} {player_first}: {conv_desc}")

                exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=False)
                moves_str = resolved_target_game.accept(exporter).strip()

                result_str = headers.get("Result", "*")

                for token in [" 1-0", " 0-1", " 1/2-1/2", " *"]:
                    if moves_str.endswith(token.strip()):
                        moves_str = moves_str[:-len(token.strip())].strip()

                if cross_game_comments:
                    combined_comment_str = " ".join(cross_game_comments)
                    pgn_io.write(f"{moves_str} {{{combined_comment_str}}} {result_str}\n\n")
                else:
                    pgn_io.write(f"{moves_str} {result_str}\n\n")

            for resolved_item in active_games:
                item_headers = getattr(resolved_item, "headers", {})
                item_tag_keys = list(item_headers.keys()) if hasattr(item_headers, "keys") else []
                standard_tags = ["Event", "Site", "Date", "Round", "White", "Black", "Result", "ECO"]
                item_ordered_tags = [t for t in standard_tags if t in item_tag_keys] + [t for t in item_tag_keys if
                                                                                        t not in item_tag_keys]

                for tag in item_ordered_tags:
                    pgn_io.write(f"[{tag} \"{item_headers.get(tag, '?')}\"]\n")
                if not item_ordered_tags:
                    pgn_io.write(
                        "[Event \"Unknown\"]\n[Site \"Unknown\"]\n[Date \"????.??.??\"]\n[Round \"?\"]\n[White \"?\"]\n[Black \"?\"]\n[Result \"*\"]\n")
                pgn_io.write("\n")

                exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=True)
                item_moves_str = resolved_item.accept(exporter).strip()
                item_result = item_headers.get("Result", "*")

                for token in [" 1-0", " 0-1", " 1/2-1/2", " *"]:
                    if item_moves_str.endswith(token.strip()):
                        item_moves_str = item_moves_str[:-len(token.strip())].strip()

                pgn_io.write(f"{item_moves_str} {item_result}\n\n")

            final_pgn_content = pgn_io.getvalue()

            popup = ctk.CTkToplevel(self)
            popup.title(title_str)
            popup.geometry("750x650")
            popup.configure(
                fg_color=THEME.get("bg_panel", "#172134"),
                bg=THEME.get("bg_panel", "#172134")
            )

            popup.attributes("-topmost", True)
            popup.after(100, lambda: popup.attributes("-topmost", False))

            lbl = ctk.CTkLabel(
                popup,
                text=title_str,
                font=("Arial", 16, "bold"),
                text_color=THEME.get("text_primary", "#ffffff"),
                fg_color="transparent"
            )
            lbl.pack(pady=(15, 5))

            txt_box = ctk.CTkTextbox(
                popup,
                wrap="word",
                fg_color=THEME.get("bg_surface", "#1e293b"),
                text_color=THEME.get("text_primary", "#ffffff"),
                border_color=THEME.get("border_color", "#334155"),
                border_width=1
            )
            txt_box.pack(fill="both", expand=True, padx=15, pady=10)

            txt_box.insert("1.0", final_pgn_content)
            txt_box.configure(state="disabled")

            btn_frame = ctk.CTkFrame(
                popup,
                fg_color=THEME.get("bg_panel", "#172134"),
                border_color=THEME.get("border_color", "#334155"),
                border_width=0
            )
            btn_frame.pack(fill="x", padx=15, pady=(0, 15))

            def copy_pgn():
                popup.clipboard_clear()
                popup.clipboard_append(final_pgn_content)

            btn_copy = ctk.CTkButton(
                btn_frame,
                text="Copy PGN",
                command=copy_pgn,
                fg_color=THEME.get("btn_initial", "#1e3a8a"),
                hover_color=THEME.get("btn_hover", "#2e4a8c"),
                text_color=THEME.get("text_primary", "#ffffff"),
                border_color=THEME.get("border_color", "#334155"),
                border_width=0
            )
            btn_copy.pack(side="right", padx=5)

            btn_close = ctk.CTkButton(
                btn_frame,
                text="Close",
                command=popup.destroy,
                fg_color=THEME.get("btn_initial", "#1e3a8a"),
                hover_color=THEME.get("btn_hover", "#2e4a8c"),
                text_color=THEME.get("text_primary", "#ffffff"),
                border_color=THEME.get("border_color", "#334155"),
                border_width=0
            )
            btn_close.pack(side="right", padx=5)
            return

        target_textbox = getattr(self, "analysis_textbox", None) or getattr(self, "pv_textbox", None)
        if not target_textbox:
            return

        target_textbox.configure(state="normal")
        target_textbox.delete("1.0", "end")

        try:
            color_filter = None
            if mode == "opening_pattern_mode":
                from gui.openings import OpeningsManager
                manager = OpeningsManager()
                manager.attach_to_workspace(self, mode_key=mode)
                return
            elif mode == "calculation_pattern_mode":
                return
            else:
                return

            inner_box = getattr(target_textbox, "_textbox", target_textbox)
            bg_active = THEME.get("active_tracker_bg", "#ff0000")
            fg_active = THEME.get("active_tracker_fg", "#ffffff")

            inner_box.tag_config("active_move", background=bg_active, foreground=fg_active, underline=False)

            stored_singles, _ = get_patterns(color_filter)
            target_game = getattr(self, "current_game", None)

            if target_game:
                all_moves = []
                curr_node = target_game
                while curr_node.variations:
                    next_node = curr_node.variation(0)
                    is_white = (curr_node.board().turn == chess.WHITE)
                    san = curr_node.board().san(next_node.move)
                    clean_san = san.replace("+", "").replace("#", "").lower()
                    move_num = curr_node.board().fullmove_number

                    is_target_side = (color_filter == "W" and is_white) or (color_filter == "B" and not is_white)
                    match_found = is_target_side and clean_san in stored_singles

                    all_moves.append({
                        "move_num": move_num,
                        "is_white": is_white,
                        "san": san,
                        "matched": match_found,
                        "node": next_node
                    })
                    curr_node = next_node

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
                        target_textbox.insert("end", f"{prefix}{m_num}. ")
                        w_text = w_move['san']
                        node_id = id(w_move['node'])
                        tag_name = str(node_id)
                        node_tag = f"move_{node_id}"

                        target_textbox.tag_config(
                            tag_name,
                            foreground=THEME.get("text_primary", "#ffffff"),
                            underline=False
                        )
                        target_textbox.tag_config(
                            node_tag,
                            foreground=THEME.get("text_primary", "#ffffff"),
                            underline=False
                        )

                        target_textbox.insert("end", w_text, (tag_name, node_tag))
                        target_textbox.tag_bind(
                            tag_name,
                            "<Button-1>",
                            lambda event, n=w_move['node']: (self.jump_to_node(n), "break")
                        )
                        target_textbox.tag_bind(
                            node_tag,
                            "<Button-1>",
                            lambda event, n=w_move['node']: (self.jump_to_node(n), "break")
                        )
                        target_textbox.insert("end", " ")
                        prefix = ""

                    if b_move:
                        if not w_move:
                            target_textbox.insert("end", f"{prefix}{m_num}... ")
                        else:
                            target_textbox.insert("end", " ")
                        b_text = b_move['san']
                        node_id = id(b_move['node'])
                        tag_name = str(node_id)
                        node_tag = f"move_{node_id}"

                        target_textbox.tag_config(
                            tag_name,
                            foreground=THEME.get("text_primary", "#ffffff"),
                            underline=False
                        )
                        target_textbox.tag_config(
                            node_tag,
                            foreground=THEME.get("text_primary", "#ffffff"),
                            underline=False
                        )

                        target_textbox.insert("end", b_text, (tag_name, node_tag))
                        target_textbox.tag_bind(
                            tag_name,
                            "<Button-1>",
                            lambda event, n=b_move['node']: (self.jump_to_node(n), "break")
                        )
                        target_textbox.tag_bind(
                            node_tag,
                            "<Button-1>",
                            lambda event, n=b_move['node']: (self.jump_to_node(n), "break")
                        )

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
                    target_textbox.insert("end", " " + " ".join(cross_game_comments))

                target_textbox.insert("end", "\n")

            self._has_tagged_pattern_view = True
            self._active_custom_analysis_content = None

            target_textbox.configure(state="disabled")

            if hasattr(self, "update_active_move_highlight"):
                self.update_active_move_highlight()

        except Exception as e:
            print(f"[ERROR in trigger_engine_mode]: {e}")
            if target_textbox:
                target_textbox.configure(state="disabled")