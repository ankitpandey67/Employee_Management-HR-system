import tkinter as tk
from tkinter import ttk

# ------------------------------------------------------
# COLOR PALETTE
# ------------------------------------------------------
COLORS = {
    "bg": "#1f1f1f",          # main window background
    "fg": "#ffffff",          # default text
    "header": "#4CAF50",      # green primary
    "accent1": "#E53935",     # red delete
    "accent2": "#2196F3",     # blue highlight
    "frame": "#2a2a2a",       # dark panels
    "border": "#3b3b3b",      # borders
    "tree_even": "#2c2c2c",
    "tree_odd": "#232323",
}


# ------------------------------------------------------
# WINDOW STYLE
# ------------------------------------------------------
def style_window(root, title, size="1200x700"):
    root.title(title)
    root.geometry(size)
    root.configure(bg=COLORS["bg"])
    root.resizable(False, False)

    # Header bar
    header = tk.Label(root, text=title, bg=COLORS["header"], fg="white",
                      font=("Arial", 20, "bold"), padx=20, pady=8)
    header.pack(fill="x")

    return header


# ------------------------------------------------------
# LABEL & ENTRY STYLE
# ------------------------------------------------------
def style_label(widget):
    widget.configure(font=("Arial", 11), fg=COLORS["fg"], bg=COLORS["bg"])


def style_entry(widget):
    widget.configure(font=("Arial", 11), bg="#2c2c2c", fg="white",
                     insertbackground="white", relief="groove")


# ------------------------------------------------------
# NICE LABELFRAME
# ------------------------------------------------------
def styled_labelframe(parent, text):
    lf = tk.LabelFrame(parent, text=text, bg=COLORS["frame"], fg="white",
                       font=("Arial", 12, "bold"), padx=10, pady=10)

    lf.configure(highlightbackground=COLORS["border"], highlightcolor=COLORS["border"])
    return lf


# ------------------------------------------------------
# COLORFUL BUTTON
# style="accent1", "accent2", "header"
# ------------------------------------------------------
def colorful_button(parent, text, cmd, style="accent2"):
    color = COLORS.get(style, COLORS["accent2"])
    btn = tk.Button(parent, text=text, command=cmd,
                    font=("Arial", 11, "bold"),
                    bg=color, fg="white",
                    activebackground=color,
                    activeforeground="white",
                    relief="flat", padx=12, pady=4,
                    cursor="hand2")
    return btn


# ------------------------------------------------------
# TREEVIEW THEME
# ------------------------------------------------------
def style_treeview(tree):
    style = ttk.Style()
    style.theme_use("default")

    style.configure("Treeview",
                    background=COLORS["bg"],
                    fieldbackground=COLORS["bg"],
                    foreground=COLORS["fg"],
                    rowheight=26,
                    borderwidth=0,
                    font=("Arial", 11))

    style.map("Treeview",
              background=[("selected", COLORS["accent2"])])

    tree.tag_configure("even", background=COLORS["frame"])
    tree.tag_configure("odd", background=COLORS["tree_odd"])
    tree.tag_configure("selected", background=COLORS["accent2"], foreground="white")


# ------------------------------------------------------
# SCROLLBAR STYLE
# ------------------------------------------------------
def style_scrollbar(scrollbar):
    style = ttk.Style()
    style.configure("Vertical.TScrollbar",
                    background=COLORS["frame"],
                    troughcolor=COLORS["bg"],
                    bordercolor=COLORS["border"],
                    arrowcolor="white")
    scrollbar.configure(style="Vertical.TScrollbar")
