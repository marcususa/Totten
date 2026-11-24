import os
import shutil
import sys
from pathlib import Path
from tkinter import messagebox
import customtkinter as ctk
from PIL import Image, ImageTk

from .theme_data import (
    load_user_data,
    save_user_data,
    handle_board_background_upload,
    handle_remove_board_background,
)

MATERIAL_KEYWORDS = ("marble", "metal", "newspaper", "sandstone", "water", "wood")
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"}

THUMB_WIDTH = 48
THUMB_HEIGHT = 32
PREVIEW_WIDTH = THUMB_WIDTH * 3
PREVIEW_HEIGHT = THUMB_HEIGHT * 3


def get_project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def get_boards_dir() -> Path:
    boards_dir = get_project_root() / "assets" / "boards"
    boards_dir.mkdir(parents=True, exist_ok=True)
    return boards_dir


def detect_material_family(filename: str) -> str | None:
    stem = Path(filename).stem.lower()
    for keyword in MATERIAL_KEYWORDS:
        if keyword in stem:
            return keyword
    return None


class ThemeBoardsWindow(ctk.CTkToplevel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title("Theme Boards")
        self.resizable(True, True)
        self.attributes("-topmost", True)

        self.boards_dir = get_boards_dir()
        self.user_data = load_user_data()
        self.board_state = dict(self.user_data.get("board_background_state", {}))

        saved_file = self.board_state.get("active_board_file")
        self.selected_board_name: str | None = saved_file if saved_file else None

        saved_recent = self.board_state.get("recent_boards", [])
        self.recent_boards: list[str] = [
            name for name in saved_recent if isinstance(name, str)
        ]
        if self.selected_board_name and self.selected_board_name not in self.recent_boards:
            self.recent_boards.insert(0, self.selected_board_name)

        self._preview_photos: dict[str, ImageTk.PhotoImage] = {}

        self._build_ui()
        self.refresh_board_grid()
        self._fit_window_to_content()

    def _fit_window_to_content(self):
        self.update_idletasks()
        window_width = max(self.winfo_reqwidth() + 40, (PREVIEW_WIDTH * 3) + 100)
        window_height = max(self.winfo_reqheight() + 40, 340)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_coord = int((screen_width / 2) - (window_width / 2))
        y_coord = int((screen_height / 2) - (window_height / 2))
        self.geometry(f"{window_width}x{window_height}+{x_coord}+{y_coord}")
        self.minsize(window_width, window_height)

    def _build_ui(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=15)

        self.grid_container = ctk.CTkFrame(main_frame, fg_color="transparent")
        self.grid_container.pack(fill="both", expand=True)
        for col in range(3):
            self.grid_container.grid_columnconfigure(col, weight=1)

        actions_outer = ctk.CTkFrame(main_frame, fg_color="transparent")
        actions_outer.pack(fill="x", pady=(12, 0))

        actions_frame = ctk.CTkFrame(actions_outer, fg_color="transparent")
        actions_frame.pack(anchor="center")

        ctk.CTkButton(
            actions_frame,
            text="Add Background",
            height=28,
            command=self.add_board_background,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            actions_frame,
            text="Apply Board",
            height=28,
            command=self.apply_selected_board,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            actions_frame,
            text="Delete Board",
            height=28,
            command=self.delete_board,
        ).pack(side="left", padx=6)

    def _promote_to_front(self, file_name: str):
        if file_name in self.recent_boards:
            self.recent_boards.remove(file_name)
        self.recent_boards.insert(0, file_name)
        self.selected_board_name = file_name
        self._persist_state()

    def _persist_state(self, clear_active: bool = False):
        try:
            user_data = load_user_data()
            state_data = dict(user_data.get("board_background_state", {}))
            state_data["recent_boards"] = list(self.recent_boards)
            if clear_active:
                state_data.pop("active_board_file", None)
                state_data.pop("resolved_board_file", None)
            elif self.selected_board_name:
                state_data["active_board_file"] = self.selected_board_name
            user_data["board_background_state"] = state_data
            save_user_data(user_data)
        except Exception as e:
            print(f"[THEME BOARDS] State save failed: {e}")

    def _confirm_delete_existing(self, file_name: str) -> bool:
        was_topmost = bool(self.attributes("-topmost"))
        self.attributes("-topmost", False)
        try:
            return messagebox.askyesno(
                title="File Already Exists",
                message=f'"{file_name}" already exists. Do you want to delete the current file with the same name?',
                parent=self,
            )
        finally:
            self.attributes("-topmost", was_topmost)

    def _existing_disk_files(self) -> dict[str, Path]:
        found: dict[str, Path] = {}
        if not self.boards_dir.exists():
            return found
        for entry in sorted(self.boards_dir.iterdir(), key=lambda p: p.name.lower()):
            if not entry.is_file() or entry.suffix.lower() not in IMAGE_EXTENSIONS:
                continue
            found[entry.name] = entry
        return found

    def get_slot_entries(self) -> list[dict]:
        found = self._existing_disk_files()
        slots: list[dict] = []
        used_names: set[str] = set()
        filled_materials: set[str] = set()

        for name in list(self.recent_boards):
            if name in found and name not in used_names:
                used_names.add(name)
                mat = detect_material_family(name)
                if mat:
                    filled_materials.add(mat)
                slots.append({
                    "key": mat or Path(name).stem.lower(),
                    "label": None,
                    "path": found[name],
                    "exists": True,
                })

        for mat in MATERIAL_KEYWORDS:
            canonical_name = f"{mat}.png"
            matching = [
                fname for fname in sorted(found.keys(), key=lambda s: s.lower())
                if fname not in used_names and detect_material_family(fname) == mat
            ]
            if canonical_name in found and canonical_name not in used_names:
                used_names.add(canonical_name)
                filled_materials.add(mat)
                slots.append({
                    "key": mat,
                    "label": None,
                    "path": found[canonical_name],
                    "exists": True,
                })
            elif matching:
                chosen = matching[0]
                used_names.add(chosen)
                filled_materials.add(mat)
                slots.append({
                    "key": mat,
                    "label": None,
                    "path": found[chosen],
                    "exists": True,
                })
            elif mat not in filled_materials:
                slots.append({
                    "key": mat,
                    "label": mat.capitalize(),
                    "path": self.boards_dir / canonical_name,
                    "exists": False,
                })

        for name in sorted(found.keys(), key=lambda s: s.lower()):
            if name not in used_names:
                used_names.add(name)
                mat = detect_material_family(name)
                if mat:
                    filled_materials.add(mat)
                slots.append({
                    "key": mat or Path(name).stem.lower(),
                    "label": None,
                    "path": found[name],
                    "exists": True,
                })

        return slots

    def _draw_missing_slot(self, canvas: ctk.CTkCanvas, width: int, height: int, label: str):
        canvas.delete("all")
        canvas.create_rectangle(2, 2, width - 2, height - 2, outline="#666666", dash=(4, 2))
        cx, cy = width // 2, height // 2
        arm = 7
        plus_cy = cy - 16
        canvas.create_line(cx - arm, plus_cy, cx + arm, plus_cy, fill="#9ca3af", width=2)
        canvas.create_line(cx, plus_cy - arm, cx, plus_cy + arm, fill="#9ca3af", width=2)
        canvas.create_text(
            cx,
            cy + 20,
            text=label,
            fill="#d1d5db",
            font=("Arial", 11, "bold"),
        )

    def refresh_board_grid(self):
        for widget in self.grid_container.winfo_children():
            widget.destroy()
        self._preview_photos.clear()

        slots = self.get_slot_entries()

        for idx, slot in enumerate(slots):
            row_idx = idx // 3
            col_slot = idx % 3
            file_name = slot["path"].name
            exists = slot["exists"]
            label_text = slot["label"] or slot["key"].capitalize()

            is_selected = (self.selected_board_name == file_name and exists)
            card = ctk.CTkFrame(
                self.grid_container,
                border_width=2,
                border_color="#3b82f6" if is_selected else "#555555",
                corner_radius=6,
            )
            card.grid(row=row_idx, column=col_slot, padx=5, pady=4, sticky="nsew")

            canvas = ctk.CTkCanvas(
                card,
                width=PREVIEW_WIDTH,
                height=PREVIEW_HEIGHT,
                bg="#2b2b2b",
                highlightthickness=0,
                cursor="hand2",
            )
            canvas.pack(padx=6, pady=6)

            if exists:
                try:
                    img = Image.open(slot["path"]).convert("RGB")
                    img = img.resize((PREVIEW_WIDTH, PREVIEW_HEIGHT), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self._preview_photos[file_name] = photo
                    canvas.create_image(PREVIEW_WIDTH // 2, PREVIEW_HEIGHT // 2, image=photo)
                    canvas.bind("<Button-1>", lambda _event, fn=file_name: self.select_board(fn))
                    card.bind("<Button-1>", lambda _event, fn=file_name: self.select_board(fn))
                except Exception:
                    self._draw_missing_slot(canvas, PREVIEW_WIDTH, PREVIEW_HEIGHT, label_text)
                    canvas.bind("<Button-1>", lambda _event, m=slot["key"]: self.add_board_background(m))
                    card.bind("<Button-1>", lambda _event, m=slot["key"]: self.add_board_background(m))
            else:
                self._draw_missing_slot(canvas, PREVIEW_WIDTH, PREVIEW_HEIGHT, label_text)
                canvas.bind("<Button-1>", lambda _event, m=slot["key"]: self.add_board_background(m))
                card.bind("<Button-1>", lambda _event, m=slot["key"]: self.add_board_background(m))

    def select_board(self, file_name: str):
        self._promote_to_front(file_name)
        self.refresh_board_grid()

    def add_board_background(self, target_material: str | None = None):
        self.attributes("-topmost", False)
        try:
            file_path = ctk.filedialog.askopenfilename(
                title="Add Board Background to /assets/boards/",
                filetypes=[("Image Files", "*.png *.jpg *.jpeg *.bmp *.gif *.webp")],
                parent=self,
            )
        finally:
            self.attributes("-topmost", True)

        if not file_path:
            return

        src = Path(file_path)
        matched_mat = target_material or detect_material_family(src.name)

        if matched_mat:
            dest_name = f"{matched_mat}.png"
            dest = self.boards_dir / dest_name
            if dest.exists() and src.resolve() != dest.resolve():
                if not self._confirm_delete_existing(dest_name):
                    return
                dest.unlink()
            try:
                img = Image.open(src).convert("RGB")
                img.save(dest, format="PNG")
                self._promote_to_front(dest.name)
                self.refresh_board_grid()
                self._fit_window_to_content()
                return
            except Exception as e:
                print(f"[THEME BOARDS] Save failed ({dest_name}): {e}")

        dest = self.boards_dir / src.name
        if dest.exists() and src.resolve() != dest.resolve():
            if not self._confirm_delete_existing(dest.name):
                return
            dest.unlink()

        try:
            if src.resolve() != dest.resolve():
                shutil.copy2(src, dest)
            self._promote_to_front(dest.name)
            self.refresh_board_grid()
            self._fit_window_to_content()
        except Exception as e:
            print(f"[THEME BOARDS] Copy failed: {e}")
            handle_board_background_upload(file_path)

    def apply_selected_board(self):
        if not self.selected_board_name:
            return

        chosen_path = self.boards_dir / self.selected_board_name
        if not chosen_path.exists():
            return

        self._promote_to_front(self.selected_board_name)

        try:
            handle_board_background_upload(str(chosen_path))
            user_data = load_user_data()
            state_data = dict(user_data.get("board_background_state", {}))
            state_data["active_board_file"] = self.selected_board_name
            state_data["resolved_board_file"] = chosen_path.name
            state_data["recent_boards"] = list(self.recent_boards)
            user_data["board_background_state"] = state_data
            save_user_data(user_data)
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"[THEME BOARDS] Apply failed: {e}")

    def delete_board(self):
        if not self.selected_board_name:
            return

        target_name = self.selected_board_name
        target_path = self.boards_dir / target_name

        if target_name in self.recent_boards:
            self.recent_boards.remove(target_name)

        try:
            if target_path.exists() and target_path.is_file():
                target_path.unlink()
        except Exception as e:
            print(f"[THEME BOARDS] Delete failed ({target_name}): {e}")

        self.selected_board_name = self.recent_boards[0] if self.recent_boards else None
        self._persist_state(clear_active=(self.selected_board_name is None))

        if self.selected_board_name is None:
            try:
                handle_remove_board_background()
            except Exception as e:
                print(f"[THEME BOARDS] Clear active background failed: {e}")

        self.refresh_board_grid()
        self._fit_window_to_content()