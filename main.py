import customtkinter as ctk
from gui.sidebar import create_sidebar
from gui.analysis_workspace import create_workspace
from gui.menus import create_menu
import gui.app_state as state


class Totten(ctk.CTk):
    """
    Main application window for Totten, initializing the core root container,
    top-level application menus, sidebar switchboard, and default startup analysis view.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Totten")
        self.geometry("1200x800")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        state.app_master = self

        self._init_ui()

    def _init_ui(self):
        # Initialize the top-level window menu bar from menus.py
        self.menu_bar = create_menu(self)

        # The sidebar acts as the central switchboard for navigation
        self.sidebar = create_sidebar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        # Initialize the default startup workspace (Analysis)
        self.workspace = create_workspace(self)
        self.workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        state.workspace = self.workspace


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = Totten()
    app.mainloop()