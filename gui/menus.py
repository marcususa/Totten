import tkinter as tk
import customtkinter as ctk
import gui.app_state as state
from pgn.importer import import_pgn, import_fen, reset_importer_state
from catalog.catalog_manager import clear_catalog
from gui.sidebar import toggle_sidebar
from .splash import LoadingOverlay


def get_workspace_parent():
    """Safely resolves the correct master container for workspace frames."""
    if hasattr(state, "workspace") and state.workspace and getattr(state.workspace, "master", None):
        return state.workspace.master
    if hasattr(state, "left_frame") and state.left_frame and getattr(state.left_frame, "master", None):
        return state.left_frame.master
    return getattr(state, "app_root", None)


def handle_clear_catalog():
    """
    1. Clears backend catalog JSON/DB state.
    2. Resets in-memory import lists & sidebar tracking.
    3. Archives/rotates active 'personal_catalog.pgn' and resets active PGN views.
    4. Clears treeview UI state to show 0 games.
    """
    clear_catalog()
    reset_importer_state()


def handle_import_pgn():
    """Ingests PGN directly into catalog with immediate overlay feedback, then jumps to Search Catalog."""
    root_window = getattr(state, "app_root", None)

    overlay = None
    if root_window:
        try:
            overlay = LoadingOverlay(root_window, title_text="Totten", message="Opening file dialog...")
            root_window.update_idletasks()
        except Exception:
            pass

    try:
        import_pgn()
    finally:
        if overlay:
            try:
                overlay.close()
            except Exception:
                pass

    show_catalog()


def handle_import_fen():
    """Ingests FEN directly, then jumps straight to Search Catalog."""
    import_fen()
    show_catalog()


def show_catalog():
    """Refreshes and brings the Search Catalog view to focus."""
    parent = get_workspace_parent()
    if parent:
        if not hasattr(state, "catalog_workspace") or not state.catalog_workspace:
            from gui.search_catalog_workspace import SearchCatalogWorkspace
            state.catalog_workspace = SearchCatalogWorkspace(parent, filename="personal_catalog.pgn")
            state.catalog_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        state.catalog_workspace.tkraise()
        state.workspace = state.catalog_workspace


def show_edit_workspace():
    """Switches to the Edit view for playlists, FEN overrides, and tag curation."""
    parent = get_workspace_parent()
    if parent:
        if not hasattr(state, "edit_workspace") or not state.edit_workspace:
            from gui.edit_workspace import EditWorkspace
            state.edit_workspace = EditWorkspace(parent)
            state.edit_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        state.edit_workspace.tkraise()
        state.workspace = state.edit_workspace


def show_analysis():
    """Switches to the Analysis view."""
    parent = get_workspace_parent()
    if parent:
        if not hasattr(state, "analysis_workspace") or not state.analysis_workspace:
            from gui.analysis_workspace import AnalysisWorkspace
            state.analysis_workspace = AnalysisWorkspace(parent)
            state.analysis_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        state.analysis_workspace.tkraise()
        state.workspace = state.analysis_workspace


def show_patterns():
    """Switches to the Patterns view."""
    parent = get_workspace_parent()
    if parent:
        if not hasattr(state, "patterns_workspace") or not state.patterns_workspace:
            from gui.patterns_workspace import PatternsWorkspace
            state.patterns_workspace = PatternsWorkspace(parent)
            state.patterns_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        state.patterns_workspace.tkraise()
        state.workspace = state.patterns_workspace


def show_calendar():
    """Switches to the Calendar view."""
    parent = get_workspace_parent()
    if parent:
        if not hasattr(state, "calendar_workspace") or not state.calendar_workspace:
            from gui.calendar_workspace import CalendarWorkspace
            state.calendar_workspace = CalendarWorkspace(parent)
            state.calendar_workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        state.calendar_workspace.tkraise()
        state.workspace = state.calendar_workspace


def show_about_dialog():
    """Displays application About information styled like the splash screen with click-to-copy email."""
    top = ctk.CTkToplevel()
    top.geometry("340x260")
    top.resizable(False, False)
    top.overrideredirect(True)
    top.configure(fg_color="#172134")

    top.update_idletasks()
    x = (top.winfo_screenwidth() - top.winfo_reqwidth()) // 2
    y = (top.winfo_screenheight() - top.winfo_reqheight()) // 2
    top.geometry(f"+{x}+{y}")

    card = ctk.CTkFrame(top, fg_color="#1e293b", corner_radius=10)
    card.pack(fill="both", expand=True, padx=10, pady=10)

    ctk.CTkLabel(
        card, text="Totten",
        font=("Arial", 48, "bold"), text_color="white"
    ).pack(pady=(20, 5))

    ctk.CTkLabel(
        card, text="Chess Catalog with Analysis",
        font=("Arial", 12), text_color="#94a3b8"
    ).pack(pady=(0, 10))

    email_text = "progrockfrog@yahoo.com"

    def copy_email(event=None):
        top.clipboard_clear()
        top.clipboard_append(email_text)
        email_lbl.configure(text="Copied to clipboard")
        top.after(1500, lambda: email_lbl.configure(text=email_text))

    email_lbl = ctk.CTkLabel(
        card, text=email_text,
        font=("Arial", 11, "underline"), text_color="#38bdf8",
        cursor="hand2"
    )
    email_lbl.pack(pady=(0, 10))
    email_lbl.bind("<Button-1>", copy_email)

    ctk.CTkButton(
        card, text="Close", width=100, fg_color="#334155", hover_color="#475569",
        command=top.destroy
    ).pack(pady=(0, 15))


def create_menu(app):
    """Creates and configures the application's menu bar."""
    menubar = tk.Menu(app)
    app.config(menu=menubar)

    # 1. File Menu
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Import PGN...", command=handle_import_pgn)
    file_menu.add_command(label="Import FEN...", command=handle_import_fen)
    file_menu.add_separator()
    file_menu.add_command(label="Clear Catalog", command=handle_clear_catalog)
    file_menu.add_separator()
    file_menu.add_command(label="Exit", command=app.quit)
    menubar.add_cascade(label="File", menu=file_menu)

    # 2. Edit Menu
    edit_menu = tk.Menu(menubar, tearoff=0)
    edit_menu.add_command(label="PGN & Engine", command=show_edit_workspace)
    menubar.add_cascade(label="Edit", menu=edit_menu)

    # 3. View Menu
    view_menu = tk.Menu(menubar, tearoff=0)
    view_menu.add_command(label="Catalog", command=show_catalog)
    view_menu.add_command(label="Mixed Collections", command=show_edit_workspace)
    view_menu.add_command(label="Calendar", command=show_calendar)
    view_menu.add_separator()
    view_menu.add_command(label="Show / Hide Sidebar", command=toggle_sidebar)
    menubar.add_cascade(label="View", menu=view_menu)

    # 4. Tools Menu
    tools_menu = tk.Menu(menubar, tearoff=0)
    tools_menu.add_command(label="Analysis", command=show_analysis)
    tools_menu.add_command(label="Patterns", command=show_patterns)
    tools_menu.add_command(label="Engines", command=show_edit_workspace)
    menubar.add_cascade(label="Tools", menu=tools_menu)

    # 5. Help Menu
    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(label="About", command=show_about_dialog)
    menubar.add_cascade(label="Help", menu=help_menu)

    return menubar