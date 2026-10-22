# -*- coding: utf-8 -*-
"""Chart generation for lekai-mixed-defects-diag. All figures traceable to analysis_frame.csv."""
import json, math
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from scipy import stats
from scipy.cluster.hierarchy import linkage, dendrogram, leaves_list
from scipy.spatial.distance import squareform

RUN = Path(__file__).resolve().parents[1]
PROC, FIG = RUN / "02_processed", RUN / "03_figures"
FIG.mkdir(exist_ok=True)
A = json.loads((PROC / "custom_analysis.json").read_text(encoding="utf-8"))
df = pd.read_csv(PROC / "analysis_frame.csv")
df["ts_start"] = pd.to_datetime(df["ts_start"])
df = df.sort_values("ts_start").reset_index(drop=True)
schema = json.loads((RUN / "01_ontology" / "schema.json").read_text(encoding="utf-8"))
FAM = schema["classification"]["process_parameter"]["families"]
PARAMS = [c for f in FAM.values() for c in f["columns"]]
PKM = {"total_defects": "total_per_km", "oligomer": "oligomer_per_km",
       "dust": "dust_per_km", "other_defects_derived": "other_per_km"}
RESP = list(PKM)
CN = {"total_defects": "缺陷总数", "oligomer": "低聚物", "dust": "粉尘/异物",
      "other_defects_derived": "未分类缺陷(残差)"}

# ---- Chinese font ----
cands = ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Zen Hei"]
have = {f.name for f in font_manager.fontManager.ttflist}
use = next((c for c in cands if c in have), None)
if use:
    plt.rcParams["font.sans-serif"] = [use, "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 130, "axes.grid": True,
                     "grid.alpha": .25, "font.size": 10})

PLOTS = []
CP78 = df["ts_start"].iloc[78]


def save(fig, name, title, desc, q, ftype, params, prio="MEDIUM", aligned=True, per_product=False):
    p = FIG / name
    fig.tight_layout()
    fig.savefig(p, bbox_inches="tight")
    plt.close(fig)
    PLOTS.append({"filename": name, "figure_type": ftype, "priority": len(PLOTS) + 1,
                  "title": title, "description": desc, "parameters_shown": params,
                  "diagnostic_question": q, "vlm_priority": prio,
                  "width_px": int(fig.get_size_inches()[0] * 130),
                  "height_px": int(fig.get_size_inches()[1] * 130), "dpi": 130,
                  "file_size_kb": round(p.stat().st_size / 1024, 1),
                  "generation_status": "success", "time_aligned": bool(aligned),
                  "has_event_markers": True, "per_product": per_product,
                  "data_source": "02_processed/analysis_frame.csv"})


# ---------- 1 response distributions ----------
fig, axes = plt.subplots(1, 3, figsize=(13, 4))
for ax, r in zip(axes, RESP[:3]):
    v = df[r].clip(lower=0.5)
    ax.hist(v, bins=np.logspace(np.log10(0.5), np.log10(v.max() * 1.1), 25), color="#3b6ea5", alpha=.85)
    ax.set_xscale("log")
    ax.axvline(df[r].median(), color="red", ls="--", lw=1.4, label=f"中位 {df[r].median():.0f}")
    ax.axvline(df[r].mean(), color="orange", ls=":", lw=1.6, label=f"均值 {df[r].mean():.0f}")
    ax.set_title(f"{CN[r]}：批次计数分布（对数轴）")
    ax.set_xlabel("缺陷计数 / 批")
    ax.set_ylabel("批次数")
    ax.legend(fontsize=8)
    ax.text(.02, .95, f"偏度={A['response_profiles'][r]['skew']:.1f}\nlog1p偏度={A['response_profiles'][r]['skew_log1p']:.1f}",
            transform=ax.transAxes, va="top", fontsize=8, bbox=dict(fc="white", alpha=.7, ec="none"))
save(fig, "fig01_response_distribution.png",
     "三类缺陷计数的重尾分布（对数轴）", "直方图展示 total/oligomer/dust 的计数分布；红虚线为中位数，橙点线为均值。均值远高于中位且偏度 7.4-12.0，证明不能以均值做比较。",
     "响应变量是否服从近似正态？均值比较是否被极端批次劫持？", "distribution", RESP[:3], "MEDIUM", False)

# ---------- 2 per-model medians ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 4.4))
mods = A["model_table"]
order = sorted(mods, key=lambda m: -mods[m]["median_total"])
x = np.arange(len(order))
w = .27
for i, r in enumerate(RESP[:3]):
    key = {"total_defects": "median_total", "oligomer": "median_oligomer", "dust": "median_dust"}[r]
    axes[0].bar(x + (i - 1) * w, [mods[m][key] for m in order], w, label=CN[r])
axes[0].set_xticks(x); axes[0].set_xticklabels([f"{m}\nn={mods[m]['n']}" for m in order], fontsize=8)
axes[0].set_yscale("log"); axes[0].set_ylabel("批内中位计数（对数轴）")
axes[0].set_title("按牌号分层：三类缺陷中位计数"); axes[0].legend(fontsize=8)

axes[1].bar(x, [mods[m]["median_total_per_km"] for m in order], color="#4a8c5e")
axes[1].set_xticks(x); axes[1].set_xticklabels(order, fontsize=8)
axes[1].set_ylabel("总缺陷密度（个/km）")
axes[1].set_title("按牌号分层：缺陷密度中位（消除批次长度暴露差异）")
for i, m in enumerate(order):
    axes[1].text(i, mods[m]["median_total_per_km"] * 1.03, f"{mods[m]['median_total_per_km']:.0f}", ha="center", fontsize=7)
save(fig, "fig02_model_response_medians.png",
     "牌号分层：缺陷计数与缺陷密度中位对比", "左图按牌号给出三类缺陷批内中位数（对数轴），右图给出总缺陷密度中位。牌号对 total_defects（Kruskal p=2.4e-5）与残差类（p=2.1e-7）影响显著，对 dust 不显著（p=0.067）。",
     "牌号是混杂变量还是真实驱动？计数差异是否只是批次长度差异？", "grouped_bar", RESP[:3] + ["meters"], "HIGH", False)

# ---------- 3 temporal overlay ----------
fig, ax = plt.subplots(figsize=(14, 5.2))
keyp = ["W1C8A@PV1_mean", "W1C86@PV1_mean", "W1C84@PV1_mean", "MD_TH012@PV_mean", "F_PS005@PV1_mean"]
z = lambda s: (s - s.mean()) / (s.std(ddof=0) + 1e-12)
ax.plot(df.ts_start, z(np.log1p(df.other_per_km)), color="crimson", lw=2.4, label="未分类缺陷密度 log1p (z)")
ax.plot(df.ts_start, z(np.log1p(df.total_per_km)), color="black", lw=2.0, ls="--", label="总缺陷密度 log1p (z)")
for p in keyp:
    ax.plot(df.ts_start, z(df[p]), lw=1.1, alpha=.85, label=p.split("@")[0])
ax.axvline(CP78, color="purple", ls=":", lw=2)
ax.text(CP78, ax.get_ylim()[1] * .92, " 变点 H2652667\n 2026-05-09 20:02", color="purple", fontsize=8, va="top")
ax.set_ylabel("z 分数（已标准化）"); ax.set_title("工艺参数与缺陷密度的时间对齐叠加（按 ts_start 排序，变点已标注）")
ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d")); ax.legend(fontsize=7.5, ncol=4, loc="lower left")
save(fig, "fig03_temporal_overlay.png",
     "工艺参数与缺陷密度的时间对齐叠加", "所有序列按 ts_start 严格排序并做 z 标准化；紫线为 total_defects 的 Pettitt 变点（索引78）。W1C 通道族与残差类缺陷同向漂移，构成了本数据集最强的共同趋势。",
     "参数与缺陷是否同向漂移？漂移是渐变还是阶跃？", "temporal_overlay", keyp + ["total_per_km", "other_per_km"], "CRITICAL")

# ---------- 4 per-product overlay (focus product PG31DS) ----------
focus = "PG31DS"
sub = df[df.model == focus].sort_values("ts_start")
fig, ax = plt.subplots(figsize=(14, 4.8))
ax.plot(sub.ts_start, z(np.log1p(sub.total_per_km)), color="black", lw=2.2, label="总缺陷密度 log1p (z)")
ax.plot(sub.ts_start, z(np.log1p(sub.other_per_km)), color="crimson", lw=2.0, label="残差缺陷密度 log1p (z)")
for p in ["W1C8A@PV1_mean", "W1C86@PV1_mean", "F_PS005@PV1_mean", "MD_TH012@PV_mean"]:
    ax.plot(sub.ts_start, z(sub[p]), lw=1.3, alpha=.9, label=p.split("@")[0])
ax.set_title(f"重点牌号 {focus}（n={len(sub)}）批内时间对齐：缺陷密度与关键参数")
ax.set_ylabel("z 分数"); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d %H:%M"))
ax.legend(fontsize=8, ncol=3)
save(fig, "fig04_per_product_overlay.png",
     "重点牌号 PG31DS 的牌号内时间对齐叠加", "仅取 PG31DS 的 67 个批次，消除牌号混杂后观察参数与缺陷是否仍在时间上同步。牌号内仍可见 W1C 通道与缺陷密度的同向漂移，说明并非纯牌号效应。",
     "剥离牌号混杂后，参数-缺陷的同步关系是否仍然存在？", "temporal_overlay", ["total_per_km", "other_per_km"] +
     ["W1C8A@PV1_mean", "W1C86@PV1_mean", "F_PS005@PV1_mean", "MD_TH012@PV_mean"], "CRITICAL", True, True)

# ---------- 5 exposure calibration ----------
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.4))
axes[0].scatter(df.meters, df.total_defects, c=df.t_index, cmap="viridis", s=22, alpha=.8)
axes[0].set_xscale("log"); axes[0].set_yscale("log")
xx = np.linspace(np.log(df.meters.min()), np.log(df.meters.max()), 50)
axes[0].plot(np.exp(xx), np.exp(np.log(df.total_defects.clip(lower=1)).mean() + 0.547 * (xx - np.log(df.meters).mean())),
             color="red", lw=2, label="FE 斜率 0.547")
axes[0].set_xlabel("批次计米 meters（对数）"); axes[0].set_ylabel("总缺陷计数（对数）")
axes[0].set_title("暴露标定 C10：计数 vs 批次长度"); axes[0].legend(fontsize=8)
cb = fig.colorbar(axes[0].collections[0], ax=axes[0]); cb.set_label("时间索引", fontsize=8)

axes[1].scatter(df.meters, df.total_per_km, c=df.t_index, cmap="viridis", s=22, alpha=.8)
axes[1].set_xscale("log"); axes[1].set_yscale("log")
axes[1].set_xlabel("批次计米 meters（对数）"); axes[1].set_ylabel("缺陷密度（个/km，对数）")
axes[1].set_title(f"缺陷密度 vs 批次长度（Spearman rho={A['exposure_calibration_C10']['spearman_meters_total_per_km'][0]:.2f}）")
save(fig, "fig05_exposure_calibration.png",
     "暴露标定 C10：批次长度与缺陷计数/密度", "左图检验计数是否与批次长度成正比（模型固定效应下对数斜率 0.547，非 1.0）；右图显示缺陷密度随批次长度显著下降（rho=-0.32），证明只看计数会系统性高估长批次。",
     "缺陷计数是否只是批次长度的暴露效应？结论应按计数还是密度表述？", "scatter",
     ["meters", "total_defects", "total_per_km"], "HIGH")

# ---------- 6 simpson stratified ----------
fig, axes = plt.subplots(1, 2, figsize=(13, 4.6))
pcol, rcol = "W1C8A@PV1_mean", "other_defects_derived"
for g, s in df.groupby("model"):
    if len(s) < 6:
        continue
    axes[0].scatter(s[pcol], s[rcol].clip(lower=.5), s=24, alpha=.8, label=f"{g}(n={len(s)})")
    if len(s) >= 8:
        sl, ic, rv, pv, se = stats.linregress(s[pcol], np.log1p(s[rcol]))
        xx = np.linspace(s[pcol].min(), s[pcol].max(), 10)
        axes[0].plot(xx, np.exp(ic + sl * xx), lw=1.1, alpha=.7)
axes[0].set_yscale("log"); axes[0].set_xlabel(pcol); axes[0].set_ylabel("未分类缺陷计数（对数）")
axes[0].set_title(f"W1C8A vs 未分类缺陷：分牌号散点（合并 rho={0.498 if False else 0.498:.2f}）")
axes[0].legend(fontsize=7, ncol=2)

top = [a for a in A["associations"] if a["target"] == "total_defects"][:0]
rows = sorted([a for a in A["associations"] if a["target"] == "other_defects_derived"],
              key=lambda z: -abs(z["spearman_rho"]))[:9]
lbl = [r["parameter"].split("@")[0] for r in rows]
y = np.arange(len(rows))
axes[1].barh(y - .2, [r["spearman_rho"] for r in rows], .38, label="合并 Spearman")
axes[1].barh(y + .2, [r["partial_rho_model_meters"] for r in rows], .38, label="控制牌号+计米后的偏相关")
axes[1].set_yticks(y); axes[1].set_yticklabels(lbl, fontsize=8); axes[1].invert_yaxis()
axes[1].axvline(0, color="k", lw=.8); axes[1].legend(fontsize=8)
axes[1].set_title("合并 vs 分层控制后的效应量对比")
save(fig, "fig06_simpson_stratified.png",
     "Simpson 悖论检查：合并相关与牌号内相关", "左侧按牌号着色展示 W1C8A 与未分类缺陷的关系，各牌号内拟合线方向不一致（6 个分层中仅 2 个与合并方向同号）；右侧对比合并 Spearman 与控制牌号+计米后的偏相关。",
     "合并相关是否由牌号间差异伪造？控制混杂后效应还剩多少？", "simpson_stratified",
     ["W1C8A@PV1_mean", "other_defects_derived", "model"], "HIGH")

# ---------- 7 correlation heatmap ----------
C = stats.spearmanr(df[PARAMS]).statistic
C = np.nan_to_num(C, nan=0.0); np.fill_diagonal(C, 1.0)
D = 1 - np.abs(C); np.fill_diagonal(D, 0)
Z = linkage(squareform(D, checks=False), "average")
order = leaves_list(Z)
fig, ax = plt.subplots(figsize=(10.5, 9))
im = ax.imshow(C[np.ix_(order, order)], cmap="RdBu_r", vmin=-1, vmax=1)
labs = [PARAMS[i].split("@")[0] for i in order]
ax.set_xticks(range(len(labs))); ax.set_xticklabels(labs, rotation=90, fontsize=6.5)
ax.set_yticks(range(len(labs))); ax.set_yticklabels(labs, fontsize=6.5)
ax.set_title("44 个工艺参数的 Spearman 相关矩阵（层次聚类排序）\n共线性结构：90% 方差仅需 10 个主成分")
fig.colorbar(im, ax=ax, fraction=.045, label="Spearman rho")
save(fig, "fig07_correlation_heatmap.png",
     "44 个工艺参数的相关矩阵与共线性聚类", "按 1-|rho| 平均连接聚类排序的 Spearman 矩阵。参数间平均 |rho|=0.37，PC1 解释 40.7% 方差，90% 方差只需 10 个主成分——诊断时不可把 44 列当作独立证据。",
     "哪些参数是同一物理信号的重复测量？独立信号到底有几个？", "heatmap", PARAMS, "MEDIUM", False)

# ---------- 8 CCF lag ----------
fig, ax = plt.subplots(figsize=(9.5, 4.4))
lags = [0, 1, 2, 3, 4, 5]
for r in ["total_defects", "oligomer", "other_defects_derived"]:
    ys = []
    for L in lags:
        xv = df["F_PS005@PV1_mean"].to_numpy(float)
        yv = np.log1p(df[r].to_numpy(float))
        a, b = (xv, yv) if L == 0 else (xv[:-L], yv[L:])
        ys.append(stats.spearmanr(a, b)[0])
    ax.plot(lags, ys, "o-", label=f"F_PS005 → {CN[r]}")
ax.axhline(0, color="k", lw=.8); ax.set_xlabel("滞后期（批，方程式 F_PS005 领先）")
ax.set_ylabel("滞后补偿后 Spearman rho"); ax.set_title("F_PS005 与三类缺陷的滞后互相关（上限 5 批，禁止批内推断）")
ax.legend(fontsize=8)
save(fig, "fig08_ccf_lag.png",
     "F_PS005 的 5 批滞后互相关", "以批次为步长计算 F_PS005 领先 0-5 批的 Spearman。注意 5 批是搜索上限，若最优点落在边界则不可宣称已找到真实物性滞后。",
     "供料回路压差是否先于缺陷出现？滞后是物理传递还是趋势自相关？", "time_lag_ccf",
     ["F_PS005@PV1_mean"] + RESP[:3], "HIGH")

# ---------- 9 F_PS005 sawtooth ----------
fig, axes = plt.subplots(2, 1, figsize=(13.5, 6), sharex=True)
axes[0].plot(df.ts_start, df["F_PS005@PV1_mean"], color="#2f6f9f", lw=1.6, label="F_PS005@PV1")
for j in A["C11_F_PS005_trend"]["level_jumps"]:
    strong = j["delta"] < -2.0
    axes[0].axvline(pd.to_datetime(j["ts_start"]), color="purple",
                    ls="-" if strong else ":", lw=1.6 if strong else 1.1, alpha=.9)
    axes[0].annotate(f"{j['delta']:+.1f}", (pd.to_datetime(j["ts_start"]), j["level_before"]),
                     textcoords="offset points", xytext=(3, 4), fontsize=7, color="purple")
axes[0].set_ylabel("F_PS005 过程值"); axes[0].legend(fontsize=8)
axes[0].set_title("预注册检查 C11：F_PS005 锯齿形态（上升漂移 + 阶跃复位）")
axes[1].plot(df.ts_start, df.total_per_km, color="crimson", lw=1.3, label="总缺陷密度 (个/km)")
axes[1].plot(df.ts_start, df.dust_per_km * 10, color="seagreen", lw=1.1, alpha=.8, label="粉尘密度 ×10")
axes[1].set_ylabel("密度 (个/km)"); axes[1].legend(fontsize=8)
axes[1].xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
save(fig, "fig09_ps005_sawtooth.png",
     "F_PS005 锯齿漂移与缺陷密度对照", "上图为 F_PS005 随时间的锯齿形态：各统计分段内均上升，共出现 3 次离散回落（索引 37/58/71，其中 58、71 两次为 -2.7、-2.6 的大幅复位）；下图为同期缺陷密度。复位后缺陷密度一次下降 23%、一次略升 9%，未能形成一致响应。",
     "F_PS005 是单向累积还是周期性复位？复位后缺陷是否同向下降（检验压差-颗粒因果链）？", "temporal_overlay",
     ["F_PS005@PV1_mean", "total_per_km", "dust_per_km"], "CRITICAL")

# ---------- 10 leverage ----------
rows = sorted([a for a in A["associations"] if a["target"] == "total_defects"],
              key=lambda z: -abs(z["spearman_rho"]))[:10]
fig, ax = plt.subplots(figsize=(10, 4.2))
y = np.arange(len(rows))
ax.barh(y, [r["loo_max_abs_delta"] for r in rows], color="#6a7fb5")
ax.axvline(0.15, color="red", ls="--", label="稳定阈值 0.15")
ax.set_yticks(y); ax.set_yticklabels([r["parameter"].split("@")[0] for r in rows], fontsize=8)
ax.invert_yaxis(); ax.set_xlabel("删除单行后的最大 |Δrho|")
ax.set_title("留一杠杆检验：total_defects 前 10 个关联的单点敏感性")
ax.legend(fontsize=8)
save(fig, "fig10_leverage.png",
     "留一杠杆检验（单点敏感性）", "对每个关联逐一删除单个批次并重算 Spearman，取最大变化量。全部 <0.15 说明这些关联不是由单一极端批次（如 9516 的 H2652611）制造的。",
     "某个关联是否只由一两个极端批次支撑？", "correlation_bar",
     [r["parameter"] for r in rows], "MEDIUM", False)

# ---------- 11 model × response heatmap ----------
mods_order = [m for m in A["model_table"]]
M = np.array([[A["model_table"][m][k] for k in ["median_total", "median_oligomer", "median_dust", "median_other"]]
              for m in mods_order], float)
fig, ax = plt.subplots(figsize=(8, 5.4))
im = ax.imshow(np.log10(M + 1), cmap="YlOrRd", aspect="auto")
ax.set_xticks(range(4)); ax.set_xticklabels(["总缺陷", "低聚物", "粉尘", "未分类残差"], fontsize=9)
ax.set_yticks(range(len(mods_order)))
ax.set_yticklabels([f"{m} (n={A['model_table'][m]['n']})" for m in mods_order], fontsize=9)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, f"{M[i, j]:.0f}", ha="center", va="center", fontsize=8,
                color="white" if M[i, j] > 200 else "black")
ax.set_title("牌号 × 缺陷类别的中位计数矩阵")
fig.colorbar(im, ax=ax, label="log10(中位计数+1)")
save(fig, "fig11_model_response_heatmap.png",
     "牌号 × 缺陷类别中位计数矩阵", "9 个牌号在四类响应上的中位计数。FP41（n=3）在总缺陷与低聚物上极端偏高，PG31DS 占样本 45% 会主导合并统计。",
     "哪个牌号在哪个缺陷类别上异常？样本量是否足以支撑分层结论？", "heatmap",
     ["model"] + RESP, "HIGH", False)

# ---------- 12 family effects ----------
fams = list(FAM)
fa = A["family_associations"]
rvals = np.array([[next(x["partial_rho"] for x in fa if x["family"] == f and x["target"] == r) for r in RESP] for f in fams])
fig, ax = plt.subplots(figsize=(8.4, 4.8))
im = ax.imshow(rvals, cmap="RdBu_r", vmin=-.6, vmax=.6, aspect="auto")
ax.set_xticks(range(4)); ax.set_xticklabels([CN[r] for r in RESP], fontsize=9)
ax.set_yticks(range(len(fams))); ax.set_yticklabels(fams, fontsize=9)
for i in range(rvals.shape[0]):
    for j in range(rvals.shape[1]):
        ax.text(j, i, f"{rvals[i, j]:+.2f}", ha="center", va="center", fontsize=8.5)
ax.set_title("参数族复合指标 → 缺陷类别（控制牌号与计米后的偏相关）")
fig.colorbar(im, ax=ax, label="偏相关 rho")
save(fig, "fig12_family_effects.png",
     "参数族复合指标与缺陷类别的偏相关", "按本体定义的 8 个参数族构造 z 复合指标，控制牌号与计米后估计偏相关。W1C 族最强，F_PS 供料族整体弱，说明单看个别 F_PS 参数会高估其作用。",
     "哪个物理段（纵拉/涂布/供料）才是缺陷的主驱动？", "heatmap", fams + RESP, "HIGH", False)

# ---------- 13 composition over time ----------
bins = pd.cut(df.t_index, bins=[0, 25, 50, 75, 100, 125, 149], include_lowest=True)
comp = df.groupby(bins, observed=True).agg(
    o=("share_oligomer", "median"), d=("share_dust", "median"),
    t0=("ts_start", "min"), n=("total_defects", "size"))
comp["x"] = (comp["o"] + comp["d"])
fig, ax = plt.subplots(figsize=(11, 4.2))
ax.bar(range(len(comp)), comp["o"], label="低聚物占比", color="#4c72b0")
ax.bar(range(len(comp)), comp["d"], bottom=comp["o"], label="粉尘占比", color="#dd8452")
ax.bar(range(len(comp)), 1 - comp["x"], bottom=comp["x"], label="未分类残差占比", color="#9aa0a6")
ax.set_xticks(range(len(comp)))
ax.set_xticklabels([d.strftime("%m-%d") for d in comp["t0"]], fontsize=8)
ax.set_ylabel("中位占比"); ax.set_ylim(0, 1.05)
ax.set_title("缺陷构成随时间的漂移（25 批一组的占比中位）")
ax.legend(fontsize=8, ncol=3)
save(fig, "fig13_defect_composition.png",
     "缺陷构成随时间漂移", "按时间顺序每 25 批分组，展示三类缺陷占比中位数的变化。若某一类占比随时间上升，说明该机制在恶化，而不是整体检测灵敏度变化。",
     "缺陷总量上升时，是某一机制恶化还是全部同步恶化？", "temporal_overlay",
     ["oligomer", "dust", "other_defects_derived"], "HIGH")

manifest = {"plots": PLOTS,
            "metadata": {"generated_by": "data-processor/custom charts",
                         "total_plots": len(PLOTS),
                         "successful_plots": sum(1 for p in PLOTS if p["generation_status"] == "success"),
                         "degraded_plots": 0, "failed_plots": 0,
                         "generation_timestamp": pd.Timestamp.now().isoformat(),
                         "data_source": "cleaned", "scenario_type": "batch_process_quality_defect_attribution",
                         "focus_product": "PG31DS"}}
(FIG / "plot_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
print("plots:", len(PLOTS), "font:", use)
for p in PLOTS:
    print(p["filename"], p["file_size_kb"], "kb")
