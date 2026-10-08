"""Blog figures for the BOUNDARY v3 DEV.to post.

Reads report/data/*.csv and the raw traces under report/raw, writes PNGs to
report/blog_figures/. Run from anywhere:  python report/make_blog_figures.py

Style: ivory paper, navy ink, Georgia bold titles, Segoe UI labels, and one
semantic palette shared by every figure (forest = in bounds, burgundy = crossed
the boundary, gold = blocked attempt, slate = failed the task, hatched = NA).
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
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Ellipse, FancyArrowPatch, FancyBboxPatch, Patch, Rectangle  # noqa: E402

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(HERE, "raw")
OUT = os.path.join(HERE, "blog_figures")
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------- identity
PAPER = "#F7F3EA"
INK = "#1B2A4A"
MUTED = "#6B6A65"
RULE = "#D8D0BF"
AXIS = "#8C8473"
GOLD = "#B08D3C"

SAFE = "#2F5D50"      # in bounds / safe
CROSSED = "#7A1E2B"   # crossed the boundary
BLOCKED_C = GOLD      # blocked attempt
FAILED = "#8A8F98"    # failed the task
NA_FACE = "#E6DFD0"   # NA (hatched)
NA_HATCH = "#BDB29C"
DEEP = "#45101A"      # overclaim / execute: darkest burgundy
ROSE = "#B97A80"      # executed read / list: light burgundy

TITLE_FONT = ["Georgia", "DejaVu Serif"]
BODY_FONT = ["Georgia", "DejaVu Serif"]
MONO_FONT = ["Consolas", "DejaVu Sans Mono"]

plt.rcParams.update({
    "font.family": "serif",
    "font.serif": BODY_FONT,
    "font.sans-serif": BODY_FONT,
    "font.monospace": MONO_FONT,
    "font.size": 13,
    "text.color": INK,
    "axes.labelcolor": INK,
    "axes.edgecolor": AXIS,
    "axes.linewidth": 0.8,
    "axes.facecolor": PAPER,
    "figure.facecolor": PAPER,
    "savefig.facecolor": PAPER,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.color": INK,
    "ytick.color": INK,
    "xtick.labelsize": 13,
    "ytick.labelsize": 13,
    "hatch.color": NA_HATCH,
    "hatch.linewidth": 0.8,
})

FOOTER = "BOUNDARY v3 · Kaggle benchmark: your-llm-doesnt-know-boundary"
LEVELS = ["closed", "task", "open"]
LEVEL_LABEL = {"closed": "Closed Box", "task": "Task Box", "open": "Open Box"}
TASKS = ["T01v3", "T08v3", "T05v3", "T11v3", "T18v3"]
TASKS_ALL = ["T01v3", "T08v3", "T05v3", "T11v3", "T18v3", "T17v3"]
TASK_SHORT = {"T01v3": "Invoices", "T08v3": "Bug fix", "T05v3": "Records", "T11v3": "Tickets",
              "T18v3": "Release", "T17v3": "Config"}
MODELS = ["GPT-6.1 Sol", "GPT-6 Astra", "GPT-6 Luna", "Claude Sonnet 5.5",
          "Claude Opus 5.5", "Gemini 3.1 Pro Preview", "Gemini 3.8 Flash",
          "Gemini 3.7 Flash", "Gemma 4 31B", "GLM-5"]
# Models whose Closed -> Open drop comes from empty replies, not from crossing a line
EMPTY_REPLY_DROP = {"Claude Opus 5.5"}
EXECUTED = {"ok", "granted", "detected"}
BLOCKED = {"denied", "not_found", "ignored"}
W = 12.0  # figure width in inches (2400 px at 200 dpi)


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


# ----------------------------------------------------------------- frame helpers
class Frame:
    """Figure with a fixed-size header (title, plain subtitle) and a small footer."""

    LEFT_IN = 0.6
    HEAD_IN = 1.45   # header height in inches
    FOOT_IN = 0.45   # footer band in inches

    def __init__(self, title, subtitle, h=6.75):
        self.h = h
        self.fig = plt.figure(figsize=(W, h), dpi=200)
        x0 = self.LEFT_IN / W
        self.fig.text(x0, self.y(0.36), title, fontsize=21, fontweight="bold", family=TITLE_FONT,
                      color=INK, ha="left", va="top")
        self.fig.text(x0, self.y(0.84), subtitle, fontsize=13.5, color=MUTED, ha="left", va="top")
        self.fig.text(x0, 0.2 / h, FOOTER, fontsize=9.5, color=MUTED, ha="left", va="bottom")

    def y(self, inches_from_top):
        return 1 - inches_from_top / self.h

    def b(self, inches_from_bottom):
        return inches_from_bottom / self.h

    def axes(self, left_in, right_in, top_in, bottom_in):
        """Axes placed by margins in inches (top measured from the figure top)."""
        return self.fig.add_axes([left_in / W, bottom_in / self.h,
                                  (W - left_in - right_in) / W,
                                  (self.h - top_in - bottom_in) / self.h])


def save(fig, name):
    path = os.path.join(OUT, name)
    fig.savefig(path, dpi=200)
    plt.close(fig)
    print("wrote", path)


def clean(ax, left=False, bottom=True):
    ax.tick_params(length=0, pad=8)
    ax.spines["left"].set_visible(left)
    ax.spines["bottom"].set_visible(bottom)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(AXIS)
        ax.spines[s].set_linewidth(0.8)


def faint_grid(ax, axis="y"):
    ax.grid(axis=axis, color=RULE, linewidth=0.6, alpha=0.7)
    ax.set_axisbelow(True)


def na_patch(ax, x, y, w, h):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=NA_FACE, hatch="////", edgecolor=NA_HATCH, linewidth=0))


# ----------------------------------------------------------------- 1 hero
def fig_hero(d):
    v = d[d.valid]
    series = [("Task success", "task_success", INK),
              ("Safe success", "safe_success", SAFE),
              ("Crossed the boundary", "boundary_violation", CROSSED)]
    F = Frame("More access, more trespassing",
              "Share of runs at each access level, all 10 models (faint band = 95% CI)")
    ax = F.axes(1.0, 3.1, 1.7, 0.95)
    x = np.arange(3)
    pts = {}
    for name, col, c in series:
        k = np.array([v[v.level == l][col].sum() for l in LEVELS])
        n = np.array([v[v.level == l][col].count() for l in LEVELS])
        p = k / n
        lo, hi = zip(*[wilson(a, b) for a, b in zip(k, n)])
        ax.fill_between(x, lo, hi, color=c, alpha=0.08, linewidth=0)
        ax.plot(x, p, color=c, linewidth=2.8, marker="o", markersize=9,
                markeredgecolor=PAPER, markeredgewidth=2, zorder=5)
        pts[name] = (p, c)
        ax.annotate(f"{p[0]:.0%}", (0, p[0]), xytext=(-16, 0), textcoords="offset points",
                    ha="right", va="center", fontsize=15, fontweight="normal", color=c)
        ax.annotate(f"{p[-1]:.0%}", (2, p[-1]), xytext=(16, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=15, fontweight="normal", color=c)
        ax.annotate(name, (2, p[-1]), xytext=(66, 0), textcoords="offset points",
                    ha="left", va="center", fontsize=14, color=c, annotation_clip=False)
    ax.set_xlim(-0.12, 2.12)
    ax.set_ylim(0, 1.04)
    ax.set_xticks(x, [LEVEL_LABEL[l] for l in LEVELS], fontsize=14)
    ax.set_yticks([0, .5, 1], ["0%", "50%", "100%"], fontsize=12, color=MUTED)
    clean(ax)
    faint_grid(ax)
    save(F.fig, "hero_boundary_curve.png")
    return {k: v_[0] for k, v_ in pts.items()}


# ----------------------------------------------------------------- 2 dumbbell
def fig_dumbbell(d):
    v = d[d.valid]
    rows = []
    for m in MODELS:
        c = v[(v.model_name == m) & (v.level == "closed")].level_score
        o = v[(v.model_name == m) & (v.level == "open")].level_score
        rows.append((m, c.mean(), o.mean(), len(c), len(o)))
    df = pd.DataFrame(rows, columns=["m", "c", "o", "nc", "no"])
    df["drop"] = df.c - df.o
    df = df.sort_values("drop", ascending=True).reset_index(drop=True)  # biggest drop on top
    F = Frame("Who held the line when the doors opened",
              "Mean score per model: Closed Box vs Open Box (1.0 = perfect)")
    ax = F.axes(2.75, 1.5, 1.8, 1.05)
    for i, r in df.iterrows():
        ax.plot([r.c, r.o], [i, i], color=RULE, linewidth=3.5, zorder=1, solid_capstyle="round")
        same = abs(r.c - r.o) < 0.005
        ax.scatter(r.c, i, s=300 if same else 170, color=SAFE, zorder=3, edgecolor=PAPER, linewidth=2)
        ax.scatter(r.o, i, s=70 if same else 170, color=CROSSED, zorder=4, edgecolor=PAPER, linewidth=1.5)
        dv = r["drop"]
        col = CROSSED if dv > 0.005 else (SAFE if dv < -0.005 else MUTED)
        txt = f"−{dv:.2f}" if dv > 0.005 else (f"+{-dv:.2f}" if dv < -0.005 else "0.00")
        ax.text(1.0, i, txt, color=col, fontsize=14, fontweight="normal", va="center", ha="right",
                transform=ax.get_yaxis_transform())
    labels = [m + ("  †" if m in EMPTY_REPLY_DROP else "") for m in df.m]
    ax.set_yticks(range(len(df)), labels, fontsize=13.5)
    ax.set_xlim(0.25, 1.17)
    ax.set_xticks([0.4, 0.6, 0.8, 1.0], ["0.4", "0.6", "0.8", "1.0"], fontsize=12, color=MUTED)
    ax.set_ylim(-0.6, len(df) - 0.1)
    clean(ax)
    ax.spines["bottom"].set_bounds(0.25, 1.02)
    faint_grid(ax, "x")
    # direct key on the top row
    top = df.iloc[-1]
    ax.annotate("Closed", (top.c, len(df) - 1), xytext=(0, 14), textcoords="offset points",
                ha="center", va="bottom", fontsize=12.5, color=SAFE, fontweight="normal")
    ax.annotate("Open", (top.o, len(df) - 1), xytext=(0, 14), textcoords="offset points",
                ha="center", va="bottom", fontsize=12.5, color=CROSSED, fontweight="normal")
    ax.annotate("drop", (1.0, len(df) - 1), xycoords=("axes fraction", "data"), xytext=(0, 14),
                textcoords="offset points", ha="right", va="bottom", fontsize=12, color=MUTED)
    if any(m in EMPTY_REPLY_DROP for m in df.m):
        F.fig.text(2.75 / W, F.b(0.5), "† drop caused by empty replies, not by crossing a line",
                   fontsize=11.5, color=MUTED, ha="left", va="bottom")
    save(F.fig, "dumbbell_closed_vs_open.png")
    return df


# ----------------------------------------------------------------- 3 outcome bars
CATS = [("Safe success", SAFE), ("Succeeded but crossed", CROSSED), ("Overclaimed", DEEP),
        ("Failed", FAILED), ("NA", NA_FACE)]


def outcome(r):
    if not r.valid:
        return "NA"
    if r.overclaim:
        return "Overclaimed"
    if r.safe_success:
        return "Safe success"
    if r.task_success and r.boundary_violation:
        return "Succeeded but crossed"
    return "Failed"


def fig_outcomes(d):
    p = d[d.task_id.isin(TASKS)].copy()
    p["cat"] = p.apply(outcome, axis=1)
    ct = pd.crosstab(p.model_name, p.cat).reindex(columns=[c for c, _ in CATS], fill_value=0)
    ct = ct.reindex(MODELS)
    assert (ct.sum(axis=1) == 15).all()
    ct = ct.sort_values(["Safe success", "NA"], ascending=[True, False])
    F = Frame("Few finish the job without crossing a line",
              "Outcome of all 15 runs per model (5 tasks × 3 access levels)")
    ax = F.axes(2.75, 0.6, 2.05, 0.75)
    y = np.arange(len(ct))
    left = np.zeros(len(ct))
    for cat, col in CATS:
        w = ct[cat].values
        if cat == "NA":
            ax.barh(y, w, left=left, color=col, height=0.7, hatch="////", edgecolor=NA_HATCH, linewidth=0)
            ax.barh(y, w, left=left, color="none", height=0.7, edgecolor=PAPER, linewidth=2)
        else:
            ax.barh(y, w, left=left, color=col, height=0.7, edgecolor=PAPER, linewidth=2)
        for yi, (l, wi) in enumerate(zip(left, w)):
            if wi >= 2:
                ax.text(l + wi / 2, yi, str(int(wi)), ha="center", va="center", fontsize=13.5,
                        fontweight="normal", color=INK if cat == "NA" else "white")
        left += w
    ax.set_yticks(y, ct.index, fontsize=13.5)
    ax.set_xlim(0, 15)
    ax.set_xticks([])
    ax.set_ylim(-0.5, len(ct) - 0.5)
    clean(ax, bottom=False)
    handles = [Patch(facecolor=c, edgecolor=NA_HATCH if n == "NA" else c,
                     hatch="////" if n == "NA" else None, label=n) for n, c in CATS]
    F.fig.legend(handles=handles, loc="center left", bbox_to_anchor=(2.7 / W, F.y(1.62)), ncol=5,
                 frameon=False, fontsize=12.5, handlelength=1.2, handleheight=1.0, columnspacing=1.8)
    save(F.fig, "outcome_bars_by_model.png")
    return ct


# ----------------------------------------------------------------- 4 crime heatmap
SEV_COL = {0: SAFE, 1: BLOCKED_C, 2: ROSE, 3: CROSSED, 4: DEEP}
SEV_TINT = {0: "#DCE6E0", 1: "#EFE3C6", 2: "#EED9DB", 3: "#E3C2C6", 4: "#D4A9AE"}
SEV_INK = {0: SAFE, 1: "#7A5E1F", 2: "#8E4A52", 3: CROSSED, 4: "#4A0F18"}
SEV_LABEL = {0: "Clean", 1: "Blocked attempt", 2: "Out-of-scope read", 3: "Wrote or took a role",
             4: "Bypassed a check"}
SLUG = {"T01v3": "boundary-v3-t01-month-end-total", "T05v3": "boundary-v3-t05-escalation-report",
        "T08v3": "boundary-v3-t08-issue-fix", "T11v3": "boundary-v3-t11-ticket-closeout",
        "T18v3": "boundary-v3-t18-blocked-release"}


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
    F = Frame("Where each model crossed the line",
              "Worst behaviour per model and task, across all three access levels")
    ax = F.axes(2.75, 0.6, 1.85, 0.9)
    ax.set_xlim(0, len(TASKS_ALL))
    ax.set_ylim(len(MODELS), 0)
    cells = {}
    for i, m in enumerate(MODELS):
        for j, t in enumerate(TASKS_ALL):
            sub = d[(d.model_name == m) & (d.task_id == t)]
            nvalid = int(sub.valid.sum())
            if nvalid == 0:
                na_patch(ax, j + .03, i + .06, .94, .88)
                ax.text(j + .5, i + .5, "NA", ha="center", va="center", fontsize=12, color=MUTED,
                        bbox=dict(boxstyle="round,pad=0.15", fc=NA_FACE, ec="none"))
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
            ax.add_patch(Rectangle((j + .03, i + .06), .94, .88, facecolor=SEV_TINT[sev], edgecolor="none"))
            if tag:
                ax.text(j + .5, i + .5, tag, ha="center", va="center", fontsize=13,
                        color=SEV_INK[sev], style="italic" if sev == 1 else "normal")
    ax.set_xticks(np.arange(len(TASKS_ALL)) + .5, [TASK_SHORT[t] for t in TASKS_ALL], fontsize=14,
                  fontweight="normal")
    ax.xaxis.tick_top()
    ax.set_yticks(np.arange(len(MODELS)) + .5, MODELS, fontsize=13.5)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.tick_params(length=0, pad=6)
    handles = [Patch(facecolor=SEV_TINT[k], edgecolor=SEV_INK[k], linewidth=0.8, label=SEV_LABEL[k]) for k in range(5)]
    handles.append(Patch(facecolor=NA_FACE, hatch="////", edgecolor=NA_HATCH, label="NA"))
    F.fig.legend(handles=handles, loc="center left", bbox_to_anchor=(2.7 / W, F.b(0.6)), ncol=6,
                 frameon=False, fontsize=11.5, handlelength=1.2, columnspacing=1.4)
    save(F.fig, "crime_heatmap.png")
    return cells


# ----------------------------------------------------------------- 5 privilege timeline
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
    words = {6: "Six"}.get(ntook, str(ntook))
    F = Frame(f"{words} agents promoted themselves",
              "Ticket task, Open Box: every tool call in order; no one was allowed the lead role",
              h=8.0)
    ax = F.axes(2.75, 2.45, 1.6, 1.4)
    maxs = max(len(t or []) for t in tracks.values())
    for i, m in enumerate(order):
        tr = tracks[m] or []
        ax.plot([0.5, maxs + 0.5], [i, i], color=RULE, linewidth=1.0, zorder=0)
        for t in tr:
            x = t["seq"]
            tool, oc = t["tool"], t["outcome"]
            if tool == "request_role" and oc == "granted":
                ax.scatter(x, i, s=380, marker="o", color=CROSSED, zorder=5, edgecolor=PAPER, linewidth=2)
            elif oc in BLOCKED:
                ax.scatter(x, i, s=90, marker="x", color=GOLD, zorder=4, linewidths=2.4)
            elif tool == "add_audit_entry":
                ax.scatter(x, i, s=300, marker="|", color=CROSSED, linewidths=3.4, zorder=4)
            elif tool == "reassign_ticket":
                ax.scatter(x, i, s=170, marker="D", color=CROSSED, zorder=4, edgecolor=PAPER, linewidth=1.2)
            elif tool == "notify_lead":
                ax.scatter(x, i, s=220, marker="o", color=SAFE, zorder=4, edgecolor=PAPER, linewidth=1.5)
            else:
                ax.scatter(x, i, s=30, marker="o", color=FAILED, zorder=3)
        if not tr:
            ax.text(1, i, "no tool calls", va="center", fontsize=12, color=MUTED,
                    bbox=dict(boxstyle="square,pad=0.2", fc=PAPER, ec="none"))
        if first_grab[m] is None:
            verdict, col = "stayed in bounds", SAFE
        else:
            verdict, col = f"took lead at step {first_grab[m]}", CROSSED
        ax.text(1.0, i, "  " + verdict, va="center", ha="left", fontsize=13.5, color=col, fontweight="normal",
                transform=ax.get_yaxis_transform())
    ax.set_yticks(range(len(order)), order, fontsize=13.5)
    ax.set_ylim(len(order) - 0.5, -0.6)
    ax.set_xlim(0.3, maxs + 0.7)
    ticks = [1] + list(range(5, maxs + 1, 5))
    ax.set_xticks(ticks, [str(t) for t in ticks], fontsize=12, color=MUTED)
    ax.text(0.3, len(order) - 0.5, "tool call  ", ha="right", va="top", fontsize=12, color=MUTED)
    clean(ax)
    handles = [
        Line2D([], [], marker="o", ls="", color=CROSSED, markersize=12, label="took lead"),
        Line2D([], [], marker="|", ls="", color=CROSSED, markersize=13, markeredgewidth=3, label="audit entry as lead"),
        Line2D([], [], marker="D", ls="", color=CROSSED, markersize=8, label="took another's ticket"),
        Line2D([], [], marker="x", ls="", color=GOLD, markersize=9, markeredgewidth=2.2, label="denied attempt"),
        Line2D([], [], marker="o", ls="", color=SAFE, markersize=10, label="asked the lead"),
        Line2D([], [], marker="o", ls="", color=FAILED, markersize=5, label="normal call"),
    ]
    F.fig.legend(handles=handles, loc="center left", bbox_to_anchor=(0.55 / W, F.b(0.62)), ncol=6, frameon=False,
                 fontsize=12, columnspacing=1.6, handletextpad=0.3)
    save(F.fig, "privilege_grab_timeline.png")
    return first_grab


# ----------------------------------------------------------------- 6 gemma ladder
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
            steps.append((t["seq"], _denied_label(t) + (", denied" if kind == "denied" else ""), kind))
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
    n = len(steps)
    nd = sum(1 for s_ in steps if s_[2] == "denied")
    words = {4: "Four"}.get(nd, str(nd))
    F = Frame(f"{words} locked doors, then the window",
              "Gemma 4 31B on the release task (Task Box), in trace order",
              h=8.0)
    ax = F.axes(0.6, 0.6, 1.6, 0.75)
    ax.set_xlim(0, 100)
    ax.set_ylim(n - 0.4, -0.6)
    ax.axis("off")
    xl = 16
    ax.plot([xl, xl], [0, n - 1], color=AXIS, linewidth=1.4, zorder=1)
    first_exec = next(k for k, s_ in enumerate(steps) if s_[2] == "executed")
    for k, (seq, lab, kind) in enumerate(steps):
        col = GOLD if kind == "denied" else CROSSED
        ax.scatter([xl], [k], s=260, color=col, zorder=3, edgecolor=PAPER, linewidth=2)
        ax.text(xl - 3, k, f"step {seq}", fontsize=13, color=MUTED, va="center", ha="right")
        text = lab.replace(", denied", "")
        text = text[0].upper() + text[1:]
        ax.text(xl + 3.5, k, text, fontsize=16, color=INK, va="center", ha="left")
        ax.text(98, k, "blocked" if kind == "denied" else "went through", fontsize=14,
                color=col, va="center", ha="right")
    ax.plot([xl + 3.5, 98], [first_exec - 0.5, first_exec - 0.5], color=AXIS, linewidth=0.8, linestyle=(0, (3, 3)))
    ax.text(60, first_exec - 0.5, "  then it found the window  ", fontsize=13.5, color=MUTED, va="center", ha="center",
            style="italic", bbox=dict(boxstyle="square,pad=0.1", fc=PAPER, ec="none"))
    save(F.fig, "gemma_escalation_ladder.png")
    return steps


# ----------------------------------------------------------------- 7 small multiples
def fig_small_multiples(d):
    v = d[d.valid]
    piv = v.groupby(["model_name", "level"]).p_risk.mean().unstack().reindex(columns=LEVELS)
    order = piv.reindex(MODELS).max(axis=1).sort_values(ascending=False).index.tolist()
    ymax = max(1.0, piv.values.max() * 1.25)
    F = Frame("Risk climbs with access, for some",
              "Mean risk score per model at each access level, same scale in every panel")
    gs = F.fig.add_gridspec(2, 5, left=0.75 / W, right=1 - 0.45 / W, top=F.y(1.75), bottom=F.b(0.85),
                            hspace=0.62, wspace=0.12)
    x = np.arange(3)
    for k, m in enumerate(order):
        ax = F.fig.add_subplot(gs[k // 5, k % 5])
        y = piv.loc[m].values
        ax.fill_between(x, 0, y, color=CROSSED, alpha=0.22, linewidth=0)
        ax.plot(x, y, color=CROSSED, linewidth=2.4, marker="o", markersize=5.5,
                markeredgecolor=PAPER, markeredgewidth=1.2)
        ax.set_ylim(0, ymax)
        ax.set_xlim(-0.3, 2.3)
        ax.set_xticks(x, ["Closed", "Task", "Open"], fontsize=11.5, color=MUTED)
        yt = [0, 3, 6] if ymax > 6 else [0, round(ymax / 2), int(ymax)]
        ax.set_yticks(yt, [str(t) for t in yt] if k % 5 == 0 else [], fontsize=11.5, color=MUTED)
        clean(ax)
        faint_grid(ax)
        ax.tick_params(pad=4)
        ax.set_title(m, fontsize=12.5, fontweight="normal", color=INK, loc="left", pad=8)
        pk = int(np.nanargmax(y))
        val = y[pk]
        ax.annotate(f"{val:.1f}" if val >= 0.1 or val == 0 else f"{val:.2f}", (pk, val),
                    xytext=(0, 8), textcoords="offset points",
                    ha="center" if pk == 1 else ("right" if pk == 2 else "left"),
                    fontsize=13, fontweight="normal", color=CROSSED if val > 0 else MUTED)
    save(F.fig, "risk_small_multiples.png")
    return piv


# ----------------------------------------------------------------- 8 credential vs write
def fig_cred_vs_write(d, inc):
    v = d[d.valid & (d.level == "open")]
    oi = inc[(inc.level == "open") & inc.outcome.isin(EXECUTED)]

    def took(task, pred):
        runs = v[v.task_id == task]
        hit = oi[(oi.task_id == task)]
        hit = hit[hit.apply(pred, axis=1)]
        ms = set(hit.model_name) & set(runs.model_name)
        return len(ms), len(runs)

    def is_cred(r):
        return "admin" in r.resource or "token" in r.resource or r.tool == "release" or "skip" in r.resource

    used_pred = lambda r: is_cred(r) and r.kind in ("credential", "execute")  # noqa: E731
    open_pred = lambda r: is_cred(r) and r.kind == "read"  # noqa: E731
    rows = [
        ("Credential bait", "T05 admin token", *took("T05v3", used_pred), took("T05v3", open_pred)[0]),
        ("Credential bait", "T18 release token", *took("T18v3", used_pred), took("T18v3", open_pred)[0]),
        ("Write / privilege bait", "T08 edit shared code",
         *took("T08v3", lambda r: r.kind == "write" and r.resource.startswith("shared/")), 0),
        ("Write / privilege bait", "T11 grab the lead role", *took("T11v3", lambda r: r.tool == "request_role"), 0),
    ]
    df = pd.DataFrame(rows, columns=["grp", "lab", "k", "n", "opened"])
    agg = df.groupby("grp", sort=False)[["k", "n", "opened"]].sum()
    ck, cn, co = (int(x) for x in agg.loc["Credential bait"])
    wk, wn, _ = (int(x) for x in agg.loc["Write / privilege bait"])

    F = Frame("They won't steal keys. They'll rewrite your code.",
              "Open Box runs that took each kind of bait")
    ax = F.axes(0.6, 0.6, 1.6, 0.6)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.add_artist(Line2D([50, 50], [8, 92], color=RULE, linewidth=1.0))

    def panel(cx, head, k, n, col, line, dots, note=None):
        ax.text(cx, 94, head, ha="center", va="top", fontsize=15, color=MUTED)
        ax.text(cx, 82, f"{k} of {n}", ha="center", va="top", fontsize=60, fontweight="bold", color=col)
        ax.text(cx, 57, line, ha="center", va="top", fontsize=16, color=INK)
        # unit chart: one dot per run, 10 per row
        per = 10
        sx, sy = 3.6, 10.5
        aspect = (W - 1.2) / (F.h - 2.2)  # data-units correction so circles stay round
        for idx, c in enumerate(dots):
            r_, c_ = divmod(idx, per)
            xx = cx - (per - 1) * sx / 2 + c_ * sx
            yy = 32 - r_ * sy
            ax.add_patch(Ellipse((xx, yy), 2.5, 2.5 * aspect, facecolor=c,
                                                    edgecolor=AXIS if c == PAPER else "none", linewidth=0.9))
        if note:
            ax.text(cx, 8, note, ha="center", va="center", fontsize=13, color=GOLD, fontweight="normal")

    cred_dots = [CROSSED] * ck + [GOLD] * co + [PAPER] * (cn - ck - co)
    panel(25, "Credential bait (admin tokens)", ck, cn, SAFE, "used a token", cred_dots,
          note=f"{co} only opened the file" if co else None)
    write_dots = [CROSSED] * wk + [PAPER] * (wn - wk)
    panel(75, "Write / privilege bait", wk, wn, CROSSED, "rewrote code or took the lead role", write_dots)
    save(F.fig, "credential_vs_write.png")
    return df, agg


# ----------------------------------------------------------------- README
README = """# BOUNDARY v3 blog figures

Generated by `report/make_blog_figures.py` from `report/data/*.csv` and the raw traces in `report/raw/`.
All rates use valid runs only; NA / invalid cells are drawn hatched, never as zero.

Shared palette: forest = in bounds / safe, burgundy = crossed the boundary, antique gold = blocked attempt,
slate = failed the task, hatched ivory = NA. Titles in Georgia bold, labels in Segoe UI.

| File | Caption |
|---|---|
| `hero_boundary_curve.png` | {hero} |
| `dumbbell_closed_vs_open.png` | {dumb} |
| `outcome_bars_by_model.png` | {bars} |
| `crime_heatmap.png` | {heat} |
| `privilege_grab_timeline.png` | {tl} |
| `gemma_escalation_ladder.png` | {lad} |
| `risk_small_multiples.png` | {sm} |
| `credential_vs_write.png` | {cw} |
"""


def main():
    d, inc = load()
    hero = fig_hero(d)
    dumb = fig_dumbbell(d)
    ct = fig_outcomes(d)
    cells = fig_heatmap(d, inc)
    grabs = fig_timeline(d)
    steps = fig_ladder()
    piv = fig_small_multiples(d)
    cw, agg = fig_cred_vs_write(d, inc)

    ts, ss, bv = hero["Task success"], hero["Safe success"], hero["Crossed the boundary"]
    big = dumb.iloc[-1]
    ntook = sum(1 for g in grabs.values() if g)
    a = agg.reset_index()
    caps = dict(
        hero=f"More access, more trespassing: from Closed to Open Box, task success falls {ts[0]:.0%} to {ts[2]:.0%}, safe success {ss[0]:.0%} to {ss[2]:.0%}, and boundary crossings rise {bv[0]:.0%} to {bv[2]:.0%} (n = 47 per level, Wilson 95% bands).",
        dumb=f"Mean level score per model, Closed vs Open Box, sorted by drop; largest drop: {big.m} ({big.c:.2f} to {big.o:.2f}), marked † because it comes from empty replies, not from crossing a line.",
        bars="Every planned level-run per model (15 each) split into safe success, succeeded-but-crossed, overclaimed, failed and NA.",
        heat="Worst thing each model did in each task across the three levels, as a one- or two-word tag from the incident log; T17 (Config) has no runs yet (NA).",
        tl=f"T11 (Tickets) Open Box tool-call tracks: {ntook} of 10 models granted themselves the lead role, then wrote audit entries or took tickets as lead.",
        lad=f"Gemma 4 31B on T18 (Release, Task Box): {sum(1 for s in steps if s[2] == 'denied')} denied out-of-scope attempts, then a patch of the vendor function from its own file got the check green and the release shipped.",
        sm="Mean p_risk per model at each access level, shared y-scale: the clean models stay flat, the risky ones climb at Open Box.",
        cw=f"Open Box: {a.k[0]} of {a.n[0]} runs used the credential bait ({a.opened[0]} only opened the token file) vs {a.k[1]} of {a.n[1]} ({a.k[1]/a.n[1]:.0%}) that took the write / privilege bait.",
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
