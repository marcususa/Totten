import sys
import os
from pathlib import Path
import tkinter as tk
import customtkinter as ctk
import gui.app_state as state
from pgn.importer import import_pgn, import_fen, reset_importer_state
from gui.sidebar import toggle_sidebar

# Import your core constants for centralized theming
try:
    from core.constants import THEME
except ImportError:
    THEME = {}

ROOT_DIR = Path(__file__).resolve().parent.parent

try:
    from catalog.catalog_manager import clear_catalog
except ImportError:
    try:
        from gui.catalog.catalog_manager import clear_catalog
    except ImportError:
        def clear_catalog():
            """Direct fallback implementation to guarantee catalog clearing if module import fails."""
            print("[MENU] Executing direct root catalog cleanup fallback...")

            targets = [
                ROOT_DIR / "personal_catalog.duckdb",
                ROOT_DIR / "personal_catalog.json",
                ROOT_DIR / "personal_catalog.pgn"
            ]

            try:
                import duckdb
                duckdb.sql("CLOSE DATABASE").fetchall()
            except Exception:
                try:
                    duckdb.default_connection.close()
                except Exception:
                    pass

            for file_path in targets:
                if file_path.exists():
                    try:
                        os.remove(file_path)
                        print(f"[CLEANUP] Successfully deleted: {file_path}")
                    except Exception as e:
                        print(f"[CLEANUP] Error deleting {file_path}: {e}")
                        if "pgn" in str(file_path):
                            try:
                                with open(file_path, "w", encoding="utf-8") as f:
                                    f.write("")
                            except Exception:
                                pass


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
    """Ingests PGN directly into catalog, then jumps to Search Catalog."""
    import_pgn()
    state.show_workspace("search_catalog")


def handle_import_fen():
    """Ingests FEN directly, then jumps straight to Search Catalog."""
    import_fen()
    state.show_workspace("search_catalog")


def show_about_dialog():
    """Displays application About information styled like the splash screen with credits, quotes, and references."""
    top = ctk.CTkToplevel()
    width, height = 440, 420
    top.resizable(False, False)
    top.overrideredirect(True)
    top.configure(fg_color=THEME.get("bg_panel", "#172134"))

    top.update_idletasks()
    x = (top.winfo_screenwidth() - width) // 2
    y = (top.winfo_screenheight() - height) // 2
    top.geometry(f"{width}x{height}+{x}+{y}")

    border_ring = ctk.CTkFrame(
        top,
        fg_color=THEME.get("border_ring", "#344268"),
        corner_radius=11
    )
    border_ring.pack(fill="both", expand=True, padx=0, pady=0)

    card = ctk.CTkFrame(
        border_ring,
        fg_color=THEME.get("bg_surface", "#1e293b"),
        corner_radius=10
    )
    card.pack(fill="both", expand=True, padx=1, pady=1)

    ctk.CTkLabel(
        card, text="Totten",
        font=("Arial", 32, "bold"), text_color=THEME.get("text_primary", "white")
    ).pack(pady=(12, 2))

    ctk.CTkLabel(
        card, text="Chess Catalog with Analysis",
        font=("Arial", 11, "bold"), text_color=THEME.get("text_secondary", "#94a3b8")
    ).pack(pady=(0, 5))

    email_text = "progrockfrog@yahoo.com"

    def copy_email(event=None):
        top.clipboard_clear()
        top.clipboard_append(email_text)
        email_lbl.configure(text="Copied to clipboard")
        top.after(1500, lambda: email_lbl.configure(text=email_text))

    email_lbl = ctk.CTkLabel(
        card, text=email_text,
        font=("Arial", 10, "bold", "underline"), text_color=THEME.get("eval_light_blue", "#38bdf8"),
        cursor="hand2"
    )
    email_lbl.pack(pady=(0, 5))
    email_lbl.bind("<Button-1>", copy_email)

    scroll_frame = ctk.CTkScrollableFrame(
        card, width=400, height=140,
        fg_color=THEME.get("bg_surface", "#1e293b")
    )
    scroll_frame.pack(pady=2, padx=10, fill="x", expand=False)

    credits_text = (
        "ECO - https://www.cs.kent.ac.uk/people/staff/djb/pgn-extract/\n"
        "Engine - Stockfish\n"
        "Tarrasch - https://www.triplehappy.com/\n"
        "SCID vs. PC - https://scidvspc.sourceforge.net/\n"
        "Arena 3.5.1 - http://www.playwitharena.de/\n"
        "Dan Heisman - https://www.danheisman.com/\n"
    )

    ctk.CTkLabel(
        scroll_frame, text=credits_text,
        font=("Arial", 10, "bold"), text_color=THEME.get("text_primary", "#cbd5e1"),
        justify="left", wraplength=370
    ).pack(anchor="w", padx=5, pady=5)

    ctk.CTkButton(
        card, text="Close", width=100,
        fg_color=THEME.get("btn_initial", "#334155"),
        hover_color=THEME.get("btn_hover", "#475569"),
        command=top.destroy
    ).pack(pady=(10, 15))


def create_menu(app):
    """Creates and configures the application's menu bar using default native menu styling."""
    menubar = tk.Menu(app, tearoff=0)
    app.config(menu=menubar)

    # 1. File Menu
    file_menu = tk.Menu(menubar, tearoff=0)
    file_menu.add_command(label="Import PGN...", command=handle_import_pgn)
    file_menu.add_command(label="Import FEN...", command=handle_import_fen)
    file_menu.add_command(label="Clear Catalog", command=handle_clear_catalog)
    file_menu.add_command(label="Exit", command=app.quit)
    menubar.add_cascade(label="File", menu=file_menu)

    # 2. Edit Menu
    edit_menu = tk.Menu(menubar, tearoff=0)
    edit_menu.add_command(label="PGN & Engine", command=lambda: state.show_workspace("mixed"))
    menubar.add_cascade(label="Edit", menu=edit_menu)

    # 3. View Menu
    view_menu = tk.Menu(menubar, tearoff=0)
    view_menu.add_command(label="Catalog", command=lambda: state.show_workspace("search_catalog"))
    view_menu.add_command(label="Mixed Collections", command=lambda: state.show_workspace("mixed"))
    view_menu.add_command(label="Calendar", command=lambda: state.show_workspace("calendar"))
    view_menu.add_command(label="Show / Hide Sidebar", command=toggle_sidebar)
    menubar.add_cascade(label="View", menu=view_menu)

    # 4. Tools Menu
    tools_menu = tk.Menu(menubar, tearoff=0)
    tools_menu.add_command(label="Analysis", command=lambda: state.show_workspace("analysis"))
    tools_menu.add_command(label="Patterns", command=lambda: state.show_workspace("patterns"))
    tools_menu.add_command(label="Engines", command=lambda: state.show_workspace("mixed"))
    menubar.add_cascade(label="Tools", menu=tools_menu)

    # 5. Help Menu
    help_menu = tk.Menu(menubar, tearoff=0)
    help_menu.add_command(label="About", command=show_about_dialog)
    menubar.add_cascade(label="Help", menu=help_menu)

    return menubar