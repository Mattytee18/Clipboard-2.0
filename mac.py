#!/usr/bin/env python3
"""
Clipboard Manager — Mac version
Requires: pip3 install customtkinter pyperclip
"""

import json
import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog

try:
    import pyperclip
except ImportError:
    pyperclip = None

import subprocess

# _copy_text is set up after the root window exists — see ClipboardManager.__init__
# We use tkinter's clipboard which handles all Unicode (curly quotes, emojis, etc.)
_tk_root = None

def _copy_text(text):
    """Copy text using tkinter's clipboard — handles all Unicode correctly on Mac."""
    if _tk_root is not None:
        try:
            _tk_root.clipboard_clear()
            _tk_root.clipboard_append(text)
            _tk_root.update()  # keeps clipboard alive after window closes
            return
        except Exception:
            pass
    # Fallback: pbcopy with UTF-8
    try:
        subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True,
                       env={**__import__("os").environ, "LANG": "en_US.UTF-8"})
    except Exception:
        if pyperclip:
            pyperclip.copy(text)

# ── Data location: ~/Library/Application Support/ClipboardManager ──────────────
_APP_SUPPORT = os.path.join(os.path.expanduser("~"), "Library", "Application Support", "ClipboardManager")
os.makedirs(_APP_SUPPORT, exist_ok=True)
DATA_FILE = os.path.join(_APP_SUPPORT, "clipboard_items.json")
CATS_FILE = os.path.join(_APP_SUPPORT, "clipboard_categories.json")

# ── Bundled default data (copied to user dir on first launch) ───────────────────
if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    _BUNDLE_DIR = sys._MEIPASS
else:
    _BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))

def _seed_default_data():
    """
    On first launch (or if data files are empty), copy bundled JSON files
    into Application Support so the user starts with pre-loaded snippets.
    """
    import shutil
    for filename, dest in [("clipboard_items.json", DATA_FILE),
                            ("clipboard_categories.json", CATS_FILE)]:
        src = os.path.join(_BUNDLE_DIR, filename)
        if not os.path.exists(src):
            continue
        should_copy = False
        if not os.path.exists(dest):
            should_copy = True
        else:
            try:
                with open(dest, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if not content or content in ("[]", "{}"):
                    should_copy = True
            except Exception:
                should_copy = True
        if should_copy:
            shutil.copy(src, dest)

_seed_default_data()

# ── Palettes ───────────────────────────────────────────────────────────────────
LIGHT_THEME = dict(
    BG         = "#F5F4F0",
    PANEL      = "#FFFFFF",
    PANEL2     = "#EEECEA",
    BORDER     = "#DEDAD6",
    ACCENT     = "#5B6AF0",
    ACCENT_HOV = "#4554D4",
    DANGER     = "#E05252",
    TEXT       = "#1A1A2E",
    TEXT_MED   = "#6B6B80",
    TEXT_LIGHT = "#A0A0B8",
    SELECT_BG  = "#EEF0FE",
    DRAG_BG    = "#DDE0FC",
    SUCCESS    = "#34A853",
    WARN       = "#F59E0B",
    DELETE_HOV = "#FFF0F0",
)

DARK_THEME = dict(
    BG         = "#1C1C28",
    PANEL      = "#252535",
    PANEL2     = "#2E2E42",
    BORDER     = "#3A3A52",
    ACCENT     = "#7B8BFF",
    ACCENT_HOV = "#6070EE",
    DANGER     = "#FF6B6B",
    TEXT       = "#E8E8F0",
    TEXT_MED   = "#9090B0",
    TEXT_LIGHT = "#5A5A78",
    SELECT_BG  = "#2D2F55",
    DRAG_BG    = "#383A62",
    SUCCESS    = "#4ADE80",
    WARN       = "#FBBF24",
    DELETE_HOV = "#3D2020",
)

_current_theme = LIGHT_THEME.copy()

def _t(key):
    """Look up a colour from the active theme."""
    return _current_theme[key]

# Convenience globals (used by code that references them directly)
def _sync_globals():
    g = globals()
    for k, v in _current_theme.items():
        g[k] = v

_sync_globals()

# Aliases so existing code still works unchanged
BG         = _current_theme["BG"]
PANEL      = _current_theme["PANEL"]
PANEL2     = _current_theme["PANEL2"]
BORDER     = _current_theme["BORDER"]
ACCENT     = _current_theme["ACCENT"]
ACCENT_HOV = _current_theme["ACCENT_HOV"]
DANGER     = _current_theme["DANGER"]
TEXT       = _current_theme["TEXT"]
TEXT_MED   = _current_theme["TEXT_MED"]
TEXT_LIGHT = _current_theme["TEXT_LIGHT"]
SELECT_BG  = _current_theme["SELECT_BG"]
DRAG_BG    = _current_theme["DRAG_BG"]
SUCCESS    = _current_theme["SUCCESS"]
WARN       = _current_theme["WARN"]

FONT_UI    = ("Segoe UI", 10)
FONT_LABEL = ("Segoe UI", 9)
FONT_TITLE = ("Segoe UI Semibold", 13)
FONT_MONO  = ("Consolas", 10)
FONT_SMALL = ("Segoe UI", 8)


# ── Persistence ────────────────────────────────────────────────────────────────

def _strip_control_chars(text):
    """Remove invalid control characters that break JSON parsing."""
    return "".join(ch for ch in text if ord(ch) >= 32 or ch in ('\n', '\r', '\t'))

def load_items():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = _strip_control_chars(f.read())
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return []
    return []


def save_items(items):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)


# ── Categories persistence ──────────────────────────────────────────────────────
# Format: {"Category Name": ["snippet_id1", "snippet_id2", ...], ...}

def load_categories():
    if os.path.exists(CATS_FILE):
        with open(CATS_FILE, "r", encoding="utf-8") as f:
            content = _strip_control_chars(f.read())
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return {}
    return {}


def save_categories(cats):
    with open(CATS_FILE, "w", encoding="utf-8") as f:
        json.dump(cats, f, indent=2, ensure_ascii=False)


def _ensure_ids(items):
    """Back-fill unique IDs onto snippets that were saved before this version."""
    import uuid
    changed = False
    for item in items:
        if "id" not in item:
            item["id"] = str(uuid.uuid4())
            changed = True
    return changed


def _cleanup_categories(categories, items):
    """Remove null entries and IDs that no longer exist in items. Returns True if changed."""
    valid_ids = {item["id"] for item in items if "id" in item}
    changed = False
    for name in categories:
        before = categories[name]
        after = [sid for sid in before if sid is not None and sid in valid_ids]
        if after != before:
            categories[name] = after
            changed = True
    return changed

# ── Modern UI (CustomTkinter) ──────────────────────────────────────────────────
import customtkinter as ctk

# Palette — every colour is a (light, dark) pair that auto-switches with the
# active appearance mode, so the theme toggle is essentially free.
COL_BG         = ("#ECEEF3", "#141620")
COL_PANEL      = ("#FFFFFF", "#1E2130")
COL_PANEL2     = ("#F2F4F9", "#272B3D")   # input fills / subtle surfaces
COL_BORDER     = ("#E3E6EE", "#2E3345")
COL_ACCENT     = ("#4F7BF7", "#5E8CFF")
COL_ACCENT_HOV = ("#3D67E0", "#4B7AF0")
COL_TEXT       = ("#1B1E2B", "#E8EAF2")
COL_MUTED      = ("#6A6E82", "#9298B4")
COL_FAINT      = ("#9BA1B4", "#5B6078")
COL_SEL        = ("#E7EEFF", "#2A3050")
COL_SEL_HOV    = ("#DBE6FF", "#323A60")
COL_DRAG       = ("#CBDCFF", "#3A4680")
COL_DANGER     = ("#E05468", "#FF6B7A")
COL_DANGER_HOV = ("#CC4356", "#F05365")
COL_DANGER_SOFT= ("#FCEBEE", "#3A2530")
COL_SUCCESS    = ("#2FA96A", "#4ADE80")

if sys.platform == "darwin":
    FAMILY, MONO = "SF Pro Text", "SF Mono"
elif sys.platform == "win32":
    FAMILY, MONO = "Segoe UI", "Cascadia Mono"
else:
    FAMILY, MONO = "Inter", "DejaVu Sans Mono"


# ── User settings (persisted) ───────────────────────────────────────────────────

SETTINGS_FILE = os.path.join(os.path.dirname(CATS_FILE), "clipboard_settings.json")


def load_settings():
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_settings(data):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def _mode_is_dark():
    return ctk.get_appearance_mode() == "Dark"


def _c(pair):
    """Resolve a (light, dark) colour pair to the active mode — for tk.Menu."""
    if isinstance(pair, tuple):
        return pair[1] if _mode_is_dark() else pair[0]
    return pair


def _copy_to_clipboard(text, root):
    """Copy text to the system clipboard, using the best method per platform."""
    if "_copy_text" in globals():          # mac build provides this
        try:
            globals()["_copy_text"](text)
            return True
        except Exception:
            pass
    if pyperclip:
        try:
            pyperclip.copy(text)
            return True
        except Exception:
            pass
    try:                                    # universal tk fallback
        root.clipboard_clear()
        root.clipboard_append(text)
        root.update()
        return True
    except Exception:
        return False


# ── Edit / Add dialog ───────────────────────────────────────────────────────────

class SnippetDialog(ctk.CTkToplevel):
    """Modal add/edit dialog. Result in .result = {"label", "text"} or None."""

    def __init__(self, parent, app, title="Add Snippet", item=None):
        super().__init__(parent)
        self.app = app
        self.result = None
        self.title(title)
        self.configure(fg_color=COL_BG)
        self.geometry("520x460")
        self.minsize(440, 380)
        self.transient(parent)
        self._build(item or {}, title)
        self.after(60, self._grab)
        self.geometry(f"+{parent.winfo_rootx() + 70}+{parent.winfo_rooty() + 50}")
        self.wait_window()

    def _grab(self):
        try:
            self.grab_set()
            self.focus_force()
        except Exception:
            pass

    def _build(self, item, title):
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=22, pady=20)

        ctk.CTkLabel(wrap, text=title, font=self.app.f_title,
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 14))

        ctk.CTkLabel(wrap, text="LABEL  (OPTIONAL)", font=self.app.f_tiny,
                     text_color=COL_FAINT).pack(anchor="w", pady=(0, 4))
        self._label_var = ctk.StringVar(value=item.get("label", ""))
        ctk.CTkEntry(wrap, textvariable=self._label_var, font=self.app.f_ui,
                     height=40, corner_radius=10, border_width=1,
                     fg_color=COL_PANEL, border_color=COL_BORDER,
                     text_color=COL_TEXT, placeholder_text="e.g. Email signature"
                     ).pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(wrap, text="SNIPPET TEXT", font=self.app.f_tiny,
                     text_color=COL_FAINT).pack(anchor="w", pady=(0, 4))
        self._text = ctk.CTkTextbox(wrap, font=self.app.f_mono, corner_radius=10,
                                    border_width=1, fg_color=COL_PANEL,
                                    border_color=COL_BORDER, text_color=COL_TEXT,
                                    wrap="word")
        self._text.pack(fill="both", expand=True, pady=(0, 16))
        if item.get("text"):
            self._text.insert("1.0", item["text"])

        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Save", command=self._save, font=self.app.f_ui_b,
                      height=40, corner_radius=10, fg_color=COL_ACCENT,
                      hover_color=COL_ACCENT_HOV, text_color="#FFFFFF"
                      ).pack(side="right")
        ctk.CTkButton(btns, text="Cancel", command=self.destroy, font=self.app.f_ui,
                      height=40, width=100, corner_radius=10, fg_color=COL_PANEL2,
                      hover_color=COL_BORDER, text_color=COL_TEXT
                      ).pack(side="right", padx=(0, 10))

    def _save(self):
        text = self._text.get("1.0", "end").strip()
        if not text:
            self.app._flash("Please enter some text first")
            return
        self.result = {"label": self._label_var.get().strip(), "text": text}
        self.destroy()


# ── Delete-choice dialog ────────────────────────────────────────────────────────

class DeleteChoiceDialog(ctk.CTkToplevel):
    """.choice = 'category' | 'all' | None (cancel)."""

    def __init__(self, parent, app, snippet_label, cat_name):
        super().__init__(parent)
        self.app = app
        self.choice = None
        self.title("Remove Snippet")
        self.configure(fg_color=COL_BG)
        self.resizable(False, False)
        self.transient(parent)

        short = (snippet_label[:45] + "…") if len(snippet_label) > 45 else snippet_label
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=22, pady=20)

        ctk.CTkLabel(wrap, text="Remove snippet?", font=self.app.f_h,
                     text_color=COL_TEXT).pack(anchor="w")
        ctk.CTkLabel(wrap, text=f'"{short}"', font=self.app.f_ui,
                     text_color=COL_MUTED, wraplength=340, justify="left"
                     ).pack(anchor="w", pady=(6, 16))

        ctk.CTkButton(wrap, text=f'Remove from "{cat_name}" only',
                      command=lambda: self._pick("category"), font=self.app.f_ui,
                      height=42, corner_radius=10, fg_color=COL_PANEL2,
                      hover_color=COL_BORDER, text_color=COL_TEXT, anchor="w"
                      ).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(wrap, text="Delete permanently (all categories)",
                      command=lambda: self._pick("all"), font=self.app.f_ui,
                      height=42, corner_radius=10, fg_color=COL_DANGER,
                      hover_color=COL_DANGER_HOV, text_color="#FFFFFF", anchor="w"
                      ).pack(fill="x", pady=(0, 8))
        ctk.CTkButton(wrap, text="Cancel", command=self.destroy, font=self.app.f_ui,
                      height=38, corner_radius=10, fg_color="transparent",
                      hover_color=COL_PANEL2, text_color=COL_MUTED
                      ).pack(fill="x")

        self.after(60, self._grab)
        self.geometry(f"+{parent.winfo_rootx() + 90}+{parent.winfo_rooty() + 90}")
        self.wait_window()

    def _grab(self):
        try:
            self.grab_set(); self.focus_force()
        except Exception:
            pass

    def _pick(self, value):
        self.choice = value
        self.destroy()


# ── Main app ────────────────────────────────────────────────────────────────────

class ClipboardManager:
    def __init__(self, root):
        self.root = root
        self.root.title("Clipboard Manager")
        self.root.geometry("980x760")
        self.root.minsize(720, 540)
        self.root.configure(fg_color=COL_BG)

        # Fonts (root must exist first)
        self.f_title = ctk.CTkFont(family=FAMILY, size=21, weight="bold")
        self.f_h     = ctk.CTkFont(family=FAMILY, size=15, weight="bold")
        self.f_ui_b  = ctk.CTkFont(family=FAMILY, size=13, weight="bold")
        self.f_ui    = ctk.CTkFont(family=FAMILY, size=13)
        self.f_sm    = ctk.CTkFont(family=FAMILY, size=12)
        self.f_tiny  = ctk.CTkFont(family=FAMILY, size=11, weight="bold")
        self.f_mono  = ctk.CTkFont(family=MONO, size=12)
        self.f_micro = ctk.CTkFont(family=FAMILY, size=11)

        self.items = load_items()
        if _ensure_ids(self.items):
            save_items(self.items)
        self.categories = load_categories()
        if _cleanup_categories(self.categories, self.items):
            save_categories(self.categories)

        self._settings = load_settings()
        self.density = int(self._settings.get("density", 2))
        self._active_category = None      # None = "All Snippets"
        self.filtered = []
        self._sel = None                  # selected filtered index
        self._status_job = None

        # drag state
        self._sd_src = None; self._sd_dst = None; self._sd_moved = False
        self._cd_src = None; self._cd_dst = None; self._cd_moved = False

        self._snip_rows = []
        self._cat_rows = []

        self._build_ui()
        self._refresh_cat_list()
        self._refresh_list()

    # ── Layout ──────────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=22, pady=(16, 20))

        # Header
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 16))
        ctk.CTkLabel(header, text="📋", font=ctk.CTkFont(size=22)).pack(side="left")
        ctk.CTkLabel(header, text="Clipboard Manager", font=self.f_title,
                     text_color=COL_TEXT).pack(side="left", padx=(8, 0))

        self._theme_btn = ctk.CTkButton(
            header, text="☀", width=40, height=40, corner_radius=20,
            font=ctk.CTkFont(size=17), fg_color=COL_PANEL, hover_color=COL_PANEL2,
            text_color=COL_MUTED, command=self._toggle_theme)
        self._theme_btn.pack(side="right")
        self.status_lbl = ctk.CTkLabel(header, text="", font=self.f_ui_b,
                                       text_color=COL_SUCCESS)
        self.status_lbl.pack(side="right", padx=14)
        dens = ctk.CTkFrame(header, fg_color="transparent")
        dens.pack(side="right", padx=(0, 12))
        ctk.CTkLabel(dens, text="Density", font=self.f_sm,
                     text_color=COL_MUTED).pack(side="left", padx=(0, 8))
        self._density_slider = ctk.CTkSlider(
            dens, from_=0, to=2, number_of_steps=2, width=120,
            command=self._set_density, fg_color=COL_PANEL2,
            progress_color=COL_ACCENT, button_color=COL_ACCENT,
            button_hover_color=COL_ACCENT_HOV)
        self._density_slider.set(self.density)
        self._density_slider.pack(side="left")

        # Two-column body
        body = ctk.CTkFrame(main, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=0, minsize=300)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_left(body)
        self._build_right(body)

    # ── Left column ───────────────────────────────────────────────────────────

    def _build_left(self, parent):
        left = ctk.CTkFrame(parent, fg_color="transparent", width=300)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 18))
        left.grid_propagate(False)

        # Quick-add card
        card = ctk.CTkFrame(left, fg_color=COL_PANEL, corner_radius=16,
                            border_width=1, border_color=COL_BORDER)
        card.pack(fill="x")
        pad = ctk.CTkFrame(card, fg_color="transparent")
        pad.pack(fill="x", padx=16, pady=16)

        ctk.CTkLabel(pad, text="Add snippet", font=self.f_h,
                     text_color=COL_TEXT).pack(anchor="w", pady=(0, 10))

        self.text_input = ctk.CTkTextbox(pad, height=92, font=self.f_mono,
                                        corner_radius=10, border_width=0,
                                        fg_color=COL_PANEL2, text_color=COL_TEXT,
                                        wrap="word")
        self.text_input.pack(fill="x")
        self._add_placeholder(self.text_input, "Paste or type your snippet…")

        self.label_input = ctk.CTkEntry(pad, font=self.f_ui, height=38,
                                        corner_radius=10, border_width=0,
                                        fg_color=COL_PANEL2, text_color=COL_TEXT,
                                        placeholder_text="Label  (optional)")
        self.label_input.pack(fill="x", pady=(10, 12))

        brow = ctk.CTkFrame(pad, fg_color="transparent")
        brow.pack(fill="x")
        ctk.CTkButton(brow, text="＋  Save", command=self._save_snippet,
                      font=self.f_ui_b, height=38, corner_radius=10,
                      fg_color=COL_ACCENT, hover_color=COL_ACCENT_HOV,
                      text_color="#FFFFFF").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(brow, text="Editor…", command=self._add_with_dialog,
                      font=self.f_ui, height=38, width=84, corner_radius=10,
                      fg_color="transparent", hover_color=COL_PANEL2,
                      text_color=COL_ACCENT, border_width=1,
                      border_color=COL_BORDER).pack(side="right", padx=(8, 0))

        # Categories card
        cat_card = ctk.CTkFrame(left, fg_color=COL_PANEL, corner_radius=16,
                                border_width=1, border_color=COL_BORDER)
        cat_card.pack(fill="both", expand=True, pady=(16, 0))

        chead = ctk.CTkFrame(cat_card, fg_color="transparent")
        chead.pack(fill="x", padx=16, pady=(14, 6))
        ctk.CTkLabel(chead, text="Categories", font=self.f_h,
                     text_color=COL_TEXT).pack(side="left")
        ctk.CTkButton(chead, text="＋", width=32, height=32, corner_radius=8,
                      font=self.f_ui_b, fg_color=COL_PANEL2, hover_color=COL_BORDER,
                      text_color=COL_ACCENT, command=self._new_category
                      ).pack(side="right")

        self.cat_scroll = ctk.CTkScrollableFrame(cat_card, fg_color="transparent",
                                                corner_radius=0)
        self.cat_scroll.pack(fill="both", expand=True, padx=10, pady=(0, 6))

        crow = ctk.CTkFrame(cat_card, fg_color="transparent")
        crow.pack(fill="x", padx=16, pady=(0, 8))
        for txt, cmd in (("Rename", self._rename_category),
                         ("Delete", self._delete_category)):
            ctk.CTkButton(crow, text=txt, command=cmd, font=self.f_sm, height=30,
                          corner_radius=8, fg_color="transparent",
                          hover_color=COL_PANEL2,
                          text_color=(COL_DANGER if txt == "Delete" else COL_MUTED),
                          border_width=1, border_color=COL_BORDER, width=70
                          ).pack(side="left", padx=(0, 6))
        ctk.CTkButton(crow, text="▼", command=self._cat_move_down, font=self.f_sm,
                      width=34, height=30, corner_radius=8, fg_color="transparent",
                      hover_color=COL_PANEL2, text_color=COL_MUTED, border_width=1,
                      border_color=COL_BORDER).pack(side="right")
        ctk.CTkButton(crow, text="▲", command=self._cat_move_up, font=self.f_sm,
                      width=34, height=30, corner_radius=8, fg_color="transparent",
                      hover_color=COL_PANEL2, text_color=COL_MUTED, border_width=1,
                      border_color=COL_BORDER).pack(side="right", padx=(0, 6))

        ctk.CTkLabel(left, text="Right-click a snippet to file it under a category",
                     font=self.f_sm, text_color=COL_FAINT, wraplength=280,
                     justify="left").pack(anchor="w", pady=(10, 0))
        io_row = ctk.CTkFrame(left, fg_color="transparent")
        io_row.pack(fill="x", pady=(10, 0))
        ctk.CTkButton(io_row, text="📥  Import", command=self._import_all,
                      font=self.f_sm, height=32, corner_radius=8,
                      fg_color="transparent", hover_color=COL_PANEL2,
                      text_color=COL_MUTED, border_width=1,
                      border_color=COL_BORDER).pack(side="left", fill="x",
                                                    expand=True, padx=(0, 4))
        ctk.CTkButton(io_row, text="📤  Export", command=self._export_all,
                      font=self.f_sm, height=32, corner_radius=8,
                      fg_color="transparent", hover_color=COL_PANEL2,
                      text_color=COL_MUTED, border_width=1,
                      border_color=COL_BORDER).pack(side="left", fill="x",
                                                    expand=True, padx=(4, 0))

    # ── Right column ──────────────────────────────────────────────────────────

    def _build_right(self, parent):
        right = ctk.CTkFrame(parent, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")

        # Search
        sbar = ctk.CTkFrame(right, fg_color=COL_PANEL, corner_radius=12,
                            border_width=1, border_color=COL_BORDER, height=46)
        sbar.pack(fill="x")
        sbar.pack_propagate(False)
        ctk.CTkLabel(sbar, text="🔍", font=ctk.CTkFont(size=14)).pack(side="left",
                                                                     padx=(14, 2))
        self.search_var = ctk.StringVar()
        se = ctk.CTkEntry(sbar, textvariable=self.search_var, font=self.f_ui,
                          border_width=0, fg_color="transparent",
                          text_color=COL_TEXT, placeholder_text="Search snippets…")
        se.pack(side="left", fill="both", expand=True, padx=(4, 12), pady=6)
        self.search_var.trace_add("write", lambda *_: self._refresh_list())

        # Heading + count
        hrow = ctk.CTkFrame(right, fg_color="transparent")
        hrow.pack(fill="x", pady=(14, 6))
        self._snippets_lbl = ctk.CTkLabel(hrow, text="Saved snippets", font=self.f_h,
                                          text_color=COL_TEXT)
        self._snippets_lbl.pack(side="left")
        self.count_var = ctk.StringVar()
        ctk.CTkLabel(hrow, textvariable=self.count_var, font=self.f_sm,
                     text_color=COL_MUTED).pack(side="right")

        # Snippet list
        list_card = ctk.CTkFrame(right, fg_color=COL_PANEL, corner_radius=16,
                                 border_width=1, border_color=COL_BORDER)
        list_card.pack(fill="both", expand=True)
        self.snip_scroll = ctk.CTkScrollableFrame(list_card, fg_color="transparent")
        self.snip_scroll.pack(fill="both", expand=True, padx=6, pady=4)

        # Preview
        prev = ctk.CTkFrame(right, fg_color=COL_PANEL2, corner_radius=12)
        prev.pack(fill="x", pady=(12, 0))
        self.preview_var = ctk.StringVar(value="Select a snippet to preview it here")
        self._preview_lbl = ctk.CTkLabel(prev, textvariable=self.preview_var,
                                         font=self.f_sm, text_color=COL_MUTED,
                                         wraplength=460, justify="left", anchor="w")
        self._preview_lbl.pack(fill="x", padx=14, pady=12)

        # Actions
        arow = ctk.CTkFrame(right, fg_color="transparent")
        arow.pack(fill="x", pady=(12, 0))
        ctk.CTkButton(arow, text="📋  Copy", command=self._copy_selected,
                      font=self.f_ui_b, height=40, width=120, corner_radius=10,
                      fg_color=COL_ACCENT, hover_color=COL_ACCENT_HOV,
                      text_color="#FFFFFF").pack(side="left")
        ctk.CTkButton(arow, text="✏  Edit", command=self._edit_selected,
                      font=self.f_ui, height=40, width=90, corner_radius=10,
                      fg_color=COL_PANEL2, hover_color=COL_BORDER,
                      text_color=COL_TEXT).pack(side="left", padx=(8, 0))
        ctk.CTkButton(arow, text="🗑  Delete", command=self._delete_selected,
                      font=self.f_ui, height=40, width=100, corner_radius=10,
                      fg_color="transparent", hover_color=COL_DANGER_SOFT,
                      text_color=COL_DANGER, border_width=1,
                      border_color=COL_BORDER).pack(side="left", padx=(8, 0))
        ctk.CTkButton(arow, text="▼", command=self._move_down, font=self.f_ui,
                      width=42, height=40, corner_radius=10, fg_color=COL_PANEL2,
                      hover_color=COL_BORDER, text_color=COL_MUTED).pack(side="right")
        ctk.CTkButton(arow, text="▲", command=self._move_up, font=self.f_ui,
                      width=42, height=40, corner_radius=10, fg_color=COL_PANEL2,
                      hover_color=COL_BORDER, text_color=COL_MUTED
                      ).pack(side="right", padx=(0, 6))

    # ── Placeholder for CTkTextbox ──────────────────────────────────────────────

    def _add_placeholder(self, w, ph):
        w._ph = ph
        w.insert("1.0", ph)
        w.configure(text_color=COL_FAINT)

        def on_in(_=None):
            if getattr(w, "_is_ph", True) and w.get("1.0", "end").strip() == ph:
                w.delete("1.0", "end")
                w.configure(text_color=COL_TEXT)
            w._is_ph = False

        def on_out(_=None):
            if not w.get("1.0", "end").strip():
                w.delete("1.0", "end")
                w.insert("1.0", ph)
                w.configure(text_color=COL_FAINT)
                w._is_ph = True

        w._is_ph = True
        w.bind("<FocusIn>", on_in)
        w.bind("<FocusOut>", on_out)

    def _get_text(self):
        if getattr(self.text_input, "_is_ph", False):
            return ""
        v = self.text_input.get("1.0", "end").strip()
        return "" if v == getattr(self.text_input, "_ph", "") else v

    def _get_label(self):
        return self.label_input.get().strip()

    def _clear_add_form(self):
        self.text_input.delete("1.0", "end")
        self.text_input.insert("1.0", self.text_input._ph)
        self.text_input.configure(text_color=COL_FAINT)
        self.text_input._is_ph = True
        self.label_input.delete(0, "end")

    # ── Theme toggle ────────────────────────────────────────────────────────────

    def _set_density(self, value):
        d = int(round(float(value)))
        if d == self.density:
            return
        self.density = d
        self._settings["density"] = d
        save_settings(self._settings)
        self._refresh_cat_list()
        self._refresh_list()

    def _toggle_theme(self):
        dark = not _mode_is_dark()
        ctk.set_appearance_mode("dark" if dark else "light")
        self._theme_btn.configure(text="🌙" if dark else "☀")

    # ── Category list ───────────────────────────────────────────────────────────

    def _cat_names(self):
        return list(self.categories.keys())

    def _refresh_cat_list(self):
        for r in self._cat_rows:
            r["frame"].destroy()
        self._cat_rows = []
        valid_ids = {i["id"] for i in self.items if "id" in i}

        rows = [("__all__", "All snippets", len(self.items))]
        for name in self.categories:
            cnt = sum(1 for sid in self.categories[name] if sid in valid_ids)
            rows.append((name, name, cnt))

        for pos, (key, label, cnt) in enumerate(rows):
            self._make_cat_row(pos, key, label, cnt)
        self._paint_cat_selection()

    def _make_cat_row(self, pos, key, label, cnt):
        d = self.density
        cpad = (1, 3, 6)[d]
        ch = (22, 26, 28)[d]
        f = ctk.CTkFrame(self.cat_scroll, fg_color="transparent", corner_radius=6)
        f.pack(fill="x", pady=(0 if d == 0 else 1))
        icon = "🗂" if key != "__all__" else "▦"
        name_lbl = ctk.CTkLabel(f, text=f"{icon}  {label}", height=ch,
                                font=(self.f_sm if d == 0 else self.f_ui),
                                text_color=COL_TEXT, anchor="w")
        name_lbl.pack(side="left", padx=(10, 4), pady=cpad)
        cnt_lbl = ctk.CTkLabel(f, text=str(cnt), height=ch,
                               font=(self.f_tiny if d == 0 else self.f_sm),
                               text_color=COL_MUTED, anchor="e")
        cnt_lbl.pack(side="right", padx=(0, 12))

        r = {"frame": f, "name_lbl": name_lbl, "cnt_lbl": cnt_lbl,
             "key": key, "pos": pos}
        self._cat_rows.append(r)

        for w in (f, name_lbl, cnt_lbl):
            w.bind("<Button-1>", lambda e, p=pos: self._cat_press(p))
            w.bind("<B1-Motion>", lambda e, p=pos: self._cat_motion(e))
            w.bind("<ButtonRelease-1>", lambda e, p=pos: self._cat_release(p))
            w.bind("<Double-Button-1>", lambda e, p=pos: self._rename_category())
            w.bind("<Button-3>", lambda e, p=pos: self._cat_context(e, p))
            w.bind("<Enter>", lambda e, rr=r: self._cat_hover(rr, True))
            w.bind("<Leave>", lambda e, rr=r: self._cat_hover(rr, False))

    def _cat_hover(self, r, on):
        active = (r["key"] == "__all__" and self._active_category is None) or \
                 (r["key"] == self._active_category)
        if active:
            return
        r["frame"].configure(fg_color=COL_PANEL2 if on else "transparent")

    def _paint_cat_selection(self):
        for r in self._cat_rows:
            active = (r["key"] == "__all__" and self._active_category is None) or \
                     (r["key"] == self._active_category)
            r["frame"].configure(fg_color=COL_SEL if active else "transparent")
            r["name_lbl"].configure(text_color=COL_ACCENT if active else COL_TEXT)

    def _select_category(self, key):
        self._active_category = None if key == "__all__" else key
        if self._active_category is None:
            self._snippets_lbl.configure(text="Saved snippets")
        else:
            self._snippets_lbl.configure(text=f'“{key}”')
        self._paint_cat_selection()
        self._sel = None
        self._refresh_list()

    # category drag
    def _cat_press(self, pos):
        self._cd_src = pos; self._cd_dst = pos; self._cd_moved = False

    def _cat_motion(self, event):
        if self._cd_src is None:
            return
        self._cd_moved = True
        t = self._row_at_pointer(self._cat_rows, event.y_root)
        if t == 0:                          # can't drop above "All snippets"
            t = 1 if len(self._cat_rows) > 1 else 0
        if t == self._cd_dst:
            return
        self._cd_dst = t
        for i, r in enumerate(self._cat_rows):
            r["frame"].configure(fg_color=COL_DRAG if i == t else "transparent")

    def _cat_release(self, pos):
        src, dst, moved = self._cd_src, self._cd_dst, self._cd_moved
        self._cd_src = self._cd_dst = None
        if not moved or src is None or dst is None or src == dst or src == 0:
            self._paint_cat_selection()
            if not moved:
                key = self._cat_rows[pos]["key"] if pos < len(self._cat_rows) else "__all__"
                self._select_category(key)
            return
        names = self._cat_names()
        cs, cd = src - 1, dst - 1
        if 0 <= cs < len(names) and 0 <= cd < len(names):
            names.insert(cd, names.pop(cs))
            self.categories = {n: self.categories[n] for n in names}
            save_categories(self.categories)
            self._refresh_cat_list()
            self._flash("✓  Categories reordered")

    def _cat_selected_pos(self):
        if self._active_category is None:
            return 0
        names = self._cat_names()
        return names.index(self._active_category) + 1 if self._active_category in names else 0

    def _cat_move_up(self):
        self._cat_move(-1)

    def _cat_move_down(self):
        self._cat_move(+1)

    def _cat_move(self, d):
        pos = self._cat_selected_pos()
        if pos == 0:
            self._flash("Select a category first")
            return
        names = self._cat_names()
        cp = pos - 1
        np_ = cp + d
        if np_ < 0 or np_ >= len(names):
            return
        names.insert(np_, names.pop(cp))
        self.categories = {n: self.categories[n] for n in names}
        save_categories(self.categories)
        self._refresh_cat_list()
        self._flash("✓  Category moved")

    def _new_category(self):
        name = self._prompt("New category", "Name for the new category:")
        if not name:
            return
        name = name.strip()
        if not name:
            return
        if name in self.categories:
            self._flash("That category already exists")
            return
        self.categories[name] = []
        save_categories(self.categories)
        self._active_category = name
        self._refresh_cat_list()
        self._select_category(name)
        self._flash(f'✓  Category "{name}" created')

    def _rename_category(self):
        if self._active_category is None:
            self._flash("Select a category to rename")
            return
        old = self._active_category
        new = self._prompt("Rename category", f'Rename "{old}" to:', old)
        if not new:
            return
        new = new.strip()
        if not new or new == old:
            return
        if new in self.categories:
            self._flash("That category already exists")
            return
        self.categories = {(new if k == old else k): v
                           for k, v in self.categories.items()}
        self._active_category = new
        save_categories(self.categories)
        self._refresh_cat_list()
        self._select_category(new)
        self._flash(f'✓  Renamed to "{new}"')

    def _delete_category(self):
        if self._active_category is None:
            self._flash("Select a category to delete")
            return
        name = self._active_category
        if not self._confirm("Delete category",
                             f'Delete "{name}"? Snippets inside are kept — only the '
                             f'category is removed.'):
            return
        del self.categories[name]
        self._active_category = None
        save_categories(self.categories)
        self._refresh_cat_list()
        self._select_category("__all__")
        self._flash(f'✓  Category "{name}" deleted')

    # ── Snippet list ────────────────────────────────────────────────────────────

    def _refresh_list(self):
        raw = self.search_var.get()
        query = raw.lower().strip()

        if self._active_category is not None:
            by_id = {it.get("id"): (i, it) for i, it in enumerate(self.items)}
            cat_ids = self.categories.get(self._active_category, [])
            pool = [by_id[sid] for sid in cat_ids if sid in by_id]
        else:
            pool = list(enumerate(self.items))

        self.filtered = [
            (i, it) for i, it in pool
            if query in it.get("label", "").lower() or query in it["text"].lower()
        ]

        for r in self._snip_rows:
            r["frame"].destroy()
        self._snip_rows = []
        if getattr(self, "_empty_lbl", None) is not None:
            self._empty_lbl.destroy()
            self._empty_lbl = None
        for pos, (real_i, item) in enumerate(self.filtered):
            self._make_snip_row(pos, item)

        if not self.filtered:
            self._empty_lbl = ctk.CTkLabel(
                self.snip_scroll,
                text="No snippets here yet." if not query else "No matches.",
                font=self.f_ui, text_color=COL_FAINT)
            self._empty_lbl.pack(pady=30)

        n = len(self.items); shown = len(self.filtered)
        self.count_var.set(
            f"{n} total" + (f" · {shown} shown" if (query or self._active_category) else ""))

        if self._sel is not None and self._sel < len(self.filtered):
            self._paint_snip_selection()
        else:
            self._sel = None
            self.preview_var.set("Select a snippet to preview it here")

    def _make_snip_row(self, pos, item):
        d = self.density
        f = ctk.CTkFrame(self.snip_scroll, fg_color="transparent",
                         corner_radius=(4 if d == 0 else 8 if d == 1 else 10))
        f.pack(fill="x", pady=(0 if d == 0 else 1 if d == 1 else 2))

        main = item.get("label") or item["text"].split("\n", 1)[0]
        main = main[:88] + ("…" if len(main) > 88 else "")

        subl = None
        if d >= 2:
            title = ctk.CTkLabel(f, text=main, font=self.f_ui_b,
                                 text_color=COL_TEXT, anchor="w", justify="left")
            sub = item["text"].replace("\n", " ").strip()
            if item.get("label"):
                sub = sub[:78] + ("…" if len(sub) > 78 else "")
            else:
                sub = sub[88:168].strip()
                sub = ("…" + sub) if sub else ""
            title.pack(fill="x", padx=14, pady=(8, 0))
            if sub:
                subl = ctk.CTkLabel(f, text=sub, font=self.f_sm,
                                    text_color=COL_MUTED, anchor="w", justify="left")
                subl.pack(fill="x", padx=14, pady=(0, 8))
            else:
                title.pack_configure(pady=(10, 10))
        else:
            H = 20 if d == 0 else 26
            fnt = self.f_micro if d == 0 else self.f_ui
            title = ctk.CTkLabel(f, text=main, font=fnt, height=H,
                                 text_color=COL_TEXT, anchor="w", justify="left")
            title.pack(fill="x", padx=(10 if d == 0 else 14),
                       pady=(1 if d == 0 else 2))

        r = {"frame": f, "title": title, "sub": subl, "pos": pos}
        self._snip_rows.append(r)

        widgets = [f, title] + ([subl] if subl else [])
        for w in widgets:
            w.bind("<Button-1>", lambda e, p=pos: self._snip_press(p))
            w.bind("<B1-Motion>", lambda e: self._snip_motion(e))
            w.bind("<ButtonRelease-1>", lambda e, p=pos: self._snip_release(p))
            w.bind("<Double-Button-1>", lambda e, p=pos: self._snip_dbl(p))
            w.bind("<Button-3>", lambda e, p=pos: self._snip_context(e, p))
            w.bind("<Enter>", lambda e, rr=r: self._snip_hover(rr, True))
            w.bind("<Leave>", lambda e, rr=r: self._snip_hover(rr, False))

    def _snip_hover(self, r, on):
        if r["pos"] == self._sel:
            return
        r["frame"].configure(fg_color=COL_PANEL2 if on else "transparent")

    def _paint_snip_selection(self):
        for r in self._snip_rows:
            sel = r["pos"] == self._sel
            r["frame"].configure(fg_color=COL_SEL if sel else "transparent")
            r["title"].configure(text_color=COL_ACCENT if sel else COL_TEXT)

    def _select_snip(self, pos):
        if pos is None or pos >= len(self.filtered):
            return
        self._sel = pos
        self._paint_snip_selection()
        _, item = self.filtered[pos]
        prev = item["text"][:240].replace("\n", " ")
        self.preview_var.set(prev + ("…" if len(item["text"]) > 240 else ""))

    # snippet drag / click
    def _snip_press(self, pos):
        self._sd_src = pos; self._sd_dst = pos; self._sd_moved = False
        self._select_snip(pos)

    def _snip_motion(self, event):
        if self._sd_src is None:
            return
        self._sd_moved = True
        t = self._row_at_pointer(self._snip_rows, event.y_root)
        if t == self._sd_dst:
            return
        self._sd_dst = t
        for i, r in enumerate(self._snip_rows):
            if i == t:
                r["frame"].configure(fg_color=COL_DRAG)
            elif i == self._sel:
                r["frame"].configure(fg_color=COL_SEL)
            else:
                r["frame"].configure(fg_color="transparent")

    def _snip_release(self, pos):
        src, dst, moved = self._sd_src, self._sd_dst, self._sd_moved
        self._sd_src = self._sd_dst = None
        if not moved or src is None or dst is None or src == dst:
            self._paint_snip_selection()
            return
        if self.search_var.get().strip():
            self._flash("Clear search to reorder")
            self._refresh_list()
            return
        self._reorder(src, dst)
        self._sel = dst
        self._refresh_list()
        self._select_snip(dst)
        self._flash("✓  Reordered")

    def _reorder(self, src, dst):
        if self._active_category is not None:
            cat_ids = self.categories[self._active_category]
            sid = self.filtered[src][1].get("id")
            did = self.filtered[dst][1].get("id")
            if sid in cat_ids and did in cat_ids:
                si, di = cat_ids.index(sid), cat_ids.index(did)
                cat_ids.insert(di, cat_ids.pop(si))
                save_categories(self.categories)
        else:
            rs = self.filtered[src][0]; rd = self.filtered[dst][0]
            it = self.items.pop(rs)
            self.items.insert(rd, it)
            save_items(self.items)

    def _snip_dbl(self, pos):
        self._select_snip(pos)
        self._copy_selected()

    def _move_up(self):
        self._move(-1)

    def _move_down(self):
        self._move(+1)

    def _move(self, d):
        if self._sel is None:
            self._flash("Select a snippet first")
            return
        if self.search_var.get().strip():
            self._flash("Clear search to reorder")
            return
        new = self._sel + d
        if new < 0 or new >= len(self.filtered):
            return
        self._reorder(self._sel, new)
        self._sel = new
        self._refresh_list()
        self._select_snip(new)

    def _row_at_pointer(self, rows, y_root):
        for i, r in enumerate(rows):
            f = r["frame"]
            try:
                top = f.winfo_rooty(); h = f.winfo_height()
            except Exception:
                continue
            if y_root < top + h:
                return i
        return len(rows) - 1

    # ── CRUD ────────────────────────────────────────────────────────────────────

    def _save_snippet(self):
        import uuid
        text = self._get_text()
        if not text:
            self._flash("Enter some text first")
            return
        item = {"id": str(uuid.uuid4()), "label": self._get_label(), "text": text}
        self.items.append(item)
        if self._active_category is not None:
            self.categories[self._active_category].append(item["id"])
            save_categories(self.categories)
        save_items(self.items)
        self._clear_add_form()
        self._refresh_cat_list()
        self._refresh_list()
        self._flash("✓  Snippet saved")

    def _add_with_dialog(self):
        import uuid
        prefill = {"label": self._get_label(), "text": self._get_text()}
        dlg = SnippetDialog(self.root, self, title="Add Snippet", item=prefill)
        if dlg.result:
            item = dlg.result
            item.setdefault("id", str(uuid.uuid4()))
            self.items.append(item)
            if self._active_category is not None:
                self.categories[self._active_category].append(item["id"])
                save_categories(self.categories)
            save_items(self.items)
            self._clear_add_form()
            self._refresh_cat_list()
            self._refresh_list()
            self._flash("✓  Snippet saved")

    def _edit_selected(self):
        if self._sel is None:
            self._flash("Select a snippet first")
            return
        idx, item = self.filtered[self._sel]
        dlg = SnippetDialog(self.root, self, title="Edit Snippet", item=item)
        if dlg.result:
            dlg.result["id"] = item.get("id", str(__import__("uuid").uuid4()))
            self.items[idx] = dlg.result
            save_items(self.items)
            self._refresh_list()
            self._select_snip(self._sel)
            self._flash("✓  Snippet updated")

    def _copy_selected(self):
        if self._sel is None:
            self._flash("Select a snippet first")
            return
        _, item = self.filtered[self._sel]
        if _copy_to_clipboard(item["text"], self.root):
            self._flash("✓  Copied to clipboard")
        else:
            self._flash("Copy failed — install pyperclip")

    def _delete_selected(self):
        if self._sel is None:
            self._flash("Select a snippet first")
            return
        idx, item = self.filtered[self._sel]
        label = item.get("label") or item["text"][:40].replace("\n", " ")
        item_id = item.get("id")

        if self._active_category is not None:
            dlg = DeleteChoiceDialog(self.root, self, label, self._active_category)
            if dlg.choice is None:
                return
            if dlg.choice == "category":
                if item_id in self.categories[self._active_category]:
                    self.categories[self._active_category].remove(item_id)
                    save_categories(self.categories)
                self._sel = None
                self._refresh_cat_list()
                self._refresh_list()
                self._flash("✓  Removed from category")
                return
        else:
            if not self._confirm("Delete snippet", f'Delete "{label}"?'):
                return

        if item_id:
            for ids in self.categories.values():
                if item_id in ids:
                    ids.remove(item_id)
            save_categories(self.categories)
        self.items.pop(idx)
        save_items(self.items)
        self._sel = None
        self._refresh_cat_list()
        self._refresh_list()
        self._flash("✓  Deleted")

    # ── Context menus (native, themed) ──────────────────────────────────────────

    def _menu(self):
        return tk.Menu(self.root, tearoff=0, bg=_c(COL_PANEL), fg=_c(COL_TEXT),
                       activebackground=_c(COL_SEL), activeforeground=_c(COL_ACCENT),
                       relief="flat", bd=0, font=(FAMILY, 10))

    def _snip_context(self, event, pos):
        self._snip_press(pos)
        self._sd_src = None
        if pos >= len(self.filtered):
            return
        _, item = self.filtered[pos]
        item_id = item.get("id")
        m = self._menu()
        m.add_command(label="📋  Copy", command=self._copy_selected)
        m.add_command(label="✏  Edit", command=self._edit_selected)
        m.add_separator()

        add_menu = self._menu()
        if self.categories:
            for name, ids in self.categories.items():
                if item_id in ids:
                    add_menu.add_command(label=f"✓  {name}", foreground=_c(COL_FAINT),
                                         command=lambda n=name: self._flash(f'Already in "{n}"'))
                else:
                    add_menu.add_command(label=f"    {name}",
                                         command=lambda n=name, s=item_id: self._ctx_add(n, s))
            add_menu.add_separator()
        add_menu.add_command(label="＋  New category…", command=self._new_category)
        m.add_cascade(label="🗂  Add to category", menu=add_menu)

        member = [n for n, ids in self.categories.items() if item_id in ids]
        if member:
            rem = self._menu()
            for name in member:
                rem.add_command(label=f"    {name}",
                                command=lambda n=name, s=item_id: self._ctx_remove(n, s))
            m.add_cascade(label="✂  Remove from category", menu=rem)

        m.add_separator()
        m.add_command(label="🗑  Delete", foreground=_c(COL_DANGER),
                      command=self._delete_selected)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()
        return "break"

    def _cat_context(self, event, pos):
        if pos < len(self._cat_rows):
            self._select_category(self._cat_rows[pos]["key"])
        m = self._menu()
        m.add_command(label="＋  New category…", command=self._new_category)
        if pos > 0:
            m.add_command(label="✏  Rename", command=self._rename_category)
            m.add_separator()
            m.add_command(label="🗑  Delete category", foreground=_c(COL_DANGER),
                          command=self._delete_category)
        try:
            m.tk_popup(event.x_root, event.y_root)
        finally:
            m.grab_release()
        return "break"

    def _ctx_add(self, name, sid):
        if sid not in self.categories[name]:
            self.categories[name].append(sid)
            save_categories(self.categories)
            self._refresh_cat_list()
            self._flash(f'✓  Added to "{name}"')

    def _ctx_remove(self, name, sid):
        if sid in self.categories[name]:
            self.categories[name].remove(sid)
            save_categories(self.categories)
            self._refresh_cat_list()
            self._refresh_list()
            self._flash(f'✓  Removed from "{name}"')

    # ── Small modal helpers (themed) ────────────────────────────────────────────

    def _prompt(self, title, message, initial=""):
        return _TextPrompt(self.root, self, title, message, initial).value

    def _confirm(self, title, message):
        return _ConfirmDialog(self.root, self, title, message).ok

    # ── Status flash ────────────────────────────────────────────────────────────

    # ── Import / Export (full backup) ────────────────────────────────────────────

    def _export_all(self):
        from tkinter import filedialog
        import datetime
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export snippets & settings",
            defaultextension=".json",
            initialfile="clipboard-manager-backup.json",
            filetypes=[("JSON backup", "*.json"), ("All files", "*.*")])
        if not path:
            return
        bundle = {
            "app": "Clipboard Manager",
            "version": 1,
            "exported": datetime.datetime.now().isoformat(timespec="seconds"),
            "items": self.items,
            "categories": self.categories,
            "settings": self._settings,
        }
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(bundle, f, indent=2, ensure_ascii=False)
            self._flash("✓  Exported backup")
        except Exception:
            self._flash("Export failed")

    def _import_all(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            parent=self.root, title="Import snippets & settings",
            filetypes=[("JSON backup", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self._flash("Could not read that file")
            return

        items = cats = settings = None
        if isinstance(data, dict) and "items" in data:
            items = data.get("items")
            cats = data.get("categories")
            settings = data.get("settings")
        elif isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            cats = data
        if items is None and cats is None:
            self._flash("Not a valid backup file")
            return

        if not self._confirm(
                "Import backup",
                "Replace your current snippets and categories with the imported "
                "file? Export first if you want to keep a copy — this can't be undone."):
            return

        if items is not None:
            self.items = items if isinstance(items, list) else []
            _ensure_ids(self.items)
            save_items(self.items)
        if cats is not None and isinstance(cats, dict):
            self.categories = cats
        _cleanup_categories(self.categories, self.items)
        save_categories(self.categories)
        if isinstance(settings, dict):
            self._settings.update(settings)
            self.density = int(self._settings.get("density", self.density))
            save_settings(self._settings)
            try:
                self._density_slider.set(self.density)
            except Exception:
                pass

        self._active_category = None
        self._sel = None
        self._snippets_lbl.configure(text="Saved snippets")
        self._refresh_cat_list()
        self._refresh_list()
        self._flash("✓  Imported backup")

    def _flash(self, msg):
        if self._status_job:
            self.root.after_cancel(self._status_job)
        self.status_lbl.configure(text=msg)
        self._status_job = self.root.after(2800, lambda: self.status_lbl.configure(text=""))


# ── Themed prompt / confirm dialogs ─────────────────────────────────────────────

class _TextPrompt(ctk.CTkToplevel):
    def __init__(self, parent, app, title, message, initial=""):
        super().__init__(parent)
        self.app = app; self.value = None
        self.title(title)
        self.configure(fg_color=COL_BG)
        self.resizable(False, False)
        self.transient(parent)
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=22, pady=20)
        ctk.CTkLabel(wrap, text=message, font=app.f_ui, text_color=COL_TEXT,
                     wraplength=320, justify="left").pack(anchor="w", pady=(0, 10))
        self._var = ctk.StringVar(value=initial)
        ent = ctk.CTkEntry(wrap, textvariable=self._var, font=app.f_ui, width=320,
                           height=40, corner_radius=10, border_width=1,
                           fg_color=COL_PANEL, border_color=COL_BORDER,
                           text_color=COL_TEXT)
        ent.pack(fill="x", pady=(0, 16))
        ent.bind("<Return>", lambda e: self._ok())
        ent.bind("<Escape>", lambda e: self.destroy())
        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="OK", command=self._ok, font=app.f_ui_b, height=38,
                      corner_radius=10, fg_color=COL_ACCENT, hover_color=COL_ACCENT_HOV,
                      text_color="#FFFFFF").pack(side="right")
        ctk.CTkButton(btns, text="Cancel", command=self.destroy, font=app.f_ui,
                      height=38, width=90, corner_radius=10, fg_color=COL_PANEL2,
                      hover_color=COL_BORDER, text_color=COL_TEXT
                      ).pack(side="right", padx=(0, 10))
        self.after(80, lambda: (self._safe_grab(), ent.focus_set()))
        self.geometry(f"+{parent.winfo_rootx() + 110}+{parent.winfo_rooty() + 120}")
        self.wait_window()

    def _safe_grab(self):
        try:
            self.grab_set(); self.focus_force()
        except Exception:
            pass

    def _ok(self):
        self.value = self._var.get()
        self.destroy()


class _ConfirmDialog(ctk.CTkToplevel):
    def __init__(self, parent, app, title, message):
        super().__init__(parent)
        self.app = app; self.ok = False
        self.title(title)
        self.configure(fg_color=COL_BG)
        self.resizable(False, False)
        self.transient(parent)
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=22, pady=20)
        ctk.CTkLabel(wrap, text=title, font=app.f_h, text_color=COL_TEXT
                     ).pack(anchor="w", pady=(0, 6))
        ctk.CTkLabel(wrap, text=message, font=app.f_ui, text_color=COL_MUTED,
                     wraplength=340, justify="left").pack(anchor="w", pady=(0, 16))
        btns = ctk.CTkFrame(wrap, fg_color="transparent")
        btns.pack(fill="x")
        ctk.CTkButton(btns, text="Delete", command=self._confirm, font=app.f_ui_b,
                      height=38, corner_radius=10, fg_color=COL_DANGER,
                      hover_color=COL_DANGER_HOV, text_color="#FFFFFF").pack(side="right")
        ctk.CTkButton(btns, text="Cancel", command=self.destroy, font=app.f_ui,
                      height=38, width=90, corner_radius=10, fg_color=COL_PANEL2,
                      hover_color=COL_BORDER, text_color=COL_TEXT
                      ).pack(side="right", padx=(0, 10))
        self.after(80, self._safe_grab)
        self.geometry(f"+{parent.winfo_rootx() + 110}+{parent.winfo_rooty() + 120}")
        self.wait_window()

    def _safe_grab(self):
        try:
            self.grab_set(); self.focus_force()
        except Exception:
            pass

    def _confirm(self):
        self.ok = True
        self.destroy()


# ── Entry point ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    if sys.platform == "win32":
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass
    if "_copy_text" in globals():          # macOS build: give _copy_text the tk root
        _tk_root = root
    # Window / dock icon
    try:
        _ibase = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
        if sys.platform == "win32" and os.path.exists(os.path.join(_ibase, "icon.ico")):
            root.iconbitmap(os.path.join(_ibase, "icon.ico"))
        elif os.path.exists(os.path.join(_ibase, "icon.png")):
            root.iconphoto(True, tk.PhotoImage(file=os.path.join(_ibase, "icon.png")))
    except Exception:
        pass
    ClipboardManager(root)
    root.mainloop()
