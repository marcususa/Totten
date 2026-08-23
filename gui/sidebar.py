# gui/sidebar.py

import customtkinter as ctk
import chess
import chess.pgn
import io
from pathlib import Path
import gui.app_state as state
from gui.statusbar import set_status_message


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_navigate_callback):
        # Reduce sidebar width from 150 to ~105 to reclaim ~50-75px for the analysis view
        super().__init__(parent, width=105, corner_radius=0, fg_color="#172134")
        self.on_navigate = on_navigate_callback

        # --- STATUS DISPLAY (Anchored at the bottom) ---
        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(side="bottom", fill="x", padx=4, pady=(5, 10))

        self.lbl_status = ctk.CTkLabel(
            self.status_container,
            text="Ready",
            anchor="sw",
            justify="left",
            wraplength=95,  # Adjusted wraplength to match narrower width
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray60")
        )
        self.lbl_status.pack(side="bottom", fill="x", anchor="sw")

        # Save reference to app_state for global updates
        state.status = self.lbl_status

        # --- NAVIGATION TREE / BUTTONS (Packed from top) ---

        # 1. Catalog
        self.btn_catalog = ctk.CTkButton(
            self,
            text="Catalog",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("catalog")
        )
        self.btn_catalog.pack(fill="x", padx=4, pady=(15, 5))

        # 2. Analysis
        self.btn_analysis = ctk.CTkButton(
            self,
            text="Analysis",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("analysis")
        )
        self.btn_analysis.pack(fill="x", padx=4, pady=5)

        # 3. Patterns
        self.btn_patterns = ctk.CTkButton(
            self,
            text="Patterns",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("patterns")
        )
        self.btn_patterns.pack(fill="x", padx=4, pady=5)

        # 4. Mixed Collections
        self.btn_mixed = ctk.CTkButton(
            self,
            text="Mixed Collections",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("edit_workspace")
        )
        self.btn_mixed.pack(fill="x", padx=4, pady=5)

        # 5. Calendar
        self.btn_calendar = ctk.CTkButton(
            self,
            text="Calendar",
            anchor="w",
            fg_color="transparent",
            hover_color="#2e4a8c",
            text_color="white",
            command=lambda: self.on_navigate("calendar")
        )
        self.btn_calendar.pack(fill="x", padx=4, pady=(5, 10))

        # --- DIVIDER LINE ---
        self.divider = ctk.CTkFrame(self, height=2, fg_color="#334155")
        self.divider.pack(fill="x", padx=6, pady=(5, 10))

        # --- QUICK EVALUATION SECTION ---
        self.lbl_qeval = ctk.CTkLabel(
            self,
            text="Quick Evaluation",
            anchor="center",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray10", "gray90")
        )
        self.lbl_qeval.pack(fill="x", padx=4, pady=(0, 5))

        # Analyze Button moved ABOVE the text box
        self.btn_qeval_analysis = ctk.CTkButton(
            self,
            text="Analyze",
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color="#344268",
            hover_color="#2e4a8c",
            command=self.handle_qeval_send_analysis
        )
        self.btn_qeval_analysis.pack(fill="x", padx=4, pady=(0, 5))

        # Text box for Quick Evaluation moves
        self.txt_qeval_moves = ctk.CTkTextbox(
            self,
            height=130,
            fg_color="#1e293b",
            text_color="#f8fafc",
            font=ctk.CTkFont(size=10),
            wrap="word"
        )
        self.txt_qeval_moves.pack(fill="x", padx=4, pady=(0, 5))

        # Add to Catalog Button
        self.btn_qeval_catalog = ctk.CTkButton(
            self,
            text="Add to Catalog",
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color="#344268",
            hover_color="#2e4a8c",
            command=self.handle_qeval_add_catalog
        )
        self.btn_qeval_catalog.pack(fill="x", padx=4, pady=(2, 5))

    def parse_qeval_pgn(self):
        """Helper to parse sidebar quick eval text box."""
        raw_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if not raw_text:
            set_status_message("Error: Quick Evaluation box is empty.")
            return None
        try:
            pgn_io = io.StringIO(raw_text)
            game_node = chess.pgn.read_game(pgn_io)
            if not game_node:
                set_status_message("Error: Invalid PGN format in Quick Evaluation.")
                return None
            return game_node
        except Exception as e:
            set_status_message(f"Quick Evaluation Parse Error: {e}")
            return None

    def handle_qeval_send_analysis(self):
        """Sends quick evaluation moves directly to the analysis view."""
        game_node = self.parse_qeval_pgn()
        if not game_node:
            return

        state.set_active_analysis_game(game_node)

        self.on_navigate("analysis")
        set_status_message("Quick Evaluation sent to Analysis.")

    def handle_qeval_add_catalog(self):
        """Appends quick evaluation moves to personal_catalog.pgn."""
        game_node = self.parse_qeval_pgn()
        if not game_node:
            return

        try:
            catalog_path = Path("personal_catalog.pgn")
            exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True)
            game_string = game_node.accept(exporter)

            with open(catalog_path, "a", encoding="utf-8") as f:
                f.write("\n\n" + game_string + "\n")

            set_status_message("Quick Evaluation added to personal_catalog.pgn!")
        except Exception as e:
            set_status_message(f"Failed to add to catalog: {e}")


# --- TOP LEVEL FUNCTIONS ---

def create_sidebar(app, on_navigate_callback=None):
    """Factory function to initialize and return the Sidebar frame."""
    if on_navigate_callback is None:
        from gui.workspace import show_workspace
        on_navigate_callback = show_workspace

    sidebar = Sidebar(app, on_navigate_callback)
    state.left_frame = sidebar
    state.sidebar_visible = True

    # Lock column 0 to match the new narrower width (~105px instead of 150)
    if hasattr(app, "grid_columnconfigure"):
        app.grid_columnconfigure(0, minsize=105, weight=0)

    return sidebar


def toggle_sidebar():
    """Toggles the visibility of the sidebar frame and keeps column 0 locked at 105px."""
    sidebar = getattr(state, "left_frame", None)

    if sidebar is None:
        print("Notice: Sidebar frame reference (state.left_frame) not found.")
        return

    app = sidebar.master

    if getattr(state, "sidebar_visible", True):
        sidebar.grid_remove()
        if hasattr(app, "grid_columnconfigure"):
            app.grid_columnconfigure(0, minsize=0, weight=0)
        state.sidebar_visible = False
    else:
        if hasattr(app, "grid_columnconfigure"):
            app.grid_columnconfigure(0, minsize=105, weight=0)

        sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        state.sidebar_visible = True