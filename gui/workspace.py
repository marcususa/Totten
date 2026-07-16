import customtkinter as ctk
import gui.app_state as state

def create_workspace(app):

    state.workspace = ctk.CTkFrame(
        app, fg_color="#172134" #main_workspace_background
    )

    state.workspace.grid(
        row=1,
        column=1,
        sticky="nsew",
        padx=0,
        pady=0
    )

    label = ctk.CTkLabel(
        state.workspace,
        text="Workspace",
        font=("Arial", 24)
    )

    label.pack(
        expand=True
    )
