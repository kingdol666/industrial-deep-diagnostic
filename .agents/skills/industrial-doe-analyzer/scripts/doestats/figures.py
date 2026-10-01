"""Figure generation (per-mode sets) with per-type ink gates.

Plot text is English on purpose: the rendering hosts may lack CJK fonts and a
tofu-box title would still pass an ink check — the Chinese narrative lives in
report.md / report.html. Ink gating: plot_verification._ink_check (size/quadrants,
reused) + a per-type minimum non-white-ratio check implemented here
(heatmaps/contours need more ink than line plots to be meaningful).

Style baseline (P2): base font 10.5pt with 150 dpi so axis/tick text stays
legible at report width; interaction effects are NOT plotted here — the HTML
report owns interaction visualization (interaction_matrix type retired).
"""

import math
from pathlib import Path

import numpy as np
import pandas as pd

TYPE_INK = {
    "pareto": 0.010, "main_effects": 0.010,
    "contour": 0.020, "residual_diagnostics": 0.010,
    "correlation_heatmap": 0.020, "contribution_bar": 0.010,
    "stability_timeline": 0.010, "segment_comparison": 0.010,
}
MIN_BYTES = 2048
DPI = 150
TIMELINE_MAX_POINTS = 5000   # equal-stride downsample above this
HEATMAP_MAX_PARAMS = 12


def _apply_style():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({
        "font.size": 10.5,
        "axes.titlesize": 11,
        "axes.labelsize": 10.5,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "legend.fontsize": 9.5,
        "figure.titlesize": 12,
        "savefig.dpi": DPI,
    })
    return plt


def _ratio(png_path):
    try:
        from PIL import Image
        a = np.asarray(Image.open(png_path).convert("L"))
        return float((a < 245).mean())
    except Exception:
        return None


def _finalize(entry, out_dir):
    path = out_dir / entry["file"]
    entry["bytes"] = path.stat().st_size if path.exists() else 0
    ok_ink, detail = True, "ink check skipped"
    try:
        import sys
        from plot_verification import _ink_check  # reused private helper (documented)
        ok_ink, detail = _ink_check(str(path))
    except Exception as exc:
        detail = f"reused ink check unavailable: {exc}"
    ratio = _ratio(path)
    threshold = TYPE_INK.get(entry["type"], 0.01)
    entry["min_ink_ratio"] = threshold
    if ratio is not None:
        if ratio < threshold:
            ok_ink = False
            detail = f"ink ratio {ratio:.4f} < {threshold} for type {entry['type']}"
        else:
            detail = f"ink ratio {ratio:.4f} ok; {detail}"
    entry["ink_ok"] = bool(ok_ink and entry["bytes"] >= MIN_BYTES)
    entry["ink_detail"] = detail
    return entry


def _save(fig, out_dir, name):
    path = out_dir / name
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    import matplotlib.pyplot as plt
    plt.close(fig)
    return name


# ------------------------------------------------------------------ designed

def _ranked_factor_order(model, effect_table, resp):
    """Core numeric factor columns ordered by the response's Pareto ranking
    (pareto_rank asc), falling back to column order when no ranks exist."""
    core = [i for i in model["factor_info"]
            if not i.get("is_block") and not i.get("is_covariate")
            and not i["zero_variance"] and i["type"] == "numeric"]
    core_cols = [i["col"] for i in core]
    tests = next((f["tests"] for f in effect_table.get("families", [])
                  if f["response"] == resp), [])
    ranked = [t for t in tests if t.get("pareto_rank") and t.get("estimable")]
    ranked.sort(key=lambda t: t["pareto_rank"])
    order = []
    for t in ranked:
        for f in t["term"].split(":"):
            if f in core_cols and f not in order:
                order.append(f)
    return ([c for c in order if c in core_cols]
            + [c for c in core_cols if c not in order]), {i["col"]: i for i in core}


def designed_figures(models, effect_table, profile, out_dir, df=None):
    out_dir = Path(out_dir)
    plots = []
    plt = _apply_style()
    from scipy import stats as sps

    for resp, model in list(models.items())[:3]:
        # pareto of |t|
        tests = next((f["tests"] for f in effect_table["families"]
                      if f["response"] == resp), [])
        rankable = [t for t in tests if t.get("std_err") not in (None, 0)]
        rankable.sort(key=lambda t: abs((t["coefficient"] or 0) / t["std_err"]))
        if rankable:
            names = [t["term"] for t in rankable]
            tvals = [abs(t["coefficient"] / t["std_err"]) for t in rankable]
            fig, ax = plt.subplots(figsize=(7, max(3, 0.4 * len(names) + 1)))
            colors = ["#c2673a" if (t.get("q_value_bh") is not None and t["q_value_bh"] < 0.05)
                      else "#8a8a8a" for t in rankable]
            ax.barh(names, tvals, color=colors)
            df_r = model["df_resid"]
            if df_r and df_r > 0:
                ref = sps.t.ppf(0.975, df_r)
                ax.axvline(ref, color="#c4433b", linestyle="--", linewidth=1)
            ax.set_title(f"Pareto of standardized effects — {resp}")
            ax.set_xlabel("|t| = |coef|/SE")
            plots.append(_finalize({
                "file": _save(fig, out_dir, f"pareto_{_safe(resp)}.png"),
                "type": "pareto", "title": f"Pareto of standardized effects — {resp}",
                "response": resp}, out_dir))

        # residual diagnostics
        try:
            resid = np.array(model["_residuals"])
            fitted = np.array(model["_fitted"])
            if resid.size > 5:
                fig, axs = plt.subplots(2, 2, figsize=(9, 7))
                axs[0, 0].scatter(fitted, resid, s=12, color="#1e3a54")
                axs[0, 0].axhline(0, color="#c4433b", linewidth=1)
                axs[0, 0].set_title("Residuals vs fitted")
                sps.probplot(resid, plot=axs[0, 1])
                axs[0, 1].set_title("Normal Q-Q")
                axs[1, 0].hist(resid, bins=20, color="#2d7d4f")
                axs[1, 0].set_title("Residual histogram")
                axs[1, 1].scatter(range(len(resid)), resid, s=12, color="#1e3a54")
                axs[1, 1].axhline(0, color="#c4433b", linewidth=1)
                axs[1, 1].set_title("Residuals vs run order (randomization check)")
                fig.tight_layout()
                plots.append(_finalize({
                    "file": _save(fig, out_dir, f"residuals_{_safe(resp)}.png"),
                    "type": "residual_diagnostics",
                    "title": f"Residual diagnostics — {resp}", "response": resp}, out_dir))
        except Exception:
            pass

    # main effects (first response): level/decile means with +/- SE error bars
    resp0 = next(iter(models), None)
    if resp0 and df is not None:
        model = models[resp0]
        core = [i for i in model["factor_info"]
                if not i.get("is_block") and not i.get("is_covariate")
                and not i["zero_variance"]][:6]
        if core:
            fig, axs = plt.subplots(1, len(core),
                                    figsize=(3 * len(core), 3.2), squeeze=False)
            se_estimable = True
            for ax, info in zip(axs[0], core):
                col = info["col"]
                try:
                    yv = pd.to_numeric(df[resp0], errors="coerce")
                    if info["type"] == "numeric":
                        x = df[col].astype(float)
                        bins = pd.qcut(x, q=min(8, max(3, x.nunique())), duplicates="drop")
                        grouped = yv.groupby(bins, observed=True)
                        labels = [f"Q{i+1}" for i in range(len(grouped))][:len(grouped)]
                    else:
                        grouped = yv.groupby(df[col].astype(str), observed=True)
                        labels = [str(i)[:8] for i in grouped.groups]
                    means, ses, kept_labels = [], [], []
                    for lab, (key, vals) in zip(labels, grouped):
                        v = pd.to_numeric(pd.Series(vals), errors="coerce").dropna()
                        if v.empty:
                            continue
                        means.append(float(v.mean()))
                        kept_labels.append(lab)
                        if len(v) > 1 and float(v.std(ddof=1)) > 0:
                            ses.append(float(v.std(ddof=1) / math.sqrt(len(v))))
                        else:
                            ses.append(None)
                    if any(s is None for s in ses):
                        se_estimable = False
                    xs = range(len(means))
                    if all(s is not None for s in ses) and ses:
                        ax.errorbar(xs, means, yerr=ses, fmt="o-", color="#1e3a54",
                                    capsize=3, markersize=4, linewidth=1.2)
                    else:
                        ax.plot(xs, means, marker="o", color="#1e3a54")
                    ax.set_xticks(list(xs), kept_labels, fontsize=8)
                    ax.set_title(col, fontsize=9.5)
                except Exception:
                    ax.set_title(f"{col} (skipped)", fontsize=8)
            suffix = "" if se_estimable else \
                " — error bars omitted (group SE not estimable)"
            fig.suptitle(f"Main effects — {resp0} (mean ± SE per factor bin/level)"
                         + suffix)
            fig.tight_layout()
            plots.append(_finalize({
                "file": _save(fig, out_dir, f"main_effects_{_safe(resp0)}.png"),
                "type": "main_effects",
                "title": f"Main effects — {resp0}" + suffix,
                "response": resp0}, out_dir))

    # contour of the top-2 Pareto-ranked active numeric factors (first response)
    resp0 = next(iter(models), None)
    if resp0:
        model = models[resp0]
        ordered, infos = _ranked_factor_order(model, effect_table, resp0)
        if len(ordered) >= 2:
            try:
                gx = np.linspace(-1, 1, 25)
                grid = np.meshgrid(gx, gx)
                f1, f2 = ordered[0], ordered[1]
                i1, i2 = infos[f1], infos[f2]
                raw1 = i1["mean"] + grid[0] * i1["half_range"]
                raw2 = i2["mean"] + grid[1] * i2["half_range"]
                z = np.empty_like(raw1)
                rest = [i for c, i in infos.items() if c not in (f1, f2)]
                anchor = {i["col"]: i["mean"] for i in rest}
                for a in range(z.shape[0]):
                    for b in range(z.shape[1]):
                        raw = dict(anchor)
                        raw[f1] = raw1[a, b]
                        raw[f2] = raw2[a, b]
                        yv = model["predict_raw"](raw)
                        z[a, b] = yv if yv is not None else np.nan
                fig, ax = plt.subplots(figsize=(6.2, 5))
                cs = ax.contourf(raw1, raw2, z, levels=18, cmap="cividis")
                fig.colorbar(cs, ax=ax)
                ax.contour(raw1, raw2, z, levels=18, colors="k", linewidths=0.4)
                ax.set_xlabel(f1)
                ax.set_ylabel(f2)
                ax.set_title(f"Predicted response contour — {resp0} "
                             f"(top-Pareto pair {f1} x {f2}; others at center)")
                plots.append(_finalize({
                    "file": _save(fig, out_dir, f"contour_{_safe(resp0)}.png"),
                    "type": "contour",
                    "title": (f"Predicted response contour — {resp0} "
                              f"(top-Pareto pair {f1} x {f2})"),
                    "response": resp0}, out_dir))
            except Exception:
                pass
    return plots


def _safe(name):
    return "".join(ch if ch.isalnum() else "_" for ch in name)[:40]


# ------------------------------------------------------------------ observational

def observational_figures(correlation, stability, df, out_dir):
    out_dir = Path(out_dir)
    plots = []
    plt = _apply_style()

    pairs = correlation.get("pairs", [])
    # honest selection: only pairs that EARNED a place — significant after BH
    # (q<0.05) or not failed anti-spurious. Title matches the actual content.
    kept_pairs = [p for p in pairs
                  if (p.get("q_value_bh") is not None and p["q_value_bh"] < 0.05)
                  or p.get("anti_spurious_verdict") != "FAIL"]
    if kept_pairs:
        targets = sorted({p["target"] for p in kept_pairs})
        all_params = sorted({p["parameter"] for p in kept_pairs},
                            key=lambda c: -max((abs(p["r"]) for p in kept_pairs
                                                if p["parameter"] == c), default=0))
        truncated = len(all_params) > HEATMAP_MAX_PARAMS
        params = all_params[:HEATMAP_MAX_PARAMS]
        mat = np.full((len(targets), len(params)), np.nan)
        for p in kept_pairs:
            if p["parameter"] in params and p["target"] in targets:
                mat[targets.index(p["target"]), params.index(p["parameter"])] = p["r"]
        if params:
            title = "Validated correlations (q<0.05 or non-FAIL pairs; r values)"
            if truncated:
                title += f" — top {HEATMAP_MAX_PARAMS} of {len(all_params)} params shown"
            fig, ax = plt.subplots(figsize=(1.0 * len(params) + 3, 1.0 * len(targets) + 2))
            im = ax.imshow(mat, cmap="cividis", vmin=-1, vmax=1, aspect="auto")
            fig.colorbar(im, ax=ax)
            ax.set_xticks(range(len(params)), params, rotation=45, ha="right", fontsize=9)
            ax.set_yticks(range(len(targets)), targets, fontsize=9)
            for i in range(len(targets)):
                for j in range(len(params)):
                    if not np.isnan(mat[i, j]):
                        ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center", fontsize=7.5)
            ax.set_title(title)
            plots.append(_finalize({
                "file": _save(fig, out_dir, "correlation_heatmap.png"),
                "type": "correlation_heatmap", "title": title,
                "response": None}, out_dir))

    top = correlation.get("top_contributors", [])[:10]
    if top:
        fig, ax = plt.subplots(figsize=(7, 4))
        names = [f"{t['factor']}" for t in top]
        vals = [t["delta_r2"] for t in top]
        ax.barh(names[::-1], vals[::-1], color="#1e3a54")
        ax.set_title("Leave-one-factor-out ΔR² contribution")
        ax.set_xlabel("ΔR²")
        plots.append(_finalize({
            "file": _save(fig, out_dir, "contribution_bar.png"),
            "type": "contribution_bar", "title": "ΔR² contribution ranking",
            "response": top[0]["response"]}, out_dir))

    segments = stability.get("steady_segments", [])
    cps = {c["response"]: c["positions"] for c in stability.get("change_points", [])}
    # timeline for up to 2 responses present in df
    seen = []
    for p in pairs:
        if p["target"] not in seen:
            seen.append(p["target"])
    for resp in seen[:2]:
        if resp not in df.columns:
            continue
        y = pd.to_numeric(df[resp], errors="coerce").to_numpy(dtype=float)
        stride = 1
        if len(y) > TIMELINE_MAX_POINTS:
            stride = int(math.ceil(len(y) / TIMELINE_MAX_POINTS))
        title = f"Stability timeline — {resp} (green: steady, dashed: change points)"
        if stride > 1:
            title += f" — downsampled 1/{stride} ({int(math.ceil(len(y) / stride))} pts)"
        fig, ax = plt.subplots(figsize=(11, 3.5))
        ax.plot(np.arange(0, len(y), stride), y[::stride], color="#1e3a54", linewidth=0.7)
        for seg in segments:
            ax.axvspan(seg["start"], seg["end"], color="#2d7d4f", alpha=0.12)
        for cp in cps.get(resp, []):
            ax.axvline(cp, color="#c2673a", linewidth=1, linestyle="--")
        ax.set_title(title)
        plots.append(_finalize({
            "file": _save(fig, out_dir, f"timeline_{_safe(resp)}.png"),
            "type": "stability_timeline", "title": title,
            "response": resp}, out_dir))

    if segments and seen:
        resp = seen[0]
        segs = [s for s in segments if s["start"] < len(df)]
        if segs:
            fig, ax = plt.subplots(figsize=(7, 4))
            means = [df.iloc[s["start"]:s["end"] + 1][resp].astype(float).mean()
                     for s in segs]
            stds = [df.iloc[s["start"]:s["end"] + 1][resp].astype(float).std()
                    for s in segs]
            labels = [f"seg{s['start']}-{s['end']}" for s in segs]
            ax.bar(labels, means, yerr=stds, capsize=3,
                   color=["#2d7d4f" if s.get("selected_for_windows") else "#8a8a8a"
                          for s in segs])
            ax.set_title(f"Steady-segment comparison — {resp} (green = selected for windows)")
            plt.setp(ax.get_xticklabels(), rotation=30, ha="right", fontsize=8)
            plots.append(_finalize({
                "file": _save(fig, out_dir, f"segments_{_safe(resp)}.png"),
                "type": "segment_comparison", "title": f"Steady-segment comparison — {resp}",
                "response": resp}, out_dir))
    return plots
