# gui/chess_board.py

import io
from PIL import Image
import customtkinter as ctk
import chess

PIECE_PATH = "assets/pieces/"


def load_piece_image(filename, size=55):
    """Loads SVG piece using cairosvg and converts to CTkImage."""
    import cairosvg
    try:
        png_data = cairosvg.svg2png(
            url=PIECE_PATH + filename,
            output_width=max(15, size),
            output_height=max(15, size)
        )
        image = Image.open(io.BytesIO(png_data))
        return ctk.CTkImage(light_image=image, dark_image=image, size=(max(15, size), max(15, size)))
    except Exception as e:
        print(f"Error loading piece image {filename}: {e}")
        return None


PIECE_MAP = {
    'P': 'wp.svg', 'R': 'wr.svg', 'N': 'wn.svg', 'B': 'wb.svg', 'Q': 'wq.svg', 'K': 'wk.svg',
    'p': 'bp.svg', 'r': 'br.svg', 'n': 'bn.svg', 'b': 'bb.svg', 'q': 'bq.svg', 'k': 'bk.svg'
}


class ChessBoardWidget(ctk.CTkFrame):
    def __init__(self, parent, square_size=55, is_popout=False, **kwargs):
        super().__init__(parent, fg_color="#0f172a", corner_radius=0, **kwargs)
        self.square_size = square_size
        self.is_popout = is_popout
        self.board = chess.Board()
        self.squares = {}
        self.piece_labels = {}
        self.image_cache = {}
        self.flipped = False
        self.popout_window = None

        self._build_ui()
        self.render_board()
        self._bind_keyboard_events()

        # Track actual pixel size changes smoothly via square frame bindings
        self.squares[(0, 0)].bind("<Configure>", self._on_square_resize)

    def _build_ui(self):
        """Builds a layout with vertical action buttons and a fully responsive grid."""
        for widget in self.winfo_children():
            widget.destroy()

        self.squares.clear()
        self.piece_labels.clear()

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        if self.is_popout:
            panel_width = 60
            self.control_panel = ctk.CTkFrame(self, fg_color="transparent", width=panel_width)
            self.control_panel.grid(row=0, column=0, sticky="sw", padx=(0, 2), pady=0)
            self.control_panel.grid_propagate(False)

            button_width = panel_width - 4
            button_height = 35
            font_size = 16
            btn_fg = "transparent"
            btn_hover = "#344268"
            text_color = "#8292a8"

            self.flip_button = ctk.CTkButton(
                self.control_panel, text="↻", width=button_width, height=button_height,
                fg_color=btn_fg, hover_color=btn_hover, text_color=text_color, font=("Arial", font_size),
                command=self.toggle_flip
            )
            self.flip_button.pack(side="top", pady=(0, 4), anchor="w")

            self.popout_button = ctk.CTkButton(
                self.control_panel, text=chr(9704), width=button_width, height=button_height,
                fg_color=btn_fg, hover_color=btn_hover, text_color=text_color, font=("Arial", font_size),
                command=self.toggle_popout
            )
            self.popout_button.pack(side="top", pady=(0, 4), anchor="w")

            self.prev_button = ctk.CTkButton(
                self.control_panel, text="◀", width=button_width, height=button_height,
                fg_color=btn_fg, hover_color=btn_hover, text_color=text_color, font=("Arial", font_size - 2),
                command=self._on_left_arrow
            )
            self.prev_button.pack(side="top", pady=(0, 4), anchor="w")

            self.next_button = ctk.CTkButton(
                self.control_panel, text="▶", width=button_width, height=button_height,
                fg_color=btn_fg, hover_color=btn_hover, text_color=text_color, font=("Arial", font_size - 2),
                command=self._on_right_arrow
            )
            self.next_button.pack(side="top", anchor="w")

        else:
            panel_width = 90
            self.control_panel = ctk.CTkFrame(self, fg_color="transparent", width=panel_width)
            self.control_panel.grid(row=0, column=0, sticky="sw", padx=(0, 0), pady=0)
            self.control_panel.grid_propagate(False)

            button_width = panel_width - 8
            button_height = 28
            btn_fg = "transparent"
            btn_hover = "#344268"
            text_color_normal = "#8292a8"

            def create_hover_button(parent, symbol, full_text, font_size):
                btn = ctk.CTkButton(
                    parent,
                    text=f"{full_text} {symbol}",
                    width=button_width,
                    height=button_height,
                    fg_color=btn_fg,
                    hover_color=btn_hover,
                    text_color=text_color_normal,
                    font=("Arial", font_size),
                    anchor="e"
                )
                return btn

            self.flip_button = create_hover_button(self.control_panel, "↻", "Flip", 14)
            self.flip_button.configure(command=self.toggle_flip)
            self.flip_button.pack(side="top", pady=(0, 4), anchor="w")

            self.popout_button = create_hover_button(self.control_panel, chr(9703), "Pop Out", 14)
            self.popout_button.configure(command=self.toggle_popout)
            self.popout_button.pack(side="top", pady=(0, 4), anchor="w")

            self.prev_button = create_hover_button(self.control_panel, "◀", "Prev ", 12)
            self.prev_button.configure(command=self._on_left_arrow)
            self.prev_button.pack(side="top", pady=(0, 4), anchor="w")

            self.next_button = create_hover_button(self.control_panel, "▶", "Next ", 12)
            self.next_button.configure(command=self._on_right_arrow)
            self.next_button.pack(side="top", pady=(0, 4), anchor="w")

        # Right container for the 8x8 chessboard
        self.grid_container = ctk.CTkFrame(self, fg_color="#0f172a", corner_radius=0)
        self.grid_container.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=0)

        for row in range(8):
            self.grid_container.grid_rowconfigure(row, weight=1)
            self.grid_container.grid_columnconfigure(row, weight=1)

            for col in range(8):
                square_color = "#9f7939" if (row + col) % 2 else "#fbcba4"

                square = ctk.CTkFrame(
                    self.grid_container,
                    fg_color=square_color,
                    corner_radius=0
                )
                # sticky="nsew" ensures squares stretch and fill their grid cells uniformly
                square.grid(row=row, column=col, sticky="nsew", padx=0, pady=0)
                square.grid_propagate(False)
                square.pack_propagate(False)

                self.squares[(row, col)] = square

                lbl = ctk.CTkLabel(square, text="", fg_color="transparent")
                lbl.pack(fill="both", expand=True)
                self.piece_labels[(row, col)] = lbl

    def _on_square_resize(self, event):
        """Monitors actual square dimension adjustments organically and redraws pieces."""
        new_size = event.height
        if new_size > 10 and new_size != self.square_size:
            self.square_size = new_size
            self.render_board()

    def resize_board(self, new_square_size):
        """Resizes square grid dimensions, clears image cache, and re-renders SVG pieces."""
        if new_square_size == self.square_size or new_square_size < 15:
            return

        self.square_size = new_square_size
        self.image_cache.clear()
        self.render_board()

    def set_position_fen(self, fen: str):
        """Updates internal board position via FEN string and redraws."""
        self.board.set_fen(fen)
        self.render_board()
        if self.popout_window and hasattr(self, 'popout_board'):
            try:
                self.popout_board.set_position_fen(fen)
            except Exception:
                pass

    def set_board(self, board_obj: chess.Board):
        """Pass a python-chess Board object directly."""
        self.board = board_obj.copy()
        self.render_board()
        if self.popout_window and hasattr(self, 'popout_board'):
            try:
                self.popout_board.set_board(self.board)
            except Exception:
                pass

    def toggle_flip(self):
        """Toggles the board orientation between White and Black perspectives."""
        self.flipped = not self.flipped
        self.render_board()
        if self.popout_window and hasattr(self, 'popout_board'):
            try:
                self.popout_board.flipped = self.flipped
                self.popout_board.render_board()
            except Exception:
                pass

    def toggle_popout(self):
        """Spawns or closes the standalone top-level window with #0f172a background."""
        if self.is_popout:
            try:
                if self.master and hasattr(self.master, 'destroy'):
                    self.master.destroy()
            except Exception:
                pass
            return

        if self.popout_window is not None:
            try:
                self.popout_window.destroy()
            except Exception:
                pass
            self.popout_window = None
            return

        self.popout_window = ctk.CTkToplevel(self)
        self.popout_window.title("Chess Board")
        self.popout_window.configure(fg_color="#0f172a")

        win_w = (self.square_size * 8) + 90
        win_h = (self.square_size * 8) + 20
        self.popout_window.geometry(f"{win_w}x{win_h}")
        self.popout_window.attributes("-topmost", True)

        self.popout_board = ChessBoardWidget(self.popout_window, square_size=self.square_size, is_popout=True)
        self.popout_board.configure(fg_color="#0f172a")
        self.popout_board.flipped = self.flipped
        self.popout_board.set_board(self.board)
        self.popout_board.pack(fill="both", expand=True, padx=0, pady=0)

        def on_close():
            try:
                if self.popout_window:
                    self.popout_window.destroy()
            except Exception:
                pass
            self.popout_window = None

        self.popout_window.protocol("WM_DELETE_WINDOW", on_close)

    def _bind_keyboard_events(self):
        """Binds arrow keys and 'f'/'F' keys at the top-level window to bypass widget focus traps."""
        top_level = self.winfo_toplevel()

        top_level.bind("<Left>", self._on_left_arrow)
        top_level.bind("<Right>", self._on_right_arrow)
        top_level.bind("<Up>", self._on_up_arrow)
        top_level.bind("<Down>", self._on_down_arrow)
        top_level.bind("f", lambda e: self.toggle_flip())
        top_level.bind("F", lambda e: self.toggle_flip())

    def _on_left_arrow(self, event=None):
        if hasattr(self, 'on_step_back') and callable(self.on_step_back):
            self.on_step_back()

    def _on_right_arrow(self, event=None):
        if hasattr(self, 'on_step_forward') and callable(self.on_step_forward):
            self.on_step_forward()

    def _on_up_arrow(self, event=None):
        if hasattr(self, 'on_jump_start') and callable(self.on_jump_start):
            self.on_jump_start()

    def _on_down_arrow(self, event=None):
        if hasattr(self, 'on_jump_end') and callable(self.on_jump_end):
            self.on_jump_end()

    def render_board(self):
        """Reads python-chess board state and updates square images with proper board flipping and scaling."""
        for row in range(8):
            for col in range(8):
                if self.flipped:
                    chess_rank = row
                    chess_file = 7 - col
                else:
                    chess_rank = 7 - row
                    chess_file = col

                square_idx = chess.square(chess_file, chess_rank)
                piece = self.board.piece_at(square_idx)

                label = self.piece_labels.get((row, col))
                if not label:
                    continue

                if piece:
                    filename = PIECE_MAP.get(piece.symbol())
                    cache_key = (filename, self.square_size)
                    if cache_key not in self.image_cache:
                        # Clear old cache values for this piece to prevent memory leaks over time
                        if len(self.image_cache) > 64:
                            self.image_cache.clear()
                        self.image_cache[cache_key] = load_piece_image(filename, size=self.square_size)

                    img = self.image_cache.get(cache_key)
                    label.configure(image=img, text="", fg_color="transparent")
                    label.image = img
                else:
                    label.configure(image="", text="", fg_color="transparent")
                    label.image = None