#!/usr/bin/env python3

import os
import time
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

CAMERA_FILE = "camera_urls.json"
CONFIG_FILE = "viewport_config.json"

# === Fetch latest camera list ===
time.sleep(2)
try:
    subprocess.run(["python3", "get_streams.py"], cwd="/home/viewport/unifi-viewport", check=True)
except Exception as e:
    messagebox.showerror("Error", f"Failed to fetch camera list:\n{e}")
    exit(1)

# === Load camera list ===
try:
    with open(CAMERA_FILE) as f:
        cameras = json.load(f)

    if not isinstance(cameras, list) or not cameras:
        raise ValueError("No valid cameras found.")

    camera_names = [cam["name"] for cam in cameras]
    camera_map = {cam["name"]: cam["url"] for cam in cameras if cam["url"] != "None"}

except Exception as e:
    messagebox.showerror("Camera Error", f"Unable to load cameras:\n{e}")
    exit(1)

# === Layout Selector UI ===
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
            self.after(10000, self.prompt_for_default)  # 10s auto fallback prompt

    def check_existing_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE) as f:
                    cfg = json.load(f)
                return isinstance(cfg, dict) and "grid" in cfg and "tiles" in cfg
        except:
            return False
        return False

    def select_layout(self):
        self.withdraw()
        LayoutEditor(self.grid_size.get())

    def use_last_layout(self):
        self.withdraw()
        subprocess.Popen(
            ["./viewport.sh"],
            cwd="/home/viewport/unifi-viewport",
            stdout=open("/home/viewport/unifi-viewport/viewport.log", "a"),
            stderr=subprocess.STDOUT
        )

    def prompt_for_default(self):
        if self.winfo_exists() and self.has_valid_config:
            use_last = messagebox.askyesno(
                "Load Saved Layout?",
                "Would you like to automatically load your last saved layout?"
            )
            if use_last:
                self.use_last_layout()

# === Camera Grid Assignment UI ===
class LayoutEditor(tk.Tk):
    def __init__(self, size):
        super().__init__()
        self.title("Assign Cameras to Grid")
        self.size = size
        self.assignments = [[tk.StringVar() for _ in range(size)] for _ in range(size)]

        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)

        flat = camera_names[:size * size]
        for r in range(size):
            for c in range(size):
                var = self.assignments[r][c]
                index = r * size + c
                if index < len(flat):
                    var.set(flat[index])

                cell = tk.Frame(frame)
                cell.grid(row=r, column=c, padx=5, pady=5)

                cb = ttk.Combobox(cell, values=camera_names, textvariable=var, width=20)
                cb.pack(side=tk.LEFT)

                def on_select(event, var=var, cb=cb):
                    var.set(cb.get())
                cb.bind("<<ComboboxSelected>>", on_select)

                def preview(var=var):
                    name = var.get()
                    url = camera_map.get(name)
                    if url:
                        subprocess.Popen([
                            "mpv", "--no-border", "--profile=low-latency",
                            "--untimed", "--rtsp-transport=tcp", url
                        ])
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

        messagebox.showinfo("Saved", "Layout saved. Launching viewer...")
        self.destroy()

        subprocess.Popen(
            ["./viewport.sh"],
            cwd="/home/viewport/unifi-viewport",
            stdout=open("/home/viewport/unifi-viewport/viewport.log", "a"),
            stderr=subprocess.STDOUT
        )

# === Run the app ===
if __name__ == "__main__":
    LayoutSelector().mainloop()
