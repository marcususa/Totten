import io
import json
import os
import chess
import chess.pgn
import customtkinter as ctk
import gui.app_state as state
import gui.calendar_workspace
from core.constants import THEME


def _get_dynamic_progress_fill():
    """Computes a high-contrast progress fill color dynamically based on background luminance."""
    bg = THEME.get("bg_panel", "#172134").lstrip('#')
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
        return "#ffffff"


def _get_dynamic_text_color(hex_str):
    """Computes high-contrast text color (dark or white) based on button background luminance."""
    clean_hex = hex_str.lstrip('#')
    try:
        r, g, b = int(clean_hex[0:2], 16), int(clean_hex[2:4], 16), int(clean_hex[4:6], 16)
        luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255.0
        return "#0f172a" if luminance > 0.5 else "#ffffff"
    except Exception:
        return THEME.get("text_primary", "#ffffff")


class Sidebar(ctk.CTkFrame):
    CONFIG_FILE = "chess_accounts.json"

    def __init__(self, parent):
        super().__init__(parent, width=205, corner_radius=0, fg_color=THEME.get("bg_panel"))
        super().pack_propagate(False)

        # Load saved accounts for both platforms
        self.saved_accounts = self._load_saved_accounts()
        self.cc_saved_username = self.saved_accounts.get("chess_com", None)
        self.lich_saved_username = self.saved_accounts.get("lichess", None)

        # Track active platform ("chess_com" or "lichess")
        self.active_platform = "chess_com"

        # Filter states
        self.filters = {"Blitz": False, "Rapid": False, "Standard": False, "All": True}

        # --- STATUS DISPLAY ---
        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(side="bottom", fill="x", padx=4, pady=(2, 6))

        self.lbl_status = ctk.CTkLabel(
            self.status_container,
            text="Ready",
            anchor="sw",
            justify="left",
            wraplength=75,
            font=ctk.CTkFont(size=10),
            text_color=THEME.get("status_text", "#ddddff")
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
            fg_color=THEME.get("progress_bg", "#1e293b"),
            progress_color=_get_dynamic_progress_fill(),
            mode="determinate"
        )
        self.progress_bar.pack(fill="x", expand=True, pady=4)
        self.progress_bar.set(0.0)

        state.progress_bar = self.progress_bar

        # Keep the progress bar hidden by default on startup
        self.progress_container.pack_forget()

        # --- NAVIGATION BUTTONS ---
        self.btn_catalog = ctk.CTkButton(
            self, text="Catalog", anchor="w", fg_color="transparent",
            hover_color=THEME["btn_hover"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=11),
            command=lambda: state.show_workspace("search_catalog")
        )
        self.btn_catalog.pack(fill="x", padx=4, pady=(15, 4))

        self.btn_analysis = ctk.CTkButton(
            self, text="Analysis", anchor="w", fg_color="transparent",
            hover_color=THEME["btn_hover"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=11),
            command=lambda: state.show_workspace("analysis")
        )
        self.btn_analysis.pack(fill="x", padx=4, pady=4)

        self.btn_patterns = ctk.CTkButton(
            self, text="Patterns", anchor="w", fg_color="transparent",
            hover_color=THEME["btn_hover"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=11),
            command=lambda: state.show_workspace("patterns")
        )
        self.btn_patterns.pack(fill="x", padx=4, pady=4)

        self.btn_mixed = ctk.CTkButton(
            self, text="Mixed", anchor="w", fg_color="transparent",
            hover_color=THEME["btn_hover"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=11),
            command=lambda: state.show_workspace("mixed")
        )
        self.btn_mixed.pack(fill="x", padx=4, pady=4)

        self.btn_calendar = ctk.CTkButton(
            self, text="Calendar", anchor="w", fg_color="transparent",
            hover_color=THEME["btn_hover"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=11),
            command=lambda: state.show_workspace("calendar")
        )
        self.btn_calendar.pack(fill="x", padx=4, pady=4)

        # Start with the analysis workspace on startup
        state.show_workspace("analysis")

        # --- QUICK EVALUATION SECTION ---
        self.placeholder_text = "Paste PGN for quick analysis. You can also search online users below."

        self.txt_qeval_moves = ctk.CTkTextbox(
            self, height=75, fg_color=THEME["bg_surface"], text_color=THEME["text_primary"],
            font=ctk.CTkFont(size=9), border_color=THEME["border_color"], border_width=1, wrap="word"
        )
        self.txt_qeval_moves.pack(fill="x", padx=4, pady=(10, 4))

        self.txt_qeval_moves.insert("1.0", self.placeholder_text)
        self.txt_qeval_moves.configure(text_color=THEME["text_secondary"])

        self.txt_qeval_moves.bind("<FocusIn>", self._on_qeval_focus_in)
        self.txt_qeval_moves.bind("<FocusOut>", self._on_qeval_focus_out)
        self.txt_qeval_moves.bind("<Button-3>", self._on_qeval_right_click)
        self.txt_qeval_moves.bind("<Button-2>", self._on_qeval_right_click)

        self.btn_qeval_analysis = ctk.CTkButton(
            self, text="Analyze", height=24, font=ctk.CTkFont(size=10),
            fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            text_color=_get_dynamic_text_color(THEME.get("btn_initial", "#344268")),
            command=self.handle_qeval_send_analysis
        )
        self.btn_qeval_analysis.pack(fill="x", padx=4, pady=(0, 4))

        # --- ONLINE ACCOUNT QUICK CONTROLS (Strictly Vertical Stack) ---
        self.account_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.account_panel.pack(fill="x", padx=4, pady=(12, 6))

        # Chess.com Button
        cc_text = self.cc_saved_username if self.cc_saved_username else "Chess.com"
        self.btn_cc_user = ctk.CTkButton(
            self.account_panel, text=cc_text, height=22, anchor="center", font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=_get_dynamic_text_color(THEME.get("btn_initial", "#344268")),
            command=lambda: self._trigger_platform_action("chess_com", action="last")
        )
        self.btn_cc_user.pack(fill="x", pady=(0, 4))

        # Lichess.org Button (Consistently Styled)
        lich_text = self.lich_saved_username if self.lich_saved_username else "Lichess.org"
        self.btn_lich_user = ctk.CTkButton(
            self.account_panel, text=lich_text, height=22, anchor="center", font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=THEME["btn_initial"],
            hover_color=THEME["btn_hover"],
            text_color=_get_dynamic_text_color(THEME.get("btn_initial", "#344268")),
            command=lambda: self._trigger_platform_action("lichess", action="last")
        )
        self.btn_lich_user.pack(fill="x", pady=(0, 6))

        # Vertical List for Time Control Checkboxes
        self.sidebar_box_labels = {}
        for mode in ("Blitz", "Rapid", "Standard", "All"):
            var = ctk.BooleanVar(value=self.filters.get(mode, False))
            chk = ctk.CTkCheckBox(
                self.account_panel, text=mode, variable=var,
                font=("Arial", 10, "bold"), checkbox_width=12, checkbox_height=12,
                border_width=1, corner_radius=2,
                text_color=THEME.get("text_secondary", "#aaaaaa"),
                command=lambda m=mode: self._toggle_sidebar_filter(m)
            )
            chk.pack(anchor="w", padx=2, pady=1)
            self.sidebar_box_labels[mode] = chk

        # Batch Download Button ("100")
        ctk.CTkButton(
            self.account_panel, text="100", height=22, anchor="center", font=ctk.CTkFont(size=9, weight="bold"),
            fg_color=THEME["btn_initial"], hover_color=THEME["btn_hover"],
            text_color=_get_dynamic_text_color(THEME.get("btn_initial", "#344268")),
            command=lambda: self._trigger_platform_action(self.active_platform, action="batch")
        ).pack(fill="x", pady=(4, 0))

    def _load_saved_accounts(self):
        """Loads saved usernames from the local JSON config file."""
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[DEBUG] Error loading accounts config: {e}")
        return {"chess_com": None, "lichess": None}

    def _set_active_platform(self, platform):
        """Highlights the active platform button."""
        self.active_platform = platform
        if platform == "chess_com":
            self.btn_cc_user.configure(fg_color=THEME["btn_initial"],
                                       text_color=_get_dynamic_text_color(THEME.get("btn_initial", "#344268")))
            self.btn_lich_user.configure(fg_color=THEME["bg_surface"], text_color=THEME["text_primary"])
        else:
            self.btn_lich_user.configure(fg_color=THEME["btn_initial"],
                                         text_color=_get_dynamic_text_color(THEME.get("btn_initial", "#344268")))
            self.btn_cc_user.configure(fg_color=THEME["bg_surface"], text_color=THEME["text_primary"])

    def _trigger_platform_action(self, platform, action="last"):
        """Fetches games directly via API for both platforms (last or batch), parses them, and loads mixed_analysis."""
        self._set_active_platform(platform)
        current_user = self.cc_saved_username if platform == "chess_com" else self.lich_saved_username

        if not current_user:
            set_status_message(f"No username for {platform}. Redirecting to Mixed.")
            state.show_workspace("mixed")
            return

        # ... rest of the method ...
        top_level = self.winfo_toplevel()
        action_label = "last game" if action == "last" else "up to 100 games"
        set_status_message(f"Fetching {action_label} for {current_user} ({platform})...")

        games_list = []
        try:
            import urllib.request
            import json
            import io
            import chess.pgn

            headers = {'User-Agent': 'ChessAnalysisApp/1.0'}

            if platform == "chess_com":
                archives_url = f"https://api.chess.com/pub/player/{current_user.lower()}/games/archives"
                req = urllib.request.Request(archives_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    archives = data.get("archives", [])
                    collected_games = []

                    if action == "last":
                        if archives:
                            latest_archive = archives[-1]
                            req_games = urllib.request.Request(latest_archive, headers=headers)
                            with urllib.request.urlopen(req_games, timeout=15) as g_res:
                                g_data = json.loads(g_res.read().decode('utf-8'))
                                month_games = g_data.get("games", [])
                                if month_games:
                                    collected_games = [month_games[-1]]
                    else:  # batch / 100
                        for archive_url in reversed(archives):
                            try:
                                req_games = urllib.request.Request(archive_url, headers=headers)
                                with urllib.request.urlopen(req_games, timeout=15) as g_res:
                                    g_data = json.loads(g_res.read().decode('utf-8'))
                                    month_games = g_data.get("games", [])
                                    collected_games = list(reversed(month_games)) + collected_games
                                    if len(collected_games) >= 100:
                                        collected_games = collected_games[:100]
                                        break
                            except Exception:
                                continue

                    for g in collected_games:
                        pgn_text = g.get("pgn", "")
                        if pgn_text:
                            parsed_game = chess.pgn.read_game(io.StringIO(pgn_text))
                            if parsed_game:
                                games_list.append(parsed_game)
            else:
                # Lichess fetch endpoint for both last (max=1) and batch (max=100)
                max_games = 1 if action == "last" else 100
                lich_url = f"https://lichess.org/api/games/user/{current_user}?max={max_games}&pgnInJson=true"
                req = urllib.request.Request(lich_url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    for line in response:
                        line_str = line.decode('utf-8').strip()
                        if line_str:
                            try:
                                g_data = json.loads(line_str)
                                pgn_text = g_data.get("pgn", "")
                                if pgn_text:
                                    parsed_game = chess.pgn.read_game(io.StringIO(pgn_text))
                                    if parsed_game:
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
                active_index=0
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
                self.txt_qeval_moves.configure(text_color=THEME["text_primary"])

            self.txt_qeval_moves.insert("insert", clipboard_text)
        except Exception:
            pass
        return "break"

    def _on_qeval_focus_in(self, event):
        current_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if current_text == self.placeholder_text:
            self.txt_qeval_moves.delete("1.0", "end")
            self.txt_qeval_moves.configure(text_color=THEME["text_primary"])

    def _on_qeval_focus_out(self, event):
        current_text = self.txt_qeval_moves.get("1.0", "end").strip()
        if not current_text:
            self.txt_qeval_moves.insert("1.0", "end")
            self.txt_qeval_moves.configure(text_color=THEME["text_secondary"])

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
        self.txt_qeval_moves.configure(text_color=THEME["text_secondary"])

        state.show_workspace("analysis")
        set_status_message(f"Loaded {len(games_list)} game(s).")


# --- LOCALIZED STATUS & PROGRESS BAR CONTROLLERS ---

def set_status_message(message, text_color=None):
    try:
        if text_color is None:
            text_color = THEME.get("status_text", "#ddddff")
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