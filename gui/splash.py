import tkinter as tk
import customtkinter as ctk


class StandaloneSplash:
    def __init__(self, title_text="Totten", message="Starting up..."):
        self.root = tk.Tk()
        self.root.overrideredirect(True)

        width = 280
        height = 150

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.configure(bg="#172134")

        self.frame = tk.Frame(self.root, bg="#222e42", highlightbackground="#344268", highlightthickness=2)
        self.frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.lbl_title = tk.Label(
            self.frame, text=title_text, font=("Arial", 28, "bold"), fg="white", bg="#222e42"
        )
        self.lbl_title.pack(pady=(25, 5))

        self.lbl_message = tk.Label(
            self.frame, text=message, font=("Arial", 12), fg="#94a3b8", bg="#222e42"
        )
        self.lbl_message.pack(pady=(0, 20))

        self.root.update()

    def update_message(self, new_message):
        try:
            self.lbl_message.config(text=new_message)
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
        self.overrideredirect(True)

        width = 280
        height = 150

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

        frame = ctk.CTkFrame(self, fg_color="#222e42", border_width=2, border_color="#344268", corner_radius=8)
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        self.lbl_title = ctk.CTkLabel(
            frame, text=title_text, font=("Arial", 28, "bold"), text_color="white"
        )
        self.lbl_title.pack(pady=(25, 5))

        self.lbl_message = ctk.CTkLabel(
            frame, text=message, font=("Arial", 12), text_color="#94a3b8"
        )
        self.lbl_message.pack(pady=(0, 20))

        self.update()

    def update_message(self, new_message):
        try:
            self.lbl_message.configure(text=new_message)
            self.update_idletasks()
        except Exception:
            pass

    def close(self):
        try:
            self.grab_release()
            self.destroy()
        except Exception:
            pass