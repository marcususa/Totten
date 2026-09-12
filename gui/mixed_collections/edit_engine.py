import threading
import chess
from core.constants import THEME
from core.chess_engine import ChessEngine


class EditEngineMixin:
    """Mixin class to handle background engine workers and evaluation displays."""

    def toggle_engine_action(self):
        """Controls the independent Engine button for raw live evaluation on the left."""
        is_running = getattr(self, "_engine_running", False)
        if is_running:
            self.start_raw_engine_analysis()
        else:
            self.stop_raw_engine_analysis()

    def start_raw_engine_analysis(self):
        """Runs a lightweight background worker for raw engine lines targeting only pv_textbox."""
        if not hasattr(self, "current_node") or not self.current_node:
            print("[RAW ENGINE] Error: No current_node found.")
            self.update_engine_display("[No active position to evaluate.]\n")
            return

        try:
            board_obj = self.current_node.board()
        except Exception as e:
            print(f"[RAW ENGINE] Error getting board from node: {e}")
            return

        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True

        class RawEngineWorker(threading.Thread):
            def __init__(self, board_state, outer):
                super().__init__()
                self.board_state = board_state
                self.outer = outer
                self.cancel = False
                self.daemon = True

            def run(self):
                print("[RAW ENGINE WORKER] Starting thread analysis...")
                try:
                    engine = ChessEngine()

                    def callback(res):
                        if self.cancel:
                            return
                        print(f"[RAW ENGINE WORKER] Received result callback: {res}")
                        current_depth = res.get('depth', 25)
                        raw_eval = res.get('eval', 0.0)

                        if isinstance(raw_eval, str) and "M" in raw_eval:
                            eval_str = raw_eval
                        else:
                            eval_str = f"{float(raw_eval):+.2f}"

                        pv_lines = res.get('pv_lines', [])
                        if isinstance(pv_lines, list) and pv_lines:
                            formatted_lines = []
                            for idx, line in enumerate(pv_lines, start=1):
                                temp_board = self.board_state.copy()
                                move_tokens = line.strip().split()
                                numbered_pv = []

                                for move_str in move_tokens:
                                    try:
                                        move = temp_board.parse_san(move_str)
                                        if temp_board.turn == chess.WHITE:
                                            numbered_pv.append(f"{temp_board.fullmove_number}. {move_str}")
                                        else:
                                            if len(numbered_pv) == 0:
                                                numbered_pv.append(f"{temp_board.fullmove_number}... {move_str}")
                                            else:
                                                numbered_pv.append(move_str)
                                        temp_board.push(move)
                                    except Exception:
                                        numbered_pv.append(move_str)

                                moves_str = " ".join(numbered_pv)
                                formatted_lines.append(f"{idx}. {current_depth} | Eval: {eval_str} {moves_str}")

                            display_text = "\n\n".join(formatted_lines) + "\n"
                        else:
                            display_text = f"1. {current_depth} | Eval: {eval_str} | PV: (none)\n"

                        self.outer.after(0, lambda: self.outer.update_engine_display(display_text))

                    engine.analyze_position(
                        self.board_state,
                        depths=(10, 15, 20, 25),
                        multipv=3,
                        callback=callback,
                        worker_ref=self
                    )
                except Exception as e:
                    print(f"[RAW ENGINE WORKER CRASH] {e}")

        self._current_raw_engine_worker = RawEngineWorker(board_obj, self)
        self._current_raw_engine_worker.start()

    def stop_raw_engine_analysis(self):
        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True
            self._current_raw_engine_worker = None

        if hasattr(self, "btn_engine_action") and self.btn_engine_action:
            try:
                self.btn_engine_action.configure(text="Engine")
            except Exception:
                pass

    def update_engine_display(self, text):
        """Strictly controls the left-column pv_textbox for raw engine outputs."""
        target_box = getattr(self, "pv_textbox", None)
        if target_box:
            try:
                target_box.configure(fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))
                inner_box.configure(state="normal")
                inner_box.delete("1.0", "end")
                inner_box.insert("end", text)
                inner_box.configure(state="disabled")
            except Exception as e:
                print(f"[ENGINE DISPLAY ERROR] {e}")