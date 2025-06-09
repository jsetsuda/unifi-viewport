#!/usr/bin/env python3
"""
layout_chooser.py

Two-step GUI:
 1) choose a layout
 2) assign cameras to each tile

Always offers “Use Previous Layout” if viewport_config.json already has grid+tiles,
and auto-selects it after 20 seconds of inactivity.
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

# Predefined custom layouts
CUSTOM_LAYOUTS = {
    "2x1": {
        "grid": [1,2],
        "tiles": [
            {"row":0,"col":0,"w":1,"h":1},
            {"row":0,"col":1,"w":1,"h":1},
        ]
    },
    "3_custom": {
        "grid": [2,2],
        "tiles":[
            {"row":0,"col":0,"w":1,"h":2},
            {"row":0,"col":1,"w":1,"h":1},
            {"row":1,"col":1,"w":1,"h":1},
        ]
    },
    "5_custom": {
        "grid": [2,3],
        "tiles":[
            {"row":0,"col":0,"w":2,"h":2},
            {"row":0,"col":1,"w":1,"h":1},
            {"row":1,"col":1,"w":1,"h":1},
            {"row":0,"col":2,"w":1,"h":1},
            {"row":1,"col":2,"w":1,"h":1},
        ]
    },
    "6_custom": {
        "grid": [3,3],
        "tiles":[
            {"row":0,"col":0,"w":2,"h":2},
            {"row":0,"col":2,"w":1,"h":1},
            {"row":1,"col":2,"w":1,"h":1},
            {"row":2,"col":0,"w":1,"h":1},
            {"row":2,"col":1,"w":1,"h":1},
            {"row":2,"col":2,"w":1,"h":1},
        ]
    },
}

SIMPLE_LAYOUTS = ["1x1","2x1","2x2","3x3"]
ALL_OPTIONS    = SIMPLE_LAYOUTS + list(CUSTOM_LAYOUTS.keys())
AUTO_TIMEOUT   = 20000  # milliseconds

def fetch_camera_list():
    """Populate camera_urls.json via get_streams.py --list."""
    try:
        subprocess.run(
            ["python3", GET_STREAMS, "--list"],
            cwd=SCRIPT_DIR, check=True,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except subprocess.CalledProcessError:
        # not critical at startup
        pass

def load_cameras():
    """Return (names, url_map)."""
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

        # load camera list
        fetch_camera_list()
        self.cam_names, self.cam_urls = load_cameras()

        # determine if a valid config exists
        self.has_existing = self._check_existing_config()

        # two frames for two steps
        self.frame1 = tk.Frame(self)
        self.frame2 = None
        self.current_cfg = {}

        self._build_step1()

    def _check_existing_config(self):
        try:
            j = json.load(open(CONFIG_FILE))
            return bool(j.get("grid") and j.get("tiles"))
        except:
            return False

    def _build_step1(self):
        self.frame1.pack(fill="both", expand=True)

        tk.Label(
            self.frame1,
            text="Step 1: Select layout",
            font=("Arial",14)
        ).pack(pady=20)

        self.choice = tk.StringVar()
        cmb = ttk.Combobox(
            self.frame1,
            values=ALL_OPTIONS,
            textvariable=self.choice,
            state="readonly",
            font=("Arial",12),
            width=30
        )
        cmb.pack(pady=10)
        cmb.bind("<<ComboboxSelected>>", lambda e: self._signal_interaction())

        btnf = tk.Frame(self.frame1)
        btnf.pack(pady=30)

        tk.Button(
            btnf, text="Next →", command=self._on_next, width=20
        ).grid(row=0,column=0,padx=5)

        if self.has_existing:
            tk.Button(
                btnf, text="Use Previous Layout", command=self._use_previous, width=20
            ).grid(row=0,column=1,padx=5)
            # auto-invoke after timeout
            self.after(AUTO_TIMEOUT, self._on_timeout)

    def _signal_interaction(self):
        """Touch the flag so viewport.sh knows not to kill us."""
        try:
            open(FLAG_FILE,"w").close()
        except:
            pass

    def _use_previous(self):
        self._signal_interaction()
        self.destroy()

    def _on_timeout(self):
        if self.has_existing:
            self._use_previous()

    def _on_next(self):
        sel = self.choice.get()
        if not sel:
            messagebox.showerror("Error","Please select a layout.")
            return

        self._signal_interaction()

        # build blank config
        if sel in CUSTOM_LAYOUTS:
            spec = CUSTOM_LAYOUTS[sel]
            self.current_cfg = {
                "grid": spec["grid"][:],
                "tiles": [t.copy() for t in spec["tiles"]]
            }
        else:
            r,c = map(int,sel.split("x"))
            tiles = [{"row":i//c,"col":i%c,"w":1,"h":1} for i in range(r*c)]
            self.current_cfg = {"grid":[r,c], "tiles":tiles}

        self.frame1.pack_forget()
        self._build_step2()

    def _build_step2(self):
        self.frame2 = tk.Frame(self)
        self.frame2.pack(fill="both", expand=True)

        tk.Label(
            self.frame2,
            text="Step 2: Assign cameras to each tile",
            font=("Arial",14)
        ).pack(pady=10)

        grid_frame = tk.Frame(self.frame2)
        grid_frame.pack(pady=10)

        self.sel_vars = []
        for t in self.current_cfg["tiles"]:
            r,c = t["row"],t["col"]
            tk.Label(
                grid_frame, text=f"Tile {r},{c}", font=("Arial",12)
            ).grid(row=r, column=c*2, padx=5, pady=5, sticky="e")

            var = tk.StringVar()
            cb = ttk.Combobox(
                grid_frame,
                values=self.cam_names,
                textvariable=var,
                state="readonly",
                font=("Arial",12),
                width=40
            )
            cb.grid(row=r, column=c*2+1, padx=5, pady=5, sticky="w")
            cb.bind("<<ComboboxSelected>>", lambda e: self._signal_interaction())
            self.sel_vars.append((var,t))

        btnf = tk.Frame(self.frame2)
        btnf.pack(pady=20, fill="x")

        tk.Button(
            btnf, text="← Back", command=self._go_back, width=12
        ).pack(side="left", padx=30)

        tk.Button(
            btnf, text="Save & Launch", command=self._on_save, width=16
        ).pack(side="right", padx=30)

    def _go_back(self):
        self.frame2.pack_forget()
        self.frame1.pack(fill="both", expand=True)

    def _on_save(self):
        self._signal_interaction()

        # collect selections
        for var,t in self.sel_vars:
            name = var.get()
            if not name:
                messagebox.showerror("Error","All tiles must have a camera.")
                return
            t["name"] = name
            t["url"]  = self.cam_urls.get(name,"")

        # write config + flag
        try:
            with open(CONFIG_FILE,"w") as f:
                json.dump(self.current_cfg, f, indent=2)
            open(FLAG_FILE,"w").close()
        except Exception as e:
            messagebox.showerror("Error",f"Failed to save config:\n{e}")
            return

        messagebox.showinfo("Saved","Configuration saved!\nLaunching streams…")
        self.destroy()

if __name__=="__main__":
    LayoutChooser().mainloop()
