# Prepared with love by YakomoDev - https://ko-fi.com/yakomodev
"""
graphs_screen.py — Monthly Graphs Screen for Mission Ui
Canvas-based chart rendering (no matplotlib required).
"""

import tkinter as tk
from tkinter import messagebox
import sqlite3
import json
import os
import math
import calendar
import datetime

# ── Colour Palette (matches app.py) ──────────────────────────────────────────
import theme_manager as tm

BG_DARK = tm.BG_DARK
BG_CARD = tm.BG_CARD
BG_CARD_HEADER = tm.BG_CARD_HEADER
BORDER_COLOR = tm.BORDER_COLOR
TEXT_WHITE = tm.TEXT_WHITE
TEXT_MUTED = tm.TEXT_MUTED
ACCENT_PURPLE = tm.ACCENT_PURPLE
ACCENT_CYAN = tm.ACCENT_CYAN
SUCCESS_GREEN = tm.SUCCESS_GREEN
GLOW_COLOR = tm.GLOW_COLOR
WARN_ORANGE = tm.WARN_ORANGE
ERR_RED = tm.ERR_RED

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "data", "missions.db")

def get_model_path():
    agent_dir = os.path.join(APP_DIR, "agent")
    if os.path.exists(agent_dir):
        try:
            gguf_files = [f for f in os.listdir(agent_dir) if f.lower().endswith(".gguf")]
            if gguf_files:
                # Prioritize larger models by sorting by file size descending
                gguf_files.sort(key=lambda x: os.path.getsize(os.path.join(agent_dir, x)), reverse=True)
                return os.path.join(agent_dir, gguf_files[0])
        except Exception:
            pass
    return os.path.join(agent_dir, "Gemma 3 1B.gguf")

# ── Data helpers ──────────────────────────────────────────────────────────────

def compute_day_stars(main_tasks, side_tasks):
    """Return a dict of star stats for one day."""
    def group_done(groups):
        done = 0.0
        mx   = 0.0
        for g in groups:
            g_stars = float(g.get("stars", 0))
            mx += g_stars
            for item in g.get("items", []):
                if item.get("done"):
                    done += g_stars * float(item.get("percent", 0)) / 100.0
        return done, mx

    def count_tasks(groups):
        done_count = 0
        total_count = 0
        for g in groups:
            items = g.get("items", [])
            if items:
                for item in items:
                    total_count += 1
                    if item.get("done"):
                        done_count += 1
            else:
                total_count += 1
                if g.get("done", False):
                    done_count += 1
        return done_count, total_count

    def count_packs(groups):
        done_packs = 0
        total_packs = len(groups)
        for g in groups:
            items = g.get("items", [])
            if items:
                # Pack is done if all items inside are done
                if all(item.get("done") for item in items):
                    done_packs += 1
            else:
                # Pack with no items is done if the group itself is done
                if g.get("done", False):
                    done_packs += 1
        return done_packs, total_packs

    m_done, m_max = group_done(main_tasks)
    s_done, s_max = group_done(side_tasks)
    t_done = m_done + s_done
    t_max  = m_max  + s_max

    m_tdone, m_ttotal = count_tasks(main_tasks)
    s_tdone, s_ttotal = count_tasks(side_tasks)
    t_tdone = m_tdone + s_tdone
    t_ttotal = m_ttotal + s_ttotal

    m_pdone, m_ptotal = count_packs(main_tasks)
    s_pdone, s_ptotal = count_packs(side_tasks)
    t_pdone = m_pdone + s_pdone
    t_ptotal = m_ptotal + s_ptotal

    return {
        "total_done":   t_done,
        "total_max":    t_max,
        "main_done":    m_done,
        "main_max":     m_max,
        "side_done":    s_done,
        "side_max":     s_max,
        "total_missed": t_max - t_done,
        "main_missed":  m_max - m_done,
        "side_missed":  s_max - s_done,
        "ratio_total":  (t_done / t_max * 100) if t_max > 0 else 0.0,
        "ratio_main":   (m_done / m_max * 100) if m_max > 0 else 0.0,
        "ratio_side":   (s_done / s_max * 100) if s_max > 0 else 0.0,

        # Task counts:
        "total_tasks_done":   t_tdone,
        "total_tasks_undone": t_ttotal - t_tdone,
        "main_tasks_done":    m_tdone,
        "main_tasks_undone":  m_ttotal - m_tdone,
        "side_tasks_done":    s_tdone,
        "side_tasks_undone":  s_ttotal - s_tdone,

        # Pack counts:
        "total_packs_done":   t_pdone,
        "total_packs_undone": t_ptotal - t_pdone,
        "main_packs_done":    m_pdone,
        "main_packs_undone":  m_ptotal - m_pdone,
        "side_packs_done":    s_pdone,
        "side_packs_undone":  s_ptotal - s_pdone,
        
        # Pack ratios:
        "ratio_packs_total":  (t_pdone / t_ptotal * 100) if t_ptotal > 0 else 0.0,
        "ratio_packs_main":   (m_pdone / m_ptotal * 100) if m_ptotal > 0 else 0.0,
        "ratio_packs_side":   (s_pdone / s_ptotal * 100) if s_ptotal > 0 else 0.0,
    }


def load_month_stats(year, month):
    """
    Query DB for all logged days in year/month.
    Returns dict: {day_number (int): stats_dict} — only for logged days.
    Missing days are absent from the dict (not 0).
    """
    pattern = f"{year}-{month:02d}-%"
    result  = {}
    try:
        conn = sqlite3.connect(DB_PATH)
        c    = conn.cursor()
        c.execute(
            "SELECT date, main_tasks, side_tasks FROM days WHERE date LIKE ?",
            (pattern,)
        )
        rows = c.fetchall()
        conn.close()
        for date_str, r_main, r_side in rows:
            day_num = int(date_str.split("-")[2])
            main_tasks = json.loads(r_main) if r_main else []
            side_tasks = json.loads(r_side) if r_side else []
            result[day_num] = compute_day_stars(main_tasks, side_tasks)
    except Exception as e:
        print(f"[graphs] DB load error: {e}")
    return result


def load_monthly_comment(year, month):
    key = f"{year}-{month:02d}"
    try:
        conn = sqlite3.connect(DB_PATH)
        c    = conn.cursor()
        c.execute("SELECT comment FROM monthly_comments WHERE year_month = ?", (key,))
        row = c.fetchone()
        conn.close()
        return row[0] if row else ""
    except Exception:
        return ""


def save_monthly_comment(year, month, comment):
    key = f"{year}-{month:02d}"
    try:
        conn = sqlite3.connect(DB_PATH)
        c    = conn.cursor()
        c.execute(
            "INSERT INTO monthly_comments (year_month, comment) VALUES (?, ?) "
            "ON CONFLICT(year_month) DO UPDATE SET comment = excluded.comment",
            (key, comment)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"[graphs] save comment error: {e}")


# ── Metric key helper ─────────────────────────────────────────────────────────

METRIC_KEYS = {
    # (scope, mode) → stats_dict key
    ("total", "done"):          "total_done",
    ("total", "missed"):        "total_missed",
    ("total", "done_tasks"):    "total_tasks_done",
    ("total", "undone_tasks"):  "total_tasks_undone",
    ("total", "ratio"):         "ratio_total",
    ("total", "done_packs"):    "total_packs_done",
    ("total", "undone_packs"):  "total_packs_undone",
    ("total", "ratio_packs"):   "ratio_packs_total",

    ("main",  "done"):          "main_done",
    ("main",  "missed"):        "main_missed",
    ("main",  "done_tasks"):    "main_tasks_done",
    ("main",  "undone_tasks"):  "main_tasks_undone",
    ("main",  "ratio"):         "ratio_main",
    ("main",  "done_packs"):    "main_packs_done",
    ("main",  "undone_packs"):  "main_packs_undone",
    ("main",  "ratio_packs"):   "ratio_packs_main",

    ("side",  "done"):          "side_done",
    ("side",  "missed"):        "side_missed",
    ("side",  "done_tasks"):    "side_tasks_done",
    ("side",  "undone_tasks"):  "side_tasks_undone",
    ("side",  "ratio"):         "ratio_side",
    ("side",  "done_packs"):    "side_packs_done",
    ("side",  "undone_packs"):  "side_packs_undone",
    ("side",  "ratio_packs"):   "ratio_packs_side",
}

# METRIC_LABELS deleted as translations are dynamic now


# ── GraphsScreen ──────────────────────────────────────────────────────────────

class GraphsScreen(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=tm.BG_DARK)
        self.parent = parent

        today = datetime.date.today()
        self.current_year  = today.year
        self.current_month = today.month

        # Selection state
        self.chart_type = tk.StringVar(value="line")   # line | bar | pie
        self.metric_scope = tk.StringVar(value="total") # total | main | side
        self.metric_mode  = tk.StringVar(value="done")  # done | missed | ratio

        # Cached data
        self._month_stats = {}    # {day_num: stats_dict}
        self._ai_running  = False

        self._build_ui()
        self.refresh()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(0, weight=0, minsize=200)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=0)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)

        self._build_header()
        self._build_left_panel()
        self._build_chart_area()
        self._build_bottom_panel()

    def _build_header(self):
        hdr = tk.Frame(self, bg=tm.BG_CARD, highlightbackground=tm.BORDER_COLOR, highlightthickness=1)
        hdr.grid(row=0, column=0, columnspan=2, sticky="ew")

        back_btn = tk.Button(hdr, text=tm.tr("menu_back"), bg=tm.BG_DARK, fg=tm.TEXT_MUTED, relief="flat",
                             font=("Helvetica", 10, "bold"), padx=14, pady=8,
                             command=self.parent.show_start_screen)
        back_btn.pack(side="left", padx=10, pady=8)
        back_btn.bind("<Enter>", lambda e: back_btn.config(bg=tm.ACCENT_PURPLE, fg=tm.BG_DARK))
        back_btn.bind("<Leave>", lambda e: back_btn.config(bg=tm.BG_DARK, fg=tm.TEXT_MUTED))

        tk.Label(hdr, text=tm.tr("graphs_dashboard"), bg=tm.BG_CARD, fg=tm.TEXT_WHITE,
                 font=("Helvetica", 14, "bold")).pack(side="left", padx=10)

        # Month navigation — right side
        nav = tk.Frame(hdr, bg=tm.BG_CARD)
        nav.pack(side="right", padx=15, pady=8)

        prev_btn = tk.Button(nav, text="◀", bg=tm.BG_DARK, fg=tm.TEXT_MUTED, relief="flat",
                             font=("Helvetica", 10, "bold"), padx=8, pady=4,
                             command=self._prev_month)
        prev_btn.pack(side="left")
        prev_btn.bind("<Enter>", lambda e: prev_btn.config(fg=tm.ACCENT_CYAN))
        prev_btn.bind("<Leave>", lambda e: prev_btn.config(fg=tm.TEXT_MUTED))

        self.month_lbl = tk.Label(nav, text="", bg=tm.BG_CARD, fg=tm.ACCENT_CYAN,
                                  font=("Helvetica", 12, "bold"), width=16)
        self.month_lbl.pack(side="left", padx=8)

        next_btn = tk.Button(nav, text="▶", bg=tm.BG_DARK, fg=tm.TEXT_MUTED, relief="flat",
                             font=("Helvetica", 10, "bold"), padx=8, pady=4,
                             command=self._next_month)
        next_btn.pack(side="left")
        next_btn.bind("<Enter>", lambda e: next_btn.config(fg=tm.ACCENT_CYAN))
        next_btn.bind("<Leave>", lambda e: next_btn.config(fg=tm.TEXT_MUTED))

    def _build_left_panel(self):
        panel = tk.Frame(self, bg=tm.BG_CARD, highlightbackground=tm.BORDER_COLOR, highlightthickness=1)
        panel.grid(row=1, column=0, sticky="nsew", padx=(10, 5), pady=(8, 4))

        # Chart type
        tk.Label(panel, text=tm.tr("chart_type"), bg=tm.BG_CARD, fg=tm.ACCENT_PURPLE,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=12, pady=(14, 4))

        for label_key, val in [("chart_line", "line"), ("chart_bar", "bar"),
                            ("chart_pie", "pie")]:
            rb = tk.Radiobutton(panel, text=tm.tr(label_key), variable=self.chart_type, value=val,
                                bg=tm.BG_CARD, fg=tm.TEXT_WHITE, selectcolor=tm.BG_DARK,
                                activebackground=tm.BG_CARD, activeforeground=tm.ACCENT_PURPLE,
                                font=("Helvetica", 10), command=self._on_controls_changed)
            rb.pack(anchor="w", padx=16, pady=2)

        tk.Frame(panel, bg=tm.BORDER_COLOR, height=1).pack(fill="x", padx=12, pady=10)

        # Scope
        tk.Label(panel, text=tm.tr("scope"), bg=tm.BG_CARD, fg=tm.ACCENT_CYAN,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=12, pady=(4, 4))

        for label_key, val in [("scope_total", "total"),
                            ("scope_main", "main"),
                            ("scope_side", "side")]:
            rb = tk.Radiobutton(panel, text=tm.tr(label_key), variable=self.metric_scope, value=val,
                                bg=tm.BG_CARD, fg=tm.TEXT_WHITE, selectcolor=tm.BG_DARK,
                                activebackground=tm.BG_CARD, activeforeground=tm.ACCENT_CYAN,
                                font=("Helvetica", 10), command=self._on_controls_changed)
            rb.pack(anchor="w", padx=16, pady=2)

        tk.Frame(panel, bg=tm.BORDER_COLOR, height=1).pack(fill="x", padx=12, pady=10)

        # Mode
        tk.Label(panel, text=tm.tr("mode"), bg=tm.BG_CARD, fg=tm.GLOW_COLOR,
                 font=("Helvetica", 9, "bold")).pack(anchor="w", padx=12, pady=(4, 4))

        for label_key, val in [("mode_done", "done"),
                            ("mode_missed", "missed"),
                            ("mode_done_tasks", "done_tasks"),
                            ("mode_undone_tasks", "undone_tasks"),
                            ("mode_ratio", "ratio"),
                            ("mode_done_packs", "done_packs"),
                            ("mode_undone_packs", "undone_packs"),
                            ("mode_packs_ratio", "ratio_packs")]:
            rb = tk.Radiobutton(panel, text=tm.tr(label_key), variable=self.metric_mode, value=val,
                                bg=tm.BG_CARD, fg=tm.TEXT_WHITE, selectcolor=tm.BG_DARK,
                                activebackground=tm.BG_CARD, activeforeground=tm.GLOW_COLOR,
                                font=("Helvetica", 10), command=self._on_controls_changed)
            rb.pack(anchor="w", padx=16, pady=2)

    def _build_chart_area(self):
        chart_frame = tk.Frame(self, bg=tm.BG_DARK)
        chart_frame.grid(row=1, column=1, sticky="nsew", padx=(5, 10), pady=(8, 4))
        chart_frame.rowconfigure(0, weight=1)
        chart_frame.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(chart_frame, bg=tm.BG_DARK, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        self.canvas.bind("<Configure>", lambda e: self._draw_chart())
        self.canvas.bind("<Button-3>", self._show_context_menu)
        self.canvas.bind("<Button-2>", self._show_context_menu)

    def _build_bottom_panel(self):
        bottom = tk.Frame(self, bg=tm.BG_DARK)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew", padx=10, pady=(0, 10))

        # Averages card
        _ar = tm._current_language == "Arabic"
        avg_card = tk.Frame(bottom, bg=tm.BG_CARD, highlightbackground=tm.BORDER_COLOR, highlightthickness=1)
        avg_card.pack(side="left", fill="both", expand=True, padx=0 if _ar else (0, 6))

        tk.Label(avg_card, text=tm.tr("monthly_averages"),
                 bg=tm.BG_CARD, fg=tm.ACCENT_CYAN, font=("Helvetica", 9, "bold")).pack(anchor="w", padx=12, pady=(8, 4))

        self.avg_vars = {}
        avg_inner = tk.Frame(avg_card, bg=tm.BG_CARD)
        avg_inner.pack(fill="x", padx=12, pady=(0, 10))

        avg_defs = [
            ("avg_t_done",   tm.tr("avg_t_done")),
            ("avg_m_done",   tm.tr("avg_m_done")),
            ("avg_s_done",   tm.tr("avg_s_done")),
            ("avg_t_ratio",  tm.tr("avg_t_ratio")),
            ("avg_m_ratio",  tm.tr("avg_m_ratio")),
            ("avg_s_ratio",  tm.tr("avg_s_ratio")),
        ]
        for col_idx, (key, label) in enumerate(avg_defs):
            var = tk.StringVar(value="—")
            self.avg_vars[key] = var
            cell = tk.Frame(avg_inner, bg=tm.BG_CARD)
            cell.grid(row=0, column=col_idx, padx=10, pady=4, sticky="w")
            tk.Label(cell, text=label, bg=tm.BG_CARD, fg=tm.TEXT_MUTED, font=("Helvetica", 8)).pack(anchor="w")
            tk.Label(cell, textvariable=var, bg=tm.BG_CARD, fg=tm.TEXT_WHITE, font=("Helvetica", 11, "bold")).pack(anchor="w")

        # AI section card
        ai_card = tk.Frame(bottom, bg=tm.BG_CARD, highlightbackground=tm.BORDER_COLOR, highlightthickness=1)
        if not _ar:
            ai_card.pack(side="right", fill="both", expand=True, padx=(6, 0))

        ai_header = tk.Frame(ai_card, bg=tm.BG_CARD)
        ai_header.pack(fill="x", padx=12, pady=(8, 4))

        tk.Label(ai_header, text=tm.tr("monthly_ai_summary"),
                 bg=tm.BG_CARD, fg=tm.ACCENT_CYAN, font=("Helvetica", 9, "bold")).pack(side="left")

        self.ai_status_lbl = tk.Label(ai_header, text="", bg=tm.BG_CARD, fg=tm.TEXT_MUTED,
                                      font=("Helvetica", 8))
        self.ai_status_lbl.pack(side="left", padx=10)

        self.ai_gen_btn = tk.Button(ai_header, text=tm.tr("generate"), bg=tm.BG_DARK, fg=tm.ACCENT_CYAN,
                                    relief="flat", font=("Helvetica", 8, "bold"), padx=8, pady=3,
                                    command=self._generate_ai_comment)
        self.ai_gen_btn.pack(side="right")
        self.ai_gen_btn.bind("<Enter>", lambda e: self.ai_gen_btn.config(bg=tm.ACCENT_CYAN, fg=tm.BG_DARK))
        self.ai_gen_btn.bind("<Leave>", lambda e: self.ai_gen_btn.config(bg=tm.BG_DARK, fg=tm.ACCENT_CYAN))

        _ar = tm._current_language == "Arabic"
        self.ai_text = tk.Text(ai_card, bg=tm.BG_DARK, fg=tm.TEXT_WHITE, insertbackground=tm.TEXT_WHITE,
                               font=("Amiri", 11) if _ar else ("Helvetica", 9), relief="flat", height=4, wrap="word")
        self.ai_text.pack(fill="both", expand=True, padx=12, pady=(0, 10))
        if _ar:
            self.ai_text.tag_configure("rtl", justify="right")
            self.ai_text.config(state="disabled")
        else:
            self.ai_text.bind("<KeyRelease>", self._on_ai_text_edited)

    # ── Navigation ────────────────────────────────────────────────────────────

    def _prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year  -= 1
        else:
            self.current_month -= 1
        self.refresh()

    def _next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year  += 1
        else:
            self.current_month += 1
        self.refresh()

    # ── Refresh (data + redraw) ───────────────────────────────────────────────

    def refresh(self):
        self._month_stats = load_month_stats(self.current_year, self.current_month)
        self.month_lbl.config(
            text=tm.format_month(self.current_year, self.current_month)
        )
        self._draw_chart()
        self._update_averages()

        # Load saved AI comment
        comment = load_monthly_comment(self.current_year, self.current_month)
        _ar = tm._current_language == "Arabic"
        self.ai_text.config(state="normal")
        self.ai_text.delete("1.0", tk.END)
        if comment:
            self.ai_text.insert("1.0", tm.shape_for_display(comment))
            if _ar:
                self.ai_text.tag_add("rtl", "1.0", "end")
        if _ar:
            self.ai_text.config(state="disabled")
        else:
            # Auto-regenerate monthly commentary on entering/refreshing graphs page
            self.after(100, self._generate_ai_comment)

    def _on_controls_changed(self):
        self._draw_chart()
        self._update_averages()

    # ── Chart Drawing ─────────────────────────────────────────────────────────

    def _get_metric_key(self):
        return METRIC_KEYS.get((self.metric_scope.get(), self.metric_mode.get()), "total_done")

    def _get_metric_label(self):
        scope = self.metric_scope.get()
        mode = self.metric_mode.get()
        key_map = {
            ("total", "done"):          "avg_t_done",
            ("total", "missed"):        "avg_t_missed",
            ("total", "done_tasks"):    "avg_t_done_tasks",
            ("total", "undone_tasks"):  "avg_t_undone_tasks",
            ("total", "ratio"):         "avg_t_ratio",
            ("total", "done_packs"):    "avg_t_done_packs",
            ("total", "undone_packs"):  "avg_t_undone_packs",
            ("total", "ratio_packs"):   "avg_t_ratio_packs",

            ("main",  "done"):          "avg_m_done",
            ("main",  "missed"):        "avg_m_missed",
            ("main",  "done_tasks"):    "avg_m_done_tasks",
            ("main",  "undone_tasks"):  "avg_m_undone_tasks",
            ("main",  "ratio"):         "avg_m_ratio",
            ("main",  "done_packs"):    "avg_m_done_packs",
            ("main",  "undone_packs"):  "avg_m_undone_packs",
            ("main",  "ratio_packs"):   "avg_m_ratio_packs",

            ("side",  "done"):          "avg_s_done",
            ("side",  "missed"):        "avg_s_missed",
            ("side",  "done_tasks"):    "avg_s_done_tasks",
            ("side",  "undone_tasks"):  "avg_s_undone_tasks",
            ("side",  "ratio"):         "avg_s_ratio",
            ("side",  "done_packs"):    "avg_s_done_packs",
            ("side",  "undone_packs"):  "avg_s_undone_packs",
            ("side",  "ratio_packs"):   "avg_s_ratio_packs",
        }
        tr_key = key_map.get((scope, mode), "avg_t_done")
        return tm.tr(tr_key)

    def _get_metric_label_raw(self):
        scope = self.metric_scope.get()
        mode = self.metric_mode.get()
        key_map = {
            ("total", "done"):          "avg_t_done",
            ("total", "missed"):        "avg_t_missed",
            ("total", "done_tasks"):    "avg_t_done_tasks",
            ("total", "undone_tasks"):  "avg_t_undone_tasks",
            ("total", "ratio"):         "avg_t_ratio",
            ("total", "done_packs"):    "avg_t_done_packs",
            ("total", "undone_packs"):  "avg_t_undone_packs",
            ("total", "ratio_packs"):   "avg_t_ratio_packs",

            ("main",  "done"):          "avg_m_done",
            ("main",  "missed"):        "avg_m_missed",
            ("main",  "done_tasks"):    "avg_m_done_tasks",
            ("main",  "undone_tasks"):  "avg_m_undone_tasks",
            ("main",  "ratio"):         "avg_m_ratio",
            ("main",  "done_packs"):    "avg_m_done_packs",
            ("main",  "undone_packs"):  "avg_m_undone_packs",
            ("main",  "ratio_packs"):   "avg_m_ratio_packs",

            ("side",  "done"):          "avg_s_done",
            ("side",  "missed"):        "avg_s_missed",
            ("side",  "done_tasks"):    "avg_s_done_tasks",
            ("side",  "undone_tasks"):  "avg_s_undone_tasks",
            ("side",  "ratio"):         "avg_s_ratio",
            ("side",  "done_packs"):    "avg_s_done_packs",
            ("side",  "undone_packs"):  "avg_s_undone_packs",
            ("side",  "ratio_packs"):   "avg_s_ratio_packs",
        }
        tr_key = key_map.get((scope, mode), "avg_t_done")
        return tm.tr_raw(tr_key)

    def _draw_chart(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w < 50 or h < 50:
            return

        chart_type = self.chart_type.get()
        if chart_type == "line":
            self._draw_line_chart(w, h)
        elif chart_type == "bar":
            self._draw_bar_chart(w, h)
        elif chart_type == "pie":
            self._draw_pie_chart(w, h)

    def _chart_margins(self, w, h):
        ml = 75   # left  (Y-axis labels)
        mr = 20   # right
        mt = 40   # top   (title)
        mb = 75   # bottom (X-axis labels and color keys)
        return ml, mr, mt, mb

    def _days_in_month(self):
        return calendar.monthrange(self.current_year, self.current_month)[1]

    def _draw_line_chart(self, w, h):
        ml, mr, mt, mb = self._chart_margins(w, h)
        cw = w - ml - mr
        ch = h - mt - mb

        key    = self._get_metric_key()
        label  = self._get_metric_label()
        ndays  = self._days_in_month()

        # Collect (day, value) pairs for logged days only
        points = [(d, self._month_stats[d][key]) for d in range(1, ndays + 1) if d in self._month_stats]

        is_ratio = self.metric_mode.get() in ("ratio", "ratio_packs")
        y_max    = 100.0 if is_ratio else (max((v for _, v in points), default=1.0) or 1.0)
        y_max    = y_max * 1.1  # 10% headroom

        # Draw title
        title = f"{tm.format_month(self.current_year, self.current_month)} — {label}"
        self.canvas.create_text(w // 2, mt // 2, text=title, fill=TEXT_WHITE,
                                font=("Helvetica", 11, "bold"))

        # Draw grid lines + Y-axis labels
        grid_steps = 5
        for i in range(grid_steps + 1):
            y_val  = y_max * i / grid_steps
            y_px   = mt + ch - (y_val / y_max) * ch
            self.canvas.create_line(ml, y_px, w - mr, y_px, fill=BORDER_COLOR, dash=(3, 5))
            mode = self.metric_mode.get()
            if is_ratio:
                fmt = f"{y_val:.0f}%"
            elif "tasks" in mode or "packs" in mode:
                fmt = f"{y_val:.0f}"
            else:
                fmt = f"{y_val:.1f}"
            self.canvas.create_text(ml - 6, y_px, text=fmt, fill=TEXT_MUTED,
                                    font=("Helvetica", 8), anchor="e")

        # Draw axes
        self.canvas.create_line(ml, mt, ml, mt + ch, fill=BORDER_COLOR, width=1)
        self.canvas.create_line(ml, mt + ch, w - mr, mt + ch, fill=BORDER_COLOR, width=1)

        # X-axis day labels (every ~5 days)
        for d in range(1, ndays + 1, max(1, ndays // 10)):
            x_px = ml + (d - 1) / max(ndays - 1, 1) * cw
            self.canvas.create_text(x_px, mt + ch + 12, text=str(d), fill=TEXT_MUTED,
                                    font=("Helvetica", 8))

        # Draw line segments (gap at missing days)
        prev_px = None
        for d, val in points:
            x_px = ml + (d - 1) / max(ndays - 1, 1) * cw
            y_px = mt + ch - (val / y_max) * ch

            if prev_px and (d - prev_px[2] == 1):
                self.canvas.create_line(prev_px[0], prev_px[1], x_px, y_px,
                                        fill=ACCENT_PURPLE, width=2)
            # Dot
            r = 4
            color = SUCCESS_GREEN if (not is_ratio and val >= y_max * 0.9) else ACCENT_CYAN
            self.canvas.create_oval(x_px - r, y_px - r, x_px + r, y_px + r,
                                    fill=color, outline=BG_DARK, width=1)
            # Tooltip value
            mode = self.metric_mode.get()
            if is_ratio:
                tooltip_txt = f"{val:.1f}%"
            elif "tasks" in mode or "packs" in mode:
                tooltip_txt = f"{val:.0f}"
            else:
                tooltip_txt = f"{val:.1f}⭐"
            self.canvas.create_text(x_px, y_px - 12, fill=TEXT_WHITE,
                                    text=tooltip_txt,
                                    font=("Helvetica", 7))
            prev_px = (x_px, y_px, d)

        # Draw axis labels
        axis_days_lbl = tm.tr("axis_days")
        self.canvas.create_text(ml + cw // 2, mt + ch + 35, text=axis_days_lbl, fill=TEXT_MUTED,
                                font=("Helvetica", 9, "bold"))
        
        mode = self.metric_mode.get()
        if mode in ("ratio", "ratio_packs"):
            y_lbl = tm.tr("axis_ratio")
        elif "tasks" in mode:
            y_lbl = tm.tr("axis_tasks")
        elif "packs" in mode:
            y_lbl = tm.tr("axis_packs")
        else:
            y_lbl = tm.tr("axis_stars")
            
        self.canvas.create_text(16, mt + ch // 2, text=y_lbl, fill=TEXT_MUTED,
                                font=("Helvetica", 9, "bold"), angle=90)

        # No data message
        if not points:
            self.canvas.create_text(w // 2, h // 2, text=tm.tr("no_logged_days"),
                                    fill=TEXT_MUTED, font=("Helvetica", 12, "italic"))

    def _draw_bar_chart(self, w, h):
        ml, mr, mt, mb = self._chart_margins(w, h)
        cw = w - ml - mr
        ch = h - mt - mb

        key    = self._get_metric_key()
        label  = self._get_metric_label()
        ndays  = self._days_in_month()

        points = [(d, self._month_stats[d][key]) for d in range(1, ndays + 1) if d in self._month_stats]

        is_ratio = self.metric_mode.get() in ("ratio", "ratio_packs")
        y_max    = 100.0 if is_ratio else (max((v for _, v in points), default=1.0) or 1.0)
        y_max    = y_max * 1.1

        title = f"{tm.format_month(self.current_year, self.current_month)} — {label}"
        self.canvas.create_text(w // 2, mt // 2, text=title, fill=TEXT_WHITE,
                                font=("Helvetica", 11, "bold"))

        # Grid + Y labels
        for i in range(6):
            y_val = y_max * i / 5
            y_px  = mt + ch - (y_val / y_max) * ch
            self.canvas.create_line(ml, y_px, w - mr, y_px, fill=BORDER_COLOR, dash=(3, 5))
            mode = self.metric_mode.get()
            if is_ratio:
                fmt = f"{y_val:.0f}%"
            elif "tasks" in mode or "packs" in mode:
                fmt = f"{y_val:.0f}"
            else:
                fmt = f"{y_val:.1f}"
            self.canvas.create_text(ml - 6, y_px, text=fmt, fill=TEXT_MUTED,
                                    font=("Helvetica", 8), anchor="e")

        self.canvas.create_line(ml, mt, ml, mt + ch, fill=BORDER_COLOR, width=1)
        self.canvas.create_line(ml, mt + ch, w - mr, mt + ch, fill=BORDER_COLOR, width=1)

        slot_w = cw / max(ndays, 1)
        bar_w  = max(2, slot_w * 0.65)

        for d, val in points:
            x_center = ml + (d - 0.5) * slot_w
            bar_h    = (val / y_max) * ch
            x0 = x_center - bar_w / 2
            x1 = x_center + bar_w / 2
            y0 = mt + ch - bar_h
            y1 = mt + ch

            # Gradient effect: lighter top
            mid_y = (y0 + y1) / 2
            self.canvas.create_rectangle(x0, y0, x1, mid_y, fill=GLOW_COLOR, outline="", width=0)
            self.canvas.create_rectangle(x0, mid_y, x1, y1, fill=ACCENT_PURPLE, outline="", width=0)

            if slot_w > 16:
                mode = self.metric_mode.get()
                if is_ratio:
                    lbl_txt = f"{val:.1f}%"
                elif "tasks" in mode or "packs" in mode:
                    lbl_txt = f"{val:.0f}"
                else:
                    lbl_txt = f"{val:.1f}⭐"
                self.canvas.create_text(x_center, y0 - 8,
                                        text=lbl_txt,
                                        fill=TEXT_WHITE, font=("Helvetica", 7))

        # X-axis labels
        for d in range(1, ndays + 1, max(1, ndays // 10)):
            x_center = ml + (d - 0.5) * slot_w
            self.canvas.create_text(x_center, mt + ch + 12, text=str(d), fill=TEXT_MUTED,
                                    font=("Helvetica", 8))

        # Draw axis labels
        axis_days_lbl = tm.tr("axis_days")
        self.canvas.create_text(ml + cw // 2, mt + ch + 35, text=axis_days_lbl, fill=TEXT_MUTED,
                                font=("Helvetica", 9, "bold"))
        
        # Draw legend for colors (only in bar chart)
        legend_y = mt + ch + 52
        cx = ml + cw // 2
        
        # Base Progress (ACCENT_PURPLE)
        self.canvas.create_rectangle(cx - 150, legend_y, cx - 140, legend_y + 10, fill=ACCENT_PURPLE, outline="", width=0)
        self.canvas.create_text(cx - 130, legend_y + 5, text=tm.tr("legend_base_progress"), fill=TEXT_MUTED, font=("Helvetica", 8, "bold"), anchor="w")
        
        # Peak Level (GLOW_COLOR)
        self.canvas.create_rectangle(cx + 10, legend_y, cx + 20, legend_y + 10, fill=GLOW_COLOR, outline="", width=0)
        self.canvas.create_text(cx + 30, legend_y + 5, text=tm.tr("legend_peak_level"), fill=TEXT_MUTED, font=("Helvetica", 8, "bold"), anchor="w")
        
        mode = self.metric_mode.get()
        if mode in ("ratio", "ratio_packs"):
            y_lbl = tm.tr("axis_ratio")
        elif "tasks" in mode:
            y_lbl = tm.tr("axis_tasks")
        elif "packs" in mode:
            y_lbl = tm.tr("axis_packs")
        else:
            y_lbl = tm.tr("axis_stars")
            
        self.canvas.create_text(16, mt + ch // 2, text=y_lbl, fill=TEXT_MUTED,
                                font=("Helvetica", 9, "bold"), angle=90)

        if not points:
            self.canvas.create_text(w // 2, h // 2, text="No logged days for this month",
                                    fill=TEXT_MUTED, font=("Helvetica", 12, "italic"))

    def _draw_pie_chart(self, w, h):
        key    = self._get_metric_key()
        label  = self._get_metric_label()

        total = sum(self._month_stats[d][key] for d in self._month_stats)

        # For "done" / "ratio" → done vs missed pie
        scope = self.metric_scope.get()
        mode  = self.metric_mode.get()

        if mode in ("done_tasks", "undone_tasks"):
            done_total = sum(self._month_stats[d][f"{scope}_tasks_done"] for d in self._month_stats)
            undone_total = sum(self._month_stats[d][f"{scope}_tasks_undone"] for d in self._month_stats)
            if mode == "done_tasks":
                segments = [(tm.tr("pie_done_tasks"), done_total, SUCCESS_GREEN), (tm.tr("pie_undone_tasks"), undone_total, ERR_RED)]
            else:
                segments = [(tm.tr("pie_undone_tasks"), undone_total, WARN_ORANGE), (tm.tr("pie_done_tasks"), done_total, ACCENT_CYAN)]
        elif mode in ("done_packs", "undone_packs", "ratio_packs"):
            done_total = sum(self._month_stats[d][f"{scope}_packs_done"] for d in self._month_stats)
            undone_total = sum(self._month_stats[d][f"{scope}_packs_undone"] for d in self._month_stats)
            if mode in ("done_packs", "ratio_packs"):
                segments = [(tm.tr("pie_done_packs"), done_total, SUCCESS_GREEN), (tm.tr("pie_undone_packs"), undone_total, ERR_RED)]
            else:
                segments = [(tm.tr("pie_undone_packs"), undone_total, WARN_ORANGE), (tm.tr("pie_done_packs"), done_total, ACCENT_CYAN)]
        elif mode in ("done", "ratio"):
            done_total   = sum(self._month_stats[d][f"{scope}_done"] for d in self._month_stats)
            missed_total = sum(self._month_stats[d][f"{scope}_missed"] for d in self._month_stats)
            segments = [(tm.tr("pie_done"), done_total, SUCCESS_GREEN), (tm.tr("pie_missed"), missed_total, ERR_RED)]
        else:  # missed only → missed vs done reverse
            done_total   = sum(self._month_stats[d][f"{scope}_done"] for d in self._month_stats)
            missed_total = sum(self._month_stats[d][f"{scope}_missed"] for d in self._month_stats)
            segments = [(tm.tr("pie_missed"), missed_total, WARN_ORANGE), (tm.tr("pie_done"), done_total, ACCENT_CYAN)]

        grand = sum(v for _, v, _ in segments)

        title = f"{tm.format_month(self.current_year, self.current_month)} — {label} ({tm.tr('month_total')})"
        self.canvas.create_text(w // 2, 20, text=title, fill=TEXT_WHITE,
                                font=("Helvetica", 11, "bold"))

        if grand == 0 or not self._month_stats:
            self.canvas.create_text(w // 2, h // 2, text=tm.tr("no_data_month"),
                                    fill=TEXT_MUTED, font=("Helvetica", 12, "italic"))
            return

        cx = w // 2
        cy = h // 2 + 10
        r  = min(w, h) // 2 - 60

        start_angle = -90.0  # start from top
        legend_y    = cy + r + 15

        for seg_label, val, color in segments:
            sweep = (val / grand) * 360.0
            if sweep < 0.5:
                continue
            # tkinter uses degrees from 3 o'clock, counter-clockwise
            self.canvas.create_arc(cx - r, cy - r, cx + r, cy + r,
                                   start=start_angle, extent=sweep,
                                   fill=color, outline=BG_DARK, width=2, style=tk.PIESLICE)
            # Label at midpoint of arc
            mid_angle = math.radians(start_angle + sweep / 2)
            lx = cx + (r * 0.65) * math.cos(mid_angle)
            ly = cy + (r * 0.65) * math.sin(mid_angle)
            pct = (val / grand) * 100
            self.canvas.create_text(lx, ly, text=f"{pct:.1f}%", fill=BG_DARK,
                                    font=("Helvetica", 9, "bold"))
            start_angle += sweep

        # Legend
        lx = cx - 80
        for i, (seg_label, val, color) in enumerate(segments):
            self.canvas.create_rectangle(lx + i * 160, legend_y, lx + i * 160 + 14, legend_y + 14,
                                         fill=color, outline="")
            self.canvas.create_text(lx + i * 160 + 20, legend_y + 7,
                                    text=f"{seg_label}: {val:.1f}", fill=TEXT_WHITE,
                                    font=("Helvetica", 9), anchor="w")

    # ── Averages ──────────────────────────────────────────────────────────────

    def _update_averages(self):
        n = len(self._month_stats)
        if n == 0:
            for k in self.avg_vars:
                self.avg_vars[k].set("—")
            return

        def mean(key):
            return sum(self._month_stats[d][key] for d in self._month_stats) / n

        self.avg_vars["avg_t_done"].set(f"{mean('total_done'):.2f} ⭐")
        self.avg_vars["avg_m_done"].set(f"{mean('main_done'):.2f} ⭐")
        self.avg_vars["avg_s_done"].set(f"{mean('side_done'):.2f} ⭐")
        self.avg_vars["avg_t_ratio"].set(f"{mean('ratio_total'):.1f}%")
        self.avg_vars["avg_m_ratio"].set(f"{mean('ratio_main'):.1f}%")
        self.avg_vars["avg_s_ratio"].set(f"{mean('ratio_side'):.1f}%")

    # ── Right-click Export ────────────────────────────────────────────────────

    def _show_context_menu(self, event):
        menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=TEXT_WHITE,
                       activebackground=ACCENT_PURPLE, activeforeground=BG_DARK,
                       font=("Helvetica", 10))
        menu.add_command(label="💾 Download as PNG", command=lambda: self._export_chart("png"))
        menu.add_command(label="📄 Download as PDF", command=lambda: self._export_chart("pdf"))
        menu.post(event.x_root, event.y_root)

    def _export_chart(self, file_format):
        # 1. Ask for Comment Options
        default_comment = self.ai_text.get("1.0", tk.END).strip()
        
        from app import CommentOptionsDialog, WriteCommentDialog
        
        chosen_comment = None
        while chosen_comment is None:
            opt_diag = CommentOptionsDialog(self, default_comment)
            self.wait_window(opt_diag)
            
            if opt_diag.result_type is None:
                return # Cancelled entire flow
                
            if opt_diag.result_type == "ai":
                chosen_comment = default_comment
            elif opt_diag.result_type == "custom":
                write_diag = WriteCommentDialog(self, "")
                self.wait_window(write_diag)
                if write_diag.result is None:
                    # Loop back
                    continue
                chosen_comment = write_diag.result
            elif opt_diag.result_type == "blank":
                chosen_comment = ""

        from tkinter import filedialog
        import json as _json

        month_str = datetime.date(self.current_year, self.current_month, 1).strftime("%m-%Y")
        default_ext = f".{file_format}"
        file_types  = [("PNG Image", "*.png")] if file_format == "png" else [("PDF Document", "*.pdf")]

        # Load last export dir
        prefs_path = os.path.join(APP_DIR, "data", "prefs.json")
        last_dir   = os.path.expanduser("~")
        try:
            if os.path.exists(prefs_path):
                with open(prefs_path, "r", encoding="utf-8") as _f:
                    prefs = _json.load(_f)
                last_dir = prefs.get("last_export_dir", last_dir)
        except Exception:
            pass

        filename = filedialog.asksaveasfilename(
            parent=self,
            title=f"Export Monthly Graph as {file_format.upper()}",
            initialdir=last_dir,
            initialfile=f"graph_{month_str}{default_ext}",
            defaultextension=default_ext,
            filetypes=file_types
        )

        if not filename:
            return

        # Save last dir
        try:
            chosen_dir = os.path.dirname(filename)
            prefs = {}
            if os.path.exists(prefs_path):
                with open(prefs_path, "r", encoding="utf-8") as _f:
                    prefs = _json.load(_f)
            prefs["last_export_dir"] = chosen_dir
            with open(prefs_path, "w", encoding="utf-8") as _f:
                _json.dump(prefs, _f)
        except Exception:
            pass

        if tm._current_language == "Arabic":
            try:
                import arabic_reshaper
                from bidi.algorithm import get_display
            except ImportError:
                import sys
                import subprocess
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", "arabic-reshaper", "python-bidi"])
                except Exception as err:
                    messagebox.showerror("Dependencies Missing", 
                                         f"Could not automatically install Arabic shaping libraries: {err}\n\n"
                                         "Please manually run:\npip install arabic-reshaper python-bidi")
        try:
            img = self._render_chart_to_pil()
            has_comment = bool(chosen_comment.strip())
            
            if file_format == "png":
                img.save(filename, "PNG")
                if has_comment:
                    from export_helper import generate_monthly_comment_image
                    month_label = datetime.date(self.current_year, self.current_month, 1).strftime("%B %Y")
                    comment_img = generate_monthly_comment_image(month_label, chosen_comment, APP_DIR)
                    base, ext = os.path.splitext(filename)
                    comment_img.save(f"{base}_comment{ext}", "PNG")
            else: # pdf
                if has_comment:
                    from export_helper import generate_monthly_comment_image
                    month_label = datetime.date(self.current_year, self.current_month, 1).strftime("%B %Y")
                    comment_img = generate_monthly_comment_image(month_label, chosen_comment, APP_DIR)
                    img.save(filename, "PDF", save_all=True, append_images=[comment_img], resolution=150.0)
                else:
                    img.save(filename, "PDF", resolution=150.0)
            messagebox.showinfo(tm.tr("export_success"), tm.tr("graph_exported_to").format(filename=filename))
        except Exception as e:
            messagebox.showerror(tm.tr("export_error"), tm.tr("failed_export_graph").format(e=e))

    def _render_chart_to_pil(self):
        """Render the current chart selection to a Pillow Image (dark theme)."""
        from PIL import Image, ImageDraw, ImageFont

        W, H = 1600, 900

        font_path, font_bold_path = tm.get_best_font_paths(APP_DIR)
        _dv_reg = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        
        ar_font_path = font_path
        latin_font_path = _dv_reg if os.path.exists(_dv_reg) else font_path

        _ar = tm._current_language == "Arabic"

        # Local helper to shape Arabic text - now a no-op since PIL/Raqm shapes natively!
        def shape(txt):
            return txt

        # Clean emojis and unsupported characters from text drawn on chart
        def clean_symbols(text):
            cleaned = []
            for c in text:
                ord_c = ord(c)
                if (32 <= ord_c <= 126) or (0x0600 <= ord_c <= 0x06FF) or (0xFE70 <= ord_c <= 0xFEFF) or (0xFB50 <= ord_c <= 0xFDFD):
                    cleaned.append(c)
            t = "".join(cleaned)
            
            # If text is primarily Arabic, replace hyphen/dash with colon to avoid boxes
            has_latin = any('a' <= c.lower() <= 'z' for c in t)
            if not has_latin:
                t = t.replace("—", " : ").replace("-", " : ")
            else:
                t = t.replace("—", "-")
                
            t = t.replace("|", "،").replace("+", "و").replace("/", "،")
            return " ".join(t.split())

        # Local helper to draw text with correct font and direction dynamically
        def draw_t(xy, txt, font, fill, anchor=None):
            txt = clean_symbols(txt)
            size = font.size if hasattr(font, "size") else 14
            
            is_ar_txt = _ar and any('\u0600' <= c <= '\u06ff' or '\ufb50' <= c <= '\ufeff' for c in txt)
            has_latin = any('a' <= c.lower() <= 'z' for c in txt)
            has_symbols = any(c in txt for c in ["★", "*", "%"])
            
            if has_latin or has_symbols:
                fpath = latin_font_path
                direction = "ltr"
            elif is_ar_txt:
                fpath = ar_font_path
                direction = "rtl"
            else:
                fpath = latin_font_path
                direction = "ltr"
                
            try:
                active_font = ImageFont.truetype(fpath, size)
            except Exception:
                active_font = font
                
            if direction == "rtl":
                draw.text(xy, txt, font=active_font, fill=fill, direction="rtl", anchor=anchor)
            else:
                draw.text(xy, txt, font=active_font, fill=fill, anchor=anchor)

        def _fnt(size):
            try:
                return ImageFont.truetype(latin_font_path, size)
            except Exception:
                return ImageFont.load_default()

        img  = Image.new("RGB", (W, H), color="#0d0d1a")
        draw = ImageDraw.Draw(img)

        key       = self._get_metric_key()
        label     = self._get_metric_label_raw()
        ndays     = self._days_in_month()
        is_ratio  = self.metric_mode.get() in ("ratio", "ratio_packs")
        scope     = self.metric_scope.get()
        mode      = self.metric_mode.get()
        chart_type = self.chart_type.get()
        
        if _ar:
            month_title = tm._format_month_raw(self.current_year, self.current_month)
            title_sep = " : "
        else:
            month_title = tm.format_month(self.current_year, self.current_month)
            title_sep = " - "
            
        title_text  = shape(f"{month_title}{title_sep}{label}")

        # Title
        draw_t((W // 2, 24), title_text, _fnt(24), TEXT_WHITE, anchor="mt")
        draw_t((W // 2, 54), f"Mission Ui  |  {datetime.date.today().isoformat()}",
                  _fnt(14), TEXT_MUTED, anchor="mt")

        # Active Filters Metadata
        c_type_raw = tm.tr_raw(f"chart_{chart_type}")
        scope_raw  = tm.tr_raw(f"scope_{scope}")
        mode_raw   = tm.tr_raw(f"mode_{mode}")
        lbl_type   = tm.tr_raw("chart_type")
        lbl_scope  = tm.tr_raw("scope")
        lbl_mode   = tm.tr_raw("mode")
        
        if _ar:
            filters_txt = f"{lbl_type}: {c_type_raw}   ،   {lbl_scope}: {scope_raw}   ،   {lbl_mode}: {mode_raw}"
        else:
            filters_txt = f"{lbl_type}: {c_type_raw}   |   {lbl_scope}: {scope_raw}   |   {lbl_mode}: {mode_raw}"
            
        draw_t((W // 2, 76), shape(filters_txt), _fnt(13), TEXT_MUTED, anchor="mt")

        ml, mr, mt, mb = 90, 40, 100, 70
        cw = W - ml - mr
        ch = H - mt - mb

        points = [(d, self._month_stats[d][key]) for d in range(1, ndays + 1) if d in self._month_stats]
        y_max  = 100.0 if is_ratio else (max((v for _, v in points), default=1.0) or 1.0)
        y_max  = y_max * 1.1

        if chart_type == "pie":
            # Pie export
            if mode in ("done_tasks", "undone_tasks"):
                done_t = sum(self._month_stats[d][f"{scope}_tasks_done"] for d in self._month_stats)
                undone_t = sum(self._month_stats[d][f"{scope}_tasks_undone"] for d in self._month_stats)
                if mode == "done_tasks":
                    segs = [(shape(tm.tr_raw("pie_done_tasks")), done_t, SUCCESS_GREEN), 
                            (shape(tm.tr_raw("pie_undone_tasks")), undone_t, ERR_RED)]
                else:
                    segs = [(shape(tm.tr_raw("pie_undone_tasks")), undone_t, WARN_ORANGE), 
                            (shape(tm.tr_raw("pie_done_tasks")), done_t, ACCENT_CYAN)]
            elif mode in ("done_packs", "undone_packs", "ratio_packs"):
                done_p = sum(self._month_stats[d][f"{scope}_packs_done"] for d in self._month_stats)
                undone_p = sum(self._month_stats[d][f"{scope}_packs_undone"] for d in self._month_stats)
                if mode in ("done_packs", "ratio_packs"):
                    segs = [(shape(tm.tr_raw("pie_done_packs")), done_p, SUCCESS_GREEN), 
                            (shape(tm.tr_raw("pie_undone_packs")), undone_p, ERR_RED)]
                else:
                    segs = [(shape(tm.tr_raw("pie_undone_packs")), undone_p, WARN_ORANGE), 
                            (shape(tm.tr_raw("pie_done_packs")), done_p, ACCENT_CYAN)]
            elif mode in ("done", "ratio"):
                done_t   = sum(self._month_stats[d][f"{scope}_done"] for d in self._month_stats)
                missed_t = sum(self._month_stats[d][f"{scope}_missed"] for d in self._month_stats)
                segs = [(shape(tm.tr_raw("pie_done")), done_t, SUCCESS_GREEN), 
                        (shape(tm.tr_raw("pie_missed")), missed_t, ERR_RED)]
            else:
                done_t   = sum(self._month_stats[d][f"{scope}_done"] for d in self._month_stats)
                missed_t = sum(self._month_stats[d][f"{scope}_missed"] for d in self._month_stats)
                segs = [(shape(tm.tr_raw("pie_missed")), missed_t, WARN_ORANGE), 
                        (shape(tm.tr_raw("pie_done")), done_t, ACCENT_CYAN)]

            grand = sum(v for _, v, _ in segs)
            if grand > 0:
                cx, cy, r = W // 2, H // 2 + 30, min(W, H) // 2 - 120
                start = -90.0
                for slabel, val, color in segs:
                    sweep = (val / grand) * 360.0
                    if sweep < 0.5:
                        continue
                    draw.pieslice([cx - r, cy - r, cx + r, cy + r],
                                  start=start, end=start + sweep,
                                  fill=color, outline="#0d0d1a", width=3)
                    mid_a = math.radians(start + sweep / 2)
                    lx    = int(cx + r * 0.65 * math.cos(mid_a))
                    ly    = int(cy + r * 0.65 * math.sin(mid_a))
                    pct   = (val / grand) * 100
                    draw_t((lx, ly), f"{pct:.1f}%", _fnt(18), "#0d0d1a", anchor="mm")
                    start += sweep
        else:
            # Grid lines + axes
            for i in range(6):
                y_val = y_max * i / 5
                y_px  = int(mt + ch - (y_val / y_max) * ch)
                draw.line([(ml, y_px), (W - mr, y_px)], fill="#2d2d44", width=1)
                if is_ratio:
                    fmt = f"{y_val:.0f}%"
                elif "tasks" in mode or "packs" in mode:
                    fmt = f"{y_val:.0f}"
                else:
                    fmt = f"{y_val:.1f}"
                draw_t((ml - 8, y_px), fmt, _fnt(14), TEXT_MUTED, anchor="rm")

            draw.line([(ml, mt), (ml, mt + ch)], fill=BORDER_COLOR, width=2)
            draw.line([(ml, mt + ch), (W - mr, mt + ch)], fill=BORDER_COLOR, width=2)

            # X-axis day labels
            for d in range(1, ndays + 1, max(1, ndays // 15)):
                x_px = int(ml + (d - 1) / max(ndays - 1, 1) * cw)
                draw_t((x_px, mt + ch + 10), str(d), _fnt(14), TEXT_MUTED, anchor="mt")

            # X-axis label
            axis_days_lbl = shape(tm.tr_raw("axis_days"))
            draw_t((ml + cw // 2, mt + ch + 38), axis_days_lbl, _fnt(14), TEXT_MUTED, anchor="mt")

            # Y-axis label (drawn horizontally above the Y-axis)
            if mode in ("ratio", "ratio_packs"):
                y_lbl = tm.tr_raw("axis_ratio")
            elif "tasks" in mode:
                y_lbl = tm.tr_raw("axis_tasks")
            elif "packs" in mode:
                y_lbl = tm.tr_raw("axis_packs")
            else:
                y_lbl = tm.tr_raw("axis_stars")
            draw_t((ml - 40, mt - 30), shape(y_lbl), _fnt(14), TEXT_MUTED)

            if chart_type == "line":
                prev_px = None
                for d, val in points:
                    x_px = int(ml + (d - 1) / max(ndays - 1, 1) * cw)
                    y_px = int(mt + ch - (val / y_max) * ch)
                    if prev_px and (d - prev_px[2] == 1):
                        draw.line([prev_px[:2], (x_px, y_px)], fill=ACCENT_PURPLE, width=3)
                    r = 6
                    color = SUCCESS_GREEN if not is_ratio else ACCENT_CYAN
                    draw.ellipse([x_px - r, y_px - r, x_px + r, y_px + r],
                                 fill=color, outline="#0d0d1a", width=2)
                    if is_ratio:
                        txt_val = f"{val:.1f}%"
                    elif "tasks" in mode or "packs" in mode:
                        txt_val = f"{val:.0f}"
                    else:
                        txt_val = f"{val:.1f}"
                    draw_t((x_px, y_px - 18),
                              txt_val,
                              _fnt(12), TEXT_WHITE, anchor="mb")
                    prev_px = (x_px, y_px, d)
            else:  # bar
                slot_w = cw / max(ndays, 1)
                bar_w  = max(4, slot_w * 0.65)
                for d, val in points:
                    x_c  = int(ml + (d - 0.5) * slot_w)
                    bh   = int((val / y_max) * ch)
                    x0   = int(x_c - bar_w / 2)
                    x1   = int(x_c + bar_w / 2)
                    mid  = int(mt + ch - bh + bh // 2)
                    draw.rectangle([x0, mt + ch - bh, x1, mt + ch],
                                   fill=ACCENT_PURPLE, outline="")
                    draw.rectangle([x0, mt + ch - bh, x1, mid],
                                   fill=GLOW_COLOR, outline="")
                    if is_ratio:
                        txt_val = f"{val:.1f}%"
                    elif "tasks" in mode or "packs" in mode:
                        txt_val = f"{val:.0f}"
                    else:
                        txt_val = f"{val:.1f}"
                    draw_t((x_c, mt + ch - bh - 8),
                              txt_val,
                              _fnt(12), TEXT_WHITE, anchor="mb")
            
            if chart_type == "bar":
                legend_y = mt + ch + 65
                cx = ml + cw // 2
                # Base Progress (ACCENT_PURPLE)
                draw.rectangle([cx - 200, legend_y, cx - 185, legend_y + 15], fill=ACCENT_PURPLE)
                draw_t((cx - 175, legend_y), tm.tr_raw("legend_base_progress"), _fnt(12), TEXT_MUTED, anchor="lt")
                # Peak Level (GLOW_COLOR)
                draw.rectangle([cx + 20, legend_y, cx + 35, legend_y + 15], fill=GLOW_COLOR)
                draw_t((cx + 45, legend_y), tm.tr_raw("legend_peak_level"), _fnt(12), TEXT_MUTED, anchor="lt")
        return img

    def _on_ai_text_edited(self, event=None):
        comment = self.ai_text.get("1.0", tk.END).strip()
        save_monthly_comment(self.current_year, self.current_month, comment)

    def _generate_ai_comment(self):
        if self._ai_running:
            return

        if not self._month_stats:
            self.ai_text.config(state="normal")
            self.ai_text.delete("1.0", tk.END)
            self.ai_text.insert("1.0", tm.tr("no_logged_days"))
            return

        model_path = get_model_path()
        if not os.path.exists(model_path):
            self.ai_status_lbl.config(text=tm.tr("error_model_not_found"), fg=ERR_RED)
            return

        try:
            import llama_cpp  # noqa: F401
        except ImportError:
            self.ai_status_lbl.config(text=tm.tr("error_llama_not_installed"), fg=ERR_RED)
            return

        self._ai_running = True
        self.ai_gen_btn.config(state="disabled", text=tm.tr("generating"))
        self.ai_status_lbl.config(text=tm.tr("loading_model"), fg=ACCENT_CYAN)
        
        # Clear and set loading text
        self.ai_text.config(state="normal")
        self.ai_text.delete("1.0", tk.END)
        self.ai_text.insert("1.0", tm.shape_for_display(tm.tr_raw("generating")))
        if tm._current_language == "Arabic":
            self.ai_text.tag_add("rtl", "1.0", "end")
            self.ai_text.config(state="disabled")

        prompt = self._build_monthly_prompt()

        import threading
        threading.Thread(target=self._ai_worker, args=(model_path, prompt), daemon=True).start()

    def _build_monthly_prompt(self):
        n = len(self._month_stats)
        
        french_months = {
            1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
            7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
        }
        arabic_months = {
            1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
            7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
        }

        def mean(k):
            return sum(self._month_stats[d][k] for d in self._month_stats) / n

        days_sorted = sorted(self._month_stats.keys())

        if tm._current_language == "French":
            month_name = f"{french_months[self.current_month]} {self.current_year}"
            facts = f"MOIS : {month_name}\nJOURS ENREGISTRÉS : {n}\n\n=== DONNÉES JOUR PAR JOUR ===\n"
            for d in days_sorted:
                s = self._month_stats[d]
                date_str = f"{self.current_year}-{self.current_month:02d}-{d:02d}"
                facts += (f"Jour {d:02d} ({date_str}) : "
                          f"Total complété={s['total_done']:.2f}⭐/{s['total_max']:.2f}⭐ "
                          f"({s['ratio_total']:.1f}%), "
                          f"Principal={s['main_done']:.2f}/{s['main_max']:.2f}⭐ "
                          f"({s['ratio_main']:.1f}%), "
                          f"Secondaire={s['side_done']:.2f}/{s['side_max']:.2f}⭐ "
                          f"({s['ratio_side']:.1f}%)\n")

            facts += (f"\n=== MOYENNES MENSUELLES (sur seulement {n} jours enregistrés) ===\n"
                      f"Moyenne Total Complété : {mean('total_done'):.2f}⭐\n"
                      f"Moyenne Principal Complété :  {mean('main_done'):.2f}⭐\n"
                      f"Moyenne Secondaire Complété :  {mean('side_done'):.2f}⭐\n"
                      f"Moyenne Taux Total : {mean('ratio_total'):.1f}%\n"
                      f"Moyenne Taux Principal :  {mean('ratio_main'):.1f}%\n"
                      f"Moyenne Taux Secondaire :  {mean('ratio_side'):.1f}%\n")

            system = (
                "Tu es un analyste de productivité strict et factuel. "
                f"Analyse les {n} jour(s) de données ci-dessous pour {month_name}. "
                "Rédige un résumé mensuel professionnel en 4 à 6 phrases. "
                "RÈGLES CRITIQUES : "
                "1. Utilise UNIQUEMENT les nombres et les dates fournis — ne crée pas de nouveaux nombres. "
                "2. Ne mentionne pas de jours absents des données. "
                "3. N'utilise pas de langage superflu ou de clichés. "
                "4. Si moins de 5 jours sont enregistrés, indique explicitement qu'il n'est pas encore possible d'établir des tendances. "
                "5. Inclus les ratios moyens de la section des moyennes. "
                "6. Rédige un rapport concis et factuel. "
                "7. LANGUE : Tu dois obligatoirement rédiger ta réponse en français."
            )
        elif tm._current_language == "Arabic":
            month_name = f"{arabic_months[self.current_month]} {self.current_year}"
            facts = f"الشهر: {month_name}\nالأيام المسجلة: {n}\n\n=== البيانات اليومية ===\n"
            for d in days_sorted:
                s = self._month_stats[d]
                date_str = f"{self.current_year}-{self.current_month:02d}-{d:02d}"
                facts += (f"اليوم {d:02d} ({date_str}): "
                          f"إجمالي المنجز={s['total_done']:.2f}⭐/{s['total_max']:.2f}⭐ "
                          f"({s['ratio_total']:.1f}%), "
                          f"الرئيسي={s['main_done']:.2f}/{s['main_max']:.2f}⭐ "
                          f"({s['ratio_main']:.1f}%), "
                          f"الثانوي={s['side_done']:.2f}/{s['side_max']:.2f}⭐ "
                          f"({s['ratio_side']:.1f}%)\n")

            facts += (f"\n=== المعدلات الشهرية (لـ {n} أيام مسجلة فقط) ===\n"
                      f"معدل إجمالي المنجز: {mean('total_done'):.2f}⭐\n"
                      f"معدل الرئيسي المنجز:  {mean('main_done'):.2f}⭐\n"
                      f"معدل الثانوي المنجز:  {mean('side_done'):.2f}⭐\n"
                      f"معدل النسبة الإجمالية: {mean('ratio_total'):.1f}%\n"
                      f"معدل نسبة الرئيسي:  {mean('ratio_main'):.1f}%\n"
                      f"معدل نسبة الثانوي:  {mean('ratio_side'):.1f}%\n")

            system = (
                "أنت محلل إنتاجية صارم وواقعي. "
                f"قم بتحليل بيانات {n} يوم (أيام) أدناه لشهر {month_name}. "
                "اكتب ملخصًا شهريًا مهنيًا في 4-6 جمل. "
                "قواعد صارمة: "
                "1. استخدم الأرقام والتواريخ المقدمة فقط — لا تخترع أرقامًا جديدة. "
                "2. لا تذكر أي أيام غير موجودة في البيانات. "
                "3. لا تستخدم لغة إنشائية أو كليشيهات تدريبية. "
                "4. إذا تم تسجيل أقل من 5 أيام، فاذكر بوضوح أنه لا يمكن تحديد الأنماط بعد. "
                "5. قم بتضمين متوسط النسب من قسم المعدلات. "
                "6. كن موجزًا وواقعيًا. "
                "7. اللغة: يجب أن تكتب ردك باللغة العربية فقط وبشكل صحيح.\n\n"
                "=== مثال على المدخلات والمخرجات المطلوبة ===\n"
                "=== البيانات اليومية ===\n"
                "اليوم 01 (2026-08-01): إجمالي المنجز=3.00⭐/4.00⭐ (75.0%), الرئيسي=2.00/2.00⭐ (100.0%), الثانوي=1.00/2.00⭐ (50.0%)\n"
                "=== المعدلات الشهرية ===\n"
                "معدل النسبة الإجمالية: 75.0%\n"
                "معدل نسبة الرئيسي: 100.0%\n"
                "معدل نسبة الثانوي: 50.0%\n\n"
                "المخرجات (4-6 جمل باللغة العربية):\n"
                "سجل المستخدم بيانات يوم واحد لشهر أغسطس 2026. نظرًا لأن عدد الأيام المسجلة أقل من 5 أيام، فلا يمكن تحديد أنماط أو اتجاهات واضحة بعد. بلغ معدل النسبة الإجمالية للمنجز 75.0% خلال هذه الفترة. وحقق المستخدم نسبة إكمال 100.0% في المهام الرئيسية ونسبة 50.0% في المهام الثانوية. يجب تسجيل المزيد من الأيام للحصول على تحليل أدق.\n"
                "========================================"
            )
        else:
            month_name = tm.format_month(self.current_year, self.current_month)
            facts = f"MONTH: {month_name}\nLOGGED DAYS: {n}\n\n=== DAY-BY-DAY DATA ===\n"
            for d in days_sorted:
                s = self._month_stats[d]
                date_str = f"{self.current_year}-{self.current_month:02d}-{d:02d}"
                facts += (f"Day {d:02d} ({date_str}): "
                          f"Total done={s['total_done']:.2f}⭐/{s['total_max']:.2f}⭐ "
                          f"({s['ratio_total']:.1f}%), "
                          f"Main={s['main_done']:.2f}/{s['main_max']:.2f}⭐ "
                          f"({s['ratio_main']:.1f}%), "
                          f"Side={s['side_done']:.2f}/{s['side_max']:.2f}⭐ "
                          f"({s['ratio_side']:.1f}%)\n")

            facts += (f"\n=== MONTHLY AVERAGES (only {n} logged days) ===\n"
                      f"Avg Total Done: {mean('total_done'):.2f}⭐\n"
                      f"Avg Main Done:  {mean('main_done'):.2f}⭐\n"
                      f"Avg Side Done:  {mean('side_done'):.2f}⭐\n"
                      f"Avg Total Ratio: {mean('ratio_total'):.1f}%\n"
                      f"Avg Main Ratio:  {mean('ratio_main'):.1f}%\n"
                      f"Avg Side Ratio:  {mean('ratio_side'):.1f}%\n")

            system = (
                "You are a strict, factual productivity analyst. "
                f"Analyze the {n} logged day(s) of data below for {month_name}. "
                "Write a professional monthly summary in 4-6 sentences. "
                "CRITICAL RULES: "
                "1. Use ONLY the numbers and dates provided — do NOT invent or calculate new numbers. "
                "2. Do NOT mention any days that are not in the logged data. "
                "3. Do NOT use subjective language, coaching clichés, or assume personal feelings. "
                "4. If fewer than 5 days are logged, explicitly state that patterns cannot be established yet. "
                "5. Include the average ratios from the averages section. "
                "6. Be concise and factual. "
                "7. LANGUAGE REQUIREMENT: {tm.tr('ai_language_prompt')}"
            )

        return (f"<start_of_turn>user\n"
                f"System: {system}\n\n{facts}\n"
                f"<end_of_turn>\n<start_of_turn>model\n")

    def _ai_worker(self, model_path, prompt):
        try:
            from llama_cpp import Llama
            llm = Llama(model_path=model_path, n_ctx=4096, verbose=False, seed=-1)
            response = llm(prompt, max_tokens=400, temperature=0.4,
                           repeat_penalty=1.15, top_p=0.9,
                           stop=["<end_of_turn>", "<|im_end|>"])
            result = response["choices"][0]["text"].strip()
        except Exception as e:
            result = f"[AI Error: {e}]"
        self.after(0, self._ai_done, result)

    def _ai_done(self, result):
        if not self.winfo_exists():
            return
            
        # Validate output and use programmatic fallback if there is any hallucination/error
        text_lower = result.lower()
        has_placeholders = any(x in text_lower for x in ["day 1", "day 2", "day 3", "month x", "average y"])
        is_arabic = (tm._current_language == "Arabic")
        
        def contains_arabic(text):
            return any('\u0600' <= char <= '\u06FF' or '\u0750' <= char <= '\u077F' or '\u08A0' <= char <= '\u08FF' for char in text)
            
        has_language_hallucination = is_arabic and not contains_arabic(result)
        
        if has_placeholders or has_language_hallucination or len(result.strip()) < 10 or "[ai error:" in text_lower:
            _lang = tm._current_language
            n = len(self._month_stats)
            
            french_months = {
                1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
                7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"
            }
            arabic_months = {
                1: "يناير", 2: "فبراير", 3: "مارس", 4: "أبريل", 5: "مايو", 6: "يونيو",
                7: "يوليو", 8: "أغسطس", 9: "سبتمبر", 10: "أكتوبر", 11: "نوفمبر", 12: "ديسمبر"
            }
            
            def mean(k):
                return sum(self._month_stats[d][k] for d in self._month_stats) / n
                
            avg_tot = mean('ratio_total')
            avg_main = mean('ratio_main')
            avg_side = mean('ratio_side')
            
            if _lang == "French":
                if n < 5:
                    result = (f"Résumé mensuel pour {french_months[self.current_month]} {self.current_year}. "
                              f"Avec seulement {n} jour(s) enregistré(s), il n'est pas encore possible d'établir des tendances fiables. "
                              f"Le taux d'achèvement global moyen est de {avg_tot:.1f}%. "
                              f"Pour le moment, les tâches principales sont complétées à {avg_main:.1f}% en moyenne, et les tâches secondaires à {avg_side:.1f}%.")
                else:
                    result = (f"Résumé mensuel pour {french_months[self.current_month]} {self.current_year} basé sur {n} jours de données. "
                              f"L'utilisateur affiche une productivité moyenne stable avec un taux de réussite global de {avg_tot:.1f}%. "
                              f"En moyenne, le taux d'achèvement des tâches principales est de {avg_main:.1f}% et celui des tâches secondaires est de {avg_side:.1f}%. "
                              f"Ces données indiquent une bonne régularité globale dans le suivi des missions mensuelles.")
            elif _lang == "Arabic":
                if n < 5:
                    result = (f"الملخص الشهري لشهر {arabic_months[self.current_month]} {self.current_year}. "
                              f"مع تسجيل {n} يوم (أيام) فقط، لا يمكن تحديد اتجاهات أو أنماط واضحة للمستخدم بعد. "
                              f"بلغ متوسط معدل الإنجاز الإجمالي {avg_tot:.1f}%. "
                              f"وفي الوقت الحالي، بلغت نسبة إكمال المهام الرئيسية {avg_main:.1f}% بينما بلغت نسبة المهام الثانوية {avg_side:.1f}%.")
                else:
                    result = (f"التقرير الشهري لشهر {arabic_months[self.current_month]} {self.current_year} بناءً على {n} يوماً من البيانات. "
                              f"يظهر المستخدم أداءً مستقراً بمتوسط معدل إنجاز إجمالي بلغ {avg_tot:.1f}%. "
                              f"بلغ متوسط معدل إنجاز المهام الرئيسية {avg_main:.1f}%، في حين سجلت المهام الثانوية معدل إنجاز متوسط قدره {avg_side:.1f}%. "
                              f"تشير هذه الأرقام إلى التزام مستمر بتحقيق الأهداف والمهام المسجلة.")
            else:
                month_name = tm.format_month(self.current_year, self.current_month)
                if n < 5:
                    result = (f"Monthly summary for {month_name}. "
                              f"With only {n} logged day(s), it is not yet possible to establish reliable productivity trends. "
                              f"The average overall completion rate is {avg_tot:.1f}%. "
                              f"Currently, main tasks have an average completion of {avg_main:.1f}%, and side tasks average {avg_side:.1f}%.")
                else:
                    result = (f"Monthly report for {month_name} based on {n} logged days. "
                              f"The user shows a stable average productivity with an overall completion rate of {avg_tot:.1f}%. "
                              f"On average, the completion rate of main tasks is {avg_main:.1f}% and side tasks average {avg_side:.1f}%. "
                              f"These numbers indicate steady progress in tracking monthly missions.")
        
        self._ai_running = False
        self.ai_gen_btn.config(state="normal", text=tm.tr("generate"))
        self.ai_status_lbl.config(text=tm.tr("done_status"), fg=SUCCESS_GREEN)
        self.after(3000, lambda: self.ai_status_lbl.config(text="") if self.winfo_exists() else None)
        self.ai_text.config(state="normal")
        self.ai_text.delete("1.0", tk.END)
        self.ai_text.insert("1.0", tm.shape_for_display(result))
        if tm._current_language == "Arabic":
            self.ai_text.tag_add("rtl", "1.0", "end")
            self.ai_text.config(state="disabled")
        save_monthly_comment(self.current_year, self.current_month, result)
