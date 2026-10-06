import threading
import os
import platform
from pathlib import Path
import chess
import chess.engine
from core.chess_engine import ChessEngine
from core.constants import THEME
from ..engine_mixins.engine_review_mixin import EngineReviewMixin
from ..engine_mixins.engine_candidate_mixin import EngineCandidateMixin
from ..engine_mixins.engine_standard_mixin import EngineStandardMixin


class CatalogEngineMixin(EngineReviewMixin, EngineCandidateMixin, EngineStandardMixin):
    """
    Unified engine mixin managing:
    1. Raw live engine PV evaluation exclusively for the left Engine panel.
    2. Mode routing and worker dispatchers for the right Analysis panel.
    """

    def on_piece_moved(self, move=None):
        """Triggers a full reset of the live raw engine analysis when pieces are moved."""
        print("[DEBUG] Piece moved detected. Resetting live engine analysis.")
        self.stop_raw_engine_analysis()
        self.clear_raw_engine_display()

    def clear_raw_engine_display(self):
        """Clears out the left-column PV text display box."""
        self.update_engine_display("[No active position to evaluate.]\n")

    def update_engine_display(self, text):
        """STRICTLY controls the left-column engine panel textbox for raw PV lines only."""
        target_box = None
        for attr_name in ("pv_textbox", "raw_engine_textbox", "engine_textbox", "left_textbox", "_cached_analysis_box"):
            box = getattr(self, attr_name, None)
            if box:
                target_box = box
                break

        if target_box:
            try:
                target_box.configure(fg_color=THEME["bg_surface"])
                inner_box = getattr(target_box, "_textbox", getattr(target_box, "textbox", target_box))

                try:
                    inner_box.configure(font=("Arial", 11))
                except Exception:
                    pass

                inner_box.configure(state="normal")
                inner_box.delete("1.0", "end")
                inner_box.insert("end", text)
                inner_box.configure(state="disabled")
            except Exception as e:
                print(f"[ENGINE DISPLAY ERROR] {e}")
        else:
            print(f"[ENGINE DISPLAY WARNING] No engine textbox found on UI! Text was:\n{text}")

    def toggle_engine_action(self):
        """Controls the independent left Engine button with start/stop/pause depth-30 state management."""
        is_running = getattr(self, "_engine_running", False)
        pausing_state = getattr(self, "_engine_pausing_to_depth_30", False)
        worker = getattr(self, "_current_raw_engine_worker", None)

        if is_running and (worker is None or not worker.is_alive()):
            is_running = False
            self._engine_running = False
            self._engine_pausing_to_depth_30 = False

        print(f"[DEBUG] Engine button clicked! Synced state: running={is_running}, pausing={pausing_state}")

        if not is_running:
            self._engine_running = True
            self._engine_pausing_to_depth_30 = False
            self.start_raw_engine_analysis()
        elif is_running and not pausing_state:
            print("[DEBUG] Stop requested: Letting analysis continue smoothly up to depth 30...")
            self._engine_pausing_to_depth_30 = True
            if worker:
                worker.pausing_to_depth_30 = True
        else:
            print("[DEBUG] Second stop press: Resetting engine display completely.")
            self.stop_raw_engine_analysis()
            self.clear_raw_engine_display()

    def start_raw_engine_analysis(self):
        """Runs background worker for raw engine PV lines (MultiPV=5, depth 30) targeting ONLY the left engine panel."""
        print("[DEBUG] start_raw_engine_analysis triggered.")

        if not hasattr(self, "current_node") or self.current_node is None or isinstance(self.current_node, int):
            game_obj = getattr(self, "current_game", None) or getattr(self, "active_game", None)
            lists_to_check = ["game_list", "filtered_games", "current_games", "games"]
            if not game_obj:
                for lst_name in lists_to_check:
                    lst = getattr(self, lst_name, None)
                    if lst:
                        idx = self.current_node if isinstance(self.current_node, int) else 0
                        if 0 <= idx < len(lst):
                            game_obj = lst[idx]
                            break
            if game_obj:
                if hasattr(game_obj, "root"):
                    self.current_node = game_obj.root()
                elif hasattr(game_obj, "board"):
                    self.current_node = game_obj
                elif isinstance(game_obj, dict) and "game" in game_obj:
                    g = game_obj["game"]
                    self.current_node = g.root() if hasattr(g, "root") else g

        if not hasattr(self, "current_node") or self.current_node is None or isinstance(self.current_node, int):
            self.update_engine_display("[No active position to evaluate.]\n")
            return

        try:
            board_obj = self.current_node.board()
        except Exception as e:
            self.update_engine_display(f"[Error evaluating position: {e}]\n")
            return

        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True

        self._engine_running = True
        self._engine_pausing_to_depth_30 = False

        for btn_name in ("btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_hover"], text="Stop Engine")
                except Exception:
                    pass

        outer_self = self

        class RawEngineWorker(threading.Thread):
            def __init__(self, board_state, outer):
                super().__init__()
                self.board_state = board_state
                self.outer = outer
                self.cancel = False
                self.pausing_to_depth_30 = False
                self.daemon = True

            def run(self):
                print("[RAW ENGINE WORKER] Starting thread analysis (MultiPV=5) for left panel...")
                engine = None
                try:
                    engine_path = "stockfish"
                    exe_filename = "stockfish.exe" if platform.system() == "Windows" else "stockfish"

                    for folder_name in ("engine", "engines"):
                        folder_path = Path(folder_name)
                        if folder_path.exists() and folder_path.is_dir():
                            candidate = folder_path / exe_filename
                            if candidate.exists():
                                engine_path = str(candidate.resolve())
                                break
                            for file_path in folder_path.iterdir():
                                if file_path.is_file():
                                    if platform.system() == "Windows" and file_path.suffix.lower() == ".exe":
                                        engine_path = str(file_path.resolve())
                                        break
                                    elif platform.system() != "Windows":
                                        engine_path = str(file_path.resolve())
                                        break

                    engine = chess.engine.SimpleEngine.popen_uci(engine_path)
                    limit = chess.engine.Limit(depth=30)

                    with engine.analysis(self.board_state, limit, multipv=5) as analysis:
                        latest_lines = {}
                        for info in analysis:
                            if self.cancel:
                                break

                            current_depth = info.get("depth", 0)
                            multipv_idx = info.get("multipv", 1)
                            score = info.get("score")
                            pv = info.get("pv", [])

                            if score and pv:
                                score_cp = score.white().score(mate_score=10000)
                                if score.is_mate():
                                    mate_val = score.white().mate()
                                    eval_str = f"M{abs(mate_val)}" if mate_val != 0 else "M0"
                                    if mate_val < 0:
                                        eval_str = f"-{eval_str}"
                                    else:
                                        eval_str = f"+{eval_str}"
                                else:
                                    eval_str = f"{score_cp / 100.0:+.2f}"

                                latest_lines[multipv_idx] = {
                                    "depth": current_depth,
                                    "eval": eval_str,
                                    "pv": pv
                                }

                                formatted_lines = []
                                for idx in sorted(latest_lines.keys()):
                                    line_data = latest_lines[idx]
                                    d = line_data["depth"]
                                    e = line_data["eval"]
                                    moves = line_data["pv"]

                                    temp_board = self.board_state.copy()
                                    numbered_pv = []
                                    for move in moves:
                                        san_move = temp_board.san(move)
                                        if temp_board.turn == chess.WHITE:
                                            numbered_pv.append(f"{temp_board.fullmove_number}. {san_move}")
                                        else:
                                            if len(numbered_pv) == 0:
                                                numbered_pv.append(f"{temp_board.fullmove_number}... {san_move}")
                                            else:
                                                numbered_pv.append(san_move)
                                        temp_board.push(move)

                                    moves_str = " ".join(numbered_pv)
                                    formatted_lines.append(f"{idx}. Depth {d}  Eval: {e}  {moves_str}")

                                display_text = "\n\n".join(formatted_lines) + "\n"
                                self.outer.after(0, lambda dt=display_text: self.outer.update_engine_display(dt))

                            if current_depth >= 30 and self.pausing_to_depth_30:
                                break

                except Exception as e:
                    print(f"[RAW ENGINE WORKER CRASH] {e}")
                finally:
                    if engine:
                        try:
                            engine.quit()
                        except Exception:
                            pass
                    self.outer.after(0, self.outer.stop_raw_engine_analysis)

        self._current_raw_engine_worker = RawEngineWorker(board_obj, self)
        self._current_raw_engine_worker.start()

    def stop_raw_engine_analysis(self):
        if hasattr(self, '_current_raw_engine_worker') and self._current_raw_engine_worker:
            self._current_raw_engine_worker.cancel = True
            self._current_raw_engine_worker = None

        self._engine_running = False
        for btn_name in ("btn_engine_action", "btn_engines"):
            btn = getattr(self, btn_name, None)
            if btn is not None:
                try:
                    btn.configure(fg_color=THEME["btn_initial"], text="Engine")
                except Exception:
                    pass

    def trigger_engine_mode(self, mode):
        """Routes review, candidates, and standard analysis modes to the right-side analysis panel."""
        self.active_engine_mode = mode
        self._selected_mode_button = mode

        mode_buttons = {
            "review": ("btn_review", "btn_review_mode"),
            "candidates": ("btn_candidates", "btn_candidate_moves"),
            "standard": ("btn_standard", "btn_standard_mode", "btn_engines")
        }

        def _apply_styles():
            for m, btn_names in mode_buttons.items():
                is_active = (mode == m)
                for name in btn_names:
                    btn = getattr(self, name, None)
                    if btn is not None:
                        try:
                            btn.configure(
                                fg_color=THEME["btn_hover"] if is_active else THEME["btn_initial"],
                                hover_color=THEME["btn_hover"],
                                text_color=THEME["text_primary"],
                            )
                        except Exception:
                            pass

        _apply_styles()
        self.after_idle(_apply_styles)

        if hasattr(self, "frame_review") and self.frame_review:
            try:
                self.frame_review.configure(border_width=0 if mode == "review" else 1)
            except Exception:
                pass
        if hasattr(self, "frame_candidates") and self.frame_candidates:
            try:
                self.frame_candidates.configure(border_width=0 if mode == "candidates" else 1)
            except Exception:
                pass
        if hasattr(self, "frame_standard") and self.frame_standard:
            try:
                self.frame_standard.configure(border_width=0 if mode == "standard" else 1)
            except Exception:
                pass

        if mode == "review":
            EngineReviewMixin.trigger_engine_mode(self, "review")
        elif mode == "candidates":
            EngineCandidateMixin.trigger_engine_mode(self, "candidates")
        elif mode == "standard":
            EngineStandardMixin.trigger_engine_mode(self, "standard")