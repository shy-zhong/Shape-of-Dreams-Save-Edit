"""通用控件工厂（深色主题）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from . import theme

__all__ = ["label", "button", "entry", "combo", "card", "hover_effect", "configure_treeview"]


def label(parent, text: str, x: int, y: int, w: int, h: int,
          font=theme.FONT_BODY, color=theme.DIM, anchor: str = "w", **extra):
    widget = tk.Label(parent, text=text, bg=parent.cget("bg"), fg=color, font=font, anchor=anchor, **extra)
    widget.place(x=x, y=y, width=w, height=h)
    return widget


def button(parent, text: str, x: int, y: int, w: int, h: int, command,
           primary: bool = False, font=None):
    if primary:
        widget = tk.Button(
            parent, text=text, bg=theme.ACCENT, fg="#10151F", activebackground="#9CBCFF",
            activeforeground="#10151F", relief="flat", bd=0,
            font=font or theme.FONT_BOLD, cursor="hand2", command=command,
        )
    else:
        widget = tk.Button(
            parent, text=text, bg=theme.BTN, fg=theme.TEXT, activebackground=theme.BTN_HOVER,
            activeforeground=theme.TEXT, relief="flat", bd=0,
            font=font or theme.FONT_BODY, cursor="hand2", command=command,
        )
        hover_effect(widget)
    widget.place(x=x, y=y, width=w, height=h)
    return widget


def hover_effect(widget, normal: str = theme.BTN, hover: str = theme.BTN_HOVER):
    widget.bind("<Enter>", lambda _event: widget.configure(bg=hover))
    widget.bind("<Leave>", lambda _event: widget.configure(bg=normal))


def entry(parent, x: int, y: int, w: int, h: int = 26, textvariable=None,
          justify: str = "left", font=theme.FONT_BODY):
    widget = tk.Entry(
        parent, textvariable=textvariable, bg=theme.INPUT, fg=theme.TEXT, insertbackground=theme.TEXT,
        relief="flat", highlightthickness=1, highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
        font=font, justify=justify,
    )
    widget.place(x=x, y=y, width=w, height=h)
    return widget


def combo(parent, x: int, y: int, w: int, values, textvariable=None):
    widget = ttk.Combobox(parent, values=list(values), textvariable=textvariable, font=theme.FONT_BODY)
    widget.place(x=x, y=y, width=w, height=26)
    return widget


def card(parent, title: str, y: int, height: int, subtitle: str = "", width: int = theme.CARD_WIDTH):
    frame = tk.Frame(parent, bg=theme.CARD, width=width, height=height)
    frame.place(x=10, y=y, width=width, height=height)
    tk.Label(frame, text=title, bg=theme.CARD, fg=theme.ACCENT, font=theme.FONT_H2, anchor="w").place(
        x=16, y=8, width=width - 40
    )
    if subtitle:
        tk.Label(frame, text=subtitle, bg=theme.CARD, fg=theme.DIM, font=theme.FONT_SMALL, anchor="w").place(
            x=16, y=32, width=width - 40
        )
    return frame


def configure_treeview(root, style: ttk.Style):
    style.theme_use("clam")
    style.configure(
        "Treeview", background=theme.CARD, fieldbackground=theme.CARD, foreground=theme.TEXT,
        borderwidth=0, rowheight=22, font=theme.FONT_MONO,
    )
    style.map("Treeview", background=[("selected", theme.ACCENT_DIM)], foreground=[("selected", theme.TEXT)])
    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure(
        "Treeview.Heading", background=theme.CARD_ALT, foreground=theme.DIM, relief="flat",
        borderwidth=0, font=theme.FONT_SMALL, padding=(6, 3), anchor="w",
    )
    style.map("Treeview.Heading", background=[("active", theme.CARD)])
    style.configure(
        "TCombobox", fieldbackground=theme.INPUT, background=theme.CARD_ALT, foreground=theme.TEXT,
        arrowcolor=theme.TEXT, bordercolor=theme.BORDER, lightcolor=theme.CARD_ALT,
        darkcolor=theme.CARD_ALT, selectbackground=theme.INPUT, selectforeground=theme.TEXT, padding=(4, 2),
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", theme.INPUT)],
        foreground=[("readonly", theme.TEXT)],
        selectbackground=[("readonly", theme.INPUT)],
        selectforeground=[("readonly", theme.TEXT)],
        background=[("active", theme.CARD_ALT)],
    )
    root.option_add("*TCombobox*Listbox.background", theme.CARD)
    root.option_add("*TCombobox*Listbox.foreground", theme.TEXT)
    root.option_add("*TCombobox*Listbox.selectBackground", theme.ACCENT_DIM)
    root.option_add("*TCombobox*Listbox.selectForeground", theme.TEXT)


def scrollbar(parent, command, **extra):
    return tk.Scrollbar(
        parent, orient="vertical", command=command, width=12, bg=theme.CARD,
        troughcolor=theme.BG, activebackground=theme.BORDER, bd=0, highlightthickness=0,
        relief="flat", **extra,
    )
