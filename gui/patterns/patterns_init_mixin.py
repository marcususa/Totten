import customtkinter as ctk
import duckdb
from gui.chess_board import ChessBoardWidget
from core.constants import THEME, LAYOUT
from core.patterns_db import get_patterns

CONFIRMED_GOOD_MOVES = set()
REJECTED_BAD_MOVES = set()

def mark_move_good(clean_san: str):
    CONFIRMED_GOOD_MOVES.add(clean_san)
    REJECTED_BAD_MOVES.discard(clean_san)

def mark_move_bad(clean_san: str):
    REJECTED_BAD_MOVES.add(clean_san)
    CONFIRMED_GOOD_MOVES.discard(clean_san)

class PatternsInitMixin:
    """Mixin class to handle the UI initialization, layout, and yellow pattern matching for PatternsAnalysis."""

    def _safe_load_game(self, game_node, category_source=None):
        if category_source and category_source != "patterns":
            return
        self.load_game(game_node, category_source=category_source)

    def toggle_pgn_data_panel(self):
        """Toggles visibility of the Game Details panel (Row 3) while strictly protecting the Eval Bar (Row 1)."""
        if hasattr(self, "pgn_data_panel") and self.pgn_data_panel.winfo_ismapped():
            # 1. Hide Game Details panel
            self.pgn_data_panel.grid_remove()

            # 2. Lock Row 1 (Good/Bad/IDK) height strictly so it cannot collapse
            self.right_analysis_panel.rowconfigure(1, weight=0, minsize=32)

            # 3. Collapse Row 3
            self.right_analysis_panel.rowconfigure(3, weight=0, minsize=0)

            # 4. Expand Row 2 (Analysis) to take all remaining vertical space
            self.right_analysis_panel.rowconfigure(2, weight=1)

            # 5. Remove bottom padding on analysis container so it fills flush down to the bottom
            self.analysis_container_frame.grid_configure(pady=(0, 0))
        else:
            # 1. Restore bottom padding on analysis container
            self.analysis_container_frame.grid_configure(pady=(0, 8))

            # 2. Re-grid Game Details on Row 3
            self.pgn_data_panel.grid(row=3, column=0, sticky="nsew", padx=0, pady=0)

            # 3. Restore row weights for Row 1, Row 2, and Row 3
            self.right_analysis_panel.rowconfigure(1, weight=0, minsize=32)
            self.right_analysis_panel.rowconfigure(2, weight=3)
            self.right_analysis_panel.rowconfigure(3, weight=1, minsize=70)

        # Ensure Row 1 eval_bar_frame remains strictly attached to Row 1
        if hasattr(self, "eval_bar_frame"):
            self.eval_bar_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 8))

    def _eval_good_action(self):
        if hasattr(self, "on_eval_good") and callable(self.on_eval_good):
            self.on_eval_good()

    def _eval_bad_action(self):
        if hasattr(self, "on_eval_bad") and callable(self.on_eval_bad):
            self.on_eval_bad()

    def _eval_idk_action(self):
        if hasattr(self, "on_eval_idk") and callable(self.on_eval_idk):
            self.on_eval_idk()

    def on_flip_board(self, event=None):
        if hasattr(self, "board_widget") and hasattr(self.board_widget, "flip_board"):
            self.board_widget.flip_board()
        elif hasattr(self, "board_widget") and hasattr(self.board_widget, "invert"):
            self.board_widget.invert()

    def _handle_keypress(self, event=None):
        if event and event.keysym in ("f", "F"):
            self.on_flip_board()
        return "break"

    def _handle_left(self, event=None):
        if hasattr(self, "on_prev_move") and callable(self.on_prev_move):
            try:
                self.on_prev_move(event)
            except TypeError:
                self.on_prev_move()
            return "break"

    def _handle_right(self, event=None):
        if hasattr(self, "on_next_move") and callable(self.on_next_move):
            try:
                self.on_next_move(event)
            except TypeError:
                self.on_next_move()
            return "break"

    def _handle_up(self, event=None):
        if hasattr(self, "on_first_move") and callable(self.on_first_move):
            try:
                self.on_first_move(event)
            except TypeError:
                self.on_first_move()
            return "break"

    def _handle_down(self, event=None):
        if hasattr(self, "on_last_move") and callable(self.on_last_move):
            try:
                self.on_last_move(event)
            except TypeError:
                self.on_last_move()
            return "break"

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
        import chess

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

            # Squares involved in this move (for castling, check the rook's new square too)
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
                    # 1. MUST be occupied by an opponent's piece (excludes empty squares & friendly pieces)
                    if board.color_at(target_sq) != opponent_color:
                        continue

                    # 2. Exclude squares the opponent can move to in one move
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
                    resolved_item = self._resolve_game_obj(game_item) if hasattr(self,
                                                                                 "_resolve_game_obj") else game_item
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

    def init_layout(self):
        import gui.app_state as state
        from tkinter import ttk

        if hasattr(state, "register_analysis_callback"):
            state.register_analysis_callback(self._safe_load_game)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_container.grid_columnconfigure(0, weight=0, minsize=LAYOUT["board_width"])
        self.main_container.grid_columnconfigure(1, weight=3)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_pane_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_pane_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        self.left_board_panel = ctk.CTkFrame(self.left_pane_container, fg_color=THEME["bg_panel"], corner_radius=8,
                                             border_width=1,
                                             border_color=THEME.get("border_color", THEME["bg_surface"]))
        self.left_board_panel.pack(side="top", anchor="w", fill="none", expand=False, padx=0, pady=(0, 5))

        self.board_holder = ctk.CTkFrame(self.left_board_panel, fg_color=THEME["bg_surface"],
                                         width=LAYOUT["board_width"], height=LAYOUT["board_height"],
                                         corner_radius=0)
        self.board_holder.pack(side="top", anchor="w", padx=10, pady=10)
        self.board_holder.pack_propagate(False)

        self.board_widget = ChessBoardWidget(self.board_holder, square_size=LAYOUT["square_size"])
        self.board_widget.pack(fill="both", expand=True)

        if hasattr(self, "on_prev_move"):
            self.board_widget.on_step_back = self.on_prev_move
        if hasattr(self, "on_next_move"):
            self.board_widget.on_step_forward = self.on_next_move
        if hasattr(self, "on_first_move"):
            self.board_widget.on_jump_start = self.on_first_move
        if hasattr(self, "on_last_move"):
            self.board_widget.on_jump_end = self.on_last_move

        self.engine_results_container_frame = ctk.CTkFrame(self.left_pane_container, fg_color=THEME["bg_panel"],
                                                           corner_radius=8,
                                                           border_width=1,
                                                           border_color=THEME.get("border_color", THEME["bg_surface"]))
        self.engine_results_container_frame.pack(side="top", fill="both", expand=True, padx=0, pady=0)

        self.engine_results_header_frame = ctk.CTkFrame(self.engine_results_container_frame, fg_color="transparent")
        self.engine_results_header_frame.pack(fill="x", padx=10, pady=(6, 2))

        self.row_analysis_btns = ctk.CTkFrame(self.engine_results_header_frame, fg_color="transparent")
        self.row_analysis_btns.pack(side="left", padx=0)

        if hasattr(self, "active_engine_mode"):
            self._active_engine_mode = self.active_engine_mode
        elif not hasattr(self, "_active_engine_mode"):
            self._active_engine_mode = None

        if not hasattr(self, "_engine_running"):
            self._engine_running = False

        if not hasattr(self, "_selected_mode_button"):
            self._selected_mode_button = None

        def toggle_engine_state():
            self._engine_running = not self._engine_running
            if hasattr(self, "btn_pv"):
                self.btn_pv.configure(
                    fg_color=THEME["btn_hover"] if self._engine_running else THEME["btn_initial"],
                    text="Stop" if self._engine_running else "PV Engine"
                )
            if hasattr(self, "toggle_engine_action"):
                self.toggle_engine_action()

        def set_analysis_mode(mode):
            self._selected_mode_button = mode
            self._active_engine_mode = mode
            self.active_engine_mode = mode
            update_analysis_buttons_state()
            if hasattr(self, "trigger_engine_mode"):
                self.trigger_engine_mode(mode)

        def update_analysis_buttons_state():
            buttons_map = {
                "white_patterns_mode": (self.btn_white, self.frame_white),
                "black_patterns_mode": (self.btn_black, self.frame_black),
                "opening_pattern_mode": (self.btn_opening, self.frame_opening),
                "calculation_pattern_mode": (self.btn_calculation, self.frame_calculation)
            }
            for m, (btn, frm) in buttons_map.items():
                is_selected = (self._selected_mode_button == m)
                btn.configure(
                    fg_color=THEME["btn_hover"] if is_selected else THEME["btn_initial"]
                )
                frm.configure(border_width=0 if is_selected else 1)

        def on_btn_enter(btn, mode, frm):
            if self._selected_mode_button != mode:
                btn.configure(fg_color=THEME["btn_hover"])
                frm.configure(border_width=0)

        def on_btn_leave(btn, mode, frm):
            if self._selected_mode_button != mode:
                btn.configure(fg_color=THEME["btn_initial"])
                frm.configure(border_width=1)

        def init_buttons_ui():
            for widget in self.row_analysis_btns.winfo_children():
                widget.destroy()

            btn_height = 20
            btn_corner = 6
            btn_font = ctk.CTkFont(size=11)
            btn_hover = THEME["btn_hover"]
            btn_initial = THEME["btn_initial"]
            text_color = THEME["text_primary"]
            border_color = THEME.get("border_color", THEME["bg_surface"])

            self.frame_pv = ctk.CTkFrame(
                self.row_analysis_btns, fg_color="transparent", corner_radius=btn_corner,
                border_width=0, border_color=border_color
            )
            self.frame_pv.pack(side="left", padx=(2, 4))

            self.btn_pv = ctk.CTkButton(
                self.frame_pv, text="Stop" if self._engine_running else "PV Engine", width=70,
                height=btn_height, corner_radius=btn_corner, border_width=0,
                fg_color=btn_hover if self._engine_running else btn_initial,
                hover_color=btn_hover, text_color=text_color, font=btn_font,
                command=toggle_engine_state
            )
            self.btn_pv.pack()

            def create_mode_button(text, width, mode_key):
                frm = ctk.CTkFrame(
                    self.row_analysis_btns, fg_color="transparent", corner_radius=btn_corner,
                    border_width=1, border_color=border_color
                )
                frm.pack(side="left", padx=2)
                btn = ctk.CTkButton(
                    frm, text=text, width=width, height=btn_height, corner_radius=btn_corner,
                    border_width=0, fg_color=btn_initial, hover_color=btn_hover,
                    text_color=text_color, font=btn_font,
                    command=lambda: set_analysis_mode(mode_key)
                )
                btn.bind("<Enter>", lambda e, b=btn, m=mode_key, f=frm: on_btn_enter(b, m, f))
                btn.bind("<Leave>", lambda e, b=btn, m=mode_key, f=frm: on_btn_leave(b, m, f))
                btn.pack()
                return btn, frm

            self.btn_white, self.frame_white = create_mode_button("White Patterns", 95, "white_patterns_mode")
            self.btn_black, self.frame_black = create_mode_button("Black Patterns", 95, "black_patterns_mode")
            self.btn_opening, self.frame_opening = create_mode_button("Opening", 75, "opening_pattern_mode")
            self.btn_calculation, self.frame_calculation = create_mode_button("Calculation", 80,
                                                                              "calculation_pattern_mode")

        init_buttons_ui()

        self.pv_inner_wrapper = ctk.CTkFrame(self.engine_results_container_frame, fg_color="transparent")
        self.pv_inner_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.pv_textbox = ctk.CTkTextbox(
            self.pv_inner_wrapper,
            fg_color=THEME["bg_surface"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=LAYOUT["pv_box_height"]
        )

        self.pv_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")
        self.pv_textbox.tag_config("active_move", background=THEME["active_tracker_bg"],
                                   foreground=THEME["active_tracker_fg"])
        self.pv_textbox.pack(fill="both", expand=True, padx=0, pady=2)

        self.right_analysis_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_analysis_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        # 4-Row Configuration (Row 1 protected with minsize=32):
        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=0, minsize=32)
        self.right_analysis_panel.rowconfigure(2, weight=3)
        self.right_analysis_panel.rowconfigure(3, weight=1)
        self.right_analysis_panel.columnconfigure(0, weight=1)

        # --- Row 0: Top Catalog Panel ---
        self.top_catalog_panel = ctk.CTkFrame(self.right_analysis_panel, fg_color=THEME["bg_panel"], corner_radius=8,
                                              border_width=1,
                                              border_color=THEME.get("border_color", THEME["bg_surface"]))
        self.top_catalog_panel.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.layout("Borderless.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])
        style.configure(
            "Borderless.Treeview",
            background=THEME["bg_surface"],
            foreground=THEME["text_primary"],
            fieldbackground=THEME["bg_surface"],
            rowheight=18,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
        )
        style.map(
            "Borderless.Treeview",
            background=[("selected", THEME["btn_hover"])],
            foreground=[("selected", "#ffffff")]
        )
        style.configure(
            "Borderless.Treeview.Heading",
            background=THEME["bg_panel"],
            foreground=THEME["text_primary"],
            font=("Arial", 10, "bold"),
            relief="flat",
            borderwidth=0
        )
        style.map(
            "Borderless.Treeview.Heading",
            background=[('active', THEME["bg_panel"]), ('selected', THEME["bg_panel"])],
            foreground=[('active', THEME["text_primary"]), ('selected', THEME["text_primary"])]
        )

        self.tree_frame = ctk.CTkFrame(self.top_catalog_panel, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.pgn_scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical")
        self.pgn_scrollbar.pack(side="right", fill="y", padx=(2, 0), pady=0)

        self.pgn_tree = ttk.Treeview(
            self.tree_frame,
            columns=("no", "white", "black", "result"),
            show="headings",
            selectmode="browse",
            height=3,
            takefocus=False,
            style="Borderless.Treeview"
        )
        self.pgn_tree.heading("no", text=" ")
        self.pgn_tree.heading("white", text="White Player", anchor="w")
        self.pgn_tree.heading("black", text="Black Player", anchor="w")
        self.pgn_tree.heading("result", text="Res")

        self.pgn_tree.column("no", width=30, anchor="center")
        self.pgn_tree.column("white", width=135, anchor="w")
        self.pgn_tree.column("black", width=135, anchor="w")
        self.pgn_tree.column("result", width=45, anchor="center")

        def _on_tree_selection(event):
            self._on_tree_selection_event(event)

        self.pgn_tree.bind("<<TreeviewSelect>>", _on_tree_selection)

        self.pgn_scrollbar.configure(command=self.pgn_tree.yview)
        self.pgn_tree.configure(yscrollcommand=self.pgn_scrollbar.set)
        self.pgn_tree.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        # --- Row 1: Thin Evaluation Bar Panel (Good, Bad, IDK) ---
        self.eval_bar_frame = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color=THEME["bg_panel"],
            corner_radius=6,
            border_width=1,
            border_color=THEME.get("border_color", THEME["bg_surface"]),
            height=32
        )
        self.eval_bar_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=(0, 8))
        self.eval_bar_frame.grid_propagate(False)

        self.eval_bar_frame.grid_rowconfigure(0, weight=1)
        self.eval_bar_frame.grid_columnconfigure((0, 1, 2), weight=1)

        eval_btn_height = 20
        eval_btn_corner = 6
        eval_btn_font = ctk.CTkFont(size=11)
        eval_btn_hover = THEME["btn_hover"]
        eval_btn_initial = THEME["btn_initial"]
        eval_text_color = THEME["text_primary"]

        self.btn_eval_good = ctk.CTkButton(
            self.eval_bar_frame,
            text="Good",
            height=eval_btn_height,
            corner_radius=eval_btn_corner,
            border_width=0,
            fg_color=eval_btn_initial,
            hover_color=eval_btn_hover,
            text_color=eval_text_color,
            font=eval_btn_font,
            command=self._eval_good_action
        )
        self.btn_eval_good.grid(row=0, column=0, padx=4, pady=4, sticky="ew")

        self.btn_eval_bad = ctk.CTkButton(
            self.eval_bar_frame,
            text="Bad",
            height=eval_btn_height,
            corner_radius=eval_btn_corner,
            border_width=0,
            fg_color=eval_btn_initial,
            hover_color=eval_btn_hover,
            text_color=eval_text_color,
            font=eval_btn_font,
            command=self._eval_bad_action
        )
        self.btn_eval_bad.grid(row=0, column=1, padx=4, pady=4, sticky="ew")

        self.btn_eval_idk = ctk.CTkButton(
            self.eval_bar_frame,
            text="IDK",
            height=eval_btn_height,
            corner_radius=eval_btn_corner,
            border_width=0,
            fg_color=eval_btn_initial,
            hover_color=eval_btn_hover,
            text_color=eval_text_color,
            font=eval_btn_font,
            command=self._eval_idk_action
        )
        self.btn_eval_idk.grid(row=0, column=2, padx=4, pady=4, sticky="ew")

        # --- Row 2: Analysis Panel ---
        self.analysis_container_frame = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color=THEME["bg_panel"],
            corner_radius=8,
            border_width=1,
            border_color=THEME.get("border_color", THEME["bg_surface"])
        )
        self.analysis_container_frame.grid(row=2, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_analysis_title = ctk.CTkLabel(
            self.analysis_container_frame,
            text="Analysis",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.get("text_secondary", "#94a3b8")
        )
        self.lbl_analysis_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.analysis_wrapper = ctk.CTkFrame(self.analysis_container_frame, fg_color="transparent")
        self.analysis_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.analysis_textbox = ctk.CTkTextbox(
            self.analysis_wrapper,
            fg_color=THEME["bg_surface"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=LAYOUT["analysis_box_height"]
        )

        self.analysis_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")
        self.analysis_textbox.pack(fill="both", expand=True, padx=0, pady=0)

        # --- Row 3: Game Details Panel ---
        self.pgn_data_panel = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color=THEME["bg_panel"],
            corner_radius=8,
            border_width=1,
            border_color=THEME.get("border_color", THEME["bg_surface"])
        )
        self.pgn_data_panel.grid(row=3, column=0, sticky="nsew", padx=0, pady=0)

        self.pgn_data_header = ctk.CTkFrame(self.pgn_data_panel, fg_color="transparent")
        self.pgn_data_header.pack(fill="x", padx=10, pady=(6, 2))

        self.lbl_pgn_data_title = ctk.CTkLabel(
            self.pgn_data_header,
            text="Game Details",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME.get("text_secondary", "#94a3b8")
        )
        self.lbl_pgn_data_title.pack(side="left")

        self.btn_close_pgn_data = ctk.CTkButton(
            self.pgn_data_header,
            text="X",
            width=26,
            height=26,
            fg_color="transparent",
            text_color=THEME.get("text_secondary", "#94a3b8"),
            hover_color=THEME.get("border_color", THEME["bg_surface"]),
            font=ctk.CTkFont(size=15, weight="bold"),
            command=self.toggle_pgn_data_panel
        )
        self.btn_close_pgn_data.pack(side="right")

        self.pgn_data_text = ctk.CTkTextbox(
            self.pgn_data_panel,
            fg_color=THEME["bg_surface"],
            text_color=THEME["text_primary"],
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=70
        )
        self.pgn_data_text._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0)
        self.pgn_data_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.pgn_data_text.insert("end", "[No game selected. Click a game to load its details...]\n")

        def _bind_keys(event=None):
            top = self.winfo_toplevel()
            top.bind_all("<Key-f>", self._handle_keypress)
            top.bind_all("<Key-F>", self._handle_keypress)
            top.bind_all("<Left>", self._handle_left)
            top.bind_all("<Right>", self._handle_right)
            top.bind_all("<Up>", self._handle_up)
            top.bind_all("<Down>", self._handle_down)

        self.bind("<Map>", _bind_keys)
        self.after(100, _bind_keys)