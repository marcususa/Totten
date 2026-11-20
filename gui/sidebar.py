import io
import json
import os
import urllib.request
import chess
import chess.pgn
import customtkinter as ctk
import gui.app_state as state
import gui.calendar_workspace
from core.constants import THEME


def _theme_color(key, fallback_key="text_primary"):
    """Looks up a color strictly from THEME without hardcoded hex fallbacks."""
    if key in THEME:
        return THEME[key]
    return THEME[fallback_key]


def _get_dynamic_progress_fill():
    """Computes a high-contrast progress fill color dynamically from background luminance."""
    bg = _theme_color("bg_panel", "bg_surface").lstrip("#")
    try:
        r, g, b = int(bg[0:2], 16), int(bg[2:4], 16), int(bg[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0

        if luminance > 0.5:
            factor = 0.25
            nr, ng, nb = int(r * factor), int(g * factor), int(b * factor)
        else:
            factor = 0.85
            nr = int(r + (255 - r) * factor)
            ng = int(g + (255 - g) * factor)
            nb = int(b + (255 - b) * factor)

        return f"#{max(0, min(255, nr)):02x}{max(0, min(255, ng)):02x}{max(0, min(255, nb)):02x}"
    except Exception:
        return _theme_color("text_primary")


def _get_dynamic_text_color(hex_str):
    """Computes high-contrast text color based on button background luminance and THEME."""
    clean_hex = (hex_str or "").lstrip("#")
    try:
        r, g, b = int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        if luminance > 0.5:
            return _theme_color("bg_surface", "bg_panel")
        return _theme_color("text_primary")
    except Exception:
        return _theme_color("text_primary")


class Sidebar(ctk.CTkFrame):
    CONFIG_FILE = "chess_accounts.json"

    def __init__(self, parent):
        super().__init__(parent, width=205, corner_radius=0, fg_color=_theme_color("bg_panel", "bg_surface"))
        super().pack_propagate(False)

        # Load saved accounts and engine preference
        self.saved_accounts = self._load_saved_accounts()
        self.cc_saved_username = self.saved_accounts.get("chess_com", None)
        self.lich_saved_username = self.saved_accounts.get("lichess", None)

        # Track active platform ("chess_com" or "lichess")
        self.active_platform = "chess_com"

        # Filter states
        self.filters = {"Blitz": False, "Rapid": False, "Standard": False, "All": True}

        btn_initial = _theme_color("btn_initial", "bg_surface")
        btn_hover = _theme_color("btn_hover", "btn_initial")
        text_primary = _theme_color("text_primary")
        text_secondary = _theme_color("text_secondary", "text_primary")

        # --- STATUS DISPLAY ---
        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(side="bottom", fill="x", padx=4, pady=(2, 6))

        self.lbl_status = ctk.CTkLabel(
            self.status_container,
            text="Ready",
            anchor="sw",
            justify="left",
            wraplength=190,
            font=ctk.CTkFont(size=10),
            text_color=_theme_color("status_text", "text_secondary"),
        )
        self.lbl_status.pack(side="bottom", fill="x", anchor="sw")

        state.status = self.lbl_status

        # --- PROGRESS CONTAINER & BAR ---
        self.progress_container = ctk.CTkFrame(self, height=16, fg_color="transparent")
        state.progress_container = self.progress_container

        self.progress_bar = ctk.CTkProgressBar(
            self.progress_container,
            height=8,
            corner_radius=2,
            fg_color=_theme_color("progress_bg", "bg_surface"),
            progress_color=_get_dynamic_progress_fill(),
            mode="determinate",
        )
        self.progress_bar.pack(fill="x", expand=True, pady=4)
        self.progress_bar.set(0.0)

        state.progress_bar = self.progress_bar

        # Keep the progress bar hidden by default on startup
        self.progress_container.pack_forget()

        # --- NAVIGATION BUTTONS ---
        nav_items = [
            ("btn_catalog", "Catalog", "search_catalog", (15, 4)),
            ("btn_analysis", "Analysis", "analysis", 4),
            ("btn_patterns", "Patterns", "patterns", 4),
            ("btn_mixed", "Mixed Collections", "mixed", 4),
            ("btn_calendar", "Calendar", "calendar", 4),
        ]
        for attr_name, label_text, workspace_key, pady_val in nav_items:
            btn = ctk.CTkButton(
                self,
                text=label_text,
                anchor="w",
                fg_color="transparent",
                hover_color=btn_hover,
                text_color=text_primary,
                font=ctk.CTkFont(size=11),
                command=lambda wk=workspace_key: state.show_workspace(wk),
            )
            btn.pack(fill="x", padx=4, pady=pady_val)
            setattr(self, attr_name, btn)

        # Start with the analysis workspace on startup
        state.show_workspace("analysis")

        # --- QUICK EVALUATION SECTION ---
        self.placeholder_text = "Paste PGN for quick analysis. You can also search online users below."

        self.txt_qeval_moves = ctk.CTkTextbox(
            self,
            height=75,
            fg_color=_theme_color("bg_surface", "bg_panel"),
            text_color=text_primary,
            font=ctk.CTkFont(size=9),
            border_color=_theme_color("border_color", "btn_initial"),
            border_width=1,
            wrap="word",
        )
        self.txt_qeval_moves.pack(fill="x", padx=4, pady=(10, 4))

        self.txt_qeval_moves.insert("1.0", self.placeholder_text)
        self.txt_qeval_moves.configure(text_color=text_secondary)

        self.txt_qeval_moves.bind("<FocusIn>", self._on_qeval_focus_in)
        self.txt_qeval_moves.bind("<FocusOut>", self._on_qeval_focus_out)
        self.txt_qeval_moves.bind("<Button-3>", self._on_qeval_right_click)
        self.txt_qeval_moves.bind("<Button-2>", self._on_qeval_right_click)

        self.btn_qeval_analysis = ctk.CTkButton(
            self,
            text="Analyze",
            height=24,
            font=ctk.CTkFont(size=10),
            fg_color=btn_initial,
            hover_color=btn_hover,
            text_color=_get_dynamic_text_color(btn_initial),
            command=self.handle_qeval_send_analysis,
        )
        self.btn_qeval_analysis.pack(fill="x", padx=4, pady=(0, 4))

        # --- ONLINE ACCOUNT QUICK CONTROLS (Strictly Vertical Stack) ---
        self.account_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.account_panel.pack(fill="x", padx=4, pady=(12, 6))

        # Chess.com Button
        cc_text = self.cc_saved_username if self.cc_saved_username else "Chess.com"
        self.btn_cc_user = ctk.CTkButton(
            self.account_panel,
            text=cc_text,
            height=22,
            anchor="center",
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=btn_initial,
            hover_color=btn_hover,
            text_color=_get_dynamic_text_color(btn_initial),
            command=lambda: self._trigger_platform_action("chess_com", action="last"),
        )
        self.btn_cc_user.pack(fill="x", pady=(0, 4))

        # Lichess.org Button
        lich_text = self.lich_saved_username if self.lich_saved_username else "Lichess.org"
        self.btn_lich_user = ctk.CTkButton(
            self.account_panel,
            text=lich_text,
            height=22,
            anchor="center",
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=btn_initial,
            hover_color=btn_hover,
            text_color=_get_dynamic_text_color(btn_initial),
            command=lambda: self._trigger_platform_action("lichess", action="last"),
        )
        self.btn_lich_user.pack(fill="x", pady=(0, 6))

        # Vertical List for Time Control Checkboxes
        self.sidebar_box_labels = {}
        for mode in ("Blitz", "Rapid", "Standard", "All"):
            var = ctk.BooleanVar(value=self.filters.get(mode, False))
            chk = ctk.CTkCheckBox(
                self.account_panel,
                text=mode,
                variable=var,
                font=ctk.CTkFont(size=10, weight="bold"),
                checkbox_width=12,
                checkbox_height=12,
                border_width=1,
                corner_radius=2,
                fg_color=btn_initial,
                hover_color=btn_hover,
                border_color=_theme_color("border_color", "btn_initial"),
                checkmark_color=_theme_color("active_tracker_fg", "text_primary"),
                text_color=text_secondary,
                command=lambda m=mode: self._toggle_sidebar_filter(m),
            )
            chk.pack(anchor="w", padx=2, pady=1)
            self.sidebar_box_labels[mode] = chk

        # Batch Download Button ("100")
        ctk.CTkButton(
            self.account_panel,
            text="100",
            height=22,
            anchor="center",
            font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=btn_initial,
            hover_color=btn_hover,
            text_color=_get_dynamic_text_color(btn_initial),
            command=lambda: self._trigger_platform_action(self.active_platform, action="batch"),
        ).pack(fill="x", pady=(4, 0))

    def _load_saved_accounts(self):
        """Loads saved usernames and settings from the local JSON config file."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as e:
                print(f"[DEBUG] Error loading accounts config: {e}")
        return {"chess_com": None, "lichess": None}

    def _set_active_platform(self, platform):
        """Highlights the active platform button using THEME colors."""
        self.active_platform = platform
        btn_initial = _theme_color("btn_initial", "bg_surface")
        bg_surface = _theme_color("bg_surface", "bg_panel")
        text_primary = _theme_color("text_primary")

        if platform == "chess_com":
            self.btn_cc_user.configure(
                fg_color=btn_initial,
                text_color=_get_dynamic_text_color(btn_initial),
            )
            self.btn_lich_user.configure(fg_color=bg_surface, text_color=text_primary)
        else:
            self.btn_lich_user.configure(
                fg_color=btn_initial,
                text_color=_get_dynamic_text_color(btn_initial),
            )
            self.btn_cc_user.configure(fg_color=bg_surface, text_color=text_primary)

    def _matches_time_control(self, game):
        """Checks whether a parsed chess.pgn.Game matches active sidebar time-control filters."""
        if self.filters.get("All", True) or not any(
            self.filters.get(m, False) for m in ("Blitz", "Rapid", "Standard")
        ):
            return True

        event_str = str(game.headers.get("Event", "")).lower()
        tc_str = str(game.headers.get("TimeControl", "")).lower()

        if self.filters.get("Blitz") and ("blitz" in event_str or tc_str in {"180", "180+2", "60", "120+1"}):
            return True
        if self.filters.get("Rapid") and ("rapid" in event_str or tc_str in {"600", "900", "900+10", "600+5"}):
            return True
        if self.filters.get("Standard") and any(k in event_str for k in ("standard", "classical", "daily")):
            return True

        return False

    def _trigger_platform_action(self, platform, action="last"):
        """Fetches games directly via API for both platforms (last or batch), parses them, and loads mixed_analysis."""
        self._set_active_platform(platform)
        current_user = self.cc_saved_username if platform == "chess_com" else self.lich_saved_username

        if not current_user:
            set_status_message(f"No username for {platform}. Redirecting to Mixed Collections.")
            state.show_workspace("mixed")
            return

        top_level = self.winfo_toplevel()
        action_label = "last game" if action == "last" else "up to 100 games"
        set_status_message(f"Fetching {action_label} for {current_user} ({platform})...")

        games_list = []
        try:
            headers = {"User-Agent": "ChessAnalysisApp/1.0"}

            if platform == "chess_com":
                archives_url = f"https://api.chess.com/pub/player/{current_user.lower()}/games/archives"
                req = urllib.request.Request(archives_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode("utf-8"))
                    archives = data.get("archives", [])
                    collected_games = []

                    if action == "last":
                        for archive_url in reversed(archives):
                            req_games = urllib.request.Request(archive_url, headers=headers)
                            with urllib.request.urlopen(req_games, timeout=15) as g_res:
                                g_data = json.loads(g_res.read().decode("utf-8"))
                                month_games = list(reversed(g_data.get("games", [])))
                                for g in month_games:
                                    pgn_text = g.get("pgn", "")
                                    if pgn_text:
                                        parsed_game = chess.pgn.read_game(io.StringIO(pgn_text))
                                        if parsed_game and self._matches_time_control(parsed_game):
                                            collected_games = [parsed_game]
                                            break
                            if collected_games:
                                break
                    else:
                        for archive_url in reversed(archives):
                            try:
                                req_games = urllib.request.Request(archive_url, headers=headers)
                                with urllib.request.urlopen(req_games, timeout=15) as g_res:
                                    g_data = json.loads(g_res.read().decode("utf-8"))
                                    month_games = g_data.get("games", [])
                                    for g in reversed(month_games):
                                        pgn_text = g.get("pgn", "")
                                        if pgn_text:
                                            parsed_game = chess.pgn.read_game(io.StringIO(pgn_text))
                                            if parsed_game and self._matches_time_control(parsed_game):
                                                collected_games.append(parsed_game)
                                                if len(collected_games) >= 100:
                                                    break
                            except Exception:
                                continue
                            if len(collected_games) >= 100:
                                break

                    games_list = collected_games[:100]
            else:
                max_games = 1 if action == "last" else 100
                lich_url = f"https://lichess.org/api/games/user/{current_user}?max={max_games}&pgnInJson=true"
                req = urllib.request.Request(lich_url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    for line in response:
                        line_str = line.decode("utf-8").strip()
                        if line_str:
                            try:
                                g_data = json.loads(line_str)
                                pgn_text = g_data.get("pgn", "")
                                if pgn_text:
                                    parsed_game = chess.pgn.read_game(io.StringIO(pgn_text))
                                    if parsed_game and self._matches_time_control(parsed_game):
                                        games_list.append(parsed_game)
                            except Exception:
                                continue
        except Exception as e:
            set_status_message(f"Fetch error: {e}")
            return

        source_data = f"{platform}_{current_user}_{action}"

        state.mixed_state["active_index"] = 0
        state.mixed_state["active_games"] = games_list
        state.mixed_state["active_focus"] = games_list[0] if games_list else None
        state.mixed_state["current_filename"] = source_data

        if hasattr(top_level, "show_workspace"):
            top_level.show_workspace(
                "mixed_analysis",
                initial_games=games_list,
                filename=source_data,
                active_focus=games_list[0] if games_list else None,
                active_index=0,
            )
        set_status_message(f"Loaded {len(games_list)} game(s) for {current_user}.")

    def _toggle_sidebar_filter(self, mode):
        """Toggles vertical filter states."""
        if mode == "All":
            is_checked = self.sidebar_box_labels["All"].get()
            if is_checked:
                for m in ("Blitz", "Rapid", "Standard"):
                    self.filters[m] = False
                    if m in self.sidebar_box_labels:
                        self.sidebar_box_labels[m].deselect()
                self.filters["All"] = True
            else:
                self.filters["All"] = False
        else:
            self.filters[mode] = bool(self.sidebar_box_labels[mode].get())
            if any(self.filters[m] for m in ("Blitz", "Rapid", "Standard")):
                self.filters["All"] = False
                if "All" in self.sidebar_box_labels:
                    self.sidebar_box_labels["All"].deselect()

    def _on_qeval_right_click(self, event):
        try:
            self.txt_qeval_moves.focus_set()
            clipboard_text = self.winfo_toplevel().clipboard_get()
            if not clipboard_text:
                return "break"

            current_text = self.txt_qeval_moves.get("1.0", "end").strip()
            if current_text == self.placeholder_text:
                self.txt_qeval_moves.delete("1.0", "end")
                self.txt_qeval_moves.configure(text_color=_theme_color("text_primary"))

            self.txt_qeval_moves.insert("insert", clipboard_text)
        except Exception:
            pass
        return "break"

    def _on_qeval_focus_in(self, event):
        current_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if current_text == self.placeholder_text:
            self.txt_qeval_moves.delete("1.0", "end")
            self.txt_qeval_moves.configure(text_color=_theme_color("text_primary"))

    def _on_qeval_focus_out(self, event):
        current_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if not current_text:
            self.txt_qeval_moves.insert("1.0", self.placeholder_text)
            self.txt_qeval_moves.configure(text_color=_theme_color("text_secondary", "text_primary"))

    def parse_qeval_pgn(self):
        raw_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if not raw_text or raw_text == self.placeholder_text:
            set_status_message("Error: Quick Evaluation box is empty.")
            return []

        cleaned_lines = [line.strip() for line in raw_text.splitlines()]
        normalized_text = "\n".join(cleaned_lines)

        games_list = []
        try:
            pgn_io = io.StringIO(normalized_text)
            while True:
                game = chess.pgn.read_game(pgn_io)
                if game is None:
                    break
                games_list.append(game)

            if not games_list:
                set_status_message("Error: No valid PGN games found.")
                return []
            return games_list
        except Exception as e:
            set_status_message(f"Parse Error: {e}")
            return []

    def handle_qeval_send_analysis(self):
        games_list = self.parse_qeval_pgn()
        if not games_list:
            return

        state.catalog_state["active_games"] = games_list
        state.catalog_state["active_index"] = 0
        state.catalog_state["active_focus"] = games_list[0]

        self.txt_qeval_moves.delete("1.0", "end")
        self.txt_qeval_moves.insert("1.0", self.placeholder_text)
        self.txt_qeval_moves.configure(text_color=_theme_color("text_secondary", "text_primary"))

        state.show_workspace("analysis")
        set_status_message(f"Loaded {len(games_list)} game(s).")


# --- LOCALIZED STATUS & PROGRESS BAR CONTROLLERS ---

def set_status_message(message, text_color=None):
    try:
        if text_color is None:
            text_color = _theme_color("status_text", "text_secondary")
        label = getattr(state, "status", None)
        if label:
            label.configure(text=message, text_color=text_color)
            label.update_idletasks()
    except Exception as e:
        print(f"Status Error: {e}")


def start_progress(indeterminate=False):
    try:
        pc = getattr(state, "progress_container", None)
        pb = getattr(state, "progress_bar", None)

        if pc and pb:
            if not pc.winfo_ismapped():
                status_box = getattr(state, "status", None)
                if status_box and status_box.master:
                    pc.pack(side="bottom", fill="x", padx=4, pady=(2, 2), before=status_box.master)
                else:
                    pc.pack(side="bottom", fill="x", padx=4, pady=(2, 2))

            if indeterminate:
                pb.configure(mode="indeterminate")
                pb.start()
            else:
                pb.configure(mode="determinate")
                pb.set(0.01)

            pc.update_idletasks()
    except Exception as e:
        print(f"Progress Start Error: {e}")


def update_progress(value):
    try:
        pb = getattr(state, "progress_bar", None)
        pc = getattr(state, "progress_container", None)

        if pb and pc:
            if not pc.winfo_ismapped():
                start_progress()

            clamped_val = max(0.0, min(1.0, value))

            if pb.cget("mode") == "indeterminate":
                try:
                    pb.stop()
                except Exception:
                    pass
                pb.configure(mode="determinate")

            pb.set(clamped_val)
            pb.update_idletasks()

            if clamped_val >= 1.0:
                pb.after(300, stop_progress)
    except Exception as e:
        print(f"Progress Update Error: {e}")


def stop_progress():
    try:
        pb = getattr(state, "progress_bar", None)
        pc = getattr(state, "progress_container", None)

        if pb:
            try:
                pb.stop()
            except Exception:
                pass
            pb.set(0.0)

        if pc and pc.winfo_ismapped():
            pc.pack_forget()
            pc.update_idletasks()
    except Exception as e:
        print(f"Progress Stop Error: {e}")


# --- TOP LEVEL FUNCTIONS ---

def create_sidebar(app, on_navigate_callback=None):
    sidebar = Sidebar(app)
    state.left_frame = sidebar
    state.sidebar_visible = True

    if hasattr(app, "grid_columnconfigure"):
        app.grid_columnconfigure(0, minsize=205, weight=0)

    return sidebar


def toggle_sidebar():
    sidebar = getattr(state, "left_frame", None)
    if sidebar is None:
        return

    app = sidebar.master

    if getattr(state, "sidebar_visible", True):
        sidebar.grid_remove()
        if hasattr(app, "grid_columnconfigure"):
            app.grid_columnconfigure(0, minsize=0, weight=0)
        state.sidebar_visible = False
    else:
        if hasattr(app, "grid_columnconfigure"):
            app.grid_columnconfigure(0, minsize=205, weight=0)

        sidebar.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        state.sidebar_visible = True