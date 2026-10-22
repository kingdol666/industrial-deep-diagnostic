# 数据分析报告 — run（乐凯膜产线 · 混线批次级 DOE 条件分析）

> 由 industrial-doe-analyzer 生成 · 分析模式 observational · 设计类型 observational ·
> 证据等级 B · 下游合同 recommendations.json v1.0
>
> 数据：149 个批次（batch 级聚合）× 44 个过程量批次均值 · 9 个产品型号混线 ·
> 响应 total_defects（minimize，weight 1.5）与 oligomer（minimize）· 分组列 model（分层核验开启）·
> 时间跨度 2026-05-04 14:42:00 .. 2026-05-13 14:26:00

---

## 一、10 秒结论卡

| 项 | 值 |
|---|---|
| 关键因子（按效应强度） | **无可信因子**。全表 88 对相关最大 \|r\|=0.2422（F_PS005@PV1_mean，且为 FAIL）；ΔR² 前两名 W1C40（0.023132）/W1C4B（0.021411）均为趋势混杂（CAUTION，去趋势后 r=0.0047/0.0006） |
| 推荐操作窗口数 | 0（其中 0 条需先做确认试验） |
| 预期收益（最优窗口） | 无——0 窗口，无可下发参数区间 |
| 证据等级 | B（观察性数据：无随机化、无纯误差项、无设计分辨力可评；anti_spurious_ok=true 但整体判定 SERIOUS_CONCERNS：serious_count=26） |
| 最重要的限制 | **混线未分层**：9 个型号缺陷基线差异悬殊（描述性中位数 35 ~ 4145），12 处 Simpson 分层方向翻转即由此产生——跨型号结论一律不可直接引用 |

**一句话结论**：**混线数据不能直接出结论，必须先按型号（必要时再按时间段）分层**——本运行 88 对相关中 12 对 FAIL、35 对趋势混杂 CAUTION、仅 41 对 PASS，8 对 q<0.05 中 6 对 FAIL；0 窗口的直接原因是合并稳态段仅 30 行、跨 6 个型号，分层三分位差（每层 ≥20 行）不可估。当前合同的正确用法是"分层复验 + 补单型号数据"，而不是取任何参数窗口。

---

## 二、1 分钟证据层

### 2.1 效应/相关排序

**多重检验（BH）**：2 个响应族 × 44 因子 = 88 次检验，q<0.05 显著 8 对（全部指向 total_defects）：

| 响应 | 因子 | r | p | q(BH) | 防伪判定 | 备注 |
|---|---|---|---|---|---|---|
| total_defects | F_PS005@PV1_mean | 0.2422 | 0.0029 | 0.033 | **FAIL** | 离群驱动 + Simpson 分层方向翻转 |
| total_defects | MD_TH012@PV_mean | -0.2407 | 0.0031 | 0.033 | **FAIL** | 离群驱动 + Simpson |
| total_defects | MD_TH013@PV_mean | -0.2247 | 0.0059 | 0.033 | **FAIL** | Simpson |
| total_defects | MD_TH014@PV_mean | -0.2246 | 0.0059 | 0.033 | PASS | 去趋势后 -0.2024 |
| total_defects | MD_TH015@PV_mean | -0.2241 | 0.0060 | 0.033 | PASS | 去趋势后 -0.2019 |
| total_defects | MD_TH016@PV_mean | -0.2352 | 0.0039 | 0.033 | **FAIL** | 离群驱动 + Simpson |
| total_defects | MD_TH017@PV_mean | -0.2358 | 0.0038 | 0.033 | **FAIL** | 离群驱动 + Simpson |
| total_defects | MD_TH018@PV_mean | -0.2358 | 0.0038 | 0.033 | **FAIL** | 离群驱动 + Simpson |

即：**显著的 8 对里 6 对被防伪判定否决**，剩下 2 对（MD_TH014/015）|r|≈0.22 且层间一致性未经验证。oligomer 侧无 q<0.05 的相关，其 MD_TH002/003/005/007/008/009 六对虽 p<0.05 但 FAIL（离群驱动或 Simpson）。

**ΔR² 贡献榜（total_defects）不可直接采信**：第 1、2 名 W1C40@PV1_mean（ΔR²=0.023132）、W1C4B@PV1_mean（ΔR²=0.021411）原始 r 仅 0.075/0.0725（p=0.3633/0.3796，CAUTION），去趋势后 r=0.0047/0.0006——贡献几乎全部来自与响应共享的时间趋势。全模型 r_full_model=0.334643（按 r² 折算联合解释方差约 11%，解读性推算），44 个过程量联合解释力不足。

**滞后不稳定**：88 对 lag_window_consistent 全部 false。例：W1C00@PV1_mean 原始 r=0.0186，最优滞后（lag=3）处 -0.2885，符号翻转。

**防伪判定总账**（anti_spurious_summary）：88 对中 PASS 41 / CAUTION 35 / FAIL 12；离群驱动（SERIOUS）8 对、Simpson 分层方向翻转 12 处、Spearman 分歧 6 处、趋势混杂（trend_confounded=true）35 对、fatal 0、serious_count 26，整体 **SERIOUS_CONCERNS**。

### 2.2 关键图

| 图 | 内容 | 墨水门 |
|---|---|---|
| `03_figures/correlation_heatmap.png` | 防伪复核后的相关矩阵（4 象限墨水比 58.3%） | PASS |
| `03_figures/contribution_bar.png` | ΔR² 贡献排序（33.5%） | PASS |
| `03_figures/timeline_total_defects.png` | total_defects 稳定性时间线（46.3%） | PASS |
| `03_figures/timeline_oligomer.png` | oligomer 稳定性时间线（46.2%） | PASS |
| `03_figures/segments_total_defects.png` | 稳态段对比（17.6%） | PASS |

5/5 图通过墨水门（G5）。时间线图直观可见：少数极端批次把均值拉离主体云团，稳态段 0-16 行（total_defects 均值 58.176471）与 84-148 行（均值 94.169231，未入选）水平差异明显。

### 2.3 稳定性/能力（观察档适用）

**能力（capability，均无规格限，Cp/Cpk/Pp/Ppk 不可算）**：

| 响应 | n | 均值 | 总体std | 组内σ(MR) | 偏度 | 超越峰度 | AD（5%临界 0.748） | 正态 | lag-1 自相关 | n_eff |
|---|---|---|---|---|---|---|---|---|---|---|
| total_defects | 149 | 204.791946 | 980.072793 | 287.497604 | 7.8311 | 63.9518 | 48.7257 | 否 | -0.0289 | 157 |
| oligomer | 149 | 29.087248 | 111.554067 | 40.306929 | 7.4388 | 61.8975 | 43.2871 | 否 | -0.0385 | 160 |

**工况划分**：steady 96 行（64.43%）/ marginal 32 行（21.48%）/ transition 21 行（14.09%）；变点 0、漂移旗 0。

**稳态段与 0 窗口的机制**：选中 3 段供建窗——行 0-16（17 行，total_defects 均值 58.176471）、行 49-51（3 行，均值 32.333333）、行 53-62（10 行，均值 65.1）；行 84-148（65 行，均值 94.169231）未入选。**合并仅 30 行，横跨 6 个型号（FP21=5、PG31DS=5、PG32B=8、PG32D=3、PG32DS=7、PG32M=2）**。分层核验（group_col=model）要求每个型号层 ≥20 行才能估计分层三分位 Welch 差值，最大层仅 8 行 → 全部候选窗口不可估 → `operating_windows=[]`、`confirmations=0`。这是结构性不足，不是计算遗漏。

**型号间差异（00_input/batches.csv 描述性汇总，未计入证据等级）**：

| 型号 | 批数 | total_defects 均值 | 中位数 | 最大值 | oligomer 均值 |
|---|---|---|---|---|---|
| FP41 | 3 | 3502.67 | 4145.0 | 6236.0 | 180.00 |
| FG22 | 6 | 1608.33 | 35.0 | 9516.0 | 187.67 |
| FP21 | 19 | 94.11 | 53.0 | 616.0 | 47.37 |
| PG31DS | 67 | 89.46 | 66.0 | 512.0 | 20.00 |
| PG32D | 16 | 70.56 | 56.0 | 264.0 | 10.88 |
| PG32B | 10 | 41.20 | 36.5 | 99.0 | 8.40 |
| PG22C | 6 | 39.33 | 37.5 | 61.0 | 5.50 |
| PG32DS | 9 | 38.78 | 33.0 | 78.0 | 6.22 |
| PG32M | 13 | 34.46 | 35.0 | 70.0 | 6.23 |

中位数从 PG32M 的 35 到 FP41 的 4145：FP41 是整条线水平性偏高，FG22 则是"中位数正常 + 单批 9516（H2652611，2026-05-07，同批 oligomer=1105）"的极端批次型。全表均值 204.791946 vs 中位数 51、total_defects>1000 仅 3 批——少数型号层 + 少数极端批次共同制造了离群驱动（8 对）与 Simpson 翻转（12 处）。**这就是"混线数据必须先分层"的数据依据。**

---

## 三、深读审计层

### 3.1 模型与检验细节

- 模式判定：observational（连续/混合因子，LHS 占用率仅 0.14，无设计实验签名）；无 mode_override。
- 检验族：BH 校正，2 族 88 检验，显著 8；effect_size_threshold=0.01，max_lag=5。
- 每对相关的复核维度：最优滞后、去趋势 r、trend_confounded、离群敏感性（留一/杠杆）、分层方向（Simpson）；evidence_level 全部 L4（图表/统计级）。
- grade_checklist：randomization_ok / pure_error_df_gt0 / resolution_ok / balanced 均为 null（观察档不适用），anti_spurious_ok=true（判定在但结论为 SERIOUS_CONCERNS，故等级停留在清单计算的 B，未上调）。
- 数据质量：0 重复行、0 常数列、0 高缺失列、0 行因目标缺失被剔除；batch_id 有 148 个唯一值对 149 行（存在一次重复编号，其余唯一），ts_start 149 个唯一值且已按时间排序。
- oligomer 侧典型 FAIL：MD_TH007/008 离群敏感性 OK 但 Simpson 翻转、MD_TH002/003/005 离群驱动 + Simpson、MD_TH009 仅 Simpson——6 对 p<0.05 全军覆没于稳健性复核。

### 3.2 披露与限制（全部保留，不得删除）

1. 观察性数据：全部结论为相关级（evidence B），执行任何操作窗口前必须完成 confirmations
2. 混线未分层：9 个型号共用一张相关表，型号间缺陷基线差异悬殊（描述性中位数 35 ~ 4145），12 处 Simpson 分层方向翻转即由此类层间结构产生——任何跨型号的方向/幅度都必须先按型号（必要时再按时间段）分层复验
3. total_defects 与 oligomer 均无规格限（lsl/usl/target 为空），Cp/Cpk/Pp/Ppk 全部不可计算，能力评估缺位
4. 响应分布极端右偏非正态（total_defects 偏度 7.8311、AD=48.7257），Pearson r 受极端批次杠杆影响；FP41（3 批）与 FG22（6 批）样本量过小，其层内数字不可单独引用
5. 0 窗口的成因是合并稳态段仅 30 行且跨 6 个型号（最大层 8 行，低于分层核验每层 ≥20 行的要求）；补数方案应以"单型号连续 ≥20 批"为最小分析单元

### 3.3 确认试验计划

本次 0 窗口 → 0 条合同内确认项。建议的确认路径（按协议补数后再触发）：

1. **先分层复跑**：以单型号为层（优先 PG31DS n=67、FP21 n=19、PG32M n=13、PG32D n=16 等样本充足层），各层内重算相关与稳态段；FP41/FG22 仅做案例记录，不进因素分析。
2. **层内补数**：目标型号连续 ≥20 批稳态数据，再由 observational_windows 产出带 `confirmation_needed=true` 的候选窗口。
3. **小型试验设计**：对分层后仍方向一致的 2-4 个因子，按"每因子 ±半窗宽两点 + 中心点、2 次重复"做确认试验（协议 runs ≤12）。

### 3.4 下游使用规则

- observational 窗口在闭环执行前必须先跑 confirmations
- confidence=low 的窗口仅可用于人工参考与试验设计，不得直接下发控制
- 混线数据先分层：任何窗口化/调参动作前，必须先按 model（必要时再按时间段）分层复跑，确认效应方向在层内一致后才有资格进入确认试验
- 本合同的 ΔR² 贡献排名含趋势混杂项（W1C40/W1C4B 为 CAUTION，去趋势后 r≈0.005），不得作为因子优先级直接采信

- 适用域：n=149，时间跨度 2026-05-04 14:42:00 .. 2026-05-13 14:26:00，工况限定 steady-state segments
- 失效条件：任一因子越出 applicability_domain.factor_observed_ranges 的 ±20%；stability_report 变点检测触发新 regime（漂移/换产）；确认试验结果与 expected_effect 的 CI95 不相交

---

## 附：工件索引

| 工件 | 说明 |
|---|---|
| `00_input/analysis_context.json` | 用户指定角色/目标（user 赋值） |
| `00_input/batches.csv` | 149 批 × 51 列输入数据（input_sha256 f7df6e56…8cfc） |
| `01_profile/data_profile.json` | 数据画像与设计探测（observational，LHS 0.14） |
| `02_analysis/correlation_report.json` | 88 对相关 + 防伪判定 + BH 校正 + ΔR² |
| `02_analysis/stability_report.json` | 能力/正态性/稳态段/工况划分 |
| `03_figures/plot_manifest.json` | 5 图清单与墨水门（5/5 PASS） |
| `conclusions/doe_conclusion.json` | 结论基线（authored_by: agent，4 条 key_findings） |
| `conclusions/recommendations.json` | 下游合同 v1.0（0 窗口 / 3 条 watchlist / 4 条 usage_rules，authored_by: agent） |
| `report.md` | 本报告 |

> 质量门禁：G1-G6 共 14 项检查全部 PASS（exit 0）。除本报告与 conclusions/ 两文件的授权编辑外，01_profile 与 02_analysis 均未改动，全部计算数字保持脚本原值。
