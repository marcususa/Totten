from pathlib import Path
import chess
import chess.pgn
import customtkinter as ctk
from core.constants import get_saved_pgn_filename
from gui.chess_board import ChessBoardWidget

from core.constants import get_saved_pgn_filename

# File 2 module titled "catalog_analysis.py"

class CatalogAnalysisMixin:
    def init_catalog_bindings(self):
        # Explicit bindings
        self.pgn_tree.bind("<Button-1>", lambda e: self.toggle_game(e))
        self.pgn_tree.bind("<FocusIn>", lambda e: "break")

        # Bindings & Setup
        self.after(100, self._bind_global_keys)
        self.load_games(self.filename)

    def _bind_global_keys(self):
        top = self.winfo_toplevel()
        top.bind("<Left>", lambda e: self.on_prev_move())
        top.bind("<Right>", lambda e: self.on_next_move())
        top.bind("<Up>", lambda e: self.on_first_move())
        top.bind("<Down>", lambda e: self.on_last_move())

    def load_games(self, filename=None):
        self.pgn_tree.delete(*self.pgn_tree.get_children())
        self.preview_lookup.clear()

        target_file = (
                filename
                or get_saved_pgn_filename()
                or "personal_catalog.pgn"
        )

        load_path = Path(__file__).resolve().parent.parent / target_file
        data = []

        if load_path.exists():
            try:
                with open(load_path, "r", encoding="utf-8") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        data.append(game)
            except Exception as e:
                print(f"Error reading PGN file {target_file}: {e}")

        if data:
            self.lbl_empty_state.pack_forget()
            for idx, game in enumerate(data, start=1):
                headers = game.headers
                white = headers.get("White", "Unknown")
                black = headers.get("Black", "Unknown")
                result = headers.get("Result", "*")

                item_id = self.pgn_tree.insert(
                    "",
                    "end",
                    values=(idx, white, black, result)
                )
                self.preview_lookup[item_id] = game
        else:
            self.lbl_empty_state.pack(
                padx=10,
                pady=15,
                anchor="center"
            )

    # --- POP OUT & RE-DOCK LOGIC ---
    def pop_out_board(self):
        if self.popout_window and self.popout_window.winfo_exists():
            self.popout_window.destroy()
            self.redock_board()
            return

        self.left_board_panel.pack_forget()
        self.is_board_popped_out = True

        self.popout_window = ctk.CTkToplevel(self)
        self.popout_window.title("Chessboard Analysis (Pop-Out)")
        self.popout_window.geometry("550x600")

        self.popout_window.grid_rowconfigure(0, weight=1)
        self.popout_window.grid_rowconfigure(1, weight=0)
        self.popout_window.grid_columnconfigure(0, weight=1)
        self.popout_window.protocol("WM_DELETE_WINDOW", self.redock_board)

        self.popout_window.bind("<Left>", lambda e: self.on_prev_move())
        self.popout_window.bind("<Right>", lambda e: self.on_next_move())
        self.popout_window.bind("<Up>", lambda e: self.on_first_move())
        self.popout_window.bind("<Down>", lambda e: self.on_last_move())

        self.popout_window.update_idletasks()
        win_w, win_h = 550, 600
        screen_w = self.popout_window.winfo_screenwidth()
        screen_h = self.popout_window.winfo_screenheight()
        pos_x = (screen_w // 2) - (win_w // 2)
        pos_y = (screen_h // 2) - (win_h // 2)
        self.popout_window.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

        self.popout_container = ctk.CTkFrame(self.popout_window, fg_color="transparent")
        self.popout_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.popout_container.grid_rowconfigure(0, weight=1)
        self.popout_container.grid_columnconfigure(0, weight=1)

        self.board_widget.pack_forget()
        self.placeholder_lbl.pack(expand=True)

        self.popout_board = ChessBoardWidget(self.popout_container, square_size=60)
        self.popout_board.grid(row=0, column=0, sticky="")

        self.popout_controls = ctk.CTkFrame(self.popout_window, fg_color="transparent")
        self.popout_controls.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 15))

        pop_btn_prev = ctk.CTkButton(
            self.popout_controls, text="◀ Prev", height=28,
            fg_color="#2e4a8c", hover_color="#4870cd",
            command=self.on_prev_move
        )
        pop_btn_prev.pack(side="left", expand=True, fill="x", padx=(0, 5))

        pop_btn_next = ctk.CTkButton(
            self.popout_controls, text="Next ▶", height=28,
            fg_color="#2e4a8c", hover_color="#4870cd",
            command=self.on_next_move
        )
        pop_btn_next.pack(side="left", expand=True, fill="x", padx=(5, 0))

        self.popout_board.set_board(self.board_widget.board)
        self.btn_popout.configure(text="Dock Board ↙")
        self.popout_container.bind("<Configure>", self._on_popout_resize)

    def _on_popout_resize(self, event):
        if not self.popout_board or not self.popout_window:
            return
        padding = 24
        available_size = min(event.width, event.height) - padding
        new_square_size = max(20, available_size // 8)
        self.popout_board.resize_board(new_square_size)

    def redock_board(self):
        self.placeholder_lbl.pack_forget()
        self.board_widget.pack()

        if self.popout_board:
            self.board_widget.set_board(self.popout_board.board)
            self.popout_board = None

        if self.popout_window and self.popout_window.winfo_exists():
            self.popout_window.destroy()
        self.popout_window = None
        self.btn_popout.configure(text="Pop Out ↗")

        self.left_board_panel.pack(side="top", fill="both", expand=False, padx=0, pady=(0, 5),
                                   before=self.top_catalog_panel)
        self.is_board_popped_out = False

    def _update_active_boards(self, board_obj):
        self.board_widget.set_board(board_obj)
        if self.popout_board:
            self.popout_board.set_board(board_obj)