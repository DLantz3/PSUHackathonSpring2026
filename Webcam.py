import tkinter as tk
from tkinter import ttk
import cv2
import threading
import os
import subprocess
import sys
from PIL import Image, ImageTk
from datetime import datetime


def detect_cameras(max_check=10):
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

        self.win = tk.Toplevel(parent)
        self.win.title("Select Video Source")
        self.win.geometry("320x160")
        self.win.resizable(False, False)
        self.win.grab_set()

        self.win.update_idletasks()
        x = (self.win.winfo_screenwidth() // 2) - 160
        y = (self.win.winfo_screenheight() // 2) - 80
        self.win.geometry(f"+{x}+{y}")

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

        tk.Button(btn_frame, text="Cancel", width=10,
                  command=self.win.destroy).pack(side="left", padx=6)

        threading.Thread(target=self._load_cameras, daemon=True).start()

    def _load_cameras(self):
        cameras = detect_cameras()
        self.win.after(0, self._populate, cameras)

    def _populate(self, cameras):
        if not cameras:
            self.combo.set("No cameras found")
            return
        self.camera_ids = [idx for idx, _ in cameras]
        self.combo["values"] = [label for _, label in cameras]
        self.combo.current(0)
        self.submit_btn.config(state="normal")

    def submit(self):
        i = self.combo.current()
        if i < 0:
            return
        cam_id = self.camera_ids[i]
        label  = self.combo.get()
        self.win.destroy()
        self.on_submit(cam_id, label)


class LiveViewer:
    # Max usable area on a 1920×1080 monitor (leaves room for taskbar/title bar)
    MAX_W = 1880
    MAX_H = 980
    BTN_H = 60      # height reserved for the button bar below the video

    def __init__(self, parent, camera_id, label):
        self.camera_id  = camera_id
        self.running    = True
        self.last_frame = None

        # ── Open camera and read its native resolution ──────────────────────
        self.cap = cv2.VideoCapture(camera_id)

        cam_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        cam_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if cam_w == 0 or cam_h == 0:
            cam_w, cam_h = 1280, 720    # safe fallback

        # ── Scale to fit MAX_W × (MAX_H - BTN_H) while keeping aspect ratio ─
        video_max_h = self.MAX_H - self.BTN_H
        scale       = min(self.MAX_W / cam_w, video_max_h / cam_h, 1.0)  # never upscale
        self.disp_w = int(cam_w * scale)
        self.disp_h = int(cam_h * scale)

        # ── Window ──────────────────────────────────────────────────────────
        self.win = tk.Toplevel(parent)
        self.win.title(f"Live – {label}  ({self.disp_w}×{self.disp_h})")
        self.win.resizable(False, False)
        self.win.protocol("WM_DELETE_WINDOW", self.on_close)

        # Centre window on screen
        win_h = self.disp_h + self.BTN_H
        sx    = (self.win.winfo_screenwidth()  - self.disp_w) // 2
        sy    = (self.win.winfo_screenheight() - win_h)       // 2
        self.win.geometry(f"{self.disp_w}x{win_h}+{sx}+{sy}")

        # ── Video canvas (exact camera aspect ratio) ─────────────────────────
        self.canvas = tk.Label(self.win, bg="black",
                               width=self.disp_w, height=self.disp_h)
        self.canvas.pack()

        # ── Button bar (fixed BTN_H pixels tall) ────────────────────────────
        ctrl = tk.Frame(self.win, height=self.BTN_H, bg="#1a1a2e")
        ctrl.pack(fill="x")
        ctrl.pack_propagate(False)      # hold the fixed height

        self.snap_btn = tk.Button(
            ctrl, text="📷  Take Picture",
            font=("Arial", 11, "bold"),
            bg="#2ecc71", fg="white",
            relief="flat", padx=12, pady=6,
            command=self.take_picture
        )
        self.snap_btn.pack(side="left", padx=14, pady=10)

        # Download links sit to the right of the button, scrolling if needed
        self.links_frame = tk.Frame(ctrl, bg="#1a1a2e")
        self.links_frame.pack(side="left", fill="both", expand=True)

        self._update()

    # ── Video loop ────────────────────────────────────────────────────────────

    def _update(self):
        if not self.running:
            return

        ret, frame = self.cap.read()
        if ret:
            frame = cv2.flip(frame, 1)
            self.last_frame = frame.copy()

            display = cv2.resize(frame, (self.disp_w, self.disp_h),
                                 interpolation=cv2.INTER_LINEAR)

            h, w  = display.shape[:2]
            box_s = h                           # square side = full height
            x1    = (w - box_s) // 2
            cv2.rectangle(display, (x1, 0), (x1 + box_s, h), (0, 255, 0), 2)

            img   = Image.fromarray(cv2.cvtColor(display, cv2.COLOR_BGR2RGB))
            photo = ImageTk.PhotoImage(image=img)
            self.canvas.config(image=photo)
            self.canvas.image = photo

        self.win.after(15, self._update)

    # ── Snapshot ──────────────────────────────────────────────────────────────

    def take_picture(self):
        if self.last_frame is None:
            return

        frame = self.last_frame             # full native resolution
        h, w  = frame.shape[:2]
        box_s = h
        x1    = (w - box_s) // 2
        crop  = frame[0:h, x1:x1 + box_s]  # crop from original, not scaled

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename  = f"snapshot_{timestamp}.png"
        filepath  = os.path.abspath(filename)
        cv2.imwrite(filepath, crop)

        self._add_download_link(filepath, filename)

    # ── Download link ─────────────────────────────────────────────────────────

    def _add_download_link(self, filepath, filename):
        row = tk.Frame(self.links_frame, bg="#1a1a2e")
        row.pack(side="left", padx=6)

        tk.Label(row, text="✅", bg="#1a1a2e",
                 font=("Arial", 10)).pack(side="left")

        link = tk.Label(row, text=filename, fg="#5dade2", bg="#1a1a2e",
                        cursor="hand2", font=("Arial", 9, "underline"))
        link.pack(side="left", padx=2)
        link.bind("<Button-1>", lambda e, p=filepath: self._open_file(p))

        tk.Button(row, text="📁", relief="flat", bg="#1a1a2e",
                  font=("Arial", 9),
                  command=lambda p=filepath: self._open_folder(p)).pack(side="left")

    @staticmethod
    def _open_file(path):
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    @staticmethod
    def _open_folder(path):
        folder = os.path.dirname(path)
        if sys.platform == "win32":
            subprocess.Popen(["explorer", "/select,", path])
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-R", path])
        else:
            subprocess.Popen(["xdg-open", folder])

    def on_close(self):
        self.running = False
        self.cap.release()
        self.win.destroy()


def open_picker():
    VideoSourcePicker(root, on_submit=lambda cid, lbl: LiveViewer(root, cid, lbl))


root = tk.Tk()
root.title("Camera App")
root.geometry("260x80")

tk.Button(root, text="Select Video Source",
          font=("Arial", 11), command=open_picker).pack(expand=True)

root.mainloop()