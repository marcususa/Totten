import json
import threading
import urllib.request
import urllib.error
import io
import chess
import chess.pgn
import gui.app_state as state


class EditDataMixin:
    """Handles network requests, background workers, filter states, and table updates."""

    def _save_cc_account(self):
        username = self.entry_cc_username.get().strip()
        if username:
            self.cc_saved_username = username
            self.cc_input_row.pack_forget()
            self.btn_cc_quick.configure(text=f"{username}")
            self.cc_active_frame.pack(fill="x", pady=(2, 0))
            print(f"[DEBUG ACCOUNT] Registered Chess.com quick-button for: {username}")

    def _save_lich_account(self):
        username = self.entry_lich_username.get().strip()
        if username:
            self.lich_saved_username = username
            self.lich_input_row.pack_forget()
            self.btn_lich_quick.configure(text=f"{username}")
            self.lich_active_frame.pack(fill="x", pady=(2, 0))
            print(f"[DEBUG ACCOUNT] Registered Lichess quick-button for: {username}")

    def _toggle_cc_filter(self, mode):
        self.cc_filters[mode] = not self.cc_filters[mode]
        for m, lbl in self.cc_box_labels.items():
            symbol = '■' if self.cc_filters[m] else '□'
            lbl.configure(text=symbol)

    def _toggle_lich_filter(self, mode):
        self.lich_filters[mode] = not self.lich_filters[mode]
        for m, lbl in self.lich_box_labels.items():
            symbol = '■' if self.lich_filters[m] else '□'
            lbl.configure(text=symbol)

    def _quick_fetch_cc_last(self):
        if self.cc_saved_username:
            print(f"[DEBUG CHESS.COM] Fetching last game for quick button: {self.cc_saved_username}")
            threading.Thread(target=self._worker_fetch_chess_com_batch,
                             args=(self.cc_saved_username, {"B": True, "R": True, "S": True, "ALL": True}, 1),
                             daemon=True).start()

    def _batch_cc_download(self):
        if self.cc_saved_username:
            print(f"[DEBUG CHESS.COM] Batch download (last 100) for {self.cc_saved_username} with filters: {self.cc_filters}")
            threading.Thread(target=self._worker_fetch_chess_com_batch,
                             args=(self.cc_saved_username, self.cc_filters, 100), daemon=True).start()

    def _quick_fetch_lich_last(self):
        if self.lich_saved_username:
            print(f"[DEBUG LICHESS] Fetching last game for quick button: {self.lich_saved_username}")
            threading.Thread(target=self._worker_fetch_lichess_batch,
                             args=(self.lich_saved_username, {"B": True, "R": True, "S": True, "ALL": True}, 1),
                             daemon=True).start()

    def _batch_lich_download(self):
        if self.lich_saved_username:
            print(f"[DEBUG LICHESS] Batch download (last 100) for {self.lich_saved_username} with filters: {self.lich_filters}")
            threading.Thread(target=self._worker_fetch_lichess_batch,
                             args=(self.lich_saved_username, self.lich_filters, 100), daemon=True).start()

    def _update_tree_with_games(self, fetched_games):
        for item in self.col_tree.get_children():
            self.col_tree.delete(item)
        self.tree_map.clear()

        self.games_list = fetched_games
        for idx, g in enumerate(fetched_games, start=1):
            if hasattr(g, "headers"):
                w = g.headers.get("White", "Unknown")
                b = g.headers.get("Black", "Unknown")
                r = g.headers.get("Result", "*")
            else:
                w = g.get("white", "Unknown")
                b = g.get("black", "Unknown")
                r = g.get("result", "*")

            item_id = self.col_tree.insert("", "end", values=(idx, w, b, r))
            self.tree_map[item_id] = (g, "online_stream")

    def _worker_fetch_chess_com_batch(self, username, filters, max_count):
        try:
            headers = {"User-Agent": "ChessAppTool/1.0"}
            url = f"https://api.chess.com/pub/player/{username.lower()}/games/archives"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                archives = json.loads(resp.read().decode("utf-8")).get("archives", [])
                if archives:
                    raw_games = []
                    for arch_url in reversed(archives):
                        if len(raw_games) >= max_count * 2:
                            break
                        try:
                            req_month = urllib.request.Request(arch_url, headers=headers)
                            with urllib.request.urlopen(req_month, timeout=10) as month_resp:
                                month_games = json.loads(month_resp.read().decode("utf-8")).get("games", [])
                                raw_games = month_games + raw_games
                        except Exception:
                            continue

                    raw_games = list(reversed(raw_games))
                    parsed = []
                    for g_data in raw_games:
                        if len(parsed) >= max_count:
                            break
                        pgn_text = g_data.get("pgn", "")
                        game_obj = chess.pgn.read_game(io.StringIO(pgn_text)) if pgn_text else chess.pgn.Game()
                        if not pgn_text:
                            game_obj.headers["White"] = g_data.get("white", {}).get("username", username)
                            game_obj.headers["Black"] = g_data.get("black", {}).get("username", username)
                            game_obj.headers["Result"] = "*"

                        if not filters.get("ALL", True):
                            tc = game_obj.headers.get("TimeControl", "").lower()
                            match_mode = False
                            if filters.get("B") and ("blitz" in tc or "bullet" in tc):
                                match_mode = True
                            if filters.get("R") and "rapid" in tc:
                                match_mode = True
                            if filters.get("S") and ("classical" in tc or "standard" in tc):
                                match_mode = True
                            if not match_mode:
                                continue

                        parsed.append(game_obj)
                    self.after(0, lambda: self._update_tree_with_games(parsed))
        except Exception as e:
            print(f"[DEBUG CHESS.COM ERROR] {e}")

    def _worker_fetch_lichess_batch(self, username, filters, max_count):
        try:
            url = f"https://lichess.org/api/games/user/{username.lower()}?max={max_count * 2}"
            headers = {"Accept": "application/x-ndjson", "User-Agent": "ChessAppTool/1.0"}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                parsed = []
                for line in resp:
                    if len(parsed) >= max_count:
                        break
                    decoded = line.decode("utf-8").strip()
                    if decoded:
                        g = json.loads(decoded)
                        speed = g.get("speed", "").lower()

                        if not filters.get("ALL", True):
                            match_mode = False
                            if filters.get("B") and speed in ("blitz", "bullet"):
                                match_mode = True
                            if filters.get("R") and speed == "rapid":
                                match_mode = True
                            if filters.get("S") and speed in ("classical", "correspondence"):
                                match_mode = True
                            if not match_mode:
                                continue

                        game_obj = chess.pgn.Game()
                        w_name = g.get("players", {}).get("white", {}).get("user", {}).get("name", "Unknown")
                        b_name = g.get("players", {}).get("black", {}).get("user", {}).get("name", "Unknown")
                        winner = g.get("winner")
                        res = "1-0" if winner == "white" else ("0-1" if winner == "black" else "1/2-1/2")

                        game_obj.headers["White"] = w_name
                        game_obj.headers["Black"] = b_name
                        game_obj.headers["Result"] = res

                        parsed.append(game_obj)
                self.after(0, lambda: self._update_tree_with_games(parsed))
        except Exception as e:
            print(f"[DEBUG LICHESS ERROR] {e}")