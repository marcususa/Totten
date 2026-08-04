# main.py
import os
from tkinter import ttk
import customtkinter as ctk
import gui.app_state as state

# Imports for GUI components
from gui.sidebar import create_sidebar
from gui.workspace import create_workspace, show_workspace
from gui.menus import create_menu

print("PYTHON WORKING DIRECTORY:", os.getcwd())
print("FILE EXISTS ON DISK:", os.path.exists("personal_catalog.pgn"))

# ----------------------------
# Main Window Setup
# ----------------------------
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.configure(fg_color="#172134")
app.title("Totten")

# Expanded size & minimum boundaries to fit sidebar + workspace + 200px buffer
app.geometry("1000x800")
app.minsize(1000, 800)

# ----------------------------
# TTK Global Styling Setup
# ----------------------------
style = ttk.Style()

available_themes = style.theme_names()
if "clam" in available_themes:
    style.theme_use("clam")
elif "alt" in available_themes:
    style.theme_use("alt")

BG_COLOR = "#172134"

# Set base colors to match the app background
style.configure(
    "Treeview",
    background=BG_COLOR,
    fieldbackground=BG_COLOR,
    foreground="white",
    rowheight=25,
    borderwidth=0,
    relief="flat",
    focuscolor=BG_COLOR  # Paint focus color same as background
)

# Paint ALL state borders & highlights as the background color
style.map(
    "Treeview",
    focuscolor=[("focus", BG_COLOR), ("active", BG_COLOR), ("selected", BG_COLOR)],
    bordercolor=[("focus", BG_COLOR), ("active", BG_COLOR), ("selected", BG_COLOR)],
    lightcolor=[("focus", BG_COLOR), ("active", BG_COLOR), ("selected", BG_COLOR)],
    darkcolor=[("focus", BG_COLOR), ("active", BG_COLOR), ("selected", BG_COLOR)]
)

# ----------------------------
# 1. Configure Grid Rows/Cols
# ----------------------------
app.grid_rowconfigure(0, weight=1)
app.grid_columnconfigure(0, minsize=150)
app.grid_columnconfigure(1, weight=1)

# ----------------------------
# 2. Initialize Components
# ----------------------------
create_sidebar(app, on_navigate_callback=show_workspace)
create_workspace(app)
create_menu(app)

app.update()

# ----------------------------
# 3. Final Grid Placement
# ----------------------------
state.left_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
state.workspace.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

# ----------------------------
# Start App
# ----------------------------
app.mainloop()