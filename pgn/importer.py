import gui.app_state as state
from tkinter import filedialog
from pathlib import Path

from gui.import_workspace import show_import_workspace
from catalog.catalog_builder import catalog_pgns
from gui.catalog_workspace import show_catalog_workspace

def import_pgn():
    print("1 - import_pgn started")

    filename = filedialog.askopenfilename(
        title="Import PGN",
        filetypes=[("PGN Files", "*.pgn")]
    )

    print("2 - file dialog returned")

    if not filename:
        return

    print(f"3 - Selected: {filename}")

    state.current_filename = filename

    show_import_workspace(
        filename,
        catalog_pgns,
        import_pgn,
        show_catalog_workspace,
        state.imported_files,
        state.status
    )

    print("4 - show_import_workspace finished")

    # Don't allow the same file twice
    if filename in state.imported_files:
        state.status.configure(
            text=f"{Path(filename).name} is already imported."
        )
        return

    state.imported_files.append(filename)

    short_name = Path(filename).name
    state.pgn_lookup[short_name] = filename

    pgn_item = state.sidebar.insert(
        state.pgn_node,
        "end",
        text=short_name,
        open=False
    )

    state.sidebar.insert(
        state.pgn_node,
        "end",
        text="Back to Import"
    )

    state.pgn_item_lookup[filename] = pgn_item

    state.sidebar.insert(
        pgn_item,
        "end",
        text="Game Data"
    )

    state.status.configure(
        text=f"Imported: {short_name}"
    )

def import_fen():
    print("Import FEN selected")
