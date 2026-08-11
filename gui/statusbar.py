import customtkinter as ctk
import gui.app_state as state

def create_statusbar(app):
    state.status = ctk.CTkLabel(
        app,
        text="Ready",
        anchor="w",
        height=26,
        padx=10,
        text_color="#94a3b8"
    )

def set_status_message(text: str):
    """Utility helper to update state.status text from any workspace."""
    if hasattr(state, "status") and state.status:
        state.status.configure(text=text)