#!/usr/bin/env python3
"""
layout_chooser.py
Description: GUI for selecting and saving camera grid layouts for viewport.sh.
Writes a full configuration including 'grid' and 'tiles' directly (one-step approach).
Keeps the chooser open for 30 seconds and cancels auto-default on any user interaction.
"""
import os
os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

import time
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# --- Section: File paths and constants ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAMERA_FILE = os.path.join(SCRIPT_DIR, "camera_urls.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "viewport_config.json")
FLAG_FILE = os.path.join(SCRIPT_DIR, "layout_updated.flag")

# Time (ms) before auto-default uses last layout
AUTO_TIMEOUT_MS = 20000  # 20 seconds

# --- Section: Predefined custom layouts ---
CUSTOM_LAYOUTS = {
    "2x1": {
        "grid": [1, 2],
        "tiles": [
            {"row": 0, "col": 0, "w": 1, "h": 1},
            {"row": 0, "col": 1, "w": 1, "h": 1}
        ]
    },
    "3_custom": {
        "grid": [2, 2],
        "tiles": [
            {"row": 0, "col": 0, "w": 1, "h": 2},
            {"row": 0, "col": 1, "w": 1, "h": 1},
            {"row": 1, "col": 1, "w": 1, "h": 1}
        ]
    },
    "5_custom": {
        "grid": [2, 3],
        "tiles": [
            {"row": 0, "col": 0, "w": 2, "h": 2},
            {"row": 0, "col": 1, "w": 1, "h": 1},
            {"row": 1, "col": 1, "w": 1, "h": 1},
            {"row": 0, "col": 2, "w": 1, "h": 1},
            {"row": 1, "col": 2, "w": 1, "h": 1}
        ]
    },
    "6_custom": {
        "grid": [3, 3],
        "tiles": [
            {"row": 0, "col": 0, "w": 2, "h": 2},
            {"row": 0, "col": 2, "w": 1, "h": 1},
            {"row": 1, "col": 2, "w": 1, "h": 1},
            {"row": 2, "col": 0, "w": 1, "h": 1},
            {"row": 2, "col": 1, "w": 1, "h": 1},
            {"row": 2, "col": 2, "w": 1, "h": 1}
        ]
    }
}

# --- Section: Camera loading and metadata injection ---
def fetch_camera_list():
    """Fetch the camera list by running get_streams.py and writing to CAMERA_FILE."""
    try:
        result = subprocess.run(
            ["python3", os.path.join(SCRIPT_DIR, "get_streams.py"), "--list"],
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
            text=True
        )
        with open(CAMERA_FILE, "w") as f:
            f.write(result.stdout)
    except subprocess.CalledProcessError as e:
        messagebox.showwarning("Camera Fetch Warning", f"Failed to fetch cameras:\n{e.output}")
    except Exception as e:
        messagebox.showwarning("Camera Fetch Error", f"Unexpected error fetching cameras:\n{e}")


def inject_metadata_into_config():
    """Inject additional camera metadata into the saved config's tiles."""
    try:
        with open(CAMERA_FILE, "r") as f:
            camera_list = json.load(f)
        camera_map = {cam["name"]: cam for cam in camera_list if "name" in cam}
    except Exception as e:
        messagebox.showerror("Metadata Error", f"Failed to load {CAMERA_FILE}: {e}")
        return

    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        for tile in config.get("tiles", []):
            meta = camera_map.get(tile.get("name", ""), {})
            for key in ("width", "height", "fps", "codec_name", "pix_fmt", "profile"):  # example keys
                if key in meta:
                    tile[key] = meta[key]
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        messagebox.showerror("Metadata Error", f"Failed to update {CONFIG_FILE}: {e}")

# --- Load camera list for dropdown ---
time.sleep(1)
fetch_camera_list()

camera_map = {}
camera_names = []
preferred = []
try:
    with open(CAMERA_FILE, "r") as f:
        cams = json.load(f)
    camera_names = sorted([c["name"] for c in cams if "name" in c])
    preferred = [n for n in camera_names if any(res in n for res in ["1920x1080", "1280x720"])]
    camera_map = {c["name"]: c.get("url", "") for c in cams}
except Exception as e:
    messagebox.showwarning("Camera Load Warning", f"Unable to load cameras:\n{e}")

# --- Main GUI for layout selection ---
class LayoutSelector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Viewport Layout Chooser")
        self.geometry("400x300")
        self.has_valid_config = self.check_existing_config()
        self.after_id = None

        tk.Button(self, text="New Grid Layout", command=self.new_grid_layout).pack(pady=5)
        tk.Button(self, text="New Custom Layout", command=self.new_custom_layout).pack(pady=5)
        if self.has_valid_config:
            tk.Button(self, text="Use Last Layout", command=self.use_last_layout).pack(pady=5)
            # schedule auto-default after timeout
            self.after_id = self.after(AUTO_TIMEOUT_MS, self.use_last_layout)
            # cancel on any user interaction
            self.bind_all("<Button>", self.cancel_auto_default)
            self.bind_all("<Key>", self.cancel_auto_default)

    def cancel_auto_default(self, event=None):
        if self.after_id:
            self.after_cancel(self.after_id)
            self.after_id = None

    def check_existing_config(self):
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            return bool(data.get("tiles"))
        except Exception:
            return False

    def new_grid_layout(self):
        self.withdraw()
        LayoutEditor(self)

    def new_custom_layout(self):
        self.withdraw()
        CustomLayoutEditor(self)

    def use_last_layout(self):
        try:
            with open(FLAG_FILE, "w") as f:
                f.write("updated")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set flag:\n{e}")
        self.destroy()

# --- Editor for N×N grid ---
class LayoutEditor(tk.Toplevel):
    def __init__(self, parent, size=2):
        super().__init__(parent)
        self.parent = parent
        self.size = size
        self.title(f"Assign Cameras {size}×{size}")
        self.assignments = [[tk.StringVar() for _ in range(size)] for _ in range(size)]

        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)

        options = preferred[:size*size] or camera_names[:size*size]
        for r in range(size):
            for c in range(size):
                var = self.assignments[r][c]
                idx = r*size + c
                if idx < len(options): var.set(options[idx])
                cell = tk.Frame(frame)
                cell.grid(row=r, column=c, padx=5, pady=5)
                cb = ttk.Combobox(cell, values=camera_names, textvariable=var, width=25)
                cb.pack(side=tk.LEFT)
                tk.Button(cell, text="🔍", command=lambda v=var: self.preview(v), width=2).pack(side=tk.LEFT)

        tk.Button(self, text="Save Layout", command=self.save_config).pack(pady=10)

    def preview(self, var):
        url = camera_map.get(var.get(), "")
        if url:
            subprocess.Popen(["mpv", "--no-border", "--profile=low-latency", "--untimed", "--rtsp-transport=tcp", url])
        else:
            messagebox.showwarning("Preview Error", "No valid stream for selected camera.")

    def save_config(self):
        config = {"grid": [self.size, self.size], "tiles": []}
        for r in range(self.size):
            for c in range(self.size):
                name = self.assignments[r][c].get().strip()
                url = camera_map.get(name, "")
                if name and url:
                    config["tiles"].append({"row": r, "col": c, "name": name, "url": url})
        if not config["tiles"]:
            messagebox.showerror("Error", "You must assign at least one camera.")
            return
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
                f.flush(); os.fsync(f.fileno())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{e}")
            return
        inject_metadata_into_config()
        with open(FLAG_FILE, "w") as f:
            f.write("updated")
        messagebox.showinfo("Saved", "Layout saved.")
        self.parent.destroy()

# --- Editor for predefined custom layouts ---
class CustomLayoutEditor(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Custom Layout Assignment")
        self.layout_name = None
        self.var = tk.StringVar()
        menu = ttk.Combobox(self, values=list(CUSTOM_LAYOUTS.keys()), textvariable=self.var, state="readonly")
        menu.pack(pady=10)
        tk.Button(self, text="Select Layout", command=self.build_editor).pack(pady=5)

    def build_editor(self):
        self.layout_name = self.var.get()
        if not self.layout_name:
            messagebox.showerror("Error", "Pick a custom layout.")
            return
        layout = CUSTOM_LAYOUTS[self.layout_name]
        self.assignments = []
        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)
        for idx, tile in enumerate(layout["tiles"]):
            var = tk.StringVar(value=preferred[idx] if idx < len(preferred) else "")
            self.assignments.append(var)
            cell = tk.Frame(frame)
            cell.grid(row=idx, column=0, padx=5, pady=5)
            cb = ttk.Combobox(cell, values=camera_names, textvariable=var, width=30)
            cb.pack(side=tk.LEFT)
            tk.Button(cell, text="🔍", command=lambda v=var: self.preview(v), width=2).pack(side=tk.LEFT)
        tk.Button(self, text="Save Layout", command=self.save_config).pack(pady=10)

    def preview(self, var):
        url = camera_map.get(var.get(), "")
        if url:
            subprocess.Popen(["mpv", "--no-border", "--profile=low-latency", "--untimed", "--rtsp-transport=tcp", url])
        else:
            messagebox.showwarning("Preview Error", "No valid stream for selected camera.")

    def save_config(self):
        layout = CUSTOM_LAYOUTS[self.layout_name]
        config = {"grid": layout["grid"], "tiles": []}
        for tile, var in zip(layout["tiles"], self.assignments):
            name = var.get().strip()
            url = camera_map.get(name, "")
            if name and url:
                config["tiles"].append({**tile, "name": name, "url": url})
        if not config["tiles"]:
            messagebox.showerror("Error", "Assign at least one camera.")
            return
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
                f.flush(); os.fsync(f.fileno())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{e}")
            return
        inject_metadata_into_config()
        with open(FLAG_FILE, "w") as f:
            f.write("updated")
        messagebox.showinfo("Saved", "Layout saved.")
        self.parent.destroy()

# --- Entry point ---
if __name__ == "__main__":
    LayoutSelector().mainloop()
