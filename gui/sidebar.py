# gui/sidebar.py

import customtkinter as ctk
import gui.app_state as state


class Sidebar(ctk.CTkFrame):
    def __init__(self, parent, on_navigate_callback):
        super().__init__(parent, width=150, corner_radius=0, fg_color="#172134")
        self.on_navigate = on_navigate_callback

        # Prevent inner widgets from forcing the frame past 150px width
        self.pack_propagate(False)

        # --- STATUS DISPLAY (Anchored at the bottom) ---
        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(side="bottom", fill="x", padx=10, pady=(5, 10))

        self.lbl_status = ctk.CTkLabel(
            self.status_container,
            text="Ready",
            anchor="sw",
            justify="left",
            wraplength=130,  # Wrapped to fit comfortably inside 150px
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
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=lambda: self.on_navigate("catalog")
        )
        self.btn_catalog.pack(fill="x", padx=5, pady=(15, 5))

        # 2. Analysis
        self.btn_analysis = ctk.CTkButton(
            self,
            text="Analysis",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=lambda: self.on_navigate("analysis")
        )
        self.btn_analysis.pack(fill="x", padx=5, pady=5)

        # 3. Patterns
        self.btn_patterns = ctk.CTkButton(
            self,
            text="Patterns",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=lambda: self.on_navigate("patterns")
        )
        self.btn_patterns.pack(fill="x", padx=5, pady=5)

        # 4. Mixed Collections
        self.btn_mixed = ctk.CTkButton(
            self,
            text="Mixed Collections",
            anchor="w",
            fg_color="transparent",
            text_color=("gray30", "gray70"),
            hover_color=("gray70", "gray30"),
            command=lambda: self.on_navigate("mixed_collections")
        )
        self.btn_mixed.pack(fill="x", padx=5, pady=5)

        # 5. Calendar
        self.btn_calendar = ctk.CTkButton(
            self,
            text="Calendar",
            anchor="w",
            fg_color="transparent",
            text_color=("gray10", "gray90"),
            hover_color=("gray70", "gray30"),
            command=lambda: self.on_navigate("calendar")
        )
        self.btn_calendar.pack(fill="x", padx=5, pady=5)


# --- TOP LEVEL FUNCTIONS ---

def create_sidebar(app, on_navigate_callback=None):
    """Factory function to initialize and return the Sidebar frame."""
    if on_navigate_callback is None:
        from gui.workspace import show_workspace
        on_navigate_callback = show_workspace

    sidebar = Sidebar(app, on_navigate_callback)
    state.left_frame = sidebar
    state.sidebar_visible = True

    if hasattr(app, "grid_columnconfigure"):
        app.grid_columnconfigure(0, minsize=150, weight=0)

    return sidebar


def toggle_sidebar():
    """Toggles the visibility of the sidebar frame and keeps column 0 locked at 150px."""
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
        # Lock frame size and column to 150px
        sidebar.configure(width=150)
        sidebar.pack_propagate(False)

        if hasattr(app, "grid_columnconfigure"):
            app.grid_columnconfigure(0, minsize=150, weight=0)

        sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        state.sidebar_visible = True