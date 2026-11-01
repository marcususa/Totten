import io
import tkinter as tk
from pathlib import Path
from PIL import Image, ImageTk, ImageDraw
import customtkinter as ctk
import chess
from core.constants import THEME
import gui.app_state as state

PIECE_PATH = "assets/pieces/"

ROOT_DIR = Path(__file__).resolve().parent
while ROOT_DIR != ROOT_DIR.parent:
    if (ROOT_DIR / "main.py").exists() or (ROOT_DIR / "core").exists():
        break
    ROOT_DIR = ROOT_DIR.parent


def load_piece_image(filename, size=64):
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
    def __init__(self, parent, square_size=64, is_popout=False, **kwargs):
        super().__init__(parent, fg_color=THEME.get("bg_panel", "#0f172a"), corner_radius=0, **kwargs)
        self.square_size = square_size
        self.is_popout = is_popout
        self.board = chess.Board()
        self.flipped = False
        self.popout_window = None
        self.is_analyzing = False  # Analysis toggle state for pop-out window

        # Interaction state tracking for dragging and clicking
        self.dragging_piece = None
        self.drag_start_square = None
        self.drag_image_ref = None
        self.drag_image_item = None
        self.selected_square = None

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
        """Builds control panel layout tailored specifically for main vs pop-out views."""
        for widget in self.winfo_children():
            widget.destroy()

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        panel_width = 45 if self.is_popout else 72
        board_pixel_size = self.square_size * 8

        self.control_panel = ctk.CTkFrame(self, fg_color="transparent", width=panel_width, corner_radius=0)
        self.control_panel.grid(row=0, column=0, sticky="ns", padx=0, pady=0)
        self.control_panel.grid_propagate(False)

        # Inner button container centered vertically
        self.buttons_container = ctk.CTkFrame(self.control_panel, fg_color="transparent", corner_radius=0)
        self.buttons_container.place(relx=0.5, rely=0.5, anchor="center")

        is_light = ctk.get_appearance_mode().lower() == "light"
        btn_fg = "#cbd5e1" if is_light else ("transparent" if self.is_popout else THEME.get("bg_surface"))
        btn_hover = "#94a3b8" if is_light else THEME.get("btn_hover", "#475569")
        text_color = "#0f172a" if is_light else (THEME.get("text_secondary", "#94a3b8"))

        if self.is_popout:
            # Pop-out layout: Compact buttons with symbols and analysis toggle 'A'
            button_width = panel_width - 4
            button_height = 35

            self.flip_button = ctk.CTkButton(
                self.buttons_container, text="↻",
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 14),
                command=self.toggle_flip
            )
            self.flip_button.pack(side="top", pady=(0, 4), anchor="center")

            self.popout_button = ctk.CTkButton(
                self.buttons_container, text=chr(9704),
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 14),
                command=self.toggle_popout
            )
            self.popout_button.pack(side="top", pady=(0, 4), anchor="center")

            self.analysis_button = ctk.CTkButton(
                self.buttons_container, text="A",
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 14, "bold"),
                command=self.toggle_analysis
            )
            self.analysis_button.pack(side="top", pady=(0, 4), anchor="center")

            self.prev_button = ctk.CTkButton(
                self.buttons_container, text="◀",
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 12),
                command=self._on_left_arrow
            )
            self.prev_button.pack(side="top", pady=(0, 4), anchor="center")

            self.next_button = ctk.CTkButton(
                self.buttons_container, text="▶",
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 12),
                command=self._on_right_arrow
            )
            self.next_button.pack(side="top", anchor="center")

        else:
            # Main app layout: Full descriptive buttons
            button_width = panel_width - 8
            button_height = 32

            self.flip_button = ctk.CTkButton(
                self.buttons_container, text="↻ Flip",
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 14, "bold"),
                command=self.toggle_flip
            )
            self.flip_button.pack(side="top", pady=(0, 6), anchor="center")

            self.popout_button = ctk.CTkButton(
                self.buttons_container, text="Pop Out",
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 13, "bold"),
                command=self.toggle_popout
            )
            self.popout_button.pack(side="top", pady=(0, 6), anchor="center")

            self.prev_button = ctk.CTkButton(
                self.buttons_container, text="◀ Prev",
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 13, "bold"),
                command=self._on_left_arrow
            )
            self.prev_button.pack(side="top", pady=(0, 6), anchor="center")

            self.next_button = ctk.CTkButton(
                self.buttons_container, text="Next ▶",
                width=button_width, height=button_height, fg_color=btn_fg,
                hover_color=btn_hover, text_color=text_color, font=("Arial", 13, "bold"),
                command=self._on_right_arrow
            )
            self.next_button.pack(side="top", anchor="center")

        self.canvas = ctk.CTkCanvas(
            self,
            width=board_pixel_size,
            height=board_pixel_size,
            bg=THEME.get("bg_panel", "#0f172a"),
            highlightthickness=0
        )
        self.canvas.grid(row=0, column=1, sticky="nsew", padx=(2, 0), pady=0)

        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def toggle_analysis(self):
        """Toggles analysis mode for independent pop-out variation testing."""
        self.is_analyzing = not self.is_analyzing
        is_light = ctk.get_appearance_mode().lower() == "light"
        if self.is_analyzing:
            active_bg = THEME.get("btn_hover", "#2563eb")
            self.analysis_button.configure(fg_color=active_bg, text_color="#ffffff")
        else:
            btn_fg = "#cbd5e1" if is_light else "transparent"
            text_color = "#0f172a" if is_light else THEME.get("text_secondary", "#94a3b8")
            self.analysis_button.configure(fg_color=btn_fg, text_color=text_color)

    def _get_chess_square(self, row, col):
        if self.flipped:
            chess_rank = row
            chess_file = 7 - col
        else:
            chess_rank = 7 - row
            chess_file = col
        return chess.square(chess_file, chess_rank)

    def _get_row_col_from_chess_square(self, chess_square):
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
        col = int(x // self.square_size)
        row = int(y // self.square_size)
        if 0 <= row < 8 and 0 <= col < 8:
            return row, col
        return None, None

    def _on_press(self, event):
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
        if not self.press_piece:
            return

        if not self.is_dragging:
            dx = abs(event.x - self.press_x)
            dy = abs(event.y - self.press_y)
            if dx > 3 or dy > 3:
                self.is_dragging = True
                self.dragging_piece = self.press_piece
                self.drag_start_square = self.press_square

        if not self.dragging_piece:
            return

        self.render_board()

        filename = PIECE_MAP.get(self.dragging_piece.symbol())
        pil_img = self.image_cache.get((filename, self.square_size))
        if not pil_img:
            pil_img = load_piece_image(filename, size=self.square_size)
            if pil_img:
                self.image_cache[(filename, self.square_size)] = pil_img

        if pil_img:
            self.drag_image_ref = ImageTk.PhotoImage(pil_img)
            self.drag_image_item = self.canvas.create_image(
                event.x, event.y, image=self.drag_image_ref, anchor="center"
            )

        if self.is_dragging and self.drag_image_item:
            self.canvas.coords(self.drag_image_item, event.x, event.y)

    def _on_release(self, event):
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
                        self.sync_with_twin()

            self.dragging_piece = None
            self.drag_start_square = None
            self.is_dragging = False
            self.selected_square = None
            self.render_board()
            return

        if row is None or col is None:
            self.selected_square = None
            self.render_board()
            return

        clicked_square = self._get_chess_square(row, col)

        if self.selected_square is None:
            piece = self.board.piece_at(clicked_square)
            if piece:
                self.selected_square = clicked_square
                self.render_board()
        else:
            target_square = clicked_square

            if self.selected_square == target_square:
                self.selected_square = None
                self.render_board()
                return

            promotion = None
            selected_piece = self.board.piece_at(self.selected_square)
            if selected_piece and selected_piece.piece_type == chess.PAWN and chess.square_rank(target_square) in (0, 7):
                promotion = chess.QUEEN

            move = chess.Move(self.selected_square, target_square, promotion=promotion)

            if move in self.board.legal_moves:
                self.board.push(move)
                self.sync_with_twin()

            self.selected_square = None
            self.render_board()

    def _on_canvas_resize(self, event):
        new_size = min(event.width, event.height) // 8
        if new_size > 10 and new_size != self.square_size:
            self.resize_board(new_size)

    def resize_board(self, new_square_size):
        if new_square_size == self.square_size or new_square_size < 15:
            return
        self.square_size = new_square_size
        self.image_cache.clear()
        board_pixel_size = new_square_size * 8
        self.canvas.configure(width=board_pixel_size, height=board_pixel_size)
        if hasattr(self, 'control_panel') and self.control_panel:
            self.control_panel.configure(height=board_pixel_size)
        self.render_board()

    def set_position(self, position):
        if isinstance(position, str):
            self.set_position_fen(position)
        elif isinstance(position, chess.Board):
            self.set_board(position)
        else:
            try:
                self.set_position_fen(str(position))
            except Exception as e:
                print(f"Error in set_position: {e}")

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

    def _on_left_arrow(self):
        targets = [
            getattr(self, 'master_widget', None),
            self.master,
            getattr(state, 'workspace', None)
        ]
        for target in targets:
            if target is not None:
                for method_name in ('on_prev_move', 'prev_move', 'step_backward', 'previous_move', 'go_back', 'prev'):
                    if hasattr(target, method_name):
                        getattr(target, method_name)()
                        return

    def _on_right_arrow(self):
        targets = [
            getattr(self, 'master_widget', None),
            self.master,
            getattr(state, 'workspace', None)
        ]
        for target in targets:
            if target is not None:
                for method_name in ('on_next_move', 'next_move', 'step_forward', 'next', 'forward'):
                    if hasattr(target, method_name):
                        getattr(target, method_name)()
                        return

    def sync_with_twin(self):
        if self.is_popout and self.is_analyzing:
            return

        if self.is_popout and hasattr(self, 'master_widget') and self.master_widget:
            if hasattr(self.master_widget, 'board'):
                self.master_widget.board = self.board.copy()
                self.master_widget.render_board()
        elif not self.is_popout and self.popout_window and hasattr(self, 'popout_board'):
            if self.popout_board and not getattr(self.popout_board, 'is_analyzing', False):
                self.popout_board.board = self.board.copy()
                self.popout_board.render_board()

    def render_board(self):
        self.canvas.delete("all")
        self._canvas_images = []

        bg_surface = THEME.get("bg_surface", "#1e293b")
        light_color = THEME.get("light_square", "#f0d9b5")
        dark_color = THEME.get("dark_square", "#b58863")
        default_highlight = THEME.get("border_color", "#ea580c")
        highlight_color = THEME.get("btn_hover", default_highlight)
        border_color = THEME.get("border_color", bg_surface)

        board_pixel_size = self.square_size * 8

        # Check if board_background image exists in project root
        bg_img_file = None
        for ext in [".png", ".jpg", ".jpeg", ".bmp", ".gif"]:
            candidate = ROOT_DIR / f"board_background{ext}"
            if candidate.exists():
                bg_img_file = candidate
                break

        base_pil_img = None
        if bg_img_file:
            try:
                img = Image.open(bg_img_file).convert("RGBA")
                base_pil_img = img.resize((board_pixel_size, board_pixel_size), Image.Resampling.LANCZOS)
            except Exception as e:
                print(f"Error loading board background image: {e}")

        if base_pil_img:
            overlay = Image.new("RGBA", base_pil_img.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)

            def hex_to_rgba(hex_str, alpha=140):
                hex_str = hex_str.lstrip('#')
                if len(hex_str) == 6:
                    r = int(hex_str[0:2], 16)
                    g = int(hex_str[2:4], 16)
                    b = int(hex_str[4:6], 16)
                    return (r, g, b, alpha)
                return (181, 136, 99, alpha)

            for row in range(8):
                for col in range(8):
                    x1 = col * self.square_size
                    y1 = row * self.square_size
                    x2 = x1 + self.square_size
                    y2 = y1 + self.square_size

                    chess_square = self._get_chess_square(row, col)

                    if (row + col) % 2 == 1:
                        sq_color = hex_to_rgba(dark_color, alpha=200)
                    else:
                        sq_color = hex_to_rgba(light_color, alpha=140)

                    if self.selected_square == chess_square:
                        sq_color = hex_to_rgba(highlight_color, alpha=180)

                    draw.rectangle([x1, y1, x2 - 1, y2 - 1], fill=sq_color)

            composite_img = Image.alpha_composite(base_pil_img, overlay)
            bg_tk_img = ImageTk.PhotoImage(composite_img)
            self._canvas_images.append(bg_tk_img)
            self.canvas.create_image(0, 0, image=bg_tk_img, anchor="nw")
        else:
            for row in range(8):
                for col in range(8):
                    x1 = col * self.square_size
                    y1 = row * self.square_size
                    x2 = x1 + self.square_size
                    y2 = y1 + self.square_size

                    chess_square = self._get_chess_square(row, col)

                    if (row + col) % 2 == 1:
                        square_color = dark_color
                    else:
                        square_color = light_color

                    if self.selected_square == chess_square:
                        square_color = highlight_color

                    self.canvas.create_rectangle(
                        x1, y1, x2, y2,
                        fill=square_color,
                        outline=""
                    )

        # Render pieces
        for row in range(8):
            for col in range(8):
                x1 = col * self.square_size
                y1 = row * self.square_size
                chess_square = self._get_chess_square(row, col)

                piece = self.board.piece_at(chess_square)
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

        self.canvas.create_rectangle(
            0, 0, board_pixel_size, board_pixel_size,
            outline=border_color,
            width=2
        )

    def toggle_popout(self):
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
        self.popout_window.title("Chessboard Analysis (Pop-Out)")
        self.popout_window.configure(fg_color=THEME.get("bg_panel", "#0f172a"))

        win_w = (self.square_size * 8) + 45
        win_h = (self.square_size * 8) + 15

        self.popout_window.update_idletasks()
        screen_w = self.popout_window.winfo_screenwidth()
        screen_h = self.popout_window.winfo_screenheight()
        pos_x = (screen_w // 2) - (win_w // 2)
        pos_y = (screen_h // 2) - (win_h // 2)

        self.popout_window.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")
        self.popout_window.minsize(200, 200)
        self.popout_window.attributes("-topmost", True)

        self.popout_window.grid_rowconfigure(0, weight=1)
        self.popout_window.grid_columnconfigure(0, weight=1)

        self.popout_board = ChessBoardWidget(self.popout_window, square_size=self.square_size, is_popout=True)
        self.popout_board.master_widget = self
        self.popout_board.grid(row=0, column=0, sticky="nsew", padx=0, pady=(5, 0))
        self.popout_board.set_board(self.board)

        def on_window_resize(event):
            if event.widget == self.popout_window:
                new_size = min(event.width - 45, event.height - 15) // 8
                if new_size > 15 and new_size != self.popout_board.square_size:
                    self.popout_board.resize_board(new_size)

        self.popout_window.bind("<Configure>", on_window_resize)

        def on_close():
            if self.popout_window:
                self.popout_window.destroy()
            self.popout_window = None

        self.popout_window.protocol("WM_DELETE_WINDOW", on_close)