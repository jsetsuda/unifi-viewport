#!/usr/bin/env python3
"""
layout_chooser.py
Description: GUI for selecting and saving camera grid layouts for viewport.sh.
Fetch is deferred until user explicitly requests a new layout; all fetch errors are logged silently.
"""
import os
import subprocess
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox

# --- Section: File paths and logging ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAMERA_FILE = os.path.join(SCRIPT_DIR, "camera_urls.json")
CONFIG_FILE = os.path.join(SCRIPT_DIR, "viewport_config.json")
FLAG_FILE = os.path.join(SCRIPT_DIR, "layout_updated.flag")

LOG_FILE = os.path.join(SCRIPT_DIR, "viewport.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='[CHOOSER %(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# --- Section: Predefined Custom Layouts ---
CUSTOM_LAYOUTS = {
    "2x1": {"grid": [1, 2], "tiles": [
        {"row": 0, "col": 0, "w": 1, "h": 1},
        {"row": 0, "col": 1, "w": 1, "h": 1}
    ]},
    "3_custom": {"grid": [2, 2], "tiles": [
        {"row": 0, "col": 0, "w": 1, "h": 2},
        {"row": 0, "col": 1, "w": 1, "h": 1},
        {"row": 1, "col": 1, "w": 1, "h": 1}
    ]},
    "5_custom": {"grid": [2, 3], "tiles": [
        {"row": 0, "col": 0, "w": 2, "h": 2},
        {"row": 0, "col": 1, "w": 1, "h": 1},
        {"row": 1, "col": 1, "w": 1, "h": 1},
        {"row": 0, "col": 2, "w": 1, "h": 1},
        {"row": 1, "col": 2, "w": 1, "h": 1}
    ]},
    "6_custom": {"grid": [3, 3], "tiles": [
        {"row": 0, "col": 0, "w": 2, "h": 2},
        {"row": 0, "col": 2, "w": 1, "h": 1},
        {"row": 1, "col": 2, "w": 1, "h": 1},
        {"row": 2, "col": 0, "w": 1, "h": 1},
        {"row": 2, "col": 1, "w": 1, "h": 1},
        {"row": 2, "col": 2, "w": 1, "h": 1}
    ]}
}

# --- Section: Camera loading (deferred) ---
def fetch_camera_list():
    """Fetch camera list via get_streams.py, logging any errors silently."""
    try:
        subprocess.run(
            ["python3", os.path.join(SCRIPT_DIR, "get_streams.py")],
            cwd=SCRIPT_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
            text=True
        )
    except subprocess.CalledProcessError as e:
        logging.warning(f"get_streams.py failed (exit {e.returncode}): {e.stderr.strip()}")
    except OSError as e:
        logging.warning(f"get_streams.py OS error: {e}")

# --- Section: Metadata injection ---
def inject_metadata_into_config():
    try:
        with open(CAMERA_FILE) as f:
            camera_list = json.load(f)
        camera_map = {cam["name"]: cam for cam in camera_list if "name" in cam}
    except Exception as e:
        logging.error(f"Failed to load {CAMERA_FILE}: {e}")
        return

    try:
        with open(CONFIG_FILE) as f:
            config = json.load(f)
        for tile in config.get("tiles", []):
            meta = camera_map.get(tile.get("name", ""), {})
            for key in ("width","height","fps","codec_name","pix_fmt","profile"):  # optional
                if key in meta:
                    tile[key] = meta[key]
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logging.error(f"Failed to update {CONFIG_FILE} with metadata: {e}")

# --- Section: Main GUI ---
class LayoutSelector(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Viewport Layout Chooser")
        self.geometry("400x300")
        self.grid_size = tk.IntVar(value=2)
        self.custom_layout = tk.StringVar()

        tk.Label(self, text="Select grid size (NxN):").pack(pady=(10,0))
        tk.Scale(self, from_=1, to=4, orient="horizontal", variable=self.grid_size).pack()
        tk.Button(self, text="New Grid Layout", command=self.new_grid_layout).pack(pady=5)

        tk.Label(self, text="Or choose custom layout:").pack(pady=(10,0))
        self.custom_menu = ttk.Combobox(
            self, textvariable=self.custom_layout,
            values=list(CUSTOM_LAYOUTS.keys()), state="readonly"
        )
        self.custom_menu.pack()
        tk.Button(self, text="New Custom Layout", command=self.new_custom_layout).pack(pady=5)

        # If there is already a valid config, offer to reuse it
        if self.check_existing_config():
            tk.Button(self, text="Use Last Layout", command=self.use_last_layout).pack(pady=5)
            self.after(10000, self.use_last_layout)

    def check_existing_config(self):
        try:
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            return bool(data.get("tiles"))
        except Exception:
            return False

    def new_grid_layout(self):
        fetch_camera_list()
        self.withdraw()
        LayoutEditor(self, size=self.grid_size.get())

    def new_custom_layout(self):
        fetch_camera_list()
        self.withdraw()
        CustomLayoutEditor(self)

    def use_last_layout(self):
        try:
            with open(FLAG_FILE, 'w') as f:
                f.write('updated')
        except Exception as e:
            messagebox.showerror("Error", f"Failed to set flag:\n{e}")
        self.destroy()

# --- Section: Grid Editor ---
class LayoutEditor(tk.Toplevel):
    def __init__(self, parent, size=2):
        super().__init__(parent)
        self.parent = parent
        self.size = size
        self.title(f"Assign Cameras {size}×{size}")
        self.assignments = [[tk.StringVar() for _ in range(size)] for _ in range(size)]

        # Load cameras for dropdowns
        try:
            with open(CAMERA_FILE) as f:
                cams = json.load(f)
            names = sorted(cam['name'] for cam in cams if 'name' in cam)
            preferred = [n for n in names if any(r in n for r in ['1920x1080','1280x720'])]
            options = preferred[:size*size] or names[:size*size]
        except Exception:
            options = []
            names = []

        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)
        for r in range(size):
            for c in range(size):
                var = self.assignments[r][c]
                idx = r*size + c
                if idx < len(options): var.set(options[idx])
                cell = tk.Frame(frame)
                cell.grid(row=r, column=c, padx=5, pady=5)
                cb = ttk.Combobox(cell, values=names, textvariable=var, width=25)
                cb.pack(side=tk.LEFT)
                tk.Button(cell, text="🔍", command=lambda v=var: self.preview(v), width=2).pack(side=tk.LEFT)

        tk.Button(self, text="Save Layout", command=self.save_config).pack(pady=10)

    def preview(self, var):
        url = json.load(open(CAMERA_FILE)).get(var.get(), '')
        if url:
            subprocess.Popen(["mpv","--no-border","--profile=low-latency","--untimed","--rtsp-transport=tcp", url])
        else:
            messagebox.showwarning("Preview Error", "No valid stream for selected camera.")

    def save_config(self):
        cfg = {"grid":[self.size, self.size], "tiles": []}
        for r in range(self.size):
            for c in range(self.size):
                name = self.assignments[r][c].get().strip()
                # reload map
                with open(CAMERA_FILE) as f:
                    camera_map = {cam['name']: cam['url'] for cam in json.load(f)}
                url = camera_map.get(name, '')
                if name and url:
                    cfg['tiles'].append({"row":r, "col":c, "name":name, "url":url})

        if not cfg['tiles']:
            messagebox.showerror("Error","You must assign at least one camera.")
            return
        try:
            with open(CONFIG_FILE,'w') as f:
                json.dump(cfg, f, indent=2)
                f.flush(); os.fsync(f.fileno())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{e}")
            return
        inject_metadata_into_config()
        with open(FLAG_FILE,'w') as f: f.write('updated')
        messagebox.showinfo("Saved","Layout saved.")
        self.parent.destroy()

# --- Section: Custom Layout Editor ---
class CustomLayoutEditor(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Select Custom Layout")
        self.var = tk.StringVar()
        ttk.Combobox(self, values=list(CUSTOM_LAYOUTS.keys()), textvariable=self.var, state="readonly").pack(pady=10)
        tk.Button(self, text="Select", command=self.build_editor).pack(pady=5)

    def build_editor(self):
        layout_name = self.var.get()
        if not layout_name:
            messagebox.showerror("Error","Pick a custom layout.")
            return
        layout = CUSTOM_LAYOUTS[layout_name]
        self.geometry("")
        self.assignments = []
        frame = tk.Frame(self)
        frame.pack(padx=10, pady=10)
        for idx, tile in enumerate(layout['tiles']):
            var = tk.StringVar()
            self.assignments.append(var)
            cell = tk.Frame(frame)
            cell.grid(row=idx, column=0, padx=5, pady=5)
            cb = ttk.Combobox(cell, values=list(json.load(open(CAMERA_FILE))[0].keys()), textvariable=var, width=30)
            cb.pack(side=tk.LEFT)
            tk.Button(cell, text="🔍", command=lambda v=var: self.preview(v), width=2).pack(side=tk.LEFT)
        tk.Button(self, text="Save Layout", command=lambda: self.save_config(layout_name)).pack(pady=10)

    def preview(self, var):
        url = json.load(open(CAMERA_FILE)).get(var.get(), '')
        if url:
            subprocess.Popen(["mpv","--no-border","--profile=low-latency","--untimed","--rtsp-transport=tcp", url])
        else:
            messagebox.showwarning("Preview Error","No valid stream for selected camera.")

    def save_config(self, name):
        layout = CUSTOM_LAYOUTS[name]
        cfg = {"grid": layout["grid"], "tiles": []}
        camera_map = {cam['name']: cam['url'] for cam in json.load(open(CAMERA_FILE))}
        for tile, var in zip(layout['tiles'], self.assignments):
            nm = var.get().strip()
            url = camera_map.get(nm, '')
            if nm and url:
                cfg['tiles'].append({**tile, 'name': nm, 'url': url})
        if not cfg['tiles']:
            messagebox.showerror("Error","Assign at least one camera.")
            return
        try:
            with open(CONFIG_FILE,'w') as f:
                json.dump(cfg, f, indent=2)
                f.flush(); os.fsync(f.fileno())
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{e}")
            return
        inject_metadata_into_config()
        with open(FLAG_FILE,'w') as f: f.write('updated')
        messagebox.showinfo("Saved","Layout saved.")
        self.parent.destroy()

# --- Entry Point ---
if __name__ == '__main__':
    LayoutSelector().mainloop()
