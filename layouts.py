"""Layout definitions shared between layout_chooser.py and the dashboard.

A "layout" is a named grid + a list of tile rectangles. The kiosk
reads `viewport_config.json` (which is just an expanded layout with
a `name` and `url` filled in per tile) and lays out `mpv` windows
accordingly.

Keep both `layout_chooser.py` (Tk GUI) and `dashboard/app.py` (Flask)
importing from this module so the available layouts stay in sync.
"""

SIMPLE_LAYOUTS = ["1x1", "2x2", "3x3"]

CUSTOM_LAYOUTS = {
    "2x1": {
        "grid": [1, 2],
        "tiles": [
            {"row": 0, "col": 0, "w": 1, "h": 1},
            {"row": 0, "col": 1, "w": 1, "h": 1},
        ],
    },
    "3_custom": {
        "grid": [2, 2],
        "tiles": [
            {"row": 0, "col": 0, "w": 1, "h": 2},
            {"row": 0, "col": 1, "w": 1, "h": 1},
            {"row": 1, "col": 1, "w": 1, "h": 1},
        ],
    },
    "5_custom": {
        "grid": [2, 3],
        "tiles": [
            {"row": 0, "col": 0, "w": 2, "h": 2},
            {"row": 0, "col": 1, "w": 1, "h": 1},
            {"row": 1, "col": 1, "w": 1, "h": 1},
            {"row": 0, "col": 2, "w": 1, "h": 1},
            {"row": 1, "col": 2, "w": 1, "h": 1},
        ],
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
        ],
    },
}

ALL_OPTIONS = SIMPLE_LAYOUTS + [k for k in CUSTOM_LAYOUTS if k not in SIMPLE_LAYOUTS]


def expand(layout_name):
    """Return {"grid": [r,c], "tiles": [{row,col,w,h}, ...]} for a layout name.

    Returns None if `layout_name` is neither a registered custom layout
    nor a parseable "RxC" string.
    """
    if layout_name in CUSTOM_LAYOUTS:
        spec = CUSTOM_LAYOUTS[layout_name]
        return {
            "grid": list(spec["grid"]),
            "tiles": [dict(t) for t in spec["tiles"]],
        }
    try:
        r, c = (int(x) for x in layout_name.split("x"))
    except (ValueError, AttributeError):
        return None
    tiles = [
        {"row": i // c, "col": i % c, "w": 1, "h": 1}
        for i in range(r * c)
    ]
    return {"grid": [r, c], "tiles": tiles}
