# ==========================================
# FILE: gui/patterns/patterns_search.py
# ==========================================

from collections import Counter
import io
import tkinter as tk
from tkinter import ttk
from pathlib import Path
import chess
import chess.pgn
import customtkinter as ctk
from PIL import Image, ImageTk
from cairosvg import svg2png
import gui.app_state as state
from core.patterns_db import get_patterns
from core.constants import THEME, LAYOUT


class PatternsSearchMixin:
    """Mixin class to handle database pattern searching, piece convergence analysis, and text rendering."""

    def display_pattern_results(self, text_content):
        """Injects pattern analysis text into the middle-right analysis panel and caches it."""
        self._last_analysis_content = text_content
        box = getattr(self, "analysis_textbox", None) or getattr(self, "pv_textbox", None) or getattr(
            self,
            "_cached_analysis_box",
            None,
        )
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

    def _set_move_sequences_panel(self, text_content: str):
        """Sets the lower-right panel header to 'Move Sequences', locks it, and writes text_content."""
        self._pattern_details_locked = True

        if hasattr(self, "lbl_pgn_data_title") and self.lbl_pgn_data_title:
            try:
                self.lbl_pgn_data_title.configure(
                    text="Move Sequences",
                    text_color=THEME["text_secondary"],
                )
                if not self.lbl_pgn_data_title.winfo_ismapped():
                    self.lbl_pgn_data_title.pack(side="left")
            except Exception:
                pass

        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                self.pgn_data_text.configure(state="normal", fg_color=THEME["bg_surface"])
                self.pgn_data_text.delete("1.0", "end")
                self.pgn_data_text.insert("end", text_content)
                self.pgn_data_text.configure(state="disabled")
            except Exception:
                pass

    def _format_piece_sequence(self, piece_moves: list, piece_label: str) -> str:
        """Formats a single piece's move path (filtering to move 11+ when available)."""
        if not piece_moves:
            return f"{piece_label}: (no moves)"
        late_moves = [m["label"] for m in piece_moves if m["move_num"] >= 11]
        chosen = late_moves if late_moves else [m["label"] for m in piece_moves]
        return f"{piece_label}: {' -> '.join(chosen)}"

    def _build_move_sequences_for_game(self, primary_color_filter: str, game_item, selected_conv):
        """Builds side-ordered move sequences (both White and Black) tracking each converging piece alone."""
        resolved_game = self._resolve_game_obj(game_item) if hasattr(self, "_resolve_game_obj") else game_item
        if not resolved_game:
            return "No move sequence available."

        headers = getattr(resolved_game, "headers", {})
        eco_code = headers.get("ECO", "???")

        first_side = "W" if primary_color_filter == "W" else "B"
        second_side = "B" if first_side == "W" else "W"

        side_blocks = []
        for side_code in (first_side, second_side):
            side_label = "White" if side_code == "W" else "Black"
            player_name = self._extract_player_first_word(headers.get(side_label, ""))
            convs = self._find_two_piece_convergences(resolved_game, side_code)

            if side_code == primary_color_filter and selected_conv:
                chosen_convs = [selected_conv]
            else:
                chosen_convs = convs

            if not chosen_convs:
                side_blocks.append(f"{side_label} ({eco_code} {player_name}): None")
                continue

            conv_lines = []
            for conv in chosen_convs:
                if not isinstance(conv, dict):
                    conv_lines.append(f"{side_label} ({eco_code} {player_name}): {conv}")
                    continue

                p1_name = conv.get("p1_name", "Piece 1")
                p2_name = conv.get("p2_name", "Piece 2")
                p1_moves = conv.get("p1_moves", [])
                p2_moves = conv.get("p2_moves", [])
                cascade_note = conv.get("cascade_note", "")

                p1_str = self._format_piece_sequence(p1_moves, p1_name)
                p2_str = self._format_piece_sequence(p2_moves, p2_name)
                entry = f"{side_label} ({eco_code} {player_name})\n  {p1_str}\n  {p2_str}"
                if cascade_note:
                    entry += f"\n  Cascade: {cascade_note}"
                conv_lines.append(entry)

            side_blocks.append("\n\n".join(conv_lines))

        return "\n\n".join(side_blocks)

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
        piece_names = {
            chess.PAWN: "Pawn",
            chess.KNIGHT: "Knight",
            chess.BISHOP: "Bishop",
            chess.ROOK: "Rook",
            chess.QUEEN: "Queen",
            chess.KING: "King",
        }
        selected_piece_type = piece_map.get(piece_char, chess.KNIGHT)

        board = resolved.board()

        # Track each individual piece across moves so we can isolate a single piece's move path
        sq_to_pid = {}
        piece_history = {}
        for sq, p_obj in board.piece_map().items():
            color_prefix = "w" if p_obj.color == chess.WHITE else "b"
            p_type_char = chess.piece_symbol(p_obj.piece_type).lower()
            pid = f"{color_prefix}_{p_type_char}_{chess.square_name(sq)}"
            sq_to_pid[sq] = pid
            piece_history[pid] = []

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

            moved_pid = sq_to_pid.pop(move.from_square, None)
            square_last_move.pop(move.from_square, None)

            if is_ep:
                ep_cap_sq = move.to_square - 8 if mover_color == chess.WHITE else move.to_square + 8
                sq_to_pid.pop(ep_cap_sq, None)
                square_last_move.pop(ep_cap_sq, None)
            else:
                sq_to_pid.pop(move.to_square, None)

            rook_pid = None
            rook_dest = None
            if is_castling:
                if move.to_square == chess.G1:
                    rook_pid = sq_to_pid.pop(chess.H1, None)
                    rook_dest = chess.F1
                    square_last_move.pop(chess.H1, None)
                    square_last_move[chess.F1] = move_label
                elif move.to_square == chess.C1:
                    rook_pid = sq_to_pid.pop(chess.A1, None)
                    rook_dest = chess.D1
                    square_last_move.pop(chess.A1, None)
                    square_last_move[chess.D1] = move_label
                elif move.to_square == chess.G8:
                    rook_pid = sq_to_pid.pop(chess.H8, None)
                    rook_dest = chess.F8
                    square_last_move.pop(chess.H8, None)
                    square_last_move[chess.F8] = move_label
                elif move.to_square == chess.C8:
                    rook_pid = sq_to_pid.pop(chess.A8, None)
                    rook_dest = chess.D8
                    square_last_move.pop(chess.A8, None)
                    square_last_move[chess.D8] = move_label
                if rook_pid and rook_dest is not None:
                    sq_to_pid[rook_dest] = rook_pid

            if moved_pid:
                sq_to_pid[move.to_square] = moved_pid
                piece_history.setdefault(moved_pid, []).append({
                    "move_num": move_num,
                    "san": san,
                    "label": move_label,
                    "sq": move.to_square,
                })
            if rook_pid and rook_dest is not None:
                piece_history.setdefault(rook_pid, []).append({
                    "move_num": move_num,
                    "san": san,
                    "label": move_label,
                    "sq": rook_dest,
                })

            square_last_move[move.to_square] = move_label
            board.push(move)

            if mover_color != target_color:
                continue

            active_squares = [move.to_square]
            if is_castling and rook_dest is not None:
                active_squares.append(rook_dest)

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

                    target_piece = board.piece_at(target_sq)
                    target_val = piece_vals.get(target_piece.piece_type, 1) if target_piece else 0

                    attackers = board.attackers(target_color, target_sq)
                    if len(attackers) < 2:
                        continue

                    attacker_vals = [
                        piece_vals.get(board.piece_at(sq).piece_type, 1)
                        for sq in attackers
                        if board.piece_at(sq)
                    ]
                    if attacker_vals and min(attacker_vals) > target_val:
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

                            cascade_str = "; ".join(cascading_notes)
                            if cascade_str:
                                base_desc += f" (Cascade: {cascade_str})"

                            active_pid = sq_to_pid.get(active_sq)
                            partner_pid = sq_to_pid.get(partner_sq)

                            # Put the selected piece type first so we answer "How did ONLY <selected piece> get there?"
                            if moved_piece.piece_type == selected_piece_type:
                                first_piece, second_piece = moved_piece, partner_piece
                                first_pid, second_pid = active_pid, partner_pid
                            else:
                                first_piece, second_piece = partner_piece, moved_piece
                                first_pid, second_pid = partner_pid, active_pid

                            matches.append({
                                "desc": base_desc,
                                "fen": board.fen(),
                                "p1_name": piece_names.get(first_piece.piece_type, "Piece"),
                                "p2_name": piece_names.get(second_piece.piece_type, "Piece"),
                                "p1_moves": list(piece_history.get(first_pid, [])),
                                "p2_moves": list(piece_history.get(second_pid, [])),
                                "cascade_note": cascade_str,
                            })

        return matches

    def trigger_engine_mode(self, mode):
        if mode in ("white_patterns_mode", "black_patterns_mode"):
            color_filter = "W" if mode == "white_patterns_mode" else "B"
            flip_board = False
            title_str = "Patterns Results"

            # Open Patterns Results window first and set initial prompt in Move Sequences
            popup = ctk.CTkToplevel(self)
            popup.title(title_str)
            popup.geometry("1120x780")
            popup.configure(
                fg_color=THEME["bg_panel"],
                bg=THEME["bg_panel"],
            )

            popup.attributes("-topmost", True)
            popup.after(100, lambda: popup.attributes("-topmost", False))

            self._set_move_sequences_panel("Select a board in Patterns Results to load its move sequence.")

            target_game = getattr(self, "current_game", None)
            raw_active_games = (
                getattr(self, "game_list", None)
                or getattr(self, "all_games_cache", None)
                or getattr(state, "all_games", None)
                or []
            )

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
                target_game and hasattr(self, "_resolve_game_obj")
            ) else target_game

            header_key = "White" if color_filter == "W" else "Black"
            cross_game_comments = []
            mini_cards = []
            standard_tags = ["Event", "Site", "Date", "Round", "White", "Black", "Result", "ECO"]

            if resolved_target_game:
                headers = getattr(resolved_target_game, "headers", {})
                tag_keys = list(headers.keys()) if hasattr(headers, "keys") else []
                base_target_tags = [t for t in standard_tags if t in tag_keys]
                ordered_tags = base_target_tags + [t for t in tag_keys if t not in base_target_tags]

                for tag in ordered_tags:
                    pgn_io.write(f"[{tag} \"{headers.get(tag, '?')}\"]\n")
                if not ordered_tags:
                    pgn_io.write(
                        "[Event \"Unknown\"]\n[Site \"Unknown\"]\n[Date \"????.??.??\"]\n[Round \"?\"]\n[White \"?\"]\n[Black \"?\"]\n[Result \"*\"]\n"
                    )
                pgn_io.write("\n")

                for resolved_item in active_games:
                    convergences = self._find_two_piece_convergences(resolved_item, color_filter)
                    if not convergences:
                        continue

                    item_headers = getattr(resolved_item, "headers", {})
                    eco_code = item_headers.get("ECO", "???")
                    player_first = self._extract_player_first_word(item_headers.get(header_key, ""))
                    player_full = (item_headers.get(header_key) or "Unknown").strip()

                    for conv in convergences:
                        conv_desc = conv["desc"] if isinstance(conv, dict) else conv
                        conv_fen = conv.get("fen") if isinstance(conv, dict) else resolved_item.board().fen()
                        cross_game_comments.append(f"{eco_code} {player_first}: {conv_desc}")
                        mini_cards.append({
                            "label": f"{eco_code} {player_full}",
                            "fen": conv_fen,
                            "game": resolved_item,
                            "conv": conv,
                        })

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
                base_item_tags = [t for t in standard_tags if t in item_tag_keys]
                item_ordered_tags = base_item_tags + [t for t in item_tag_keys if t not in base_item_tags]

                for tag in item_ordered_tags:
                    pgn_io.write(f"[{tag} \"{item_headers.get(tag, '?')}\"]\n")
                if not item_ordered_tags:
                    pgn_io.write(
                        "[Event \"Unknown\"]\n[Site \"Unknown\"]\n[Date \"????.??.??\"]\n[Round \"?\"]\n[White \"?\"]\n[Black \"?\"]\n[Result \"*\"]\n"
                    )
                pgn_io.write("\n")

                exporter = chess.pgn.StringExporter(headers=False, variations=True, comments=True)
                item_moves_str = resolved_item.accept(exporter).strip()
                item_result = item_headers.get("Result", "*")

                for token in [" 1-0", " 0-1", " 1/2-1/2", " *"]:
                    if item_moves_str.endswith(token.strip()):
                        item_moves_str = item_moves_str[:-len(token.strip())].strip()

                pgn_io.write(f"{item_moves_str} {item_result}\n\n")

            final_pgn_content = pgn_io.getvalue()

            mini_w = 300
            mini_h = 300
            mini_sq = mini_w / 8.0
            piece_px = int(mini_sq * 0.88)

            root_dir = Path(__file__).resolve().parents[2]
            pieces_dir = root_dir / "assets" / "pieces"
            svg_cache = {}
            for p_code in ("wp", "wn", "wb", "wr", "wq", "wk", "bp", "bn", "bb", "br", "bq", "bk"):
                svg_file = pieces_dir / f"{p_code}.svg"
                if svg_file.exists():
                    try:
                        png_bytes = svg2png(url=str(svg_file), output_width=piece_px, output_height=piece_px)
                        pil_img = Image.open(io.BytesIO(png_bytes))
                        svg_cache[p_code] = ImageTk.PhotoImage(pil_img, master=popup)
                    except Exception:
                        pass

            popup._mini_piece_refs = list(svg_cache.values())

            strip_outer = ctk.CTkFrame(
                popup,
                fg_color=THEME["bg_panel"],
            )
            strip_outer.pack(fill="x", expand=False, padx=8, pady=(6, 4))

            h_scroll = ttk.Scrollbar(strip_outer, orient="horizontal")
            h_scroll.pack(side="bottom", fill="x")

            strip_canvas = tk.Canvas(
                strip_outer,
                height=mini_h + 32,
                bg=THEME["bg_panel"],
                highlightthickness=0,
                bd=0,
                xscrollcommand=h_scroll.set,
            )
            strip_canvas.pack(side="top", fill="x", expand=True, pady=(0, 3))
            h_scroll.configure(command=strip_canvas.xview)

            mini_row = ctk.CTkFrame(strip_canvas, fg_color=THEME["bg_panel"])
            strip_canvas.create_window((0, 0), window=mini_row, anchor="nw")

            def _sync_strip_scroll(event=None):
                strip_canvas.configure(scrollregion=strip_canvas.bbox("all"))

            mini_row.bind("<Configure>", _sync_strip_scroll)

            light_sq = THEME.get("board_light", THEME.get("light_square"))
            dark_sq = THEME.get("board_dark", THEME.get("dark_square"))

            def _on_board_button_click(card_info):
                seq_text = self._build_move_sequences_for_game(
                    color_filter,
                    card_info["game"],
                    card_info["conv"],
                )
                self._set_move_sequences_panel(seq_text)

            for idx, card_info in enumerate(mini_cards):
                card_label = card_info["label"]
                card_fen = card_info["fen"]

                cell = ctk.CTkFrame(
                    mini_row,
                    fg_color=THEME["bg_surface"],
                    corner_radius=6,
                    border_width=1,
                    border_color=THEME["border_color"],
                )
                cell.grid(row=0, column=idx, padx=5, pady=2)

                mini_canvas = tk.Canvas(
                    cell,
                    width=mini_w,
                    height=mini_h,
                    highlightthickness=0,
                    bd=0,
                    cursor="hand2",
                )
                mini_canvas.pack(padx=4, pady=(4, 2))

                try:
                    pos_board = chess.Board(card_fen) if card_fen else chess.Board()
                except Exception:
                    pos_board = chess.Board()

                for draw_row in range(8):
                    for draw_col in range(8):
                        board_rank = draw_row if flip_board else (7 - draw_row)
                        board_file = (7 - draw_col) if flip_board else draw_col
                        sq = chess.square(board_file, board_rank)

                        x0 = draw_col * mini_sq
                        y0 = draw_row * mini_sq
                        x1 = x0 + mini_sq
                        y1 = y0 + mini_sq
                        fill_col = light_sq if (board_rank + board_file) % 2 == 1 else dark_sq
                        mini_canvas.create_rectangle(x0, y0, x1, y1, fill=fill_col, outline="")

                        piece = pos_board.piece_at(sq)
                        if piece:
                            p_code = f"{'w' if piece.color == chess.WHITE else 'b'}{piece.symbol().lower()}"
                            img_obj = svg_cache.get(p_code)
                            if img_obj:
                                mini_canvas.create_image((x0 + x1) // 2, (y0 + y1) // 2, image=img_obj)

                mini_canvas.bind(
                    "<Button-1>",
                    lambda event, info=card_info: _on_board_button_click(info),
                )

                lbl_card = ctk.CTkLabel(
                    cell,
                    text=card_label,
                    font=("Arial", 10),
                    text_color=THEME["text_primary"],
                    fg_color="transparent",
                    cursor="hand2",
                )
                lbl_card.pack(pady=(0, 4))
                lbl_card.bind(
                    "<Button-1>",
                    lambda event, info=card_info: _on_board_button_click(info),
                )

            txt_box = ctk.CTkTextbox(
                popup,
                wrap="word",
                fg_color=THEME["bg_surface"],
                text_color=THEME["text_primary"],
                border_color=THEME["border_color"],
                border_width=1,
            )
            txt_box.pack(fill="both", expand=True, padx=8, pady=5)

            txt_box.insert("1.0", final_pgn_content)
            txt_box.configure(state="disabled")

            btn_frame = ctk.CTkFrame(
                popup,
                fg_color=THEME["bg_panel"],
                border_color=THEME["border_color"],
                border_width=0,
            )
            btn_frame.pack(fill="x", expand=False, padx=8, pady=(0, 8))

            btn_center = ctk.CTkFrame(btn_frame, fg_color="transparent")
            btn_center.pack(anchor="center")

            def copy_pgn():
                popup.clipboard_clear()
                popup.clipboard_append(final_pgn_content)

            btn_copy = ctk.CTkButton(
                btn_center,
                text="Copy PGN",
                command=copy_pgn,
                fg_color=THEME["btn_initial"],
                hover_color=THEME["btn_hover"],
                text_color=THEME["text_primary"],
                border_color=THEME["border_color"],
                border_width=0,
            )
            btn_copy.pack(side="left", padx=5)

            btn_close = ctk.CTkButton(
                btn_center,
                text="Close",
                command=popup.destroy,
                fg_color=THEME["btn_initial"],
                hover_color=THEME["btn_hover"],
                text_color=THEME["text_primary"],
                border_color=THEME["border_color"],
                border_width=0,
            )
            btn_close.pack(side="left", padx=5)
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
            bg_active = THEME.get("active_tracker_bg")
            fg_active = THEME.get("active_tracker_fg")

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
                        "node": next_node,
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
                            foreground=THEME["text_primary"],
                            underline=False,
                        )
                        target_textbox.tag_config(
                            node_tag,
                            foreground=THEME["text_primary"],
                            underline=False,
                        )

                        target_textbox.insert("end", w_text, (tag_name, node_tag))
                        target_textbox.tag_bind(
                            tag_name,
                            "<Button-1>",
                            lambda event, n=w_move['node']: (self.jump_to_node(n), "break"),
                        )
                        target_textbox.tag_bind(
                            node_tag,
                            "<Button-1>",
                            lambda event, n=w_move['node']: (self.jump_to_node(n), "break"),
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
                            foreground=THEME["text_primary"],
                            underline=False,
                        )
                        target_textbox.tag_config(
                            node_tag,
                            foreground=THEME["text_primary"],
                            underline=False,
                        )

                        target_textbox.insert("end", b_text, (tag_name, node_tag))
                        target_textbox.tag_bind(
                            tag_name,
                            "<Button-1>",
                            lambda event, n=b_move['node']: (self.jump_to_node(n), "break"),
                        )
                        target_textbox.tag_bind(
                            node_tag,
                            "<Button-1>",
                            lambda event, n=b_move['node']: (self.jump_to_node(n), "break"),
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