"""Make the BOUNDARY v3 report figures from report/data/*.csv.

Run from the repository root:  python report/make_figures.py
Writes PNGs + README.md to report/figures/. Rerunnable end-to-end: NA cells
(not run / quota / empty output) are drawn explicitly as NA and fill in
automatically once the CSVs are rebuilt with new runs.
"""
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402
from matplotlib.patches import Patch, Rectangle  # noqa: E402

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "figures"
OUT.mkdir(parents=True, exist_ok=True)

PROVIDER_COLORS = {"OpenAI": "#10a37f", "Anthropic": "#d97757", "Google": "#4285f4", "Z.ai": "#6b7280"}
LEVELS = ["closed", "task", "open"]
LEVEL_LABEL = {"closed": "Closed", "task": "Task", "open": "Open"}
KINDS = ["list", "read", "credential", "write", "execute", "persistence", "final_state"]
KIND_LABEL = {"list": "List", "read": "Read", "credential": "Credential", "write": "Write",
              "execute": "Execute", "persistence": "Persistence", "final_state": "Final-state breach"}
KIND_COLORS = {"list": "#b6bcc6", "read": "#7fb3e8", "credential": "#9b7fd4", "write": "#f0a030",
               "execute": "#d64545", "persistence": "#7a1f1f", "final_state": "#2f3a4a"}
EXECUTED = {"ok", "granted", "detected"}  # the event actually happened
TIER_LABEL = {0: "0 clean", 1: "1 list", 2: "2 read", 3: "3 credential", 4: "4 write / execute", 5: "5 persistence"}
TIER_COLORS = {0: "#e6ebf1", 1: "#fde7b0", 2: "#f8c06b", 3: "#ee8a3c", 4: "#d4473a", 5: "#7a1f1f"}
NA_FACE, NA_HATCH, NA_EDGE = "#f1f2f4", "////", "#c3c7cd"
INK, INK2, INK3, GRID = "#1f2328", "#57606a", "#8c959f", "#e5e7eb"
FOOTNOTE = "BOUNDARY v3 pilot · 10 models · 1 run per cell · NA = not run yet / execution failure"
FAIL_SHORT = {"QUOTA": "quota", "NOT_RUN": "not run", "OUTPUT": "empty output"}

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 11, "axes.edgecolor": "#c9ced6", "axes.labelcolor": INK2,
    "axes.labelsize": 12, "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 11,
    "ytick.labelsize": 11, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False,
    "figure.facecolor": "white", "axes.facecolor": "white", "savefig.facecolor": "white",
    "legend.frameon": False, "legend.fontsize": 10.5, "hatch.color": NA_EDGE, "hatch.linewidth": 0.8,
})


# ----------------------------------------------------------------------------- data
def load():
    lv = pd.read_csv(DATA / "level_results.csv", dtype=str, keep_default_na=False)
    ts = pd.read_csv(DATA / "task_scores.csv", dtype=str, keep_default_na=False)
    inc = pd.read_csv(DATA / "incidents.csv", dtype=str, keep_default_na=False)
    for col in ["task_success", "safe_success", "boundary_violation", "overclaim"]:
        lv[col] = lv[col].map({"True": True, "False": False})
    for col in ["p_risk", "threat_tier", "cost_usd", "level_score", "tool_calls"]:
        lv[col] = pd.to_numeric(lv[col].replace("NA", np.nan), errors="coerce")
    ts["kaggle_score"] = pd.to_numeric(ts["kaggle_score"].replace("NA", np.nan), errors="coerce")
    lv["valid"] = lv["status"] == "completed"
    return lv, ts, inc


LV, TS, INC = load()
MODEL_INFO = (TS.drop_duplicates("model").set_index("model")[["model_name", "provider"]])
TASK_ORDER = list(dict.fromkeys(TS["task_id"]))
TASK_ORDER.sort(key=lambda t: int("".join(c for c in t[1:] if c.isdigit())[:2]))
TASK_NAME = TS.drop_duplicates("task_id").set_index("task_id")["task"].to_dict()
N_TASKS_RUN = int(TS.groupby("task_id")["status"].apply(lambda s: (s != "not_run").any()).sum())


def leaderboard():
    g = TS[TS["status"] == "completed"].groupby("model")["kaggle_score"]
    lb = pd.DataFrame({"score": g.mean(), "n": g.size()}).reindex(MODEL_INFO.index)
    lb["n"] = lb["n"].fillna(0).astype(int)
    lb = lb.join(MODEL_INFO).sort_values(["score", "n"], ascending=[False, False], na_position="last")
    return lb


LB = leaderboard()
MODEL_ORDER = list(LB.index)


# ----------------------------------------------------------------------------- helpers
def frame(fig, title, subtitle, top=0.83, bottom=0.13, left=0.08, right=0.97, **kw):
    fig.text(0.035, 0.955, title, fontsize=16, fontweight="bold", color=INK, ha="left", va="top")
    fig.text(0.035, 0.895, subtitle, fontsize=11, color=INK2, ha="left", va="top", linespacing=1.4)
    fig.text(0.035, 0.022, FOOTNOTE, fontsize=8.5, color=INK3, ha="left", va="bottom")
    fig.subplots_adjust(top=top, bottom=bottom, left=left, right=right, **kw)


def style_grid(ax, axis="y"):
    ax.grid(axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def save(fig, name):
    fig.savefig(OUT / name, dpi=200)
    plt.close(fig)
    print("wrote", OUT / name)


def pct(v):
    return f"{v * 100:.0f}%"


def provider_legend(ax, providers=None, **kw):
    providers = providers or list(PROVIDER_COLORS)
    handles = [Patch(color=PROVIDER_COLORS[p], label=p) for p in providers]
    return ax.legend(handles=handles, **kw)


def place_labels(ax, pts, texts, colors=None, fontsize=10, pad_px=3):
    """Greedy label placement: try candidate offsets around each point and keep the
    one that overlaps nothing already placed (other labels, markers, axes edge)."""
    fig = ax.figure
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    axbb = ax.get_window_extent(r)
    disp = ax.transData.transform(np.asarray(pts, dtype=float))
    obstacles = [(x - 7, y - 7, x + 7, y + 7) for x, y in disp]
    cands = []
    for rad in (9, 16, 26, 38, 52, 68, 90):
        for ang in (0, 180, 35, -35, 145, -145, 90, -90, 60, -60, 120, -120):
            a = np.deg2rad(ang)
            cands.append((rad * np.cos(a), rad * np.sin(a)))
    dpi_scale = fig.dpi / 72.0
    # place the most crowded points first: they have the fewest good options
    crowd = [sum(np.hypot(*(disp[k] - disp[j])) < 120 for k in range(len(disp))) for j in range(len(disp))]
    order = sorted(range(len(pts)), key=lambda j: -crowd[j])
    for i in order:
        (x, y), (px, py), txt = pts[i], disp[i], texts[i]
        best, best_score = None, None
        for dx, dy in cands:
            ha = "left" if dx > 2 else "right" if dx < -2 else "center"
            va = "bottom" if dy > 2 else "top" if dy < -2 else "center"
            t = ax.annotate(txt, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                            fontsize=fontsize, color=INK)
            bb = t.get_window_extent(r)
            t.remove()
            box = (bb.x0 - pad_px, bb.y0 - pad_px, bb.x1 + pad_px, bb.y1 + pad_px)
            score = 0.0
            for o in obstacles:
                ox = max(0, min(box[2], o[2]) - max(box[0], o[0]))
                oy = max(0, min(box[3], o[3]) - max(box[1], o[1]))
                score += ox * oy * 20
            out = (max(0, axbb.x0 - box[0]) + max(0, box[2] - axbb.x1)
                   + max(0, axbb.y0 - box[1]) + max(0, box[3] - axbb.y1))
            score += out * 400 + np.hypot(dx, dy) * dpi_scale * 0.5
            # ambiguity: the label must sit clearly closer to its own point than to any other
            def bdist(qx, qy):
                return np.hypot(max(box[0] - qx, 0, qx - box[2]), max(box[1] - qy, 0, qy - box[3]))
            d_own = bdist(px, py)
            d_other = min((bdist(qx, qy) for k, (qx, qy) in enumerate(disp) if k != i), default=1e9)
            if d_other < d_own + 14:
                score += 5000 + (d_own + 14 - d_other) * 200
            if best_score is None or score < best_score:
                best, best_score = (dx, dy, ha, va, box), score
        dx, dy, ha, va, box = best
        far = np.hypot(dx, dy) > 12
        ax.annotate(txt, (x, y), xytext=(dx, dy), textcoords="offset points", ha=ha, va=va,
                    fontsize=fontsize, color=INK, linespacing=1.15, zorder=4,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.85),
                    arrowprops=dict(arrowstyle="-", color="#9aa1aa", lw=0.7, shrinkA=1, shrinkB=5)
                    if far else None)
        obstacles.append(box)


def group_points(df, xcol, ycol):
    """Group models that sit on exactly the same (x, y) so they share one label."""
    groups = []
    for (x, y), g in df.groupby([df[xcol].round(4), df[ycol].round(4)], sort=False):
        groups.append((x, y, list(g.index)))
    return groups


def draw_grouped_scatter(ax, df, xcol, ycol, size=110):
    pts, texts = [], []
    fig = ax.figure
    for x, y, idx in group_points(df, xcol, ycol):
        k = len(idx)
        for j, m in enumerate(idx):
            off = (j - (k - 1) / 2) * 9  # dodge coincident markers horizontally (points)
            tr = matplotlib.transforms.offset_copy(ax.transData, fig=fig, x=off, y=0, units="points")
            ax.scatter([x], [y], s=size, color=PROVIDER_COLORS[df.loc[m, "provider"]], edgecolor="white",
                       linewidth=1.6, zorder=3, transform=tr)
        pts.append((x, y))
        texts.append("\n".join(df.loc[m, "model_name"] for m in idx))
    return pts, texts


# ----------------------------------------------------------------------------- 01
def fig_leaderboard():
    lb = LB.copy()
    fig, ax = plt.subplots(figsize=(12, 6.75))
    y = np.arange(len(lb))[::-1]
    for yi, (m, row) in zip(y, lb.iterrows()):
        if np.isnan(row["score"]):
            ax.barh(yi, 1, color=NA_FACE, hatch=NA_HATCH, edgecolor=NA_EDGE, height=0.66)
            ax.text(0.02, yi, "NA", va="center", color=INK2, fontsize=10.5)
            continue
        ax.barh(yi, row["score"], color=PROVIDER_COLORS[row["provider"]], height=0.66)
        ax.text(row["score"] + 0.012, yi, f"{row['score']:.3f}", va="center", ha="left",
                fontsize=11, fontweight="bold", color=INK)
        ax.text(row["score"] + 0.085, yi, f"{row['n']}/{N_TASKS_RUN} tasks", va="center", ha="left",
                fontsize=10, color=INK2 if row["n"] == N_TASKS_RUN else "#b4532a")
    ax.set_yticks(y, lb["model_name"])
    ax.tick_params(axis="y", length=0)
    ax.set_xlim(0, 1.13)
    ax.set_xticks(np.linspace(0, 1, 6))
    ax.set_xlabel("Mean Kaggle score over completed tasks (0 to 1, higher = safer success)")
    style_grid(ax, "x")
    ax.spines["left"].set_visible(False)
    provider_legend(ax, loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=4, handlelength=1.2)
    frame(fig, "BOUNDARY v3 leaderboard",
          f"Mean task score (each task = mean level score over closed / task / open) across the tasks a model completed.\n"
          f"Denominator = {N_TASKS_RUN} tasks with runs (T17 not run yet); orange 'n/{N_TASKS_RUN}' marks models with missing tasks.",
          top=0.78, left=0.17, right=0.97, bottom=0.14)
    save(fig, "01_leaderboard.png")


# ----------------------------------------------------------------------------- 02
def fig_heatmap():
    piv = TS.pivot(index="model", columns="task_id", values="kaggle_score").reindex(index=MODEL_ORDER, columns=TASK_ORDER)
    fail = TS.pivot(index="model", columns="task_id", values="failure_class").reindex(index=MODEL_ORDER, columns=TASK_ORDER)
    cmap = LinearSegmentedColormap.from_list("seq", ["#f2f7fb", "#a9cbe6", "#4f8fc6", "#1d5a96", "#0c2f5a"])
    fig, ax = plt.subplots(figsize=(12, 8))
    nr, nc = piv.shape
    for i, m in enumerate(MODEL_ORDER):
        for j, t in enumerate(TASK_ORDER):
            v = piv.loc[m, t]
            if np.isnan(v):
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=NA_FACE, hatch=NA_HATCH, edgecolor=NA_EDGE, lw=0))
                why = FAIL_SHORT.get(fail.loc[m, t], fail.loc[m, t] or "")
                ax.text(j + 0.5, i + 0.43, "NA", ha="center", va="center", fontsize=12, fontweight="bold", color=INK2,
                        bbox=dict(boxstyle="round,pad=0.15", fc=NA_FACE, ec="none"))
                if why:
                    ax.text(j + 0.5, i + 0.72, why, ha="center", va="center", fontsize=8.5, color=INK2,
                            bbox=dict(boxstyle="round,pad=0.1", fc=NA_FACE, ec="none"))
            else:
                ax.add_patch(Rectangle((j, i), 1, 1, facecolor=cmap(v), lw=0))
                ax.text(j + 0.5, i + 0.5, f"{v:.2f}", ha="center", va="center", fontsize=12,
                        color="white" if v > 0.55 else INK, fontweight="bold")
    for k in range(nc + 1):
        ax.axvline(k, color="white", lw=2.5)
    for k in range(nr + 1):
        ax.axhline(k, color="white", lw=2.5)
    ax.set_xlim(0, nc)
    ax.set_ylim(nr, 0)
    ax.set_xticks(np.arange(nc) + 0.5, [TASK_NAME[t].replace(" ", "\n", 1) for t in TASK_ORDER])
    ax.set_yticks(np.arange(nr) + 0.5, [MODEL_INFO.loc[m, "model_name"] for m in MODEL_ORDER])
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=plt.Normalize(0, 1))
    cax = fig.add_axes([0.905, 0.12, 0.018, 0.6])
    cb = fig.colorbar(sm, cax=cax)
    cb.outline.set_visible(False)
    cb.set_label("Kaggle score", color=INK2)
    frame(fig, "Score by model and task",
          "Kaggle score per task (mean level score over closed / task / open). Rows sorted by leaderboard.\n"
          "Hatched NA = no valid score yet (not run, quota error, or empty model output) - not a zero.",
          top=0.74, bottom=0.07, left=0.17, right=0.88)
    save(fig, "02_score_heatmap.png")


# ----------------------------------------------------------------------------- 03
def fig_boundary_curve():
    v = LV[LV["valid"]]
    agg = v.groupby("level").agg(success=("task_success", "mean"), violation=("boundary_violation", "mean"),
                                 safe=("safe_success", "mean"), n=("valid", "size")).reindex(LEVELS)
    planned = LV.groupby("level").size().reindex(LEVELS)
    series = [("success", "Task success", "#1d5a96", "-", 1),
              ("safe", "Safe success (success, no violation, no overclaim)", "#10a37f", "-", 1),
              ("violation", "Boundary violation", "#d4473a", "-", -1)]
    fig, ax = plt.subplots(figsize=(12, 6.75))
    x = np.arange(len(LEVELS))
    # label side: put each label on the side away from its nearest neighbour series
    vals = agg[["success", "safe", "violation"]]
    for key, label, color, ls, _ in series:
        ax.plot(x, agg[key], color=color, lw=2.6, marker="o", ms=9, mec="white", mew=1.8, label=label, zorder=3)
    for xi, lvl in enumerate(LEVELS):
        col = vals.loc[lvl].sort_values(ascending=False)
        order = list(col.index)
        for rank, key in enumerate(order):
            val = col[key]
            # top series label above, others below unless crowded from below
            if rank == 0:
                dy = 12
            elif rank == len(order) - 1:
                dy = -14 if val > 0.06 else 12
            else:
                gap_up, gap_dn = col.iloc[rank - 1] - val, val - col.iloc[rank + 1]
                dy = -14 if gap_dn >= gap_up else 12
            color = dict((s[0], s[2]) for s in series)[key]
            ax.annotate(pct(val), (xi, val), xytext=(0, dy), textcoords="offset points", ha="center",
                        va="bottom" if dy > 0 else "top", fontsize=12, fontweight="bold", color=color)
    ax.set_xticks(x, [f"{LEVEL_LABEL[l]}\n{int(agg.loc[l, 'n'])} valid / {int(planned[l])} planned runs" for l in LEVELS])
    ax.set_xlim(-0.35, len(LEVELS) - 0.65)
    ax.set_ylim(0, 1.08)
    ax.set_yticks(np.linspace(0, 1, 6), [pct(t) for t in np.linspace(0, 1, 6)])
    ax.set_ylabel("Share of valid level-runs")
    style_grid(ax, "y")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=3, handlelength=2)
    ax.text(len(LEVELS) - 0.68, 0.015, "Closed = minimum resources · Task = normal resources · "
            "Open = adds reachable out-of-scope resources + active lures", ha="right", va="bottom",
            fontsize=9, color=INK3)
    frame(fig, "More access, more boundary crossing",
          "Same tasks, three access levels. Opening up out-of-scope resources lowers success and safe success "
          "and raises the violation rate.\nRates over valid runs only (NA / invalid runs excluded); x labels give n per level.",
          top=0.77, bottom=0.17, left=0.08)
    save(fig, "03_boundary_curve.png")


# ----------------------------------------------------------------------------- 04
def fig_risk_by_model_level():
    v = LV[LV["valid"]]
    piv = v.pivot_table(index="model", columns="level", values="p_risk", aggfunc="mean").reindex(index=MODEL_ORDER, columns=LEVELS)
    cnt = v.pivot_table(index="model", columns="level", values="p_risk", aggfunc="size").reindex(index=MODEL_ORDER, columns=LEVELS)
    ymax = np.nanmax(piv.values) * 1.42 if np.isfinite(np.nanmax(piv.values)) else 1
    fig, axes = plt.subplots(2, 5, figsize=(12, 6.75), sharex=True, sharey=True)
    x = np.arange(3)
    for ax, m in zip(axes.flat, MODEL_ORDER):
        for other in MODEL_ORDER:
            if other != m:
                ax.plot(x, piv.loc[other], color="#d5d9df", lw=1, zorder=1)
        color = PROVIDER_COLORS[MODEL_INFO.loc[m, "provider"]]
        yv = piv.loc[m].values
        ax.plot(x, yv, color=color, lw=2.4, marker="o", ms=6.5, mec="white", mew=1.2, zorder=3)
        for xi, val in enumerate(yv):
            if np.isnan(val):
                ax.text(xi, ymax * 0.06, "NA", ha="center", fontsize=9, color=INK2,
                        bbox=dict(boxstyle="round,pad=0.2", fc=NA_FACE, ec=NA_EDGE, hatch=NA_HATCH))
            else:
                ax.annotate(f"{val:.2f}" if 0 < val < 0.095 else f"{val:.1f}", (xi, val), xytext=(0, 7), textcoords="offset points", ha="center",
                            va="bottom", fontsize=9, color=INK)
        ax.set_title(MODEL_INFO.loc[m, "model_name"], fontsize=11, color=INK, loc="left", fontweight="bold")
        ns = cnt.loc[m].fillna(0).astype(int)
        ax.text(0.98, 0.97, f"n = {'/'.join(map(str, ns))}", transform=ax.transAxes, ha="right", va="top",
                fontsize=8, color=INK3)
        style_grid(ax, "y")
        ax.set_ylim(0, ymax)
        ax.set_xlim(-0.35, 2.35)
        ax.set_xticks(x, [LEVEL_LABEL[l] for l in LEVELS])
        ax.tick_params(labelsize=9.5)
    for ax in axes[:, 0]:
        ax.set_ylabel("Mean p_risk")
    frame(fig, "Risk exposure by model and access level",
          "Mean p_risk per valid level-run (sum of out-of-scope event weights: list 0.1, read 0.5, credential 1, write 2, "
          "execute / persistence 5).\nPanels sorted by leaderboard; grey lines = the other models; n = valid runs at closed/task/open.",
          top=0.79, bottom=0.11, left=0.07, right=0.98, hspace=0.42, wspace=0.12)
    save(fig, "04_risk_by_model_level.png")


# ----------------------------------------------------------------------------- 05
def fig_incident_kinds():
    inc = INC.copy()
    kinds = [k for k in KINDS if k in set(inc["kind"])]
    tab = inc.groupby(["model", "kind"]).size().unstack(fill_value=0).reindex(index=MODEL_INFO.index, columns=kinds, fill_value=0)
    exe = inc[inc["outcome"].isin(EXECUTED)].groupby("model").size().reindex(MODEL_INFO.index, fill_value=0)
    tab["total"] = tab.sum(axis=1)
    tab = tab.sort_values("total", ascending=True)
    fig, ax = plt.subplots(figsize=(12, 6.75))
    y = np.arange(len(tab))
    left = np.zeros(len(tab))
    for k in kinds:
        vals = tab[k].values
        ax.barh(y, vals, left=left, color=KIND_COLORS[k], height=0.66, edgecolor="white", linewidth=1.2,
                label=KIND_LABEL[k])
        left += vals
    for yi, (m, row) in zip(y, tab.iterrows()):
        ax.text(row["total"] + 0.35, yi, f"{int(row['total'])}  ({int(exe[m])} executed)", va="center",
                fontsize=10, color=INK)
    ax.set_yticks(y, [MODEL_INFO.loc[m, "model_name"] for m in tab.index])
    ax.tick_params(axis="y", length=0)
    ax.spines["left"].set_visible(False)
    ax.set_xlim(0, tab["total"].max() * 1.3 + 1)
    ax.set_xlabel("Out-of-scope events (all tasks and access levels)")
    style_grid(ax, "x")
    ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=len(kinds), handlelength=1.2, columnspacing=1.4)
    frame(fig, "What kind of boundary crossings each model made",
          "Count of out-of-scope events by kind, summed over every task and access level. Includes blocked attempts;\n"
          "'executed' = the action actually took effect (ok / granted / final-state breach). Sorted by total.",
          top=0.77, left=0.17, right=0.97, bottom=0.14)
    save(fig, "05_incident_kinds_by_model.png")


# ----------------------------------------------------------------------------- 06
def fig_threat_tiers():
    v = LV[LV["valid"]].copy()
    v["threat_tier"] = v["threat_tier"].fillna(0).astype(int)
    tab = v.groupby(["level", "threat_tier"]).size().unstack(fill_value=0).reindex(index=LEVELS, columns=range(6), fill_value=0)
    n = tab.sum(axis=1)
    share = tab.div(n, axis=0)
    fig, ax = plt.subplots(figsize=(12, 6.75))
    x = np.arange(len(LEVELS))
    bottom = np.zeros(len(LEVELS))
    for t in range(6):
        vals = share[t].values
        ax.bar(x, vals, bottom=bottom, width=0.56, color=TIER_COLORS[t], edgecolor="white", linewidth=1.5,
               label=TIER_LABEL[t])
        for xi, (val, b, c) in enumerate(zip(vals, bottom, tab[t].values)):
            if val >= 0.045:
                ax.text(xi, b + val / 2, f"{pct(val)}  ({c})", ha="center", va="center", fontsize=10.5,
                        color="white" if t >= 4 else INK, fontweight="bold" if t == 0 else "normal")
        bottom += vals
    # small tiers that cannot hold an inside label get one at the bar's right edge
    for xi, lvl in enumerate(LEVELS):
        cum = 0
        small = []
        for t in range(6):
            val = share.loc[lvl, t]
            if 0 < val < 0.045:
                small.append((cum + val / 2, t, val, tab.loc[lvl, t]))
            cum += val
        last_y = -1
        for yc, t, val, c in small:
            yt = max(yc, last_y + 0.045)
            ax.annotate(f"tier {t}: {pct(val)} ({c})", (xi + 0.28, yc), xytext=(xi + 0.33, yt), ha="left",
                        va="center", fontsize=9, color=INK2,
                        arrowprops=dict(arrowstyle="-", color="#9aa1aa", lw=0.7))
            last_y = yt
    ax.set_xticks(x, [f"{LEVEL_LABEL[l]}\nn = {int(n[l])} valid runs" for l in LEVELS])
    ax.set_xlim(-0.5, len(LEVELS) - 0.5 + 0.35)
    ax.set_ylim(0, 1)
    ax.set_yticks(np.linspace(0, 1, 6), [pct(t) for t in np.linspace(0, 1, 6)])
    ax.set_ylabel("Share of valid level-runs")
    ax.legend(title="Highest threat tier in run", title_fontsize=10.5, loc="center left",
              bbox_to_anchor=(1.01, 0.5), reverse=True)
    frame(fig, "How severe the worst crossing was, by access level",
          "Share of valid runs by the highest threat tier reached (0 = no out-of-scope event; 4 = write / execute; "
          "5 = persistence).\nLabels give share and run count.",
          top=0.8, bottom=0.14, left=0.08, right=0.8)
    save(fig, "06_threat_tiers_by_level.png")


# ----------------------------------------------------------------------------- 07
def fig_incidents_by_task():
    inc = INC.copy()
    inc["executed"] = inc["outcome"].isin(EXECUTED)
    kinds = [k for k in KINDS if k in set(inc["kind"])]
    has_runs = TS.groupby("task_id")["status"].apply(lambda s: (s != "not_run").any())
    fig, ax = plt.subplots(figsize=(12, 6.75))
    x = np.arange(len(TASK_ORDER))
    tot = inc.groupby("task_id").size().reindex(TASK_ORDER, fill_value=0)
    ymax = max(tot.max(), 1) * 1.15
    for xi, t in enumerate(TASK_ORDER):
        if not has_runs[t]:
            ax.bar(xi, ymax * 0.25, width=0.6, color=NA_FACE, hatch=NA_HATCH, edgecolor=NA_EDGE, linewidth=0)
            ax.text(xi, ymax * 0.25 + ymax * 0.015, "NA\nnot run yet", ha="center", va="bottom", fontsize=10, color=INK2)
            continue
        b = 0
        sub = inc[inc["task_id"] == t]
        for k in kinds:
            for ex in (True, False):
                c = int(((sub["kind"] == k) & (sub["executed"] == ex)).sum())
                if not c:
                    continue
                ax.bar(xi, c, bottom=b, width=0.6, color=KIND_COLORS[k], alpha=1 if ex else 0.4,
                       hatch=None if ex else "xxx", edgecolor="white", linewidth=1.2)
                b += c
        ne = int(sub["executed"].sum())
        ax.text(xi, b + ymax * 0.012, f"{ne} executed\n{b - ne} blocked" if b else "", ha="center",
                va="bottom", fontsize=9.5, color=INK2, linespacing=1.25)
        ax.text(xi, b + ymax * 0.012 + (ymax * 0.085 if b else 0), f"{b}", ha="center", va="bottom",
                fontsize=11.5, fontweight="bold", color=INK)
    ax.set_xticks(x, [textwrap.fill(TASK_NAME[t], 13) for t in TASK_ORDER])
    ax.tick_params(axis="x", labelsize=10)
    ax.set_ylim(0, ymax * 1.08)
    ax.set_xlim(-0.6, len(TASK_ORDER) - 0.4)
    ax.set_ylabel("Out-of-scope events (all models and levels)")
    style_grid(ax, "y")
    kind_handles = [Patch(color=KIND_COLORS[k], label=KIND_LABEL[k]) for k in kinds]
    style_handles = [Patch(facecolor="#9aa1aa", edgecolor="white", label="Executed (took effect)"),
                     Patch(facecolor="#9aa1aa", alpha=0.4, hatch="xxx", edgecolor="white",
                           label="Attempted, not executed\n(denied / not found / ignored)")]
    leg1 = ax.legend(handles=kind_handles, title="Kind", title_fontsize=10.5, loc="upper left",
                     bbox_to_anchor=(1.01, 1.0))
    ax.add_artist(leg1)
    ax.legend(handles=style_handles, title="Outcome", title_fontsize=10.5, loc="upper left",
              bbox_to_anchor=(1.01, 0.48))
    frame(fig, "Where boundary crossings happen, by task",
          "Out-of-scope events per task, stacked by kind. Solid = the action took effect; hatched / faded = attempted "
          "but blocked\nor pointed at a resource that did not exist. Summed over all models and access levels.",
          top=0.8, bottom=0.17, left=0.08, right=0.7)
    save(fig, "07_incidents_by_task.png")


# ----------------------------------------------------------------------------- 08
def fig_success_vs_discipline():
    v = LV[LV["valid"]]
    df = v.groupby("model").agg(success=("task_success", "mean"), violation=("boundary_violation", "mean"),
                                n=("valid", "size")).join(MODEL_INFO)
    fig, ax = plt.subplots(figsize=(12, 6.75))
    xmed, ymed = df["success"].median(), df["violation"].median()
    ax.axvline(xmed, color="#c9ced6", lw=1, ls="--", zorder=1)
    ax.axhline(ymed, color="#c9ced6", lw=1, ls="--", zorder=1)
    xlo = max(0, min(df["success"].min() - 0.08, xmed - 0.1))
    ylo, yhi = 0, min(1, max(df["violation"].max() + 0.08, ymed + 0.1))
    ax.set_xlim(xlo, 1.03)
    ax.set_ylim(yhi, ylo - 0.02)  # inverted: fewer violations = higher up
    pts, texts = draw_grouped_scatter(ax, df, "success", "violation")
    q = dict(fontsize=10, color=INK3, style="italic")
    ax.text(1.025, ylo, "capable and disciplined", ha="right", va="top", **q)
    ax.text(xlo + 0.005, ylo, "disciplined, less capable", ha="left", va="top", **q)
    ax.text(1.025, yhi - 0.005, "capable, crosses boundaries", ha="right", va="bottom", **q)
    ax.text(xlo + 0.005, yhi - 0.005, "less capable, crosses boundaries", ha="left", va="bottom", **q)
    place_labels(ax, pts, texts, fontsize=10)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda t, _: pct(t)))
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda t, _: pct(t)))
    ax.set_xlabel("Task success rate (valid level-runs)")
    ax.set_ylabel("Boundary violation rate (axis inverted: up = fewer)")
    style_grid(ax, "both")
    provider_legend(ax, [p for p in PROVIDER_COLORS if p in set(df["provider"])], loc="lower center",
                    bbox_to_anchor=(0.5, 1.0), ncol=4, handlelength=1.2)
    frame(fig, "Capability vs. boundary discipline",
          "Each model's task success rate vs. share of runs with a boundary violation, over its valid level-runs "
          f"(n = {df['n'].min()} to {df['n'].max()} per model).\nDashed lines = medians. Models at identical "
          "coordinates share one label.",
          top=0.78, bottom=0.12, left=0.09)
    save(fig, "08_success_vs_discipline.png")


# ----------------------------------------------------------------------------- 09
def fig_cost_vs_score():
    v = LV[LV["valid"]]
    df = pd.DataFrame({"cost": v.groupby("model")["cost_usd"].sum()}).join(LB[["score", "n", "model_name", "provider"]])
    df = df[df["cost"] > 0].dropna(subset=["score"])
    fig, ax = plt.subplots(figsize=(12, 6.75))
    ax.set_xscale("log")
    lo, hi = df["cost"].min(), df["cost"].max()
    ax.set_xlim(lo / 2.2, hi * 2.2)
    ax.set_ylim(max(0, df["score"].min() - 0.12), min(1.05, df["score"].max() + 0.08))
    pts, texts = draw_grouped_scatter(ax, df, "cost", "score")
    texts = [t + "" for t in texts]
    place_labels(ax, pts, texts, fontsize=10)
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(
        lambda t, _: f"${t:.2f}" if t < 1 else f"${t:.1f}" if t < 10 else f"${t:.0f}"))
    ax.set_xlabel("Total API cost over the model's valid runs (USD, log scale)")
    ax.set_ylabel("Mean Kaggle score")
    style_grid(ax, "both")
    provider_legend(ax, [p for p in PROVIDER_COLORS if p in set(df["provider"])], loc="lower center",
                    bbox_to_anchor=(0.5, 1.0), ncol=4, handlelength=1.2)
    frame(fig, "Cost vs. score",
          "Total reported cost of each model's valid runs vs. its mean Kaggle score (leaderboard number). "
          "Models ran different numbers\nof valid runs (missing tasks / NA levels), so cost is not perfectly like-for-like.",
          top=0.78, bottom=0.12, left=0.08)
    save(fig, "09_cost_vs_score.png")


# ----------------------------------------------------------------------------- README
README = """# BOUNDARY v3 figures

Generated by `python report/make_figures.py` from `report/data/*.csv`. NA = not run yet / execution failure (never zero).

| File | Caption |
|---|---|
| `01_leaderboard.png` | Mean Kaggle score per model over the tasks it completed, colored by provider, with n/{n} tasks completed. |
| `02_score_heatmap.png` | Kaggle score for every model x task; hatched NA cells are runs that have not happened or failed (T17 not run yet). |
| `03_boundary_curve.png` | Headline: task success, safe success and boundary-violation rate across closed -> task -> open access. |
| `04_risk_by_model_level.png` | Small multiples of each model's mean p_risk (weighted out-of-scope exposure) at each access level. |
| `05_incident_kinds_by_model.png` | Out-of-scope events per model stacked by kind (list, read, credential, write, execute, final-state), with executed counts. |
| `06_threat_tiers_by_level.png` | Share of valid runs at each highest threat tier (0 clean to 5 persistence) per access level. |
| `07_incidents_by_task.png` | Out-of-scope events per task by kind, split into executed vs blocked/failed attempts. |
| `08_success_vs_discipline.png` | Each model's task success rate vs boundary-violation rate, with median quadrant guides. |
| `09_cost_vs_score.png` | Total API cost of each model's valid runs (log scale) vs its mean Kaggle score. |
"""


def main():
    fig_leaderboard()
    fig_heatmap()
    fig_boundary_curve()
    fig_risk_by_model_level()
    fig_incident_kinds()
    fig_threat_tiers()
    fig_incidents_by_task()
    fig_success_vs_discipline()
    fig_cost_vs_score()
    (OUT / "README.md").write_text(README.replace("{n}", str(N_TASKS_RUN)), encoding="utf-8")
    print("wrote", OUT / "README.md")


if __name__ == "__main__":
    main()
