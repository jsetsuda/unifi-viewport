#!/usr/bin/env python3
"""
layout_chooser.py

Two-step GUI:
 1) choose grid size
 2) assign cameras to each tile
"""

import os
import json
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

SCRIPT_DIR    = os.path.dirname(os.path.abspath(__file__))
CAMERA_FILE   = os.path.join(SCRIPT_DIR, "camera_urls.json")
CONFIG_FILE   = os.path.join(SCRIPT_DIR, "viewport_config.json")
FLAG_FILE     = os.path.join(SCRIPT_DIR, "layout_updated.flag")
GET_STREAMS   = os.path.join(SCRIPT_DIR, "get_streams.py")

CUSTOM_LAYOUTS = {
    "2x1": {
        "grid": [1, 2],
        "tiles": [
            {"row": 0, "col": 0, "w": 1, "h": 1},
            {"row": 0, "col": 1, "w": 1, "h": 1},
        ]
    },
    "3_custom": {
        "grid": [2, 2],
        "tiles": [
            {"row": 0, "col": 0, "w": 1, "h": 2},
            {"row": 0, "col": 1, "w": 1, "h": 1},
            {"row": 1, "col": 1, "w": 1, "h": 1},
        ]
    },
    "5_custom": {
        "grid": [2, 3],
        "tiles": [
            {"row": 0, "col": 0, "w": 2, "h": 2},
            {"row": 0, "col": 1, "w": 1, "h": 1},
            {"row": 1, "col": 1, "w": 1, "h": 1},
            {"row": 0, "col": 2, "w": 1, "h": 1},
            {"row": 1, "col": 2, "w": 1, "h": 1},
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
            {"row": 2, "col": 2, "w": 1, "h": 1},
        ]
    },
}


def fetch_camera_list():
    """Populate camera_urls.json via get_streams.py"""
    try:
        subprocess.run(
            ["python3", GET_STREAMS, "--list"],
            cwd=SCRIPT_DIR,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        messagebox.showwarning("Camera Fetch Warning", "Could not fetch camera list.")


def load_cameras():
    """Return (names, url_map)"""
    try:
        with open(CAMERA_FILE) as f:
            cams = json.load(f)
    except:
        return [], {}
    names = sorted(c["name"] for c in cams if "name" in c)
    url_map = {c["name"]: c.get("url","") for c in cams}
    return names, url_map


class LayoutChooser(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Viewport Layout Chooser")
        self.geometry("800x600")
        self.resizable(False, False)

        # load cameras once
        fetch_camera_list()
        self.cam_names, self.cam_urls = load_cameras()

        # step1 UI
        self.frame1 = tk.Frame(self)
        tk.Label(self.frame1, text="Step 1: Select layout", font=("Arial",14)).pack(pady=20)
        self.choice = tk.StringVar()
        opts = ["1x1","2x1","2x2","3x3"] + list(CUSTOM_LAYOUTS.keys())
        self.menu = ttk.Combobox(self.frame1, values=opts, textvariable=self.choice,
                                 state="readonly", font=("Arial",12), width=20)
        self.menu.pack(pady=10)
        tk.Button(self.frame1, text="Next →", command=self._on_next, width=20).pack(pady=30)
        self.frame1.pack(fill="both", expand=True)

        # placeholder for step2
        self.frame2 = None
        self.current_cfg = {}

    def _on_next(self):
        sel = self.choice.get()
        if not sel:
            messagebox.showerror("Error", "Please choose a layout.")
            return

        # build base config (no names/urls yet)
        if sel in CUSTOM_LAYOUTS:
            cfg = {
                "grid": CUSTOM_LAYOUTS[sel]["grid"][:],
                "tiles": [t.copy() for t in CUSTOM_LAYOUTS[sel]["tiles"]]
            }
        else:
            r, c = map(int, sel.split("x"))
            cfg = {"grid": [r, c], "tiles": []}
            for idx in range(r*c):
                cfg["tiles"].append({
                    "row": idx//c,
                    "col": idx%c,
                    "w": 1, "h": 1
                })
        self.current_cfg = cfg

        # go to step2
        self.frame1.pack_forget()
        self._show_camera_assignment()

    def _show_camera_assignment(self):
        self.frame2 = tk.Frame(self)
        tk.Label(self.frame2, text="Step 2: Assign cameras", font=("Arial",14)).pack(pady=10)

        grid_frame = tk.Frame(self.frame2)
        grid_frame.pack(pady=10)

        self.sel_vars = []
        for tile in self.current_cfg["tiles"]:
            r, c = tile["row"], tile["col"]
            lbl = tk.Label(grid_frame, text=f"Tile {r},{c}")
            lbl.grid(row=r, column=c*2, padx=5, pady=5, sticky="e")
            var = tk.StringVar()
            cb = ttk.Combobox(grid_frame, values=self.cam_names, textvariable=var,
                              state="readonly", width=20)
            cb.grid(row=r, column=c*2+1, padx=5, pady=5, sticky="w")
            self.sel_vars.append((var, tile))

        tk.Button(self.frame2, text="← Back", command=self._go_back, width=12).pack(side="left", padx=30, pady=20)
        tk.Button(self.frame2, text="Save & Launch", command=self._on_save, width=16).pack(side="right", padx=30, pady=20)

        self.frame2.pack(fill="both", expand=True)

    def _go_back(self):
        self.frame2.pack_forget()
        self.frame1.pack(fill="both", expand=True)

    def _on_save(self):
        # collect selections
        for var, tile in self.sel_vars:
            name = var.get()
            if not name:
                messagebox.showerror("Error", "Every tile needs a camera.")
                return
            tile["name"] = name
            tile["url"]  = self.cam_urls.get(name, "")

        # write config
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.current_cfg, f, indent=2)
        except Exception as e:
            messagebox.showerror("Error", f"Could not write config:\n{e}")
            return

        # touch flag
        open(FLAG_FILE, "w").write("updated")

        messagebox.showinfo("Saved", "Configuration saved!\nLaunching streams…")
        self.destroy()


if __name__ == "__main__":
    LayoutChooser().mainloop()
