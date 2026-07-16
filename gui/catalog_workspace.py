import customtkinter as ctk
from tkinter import ttk
import json
import os

import gui.app_state as state

def show_catalog_workspace():
    global add_catalog_button, import_button, catalog_button

    # Clear the workspace
    for widget in state.workspace.winfo_children():
        widget.destroy()

        print("A")

    # Title
    title = ctk.CTkLabel(
        state.workspace,
        text="Opening Catalog",
        font=("Arial", 24, "bold")
    )
    title.pack(anchor="w", padx=20, pady=(15, 10))

    print("B")

    # ----- Table Frame -----

    table_frame = ctk.CTkFrame(state.workspace)
    table_frame.pack(fill="both", anchor="w", expand=True, padx=(0, 0), pady=(0, 0))

    columns = (
        "Select",
        "Games",
        "ECO",
        "Opening",
        "Variation",
     )

    catalog_table = ttk.Treeview(
        table_frame,
        columns=columns,
        show="headings"
    )

    # Headings
    catalog_table.heading("Select", anchor="center", text=" ☐")
    catalog_table.heading("Games", anchor="center",  text="Games")
    catalog_table.heading("ECO", anchor="w",  text="ECO")
    catalog_table.heading("Opening", anchor="w",  text="Opening")
    catalog_table.heading("Variation", anchor="w",  text="Variation")


    # Column widths
    catalog_table.column("Select", width=45, anchor="center", stretch=False)
    catalog_table.column("Games", width=70, anchor="center", stretch=False)
    catalog_table.column("ECO", width=50, anchor="w", stretch=False)
    catalog_table.column("Opening", width=150, anchor ="w", stretch=False)
    catalog_table.column("Variation", width=200, anchor="w", stretch=True)


    # Scrollbar
    scrollbar = ttk.Scrollbar(
        table_frame,
        orient="vertical",
        command=catalog_table.yview
    )

    catalog_table.configure(yscrollcommand=scrollbar.set)

    catalog_table.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # -------------------------
    # Load catalog from JSON
    # -------------------------

    if not os.path.exists("personal_catalog.json"):
        return

    with open("personal_catalog.json", "r", encoding="utf-8") as f:
        catalog = json.load(f)

    rows = []
    total_games = 0

    for group in catalog:
        if group == "cataloged_files":
            continue

        for eco, entry in catalog[group].items():

            opening = entry.get("opening", "")
            variation = entry.get("variation", "")
            games = entry.get("frequency", 0)

            total_games += games

            rows.append((
                games,
                eco,
                opening,
                variation
            ))

    # Highest frequency first
    rows.sort(key=lambda row: row[0], reverse=True)

    # Insert into table
    for games, eco, opening, variation in rows:

        catalog_table.insert(
            "",
            "end",
            values=(
                "☐",
                games,
                eco,
                opening,
                variation
            )
        )

    # Total games in catalog
    catalog_table.heading(
        "Select",
        text=str(total_games)
    )
