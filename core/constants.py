import os
import json
import threading
from pathlib import Path
from tkinter import ttk
import chess.pgn
import customtkinter as ctk

CONFIG_FILE = Path(__file__).resolve().parent.parent / "app_config.json"
CATALOG_PGN_FILE = Path(__file__).resolve().parent.parent / "personal_catalog.pgn"

def get_saved_pgn_filename():
    return "personal_catalog.pgn"