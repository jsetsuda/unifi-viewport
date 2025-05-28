# overlay_box.py
# Draws a red border overlay on a stream tile if there's a failure

import sys
import tkinter as tk

# Usage: python3 overlay_box.py <window_title> red
if len(sys.argv) != 3:
    print("Usage: overlay_box.py <window_title> <color>")
    sys.exit(1)

window_title = sys.argv[1]
color = sys.argv[2].lower()

if color != "red":
    sys.exit(0)  # Don't show overlay unless red

def main():
    root = tk.Tk()
    root.title(f"overlay_{window_title}")
    root.geometry("200x100+50+50")  # Optional: dynamically place later
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.0)  # Fully transparent base window
    root.overrideredirect(True)

    canvas = tk.Canvas(root, width=200, height=100, highlightthickness=4, highlightbackground="#FF0000")
    canvas.pack()

    # Auto-close after 10 seconds unless refreshed
    root.after(10000, root.destroy)
    root.mainloop()

if __name__ == "__main__":
    main()
