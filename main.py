import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import chess
import chess.pgn
import json
import os

from gui.workspace import create_workspace
from gui.sidebar import create_sidebar
import gui.app_state as state
from gui.menus import create_menu
from gui.statusbar import create_statusbar


# ----------------------------
# Main Window
# ----------------------------

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")
app = ctk.CTk()

state.app = app

app.configure(fg_color="#172134")

app.title("Chess Catalog")
app.geometry("800x700") #change default width later to be longer

# ----------------------------
# Configure Grid
# ----------------------------

app.grid_rowconfigure(1, weight=1)
app.grid_columnconfigure(1, weight=1)

# ----------------------------
# PGN Collection
# ----------------------------

# create_menu(app)
# create_sidebar(app)
# create_workspace(app)
# create_statusbar(app)

create_sidebar(app)
create_workspace(app)
create_menu(app)
create_statusbar(app)

app.mainloop()