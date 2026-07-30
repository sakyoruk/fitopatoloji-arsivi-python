# -*- coding: utf-8 -*-
"""Windows 7 ile uyumlu, yalnızca ttk kullanan modern görünüm."""
from .common import tk, ttk

COLORS = {
    "bg": "#f4f6f1",
    "surface": "#ffffff",
    "surface_alt": "#edf2eb",
    "nav": "#183c32",
    "nav_hover": "#245447",
    "nav_active": "#2f6f5e",
    "primary": "#2f6f5e",
    "primary_hover": "#25594c",
    "accent": "#dcebe2",
    "accent_warm": "#efe4c9",
    "text": "#22312b",
    "muted": "#68776f",
    "border": "#d5ddd7",
    "danger": "#a33f3f",
    "warning": "#9a6a1c",
    "success": "#387a57",
}


def apply_theme(root):
    root.configure(background=COLORS["bg"])
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    default_font = ("Segoe UI", 9)
    style.configure(".", font=default_font, background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("TFrame", background=COLORS["bg"])
    style.configure("Surface.TFrame", background=COLORS["surface"])
    style.configure("Nav.TFrame", background=COLORS["nav"])
    style.configure("Header.TFrame", background=COLORS["surface"])
    style.configure("Card.TFrame", background=COLORS["surface"], relief="solid", borderwidth=1)
    style.configure("SoftCard.TFrame", background=COLORS["surface_alt"], relief="flat", borderwidth=0)
    style.configure("Toolbar.TFrame", background=COLORS["surface_alt"])

    style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"])
    style.configure("Surface.TLabel", background=COLORS["surface"], foreground=COLORS["text"])
    style.configure("Muted.TLabel", background=COLORS["surface"], foreground=COLORS["muted"])
    style.configure("Title.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 17, "bold"))
    style.configure("Subtitle.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=("Segoe UI", 9))
    style.configure("Section.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 10, "bold"))
    style.configure("NavTitle.TLabel", background=COLORS["nav"], foreground="#ffffff", font=("Segoe UI", 13, "bold"))
    style.configure("NavSub.TLabel", background=COLORS["nav"], foreground="#b9cad8", font=("Segoe UI", 8))
    style.configure("NavSection.TLabel", background=COLORS["nav"], foreground="#90a9bc", font=("Segoe UI", 8, "bold"))

    style.configure("TButton", padding=(10, 6), borderwidth=1, background=COLORS["surface_alt"], foreground=COLORS["text"])
    style.map("TButton", background=[("active", "#e2e9ee"), ("pressed", "#d6e0e7")])
    style.configure("Primary.TButton", padding=(12, 7), background=COLORS["primary"], foreground="#ffffff", borderwidth=0)
    style.map("Primary.TButton", background=[("active", COLORS["primary_hover"]), ("pressed", COLORS["primary_hover"])], foreground=[("disabled", "#d5e2de")])
    style.configure("Nav.TButton", anchor="w", padding=(15, 9), background=COLORS["nav"], foreground="#e9f2ee", borderwidth=0)
    style.map("Nav.TButton", background=[("active", COLORS["nav_hover"]), ("pressed", COLORS["nav_active"])])
    style.configure("NavActive.TButton", anchor="w", padding=(15, 9), background=COLORS["nav_active"], foreground="#ffffff", borderwidth=0, font=("Segoe UI", 9, "bold"))
    style.map("NavActive.TButton", background=[("active", COLORS["nav_active"]), ("pressed", COLORS["nav_active"])])
    style.configure("Danger.TButton", background="#f8e8e8", foreground=COLORS["danger"])
    style.map("Danger.TButton", background=[("active", "#f2d7d7")])

    style.configure("TEntry", padding=6, fieldbackground="#ffffff", bordercolor=COLORS["border"], lightcolor=COLORS["border"], darkcolor=COLORS["border"])
    style.configure("TCombobox", padding=5, fieldbackground="#ffffff", background="#ffffff", bordercolor=COLORS["border"])
    style.configure("TCheckbutton", background=COLORS["surface"], foreground=COLORS["text"])

    style.configure("Treeview", rowheight=29, background="#ffffff", fieldbackground="#ffffff", foreground=COLORS["text"], bordercolor=COLORS["border"], borderwidth=1)
    style.configure("Treeview.Heading", padding=(8, 7), background=COLORS["surface_alt"], foreground=COLORS["text"], font=("Segoe UI", 9, "bold"), relief="flat")
    style.map("Treeview", background=[("selected", COLORS["primary"])], foreground=[("selected", "#ffffff")])
    style.map("Treeview.Heading", background=[("active", "#e1e9ef")])

    style.configure("TNotebook", background=COLORS["surface"], borderwidth=0)
    style.configure("TNotebook.Tab", padding=(13, 8), background=COLORS["surface_alt"], foreground=COLORS["muted"], borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", COLORS["surface"]), ("active", "#e3ecef")], foreground=[("selected", COLORS["primary"])])
    style.configure("TLabelframe", background=COLORS["surface"], bordercolor=COLORS["border"], relief="solid", borderwidth=1)
    style.configure("TLabelframe.Label", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 9, "bold"))
    style.configure("Status.TLabel", background="#e7ede8", foreground=COLORS["muted"], padding=(10, 6))
    style.configure("Badge.TLabel", background=COLORS["accent"], foreground=COLORS["primary"], font=("Segoe UI", 8, "bold"), padding=(8, 3))
    style.configure("WarmBadge.TLabel", background=COLORS["accent_warm"], foreground=COLORS["warning"], font=("Segoe UI", 8, "bold"), padding=(8, 3))
    style.configure("MetricValue.TLabel", background=COLORS["surface"], foreground=COLORS["primary"], font=("Segoe UI", 16, "bold"))
    style.configure("MetricLabel.TLabel", background=COLORS["surface"], foreground=COLORS["muted"], font=("Segoe UI", 8))
    style.configure("Quiet.TButton", padding=(9, 6), background=COLORS["surface"], foreground=COLORS["muted"], borderwidth=0)
    style.map("Quiet.TButton", background=[("active", COLORS["surface_alt"])], foreground=[("active", COLORS["text"])])
    style.configure("Horizontal.TPanedwindow", background=COLORS["bg"])

    style.configure("Ribbon.TFrame", background=COLORS["surface_alt"])
    style.configure("Ribbon.TNotebook", background=COLORS["surface_alt"], borderwidth=0)
    style.configure("Ribbon.TNotebook.Tab", padding=(15, 7), background=COLORS["surface_alt"], foreground=COLORS["muted"], font=("Segoe UI", 8, "bold"))
    style.map("Ribbon.TNotebook.Tab", background=[("selected", COLORS["surface"]), ("active", "#e1e9ef")], foreground=[("selected", COLORS["primary"])])
    style.configure("Ribbon.TButton", padding=(9, 7), background=COLORS["surface_alt"], foreground=COLORS["text"], borderwidth=0)
    style.map("Ribbon.TButton", background=[("active", "#dce7ed"), ("pressed", "#cfdee6")])
    style.configure("RibbonPrimary.TButton", padding=(10, 7), background=COLORS["accent"], foreground=COLORS["primary"], borderwidth=0)
    style.map("RibbonPrimary.TButton", background=[("active", "#cde4dc"), ("pressed", "#bddacf")])
    style.configure("RibbonGroup.TLabel", background=COLORS["surface_alt"], foreground=COLORS["muted"], font=("Segoe UI", 7), anchor="center")
    style.configure("Eyebrow.TLabel", background=COLORS["surface"], foreground=COLORS["primary"], font=("Segoe UI", 8, "bold"))
    style.configure("ContextTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 12, "bold"))
    style.configure("Score.TLabel", background=COLORS["surface"], foreground=COLORS["primary"], font=("Segoe UI", 10, "bold"))
    style.configure("AboutTitle.TLabel", background=COLORS["surface"], foreground=COLORS["text"], font=("Segoe UI", 18, "bold"))
    return style
