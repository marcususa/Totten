# gui/mixed_analysis.py

from pathlib import Path
import json
import chess.pgn
from tkinter import ttk
import customtkinter as ctk
import chess

import gui.app_state as state
from gui.statusbar import set_status_message
from gui.chess_board import ChessBoardWidget
from core.constants import CONFIG_FILE

BASE_PGN_DIR = Path(__file__).resolve().parent.parent / "pgn"


def get_category_path(category_name):
    if not category_name:
        return "custom", "custom_collections.pgn"

    slug = (
        category_name.lower()
        .replace("'", "")
        .replace(" / ", "_")
        .replace(" ", "_")
    )
    return slug, f"{slug}.pgn"


class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        if self.tooltip_window or not self.text:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        self.tooltip_window = tw = ctk.CTkToplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ctk.CTkLabel(
            tw,
            text=self.text,
            fg_color="#1e293b",
            text_color="#f8fafc",
            corner_radius=4,
            font=("Arial", 11)
        )
        label.pack(padx=6, pady=4)

    def hide_tooltip(self, event=None):
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


def get_saved_pgn_filename():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("current_pgn_filename")
        except Exception:
            pass
    return None


class MixedAnalysis(ctk.CTkFrame):
    def __init__(self, parent, filename=None, *args, **kwargs):
        super().__init__(parent, fg_color="#172134", corner_radius=0, *args, **kwargs)
        self.filename = filename or (BASE_PGN_DIR / "mixed_analysis.pgn")
        self.game_list = []
        self.current_game = None
        self.board_node = None
        self.preview_lookup = {}
        self.game_lookup = {}

        self.active_game = None
        self.root_game_node = None
        self.current_node = None
        self.active_engine_mode = "standard"

        self.popout_window = None
        self.popout_board = None
        self.popout_container = None
        self.is_board_popped_out = False

        self.col_tree = None
        self.pgn_tree = None

        self.init_layout()
        self._apply_tree_styles()
        self._bind_analysis_events()

        if hasattr(state, "active_category_source") and state.active_category_source:
            if isinstance(state.active_category_source, list):
                self.load_mixed_collection(state.active_category_source)
            else:
                self.load_games(filename=state.active_category_source)
        else:
            self.load_games()

    def pop_out_board(self, *args, **kwargs):
        if hasattr(self, "popout_board_window"):
            return self.popout_board_window(*args, **kwargs)
        elif hasattr(self, "popout_board") and callable(getattr(self, "popout_board", None)) and not isinstance(
                self.popout_board, ctk.CTkFrame):
            # If it's a method
            pass

        if self.is_board_popped_out:
            if self.popout_window:
                self.popout_window.focus()
            return

        self.is_board_popped_out = True

        self.board_widget.pack_forget()
        self.placeholder_lbl.pack(padx=10, pady=25)

        if hasattr(self, "btn_popout"):
            self.btn_popout.configure(text="Dock Board ↙", fg_color="#475569", hover_color="#64748b")

        self.popout_window = ctk.CTkToplevel(self)
        self.popout_window.title("Chess Board Analysis - Pop-out")
        self.popout_window.geometry("400x440")
        self.popout_window.configure(fg_color="#172134")

        self.popout_window.attributes("-topmost", True)
        self.popout_window.protocol("WM_DELETE_WINDOW", self.restore_popped_board)

        popout_container = ctk.CTkFrame(self.popout_window, fg_color="transparent")
        popout_container.pack(fill="both", expand=True, padx=20, pady=20)

        self.popout_board = ChessBoardWidget(popout_container, square_size=55)
        self.popout_board.pack(anchor="center", pady=(10, 10))

        fen_to_set = self.board_node.board().fen() if self.board_node else (
            self.current_game.board().fen() if self.current_game else chess.STARTING_FEN)
        self.popout_board.set_position_fen(fen_to_set)

    def restore_popped_board(self):
        self.is_board_popped_out = False

        if self.popout_window:
            try:
                self.popout_window.destroy()
            except Exception:
                pass
            self.popout_window = None
            self.popout_board = None

        if hasattr(self, "btn_popout"):
            self.btn_popout.configure(text="Pop Out ↗", fg_color="#334155", hover_color="#475569")

        if hasattr(self, "placeholder_lbl"):
            self.placeholder_lbl.pack_forget()
        if hasattr(self, "board_widget") and hasattr(self, "board_holder"):
            self.board_widget.pack(in_=self.board_holder)

        fen_to_set = self.board_node.board().fen() if self.board_node else (
            self.current_game.board().fen() if self.current_game else chess.STARTING_FEN)
        self.board_widget.set_position_fen(fen_to_set)

    def load_game(self, game_node, category_source=None):
        if hasattr(self, "load_game_hardwired"):
            return self.load_game_hardwired(game_node, category_source=category_source)
        return self.load_game_from_state(game_node, category_source=category_source)

    def _apply_tree_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.layout("Borderless.Treeview", [('Treeview.treearea', {'sticky': 'nswe'})])

        style.configure(
            "Borderless.Treeview",
            background="#172134",
            foreground="#f8fafc",
            fieldbackground="#172134",
            rowheight=22,
            font=("Arial", 10),
            borderwidth=0,
            relief="flat",
            highlightthickness=0
        )
        style.map(
            "Borderless.Treeview",
            background=[("selected", "#2e4a8c"), ("focus", "#172134"), ("active", "#172134")],
            foreground=[("selected", "#ffffff"), ("focus", "#f8fafc"), ("active", "#f8fafc")],
            borderwidth=[("focus", 0), ("active", 0)]
        )
        style.configure(
            "Borderless.Treeview.Heading",
            background="#0f172a",
            foreground="#f8fafc",
            font=("Arial", 10, "bold"),
            relief="flat",
            borderwidth=0
        )
        style.map(
            "Borderless.Treeview.Heading",
            background=[('active', '#0f172a'), ('selected', '#0f172a')],
            foreground=[('active', '#f8fafc'), ('selected', '#f8fafc')]
        )

        target = getattr(self, "col_tree", None) or getattr(self, "pgn_tree", None)
        if target:
            try:
                target.configure(style="Borderless.Treeview", takefocus=False)
            except Exception:
                pass

    def _bind_analysis_events(self):
        target = getattr(self, "col_tree", None) or getattr(self, "pgn_tree", None)
        if target:
            target.bind("<<TreeviewSelect>>", self._on_tree_select, add="+")

    def _on_tree_select(self, event):
        target = event.widget
        selected_items = target.selection()
        if not selected_items:
            return

        item_id = selected_items[0]
        self._handle_item_selection(item_id)

    def _handle_item_selection(self, item_id):
        if not item_id:
            return False

        lookup_dict = getattr(self, "game_lookup", None) or getattr(self, "preview_lookup", None)
        if lookup_dict and item_id in lookup_dict:
            game_data = lookup_dict[item_id]
            if isinstance(game_data, tuple):
                game, source_data = game_data
            else:
                game = game_data
                source_data = getattr(self, "filename", None)

            state.active_analysis_game = game
            state.active_category_source = source_data
            # Pass False so load_game_from_state doesn't re-select the item in the tree
            self.load_game_from_state(game, category_source=source_data, update_tree_selection=False)
            return True

        return False

    def load_mixed_collection(self, games_list, category=None, target_game=None):
        target_dir = BASE_PGN_DIR
        file_name = "mixed_analysis.pgn"

        if category:
            subfolder, file_name = get_category_path(category)
            target_dir = BASE_PGN_DIR / subfolder

        target_dir.mkdir(parents=True, exist_ok=True)
        target_file_path = target_dir / file_name

        extracted_games = []
        for item in games_list:
            if isinstance(item, dict):
                g_obj = item.get("game_object") or item.get("game")
                if g_obj:
                    extracted_games.append(g_obj)
            elif isinstance(item, chess.pgn.Game):
                extracted_games.append(item)

        if not target_game and extracted_games:
            target_game = extracted_games[0]
        elif isinstance(target_game, dict):
            target_game = target_game.get("game_object") or target_game.get("game", target_game)

        try:
            with open(target_file_path, "w", encoding="utf-8") as f:
                exporter = chess.pgn.FileExporter(f)
                for g in extracted_games:
                    g.accept(exporter)
                    f.write("\n")
        except Exception as e:
            set_status_message(f"Error saving collection to PGN path: {e}")
            return

        self.filename = target_file_path
        self.load_games(filename=target_file_path)

        if target_game:
            self.load_game_from_state(target_game, category_source=target_file_path)

    def load_games(self, filename=None):
        if filename:
            self.filename = filename

        active_load_file = self.filename if self.filename else (BASE_PGN_DIR / "mixed_analysis.pgn")

        target = getattr(self, "col_tree", None) or getattr(self, "pgn_tree", None)
        if target:
            try:
                target.configure(style="Borderless.Treeview", takefocus=False)
            except Exception:
                pass
            target.delete(*target.get_children())

        self.preview_lookup.clear()
        self.game_lookup.clear()
        game_list = []

        if Path(active_load_file).exists():
            try:
                with open(active_load_file, "r", encoding="utf-8") as f:
                    while True:
                        game = chess.pgn.read_game(f)
                        if game is None:
                            break
                        game_list.append(game)
            except Exception as e:
                set_status_message(f"Error loading PGN file: {e}")

        self.game_list = game_list

        if target:
            for idx, game in enumerate(game_list, start=1):
                headers = game.headers
                white = headers.get("White", "Unknown")
                black = headers.get("Black", "Unknown")
                result = headers.get("Result", "*")

                item_id = target.insert("", "end", values=(idx, white, black, result))
                self.preview_lookup[item_id] = game
                self.game_lookup[item_id] = game

        if not game_list and hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
            self.lbl_empty_state.configure(text="No games loaded in analysis view.")
            self.lbl_empty_state.pack(padx=20, pady=20)
        elif hasattr(self, "lbl_empty_state") and self.lbl_empty_state:
            self.lbl_empty_state.pack_forget()

    def load_game_on_board(self, game_obj):
        self.load_game_from_state(game_obj)

    def load_game_from_state(self, game_obj, category_file=None, category_source=None, update_tree_selection=True):
        if not game_obj:
            return

        self.current_game = game_obj
        self.board_node = game_obj
        self.active_game = game_obj
        self.root_game_node = game_obj
        self.current_node = game_obj

        if hasattr(self, "board_widget") and self.board_widget:
            try:
                fen_str = game_obj.board().fen()
                self.board_widget.set_position_fen(fen_str)
            except Exception:
                pass

        if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
            try:
                fen_str = game_obj.board().fen()
                self.popout_board.set_position_fen(fen_str)
            except Exception:
                pass

        headers = game_obj.headers
        white = headers.get("White", "Unknown")
        black = headers.get("Black", "Unknown")
        result = headers.get("Result", "*")

        if hasattr(self, "pgn_data_text") and self.pgn_data_text:
            try:
                exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=None)
                pgn_text_export = game_obj.accept(exporter)

                self.pgn_data_text.configure(state="normal")
                self.pgn_data_text.delete("1.0", "end")
                self.pgn_data_text.insert("end", pgn_text_export)
                self.pgn_data_text.configure(state="disabled")
            except Exception:
                pass

        if hasattr(self, "moves_textbox") and self.moves_textbox:
            try:
                self.moves_textbox.configure(state="normal")
                self.moves_textbox.delete("1.0", "end")
                self.moves_textbox.insert("1.0", str(game_obj.mainline()))
                self.moves_textbox.configure(state="disabled")
            except Exception:
                pass

        if hasattr(self, "_load_plain_game_moves"):
            try:
                self._load_plain_game_moves(game_obj)
            except Exception:
                pass

        # Only update selection programmatically if called externally (not from clicking a row)
        if update_tree_selection:
            target = getattr(self, "col_tree", None) or getattr(self, "pgn_tree", None)
            lookup_dict = getattr(self, "game_lookup", None) or getattr(self, "preview_lookup", None)
            if target and lookup_dict:
                for item_id, g in lookup_dict.items():
                    if g == game_obj:
                        target.selection_set(item_id)
                        target.see(item_id)
                        break

    def on_prev_move(self):
        if hasattr(self, "board_node") and self.board_node and self.board_node.parent:
            self.board_node = self.board_node.parent
            fen = self.board_node.board().fen()
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(fen)
            if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
                self.popout_board.set_position_fen(fen)

    def on_next_move(self):
        if hasattr(self, "board_node") and self.board_node and self.board_node.variations:
            self.board_node = self.board_node.variation(0)
            fen = self.board_node.board().fen()
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(fen)
            if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
                self.popout_board.set_position_fen(fen)

    def on_first_move(self):
        if hasattr(self, "current_game") and self.current_game:
            self.board_node = self.current_game
            fen = self.current_game.board().fen()
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(fen)
            if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
                self.popout_board.set_position_fen(fen)

    def on_last_move(self):
        if hasattr(self, "current_game") and self.current_game:
            node = self.current_game
            while node.variations:
                node = node.variation(0)
            self.board_node = node
            fen = node.board().fen()
            if hasattr(self, "board_widget") and self.board_widget:
                self.board_widget.set_position_fen(fen)
            if getattr(self, "is_board_popped_out", False) and hasattr(self, "popout_board") and self.popout_board:
                self.popout_board.set_position_fen(fen)

    def trigger_engine_mode(self, mode):
        self.active_engine_mode = mode
        if hasattr(self, "btn_review") and hasattr(self, "btn_candidates") and hasattr(self, "btn_standard"):
            for b in (self.btn_review, self.btn_candidates, self.btn_standard):
                b.configure(fg_color="#1e293b", hover_color="#334155")
            if mode == "review":
                self.btn_review.configure(fg_color="#2e4a8c", hover_color="#4870cd")
            elif mode == "candidates":
                self.btn_candidates.configure(fg_color="#2e4a8c", hover_color="#4870cd")
            elif mode == "standard":
                self.btn_standard.configure(fg_color="#2e4a8c", hover_color="#4870cd")

    def init_layout(self):
        if hasattr(state, "register_analysis_callback"):
            state.register_analysis_callback(self.load_game)

        self.preview_lookup = {}
        self.game_lookup = {}
        self.active_game = None
        self.active_engine_mode = "standard"

        self.popout_window = None
        self.popout_board = None
        self.popout_container = None
        self.is_board_popped_out = False

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.main_container.grid_columnconfigure(0, weight=3)
        self.main_container.grid_columnconfigure(1, weight=2)
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_pane_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.left_pane_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10), pady=0)

        self.left_board_panel = ctk.CTkFrame(
            self.left_pane_container,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.left_board_panel.pack(side="top", fill="both", expand=False, padx=0, pady=(0, 5))

        self.board_holder = ctk.CTkFrame(self.left_board_panel, fg_color="transparent")
        self.board_holder.pack(side="top", padx=10, pady=(10, 2))

        self.board_widget = ChessBoardWidget(self.board_holder, square_size=50)
        self.board_widget.pack()

        self.placeholder_lbl = ctk.CTkLabel(
            self.board_holder, text="[ Board Popped Out ]", text_color="#94a3b8"
        )

        self.board_controls = ctk.CTkFrame(self.left_board_panel, fg_color="transparent")
        self.board_controls.pack(side="top", fill="x", padx=10, pady=(2, 10))

        self.row_controls_layout = ctk.CTkFrame(self.board_controls, fg_color="transparent")
        self.row_controls_layout.pack(anchor="center")

        self.btn_prev = ctk.CTkButton(
            self.row_controls_layout,
            text="◀ Prev",
            width=80,
            height=26,
            fg_color="#2e4a8c",
            hover_color="#4870cd",
            command=self.on_prev_move
        )
        self.btn_prev.pack(side="left", padx=(0, 4))

        self.btn_popout = ctk.CTkButton(
            self.row_controls_layout,
            text="Pop Out ↗",
            width=85,
            height=26,
            fg_color="#334155",
            hover_color="#475569",
            command=self.pop_out_board
        )
        self.btn_popout.pack(side="left", padx=4)

        self.btn_next = ctk.CTkButton(
            self.row_controls_layout,
            text="Next ▶",
            width=80,
            height=26,
            fg_color="#2e4a8c",
            hover_color="#4870cd",
            command=self.on_next_move
        )
        self.btn_next.pack(side="left", padx=(4, 0))

        self.top_catalog_panel = ctk.CTkFrame(
            self.left_pane_container,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.top_catalog_panel.pack(side="top", fill="both", expand=True, padx=0, pady=0)

        self.lbl_empty_state = ctk.CTkLabel(
            self.top_catalog_panel,
            text="No games loaded in memory.",
            font=ctk.CTkFont(size=11),
            text_color="gray70",
            wraplength=250
        )

        self.tree_frame = ctk.CTkFrame(self.top_catalog_panel, fg_color="transparent")
        self.tree_frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.col_tree = ttk.Treeview(
            self.tree_frame,
            columns=("no", "white", "black", "result"),
            show="headings",
            selectmode="browse",
            height=6,
            takefocus=False,
            style="Borderless.Treeview"
        )
        self.col_tree.heading("no", text="No.")
        self.col_tree.heading("white", text="White Player", anchor="w")
        self.col_tree.heading("black", text="Black Player", anchor="w")
        self.col_tree.heading("result", text="Res")

        self.col_tree.column("no", width=30, anchor="center")
        self.col_tree.column("white", width=145, anchor="w")
        self.col_tree.column("black", width=145, anchor="w")
        self.col_tree.column("result", width=45, anchor="center")

        self.pgn_tree = self.col_tree

        self.pgn_scrollbar = ttk.Scrollbar(
            self.tree_frame,
            orient="vertical",
            command=self.col_tree.yview
        )
        self.col_tree.configure(yscrollcommand=self.pgn_scrollbar.set)
        self.col_tree.pack(side="left", fill="both", expand=True, padx=0, pady=0)
        self.pgn_scrollbar.pack(side="right", fill="y", padx=0, pady=0)

        self.right_analysis_panel = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.right_analysis_panel.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)

        self.right_analysis_panel.rowconfigure(0, weight=1)
        self.right_analysis_panel.rowconfigure(1, weight=1)
        self.right_analysis_panel.rowconfigure(2, weight=0)
        self.right_analysis_panel.columnconfigure(0, weight=1)

        self.analysis_container_frame = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.analysis_container_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_analysis_title = ctk.CTkLabel(
            self.analysis_container_frame, text="Analysis", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_analysis_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.analysis_inner_wrapper = ctk.CTkFrame(self.analysis_container_frame, fg_color="transparent")
        self.analysis_inner_wrapper.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.review_container = ctk.CTkFrame(self.analysis_inner_wrapper, fg_color="transparent")

        self.moves_textbox = ctk.CTkTextbox(
            self.review_container,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=110
        )
        self.moves_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0, wrap="word")

        self.moves_textbox.tag_config("red", foreground="#FF4444")
        self.moves_textbox.tag_config("orange", foreground="#FFA500")
        self.moves_textbox.tag_config("green", foreground="#00C851")
        self.moves_textbox.tag_config("light_blue", foreground="#33b5e5")
        self.moves_textbox.tag_config("default", foreground="#f8fafc")
        self.moves_textbox.tag_config("active_move", background="#660000", foreground="#ffffff")

        self.moves_textbox.pack(fill="both", expand=True, padx=0, pady=0)
        self.review_container.pack(fill="both", expand=True)

        self.candidates_container = ctk.CTkFrame(self.analysis_inner_wrapper, fg_color="transparent")

        self.candidates_textbox = ctk.CTkTextbox(
            self.candidates_container,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            height=80,
            wrap="none"
        )
        self.candidates_textbox._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0)

        self.candidates_textbox.tag_config("red", foreground="#FF4444")
        self.candidates_textbox.tag_config("orange", foreground="#FFA500")
        self.candidates_textbox.tag_config("green", foreground="#00C851")
        self.candidates_textbox.tag_config("light_blue", foreground="#33b5e5")
        self.candidates_textbox.tag_config("default", foreground="#f8fafc")
        self.candidates_textbox.pack(side="left", fill="both", expand=True, padx=0, pady=0)

        self.pgn_data_panel = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.pgn_data_panel.grid(row=1, column=0, sticky="nsew", padx=0, pady=(0, 8))

        self.lbl_pgn_data_title = ctk.CTkLabel(
            self.pgn_data_panel, text="Game Details", font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#94a3b8"
        )
        self.lbl_pgn_data_title.pack(anchor="w", padx=10, pady=(6, 2))

        self.pgn_data_text = ctk.CTkTextbox(
            self.pgn_data_panel,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Arial", size=11),
            wrap="word",
            height=80
        )
        self.pgn_data_text._textbox.configure(font=("Arial", 11), highlightthickness=0, takefocus=0)
        self.pgn_data_text.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.pgn_data_text.insert("end", "[No game selected. Click a game to load its PGN moves...]\n")

        self.controls_panel = ctk.CTkFrame(
            self.right_analysis_panel,
            fg_color="#0f172a",
            corner_radius=8,
            border_width=1,
            border_color="#334155"
        )
        self.controls_panel.grid(row=2, column=0, sticky="nsew", padx=0, pady=0)

        self.analysis_mode_content = ctk.CTkFrame(self.controls_panel, fg_color="transparent")
        self.analysis_mode_content.pack(fill="x", expand=True, padx=10, pady=10)

        self.row_analysis_layout = ctk.CTkFrame(self.analysis_mode_content, fg_color="transparent")
        self.row_analysis_layout.pack(anchor="center")

        self.lbl_engine_title = ctk.CTkLabel(
            self.row_analysis_layout, text="Engine", font=ctk.CTkFont(size=11), text_color="#94a3b8"
        )
        self.lbl_engine_title.pack(side="left", padx=(0, 8))

        self.row_analysis_btns = ctk.CTkFrame(self.row_analysis_layout, fg_color="transparent")
        self.row_analysis_btns.pack(side="left")

        self.btn_review = ctk.CTkButton(
            self.row_analysis_btns,
            text="1",
            width=24,
            height=24,
            fg_color="#2e4a8c",
            hover_color="#4870cd",
            command=lambda: self.trigger_engine_mode("review")
        )
        self.btn_review.pack(side="left", padx=2)
        ToolTip(self.btn_review, "Game Review")

        self.btn_candidates = ctk.CTkButton(
            self.row_analysis_btns,
            text="2",
            width=24,
            height=24,
            fg_color="#1e293b",
            hover_color="#334155",
            command=lambda: self.trigger_engine_mode("candidates")
        )
        self.btn_candidates.pack(side="left", padx=2)
        ToolTip(self.btn_candidates, "Candidate Moves")

        self.btn_standard = ctk.CTkButton(
            self.row_analysis_btns,
            text="3",
            width=24,
            height=24,
            fg_color="#1e293b",
            hover_color="#334155",
            command=lambda: self.trigger_engine_mode("standard")
        )
        self.btn_standard.pack(side="left", padx=2)
        ToolTip(self.btn_standard, "Standard")


def create_mixed_workspace(master, filename=None):
    instance = MixedAnalysis(master, filename=filename)
    instance.grid(row=0, column=0, sticky="nsew")
    state.workspace = instance
    state.analysis_workspace = instance
    return instance