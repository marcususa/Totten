import tkinter as tk
import customtkinter as ctk


class StandaloneSplash:
    def __init__(self, title_text="Totten", message="Starting up..."):
        self.root = tk.Tk()
        self.root.overrideredirect(True)

        width = 280
        height = 170

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(bg="#172134")

        self.frame = tk.Frame(self.root, bg="#222e42", bd=0)
        self.frame.pack(fill="both", expand=True, padx=2, pady=2)

        # Centered vertical padding for startup splash (no progress bar)
        self.lbl_title = tk.Label(
            self.frame, text=title_text, font=("Arial", 28, "bold"), fg="white", bg="#222e42"
        )
        self.lbl_title.pack(pady=(35, 5))

        padded_msg = f"{message:^30}"
        self.lbl_message = tk.Label(
            self.frame, text=padded_msg, font=("Arial", 12), fg="#94a3b8", bg="#222e42"
        )
        self.lbl_message.pack(pady=(0, 20))

        self.root.update()

    def update_message(self, new_message):
        try:
            padded_msg = f"{new_message:^30}"
            self.lbl_message.config(text=padded_msg, bg="#222e42", fg="#94a3b8")
            self.root.update_idletasks()
        except Exception:
            pass

    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass


class LoadingOverlay(ctk.CTkToplevel):
    def __init__(self, master=None, title_text="Totten", message="Loading..."):
        super().__init__(master)

        self.withdraw()
        self.overrideredirect(True)

        width = 280
        height = 195

        if master and master.winfo_exists():
            m_x = master.winfo_rootx()
            m_y = master.winfo_rooty()
            m_w = master.winfo_width()
            m_h = master.winfo_height()
            x = int(m_x + (m_w / 2) - (width / 2))
            y = int(m_y + (m_h / 2) - (height / 2))
        else:
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            x = int((screen_width / 2) - (width / 2))
            y = int((screen_height / 2) - (height / 2))

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.configure(fg_color="#172134")
        self.transient(master)
        self.grab_set()

        frame = ctk.CTkFrame(self, fg_color="#222e42", corner_radius=0)
        frame.pack(fill="both", expand=True, padx=2, pady=2)

        self.lbl_title = ctk.CTkLabel(
            frame, text=title_text, font=("Arial", 28, "bold"), text_color="white", fg_color="#222e42"
        )
        self.lbl_title.pack(pady=(20, 5))

        padded_msg = f"{message:^30}"
        self.lbl_message = ctk.CTkLabel(
            frame, text=padded_msg, font=("Arial", 12), text_color="#94a3b8", fg_color="#222e42", width=260
        )
        self.lbl_message.pack(pady=(0, 10))

        # Animated looping progress bar
        self.progress_bar = ctk.CTkProgressBar(
            frame, width=220, height=8, fg_color="#172134", progress_color="#2e4a8c", corner_radius=0
        )
        self.progress_bar.pack(pady=(0, 8))
        self.progress_bar.set(0)

        # "Please wait." label using exact same font style and size (Arial 12)
        self.lbl_wait = ctk.CTkLabel(
            frame, text="", font=("Arial", 12), text_color="#94a3b8", fg_color="#222e42", width=260
        )
        self.lbl_wait.pack(pady=(0, 10))

        self._is_animating = True
        self._animate_progress()

        self.update_idletasks()
        self.deiconify()

    def _animate_progress(self):
        if not self._is_animating:
            return
        try:
            current = self.progress_bar.get()
            next_val = current + 0.05
            if next_val > 1.0:
                next_val = 0.0
            self.progress_bar.set(next_val)

            self.update_idletasks()
            if self.master and hasattr(self.master, "update_idletasks"):
                self.master.update_idletasks()

            self.after(30, self._animate_progress)
        except Exception:
            pass

    def update_message(self, new_message):
        try:
            padded_msg = f"{new_message:^30}"
            self.lbl_message.configure(text=padded_msg, fg_color="#222e42", text_color="#94a3b8")

            if "building" in new_message.lower():
                self.lbl_wait.configure(text=f"{'Please wait.':^30}")
            else:
                self.lbl_wait.configure(text="")

            self.update_idletasks()
        except Exception:
            pass

    def close(self):
        self._is_animating = False
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass