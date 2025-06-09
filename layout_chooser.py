#!/usr/bin/env python3
"""
layout_chooser.py

Two-step GUI:
 1) choose a layout
 2) assign cameras to each tile

On any user interaction (dropdown selection), writes layout_updated.flag,
so the killer loop in viewport.sh will back off.
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

SIMPLE_LAYOUTS = ["1x1", "2x1", "2x2", "3x3"]
ALL_OPTIONS    = SIMPLE_LAYOUTS + list(CUSTOM_LAYOUTS.keys())

def signal_interaction():
    """Touch the flag file so viewport.sh stops killing our window."""
    try:
        open(FLAG_FILE, "w").close()
    except:
        pass

def fetch_camera_list():
    """Populate camera_urls.json via get_streams.py"""
    try:
        subprocess.run(
            ["python3", GET_STREAMS, "--list"],
            cwd=SCRIPT_DIR, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        # Startup fetch may fail; we'll warn if needed later
        pass

def load_cameras():
    """Return (names, url_map)"""
    if not os.path.isfile(CAMERA_FILE):
        return [], {}
    try:
        cams = json.load(open(CAMERA_FILE))
        names = sorted(c["name"] for c in cams if "name" in c)
        urls  = {c["name"]: c.get("url","") for c in cams}
        return names, urls
    except:
        return [], {}

class LayoutChooser(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Viewport Layout Chooser")
        self.geometry("800x600")
        self.resizable(False, False)

        # Load cameras (deferred fetch)
        fetch_camera_list()
        self.cam_names, self.cam_urls = load_cameras()

        # Step 1 UI
        self.frame1 = tk.Frame(self)
        tk.Label(self.frame1, text="Step 1: Select layout", font=("Arial",14)).pack(pady=20)

        self.choice = tk.StringVar()
        cmb = ttk.Combobox(
            self.frame1, values=ALL_OPTIONS,
            textvariable=self.choice, state="readonly",
            font=("Arial",12), width=30
        )
        cmb.pack(pady=10)
        cmb.bind("<<ComboboxSelected>>", lambda e: signal_interaction())

        tk.Button(self.frame1, text="Next →", command=self._on_next, width=20).pack(pady=30)
        self.frame1.pack(fill="both", expand=True)

        self.frame2 = None
        self.current_cfg = {}

    def _on_next(self):
        sel = self.choice.get()
        if not sel:
            messagebox.showerror("Error", "Please choose a layout.")
            return

        signal_interaction()  # stop the killer
        # Build base config
        if sel in CUSTOM_LAYOUTS:
            spec = CUSTOM_LAYOUTS[sel]
            cfg = {"grid": spec["grid"][:], "tiles": [t.copy() for t in spec["tiles"]]}
        else:
            r, c = map(int, sel.split("x"))
            cfg = {"grid": [r, c], "tiles": []}
            for i in range(r*c):
                cfg["tiles"].append({"row": i//c, "col": i%c, "w":1, "h":1})

        self.current_cfg = cfg
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
            tk.Label(grid_frame, text=f"Tile {r},{c}", font=("Arial",12))\
              .grid(row=r, column=c*2, padx=5, pady=5, sticky="e")

            var = tk.StringVar()
            cb = ttk.Combobox(
                grid_frame, values=self.cam_names,
                textvariable=var, state="readonly",
                width=40, font=("Arial",12)
            )
            cb.grid(row=r, column=c*2+1, padx=5, pady=5, sticky="w")
            cb.bind("<<ComboboxSelected>>", lambda e: signal_interaction())
            self.sel_vars.append((var, tile))

        btnf = tk.Frame(self.frame2)
        btnf.pack(pady=20, fill="x")
        tk.Button(btnf, text="← Back", command=self._go_back, width=12)\
          .pack(side="left", padx=30)
        tk.Button(btnf, text="Save & Launch", command=self._on_save, width=16)\
          .pack(side="right", padx=30)

        self.frame2.pack(fill="both", expand=True)

    def _go_back(self):
        self.frame2.pack_forget()
        self.frame1.pack(fill="both", expand=True)

    def _on_save(self):
        signal_interaction()
        # collect assignments
        for var, tile in self.sel_vars:
            name = var.get()
            if not name:
                messagebox.showerror("Error", "Every tile must have a camera.")
                return
            tile["name"] = name
            tile["url"]  = self.cam_urls.get(name, "")

        # write config
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump(self.current_cfg, f, indent=2)
            open(FLAG_FILE, "w").close()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save config:\n{e}")
            return

        messagebox.showinfo("Saved", "Configuration saved!\nLaunching streams…")
        self.destroy()

if __name__ == "__main__":
    LayoutChooser().mainloop()
