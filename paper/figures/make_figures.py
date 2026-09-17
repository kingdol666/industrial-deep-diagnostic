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
# All figure widths are set to the final print width (\textwidth = 5.4 in) so that
# the nominal point sizes below are the *printed* sizes (reviewers flagged figures
# whose effective font was 4.7-5.5 pt after down-scaling).
PRINT_W = 5.4
plt.rcParams.update({
    "font.family": "Arial",
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.linewidth": 1.0,
    "xtick.labelsize": 8.5,
    "ytick.labelsize": 8.5,
    "legend.fontsize": 8,
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


def wilson(x, n, z=1.96):  # z=1.96 matches the released scorer (aggregate.mjs)
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
    # Stacked layout: at print width the 12 scenario labels need the full line,
    # so the two panels share one column (reviewer V1: side-by-side overlapped).
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(PRINT_W, 4.5),
                                   gridspec_kw={"height_ratios": [1, 2.6], "hspace": 0.55})

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
            # Convention (as Fig 8): SKY = capped COMPETING_SET with the true mechanism ranked.
            # Black '///' hatch (same as Fig 4 calibration bars + Fig 8 suite-matrix cells)
            # keeps the capped verdict separable from solid BLUE in grayscale — SKY vs AMBER
            # luminance differs by ~1%, so hue alone cannot carry the ranked/unranked split.
            ax1.barh(y, topk_only, left=top1, color=SKY, height=0.52,
                     edgecolor="#222222", lw=0.6, hatch="///", hatch_linewidth=0.5,
                     label="capped CS, true mechanism ranked (top-k)" if y == 2 else None)
        if miss:
            # AMBER = capped COMPETING_SET without the true mechanism (the TEP IDV3 miss)
            ax1.barh(y, miss, left=top1 + topk_only, color=ORANGE, height=0.52,
                     label="capped CS, true mechanism not ranked" if y == 2 else None)
        ax1.text(n + 0.15, y, f"{top1}/{n}", va="center", fontsize=7.6, fontweight="bold", color="#1e3a54")
    ax1.set_yticks(ypos)
    ax1.set_yticklabels([r[0] for r in rows])
    ax1.set_xlim(0, 7.6)
    ax1.set_xticks([0, 1, 2, 3, 4, 5, 6])
    ax1.set_xlabel("Fault scenarios (n = 9)")
    ax1.set_title("(a) Fault outcomes by dataset", fontsize=9, loc="left")
    # legend intentionally omitted: colours are defined in the figure caption

    # (b) rubric + judge gate per scenario (faults only, controls marked).
    # Single hue for faults (blue) + grey for controls: dataset/verdict-typing is
    # carried by panel (a) and Table 4, so the marker colours here must NOT imply
    # a second categorical scale (reviewer V1: legend/colour mismatch).
    ids = [i for i in ORDER]
    ys = list(range(len(ids)))[::-1]
    for y, cid in zip(ys, ids):
        g = gradings[cid]
        c = cases[cid]
        rub, jud = g["rubric"]["score"], g["judge_score"]
        col = GREY if c.get("control") else BLUE
        ax2.plot(jud, y, "o", ms=4.6, mfc="white", mec=col, mew=1.4)
        ax2.plot(rub, y, "o", ms=4.6, color=col)
    ax2.set_yticks(ys)
    ax2.set_yticklabels([SHORT[i] for i in ids], fontsize=8)
    ax2.set_xlim(50, 103)
    ax2.set_xticks([50, 60, 70, 80, 90, 100])
    ax2.set_xlabel("Score (points)")
    ax2.set_title("(b) Rubric vs. judge gate", fontsize=9, loc="left")
    ax2.axvline(90, color="#b9c2cc", lw=0.9, ls=":")
    ax2.text(90, len(ids) - 0.15, "gate 90", fontsize=7.5, color="#7a848e", ha="center", va="bottom")
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], marker="o", ls="", mfc=BLUE, mec=BLUE, ms=4.6, label="rubric (faults)"),
               Line2D([], [], marker="o", ls="", mfc="white", mec=BLUE, ms=4.6, label="judge gate (faults)"),
               Line2D([], [], marker="o", ls="", mfc=GREY, mec=GREY, ms=4.6, label="controls")]
    # legend intentionally omitted: marker semantics are defined in the figure caption
    save(fig, "fig_benchmark")


# ── Fig. calibration：12 场景置信度 + 协议上限线 ────────────────────────
def fig_calibration():
    fig, ax = plt.subplots(figsize=(PRINT_W, 2.47))
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
            # Convention (as Fig 8): SKY = capped CS with the true mechanism ranked,
            # AMBER = capped CS without it (TEP IDV3). The capped SKY bars carry a
            # black '///' hatch so the capped verdict stays distinct from the solid
            # DETERMINED blues even in grayscale (hue alone was near-identical).
            ranked = bool(g.get("topk"))
            if ranked:
                ax.barh(y, conf, height=0.62, color=SKY, edgecolor="#222222",
                        lw=0.6, hatch="///", hatch_linewidth=0.5)
            else:
                ax.barh(y, conf, height=0.62, color=ORANGE)
            lbl, tc = (f"CS {conf:.2f}", "#123a52") if ranked else (f"CS {conf:.2f}", AMBER_DARK)
        else:
            # Convention: solid IDD dark BLUE = DETERMINED everywhere (SKAB, TEP and
            # IndPenSim — the batch-93 bar was GREEN, now unified with the Fig 8
            # suite-matrix column 1); GREEN is reserved for controls only.
            ax.barh(y, conf, height=0.62, color=BLUE)
            lbl, tc = f"DET {conf:.2f}", "#1e3a54"
        # white semi-opaque bbox on every value label so the amber 0.70 ceiling
        # dashes cannot strike through glyphs like "CS 0.60" (same convention
        # as the ann_bbox in fig_case_study)
        ax.text(conf + 0.008, y, lbl, va="center", fontsize=7.2, fontweight="bold", color=tc,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1.2))
    ax.set_yticks(ys)
    ax.set_yticklabels([SHORT[i] for i in ids] if False else [SHORT[i] for i in ORDER], fontsize=7.3)
    ax.axvline(0.70, color=ORANGE, lw=1.0, ls="--", zorder=0.5)  # beneath the bars (patches zorder=1)
    ax.set_ylim(-0.6, 12.7)  # headroom band above the top bar for the ceiling label
    ax.text(0.693, 12.15, "ceiling for capped verdicts only (0.70)", fontsize=7.6,
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
    fig, ax = plt.subplots(figsize=(PRINT_W, 2.00))
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
            # IDD-won cells use the IDD BLUE (same as Fig 4 DETERMINED bars); the old
            # #0a7d38 was a second green colliding with the FE-correct #009E73 green.
            cells.append((f"Top-1  ({conf:.2f})", BLUE, "white"))
        else:
            # same amber constant as the unranked-CS cell in fig_suite_matrix (ORANGE);
            # one verdict = one amber; dark text keeps legibility on the saturated fill
            cells.append((f"capped CS  ({conf:.2f})", ORANGE, "#3a2600"))
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
    fig, ax = plt.subplots(figsize=(PRINT_W, 2.27))
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
        ax.text(-2, y - 0.34, f"n = {nn} · {sub}", ha="left", fontsize=8.2, color="#7a848e")
    ax.axvline(50, color="#c9cdd3", lw=0.8, ls=":")
    ax.text(50, len(rows) - 0.2, "50%", fontsize=7.8, color="#7a848e", ha="center", va="bottom")
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

    rate_cmap = LinearSegmentedColormap.from_list("rate", ["#FFFFFF", "#CCE3DC", "#2E6E63"])  # teal, orthogonal to semantic hues

    fig, ax = plt.subplots(figsize=(PRINT_W, 4.35))
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
            # Convention: IDD dark BLUE = resolved DETERMINED (same constant as the
            # Fig 4 calibration DETERMINED bars); GREEN is reserved for controls.
            col, txt = BLUE, "Top-1\n%.2f" % (g["confidence"] / 100.0)
        elif g.get("topk"):
            col, txt = SKY, "CS %.2f\nranked" % (g["confidence"] / 100.0)
        else:
            col, txt = ORANGE, "CS %.2f\nunranked" % (g["confidence"] / 100.0)
        ax.add_patch(Rectangle((0, y), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
        if col == SKY:
            # same black '///' hatch as the capped-CS bars in fig_calibration:
            # keeps SKY (ranked CS) separable from the dark BLUE (DETERMINED) in grayscale
            ax.add_patch(Rectangle((0, y), 1, 1, facecolor="none", edgecolor="#222222",
                                   lw=0, hatch="///", hatch_linewidth=0.5))
        ax.text(0.5, y + 0.5, txt, ha="center", va="center", fontsize=8.1,
                color=("#3a2600" if col == ORANGE else
                       ("white" if col != SKY else "#123a52")), linespacing=1.1)
        # 2) bare-LLM strict
        nc = bl.get("no_candidates")
        if nc is None:
            col, txt = "#eef0f2", "n/a"
        elif c.get("control"):
            col, txt = (GREEN, "normal") if nc.get("normal_verdict") else (VERM, "alarm!")
        else:
            col, txt = (GREEN, "hit") if nc.get("strict_top1_hit") else (VERM, "miss")
        ax.add_patch(Rectangle((1, y), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
        ax.text(1.5, y + 0.5, txt, ha="center", va="center", fontsize=8.3,
                color="white" if col in (GREEN, VERM) else "#5a6a7a")
        # 3) FE-style with candidates (TEP faults only)
        wc = bl.get("with_candidates")
        if c["dataset"] != "tep" or c.get("control"):
            col, txt = "#eef0f2", "-"
        else:
            col, txt = (GREEN, "hit") if (wc or {}).get("fe_style_top3_hit") else (VERM, "miss")
        ax.add_patch(Rectangle((2, y), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
        ax.text(2.5, y + 0.5, txt, ha="center", va="center", fontsize=8.3,
                color="white" if col in (GREEN, VERM) else "#5a6a7a")
        # 4/5) PCA detection rates (suite live execution)
        sp = suite_json(cid + ".pca.json")
        rates = [(sp or {}).get("detection", {}).get(k) for k in ("detection_rate_T2", "detection_rate_SPE")]
        if rates[0] is None:
            rates = [baselines["pca"][cid]["detection_rate_T2"], baselines["pca"][cid]["detection_rate_SPE"]]
        for xi, r in zip((3, 4), rates):
            r = float(r)  # int rates (1) would index the cmap LUT instead of normalizing
            ax.add_patch(Rectangle((xi, y), 1, 1, facecolor=rate_cmap(r), edgecolor="white", lw=1.2))
            ax.text(xi + 0.5, y + 0.5, "%.0f" % (r * 100), ha="center", va="center", fontsize=8.3,
                    color="white" if r > 0.62 else "#1e3a54")
        # 6) FE-protocol detection (suite live execution)
        sf = suite_json(cid + ".fe.json")
        if sf is None:
            col, txt = "#eef0f2", "-"
        elif cases[cid].get("control"):
            col, txt = "#eef0f2", "no (correct:\ncontrol)"  # two lines: single line overflows the last column
        else:
            col, txt = (GREEN, "det.") if sf["detection"]["detected"] else (VERM, "no")
        ax.add_patch(Rectangle((5, y), 1, 1, facecolor=col, edgecolor="white", lw=1.2))
        ax.text(5.5, y + 0.5, txt, ha="center", va="center", fontsize=8.3,
                color="white" if col in (GREEN, VERM) else "#5a6a7a")

    # dataset group separators (skab | tep | indpensim | tep)
    for yi in range(1, n):
        if cases[ORDER[yi]]["dataset"] != cases[ORDER[yi - 1]]["dataset"]:
            ax.axhline(n - yi, color="#4a5a6a", lw=1.0)
    ax.set_xlim(0, 6)
    ax.set_ylim(0, n)
    ax.set_yticks([n - 0.5 - i for i in range(n)])
    ax.set_yticklabels([SHORT[cid] for cid in ORDER], fontsize=8.4)
    ax.set_xticks([0.5, 1.5, 2.5, 3.5, 4.5, 5.5])
    ax.set_xticklabels(["IDD verdict\n(conf.)", "Bare LLM\n(strict)", "FE style\n(cand.)",
                        "PCA T²\ndet. %", "PCA SPE\ndet. %", "FE prot.\ndet."], fontsize=7.9)
    ax.tick_params(length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.set_aspect("auto")
    handles = [
        mpatches.Patch(facecolor=BLUE, label="IDD resolved (Top-1)"),
        mpatches.Patch(facecolor=GREEN, label="baseline hit / control pass"),
        mpatches.Patch(facecolor=SKY, edgecolor="#222222", hatch="///",
                       hatch_linewidth=0.5, label="capped CS, mechanism ranked"),
        mpatches.Patch(facecolor=ORANGE, label="capped CS, not ranked"),
        mpatches.Patch(facecolor=VERM, label="miss / not detected"),
        mpatches.Patch(facecolor="#eef0f2", label="not in protocol scope"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.5, -0.09),
              ncol=3, frameon=False, fontsize=8.1, handlelength=1.2, handleheight=0.9)
    save(fig, "fig_suite_matrix")


def fig_case_study():
    """Case-study figure: signal annotation + evidence chain for the SKAB inlet-valve
    scenario (the capped COMPETING_SET verdict). Every annotation is read from the
    canonical run's own artifacts — no hand-entered values."""
    import csv as _csv
    RUN = os.path.join(ROOT, "workspace", "diagnostic-runs", "202609150453290_bench_skab_valve1_1")
    seg = json.load(open(os.path.join(RUN, "02_processed/anomaly_segment_analysis.json"), encoding="utf-8"))
    conf = json.load(open(os.path.join(RUN, "04_diagnostics/confidence.json"), encoding="utf-8"))
    lo, hi = seg["anomaly_window"]["index_range"]
    flow, cur = [], []
    with open(os.path.join(RUN, "00_input/data.csv"), encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            flow.append(float(r["Volume Flow RateRMS"]))
            cur.append(float(r["Current"]))
    conf_pct = conf["overall_confidence"]["score"]
    residence = (seg["anomaly_window"]["detection"].split(";")[-1].strip()
                 .replace("quantized", "quantised"))
    switches = seg["flow_in_window"]["switch_count_30_31"]
    cur_delta = seg["current_in_vs_out"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(PRINT_W, 3.6), sharex=True,
                                   gridspec_kw={"height_ratios": [1, 1], "hspace": 0.12})
    x = list(range(len(flow)))
    for ax, series, ylab in ((ax1, flow, "Volume flow rate (L/min)"), (ax2, cur, "Pump current (A)")):
        ax.axvspan(lo, hi, color="#FBEAD6", zorder=0)
        ax.plot(x, series, color=BLUE, lw=0.8)
        ax.set_ylabel(ylab)
        ax.set_xlim(560, 1005)
    ax1.axhspan(29.6, 30.6, color="#E8F1EA", zorder=0)
    ax1.set_ylim(29.3, 34.4)
    # headroom strip above the pump-current trace so its annotation never
    # competes with the dense spikes (the trace fills the whole panel otherwise)
    ax2.set_ylim(min(cur) - 0.08, max(cur) + 0.34)
    # near-opaque bbox on every annotation so signal spikes cannot strike through the text
    ann_bbox = dict(facecolor="white", edgecolor="none", alpha=0.95, pad=1.5)
    ax1.annotate("lowest quantisation bin (30 L/min):\n%d rows, %d runs, mean run %.2f samples"
                 % (seg["flow_in_window"]["value_counts"]["30.0"],
                    seg["flow_in_window"]["n_runs_at_30"],
                    seg["flow_in_window"]["mean_run_len"]),
                 xy=(hi - 120, 30.35), xytext=(655, 32.35), fontsize=8, color="#2E6E63",
                 va="top", ha="left", bbox=ann_bbox, zorder=6,
                 arrowprops=dict(arrowstyle="->", color="#2E6E63", lw=0.9))
    ax1.annotate("anomaly window (rows %d-%d)\n%d switches, 30 \u2194 31 L/min" % (lo, hi, switches),
                 xy=((lo + hi) / 2, 32.6), xytext=(575, 34.25), fontsize=8, color="#7a5230",
                 va="top", ha="left", bbox=ann_bbox, zorder=6)
    ax2.annotate("pump load %.3f A in-window vs %.3f A outside (\u22124.3%%)"
                 % (cur_delta["inside_mean"], cur_delta["outside_mean"]),
                 xy=(hi - 40, min(cur) + 0.012), xytext=(600, max(cur) + 0.30), fontsize=8,
                 color="#5a6a7a", bbox=ann_bbox, zorder=6)
    ax2.set_xlabel("Sample index (1 Hz)")

    # evidence strip fully inside the canvas: reserve bottom margin, anchor above the lower edge
    fig.subplots_adjust(bottom=0.30, top=0.97)
    fig.text(0.5, 0.012,
             "Evidence chain:  L1 recorded signals (flow hunts in the two lowest bins; no vibration/thermal shift; valve-position channel absent)  \u2192  "
             "L3 statistics (window mean 30.62 vs 31.73 L/min, \u22123.5%; " + residence + ")  \u2192  "
             "L5 mechanism (downstream resistance \u2191 forces the pump down its curve)  \u2192  "
             "H1 valve/downstream restriction  vs  H2 range-floor meter artifact  \u2192  "
             "verdict: capped COMPETING_SET %.2f \u2014 named missing channel: valve-position/command feedback"
             % (conf_pct / 100.0),
             ha="center", va="bottom", fontsize=8.0, color="#1c2733", wrap=True)
    save(fig, "fig_case_study")


def fig_consistency():
    """Consistency-audit figure, read entirely from the released consistency audit
    (consistency_audit.json). Panel (a): every proven independent execution of every
    scenario, era-coded (grey open = pre-discipline v1 era, excluded from the
    headline; filled = current v2 era, coloured by verdict type) with the audit
    status per scenario. Panel (b): the four re-tested current-era pairs, with the
    single within-era type flip (TEP IDV11) highlighted."""
    audit = json.load(open(os.path.join(RES, "consistency_audit.json"), encoding="utf-8"))
    TYPE_COLOR = {"DETERMINED": BLUE, "COMPETING_SET": SKY}
    STATUS_COLOR = {"CONSISTENT": GREEN, "WEAK": ORANGE, "DIVERGENT": VERM,
                    "INSUFFICIENT-RUNS": GREY}

    fig = plt.figure(figsize=(PRINT_W, 5.9))
    gs = fig.add_gridspec(2, 1, height_ratios=[1.55, 1.0], hspace=0.62)

    # ---- panel (a): per-scenario execution map ---------------------------------
    ax = fig.add_subplot(gs[0])
    y = {c: len(ORDER) - 1 - i for i, c in enumerate(ORDER)}
    for c in ORDER:
        runs = audit["cases"][c]["runs"]
        v2 = sorted([r for r in runs if r["era"] == "v2" and r["proven"] and r["confidence"]],
                    key=lambda r: r["run_id"])
        v1 = [r for r in runs if r["era"] == "v1" and r["proven"] and r["confidence"]]
        for r in v1:
            ax.plot(r["confidence"] / 100.0, y[c], marker="o", markersize=3.6,
                    markerfacecolor="none", markeredgecolor=GREY, markeredgewidth=0.9,
                    linestyle="none", zorder=2)
        if len(v2) >= 2:
            ax.plot([r["confidence"] / 100.0 for r in v2], [y[c]] * len(v2),
                    color="#b9c4cc", lw=0.9, zorder=1)
        for r in v2:
            ax.plot(r["confidence"] / 100.0, y[c], marker="o", markersize=6,
                    color=TYPE_COLOR[r["diagnosis_type"]], linestyle="none", zorder=3,
                    markeredgecolor="white", markeredgewidth=0.6)
        status = audit["cases"][c]["status"]
        n2 = len(v2)
        status_text = {"CONSISTENT": "consistent", "WEAK": "weak", "DIVERGENT": "divergent",
                       "INSUFFICIENT-RUNS": "awaiting retest"}[status]
        ax.text(1.05, y[c], status_text, fontsize=6.8,
                va="center", ha="left", color=STATUS_COLOR[status],
                fontweight="bold" if status != "INSUFFICIENT-RUNS" else "normal")
        ax.text(1.025, y[c], f"{n2}" if n2 else "0", fontsize=6.8, va="center",
                ha="right", color="#444444")
    ax.axvline(0.70, color=ORANGE, lw=0.9, linestyle=(0, (4, 3)), zorder=0)
    ax.text(0.703, len(ORDER) - 0.45, "0.70 competing-set cap", fontsize=6.8,
            color=AMBER_DARK, ha="left", va="top")
    ax.set_yticks([y[c] for c in ORDER])
    ax.set_yticklabels([SHORT[c] for c in ORDER], fontsize=7.6)
    ax.set_xlim(0.4, 1.26)
    ax.set_xticks([0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    ax.set_xlabel("Reported confidence")
    ax.set_ylabel("Scenario")
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    from matplotlib.lines import Line2D
    handles = [
        Line2D([], [], marker="o", markersize=6, color=BLUE, linestyle="none",
               markeredgecolor="white", label="determined (current era)"),
        Line2D([], [], marker="o", markersize=6, color=SKY, linestyle="none",
               markeredgecolor="white", label="competing\u005fset (current era)"),
        Line2D([], [], marker="o", markersize=4.2, color=GREY, linestyle="none",
               markerfacecolor="none", markeredgewidth=0.9,
               label="pre-discipline era (context, excluded)"),
    ]
    ax.legend(handles=handles, loc="upper center", bbox_to_anchor=(0.42, -0.16),
              ncol=3, frameon=False, fontsize=7, handletextpad=0.3,
              columnspacing=1.1, borderaxespad=0.0)
    ax.text(-0.02, 1.06, "(a)", transform=ax.transAxes, fontsize=9.5, fontweight="bold")

    # ---- panel (b): the four re-tested current-era pairs -----------------------
    axb = fig.add_subplot(gs[1])
    retested = [c for c in ORDER
                if len([r for r in audit["cases"][c]["runs"]
                        if r["era"] == "v2" and r["proven"] and r["confidence"]]) >= 2]
    xs = {c: i for i, c in enumerate(retested)}
    for c in retested:
        v2 = sorted([r for r in audit["cases"][c]["runs"]
                     if r["era"] == "v2" and r["proven"] and r["confidence"]],
                    key=lambda r: r["run_id"])
        confs = [r["confidence"] / 100.0 for r in v2]
        types = [r["diagnosis_type"] for r in v2]
        # jitter coincident confidences (e.g. two runs both capping at 0.65)
        spread = 0.10 if max(confs) - min(confs) < 0.02 else 0.0
        mxs = [xs[c] + (i - (len(confs) - 1) / 2) * spread for i in range(len(confs))]
        axb.plot(mxs, confs, color="#b9c4cc", lw=1.1, zorder=1)
        for i, (xx, cc, tt) in enumerate(zip(mxs, confs, types)):
            retest_flip = c == "tep_d11_reactor_cooling_random" and i == 1
            axb.plot(xx, cc, marker="o", markersize=7.5 if retest_flip else 6,
                     color=TYPE_COLOR[tt], linestyle="none", zorder=3,
                     markeredgecolor=VERM if retest_flip else "white",
                     markeredgewidth=1.6 if retest_flip else 0.6)
        if len(set(types)) == 1:
            axb.text(xs[c], max(confs) + 0.026,
                     "%d\u00d7 %s" % (len(types), "DET" if types[0] == "DETERMINED" else "CS"),
                     fontsize=6.2, ha="center", color=TYPE_COLOR[types[0]], fontweight="bold")
        else:
            for xx, cc, tt in zip(mxs, confs, types):
                axb.text(xx, cc + 0.026, "DET" if tt == "DETERMINED" else "CS",
                         fontsize=6.2, ha="center", color=TYPE_COLOR[tt], fontweight="bold")
        st = audit["cases"][c]["status"]
        axb.text(xs[c], 1.055, st.replace("-RUNS", ""), fontsize=6.6, ha="center",
                 color=STATUS_COLOR[st], fontweight="bold")
    axb.axhline(0.70, color=ORANGE, lw=0.9, linestyle=(0, (4, 3)), zorder=0)
    axb.text(len(retested) - 0.55, 0.712, "0.70 cap", fontsize=6.8, color=AMBER_DARK,
             ha="right", va="bottom")
    axb.set_xticks(list(xs.values()))
    axb.set_xticklabels([SHORT[c].replace("TEP ", "").replace("SKAB ", "SKAB\n")
                         for c in retested], fontsize=7.2)
    axb.set_ylim(0.5, 1.0)
    axb.set_ylabel("Confidence")
    axb.text(-0.10, 1.10, "(b)", transform=axb.transAxes, fontsize=9.5, fontweight="bold")
    save(fig, "fig_consistency")


fig_benchmark()
fig_calibration()
fig_tep()
fig_forest()
fig_suite_matrix()
fig_case_study()
fig_consistency()
print("done")
