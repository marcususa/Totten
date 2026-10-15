from core.constants import THEME


class PatternsDatabase:
    """Handles DuckDB connections, schema inspections, pattern checklist queries, and motif chain matching."""

    def trigger_engine_mode(self, mode):
        """PGN-compliant continuous text stream with inline pattern comment annotations from DuckDB."""
        if hasattr(self, "stop_raw_engine_analysis"):
            self.stop_raw_engine_analysis()

        self.active_engine_mode = mode
        self._selected_mode_button = mode

        if hasattr(self, "pv_textbox") and self.pv_textbox:
            try:
                target_box = self.pv_textbox
                target_box.configure(fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
                inner_box.configure(state="normal")
                inner_box.delete("1.0", "end")

                inner_box.tag_config("pattern_yellow", foreground=THEME["pattern_yellow"])

                if mode == "white_patterns_mode":
                    target_color = "W"
                    color_label = "White"
                elif mode == "black_patterns_mode":
                    target_color = "B"
                    color_label = "Black"
                elif mode == "opening_pattern_mode":
                    inner_box.insert("end", "=== OPENING MODE READY ===\nClick a game or move to analyze opening extensions.")
                    inner_box.configure(state="disabled")
                    return
                elif mode == "calculation_pattern_mode":
                    inner_box.insert("end", "=== CALCULATION MODE READY ===\nSelect a variation to begin calculation evaluation.")
                    inner_box.configure(state="disabled")
                    return
                else:
                    inner_box.configure(state="disabled")
                    return

                stored_singles = set()
                stored_chains = []
                try:
                    import duckdb
                    conn = duckdb.connect("patterns.duckdb", read_only=True)
                    cols = [col[1] for col in conn.execute("PRAGMA table_info('pattern_checklist')").fetchall()]

                    if 'color' in cols:
                        rows = conn.execute("SELECT * FROM pattern_checklist WHERE color = ? OR color = 'BOTH'", [target_color]).fetchall()
                    else:
                        rows = conn.execute("SELECT * FROM pattern_checklist").fetchall()
                    conn.close()

                    for row in rows:
                        for item in row:
                            if item is not None and isinstance(item, str):
                                clean_item = item.strip().replace("+", "").replace("#", "").lower()
                                if " " in clean_item:
                                    stored_chains.append(clean_item)
                                elif clean_item and len(clean_item) <= 7:
                                    stored_singles.add(clean_item)
                except Exception:
                    pass

                all_moves = []
                raw_target_moves = []
                if hasattr(self, "current_game") and self.current_game:
                    for idx, node in enumerate(self.current_game.mainline(), start=1):
                        is_white = (idx % 2 != 0)
                        san = node.san()
                        clean_san = san.replace("+", "").replace("#", "").lower()
                        move_num = (idx + 1) // 2

                        is_target_side = (target_color == "W" and is_white) or (target_color == "B" and not is_white)
                        match_found = is_target_side and clean_san in stored_singles

                        all_moves.append({
                            "move_num": move_num,
                            "is_white": is_white,
                            "san": san,
                            "clean_san": clean_san,
                            "is_target_side": is_target_side,
                            "matched": match_found
                        })

                        if is_target_side:
                            raw_target_moves.append(clean_san)

                game_phrase = " ".join(raw_target_moves)
                matched_chains = [chain for chain in stored_chains if chain in game_phrase]

                if matched_chains:
                    chains_str = ", ".join([f'"{c}"' for c in matched_chains])
                    inner_box.insert("end", f"{{ Motifs Detected ({color_label}): {chains_str} }} ")

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
                        inner_box.insert("end", f"{prefix}{m_num}. ")
                        is_w_match = (target_color == "W" and w_move["matched"])
                        tag = "pattern_yellow" if is_w_match else ()

                        inner_box.insert("end", w_move['san'], tag)
                        if is_w_match:
                            inner_box.insert("end", f" {{ Pattern Match: {w_move['san']} }}")
                        prefix = " "

                    if b_move:
                        if not w_move:
                            inner_box.insert("end", f"{prefix}{m_num}... ")
                        else:
                            inner_box.insert("end", " ")

                        is_b_match = (target_color == "B" and b_move["matched"])
                        tag = "pattern_yellow" if is_b_match else ()

                        inner_box.insert("end", b_move['san'], tag)
                        if is_b_match:
                            inner_box.insert("end", f" {{ Pattern Match: {b_move['san']} }}")

                inner_box.insert("end", "\n")
                inner_box.configure(state="disabled")

            except Exception as e:
                print(f"[ERROR in trigger_engine_mode]: {e}")