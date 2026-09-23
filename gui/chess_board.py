# gui/chess_board.py

import io
from PIL import Image
import customtkinter as ctk
import chess

PIECE_PATH = "assets/pieces/"


def load_piece_image(filename, size=55):
    """Loads SVG piece using cairosvg and converts to PIL Image for canvas rendering."""
    import cairosvg
    try:
        png_data = cairosvg.svg2png(
            url=PIECE_PATH + filename,
            output_width=max(15, size),
            output_height=max(15, size)
        )
        return Image.open(io.BytesIO(png_data))
    except Exception as e:
        print(f"Error loading piece image {filename}: {e}")
        return None


PIECE_MAP = {
    'P': 'wp.svg', 'R': 'wr.svg', 'N': 'wn.svg', 'B': 'wb.svg', 'Q': 'wq.svg', 'K': 'wk.svg',
    'p': 'bp.svg', 'r': 'br.svg', 'n': 'bn.svg', 'b': 'bb.svg', 'q': 'bq.svg', 'k': 'bk.svg'
}


class ChessBoardWidget(ctk.CTkFrame):
    def __init__(self, parent, square_size=55, is_popout=False, **kwargs):
        super().__init__(parent, fg_color="#172134", corner_radius=0, **kwargs)
        self.square_size = square_size
        self.is_popout = is_popout
        self.board = chess.Board()
        self.flipped = False
        self.popout_window = None

        # Interaction state tracking for dragging and clicking
        self.dragging_piece = None
        self.drag_start_square = None
        self.drag_image_ref = None
        self.drag_image_item = None
        self.selected_square = None  # For click-to-move support

        # Press tracking for hybrid click/drag motion
        self.press_x = 0
        self.press_y = 0
        self.press_square = None
        self.press_piece = None
        self.is_dragging = False

        self.image_cache = {}

        self._build_ui()
        self.render_board()

    def _build_ui(self):
        """Builds control panel layout alongside an interactive canvas board."""
        for widget in self.winfo_children():
            widget.destroy()

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        panel_width = 60 if self.is_popout else 90
        self.control_panel = ctk.CTkFrame(self, fg_color="transparent", width=panel_width)
        self.control_panel.grid(row=0, column=0, sticky="sw", padx=0, pady=0)
        self.control_panel.grid_propagate(False)

        button_width = panel_width - (4 if self.is_popout else 8)
        button_height = 35 if self.is_popout else 28
        btn_fg = "transparent"
        btn_hover = "#344268"
        text_color = "#8292a8"

        self.flip_button = ctk.CTkButton(
            self.control_panel, text="↻ Flip" if not self.is_popout else "↻",
            width=button_width, height=button_height, fg_color=btn_fg,
            hover_color=btn_hover, text_color=text_color, font=("Arial", 14),
            command=self.toggle_flip
        )
        self.flip_button.pack(side="top", pady=(0, 4), anchor="w")

        self.popout_button = ctk.CTkButton(
            self.control_panel, text=f"Pop Out {chr(9703)}" if not self.is_popout else chr(9704),
            width=button_width, height=button_height, fg_color=btn_fg,
            hover_color=btn_hover, text_color=text_color, font=("Arial", 14),
            command=self.toggle_popout
        )
        self.popout_button.pack(side="top", pady=(0, 4), anchor="w")

        self.prev_button = ctk.CTkButton(
            self.control_panel, text="Prev ◀" if not self.is_popout else "◀",
            width=button_width, height=button_height, fg_color=btn_fg,
            hover_color=btn_hover, text_color=text_color, font=("Arial", 12),
            command=self._on_left_arrow
        )
        self.prev_button.pack(side="top", pady=(0, 4), anchor="w")

        self.next_button = ctk.CTkButton(
            self.control_panel, text="Next ▶" if not self.is_popout else "▶",
            width=button_width, height=button_height, fg_color=btn_fg,
            hover_color=btn_hover, text_color=text_color, font=("Arial", 12),
            command=self._on_right_arrow
        )
        self.next_button.pack(side="top", anchor="w")

        board_pixel_size = self.square_size * 8
        self.canvas = ctk.CTkCanvas(
            self,
            width=board_pixel_size,
            height=board_pixel_size,
            bg="#0f172a",
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=0)

        # Bind canvas interaction for all boards
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)

        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _get_chess_square(self, row, col):
        """Translates row/col grid coordinates to chess square index accounting for board orientation."""
        if self.flipped:
            chess_rank = row
            chess_file = 7 - col
        else:
            chess_rank = 7 - row
            chess_file = col
        return chess.square(chess_file, chess_rank)

    def _get_row_col_from_chess_square(self, chess_square):
        """Maps a python-chess square index back to canvas grid row and col."""
        chess_file = chess.square_file(chess_square)
        chess_rank = chess.square_rank(chess_square)
        if self.flipped:
            row = chess_rank
            col = 7 - chess_file
        else:
            row = 7 - chess_rank
            col = chess_file
        return row, col

    def _get_row_col_from_coords(self, x, y):
        """Maps canvas pixel coordinates back to grid row and column."""
        col = int(x // self.square_size)
        row = int(y // self.square_size)
        if 0 <= row < 8 and 0 <= col < 8:
            return row, col
        return None, None

    def _on_press(self, event):
        """Records initial press location for both click-to-move and potential dragging."""
        row, col = self._get_row_col_from_coords(event.x, event.y)
        if row is None or col is None:
            return

        clicked_square = self._get_chess_square(row, col)
        piece = self.board.piece_at(clicked_square)

        self.press_x = event.x
        self.press_y = event.y
        self.press_square = clicked_square
        self.press_piece = piece
        self.is_dragging = False

    def _on_drag_motion(self, event):
        """Triggers dragging mode if the mouse moves away from the press origin without mutating board state."""
        if not self.press_piece:
            return

        if not self.is_dragging:
            dx = abs(event.x - self.press_x)
            dy = abs(event.y - self.press_y)
            if dx > 3 or dy > 3:  # Threshold to distinguish click from drag
                self.is_dragging = True
                self.dragging_piece = self.press_piece
                self.drag_start_square = self.press_square

                # Refresh board view so the piece hides from its start square visually
                self.render_board()

                filename = PIECE_MAP.get(self.dragging_piece.symbol())
                pil_img = self.image_cache.get((filename, self.square_size))
                if not pil_img:
                    pil_img = load_piece_image(filename, size=self.square_size)
                    if pil_img:
                        self.image_cache[(filename, self.square_size)] = pil_img

                if pil_img:
                    from PIL import ImageTk
                    self.drag_image_ref = ImageTk.PhotoImage(pil_img)
                    self.drag_image_item = self.canvas.create_image(
                        event.x, event.y, image=self.drag_image_ref, anchor="center"
                    )

        if self.is_dragging and self.drag_image_item:
            self.canvas.coords(self.drag_image_item, event.x, event.y)

    def _on_release(self, event):
        """Handles mouse release for drag-and-drop or click-to-move with strict python-chess legal move enforcement."""
        if self.drag_image_item:
            self.canvas.delete(self.drag_image_item)
            self.drag_image_item = None
            self.drag_image_ref = None

        row, col = self._get_row_col_from_coords(event.x, event.y)

        if self.is_dragging:
            if self.dragging_piece is not None and self.drag_start_square is not None:
                if row is not None and col is not None:
                    target_square = self._get_chess_square(row, col)

                    promotion = None
                    if self.dragging_piece.piece_type == chess.PAWN and chess.square_rank(target_square) in (0, 7):
                        promotion = chess.QUEEN

                    move = chess.Move(self.drag_start_square, target_square, promotion=promotion)

                    if move in self.board.legal_moves:
                        self.board.push(move)
                        self.sync_with_twin()  # <--- Step 4: Sync after drag-and-drop move

            self.dragging_piece = None
            self.drag_start_square = None
            self.is_dragging = False
            self.selected_square = None
            self.render_board()

        else:
            # Click-to-move handling
            if row is None or col is None:
                self.selected_square = None
                self.render_board()
                return

            clicked_square = self._get_chess_square(row, col)

            if self.selected_square is None:
                # First click: Select the piece if there is one on the square
                piece = self.board.piece_at(clicked_square)
                if piece:
                    self.selected_square = clicked_square
                    self.render_board()
            else:
                # Second click: Attempt to move from selected_square to clicked_square
                target_square = clicked_square

                # If clicking the exact same square twice, deselect it
                if self.selected_square == target_square:
                    self.selected_square = None
                    self.render_board()
                    return

                promotion = None
                selected_piece = self.board.piece_at(self.selected_square)
                if selected_piece and selected_piece.piece_type == chess.PAWN and chess.square_rank(target_square) in (
                        0, 7):
                    promotion = chess.QUEEN

                move = chess.Move(self.selected_square, target_square, promotion=promotion)

                if move in self.board.legal_moves:
                    self.board.push(move)
                    self.sync_with_twin()  # <--- Step 4: Sync after click-to-move

                # Reset selection and refresh view
                self.selected_square = None
                self.render_board()

    def _on_canvas_resize(self, event):
        """Dynamically scales square size if window container resizes."""
        new_size = event.height // 8
        if new_size > 10 and new_size != self.square_size:
            self.square_size = new_size
            self.image_cache.clear()
            self.render_board()

    def resize_board(self, new_square_size):
        if new_square_size == self.square_size or new_square_size < 15:
            return
        self.square_size = new_square_size
        self.image_cache.clear()
        self.canvas.configure(width=new_square_size * 8, height=new_square_size * 8)
        self.render_board()

    def set_position_fen(self, fen: str):
        self.board.set_fen(fen)
        self.render_board()
        if self.popout_window and hasattr(self, 'popout_board'):
            try:
                self.popout_board.set_position_fen(fen)
            except Exception:
                pass

    def set_board(self, board_obj: chess.Board):
        self.board = board_obj.copy()
        self.render_board()
        if self.popout_window and hasattr(self, 'popout_board'):
            try:
                self.popout_board.set_board(self.board)
            except Exception:
                pass

    def toggle_flip(self):
        self.flipped = not self.flipped
        self.render_board()
        if self.popout_window and hasattr(self, 'popout_board'):
            try:
                self.popout_board.flipped = self.flipped
                self.popout_board.render_board()
            except Exception:
                pass

    def toggle_popout(self):
        """Spawns or closes the standalone popout window."""
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

        # --- LINK THE TWINS ---
        self.popout_board.master_widget = self  # Popout points back to Main
        # ---------------------

        self.popout_board.on_step_back = getattr(self, 'on_step_back', None)
        self.popout_board.on_step_forward = getattr(self, 'on_step_forward', None)
        self.popout_board.on_jump_start = getattr(self, 'on_jump_start', None)
        self.popout_board.on_jump_end = getattr(self, 'on_jump_end', None)

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
            # Clear reference so parent stops trying to sync a closed window
            if hasattr(self, 'popout_board'):
                del self.popout_board

        self.popout_window.protocol("WM_DELETE_WINDOW", on_close)

    def sync_with_twin(self):
        """Pushes current board state to the paired twin board (Main <-> Popout)."""
        # If this is the main board, update the popout child
        if hasattr(self, 'popout_board') and self.popout_board:
            if self.popout_board.board != self.board:
                self.popout_board.board = self.board.copy()
                self.popout_board.render_board()

        # If this is the popout board, update the main parent
        if hasattr(self, 'master_widget') and self.master_widget:
            if self.master_widget.board != self.board:
                self.master_widget.board = self.board.copy()
                self.master_widget.render_board()

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
        """Redraws all board squares, selection highlights, and pieces cleanly without altering model data during drags."""
        self.canvas.delete("all")
        from PIL import ImageTk

        if not hasattr(self, '_canvas_images'):
            self._canvas_images = []
        self._canvas_images.clear()

        for row in range(8):
            for col in range(8):
                x1 = col * self.square_size
                y1 = row * self.square_size
                x2 = x1 + self.square_size
                y2 = y1 + self.square_size

                square_color = "#9f7939" if (row + col) % 2 else "#fbcba4"

                chess_square = self._get_chess_square(row, col)
                if self.selected_square is not None and chess_square == self.selected_square:
                    square_color = "#d4af37"  # Gold highlight for selected piece

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=square_color, outline="")

                piece = self.board.piece_at(chess_square)

                # Only hide the piece visually on its start square while dragging
                if piece and not (self.is_dragging and chess_square == self.drag_start_square):
                    filename = PIECE_MAP.get(piece.symbol())
                    cache_key = (filename, self.square_size)
                    if cache_key not in self.image_cache:
                        if len(self.image_cache) > 64:
                            self.image_cache.clear()
                        pil_img = load_piece_image(filename, size=self.square_size)
                        if pil_img:
                            self.image_cache[cache_key] = pil_img

                    pil_img = self.image_cache.get(cache_key)
                    if pil_img:
                        img_tk = ImageTk.PhotoImage(pil_img)
                        self._canvas_images.append(img_tk)
                        cx = x1 + (self.square_size / 2)
                        cy = y1 + (self.square_size / 2)
                        self.canvas.create_image(cx, cy, image=img_tk, anchor="center")