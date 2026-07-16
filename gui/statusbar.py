import customtkinter as ctk
import gui.app_state as state


def create_statusbar(app):

    state.status = ctk.CTkLabel(
        app,
        text="Import PGN files ",
        anchor="e",
        height=26
    )

    state.status.grid(
        row=2,
        column=1,
        sticky="ew",
        padx=10
    )