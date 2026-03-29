import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import threading


def detect_cameras(max_check=10):
    """Try opening camera indexes 0–max_check and return available ones."""
    cameras = []
    for i in range(max_check):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            cameras.append((i, f"Camera {i}"))
            cap.release()
    return cameras


class VideoSourcePicker:
    def __init__(self, parent, on_submit):
        self.on_submit = on_submit

        # --- Create popup window ---
        self.win = tk.Toplevel(parent)
        self.win.title("Select Video Source")
        self.win.geometry("320x160")
        self.win.resizable(False, False)
        self.win.grab_set()  # Block interaction with parent window

        # Center on screen
        self.win.update_idletasks()
        x = (self.win.winfo_screenwidth() // 2) - 160
        y = (self.win.winfo_screenheight() // 2) - 80
        self.win.geometry(f"+{x}+{y}")

        # --- Widgets ---
        tk.Label(self.win, text="Select a video source:", pady=8).pack()

        self.combo = ttk.Combobox(self.win, state="readonly", width=35)
        self.combo.pack(padx=20)
        self.combo.set("Scanning for cameras...")

        btn_frame = tk.Frame(self.win)
        btn_frame.pack(pady=12)

        self.submit_btn = tk.Button(
            btn_frame, text="Submit", width=10,
            command=self.submit, state="disabled"
        )
        self.submit_btn.pack(side="left", padx=6)

        tk.Button(
            btn_frame, text="Cancel", width=10,
            command=self.win.destroy
        ).pack(side="left", padx=6)

        # --- Detect cameras in background thread (avoids freezing UI) ---
        threading.Thread(target=self._load_cameras, daemon=True).start()

    def _load_cameras(self):
        cameras = detect_cameras()
        # Schedule UI update back on the main thread
        self.win.after(0, self._populate, cameras)

    def _populate(self, cameras):
        if not cameras:
            self.combo.set("No cameras found")
            return

        labels = [label for _, label in cameras]
        self.camera_ids = [idx for idx, _ in cameras]

        self.combo["values"] = labels
        self.combo.current(0)
        self.submit_btn.config(state="normal")

    def submit(self):
        selected_index = self.combo.current()
        if selected_index < 0:
            messagebox.showwarning("No Selection", "Please select a camera.")
            return

        camera_id = self.camera_ids[selected_index]
        camera_label = self.combo.get()

        self.win.destroy()  # Close the popup
        self.on_submit(camera_id, camera_label)  # Fire callback


# --- Main app ---
def on_source_selected(camera_id, label):
    print(f"Selected: {label} (index {camera_id})")

    # Example: open the stream with OpenCV
    cap = cv2.VideoCapture(camera_id)
    print(f"Stream opened: {cap.isOpened()}")

    # Show live feed until 'q' is pressed
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        cv2.imshow(f"Live - {label}", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()


def open_picker():
    VideoSourcePicker(root, on_submit=on_source_selected)


root = tk.Tk()
root.title("My App")
root.geometry("300x100")

tk.Button(root, text="Select Video Source", command=open_picker).pack(expand=True)

root.mainloop()