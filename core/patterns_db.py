from core.constants import THEME


class PatternsDatabase:
    """Handles pattern mode selection and pre-evaluation display state."""

    def trigger_engine_mode(self, mode):
        """Updates active pattern mode and prepares the PV display box before evaluation."""
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

                if mode == "white_patterns_mode":
                    inner_box.insert("end", "=== WHITE PATTERNS READY ===\nSelect a piece or game to evaluate.")
                elif mode == "black_patterns_mode":
                    inner_box.insert("end", "=== BLACK PATTERNS READY ===\nSelect a piece or game to evaluate.")
                elif mode == "opening_pattern_mode":
                    inner_box.insert("end", "=== OPENING MODE READY ===\nClick a game or move to analyze opening extensions.")
                elif mode == "calculation_pattern_mode":
                    inner_box.insert("end", "=== CALCULATION MODE READY ===\nSelect a variation to begin calculation evaluation.")
                else:
                    inner_box.configure(state="disabled")
                    return

                inner_box.insert("end", "\n")
                inner_box.configure(state="disabled")
            except Exception as e:
                print(f"[ERROR in trigger_engine_mode]: {e}")