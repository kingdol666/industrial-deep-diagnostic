# Method Notes — E-1H 公式、口径与失败模式（文献告诫落点）

> 口径钉死（doe-analyzer v1.1 先例）：本文件是特征公式的唯一权威；改公式必须先改这里再改代码。
> 文献依据见 `.omc/plans/hetero-data-preprocessing-skill-v1-appendix-prior-art.md`。

## 1. 公式与口径

| 特征 | 公式 | 最少输入 | 单位口径 |
|---|---|---|---|
| MEAN/STD | 有限值均值 / `ddof=1` 标准差 | STD≥2 | 源单位 |
| P05/P50/P95 | numpy.percentile 线性插值 | ≥1 | 源单位 |
| MAD | `median(|x−median|)`（**不带** 1.4826 因子） | ≥1 | 源单位 |
| IQR | P75−P25 | ≥1 | 源单位 |
| SLOPE-LSQ-PER100 | `polyfit(x,·,1)` 斜率 × `100/(n−1)`，x=0..n−1（位置序） | ≥3 | 源单位/100 位置 |
| CURV-LSQ | `polyfit(x,·,2)` 二次项系数 | ≥4 | 源单位/位置² |
| ZONE-<a>-<b>-MEAN | 等宽分区均值（默认三等分） | 每区 ≥1 | 源单位 |
| EDGE-L/R-DEV | 外侧 10% 带均值 − 中心带均值（带宽 `max(1, round(n*0.1))`，要求 n≥6） | ≥6 | 源单位 |
| ARGDEV-NBR / DEV-POS\<i\> | `x[i] − mean(相邻有限位)`；取绝对值最大者 | 相邻 ≥1 | 源单位 |
| SHIFT-EST | 对基线模板（in-control 均值剖面）的部分重叠互相关，整数位偏移；要求重叠 ≥max(3, n/3) | 基线 ≥3 | 位置数（右移为正） |
| HOTAREA-P90 / COLDAREA-P10 | 超过 `median+3·MAD` / 低于 `median−3·MAD` 的像元占比 | 栅格 ≥6×6 | 比例 |
| GRAD-P95 | 前向差分（finite difference，非 Sobel）梯度幅值 P95 / 栅格间距 | ≥30 点 | 源单位/格 |
| ENTROPY | 64-bin 灰度直方图 Shannon 熵 | 1 图 | bit |
| FOCUS | Laplacian（`[[0,1,0],[1,-4,1],[0,1,0]]`）响应方差（**ddof=0**，总体方差） | 1 图 | — |
| 事件窗列 | `EVT-<SLUG>` ∈ {0,1}：`event_ts ≤ t < event_ts + event_window_s`（**只向前**） | — | — |

- `evidence_level`：直接统计自保留源 ⇒ L1（`evidence_level_basis` 注明"derived from retained source"）；
  几何解释类（EDGE/ZONE/CENTROID/SHIFT…）物理含义 ⇒ 本体侧 `INFERRED`（数值仍是 L1 溯源）。
  LLM/VLM 产物 ⇒ 证据等级 ≤L5 且 `model_derived=true`（禁入 DETERMINED 主证据链）。
- `stats_eligible` 判据：anchor 行非空覆盖 ≥0.5（R2 教训：<50% 的列会被 `core_stats` 静默丢弃）。

## 2. 失败模式与守卫（文献告诫 → 代码化）

| 告诫（出处见附录） | 落地的守卫 |
|---|---|
| E-1 的 `_normalize_cn_datetime` 丢时分秒但 `_parses_as_time` 报 1.0（R4 实测） | E-1H 自带显式格式清单解析；**H6b**：节奏 <24h 的源必须出现非午夜时分秒 |
| 剖面横向偏移会被读成形状变化（J. Process Control 2011） | `SHIFT-EST` 单独成列并随 manifest 报告；解释 EDGE 变化前先看 SHIFT |
| N 个位置当独立变量 → 荒谬报警（QREI 2013） | E-1H 把剖面折叠成少量命名特征；`pos_*` 原列进 `explicit_cols.excludes` |
| 图像光照/相机漂移误报（MIA 2014） | M1 整图质量向量（SATFRAC/DARKFRAC/FOCUS）随特征同行输出；M2 参考帧差 + SHIFT-X/Y 配准 |
| 交接班文本有整点周期混杂（附录 §A7） | `hour_of_day`/`shift_bucket` 协变量列；解释时作为显式协变量 |
| ZOH 冒充会制造虚假平坦段，污染时滞分析 | 陈旧度上限外一律 NaN；`merge_asof(backward)`；禁 forward-fill（manifest 固定 `"forward_fill":"none"`） |
| "可溯源 ≠ 正确"（红队 F6） | 夹具断言**幅值与变点**（如 EDGE-R-DEV ∈[0.6%,1.0%]），不只是 sha256 追踪 |
| 窄多指标表被"量级相近"回退误判成剖面（2026-10-17 BOPET 实测：LIMS 8 项指标生成 18 个伪特征） | 宽表回退增加**相邻列时序相干性**门槛（median adjacent r ≥ 0.25）：同一物理量沿位置扫描时相邻测点随工况同向变化，互不相关指标表不满足；位置命名命中 `pos_*` 的宽表不受此门槛影响 |

## 3. 质量门禁 H1–H8 速查

| 门禁 | 检查 | 失败即 |
|---|---|---|
| H1/H1b | 3 schema 过 `validate.mjs` + **严格 extra-keys** | exit 3 |
| H2 | joined 行数/行序 == anchor；HX 列只在表尾（前缀不变 ⇒ `schema_fp` 不变） | exit 3 |
| H3 | `n_inputs>0`；`source_sha256` 回算；`_src_ts ≤ ts` | exit 3 |
| H4 | `coverage<0.3 ⇒ sparse`；`stats_eligible ⇒ coverage≥0.5` | exit 3 |
| H5 | 零网络/零 LLM 静态扫描；`zero_llm` 标志 | exit 3 |
| H6/H6b | ts ISO 格式；子日节奏源必须非全午夜 | exit 3 |
| H7 | E-1 四文件 sha 不变；写入只落 `07_hetero/**` + 白名单 | exit 3 |
| H8 | 列名正则/长度；slug 单射；禁 merged/joined/_2 词根 | exit 3 |

退出码：`0` ok｜`2` undetermined（marker 缺失=阶段没跑，finalize 会抓）｜`3` gate-fail｜`1` 硬错误。
