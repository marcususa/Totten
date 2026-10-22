from core.constants import THEME

CONFIRMED_GOOD_MOVES = set()
REJECTED_BAD_MOVES = set()

def mark_move_good(clean_san: str):
    CONFIRMED_GOOD_MOVES.add(clean_san)
    REJECTED_BAD_MOVES.discard(clean_san)

def mark_move_bad(clean_san: str):
    REJECTED_BAD_MOVES.add(clean_san)
    CONFIRMED_GOOD_MOVES.discard(clean_san)

# patterns_db.py
WHITE_PATTERNS = [
    ("f3", 1), ("f4", 1), ("g4", 1),
    ("h3, g4", 1),
    ("Bb4, Bb5", 1), ("Bb5, Bb4", 1), ("Bb5, Ba4", 1),
    ("Bf1", 1), ("Bg5, Bh4", 1), ("Bxh6", 1),
    ("Nb5", 1), ("Nc3, Ne2, Ng3", 1),
    ("Nxd5", 1), ("Nxe5", 1), ("Nh2", 1),
    ("Ra2", 1), ("Rb1", 1),
    ("Qb3", 1), ("Qe2", 1), ("Kf1", 1)
]

BLACK_PATTERNS = [
    ("f6", 1), ("f5", 1), ("g5", 1),
    ("h6, g5", 1),
    ("Ba6, Ba7", 1), ("Bc5, Bb6", 1),
    ("Bf8", 1), ("Bh3", 1),
    ("Na5", 1), ("Nc6, Ne7, Ng3", 1),
    ("Nxd4", 1), ("Nxe4", 1),
    ("Ra7", 1), ("Rb8", 1),
    ("Qb6", 1), ("Qe7", 1), ("Kf7", 1)
]

BOTH_PATTERNS = [
    ("Be3, Bc5", 1),
    ("Bc4, Be6", 1)
]


def get_patterns(target_color):
    """Returns stored_singles set and stored_chains list for the given target color ('W' or 'B')."""
    stored_singles = set()
    stored_chains = []

    raw_list = []
    if target_color == "W":
        raw_list = WHITE_PATTERNS + BOTH_PATTERNS
    elif target_color == "B":
        raw_list = BLACK_PATTERNS + BOTH_PATTERNS

    for pattern_str, tier in raw_list:
        if "," in pattern_str:
            clean_chain = pattern_str.strip().replace("+", "").replace("#", "").lower()
            formatted_chain = clean_chain.replace(",", "")
            stored_chains.append(formatted_chain)

            for m in pattern_str.split(","):
                cm = m.strip().replace("+", "").replace("#", "").lower()
                if cm and len(cm) <= 7:
                    stored_singles.add(cm)
        else:
            clean_item = pattern_str.strip().replace("+", "").replace("#", "").lower()
            if " " in clean_item:
                stored_chains.append(clean_item)
            elif clean_item and len(clean_item) <= 7:
                stored_singles.add(clean_item)

    # Incorporate user evaluations directly into the pattern set
    stored_singles.update(CONFIRMED_GOOD_MOVES)
    stored_singles.difference_update(REJECTED_BAD_MOVES)

    return stored_singles, stored_chains


class PatternsDatabase:
    """Handles hardcoded pattern checklist rules and motif chain matching."""

    def trigger_engine_mode(self, mode):
        """PGN-compliant continuous text stream with inline pattern comment annotations."""
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

                # Load patterns instantly from the hardcoded module functions
                stored_singles, stored_chains = get_patterns(target_color)

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

                        if clean_san in REJECTED_BAD_MOVES:
                            match_found = False
                        elif clean_san in CONFIRMED_GOOD_MOVES:
                            match_found = True
                        else:
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
                        prefix = " "

                    if b_move:
                        if not w_move:
                            inner_box.insert("end", f"{prefix}{m_num}... ")
                        else:
                            inner_box.insert("end", " ")

                        is_b_match = (target_color == "B" and b_move["matched"])
                        tag = "pattern_yellow" if is_b_match else ()

                        inner_box.insert("end", b_move['san'], tag)

                inner_box.insert("end", "\n")
                inner_box.configure(state="disabled")

            except Exception as e:
                print(f"[ERROR in trigger_engine_mode]: {e}")