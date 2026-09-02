# gui/statusbar.py

import gui.app_state as state


def set_status_message(message, text_color="#ddddff"):
    """Updates the status bar label in the sidebar safely with #ddddff default."""
    print(f"[DEBUG STATUS]: {message}")
    try:
        label = getattr(state, "status", None) or getattr(state, "status_label", None)
        if label:
            active_color = text_color if text_color else "#ddddff"
            label.configure(text=message, text_color=active_color)
            if hasattr(label, "update_idletasks"):
                label.update_idletasks()
    except Exception as e:
        print(f"Status Error: {e}")


def start_progress(indeterminate=False):
    """Packs the container and resets progress bar to start with stack trace debugging."""
    import traceback
    print("[DEBUG START_PROGRESS CALLED BY:]")
    traceback.print_stack(limit=5)

    try:
        pc = getattr(state, "progress_container", None)
        pb = getattr(state, "progress_bar", None)

        if pc and pb:
            if not pc.winfo_ismapped():
                status_box = getattr(state, "status", None)
                if status_box and status_box.master:
                    pc.pack(side="bottom", fill="x", padx=6, pady=(2, 2), before=status_box.master)
                else:
                    pc.pack(side="bottom", fill="x", padx=6, pady=(2, 2))

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
    """Grows the red bar smoothly from left to right (value between 0.0 and 1.0)."""
    try:
        pb = getattr(state, "progress_bar", None)
        if pb:
            if pb.cget("mode") != "determinate":
                pb.configure(mode="determinate")

            pb.set(max(0.0, min(1.0, value)))

            master_root = pb.winfo_toplevel()
            if master_root:
                master_root.update_idletasks()
    except Exception as e:
        print(f"Progress Update Error: {e}")


def stop_progress():
    """Completes the bar to 1.0 briefly or resets it back to empty (0.0)."""
    try:
        pb = getattr(state, "progress_bar", None)
        if pb:
            pb.set(1.0)  # Fill completely on finish
            master_root = pb.winfo_toplevel()
            if master_root:
                master_root.update_idletasks()
    except Exception as e:
        print(f"Progress Stop Error: {e}")

def hide_progress():
    """Resets the progress bar to 0.0 and leaves it ready for the next task."""
    try:
        pb = getattr(state, "progress_bar", None)
        if pb:
            pb.set(0.0)
            master_root = pb.winfo_toplevel()
            if master_root:
                master_root.update_idletasks()
    except Exception as e:
        print(f"Progress Hide Error: {e}")