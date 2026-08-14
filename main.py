# main.py
import os
from tkinter import ttk
import customtkinter as ctk
import gui.app_state as state
from gui.splash import StandaloneSplash

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
app.withdraw()  # Hide main window temporarily to prevent raw layout flashing
app.configure(fg_color="#172134")
app.title("Totten")

# Expanded size & minimum boundaries to fit sidebar + workspace + 200px buffer
app.geometry("1000x800")
app.minsize(1000, 800)

# Pop up the loading splash screen
splash = StandaloneSplash(title_text="Totten", message="Starting up...")

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

# Global fallback styles so any workspace using standard Treeview headings matches cleanly
style.configure(
    "Heading",
    background="#344268",
    foreground="#f8fafc",
    font=("Arial", 10, "bold"),
    relief="flat",
    borderwidth=0,
)
style.map(
    "Heading",
    background=[('active', '#344268'), ('selected', '#344268')],
    foreground=[('active', '#f8fafc'), ('selected', '#f8fafc')]
)

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
# Startup Complete - Reveal App
# ----------------------------
def reveal_main_app():
    splash.close()
    app.deiconify()  # Bring the fully rendered main window forward

# Small delay to ensure everything settles before displaying
app.after(600, reveal_main_app)

# ----------------------------
# Start App
# ----------------------------
app.mainloop()