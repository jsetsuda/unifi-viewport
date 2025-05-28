# overlay_box.py
# Draws a status indicator overlay per stream tile window
import sys
import time
import tkinter as tk

# Usage: python3 overlay_box.py tile_0_0 green
if len(sys.argv) != 3:
    print("Usage: overlay_box.py <window_title> <color>")
    sys.exit(1)

window_title = sys.argv[1]
color = sys.argv[2].lower()

if color not in ("green", "yellow", "red"):
    color = "yellow"

overlay_colors = {
    "green": "#00FF00",
    "yellow": "#FFFF00",
    "red": "#FF0000"
}

# Create a top-left transparent window
def main():
    root = tk.Tk()
    root.title(f"overlay_{window_title}")
    root.geometry("60x30+10+10")  # Size and position (top-left)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.6)
    root.configure(bg=overlay_colors[color])
    root.overrideredirect(True)

    canvas = tk.Canvas(root, bg=overlay_colors[color], highlightthickness=0)
    canvas.pack(fill="both", expand=True)
    canvas.create_text(30, 15, text=color.upper(), fill="black", font=("Arial", 10, "bold"))

    # Auto-close after 5 seconds unless manually restarted
    root.after(5000, root.destroy)
    root.mainloop()

if __name__ == "__main__":
    main()
