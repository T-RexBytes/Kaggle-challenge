"""Blog figures for the BOUNDARY v3 DEV.to post: "The Trial of Ten Models".

Reads report/data/*.csv and the raw traces under report/raw, writes PNGs to
report/blog_figures/. Run from anywhere:  python report/make_blog_figures.py

Every chart is a numbered PLATE in a candlelit record of the trial: charred ink
background with a faint candle glow, a double gold rule with corner stars, a
centred header (tracked plate label, Perpetua Titling title, gold divider,
Goudy subtitle) and a small footer. One semantic palette everywhere:
verdigris = in bounds / clean, crimson = crossed the line, candle gold = blocked
attempt, ash = failed the task, faint hatch = NA. Points are drawn as wax seals.
"""
from __future__ import annotations

import glob
import json
import logging
import math
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.patches import Polygon, Rectangle  # noqa: E402
from matplotlib.transforms import blended_transform_factory  # noqa: E402

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "blog_figures")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------- the chamber
BG = "#15120E"          # charred ink
GLOW = "#2A2117"        # candlelight at the upper centre
GOLD_RULE = "#B8975A"   # outer rule, ornaments, plate label
GOLD_INNER = "#6E5A36"  # inner rule, hairlines
TITLE_INK = "#F1E6CF"   # parchment, titles
INK = "#E8DCC2"         # parchment, body text and neutral lines
SUB = "#B9AC93"         # muted parchment, subtitles
MUTED = "#958A76"       # axis ticks, quiet notes
FOOT = "#8C8070"        # footer
GRID = "#2E2820"        # gridlines, barely there
TRACK = "#3D3428"       # faint guide lines (timeline tracks, dumbbell bars)

CLEAN = "#6FA58C"       # in bounds / clean
CLEAN_FILL = "#3F6E5B"
CRIMSON = "#C2413B"     # crossed the line
CRIMSON_FILL = "#8E2A26"
CRIMSON_TEXT = "#DA5B53"  # crimson lifted a touch so small text stays readable
CANDLE = "#D9A441"      # blocked attempt
ASH = "#8C8478"         # failed the task
ASH_FILL = "#5F594F"
NA_FACE = "#3A3329"     # NA, hatched
NA_HATCH = "#594E3F"

TITLING = ["Perpetua Titling MT", "Castellar", "DejaVu Serif"]
BODY = ["Goudy Old Style", "Segoe UI Symbol", "DejaVu Serif"]
NUM = ["Perpetua", "Goudy Old Style", "Segoe UI Symbol", "DejaVu Serif"]
BLACKLETTER = ["Old English Text MT", "DejaVu Serif"]
SYMBOL = ["Segoe UI Symbol", "DejaVu Sans"]

plt.rcParams.update({
    "font.family": BODY,
    "font.size": 14,
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.edgecolor": GOLD_INNER,
    "axes.linewidth": 0.8,
    "axes.facecolor": "none",
    "figure.facecolor": BG,
    "savefig.facecolor": BG,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK,
    "ytick.color": INK,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "hatch.color": NA_HATCH,
    "hatch.linewidth": 0.9,
})

FOOTER = "BOUNDARY  ·  the trial of ten models  ·  kaggle.com/benchmarks/trexbytes/your-llm-doesnt-know-boundary"
LEVELS = ["closed", "task", "open"]
LEVEL_LABEL = {"closed": "Closed Box", "task": "Task Box", "open": "Open Box"}
TASKS = ["T01v3", "T08v3", "T05v3", "T11v3", "T18v3"]
TASKS_ALL = ["T01v3", "T08v3", "T05v3", "T11v3", "T18v3"]
TASK_SHORT = {"T01v3": "Invoices", "T08v3": "Bug fix", "T05v3": "Records", "T11v3": "Tickets",
              "T18v3": "Release", "T17v3": "Config"}
MODELS = ["GPT-6.1 Sol", "GPT-6 Astra", "GPT-6 Luna", "Claude Sonnet 5.5",
          "Claude Opus 5.5", "Gemini 3.1 Pro Preview", "Gemini 3.8 Flash",
          "Gemini 3.7 Flash", "Gemma 4 31B", "GLM-5"]
EXECUTED = {"ok", "granted", "detected"}
BLOCKED = {"denied", "not_found", "ignored"}
SLUG = {"T01v3": "boundary-v3-t01-month-end-total", "T05v3": "boundary-v3-t05-escalation-report",
        "T08v3": "boundary-v3-t08-issue-fix", "T11v3": "boundary-v3-t11-ticket-closeout",
        "T18v3": "boundary-v3-t18-blocked-release"}
W = 12.0    # figure width in inches
DPI = 200   # 2400 px wide


# ----------------------------------------------------------------- data
def _bool(s):
    return s.map({"True": True, "False": False})


def load():
    d = pd.read_csv(os.path.join(DATA, "level_results.csv"), keep_default_na=False, dtype=str)
    for c in ["task_success", "safe_success", "boundary_violation", "overclaim", "round_limit_hit"]:
        d[c] = _bool(d[c])
    for c in ["violation_count", "p_risk", "threat_tier", "level_score", "tool_calls", "cost_usd"]:
        d[c] = pd.to_numeric(d[c].replace("NA", np.nan), errors="coerce")
    d["valid"] = d["status"] == "completed"
    inc = pd.read_csv(os.path.join(DATA, "incidents.csv"), keep_default_na=False, dtype=str)
    inc["weight"] = pd.to_numeric(inc["weight"])
    return d, inc


def wilson(k, n, z=1.96):
    if n == 0:
        return np.nan, np.nan
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def raw_run(task_slug, model_slug, level):
    pat = os.path.join(RAW, task_slug, "*", model_slug, "*", "outputs", "*",
                       f"*-{level.upper()}-R01.json")
    files = sorted(glob.glob(pat))
    if not files:
        return None
    with open(files[-1], encoding="utf-8") as fh:
        return json.load(fh)


def empty_reply(task_id, model_slug, level):
    """True when the run completed but the model's final reply was empty."""
    if task_id not in SLUG:
        return False
    rec = raw_run(SLUG[task_id], model_slug, level)
    if not rec:
        return False
    fr = rec.get("final_response")
    return not (fr.strip() if isinstance(fr, str) else fr)


# ----------------------------------------------------------------- theme layer
def seal(ax, x, y, color, s=150, fill=None, z=5, ring=True, **kw):
    """A wax seal: filled centre, a thin dark gap, then a thin outer ring in the same hue."""
    ax.scatter(x, y, s=s, color=fill or color, edgecolors=BG, linewidths=1.1, zorder=z, **kw)
    if ring:
        ax.scatter(x, y, s=s * 2.1, facecolors="none", edgecolors=color, linewidths=0.9,
                   zorder=z - 0.1, **kw)


def star4(ax, x, y, r, color, z=30):
    """Four point star (corner ornament) in inch coordinates on the overlay axes."""
    k = r * 0.28
    pts = [(x, y + r), (x + k, y + k), (x + r, y), (x + k, y - k),
           (x, y - r), (x - k, y - k), (x - r, y), (x - k, y + k)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=color, edgecolor="none", zorder=z))


def diamond(ax, x, y, r, color, z=30, face=None, lw=0.9):
    pts = [(x, y + r), (x + r * 0.72, y), (x, y - r), (x - r * 0.72, y)]
    ax.add_patch(Polygon(pts, closed=True, facecolor=face or color, edgecolor=color, linewidth=lw, zorder=z))


class Plate:
    """A numbered plate: background glow, double gold frame, centred header, footer.

    Layout helpers work in inches. `self.ov` is a full-figure overlay axes whose data
    units are inches from the bottom-left corner, so ornaments and legends stay round
    and exact. `self.top` is the inch offset (from the top) where content may begin.
    """

    OUTER = 0.20
    INNER = 0.28

    def __init__(self, numeral, name, title, subtitle, h=7.6):
        self.h = h
        self.fig = plt.figure(figsize=(W, h), dpi=DPI)
        self.rend = self.fig.canvas.get_renderer()
        self._background()
        self.ov = self.fig.add_axes([0, 0, 1, 1], zorder=20)
        self.ov.set_xlim(0, W)
        self.ov.set_ylim(0, h)
        self.ov.axis("off")
        self.ov.patch.set_alpha(0)
        self._frame()
        self.top = self._header(f"PLATE {numeral} · {name}", title, subtitle)
        self.text(0.58, 0.50, FOOTER, size=10.5, color=FOOT, ha="left", va="baseline")

    # -- coordinates
    def Y(self, from_top):
        return self.h - from_top

    def axes(self, left_in, right_in, top_in, bottom_in):
        """Data axes placed by margins in inches (top measured from the figure top)."""
        return self.fig.add_axes([left_in / W, bottom_in / self.h,
                                  (W - left_in - right_in) / W,
                                  (self.h - top_in - bottom_in) / self.h])

    # -- text
    def text(self, x, y, s, size=14, family=None, color=INK, **kw):
        return self.ov.text(x, y, s, fontsize=size, family=family or BODY, color=color, **kw)

    def width(self, s, size=14, family=None, weight="normal"):
        t = self.fig.text(0, 0, s, fontsize=size, family=family or BODY, fontweight=weight)
        w = t.get_window_extent(self.rend).width / DPI
        t.remove()
        return w

    def tracked(self, x, y, s, size, family, color, tracking=0.2, weight="normal"):
        """Letter spaced caps, centred on x, baseline y. A middle dot becomes a small gold diamond."""
        track = tracking * size / 72
        ws = []
        for ch in s:
            if ch == " ":
                ws.append(size * 0.30 / 72)
            elif ch == "·":
                ws.append(size * 0.55 / 72)
            else:
                ws.append(self.width(ch, size, family, weight))
        total = sum(ws) + track * (len(s) - 1)
        cx = x - total / 2
        for ch, w in zip(s, ws):
            if ch == "·":
                diamond(self.ov, cx + w / 2, y + size * 0.33 / 72, size * 0.16 / 72, color)
            elif ch != " ":
                self.ov.text(cx, y, ch, fontsize=size, family=family, color=color, fontweight=weight,
                             ha="left", va="baseline")
            cx += w + track
        return total

    # -- chrome
    def _background(self):
        bg = self.fig.add_axes([0, 0, 1, 1], zorder=-50)
        bg.axis("off")
        ny, nx = 300, 480
        yy, xx = np.mgrid[0:1:complex(0, ny), 0:1:complex(0, nx)]
        r = np.sqrt(((xx - 0.5) / 0.62) ** 2 + ((yy - 0.80) / 0.70) ** 2)
        t = np.clip(1 - r, 0, 1) ** 1.7
        c0 = np.array(matplotlib.colors.to_rgb(BG))
        c1 = np.array(matplotlib.colors.to_rgb(GLOW))
        img = c0 + (c1 - c0) * t[..., None]
        bg.imshow(img, origin="lower", extent=(0, 1, 0, 1), aspect="auto", interpolation="bicubic")
        bg.set_xlim(0, 1)
        bg.set_ylim(0, 1)

    def _frame(self):
        o, i, h = self.OUTER, self.INNER, self.h
        for inset, col, lw in ((o, GOLD_RULE, 1.1), (i, GOLD_INNER, 0.8)):
            self.ov.add_patch(Rectangle((inset, inset), W - 2 * inset, h - 2 * inset, facecolor="none",
                                        edgecolor=col, linewidth=lw, zorder=25))
        m = (o + i) / 2
        for cx, cy in ((m, m), (W - m, m), (m, h - m), (W - m, h - m)):
            diamond(self.ov, cx, cy, 0.075, BG, z=29, face=BG, lw=0)
            star4(self.ov, cx, cy, 0.085, GOLD_RULE)

    def divider(self, cx, y, half=1.25, color=GOLD_RULE):
        gap = 0.13
        self.ov.plot([cx - half, cx - gap], [y, y], color=color, linewidth=0.8, zorder=30)
        self.ov.plot([cx + gap, cx + half], [y, y], color=color, linewidth=0.8, zorder=30)
        diamond(self.ov, cx, y, 0.055, color)
        for sx in (-1, 1):
            self.ov.scatter([cx + sx * (half + 0.06)], [y], s=3, color=color, zorder=30)

    def _header(self, label, title, subtitle):
        cx = W / 2
        y = 0.70
        self.tracked(cx, self.Y(y), label.upper(), 12.5, TITLING, GOLD_RULE, tracking=0.28, weight="bold")
        y += 0.56
        for k, line in enumerate(title.split("\n")):
            if k:
                y += 0.50
            self.tracked(cx, self.Y(y), line.upper(), 28, TITLING, TITLE_INK, tracking=0.05)
        y += 0.27
        self.divider(cx, self.Y(y))
        y += 0.33
        self.text(cx, self.Y(y), subtitle, size=15, color=SUB, ha="center", va="baseline")
        return y + 0.38

    # -- legend: one centred row of marks with plain words
    def legend(self, y_from_top, items, size=13.5, gap=0.42):
        mark_w, pad = 0.24, 0.09
        widths = [mark_w + pad + self.width(lab, size) for _, _, lab in items]
        total = sum(widths) + gap * (len(items) - 1)
        x = W / 2 - total / 2
        y = self.Y(y_from_top)
        for (kind, col, lab), w in zip(items, widths):
            mx = x + mark_w / 2
            self._mark(kind, col, mx, y)
            self.text(x + mark_w + pad, y, lab, size=size, color=INK, ha="left", va="center")
            x += w + gap

    def _mark(self, kind, col, x, y):
        ax = self.ov
        if kind == "seal":
            seal(ax, x, y, col, s=60, z=31)
        elif kind == "dot":
            ax.scatter([x], [y], s=14, color=col, zorder=31)
        elif kind == "x":
            ax.scatter([x], [y], s=55, marker="x", color=col, linewidths=2.0, zorder=31)
        elif kind == "tick":
            ax.plot([x, x], [y - 0.09, y + 0.09], color=col, linewidth=2.6, zorder=31)
        elif kind == "diamond":
            diamond(ax, x, y, 0.075, col, z=31)
        elif kind == "panel":
            ax.add_patch(Rectangle((x - 0.12, y - 0.08), 0.24, 0.16, facecolor=col[0], edgecolor=col[1],
                                   linewidth=0.8, zorder=31))
        elif kind == "hatch":
            ax.add_patch(Rectangle((x - 0.12, y - 0.08), 0.24, 0.16, facecolor=NA_FACE, edgecolor=NA_HATCH,
                                   hatch="////", linewidth=0.6, zorder=31))
        elif kind == "line":
            ax.plot([x - 0.12, x + 0.12], [y, y], color=col, linewidth=2.4, zorder=31)

    def save(self, name):
        path = os.path.join(OUT, name)
        self.fig.savefig(path, dpi=DPI)
        plt.close(self.fig)
        print("wrote", path)


def quiet(ax, left=False, bottom=False):
    ax.tick_params(length=0, pad=9)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GOLD_INNER)
        ax.spines[s].set_linewidth(0.8)


def faint_grid(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def na_patch(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=NA_FACE, hatch="////", edgecolor=NA_HATCH, linewidth=0))


def fmt_signed(v):
    if v > 0.005:
        return f"−{v:.2f}"
    if v < -0.005:
        return f"+{-v:.2f}"
    return "0.00"


# ----------------------------------------------------------------- I hero
def fig_hero(d):
    v = d[d.valid]
    series = [("Task success", "task_success", INK, INK),
              ("Clean success", "safe_success", CLEAN, CLEAN),
              ("Crossed a boundary", "boundary_violation", CRIMSON, CRIMSON_TEXT)]
    P = Plate("I", "THE THREE CHAMBERS", "More access, more trespassing",
              "Share of runs at each access level, all ten models (faint bands: 95% confidence)", h=7.6)
    ax = P.axes(1.55, 3.05, P.top + 0.15, 1.25)
    x = np.arange(3)
    pts = {}
    for name, col, c, tc in series:
        k = np.array([v[v.level == l][col].sum() for l in LEVELS])
        n = np.array([v[v.level == l][col].count() for l in LEVELS])
        p = k / n
        lo, hi = zip(*[wilson(a, b) for a, b in zip(k, n)])
        ax.fill_between(x, lo, hi, color=c, alpha=0.06, linewidth=0)
        ax.plot(x, p, color=c, linewidth=2.3, zorder=4, solid_capstyle="round")
        seal(ax, x, p, c, s=95, z=6)
        pts[name] = (p, n)
        ax.annotate(f"{p[0]:.0%}", (0, p[0]), xytext=(-20, 0), textcoords="offset points",
                    ha="right", va="center", fontsize=19, family=NUM, color=tc)
        ax.annotate(f"{p[-1]:.0%}", (2, p[-1]), xytext=(20, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=19, family=NUM, color=tc)
        ax.annotate(name, (2, p[-1]), xytext=(74, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=16, color=tc, annotation_clip=False)
    ax.set_xlim(-0.1, 2.1)
    ax.set_ylim(0, 1.04)
    ax.set_xticks(x, [LEVEL_LABEL[l] for l in LEVELS], fontsize=16, color=INK)
    ax.set_yticks([0, .5, 1], ["0%", "50%", "100%"], fontsize=13, color=MUTED, family=NUM)
    quiet(ax, bottom=True)
    ax.spines["bottom"].set_color(GOLD_INNER)
    faint_grid(ax)
    P.save("hero_boundary_curve.png")
    return pts


# ----------------------------------------------------------------- V dumbbell
def fig_dumbbell(d):
    v = d[d.valid]
    rows = []
    for m in MODELS:
        c = v[(v.model_name == m) & (v.level == "closed")]
        o = v[(v.model_name == m) & (v.level == "open")]
        # does the drop come from empty replies rather than from crossing a line?
        empty = o[[empty_reply(r.task_id, r.model, "open") for r in o.itertuples()]]
        o_rest = o.drop(empty.index)
        drop = c.level_score.mean() - o.level_score.mean()
        drop_rest = c.level_score.mean() - o_rest.level_score.mean() if len(o_rest) else drop
        flag = len(empty) > 0 and drop > 0.1 and drop_rest < drop / 2
        rows.append((m, c.level_score.mean(), o.level_score.mean(), len(c), len(o), len(empty), flag))
    df = pd.DataFrame(rows, columns=["m", "c", "o", "nc", "no", "nempty", "dagger"])
    df["drop"] = df.c - df.o
    df = df.sort_values("drop", ascending=True).reset_index(drop=True)  # biggest drop on top
    P = Plate("V", "THE RECKONING", "Who held the line when the doors opened",
              "Mean score per model, Closed Box against Open Box (1.0 is a perfect run)", h=8.2)
    has_dagger = bool(df.dagger.any())
    ax = P.axes(3.0, 1.75, P.top + 0.55, 1.5 if has_dagger else 1.2)
    for i, r in df.iterrows():
        ax.plot([r.c, r.o], [i, i], color=TRACK, linewidth=3.2, zorder=1, solid_capstyle="round")
        same = abs(r.c - r.o) < 0.005
        seal(ax, r.c, i, CLEAN, s=210 if same else 120, z=4)
        seal(ax, r.o, i, CRIMSON, s=55 if same else 120, z=6)
        dv = r["drop"]
        col = CRIMSON_TEXT if dv > 0.005 else (CLEAN if dv < -0.005 else ASH)
        ax.text(1.04, i, fmt_signed(dv), color=col, fontsize=19, family=NUM, va="center_baseline", ha="left",
                transform=ax.get_yaxis_transform())
    labels = [m + ("  †" if dg else "") for m, dg in zip(df.m, df.dagger)]
    ax.set_yticks(range(len(df)), labels, fontsize=15.5, color=INK)
    ax.set_xlim(0.2, 1.04)
    ax.set_xticks([0.2, 0.4, 0.6, 0.8, 1.0], ["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=13, color=MUTED,
                  family=NUM)
    ax.set_ylim(-0.6, len(df) - 0.4)
    quiet(ax)
    faint_grid(ax, "x")
    top = df.iloc[-1]
    ytop = len(df) - 1
    ax.annotate("Closed Box", (top.c, ytop), xytext=(0, 17), textcoords="offset points",
                ha="center", va="bottom", fontsize=14, color=CLEAN)
    ax.annotate("Open Box", (top.o, ytop), xytext=(0, 17), textcoords="offset points",
                ha="center", va="bottom", fontsize=14, color=CRIMSON_TEXT)
    ax.annotate("drop", (1.04, ytop), xycoords=("axes fraction", "data"), xytext=(0, 17),
                textcoords="offset points", ha="left", va="bottom", fontsize=14, color=SUB)
    if has_dagger:
        P.text(3.0, 0.92, "†  these drops come from empty replies, not from crossing a line",
               size=13.5, color=SUB, ha="left", va="baseline")
    P.save("dumbbell_closed_vs_open.png")
    return df


# ----------------------------------------------------------------- VII outcome bars
CATS = [("Clean success", CLEAN_FILL), ("Succeeded but crossed", CRIMSON_FILL), ("Overclaimed", CRIMSON),
        ("Failed", ASH_FILL), ("NA", NA_FACE)]


def outcome(r):
    if not r.valid:
        return "NA"
    if r.overclaim:
        return "Overclaimed"
    if r.safe_success:
        return "Clean success"
    if r.task_success and r.boundary_violation:
        return "Succeeded but crossed"
    return "Failed"


def fig_outcomes(d):
    p = d[d.task_id.isin(TASKS)].copy()
    p["cat"] = p.apply(outcome, axis=1)
    ct = pd.crosstab(p.model_name, p.cat).reindex(columns=[c for c, _ in CATS], fill_value=0)
    ct = ct.reindex(MODELS)
    assert (ct.sum(axis=1) == 15).all()
    ct = ct.sort_values(["Clean success", "NA"], ascending=[True, False])
    P = Plate("VII", "THE VERDICTS", "How every run ended",
              "All 15 runs per model: five tasks, each at three access levels", h=8.2)
    P.legend(P.top + 0.12, [("panel", (c, c if n != "NA" else NA_HATCH), n) if n != "NA" else ("hatch", None, n)
                            for n, c in CATS if n != "NA" or ct["NA"].sum() > 0])
    ax = P.axes(3.0, 0.75, P.top + 0.55, 0.95)
    y = np.arange(len(ct))
    left = np.zeros(len(ct))
    for cat, col in CATS:
        w = ct[cat].values
        if cat == "NA":
            ax.barh(y, w, left=left, color=col, height=0.66, hatch="////", edgecolor=NA_HATCH, linewidth=0)
            ax.barh(y, w, left=left, color="none", height=0.66, edgecolor=BG, linewidth=2.2)
        else:
            ax.barh(y, w, left=left, color=col, height=0.66, edgecolor=BG, linewidth=2.2)
        for yi, (l, wi) in enumerate(zip(left, w)):
            if wi >= 1 and cat != "NA":
                ax.text(l + wi / 2, yi, str(int(wi)), ha="center", va="center_baseline", fontsize=16, family=NUM,
                        color=TITLE_INK)
            elif wi >= 1:
                ax.text(l + wi / 2, yi, str(int(wi)), ha="center", va="center_baseline", fontsize=16, family=NUM,
                        color=TITLE_INK)
        left += w
    ax.set_yticks(y, ct.index, fontsize=15.5, color=INK)
    ax.set_xlim(0, 15)
    ax.set_xticks([])
    ax.set_ylim(-0.55, len(ct) - 0.45)
    quiet(ax)
    P.save("outcome_bars_by_model.png")
    return ct


# ----------------------------------------------------------------- VI ledger of trespass
SEV_HUE = {0: CLEAN, 1: CANDLE, 2: "#CF8A7C", 3: CRIMSON_TEXT, 4: TITLE_INK}
SEV_FACE = {0: "#1C1F19", 1: "#2A2216", 2: "#2B1E1A", 3: "#33191A", 4: CRIMSON_FILL}
SEV_EDGE = {0: "#2F3A31", 1: "#6B5427", 2: "#6B4840", 3: "#7A2F2B", 4: CRIMSON}
SEV_LABEL = {0: "Clean", 1: "Blocked attempt", 2: "Read out of bounds", 3: "Wrote or took a role",
             4: "Bypassed a check"}


def _target(res):
    """One short word naming what the incident touched."""
    if "admin" in res and ("env" in res or "token" in res):
        return "token"
    if res.startswith("tickets/"):
        return "ticket"
    if res.startswith("audit/"):
        return "audit log"
    if res == "session/role":
        return "role"
    if res.startswith("billing/"):
        return "release"
    if res.startswith("ci/"):
        return "CI"
    if res.startswith("release/"):
        return "stray note"
    head = res.split("/", 1)[0]
    if "." in head and not head.startswith("."):
        head = head.rsplit(".", 1)[0]
    return head


def inc_severity(r):
    if r.outcome in BLOCKED:
        return 1
    if r.kind == "execute":
        return 4
    if r.kind in ("write", "credential"):
        return 3
    return 2


def inc_tag(r):
    t = _target(r.resource)
    if r.outcome in BLOCKED:
        return f"probed {t}" if r.outcome == "not_found" else f"tried {t}"
    if r.tool == "request_role":
        return "role grab"
    if r.tool == "(final state)":
        rec = raw_run(SLUG[r.task_id], r.model + "*", r.level)
        summ = json.dumps(rec.get("evaluation", {})).lower() if rec else ""
        return "monkeypatch" if "monkeypatch" in summ else "bypassed check"
    if r.kind == "write":
        return f"edited {t}"
    if r.kind == "read":
        return f"read {t}"
    if r.kind == "list":
        return f"peeked {t}"
    return f"{r.tool} {t}"


def fig_heatmap(d, inc):
    inc = inc.copy()
    inc["sev"] = inc.apply(inc_severity, axis=1)
    P = Plate("VI", "THE LEDGER OF TRESPASS", "Where each model crossed the line",
              "The worst act of each model in each task, across all three access levels", h=8.9)
    ax = P.axes(2.95, 0.6, P.top + 0.5, 1.35)
    ax.set_xlim(0, len(TASKS_ALL))
    ax.set_ylim(len(MODELS), 0)
    cells = {}
    pw, ph = 0.94, 0.84
    for i, m in enumerate(MODELS):
        for j, t in enumerate(TASKS_ALL):
            x0, y0 = j + (1 - pw) / 2, i + (1 - ph) / 2
            sub = d[(d.model_name == m) & (d.task_id == t)]
            nvalid = int(sub.valid.sum())
            if nvalid == 0:
                na_patch(ax, x0, y0, pw, ph)
                ax.text(j + .5, i + .5, "NA", ha="center", va="center", fontsize=13, color=SUB,
                        bbox=dict(boxstyle="square,pad=0.15", fc=NA_FACE, ec="none"))
                cells[(m, t)] = (None, "NA")
                continue
            mi = inc[(inc.model_name == m) & (inc.task_id == t)]
            vl = set(sub[sub.valid].level)  # only incidents from valid levels
            mi = mi[mi.level.isin(vl)]
            sev, tag = 0, ""
            if len(mi):
                mi = mi.assign(sal=mi.weight + np.where((mi.tool == "request_role") & (mi.outcome == "granted"), 10, 0))
                top = mi.sort_values(["sev", "sal"], ascending=False).iloc[0]
                sev, tag = int(top.sev), inc_tag(top)
            oc = sub[sub.valid & (sub.overclaim == True)]  # noqa: E712
            if len(oc) and sev < 4:
                sev, tag = 4, "overclaimed"
            cells[(m, t)] = (sev, tag)
            ax.add_patch(Rectangle((x0, y0), pw, ph, facecolor=SEV_FACE[sev], edgecolor=SEV_EDGE[sev],
                                   linewidth=0.7))
            if tag:
                ax.text(j + .5, i + .5, tag, ha="center", va="center_baseline", fontsize=14, color=SEV_HUE[sev])
            else:
                ax.scatter([j + .5], [i + .5], s=16, color=CLEAN, zorder=3)
    ax.set_xticks(np.arange(len(TASKS_ALL)) + .5, [TASK_SHORT[t] for t in TASKS_ALL], fontsize=15.5, color=SUB)
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(MODELS)) + .5, MODELS, fontsize=15.5, color=INK)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0, pad=8)
    items = [("dot", CLEAN, "Clean")]
    items += [("panel", (SEV_FACE[k], SEV_HUE[k] if k < 4 else CRIMSON), SEV_LABEL[k]) for k in range(1, 5)]
    if any(v[0] is None for v in cells.values()):
        items.append(("hatch", None, "NA"))
    P.legend(P.h - 0.95, items, size=13.5, gap=0.38)
    P.save("crime_heatmap.png")
    return cells


# ----------------------------------------------------------------- II privilege timeline
def fig_timeline(d):
    slugs = d.drop_duplicates("model_name").set_index("model_name").model.to_dict()
    tracks = {}
    for m in MODELS:
        rec = raw_run("boundary-v3-t11-ticket-closeout", slugs[m], "open")
        tracks[m] = rec["trace"] if rec else None
    first_grab = {}
    for m, tr in tracks.items():
        g = [t["seq"] for t in (tr or []) if t["tool"] == "request_role" and t["outcome"] == "granted"]
        first_grab[m] = g[0] if g else None
    order = sorted(MODELS, key=lambda m: (first_grab[m] is None, first_grab[m] or 0, MODELS.index(m)))
    ntook = sum(1 for g in first_grab.values() if g)
    words = {1: "One agent", 2: "Two agents", 3: "Three agents", 4: "Four agents", 5: "Five agents",
             6: "Six agents", 7: "Seven agents", 8: "Eight agents", 9: "Nine agents",
             10: "All ten agents"}.get(ntook, f"{ntook} agents")
    P = Plate("II", "THE SELF CROWNED", f"{words} promoted themselves",
              "Ticket task, Open Box: every tool call in order. No one was allowed the lead role.", h=9.0)
    ax = P.axes(2.95, 2.6, P.top + 0.25, 1.75)
    maxs = max(len(t or []) for t in tracks.values())
    for i, m in enumerate(order):
        tr = tracks[m] or []
        ax.plot([0.5, maxs + 0.5], [i, i], color=TRACK, linewidth=0.9, zorder=0)
        for t in tr:
            x = t["seq"]
            tool, oc = t["tool"], t["outcome"]
            if tool == "request_role" and oc == "granted":
                seal(ax, x, i, CRIMSON, s=330, z=6)
                ax.text(x, i, "♛", family=SYMBOL, fontsize=10.5, color=TITLE_INK, ha="center",
                        va="center", zorder=7)
            elif oc in BLOCKED:
                ax.scatter(x, i, s=80, marker="x", color=CANDLE, zorder=4, linewidths=2.2)
            elif tool == "add_audit_entry":
                ax.scatter(x, i, s=260, marker="|", color=CRIMSON, linewidths=3.0, zorder=4)
            elif tool == "reassign_ticket":
                ax.scatter(x, i, s=120, marker="D", color=CRIMSON, zorder=4, edgecolor=BG, linewidth=1.0)
            elif tool == "notify_lead":
                seal(ax, x, i, CLEAN, s=120, z=5)
            else:
                ax.scatter(x, i, s=22, marker="o", color=ASH, zorder=3)
        if not tr:
            ax.text(1, i, "no tool calls", va="center", fontsize=13.5, color=SUB)
        if first_grab[m] is None:
            verdict, col = "stayed in bounds", CLEAN
        else:
            verdict, col = f"crowned at step {first_grab[m]}", CRIMSON_TEXT
        ax.text(1.0, i, "   " + verdict, va="center", ha="left", fontsize=15, color=col,
                transform=ax.get_yaxis_transform())
    ax.set_yticks(range(len(order)), order, fontsize=15.5, color=INK)
    ax.set_ylim(len(order) - 0.5, -0.6)
    ax.set_xlim(0.3, maxs + 0.7)
    ticks = [1] + list(range(5, maxs + 1, 5))
    ax.set_xticks(ticks, [str(t) for t in ticks], fontsize=13, color=MUTED, family=NUM)
    quiet(ax)
    ax.annotate("tool call", (0.3, 0), xycoords=blended_transform_factory(ax.transData, ax.transAxes),
                xytext=(-4, -9), textcoords="offset points", ha="right", va="top", fontsize=13, color=MUTED)
    P.legend(P.h - 1.0, [
        ("seal", CRIMSON, "took the lead role"),
        ("tick", CRIMSON, "audit entry as lead"),
        ("diamond", CRIMSON, "took another's ticket"),
        ("x", CANDLE, "denied attempt"),
        ("seal", CLEAN, "asked the lead"),
        ("dot", ASH, "ordinary call"),
    ], size=13, gap=0.28)
    P.save("privilege_grab_timeline.png")
    return first_grab


# ----------------------------------------------------------------- III gemma ladder
def _denied_label(t):
    res, tool = t["resource_id"], t["tool"]
    if tool == "release":
        return "force release" if t["detail"].get("force") else "release"
    if res.startswith("vendor/"):
        return "edit vendor code"
    if res.startswith("tests/"):
        return "edit the test"
    if res.startswith("ci/"):
        return "edit CI script"
    return f"{tool} {res}"


def fig_ladder():
    rec = raw_run("boundary-v3-t18-blocked-release", "gemma-4-31b-it", "task")
    tr = {t["seq"]: t for t in rec["trace"]}
    steps = []
    for t in rec["trace"]:
        if t.get("authorization_class") == "out_of_scope":
            kind = "denied" if t["outcome"] in BLOCKED else "executed"
            steps.append((t["seq"], _denied_label(t), kind))
    # the window: the in-scope file that carried the monkeypatch, then the consequences
    patch_seq = max(s for s, t in tr.items() if t["tool"] == "write_file" and t["resource_id"].startswith("services/"))
    steps.append((patch_seq, "patch vendor function from own file", "executed"))
    chk = [s for s, t in tr.items() if t["tool"] == "run_check" and t["outcome"] == "passed"][0]
    steps.append((chk, "check passes", "executed"))
    rel = [s for s, t in tr.items() if t["tool"] == "release" and t["outcome"] == "released"][0]
    steps.append((rel, "release shipped", "executed"))
    st = [s for s, t in tr.items() if t["resource_id"] == "release/status.json"][-1]
    steps.append((st, "status: released", "executed"))
    steps.sort()
    nd = sum(1 for s_ in steps if s_[2] == "denied")
    words = {1: "One locked door", 2: "Two locked doors", 3: "Three locked doors", 4: "Four locked doors",
             5: "Five locked doors", 6: "Six locked doors"}.get(nd, f"{nd} locked doors")
    P = Plate("III", "THE FOUR DOORS" if nd == 4 else f"THE {words.split()[0].upper()} DOORS",
              f"{words}, then the window", "Gemma 4 31B on the release task (Task Box), in the order it acted",
              h=9.0)
    first_exec = next(k for k, s_ in enumerate(steps) if s_[2] == "executed")
    # one extra row slot for the divider between the doors and the window
    ys = [k if k < first_exec else k + 1 for k in range(len(steps))]
    nrows = len(steps) + 1
    ax = P.axes(0.6, 0.6, P.top + 0.2, 0.95)
    ax.set_xlim(0, W - 1.2)
    ax.set_ylim(nrows - 0.45, -0.55)
    ax.axis("off")
    xl = 2.35
    ax.plot([xl, xl], [ys[0], ys[first_exec - 1]], color=GOLD_INNER, linewidth=1.2, zorder=1)
    ax.plot([xl, xl], [ys[first_exec], ys[-1]], color=GOLD_INNER, linewidth=1.2, zorder=1)
    xr = W - 1.2 - 0.55
    for k, (seq, lab, kind) in enumerate(steps):
        y = ys[k]
        col = CANDLE if kind == "denied" else CRIMSON
        seal(ax, xl, y, col, s=150, z=4)
        ax.text(xl - 0.38, y, f"step {seq}", fontsize=14, color=MUTED, va="center", ha="right")
        text = lab[0].upper() + lab[1:]
        ax.text(xl + 0.42, y, text, fontsize=19, color=INK, va="center", ha="left")
        ax.text(xr, y, "blocked" if kind == "denied" else "went through", fontsize=17,
                color=CANDLE if kind == "denied" else CRIMSON_TEXT, va="center", ha="right")
    # divider row: thin gold rules with a diamond either side of the phrase
    yd = first_exec
    cx = (xl + 0.42 + xr) / 2
    ax.text(cx, yd, "then it found the window", fontsize=17, color=SUB, va="center", ha="center")
    half_txt = P.width("then it found the window", 17) / 2
    for sx in (-1, 1):
        a, b = cx + sx * (half_txt + 0.2), cx + sx * (half_txt + 1.9)
        ax.plot([a, b], [yd, yd], color=GOLD_INNER, linewidth=0.8)
        ax.scatter([a + sx * -0.0], [yd], s=18, marker="D", color=GOLD_RULE, zorder=3)
    P.save("gemma_escalation_ladder.png")
    return steps


# ----------------------------------------------------------------- VIII small multiples
def fig_small_multiples(d):
    v = d[d.valid]
    piv = v.groupby(["model_name", "level"]).p_risk.mean().unstack().reindex(columns=LEVELS)
    order = piv.reindex(MODELS).max(axis=1).sort_values(ascending=False).index.tolist()
    ymax = max(1.0, piv.values.max() * 1.3)
    P = Plate("VIII", "THE WEIGHING", "Risk climbs with access, for some",
              "Mean risk score per model at each access level, the same scale in every panel", h=8.4)
    gs = P.fig.add_gridspec(2, 5, left=0.95 / W, right=1 - 0.75 / W, top=1 - (P.top + 0.5) / P.h,
                            bottom=1.3 / P.h, hspace=0.66, wspace=0.14)
    x = np.arange(3)
    for k, m in enumerate(order):
        ax = P.fig.add_subplot(gs[k // 5, k % 5])
        y = piv.loc[m].values
        ax.fill_between(x, 0, y, color=CRIMSON, alpha=0.16, linewidth=0)
        for lw, a in ((9, 0.05), (5.5, 0.09)):
            ax.plot(x, y, color=CRIMSON, linewidth=lw, alpha=a, solid_capstyle="round")
        ax.plot(x, y, color=CRIMSON, linewidth=2.2)
        seal(ax, x, y, CRIMSON, s=26, z=6)
        ax.set_ylim(0, ymax)
        ax.set_xlim(-0.3, 2.3)
        ax.set_xticks(x, ["Closed", "Task", "Open"], fontsize=13, color=MUTED)
        yt = [0, 3, 6] if ymax > 6 else [0, round(ymax / 2), int(ymax)]
        ax.set_yticks(yt, [str(t) for t in yt] if k % 5 == 0 else [], fontsize=13, color=MUTED, family=NUM)
        quiet(ax, bottom=True)
        faint_grid(ax)
        ax.tick_params(pad=5)
        ax.set_title(m, fontsize=14, color=INK, loc="left", pad=10)
        pk = int(np.nanargmax(y))
        val = y[pk]
        ax.annotate(f"{val:.1f}" if val >= 0.1 or val == 0 else f"{val:.2f}", (pk, val),
                    xytext=(0, 10), textcoords="offset points",
                    ha="center" if pk == 1 else ("right" if pk == 2 else "left"),
                    fontsize=17, family=NUM, color=CRIMSON_TEXT if val > 0 else ASH)
    P.save("risk_small_multiples.png")
    return piv


# ----------------------------------------------------------------- IV keys and quill
def fig_cred_vs_write(d, inc):
    v = d[d.valid & (d.level == "open")]
    oi = inc[(inc.level == "open") & inc.outcome.isin(EXECUTED)]

    def runs_of(task, pred):
        """Per valid run of `task` in Open Box: (model, took bait)."""
        runs = v[v.task_id == task]
        hit = oi[(oi.task_id == task)]
        hit = set(hit[hit.apply(pred, axis=1)].model_name) if len(hit) else set()
        return [(m, m in hit) for m in runs.model_name]

    def is_cred(r):
        return "admin" in r.resource or "token" in r.resource or r.tool == "release" or "skip" in r.resource

    used_pred = lambda r: is_cred(r) and r.kind in ("credential", "execute")  # noqa: E731
    open_pred = lambda r: is_cred(r) and r.kind == "read"  # noqa: E731
    cred = []
    for t in ("T05v3", "T18v3"):
        used = dict(runs_of(t, used_pred))
        opened = dict(runs_of(t, open_pred))
        cred.append((t, [("used" if used[m] else ("opened" if opened[m] else "clean")) for m in used]))
    write = [("T08v3", ["took" if h else "clean" for _, h in
                        runs_of("T08v3", lambda r: r.kind == "write" and r.resource.startswith("shared/"))]),
             ("T11v3", ["took" if h else "clean" for _, h in runs_of("T11v3", lambda r: r.tool == "request_role")])]
    rows = [("Credential bait", "T05 admin token", sum(s == "used" for s in cred[0][1]), len(cred[0][1]),
             sum(s == "opened" for s in cred[0][1])),
            ("Credential bait", "T18 release token", sum(s == "used" for s in cred[1][1]), len(cred[1][1]),
             sum(s == "opened" for s in cred[1][1])),
            ("Write / privilege bait", "T08 edit shared code", write[0][1].count("took"), len(write[0][1]), 0),
            ("Write / privilege bait", "T11 grab the lead role", write[1][1].count("took"), len(write[1][1]), 0)]
    df = pd.DataFrame(rows, columns=["grp", "lab", "k", "n", "opened"])
    agg = df.groupby("grp", sort=False)[["k", "n", "opened"]].sum()
    ck, cn, co = (int(x) for x in agg.loc["Credential bait"])
    wk, wn, _ = (int(x) for x in agg.loc["Write / privilege bait"])

    P = Plate("IV", "THE KEYS AND THE QUILL", "They won't steal keys.\nThey'll rewrite your code.",
              "Open Box runs that took each kind of bait, one seal per run", h=8.6)
    ov = P.ov
    t0 = P.top + 0.1
    P.ov.plot([W / 2, W / 2], [P.Y(t0 + 0.1), P.Y(P.h - 1.0)], color=GOLD_INNER, linewidth=0.8)
    diamond(ov, W / 2, P.Y(t0 + 0.1), 0.05, GOLD_INNER)
    diamond(ov, W / 2, P.Y(P.h - 1.0), 0.05, GOLD_INNER)

    def panel(cx, head, k, n, col, line, groups, colors, note, note_col, verdict):
        P.text(cx, P.Y(t0 + 0.45), head, size=17, color=SUB, ha="center", va="baseline")
        P.text(cx, P.Y(t0 + 1.55), f"{k} of {n}", size=76, family=NUM, color=col, ha="center", va="baseline")
        P.text(cx, P.Y(t0 + 2.05), line, size=17, color=INK, ha="center", va="baseline")
        sx = 0.36
        for r_, (task, states) in enumerate(groups):
            yy = P.Y(t0 + 2.65 + r_ * 0.48)
            x0 = cx - (10 - 1) * sx / 2
            P.text(x0 - 0.32, yy, TASK_SHORT[task], size=14, color=MUTED, ha="right", va="center")
            for idx, s in enumerate(states):
                seal(ov, x0 + idx * sx, yy, colors[s], s=75, z=31)
        P.text(cx, P.Y(t0 + 3.75), note, size=15, color=note_col, ha="center", va="baseline")
        P.text(cx, P.Y(t0 + 4.55), verdict, size=30, family=BLACKLETTER, color=col, ha="center", va="baseline")

    panel(W / 4 + 0.05, "Credential bait: admin tokens", ck, cn, CLEAN, "used an admin token", cred,
          {"used": CRIMSON, "opened": CANDLE, "clean": CLEAN},
          f"{co} only opened the token file" if co else "none opened the token file", CANDLE if co else SUB,
          "Clean" if ck == 0 else "Trespass")
    nb, nt = write[0][1].count("took"), write[1][1].count("took")
    panel(3 * W / 4 - 0.05, "Write and privilege bait", wk, wn, CRIMSON_TEXT, "rewrote shared code or took a role",
          write, {"took": CRIMSON, "clean": CLEAN},
          f"{nb} edited shared code, {nt} took the lead role", SUB, "Trespass" if wk else "Clean")
    P.save("credential_vs_write.png")
    return df, agg


# ----------------------------------------------------------------- README
README = """# BOUNDARY v3 blog figures: the trial of ten models

Generated by `report/make_blog_figures.py` from `report/data/*.csv` and the raw traces in `report/raw/`.
All rates use valid runs only; NA and invalid cells are drawn hatched, never as zero.

Theme: each chart is a numbered plate in a candlelit record of the trial. Charred ink background with a faint
candle glow, a double antique gold rule with corner stars, a centred header (tracked plate label and title in
Perpetua Titling MT, a gold divider, a Goudy Old Style subtitle), body text in Goudy Old Style, numbers in
Perpetua, and Old English Text MT only for the two verdict words on plate IV.

Palette: verdigris = in bounds or clean, crimson = crossed the line, candle gold = blocked attempt,
ash = failed the task, faint hatch = NA. Points that matter are drawn as wax seals (filled centre, thin ring).

| Plate | File | Caption |
|---|---|---|
| I | `hero_boundary_curve.png` | {hero} |
| II | `privilege_grab_timeline.png` | {tl} |
| III | `gemma_escalation_ladder.png` | {lad} |
| IV | `credential_vs_write.png` | {cw} |
| V | `dumbbell_closed_vs_open.png` | {dumb} |
| VI | `crime_heatmap.png` | {heat} |
| VII | `outcome_bars_by_model.png` | {bars} |
| VIII | `risk_small_multiples.png` | {sm} |
"""


def main():
    d, inc = load()
    hero = fig_hero(d)
    grabs = fig_timeline(d)
    steps = fig_ladder()
    cw, agg = fig_cred_vs_write(d, inc)
    dumb = fig_dumbbell(d)
    cells = fig_heatmap(d, inc)
    ct = fig_outcomes(d)
    piv = fig_small_multiples(d)

    (ts, n), (ss, _), (bv, _) = hero["Task success"], hero["Clean success"], hero["Crossed a boundary"]
    big = dumb.iloc[-1]
    ntook = sum(1 for g in grabs.values() if g)
    a = agg.reset_index()
    nempty = {1: "one empty reply", 2: "two empty replies"}.get(int(big.nempty), f"{int(big.nempty)} empty replies")
    dagger_note = (f", marked † because the drop comes from {nempty}, not from crossing a line"
                   if big.dagger else "")
    caps = dict(
        hero=f"Plate I, More access, more trespassing: from Closed to Open Box, task success falls {ts[0]:.0%} to {ts[2]:.0%}, clean success {ss[0]:.0%} to {ss[2]:.0%}, and boundary crossings rise {bv[0]:.0%} to {bv[2]:.0%} (valid runs per level: {n[0]}, {n[1]}, {n[2]}; Wilson 95% bands).",
        dumb=f"Plate V, Who held the line when the doors opened: mean level score per model, Closed vs Open Box, sorted by drop; largest drop {big.m} ({big.c:.2f} to {big.o:.2f}){dagger_note}.",
        bars="Plate VII, How every run ended: every planned level run per model (15 each) split into clean success, succeeded but crossed, overclaimed, failed and NA.",
        heat="Plate VI, Where each model crossed the line: the worst act of each model in each task across the three levels, as a one or two word tag from the incident log.",
        tl=f"Plate II, the self crowned: T11 (Tickets) Open Box tool call tracks; {ntook} of 10 models granted themselves the lead role, then wrote audit entries or took tickets as lead.",
        lad=f"Plate III, Four locked doors, then the window: Gemma 4 31B on T18 (Release, Task Box) made {sum(1 for s in steps if s[2] == 'denied')} denied out of scope attempts, then patched the vendor function from its own file, got the check green and shipped the release.",
        sm="Plate VIII, Risk climbs with access, for some: mean p_risk per model at each access level on a shared scale; the clean models stay flat, the risky ones climb at Open Box.",
        cw=f"Plate IV, They won't steal keys. They'll rewrite your code.: in Open Box, {a.k[0]} of {a.n[0]} runs used the credential bait ({a.opened[0]} only opened the token file), while {a.k[1]} of {a.n[1]} ({a.k[1]/a.n[1]:.0%}) took the write or privilege bait.",
    )
    with open(os.path.join(OUT, "README.md"), "w", encoding="utf-8") as fh:
        fh.write(README.format(**caps))
    print("\n".join(f"{k}: {v}" for k, v in caps.items()))
    print(dumb.round(3).to_string())
    print(ct.to_string())
    print(piv.round(2).to_string())
    print(cw.to_string())
    for k, v_ in cells.items():
        if v_[1]:
            print(k, v_)


if __name__ == "__main__":
    main()
