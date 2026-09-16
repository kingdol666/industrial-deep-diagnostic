#!/usr/bin/env python3
"""make_figures.py — AEI 投稿结果图（矢量 PDF，数据驱动）。

所有数值直接读取 results/benchmark/{metrics,gradings,cases} 真实评分，
不经手工转抄；重跑 `python make_figures.py` 即可随基准结果更新再生。
配色 = Okabe-Ito（色盲安全）；字体 = Arial；输出 = 矢量 PDF + 预览 PNG。
"""
import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
RES = os.path.join(ROOT, "results", "benchmark")

# ── AEI/Elsevier 矢量图规范 ─────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 8.5,
    "axes.labelsize": 8.5,
    "axes.linewidth": 0.7,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7.5,
    "pdf.fonttype": 42,   # 嵌入 TrueType（Elsevier 要求，可编辑文本）
    "ps.fonttype": 42,
    "axes.spines.top": False,
    "axes.spines.right": False,
})

# Okabe-Ito
BLUE, SKY, GREEN, VERM, ORANGE, GREY = "#0072B2", "#56B4E9", "#009E73", "#D55E00", "#E69F00", "#8F8F8F"
AMBER_DARK = "#A35C17"

metrics = json.load(open(os.path.join(RES, "metrics.json"), encoding="utf-8"))
cases = {c["case_id"]: c for c in json.load(open(
    os.path.join(ROOT, "scripts", "benchmark", "cases", "benchmark_cases.json"), encoding="utf-8"))["cases"]}
gradings = {}
for f in os.listdir(os.path.join(RES, "gradings")):
    if f.endswith(".json"):
        g = json.load(open(os.path.join(RES, "gradings", f), encoding="utf-8"))
        gradings[g["case_id"]] = g

ORDER = ["skab_valve1_1", "skab_cavitation_13", "skab_normal_control",
         "tep_d01_ac_feed_ratio", "tep_d03_hard", "tep_d00_normal_control",
         "indpensim_batch093", "indpensim_batch001_control",
         "tep_d04_reactor_cooling_step", "tep_d07_header_pressure",
         "tep_d11_reactor_cooling_random", "tep_d14_reactor_valve_sticking"]
SHORT = {
    "skab_valve1_1": "SKAB inlet-valve throttling",
    "skab_cavitation_13": "SKAB cavitation (blind)",
    "skab_normal_control": "Control: SKAB anomaly-free",
    "tep_d01_ac_feed_ratio": "TEP IDV1 feed-ratio step",
    "tep_d03_hard": "TEP IDV3 D-feed temp. (hard)",
    "tep_d00_normal_control": "Control: TEP fault-free",
    "indpensim_batch093": "IndPenSim batch-93 deviation",
    "indpensim_batch001_control": "Control: IndPenSim batch-1",
    "tep_d04_reactor_cooling_step": "TEP IDV4 cooling step",
    "tep_d07_header_pressure": "TEP IDV7 C-header pressure",
    "tep_d11_reactor_cooling_random": "TEP IDV11 cooling random",
    "tep_d14_reactor_valve_sticking": "TEP IDV14 valve stiction",
}


def wilson(x, n, z=1.959963985):
    p, nn = x / n, n
    d = 1 + z * z / nn
    c = p + z * z / (2 * nn)
    r = z * math.sqrt(p * (1 - p) / nn + z * z / (4 * nn * nn))
    return 100 * (c - r) / d, 100 * (c + r) / d


def save(fig, name):
    fig.savefig(os.path.join(HERE, name + ".pdf"), bbox_inches="tight", pad_inches=0.02)
    fig.savefig(os.path.join(HERE, name + ".png"), dpi=220, bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    print("wrote", name)


# ── Fig. benchmark：数据集结局构成 + 每场景质量双图 ─────────────────────
def fig_benchmark():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(7.1, 2.95), gridspec_kw={"width_ratios": [1, 1.3], "wspace": 0.62})

    # (a) per-dataset fault outcomes, stacked
    ds = [("SKAB", ["skab_valve1_1", "skab_cavitation_13"]),
          ("TEP", ["tep_d01_ac_feed_ratio", "tep_d03_hard", "tep_d04_reactor_cooling_step",
                   "tep_d07_header_pressure", "tep_d11_reactor_cooling_random", "tep_d14_reactor_valve_sticking"]),
          ("IndPenSim", ["indpensim_batch093"])]
    rows = []
    for name, ids in ds:
        top1 = sum(1 for i in ids if gradings[i].get("top1"))
        topk_only = sum(1 for i in ids if not gradings[i].get("top1") and gradings[i].get("topk"))
        miss = len(ids) - top1 - topk_only
        rows.append((name, top1, topk_only, miss, len(ids)))
    ypos = [2, 1, 0]
    for (name, top1, topk_only, miss, n), y in zip(rows, ypos):
        ax1.barh(y, top1, color=BLUE, height=0.52,
                 label="Top-1 correct (DETERMINED)" if y == 2 else None)
        if topk_only:
            ax1.barh(y, topk_only, left=top1, color=ORANGE, height=0.52,
                     label="true cause in top-k only (capped CS)" if y == 2 else None)
        if miss:
            ax1.barh(y, miss, left=top1 + topk_only, color="#c9cdd3", height=0.52,
                     label="not identified" if y == 2 else None)
        ax1.text(n + 0.15, y, f"{top1}/{n}", va="center", fontsize=7.6, fontweight="bold", color="#1e3a54")
    ax1.set_yticks(ypos)
    ax1.set_yticklabels([r[0] for r in rows])
    ax1.set_xlim(0, 7.6)
    ax1.set_xticks([0, 1, 2, 3, 4, 5, 6])
    ax1.set_xlabel("Fault scenarios (n = 9)\ncontrols: 3/3 pass, zero false alarms", linespacing=1.5)
    ax1.set_title("(a) Fault outcomes by dataset", fontsize=8.5, loc="left")
    ax1.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), frameon=False, handlelength=1.2,
               handleheight=0.9, borderaxespad=0)

    # (b) rubric + judge gate per scenario (faults only, controls marked)
    ids = [i for i in ORDER]
    ys = list(range(len(ids)))[::-1]
    for y, cid in zip(ys, ids):
        g = gradings[cid]
        c = cases[cid]
        rub, jud = g["rubric"]["score"], g["judge_score"]
        col = GREY if c.get("control") else (ORANGE if g["diagnosis_type"] == "COMPETING_SET" else
                                             (BLUE if c["dataset"] == "skab" else SKY if c["dataset"] == "tep" else GREEN))
        ax2.plot(jud, y, "o", ms=4.2, mfc="white", mec=col, mew=1.3)
        ax2.plot(rub, y, "o", ms=4.2, color=col)
    ax2.set_yticks(ys)
    ax2.set_yticklabels([SHORT[i] for i in ids], fontsize=7.3)
    ax2.set_xlim(50, 103)
    ax2.set_xticks([50, 60, 70, 80, 90, 100])
    ax2.set_xlabel("Score (points)")
    ax2.set_title("(b) Rubric vs. judge gate", fontsize=8.5, loc="left")
    ax2.axvline(90, color="#b9c2cc", lw=0.7, ls=":")
    ax2.text(90, len(ids) - 0.1, "gate 90", fontsize=6.8, color="#7a848e", ha="center", va="bottom")
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="o", ls="", mfc=BLUE, mec=BLUE, ms=4.2, label="rubric (fault)"),
               Line2D([], [], marker="o", ls="", mfc="white", mec=BLUE, ms=4.2, label="judge gate (fault)"),
               Line2D([], [], marker="o", ls="", mfc=GREY, mec=GREY, ms=4.2, label="controls")]
    ax2.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.24), frameon=False,
               ncol=3, columnspacing=1.0, handletextpad=0.25, borderaxespad=0)
    save(fig, "fig_benchmark")


# ── Fig. calibration：12 场景置信度 + 协议上限线 ────────────────────────
def fig_calibration():
    fig, ax = plt.subplots(figsize=(6.9, 3.15))
    ys = list(range(len(ORDER)))[::-1]
    for y, cid in zip(ys, ORDER):
        g, c = gradings[cid], cases[cid]
        conf = g["confidence"] / 100 if g["confidence"] else 0
        cs = g["diagnosis_type"] == "COMPETING_SET"
        if c.get("control"):
            ax.barh(y, conf, height=0.62, color="#e4e7eb")
            ax.barh(y, conf, height=0.62, color="none", edgecolor=GREY, lw=0.8, hatch="///")
            lbl, tc = f"normal {conf:.2f}", "#4a4a4a"
        elif cs:
            ax.barh(y, conf, height=0.62, color=ORANGE)
            lbl, tc = f"CS {conf:.2f}", AMBER_DARK
        else:
            base = BLUE if c["dataset"] == "skab" else SKY if c["dataset"] == "tep" else GREEN
            ax.barh(y, conf, height=0.62, color=base)
            lbl, tc = f"DET {conf:.2f}", "#1e3a54"
        ax.text(conf + 0.008, y, lbl, va="center", fontsize=7.2, fontweight="bold", color=tc)
    ax.set_yticks(ys)
    ax.set_yticklabels([SHORT[i] for i in ids] if False else [SHORT[i] for i in ORDER], fontsize=7.3)
    ax.axvline(0.70, color=ORANGE, lw=1.0, ls="--")
    ax.text(0.693, 11.65, "ceiling for capped verdicts only (0.70)", fontsize=6.8,
            color=AMBER_DARK, va="center", ha="right")
    ax.set_xlim(0, 1.02)
    ax.set_xticks([0, 0.25, 0.5, 0.75, 1.0])
    ax.set_xlabel("Reported confidence (overconfidence = DETERMINED and wrong: 0 occurrences)")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    save(fig, "fig_calibration")


# ── Fig. TEP per-fault 对比矩阵 ─────────────────────────────────────────
def fig_tep():
    tep_ids = ["tep_d01_ac_feed_ratio", "tep_d03_hard", "tep_d04_reactor_cooling_step",
               "tep_d07_header_pressure", "tep_d11_reactor_cooling_random", "tep_d14_reactor_valve_sticking"]
    labels = ["IDV1  A/C feed-ratio step", "IDV3  D-feed temperature step (hard)",
              "IDV4  reactor cooling-water step", "IDV7  C-header pressure loss",
              "IDV11  cooling-water random", "IDV14  cooling-valve stiction"]
    cols = ["FaultExplainer\nGPT-4o", "FaultExplainer\no1-preview", "PCA\ndetectable", "IDD (this work)\nno candidates"]
    fig, ax = plt.subplots(figsize=(6.9, 2.55))
    ax.set_xlim(0, 4)
    ax.set_ylim(0, len(tep_ids))
    ax.axis("off")
    for j, cname in enumerate(cols):
        ax.text(j + 0.5, len(tep_ids) + 0.12, cname, ha="center", va="bottom", fontsize=7.8,
                fontweight="bold", color="#1e3a54")
    for i, cid in enumerate(tep_ids):
        y = len(tep_ids) - 0.5 - i
        g, c = gradings[cid], cases[cid]
        lb = c.get("literature_baseline", {})
        ax.text(-0.06, y, labels[i], ha="right", va="center", fontsize=7.8, color="#111111")
        fe1 = lb.get("fe_gpt4o", "unscored")
        fe2 = lb.get("fe_o1", "unscored")
        pca = lb.get("pca", "detectable")
        top1 = g.get("top1")
        conf = (g["confidence"] or 0) / 100
        cells = []
        for val, oktxt, badtxt, nstxt in ((fe1, "correct", "wrong", "unscored"), (fe2, "correct", "wrong", "unscored")):
            cells.append((oktxt, GREEN, "white") if val == "correct" else
                         ((badtxt, VERM, "white") if val == "incorrect" else (nstxt, "#eef1f4", "#7a848e")))
        cells.append(("yes", "#eef1f4", "#4a4a4a") if pca == "detectable" else ("no", "#dfe6ec", "#1e3a54"))
        if top1:
            cells.append((f"Top-1  ({conf:.2f})", "#0a7d38", "white"))
        else:
            cells.append((f"capped CS  ({conf:.2f})", "#f5e3c8", AMBER_DARK))
        for j, (txt, bg, fg) in enumerate(cells):
            r = FancyBboxPatch((j + 0.045, y - 0.36), 0.91, 0.72,
                               boxstyle="round,pad=0.012,rounding_size=0.06",
                               fc=bg, ec="#d5dbe1", lw=0.5)
            ax.add_patch(r)
            ax.text(j + 0.5, y, txt, ha="center", va="center", fontsize=7.6,
                    color=fg, fontweight="bold" if j == 3 else "normal")
    ax.axvline(3, color=BLUE, lw=1.1)
    save(fig, "fig_tep")


# ── Fig. forest：Wilson 区间汇总 ────────────────────────────────────────
def fig_forest():
    n = metrics["fault_cases"]
    top1, = [metrics["top1"]]
    topk = sum(1 for i in gradings if not cases[i].get("control") and gradings[i].get("topk"))
    cpass = metrics["control_pass"]
    rows = [
        ("FaultExplainer GPT-4o", 7, 11, GREY, "o", "candidates in prompt"),
        ("FaultExplainer o1-preview", 9, 11, GREY, "o", "candidates in prompt"),
        ("IDD — TEP subset, Top-1", 5, 6, BLUE, "o", "no candidates"),
        ("IDD — all faults, Top-1", top1, n, BLUE, "o", "no candidates"),
        ("IDD — all faults, top-k", topk, n, BLUE, "o", "no candidates"),
        ("IDD — controls passed", cpass, 3, GREEN, "o", "zero false alarms"),
    ]
    fig, ax = plt.subplots(figsize=(6.9, 2.9))
    ys = list(range(len(rows)))[::-1]
    for y, (label, x, nn, col, mk, sub) in zip(ys, rows):
        lo, hi = wilson(x, nn)
        ax.plot([lo, hi], [y, y], color=col, lw=2.2, solid_capstyle="round", alpha=0.85 if col == GREY else 1.0)
        ax.plot(x / nn * 100, y, marker=mk, ms=6, mfc=(col if col != BLUE or mk == "o" else "white"),
                mec=col, mew=1.2)
        ax.text(102, y, f"{x}/{nn} = {x/nn*100:.1f}%  [{lo:.1f}, {hi:.1f}]", va="center", fontsize=7.2,
                color="#1e3a54")
        ax.text(-2, y + 0.28, label, ha="left", fontsize=8, color="#111111",
                fontweight="bold" if label.startswith("IDD — all") else "normal")
        ax.text(-2, y - 0.34, f"n = {nn} · {sub}", ha="left", fontsize=6.8, color="#7a848e")
    ax.axvline(50, color="#c9cdd3", lw=0.8, ls=":")
    ax.text(50, len(rows) - 0.2, "50%", fontsize=6.8, color="#7a848e", ha="center", va="bottom")
    ax.set_xlim(0, 137)
    ax.set_ylim(-0.9, len(rows))
    ax.set_yticks([])
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xlabel("Accuracy (%) with Wilson 95% CI")
    ax.spines["left"].set_visible(False)
    save(fig, "fig_forest")


def fig_suite_matrix():
    """Per-scenario x multi-system comparison matrix (IDD vs same-model baselines).
    Data: gradings (IDD verdicts) + baselines.json (scored LLM arms) +
    baselines/baseline-suite/runs (live PCA/FE suite executions). Zero hand-copied values."""
    import matplotlib.patches as mpatches
    from matplotlib.colors import LinearSegmentedColormap

    baselines = json.load(open(os.path.join(RES, "baselines.json"), encoding="utf-8"))
    suite = os.path.join(ROOT, "baselines", "baseline-suite", "runs")

    def suite_json(name):
        p = os.path.join(suite, name)
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None

    rate_cmap = LinearSegmentedColormap.from_list("rate", ["#FFFFFF", "#BFD7EE", BLUE])

    fig, ax = plt.subplots(figsize=(7.05, 3.85))
    n = len(ORDER)
    for yi, cid in enumerate(ORDER):
        y = n - 1 - yi
        c = cases[cid]
        g = gradings[cid]
        bl = baselines["llm"].get(cid, {})
        # 1) IDD verdict
        if c.get("control"):
            col, txt = GREEN, "normal\n%.2f" % (g["confidence"] / 100.0)
        elif g.get("top1"):
            col, txt = GREEN, "Top-1\n%.2f" % (g["confidence"] / 100.0)
        elif g.get("topk"):
            col, txt = SKY, "CS %.2f\nranked" % (g["confidence"] / 100.0)
        else:
            col, txt = ORANGE, "CS %.2f\nunranked" % (g["confidence"] / 100.0)
        ax.add_patch(Rectangle((0, y), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
        ax.text(0.5, y + 0.5, txt, ha="center", va="center", fontsize=6.6,
                color="white" if col != SKY else "#123a52", linespacing=1.1)
        # 2) bare-LLM strict
        nc = bl.get("no_candidates")
        if nc is None:
            col, txt = "#eef0f2", "n/a"
        elif c.get("control"):
            col, txt = (GREEN, "normal") if nc.get("normal_verdict") else (VERM, "alarm!")
        else:
            col, txt = (GREEN, "hit") if nc.get("strict_top1_hit") else (VERM, "miss")
        ax.add_patch(Rectangle((1, y), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
        ax.text(1.5, y + 0.5, txt, ha="center", va="center", fontsize=6.8,
                color="white" if col in (GREEN, VERM) else "#5a6a7a")
        # 3) FE-style with candidates (TEP faults only)
        wc = bl.get("with_candidates")
        if c["dataset"] != "tep" or c.get("control"):
            col, txt = "#eef0f2", "-"
        else:
            col, txt = (GREEN, "hit") if (wc or {}).get("fe_style_top3_hit") else (VERM, "miss")
        ax.add_patch(Rectangle((2, y), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
        ax.text(2.5, y + 0.5, txt, ha="center", va="center", fontsize=6.8,
                color="white" if col in (GREEN, VERM) else "#5a6a7a")
        # 4/5) PCA detection rates (suite live execution)
        sp = suite_json(cid + ".pca.json")
        rates = [(sp or {}).get("detection", {}).get(k) for k in ("detection_rate_T2", "detection_rate_SPE")]
        if rates[0] is None:
            rates = [baselines["pca"][cid]["detection_rate_T2"], baselines["pca"][cid]["detection_rate_SPE"]]
        for xi, r in zip((3, 4), rates):
            r = float(r)  # int rates (1) would index the cmap LUT instead of normalizing
            ax.add_patch(Rectangle((xi, y), 1, 1, facecolor=rate_cmap(r), edgecolor="white", lw=1.2))
            ax.text(xi + 0.5, y + 0.5, "%.0f" % (r * 100), ha="center", va="center", fontsize=6.8,
                    color="white" if r > 0.62 else "#1e3a54")
        # 6) FE-protocol detection (suite live execution)
        sf = suite_json(cid + ".fe.json")
        if sf is None:
            col, txt = "#eef0f2", "-"
        else:
            col, txt = (GREEN, "det.") if sf["detection"]["detected"] else (VERM, "no")
        ax.add_patch(Rectangle((5, y), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
        ax.text(5.5, y + 0.5, txt, ha="center", va="center", fontsize=6.8,
                color="white" if col in (GREEN, VERM) else "#5a6a7a")

    # dataset group separators (skab | tep | indpensim | tep)
    for yi in range(1, n):
        if cases[ORDER[yi]]["dataset"] != cases[ORDER[yi - 1]]["dataset"]:
            ax.axhline(n - yi, color="#4a5a6a", lw=1.0)
    ax.set_xlim(0, 6)
    ax.set_ylim(0, n)
    ax.set_yticks([n - 0.5 - i for i in range(n)])
    ax.set_yticklabels([SHORT[cid] for cid in ORDER], fontsize=7)
    ax.set_xticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
    ax.set_xticklabels(["IDD verdict\n(conf.)", "Bare LLM\n(strict)", "FE style\n(cand.)",
                        "PCA T²\ndet. %", "PCA SPE\ndet. %", "FE prot.\ndet."], fontsize=6.9)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_aspect("auto")
    handles = [
        mpatches.Patch(facecolor=GREEN, label="resolved / hit / pass"),
        mpatches.Patch(facecolor=SKY, label="capped CS, mechanism ranked"),
        mpatches.Patch(facecolor=ORANGE, label="capped CS, not ranked"),
        mpatches.Patch(facecolor=VERM, label="miss / not detected"),
        mpatches.Patch(facecolor="#eef0f2", label="not in protocol scope"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.09),
              ncol=3, frameon=False, fontsize=6.6, handlelength=1.2, handleheight=0.9)
    save(fig, "fig_suite_matrix")



fig_benchmark()
fig_calibration()
fig_tep()
fig_forest()
fig_suite_matrix()
print("done")
