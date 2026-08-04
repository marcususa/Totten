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
            output_width=size,
            output_height=size
        )
        image = Image.open(io.BytesIO(png_data))
        return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
    except Exception as e:
        print(f"Error loading piece image {filename}: {e}")
        return None


PIECE_MAP = {
    'P': 'wp.svg', 'R': 'wr.svg', 'N': 'wn.svg', 'B': 'wb.svg', 'Q': 'wq.svg', 'K': 'wk.svg',
    'p': 'bp.svg', 'r': 'br.svg', 'n': 'bn.svg', 'b': 'bb.svg', 'q': 'bq.svg', 'k': 'bk.svg'
}


class ChessBoardWidget(ctk.CTkFrame):
    def __init__(self, parent, square_size=55, **kwargs):
        super().__init__(parent, fg_color="transparent", corner_radius=0, **kwargs)
        self.square_size = square_size
        self.board = chess.Board()
        self.squares = {}
        self.piece_labels = {}
        self.image_cache = {}

        self._build_board()
        self.render_board()

    def _build_board(self):
        """Creates an 8x8 grid with explicit dimensions based on self.square_size."""
        # Clear existing square widgets if rebuilding
        for widget in self.winfo_children():
            widget.destroy()

        self.squares.clear()
        self.piece_labels.clear()

        for row in range(8):
            self.grid_rowconfigure(row, minsize=self.square_size, weight=0)
            self.grid_columnconfigure(row, minsize=self.square_size, weight=0)

            for col in range(8):
                square_color = "#9f7939" if (row + col) % 2 else "#fbcba4"

                square = ctk.CTkFrame(
                    self,
                    width=self.square_size,
                    height=self.square_size,
                    fg_color=square_color,
                    corner_radius=0
                )
                square.grid(row=row, column=col, sticky="nsew", padx=0, pady=0)
                square.grid_propagate(False)
                square.pack_propagate(False)

                self.squares[(row, col)] = square

                lbl = ctk.CTkLabel(square, text="", width=self.square_size, height=self.square_size)
                lbl.pack(fill="both", expand=True)
                self.piece_labels[(row, col)] = lbl

    def resize_board(self, new_square_size):
        """Resizes square grid dimensions, clears image cache, and re-renders SVG pieces."""
        if new_square_size == self.square_size or new_square_size < 15:
            return

        self.square_size = new_square_size
        self.image_cache.clear()  # Clear cache so SVGs re-render at new dimensions
        self._build_board()
        self.render_board()

    def set_position_fen(self, fen: str):
        """Updates internal board position via FEN string and redraws."""
        self.board.set_fen(fen)
        self.render_board()

    def set_board(self, board_obj: chess.Board):
        """Pass a python-chess Board object directly."""
        self.board = board_obj.copy()
        self.render_board()

    def render_board(self):
        """Reads python-chess board state and updates square images."""
        for row in range(8):
            for col in range(8):
                square_idx = chess.square(col, 7 - row)
                piece = self.board.piece_at(square_idx)

                label = self.piece_labels.get((row, col))
                if not label:
                    continue

                if piece:
                    filename = PIECE_MAP.get(piece.symbol())
                    if filename not in self.image_cache:
                        self.image_cache[filename] = load_piece_image(filename, size=self.square_size)

                    img = self.image_cache.get(filename)
                    label.configure(image=img, text="")
                    label.image = img
                else:
                    label.configure(image="", text="")
                    label.image = None