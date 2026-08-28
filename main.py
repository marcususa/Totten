import customtkinter as ctk
from gui.sidebar import create_sidebar
from gui.catalog_analysis import create_workspace, show_workspace
from gui.menus import create_menu
import gui.app_state as state


class Totten(ctk.CTk):
    """
    Main application window for Totten, initializing the core root container,
    top-level application menus, sidebar switchboard, and default startup catalog analysis view.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Totten")
        self.geometry("1200x800")
        self.configure(fg_color="#172134")

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        state.app_root = self
        state.app_master = self

        self._init_ui()

    def _init_ui(self):
        # Initialize the top-level window menu bar from menus.py
        self.menu_bar = create_menu(self)

        # The sidebar acts as the central switchboard for navigation
        self.sidebar = create_sidebar(self)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        state.left_frame = self.sidebar

        # Initialize the default startup workspace (CatalogAnalysis) via the new factory function
        self.workspace = create_workspace(self)
        self.workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        state.workspace = self.workspace
        state.analysis_workspace = self.workspace

    def show_workspace(self, target):
        """Switchboard method to route workspace views dynamically from inside active frames."""
        if target == "analysis" or target == "mixed":
            if not hasattr(state, "mixed_workspace") or not state.mixed_workspace:
                from gui.mixed_analysis import MixedAnalysis
                state.mixed_workspace = MixedAnalysis(self)
                state.mixed_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

            # Raise mixed_workspace to the top and update states
            state.mixed_workspace.tkraise()
            state.workspace = state.mixed_workspace
            state.analysis_workspace = state.mixed_workspace

            # Load games based on what's in state
            if hasattr(state, "active_category_source") and state.active_category_source:
                if isinstance(state.active_category_source, list):
                    if hasattr(state.mixed_workspace, "load_mixed_collection"):
                        state.mixed_workspace.load_mixed_collection(state.active_category_source)
                else:
                    if hasattr(state.mixed_workspace, "load_games"):
                        state.mixed_workspace.load_games(filename=state.active_category_source)
            else:
                # Default fallback load if no state is explicitly set yet
                if hasattr(state.mixed_workspace, "load_games"):
                    state.mixed_workspace.load_games()


if __name__ == "__main__":
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("blue")
    app = Totten()
    app.mainloop()