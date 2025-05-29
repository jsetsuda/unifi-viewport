#!/usr/bin/env python3
import os
import time
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAMERA_FILE = os.path.join(SCRIPT_DIR, "camera_urls.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "viewport_config.json")


def fetch_camera_list():
    try:
        result = subprocess.run(
            ["python3", "get_streams.py"],
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=True,
            text=True
        )
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"[WARN] get_streams.py failed:\n{e.output}")


def inject_metadata_into_config():
    try:
        with open(CAMERA_FILE, "r") as f:
            camera_list = json.load(f)
        camera_map = {cam["name"]: cam for cam in camera_list if "name" in cam}
    except Exception as e:
        print(f"[ERROR] Failed to load {CAMERA_FILE}: {e}")
        return

    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
        for tile in config.get("tiles", []):
            meta = camera_map.get(tile["name"])
            if meta:
                tile.update({k: meta[k] for k in ("width", "height", "fps", "codec_name", "pix_fmt", "profile") if k in meta})
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        print(f"[ERROR] Failed to update {CONFIG_FILE} with metadata: {e}")


# Fetch camera list
time.sleep(2)
fetch_camera_list()

# Load cameras
camera_map = {}
camera_names = []

try:
    with open(CAMERA_FILE, "r") as f:
        cameras = json.load(f)
    if not isinstance(cameras, list) or not cameras:
        raise ValueError("Camera list is empty.")
    camera_names = sorted([cam["name"] for cam in cameras])
    preferred = [name for name in camera_names if "(1920x1080)" in name or "(1280x720)" in name]
    camera_map = {cam["name"]: cam["url"] for cam in cameras if cam.get("url")}
except Exception as e:
    messagebox.showwarning("Camera Load Warning", f"Unable to load cameras:\n{e}")


class LayoutSelector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Viewport Layout Chooser")
        self.geometry("400x240")
        self.grid_size = tk.IntVar(value=2)

        tk.Label(self, text="Select grid size (NxN):").pack(pady=(10, 0))
        tk.Scale(self, from_=1, to=4, orient="horizontal", variable=self.grid_size).pack()

        tk.Button(self, text="Create New Layout", command=self.select_layout).pack(pady=10)

        self.has_valid_config = self.check_existing_config()

        if self.has_valid_config:
            tk.Button(self, text="Use Last Layout", command=self.use_last_layout).pack(pady=5)
            self.after(10000, self.prompt_for_default)

    def check_existing_config(self):
        try:
            if not os.path.isfile(CONFIG_FILE):
                return False
            with open(CONFIG_FILE) as f:
                data = json.load(f)
                return bool(data.get("tiles"))
        except Exception:
            return False

    def select_layout(self):
        self.withdraw()
        LayoutEditor(self.grid_size.get())

    def use_last_layout(self):
        self.withdraw()
        subprocess.Popen(
            ["./viewport.sh"],
            cwd=SCRIPT_DIR,
            stdout=open(os.path.join(SCRIPT_DIR, "viewport.log"), "a"),
            stderr=subprocess.STDOUT
        )

    def prompt_for_default(self):
        if self.winfo_exists() and self.has_valid_config:
            self.use_last_layout()


class LayoutEditor(tk.Tk):
    def __init__(self, size):
        super().__init__()
        self.title("Assign Cameras to Grid")
        self.size = size
        self.assignments = [[tk.StringVar() for _ in range(size)] for _ in range(size)]

        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)

        flat = preferred[:size * size] or camera_names[:size * size]
        for r in range(size):
            for c in range(size):
                var = self.assignments[r][c]
                index = r * size + c
                if index < len(flat):
                    var.set(flat[index])

                cell = tk.Frame(frame)
                cell.grid(row=r, column=c, padx=5, pady=5)

                cb = ttk.Combobox(cell, values=camera_names, textvariable=var, width=30)
                cb.pack(side=tk.LEFT)

                def on_select(event, var=var, cb=cb):
                    var.set(cb.get())
                cb.bind("<<ComboboxSelected>>", on_select)

                def preview(var=var):
                    name = var.get()
                    url = camera_map.get(name)
                    if url:
                        subprocess.Popen(["mpv", "--no-border", "--profile=low-latency", "--untimed", "--rtsp-transport=tcp", url])
                    else:
                        messagebox.showwarning("Preview Error", f"No valid stream for {name}")
                tk.Button(cell, text="🔍", command=preview, width=2).pack(side=tk.LEFT)

        tk.Button(self, text="Save Layout and Launch Viewer", command=self.save_config).pack(pady=10)

    def save_config(self):
        config = {
            "grid": [self.size, self.size],
            "tiles": []
        }

        for r in range(self.size):
            for c in range(self.size):
                name = self.assignments[r][c].get().strip()
                url = camera_map.get(name)
                if name and url:
                    config["tiles"].append({
                        "row": r,
                        "col": c,
                        "name": name,
                        "url": url
                    })

        if not config["tiles"]:
            messagebox.showerror("Error", "You must assign at least one camera.")
            return

        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{e}")
            return

        inject_metadata_into_config()

        messagebox.showinfo("Saved", "Layout saved. Launching viewer...")
        self.destroy()

        subprocess.Popen(
            ["./viewport.sh"],
            cwd=SCRIPT_DIR,
            stdout=open(os.path.join(SCRIPT_DIR, "viewport.log"), "a"),
            stderr=subprocess.STDOUT
        )


if __name__ == "__main__":
    LayoutSelector().mainloop()
