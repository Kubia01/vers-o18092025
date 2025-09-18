import tkinter as tk
from tkinter import ttk


# Centralized visual theme for the CRM application.
# This module intentionally does not change any business logic. It only
# defines styles, colors, and fonts and applies them globally to ttk widgets.


PALETTE = {
    # SAP Fiori-like palette
    "bg_app": "#f7f7f7",
    "bg_card": "#ffffff",
    "bg_header": "#0a6ed1",
    "text_primary": "#2c3f57",
    "text_secondary": "#6a7d95",
    "accent": "#0a6ed1",
    "success": "#107e3e",
    "danger": "#bb0000",
    "border": "#dde3ea",
    "focus": "#0854a0",
}


FONTS = {
    "base": ("Segoe UI", 10),
    "base_bold": ("Segoe UI", 10, "bold"),
    "title": ("Segoe UI", 18, "bold"),
    "subtitle": ("Segoe UI", 12, "bold"),
    "mono": ("Consolas", 10),
}


def apply_theme(root: tk.Misc) -> None:
    """Apply a modern, clean ttk theme and styles to the application.

    This function is safe to call once at startup. It does not modify
    application logic, only widget appearance.
    """
    try:
        # Use the built-in 'clam' theme as a base for consistent rendering
        style = ttk.Style(master=root)
        try:
            style.theme_use("clam")
        except Exception:
            # Fallback to any available theme
            for candidate in ("alt", "default", "classic"):
                try:
                    style.theme_use(candidate)
                    break
                except Exception:
                    continue

        root.configure(bg=PALETTE["bg_app"])  # background for tk containers

        # Global fonts (applies to ttk via style mappings below)
        root.option_add("*Font", FONTS["base"])

        # Base colors for common ttk widgets
        style.configure(
            "TLabel",
            background=PALETTE["bg_app"],
            foreground=PALETTE["text_primary"],
        )
        style.configure(
            "Card.TFrame",
            background=PALETTE["bg_card"],
            bordercolor=PALETTE["border"],
            relief="flat",
        )
        style.configure(
            "TFrame",
            background=PALETTE["bg_app"],
        )

        # Buttons
        def _elevated_button(base, bg, fg="#ffffff", active_bg=None, disabled_bg=None):
            style.configure(
                base,
                background=bg,
                foreground=fg,
                bordercolor=bg,
                focusthickness=2,
                focuscolor=PALETTE["focus"],
                padding=(18, 10),
            )
            style.map(
                base,
                background=[("active", active_bg or bg), ("disabled", disabled_bg or bg)],
                relief=[("pressed", "sunken"), ("!pressed", "flat")],
            )

        def _outline_button(base, border, fg):
            style.configure(
                base,
                background="#ffffff",
                foreground=fg,
                bordercolor=border,
                focusthickness=2,
                focuscolor=PALETTE["focus"],
                padding=(16, 9),
            )
            style.map(
                base,
                background=[("active", "#f2f6fb")],
            )

        _elevated_button("Primary.TButton", PALETTE["accent"], active_bg="#0854a0", disabled_bg="#9cc3ea")
        _elevated_button("Success.TButton", PALETTE["success"], active_bg="#0b6b34", disabled_bg="#a7d7b9")
        _elevated_button("Danger.TButton", PALETTE["danger"], active_bg="#a10000", disabled_bg="#e3a6a6")
        _outline_button("Secondary.TButton", PALETTE["border"], PALETTE["text_primary"]) 
        _outline_button("Ghost.TButton", PALETTE["bg_app"], PALETTE["text_secondary"]) 

        # Entries
        style.configure(
            "TEntry",
            fieldbackground="#ffffff",
            foreground=PALETTE["text_primary"],
            bordercolor=PALETTE["border"],
            lightcolor=PALETTE["focus"],
            darkcolor=PALETTE["border"],
            padding=(8, 6),
        )
        # Combobox (drop-downs)
        try:
            style.configure(
                "TCombobox",
                fieldbackground="#ffffff",
                background="#ffffff",
                foreground=PALETTE["text_primary"],
                arrowcolor=PALETTE["text_secondary"],
                bordercolor=PALETTE["border"],
                lightcolor=PALETTE["focus"],
                darkcolor=PALETTE["border"],
                padding=(6, 4),
            )
            style.map(
                "TCombobox",
                fieldbackground=[("readonly", "#ffffff"), ("focus", "#ffffff")],
                background=[("active", "#ffffff")],
                bordercolor=[("focus", PALETTE["focus"])],
            )
        except Exception:
            pass

        # Notebook (tabs)
        style.configure(
            "TNotebook",
            background=PALETTE["bg_app"],
            borderwidth=0,
        )
        # Keep default tabs visible for module notebooks
        style.configure(
            "TNotebook.Tab",
            font=FONTS["base"],
            padding=(14, 8),
            background="#ffffff",
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#eef4fb")],
            foreground=[("selected", PALETTE["text_primary"])],
        )
        # Create a special style for the main app notebook with hidden tabs
        try:
            style.layout("Main.TNotebook.Tab", [])
        except Exception:
            pass

        # Treeview (tables)
        style.configure(
            "Treeview",
            background="#ffffff",
            fieldbackground="#ffffff",
            foreground=PALETTE["text_primary"],
            bordercolor=PALETTE["border"],
            rowheight=28,
        )
        style.configure(
            "Treeview.Heading",
            font=FONTS["base_bold"],
            background="#ffffff",
            foreground=PALETTE["text_primary"],
            bordercolor=PALETTE["border"],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#eef4fb")],
        )

        # Scrollbars (clean, light)
        try:
            style.configure(
                "Vertical.TScrollbar",
                background="#e9eef5",
                troughcolor="#ffffff",
                arrowcolor=PALETTE["text_secondary"],
                bordercolor=PALETTE["border"],
            )
            style.configure(
                "Horizontal.TScrollbar",
                background="#e9eef5",
                troughcolor="#ffffff",
                arrowcolor=PALETTE["text_secondary"],
                bordercolor=PALETTE["border"],
            )
        except Exception:
            pass

        # Header style (used by main window top bar)
        style.configure(
            "Header.TFrame",
            background=PALETTE["bg_header"],
        )
        style.configure(
            "Header.TLabel",
            background=PALETTE["bg_header"],
            foreground="#ffffff",
            font=FONTS["title"],
        )
        style.configure(
            "Subtle.TLabel",
            foreground=PALETTE["text_secondary"],
            background=PALETTE["bg_app"],
        )

        # Buttons intended to be used on dark headers (white text, stronger outline)
        style.configure(
            "SecondaryOnDark.TButton",
            background="#000000",  # Black background for maximum contrast
            foreground="#ffffff",
            bordercolor="#ffffff",
            focusthickness=3,
            focuscolor="#ffffff",
            padding=(16, 10),
            font=FONTS["base_bold"],  # Use bold font for better visibility
        )
        style.map(
            "SecondaryOnDark.TButton",
            background=[("active", "#1e40af"), ("pressed", "#1e3a8a")],
            foreground=[("disabled", "#e5e7eb")],
        )
    except Exception:
        # Fail-safe: never break the app if styling fails
        pass


def style_header_frame(frame: tk.Misc) -> None:
    try:
        frame.configure(bg=PALETTE["bg_header"])
    except Exception:
        pass


def card(frame: tk.Misc) -> None:
    try:
        frame.configure(bg=PALETTE["bg_card"])  # for tk.Frame usage
    except Exception:
        pass

