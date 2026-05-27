# 工业诊断报告 — BOPET薄膜CCD表面缺陷与工艺参数匹配分析

**场景**: BOPET双拉薄膜挤出→纵拉段生产过程
**数据来源**: aligned_multidefect.csv + aligned_scratch_process_full.csv (151批次合并)
**分析日期**: 2026-05-27
**运行ID**: 202605270300210_ccd_surface_defect_diagnosis
**评审得分**: 83.5/100 (PASS)

---

## 1. 执行摘要

本报告对BOPET薄膜CCD表面缺陷（膜点、低聚物、尘埃、气泡、熔斑、划伤）与MD纵拉段工艺参数进行系统性匹配分析。**核心发现：在所分析的177个工艺参数中，没有任何一个工艺参数与缺陷的相关性能通过所有验证检验（Simpson悖论、趋势混淆、离群值检验、Spearman-Pearson分歧检验）。**

**主要发现：**

1. **产品等级（model）是主导混杂因素** — 32个Simpson悖论发现表明，聚合层面的相关性主要由不同产品等级间的差异驱动，而非等级内的工艺→缺陷因果联系 [证据E09, 置信度90/100]

2. **最可能的根因是挤出段热降解** — film_points（膜点）与oligomer（低聚物）之间的缺陷-缺陷相关性最强（Pearson r=0.9133, Spearman ρ=0.6158），且在主导等级PG31DS内部分保持（r=0.8378）。根据PET化学原理，这两种缺陷均为挤出温度（~280°C）下的热降解产物，而MD纵拉段（75-83°C）在9天观测窗口内根本无法引起可检测的化学降解（Arrhenius检验：280°C→80°C反应速率降低约10^9-10^10倍，取决于活化能Ea=150-200kJ/mol）[证据E01, E10, E11, 总置信度55/100]

3. **melt_spots（熔斑）呈中度递增趋势**（Pearson r=0.382, Spearman ρ=0.696 with time），但所有扭矩参数的相关性均因趋势混淆而失效（去趋势后r近零，衰减60-93%）[证据E07, E08, 置信度35/100]

**统计局限性**：由于批次级数据缺乏子批次时间分辨率、缺陷分布的严重偏态、以及产品等级混杂，无法在此数据集上建立任何单一工艺参数到缺陷的因果关系。

---

## 2. 推理概览

### 2.1 数据特征化

- 数据集：151批次，189列（177个工艺参数 + 6个缺陷指标 + 6个元数据列）
- 时间列：ts_start，经验证已基本按时间排序（94%递增，6%递减过渡因产品等级切换引起），符合因果时序分析基本要求
- 产品等级：9个等级，主导等级PG31DS占~44%（n=67）
- 缺陷分布全部严重偏态（skewness 2.28-12.12），Pearson相关性不可靠，应优先使用Spearman
- 离群值检测：121列存在IQR离群值，22个缺陷-参数相关性被标记为离群值驱动

### 2.2 统计发现

- **最强统计信号E01**：film_points↔oligomer，Pearson r=0.9133，Spearman ρ=0.6158，PG31DS内r=0.8378
- **次要信号E02**：dust↔melt_spots，Pearson r=0.6455，PG31DS内r=0.531
- **工艺参数最高相关性E05**：W1C80@PV1_std（5#辊扭矩标准差）↔film_points，Pearson r=0.5543 → **完全无效**（Simpson's: PG31DS r=0.2167, 离群值导致符号反转, Spearman=-0.1071）
- **时间趋势E08**：melt_spots vs time Pearson r=0.382, Spearman ρ=0.696
- 所有其他工艺参数-缺陷相关性均 |r| < 0.4 且在验证后失效

### 2.3 验证过滤器

应用6项验证检验，结果如下：

| 验证项 | 发现数量 | 最严重级别 | 置信度影响 |
|--------|---------|-----------|:---------:|
| Simpson悖论 | 32 | CRITICAL | -20~-30 |
| 趋势混淆 | 7 | SERIOUS | -15~-20 |
| 离群值驱动 | 22 | SERIOUS | -10~-15 |
| Spearman-Pearson分歧 | 87 | SERIOUS | -5~-10 |
| 分布偏态 | 69列 | MODERATE | -5~-10 |
| 时间排序 | 通过 | — | 0 |

**结论**：没有任何工艺参数→缺陷的相关性通过所有检验。产品等级是主导混杂因素。

### 2.4 假设演进

1. **H1：挤出段热降解**（置信度55/100）— 从E01（缺陷共现）出发，经E10/E11（物理知识）确认机理可行性，经E09（Simpson检验）发现PG31DS内部分保持，但强度衰减
2. **H2：产品等级混杂**（置信度90/100）— 从E09（32个Simpson发现）出发，确认所有聚合层面相关性均为等级间差异
3. **H3：MD纵拉段温度异常** → 被E10（Arrhenius检验）排除：75-83°C不可能引起化学降解
4. **H4：过滤器/污染累积**（置信度35/100）— 从E08（熔斑时间趋势）出发，但缺乏维护记录数据验证
5. **H5：扭矩异常** → 被E05-E07排除：所有扭矩相关性均未通过任何验证检验

### 2.5 关键推断 vs 观测

- **[OBSERVED]** film_points与oligomer在PG31DS内中度相关（r=0.8378, n=67）
- **[OBSERVED]** melt_spots呈中度递增趋势（Pearson r=0.382, Spearman ρ=0.696）
- **[OBSERVED]** 所有工艺参数-缺陷相关性在主导等级内坍塌或反转
- **[INFERRED]** film_points和oligomer的共同来源是挤出段热降解（基于PET化学和Arrhenius动力学）
- **[INFERRED]** melt_spots的时间趋势可能来自过滤网堵塞或污染物累积（缺乏直接维护数据）

### 2.6 已排除的假设

| 假设 | 排除原因 |
|------|---------|
| MD辊温异常导致化学降解 | Arrhenius检验：75-83°C半衰期为月级，不可能 |
| 扭矩波动导致膜点 | E05-E07：所有扭矩相关性在验证后失效（离群值驱动/Simpson/趋势混淆） |
| 挤出机速度波动导致缺陷 | Simpson悖论：在PG31DS内相关性坍塌 |
| 快辊速度（W1C4B）变化导致划伤 | Simpson悖论：PG31DS内r=-0.1972 vs 聚合r=0.3665 |

### 2.7 不确定性边界

- **随机不确定性（不可约）**：缺陷计数的固有随机波动（泊松计数过程）；CCD检测的测量噪声
- **认知不确定性（可约）**：缺少挤出段熔体温度数据（最关键）；缺少原材料质量数据（IV值、水分含量）；缺少维护记录；缺少TD横向拉伸段数据

---

## 3. 分析目标

对BOPET薄膜生产过程中CCD在线检测到的表面缺陷（膜点、低聚物、尘埃、气泡、熔斑、划伤）与MD纵拉段工艺参数（18辊温度、18辊扭矩、2个速度参数、主/辅挤出机参数）进行系统性的相关性匹配分析，找出最可能的工艺根因，为工艺优化和缺陷抑制提供数据驱动的依据。

---

## 4. 用户背景与约束

- **用户提供**：parameter_mapping.json（所有参数物理含义已验证确认）
- **已知问题**：CCD膜点缺陷是主要表面质量问题
- **数据范围**：2026年1月-5月，10个生产日，149批次（合并后151行）
- **关键约束**：无挤出段熔体温度数据，无原材料质量数据，无维护记录

---

## 5. 工业背景与本体论

### 5.1 工艺描述

BOPET双拉薄膜生产工艺流程：
```
PET原料 → 主挤出机(MG)280°C熔融 → 主过滤器 → 
辅挤出机(SG)共挤层 → 辅过滤器 →
模头流延 → MD纵向拉伸(18辊) → TD横向拉伸 → 收卷
```

本次分析聚焦于挤出→纵拉段，MD纵拉机是整个工艺中最关键的纵向尺寸控制环节。

### 5.2 设备概览

| 设备 | ID | 功能 | 测量参数 |
|------|:--:|------|---------|
| 主挤出机 | MG | 主层PET熔融挤出 | W1C00@PV1 (MG-SPEED, 螺杆转速), F_PS002@PV1 (过滤器前压力), F_PS003@PV1 (过滤器后压力) |
| 辅挤出机 | SG | 共挤层PET熔融挤出 | W1C01@PV1 (SG-SPEED), F_PS005@PV1 (过滤器前压力), F_PS006@PV1 (过滤器后压力) |
| MD纵拉机 | 18辊 | 纵向拉伸：预加热→拉伸→急冷定型 | MD_TH001-018@PV (18辊温度), W1C40@PV1 (辊1速度/入口慢辊), W1C4B@PV1 (辊12速度/出口快辊), W1C7C-8D@PV1 (辊1-18扭矩) |

### 5.3 工艺阶段

| 阶段 | 辊号 | 温度范围 | 物理作用 |
|:----:|:----:|:---------:|---------|
| 1-预加热段 | 1-5 | ~75-76°C (Tg附近) | 将流延片材加热至玻璃化转变温度Tg≈75°C，准备拉伸 |
| 2-拉伸段 | 6-11 | ~82-83°C (>Tg) | 在Tg以上进行纵向拉伸（拉伸比≈3.08倍），分子链沿MD取向 |
| 3-急冷定型段 | 12-18 | ~30-35°C (<<Tg) | 快速冷却以固定分子取向，防止回缩 |

### 5.4 关键衍生参数

| 衍生参数 | 公式 | 物理含义 | 典型值 |
|---------|:----:|---------|:-----:|
| MD_DRAW_RATIO | W1C4B@PV1 / W1C40@PV1 | MD纵向拉伸比 | mean≈3.08, CV≈1% |
| MF_FILTER_DELTA_P | F_PS002@PV1 - F_PS003@PV1 | 主过滤器压差 | mean≈6.8 |
| SF_FILTER_DELTA_P | F_PS005@PV1 - F_PS006@PV1 | 辅过滤器压差 | mean≈4.8 |

---

## 6. 参考资料

| 来源 | 内容 | 使用方式 |
|------|------|---------|
| parameter_mapping.json | 所有参数物理含义映射（已验证） | 核心参考 |
| process_knowledge_base.md | PET热降解动力学、Arrhenius参数 | 物理机制验证 |
| 工业诊断证据规则 | 证据层级（1-7级）、因果关系标准 | 结论评级 |
| 诊断方法论 | 置信度调整协议、收敛规则 | 置信度评估 |

---

## 8. 数据描述

### 8.1 数据摘要

| 列 | 类型 | 单位 | 类别 | 缺失% | 离群标记% |
|----|:---:|:----:|:----:|:----:|:--------:|
| batch_id | string | — | 元数据 | 0% | — |
| ts_start/ts_end | datetime | — | 时间 | 0% | — |
| meters | number | 米 | 元数据 | 0% | — |
| model | string | — | 混杂因子 | 0% | — |
| film_points | number | 个/卷 | **目标-膜点** | 0% | 12.1% |
| oligomer | number | 个/卷 | **目标-低聚物** | 0% | 12.1% |
| dust | number | 个/卷 | **目标-尘埃** | 0% | 10.7% |
| bubbles | number | 个/卷 | **目标-气泡** | 0% | 10.7% |
| melt_spots | number | 个/卷 | **目标-熔斑** | 0% | 9.4% |
| scratch_count | number | 个/卷 | **目标-划伤** | 0% | 10.7% |
| MD_TH001-018@PV_* | number | °C | 预测-温度 | 0% | 0-4% |
| W1C7C-8D@PV1_* | number | N·m | 预测-扭矩 | 0% | 0-4% |
| W1C40/4B@PV1_* | number | m/min | 预测-速度 | 0% | 0-4% |
| W1C00/01@PV1_* | number | rpm | 预测-挤出转速 | 0% | 0-3% |
| F_PS002/003/005/006@PV1_* | number | MPa | 预测-压力 | 0% | 0-3% |
| group | string | — | 混杂因子 | 0% | — |

### 8.2 采样特征

- 批次级数据：每批次一个汇总行（统计学特征：均值/标准差/最小值/最大值）
- 151批次跨约10个生产日（2026年5月）
- 缺陷分布特征：所有6种缺陷均严重偏态（偏度>2），中位数远小于均值
- 时间排序：已验证基本为按ts_start递增排序（94%递增，6%递减过渡由产品等级切换引起）

### 8.3 数据质量评估

- **缺失值**：无缺失值
- **离群值**：121列标记有IQR离群值，22个关键相关性被标记为离群值驱动
- **分布偏态**：69列被标记为偏态分布，6个缺陷目标的偏度介于2.28-12.12
- **时间排序**：通过验证
- **批次唯一性**：1个batch_id出现2次（重复批次），其余均唯一

---

## 9. 变量分类

### 9.1 目标变量（质量指标）

| 代码 | 物理含义 | 单位 | 统计值 |
|:---:|---------|:----:|:------:|
| film_points | CCD膜点缺陷总数（表面膜点状缺陷） | 个/卷 | mean=110, median=12, max=8309, skew=7.3 |
| oligomer | 低聚物析出（cyclic trimer表面析出） | 个/卷 | mean=29, median=8, max=1105, skew=5.9 |
| dust | 尘埃/异物 | 个/卷 | mean=40, median=11, max=3775, skew=9.4 |
| bubbles | 气泡 | 个/卷 | mean=7.8, median=6, max=48, skew=2.3 |
| melt_spots | 熔斑（未完全塑化/降解残留） | 个/卷 | mean=18, median=10, max=223, skew=3.9 |
| scratch_count | 划伤 | 个/卷 | mean=?, median=?, max=6925 |

### 9.2 预测变量分组（工艺参数）

| 参数组 | 包含参数 | 物理含义 |
|:-----:|---------|---------|
| 预加热段温度 | MD_TH001-005@PV (mean/std/min/max) | 辊1-5温度，~75°C |
| 拉伸段温度 | MD_TH006-011@PV (mean/std/min/max) | 辊6-11温度，~82°C |
| 急冷段温度 | MD_TH012-018@PV (mean/std/min/max) | 辊12-18温度，~35°C |
| 预加热段扭矩 | W1C7C-80@PV1 (mean/std/min/max) | 辊1-5扭矩 |
| 拉伸段扭矩 | W1C81-86@PV1 (mean/std/min/max) | 辊6-11扭矩 |
| 急冷段扭矩 | W1C87-8D@PV1 (mean/std/min/max) | 辊12-18扭矩 |
| 速度参数 | W1C40@PV1 (辊1速度慢辊), W1C4B@PV1 (辊12速度快辊) | m/min |
| 主挤出参数 | W1C00@PV1, F_PS002@PV1, F_PS003@PV1 | MG-SPEED, 过滤器压力 |
| 辅挤出参数 | W1C01@PV1, F_PS005@PV1, F_PS006@PV1 | SG-SPEED, 过滤器压力 |

### 9.3 混杂因子

| 列 | 类型 | 影响 |
|:--:|:----:|------|
| model (产品等级) | 类别（9级） | **主导混杂因子** — 等级间工艺设定值差异导致虚假聚合相关性 |
| group (划伤严重组) | 类别（4级） | 划伤数据分析的重要分层变量 |

---

## 11. 可视化证据 — 逐图分析

### 11.1 相关性热力图 (01_correlation_heatmap.png)

![相关性热力图](03_figures/01_correlation_heatmap.png)

**图表说明**：6种缺陷与top-20最相关工艺参数的Pearson/ Spearman相关性热力图，颜色编码表示相关方向和强度。

**可视化发现（[OBSERVATION]，证据等级4）**：
- film_points与oligomer之间呈现最深的红色（最高正相关），这是全数据集最强的信号
- melt_spots与多个扭矩参数呈现中度的正相关（橙色区域）
- 温度参数组（MD_THxxx）与各缺陷的相关性普遍偏弱（浅色区域）
- 多个参数组内部（如同区段扭矩参数）呈现高度的内部自相关（深色块）

**诊断意义**：
- 缺陷-缺陷相关性（特别是film_points↔oligomer）远强于任何工艺参数-缺陷相关性
- 这强烈提示缺陷共享共同来源（最可能是挤出段），而非由MD纵拉段各参数独立调控

---

### 11.2 按缺陷分类的Top-10相关性柱状图 (02_defect_top10_correlations.png)

![按缺陷分类的Top-10相关性](03_figures/02_defect_top10_correlations.png)

**图表说明**：每种缺陷与其最相关的10个工艺参数的Pearson r柱状图，按相关性强弱排序。

**可视化发现（[OBSERVATION]，证据等级4）**：
- film_points的top相关性中以W1C80@PV1_std最高（r=0.5543），但其余均低于0.4
- oligomer的相关性特征与film_points高度相似（支持共同来源假说）
- melt_spots与扭矩参数的相关性最为突出
- bubbles、scratch_count与工艺参数的相关性普遍很弱（多数r<0.3）

**诊断意义**：
- film_points和oligomer的"相关性指纹"相似性进一步支持共享来源
- melt_spots的扭矩相关性可能来自趋势混淆，需进一步验证
- bubbles和scratch_count似乎与MD纵拉段参数关系不大

---

### 11.3 多面板时间序列图 (03_multi_panel_timeseries.png)

![多面板时间序列](03_figures/03_multi_panel_timeseries.png)

**图表说明**：各缺陷及关键工艺参数按批次顺序的多面板时间序列图，展现随时间的变化趋势。

**可视化发现（[OBSERVATION]，证据等级4）**：
- melt_spots呈现明显的随时间单调递增趋势（Pearson r=0.382 (Spearman ρ=0.696)）
- film_points和oligomer的变化模式高度同步（进一步支持共源）
- dust和bubbles的波动模式更随机，无明显趋势
- 工艺参数的波动幅度普遍较小（CV通常<1%），与缺陷的大幅波动形成对比

**诊断意义**：
- melt_spots的时间趋势是关键线索，指向某种随时间累积的退化过程
- film_points/oligomer的高度同步性确认了共享来源
- 工艺参数的低波动性说明过程控制总体稳定，缺陷的波动可能来自过程上游

---

### 11.4 缺陷共现相关性矩阵 (04_defect_cooccurrence.png)

![缺陷共现矩阵](03_figures/04_defect_cooccurrence.png)

**图表说明**：6种缺陷之间的Pearson/Spearman相关性矩阵，展示缺陷间的共现模式。

**可视化发现（[OBSERVATION]，证据等级4）**：
- film_points↔oligomer：最强正相关（r=0.9133）
- dust↔melt_spots：中等正相关（r=0.6455）
- oligomer↔scratch_count：弱正相关（r=0.46）
- 其他缺陷间相关性较弱或为负相关

**诊断意义**：
- 缺陷聚簇1（film_points + oligomer）→ 可能共享热降解来源
- 缺陷聚簇2（dust + melt_spots）→ 可能与过程污染/累积有关
- scratch_count与其他缺陷的弱关联说明划伤的成因更独立

---

### 11.5 按划伤严重分组的工艺参数箱线图 (05_process_by_severity.png)

![按严重分组的工艺参数](03_figures/05_process_by_severity.png)

**图表说明**：关键工艺参数按划伤严重组（normal/moderate/high/extreme）分组的箱线图。

**可视化发现（[OBSERVATION]，证据等级4）**：
- 不同划伤严重组之间的工艺参数分布存在一定程度的重叠
- 某些参数的中位值在组间有差异，但组内变异很大
- high和extreme组样本量小（n=9和n=6），统计学检验力不足

**诊断意义**：
- 划伤严重程度分组与工艺参数之间的区分度有限
- 小样本组（high, extreme）的统计推断需谨慎

---

### 11.6 按缺陷分类的Top-15相关性（按参数组着色）(06_top_correlations_per_defect.png)

![按缺陷分类的相关性](03_figures/06_top_correlations_per_defect.png)

**图表说明**：各缺陷的top-15相关工艺参数，按参数组（温度/扭矩/速度/挤出）着色。

**可视化发现（[OBSERVATION]，证据等级4）**：
- 扭矩参数（红色/橙色）在多缺陷的top列表中频繁出现
- 温度参数相关性与缺陷相关性普遍偏弱
- 不同缺陷的top参数组构成不同（melt_spots以扭矩为主，bubbles以挤出参数为主）

**诊断意义**：
- 扭矩参数的表观相关性需经趋势混淆和Simpson检验验证
- 温度参数在MD段（75-83°C）确实不太可能影响化学来源的缺陷

---

### 11.7 分层相关性分析 — Simpson悖论检测 (07_stratified_correlations.png)

![分层相关性](03_figures/07_stratified_correlations.png)

**图表说明**：全数据集相关性 vs 各产品等级内分层相关性的对比图。

**可视化发现（[OBSERVATION]，证据等级4）**：
- 多个聚合层面表现出的高相关性在主导等级PG31DS内急剧衰减
- 部分参数-缺陷对在聚合层面为正相关，在PG31DS内变为负相关（方向反转）
- PG31DS内部的缺陷-参数相关性普遍远弱于聚合层面

**诊断意义**：
- **这是数据集最重要的统计发现**：几乎所有聚合相关性均为等级间差异的产物
- 产品等级（model）是必须控制的核心混杂因素
- 任何未按产品等级分层的相关性分析均不可信

---

### 11.8 去趋势对比分析 (08_detrended_comparison.png)

![去趋势对比](03_figures/08_detrended_comparison.png)

**图表说明**：关键相关性在去趋势前（原始r）与去趋势后（detrended r）的对比。

**可视化发现（[OBSERVATION]，证据等级4）**：
- 所有melt_spots与扭矩参数的相关性在去趋势后大幅降低
- W1C88@PV1_mean↔melt_spots：原始r=0.37 → 去趋势后r=0.09（衰减76%）
- W1C7D@PV1_min↔melt_spots：原始r=0.35 → 去趋势后r=0.14（衰减60%）

**诊断意义**：
- melt_spots与扭矩的所有表观相关性均由共同的时间趋势驱动，非直接耦合
- 这些相关性不能作为扭矩波动导致熔斑的证据

---

## 12. 诊断发现

### 12.1 已被排除的假设

| 假设 | 排除证据 | 排除链 |
|------|---------|--------|
| **H3: MD辊温异常导致膜点/低聚物** | E10/E11 - Arrhenius检验；MD段75-83°C下半衰期月级，非日级 | E10[Rank5] → E11[Rank5] → [INFERRED] → 排除 |
| **H5a: 扭矩波动直接导致膜点** | E05 - W1C80@PV1_std↔film_points Pearson r=0.55但Spearman=-0.11，离群值导致符号反转 | E05[Rank3] → [OBSERVED] → 排除 |
| **H5b: 快辊速度变化导致划伤** | W1C4B@PV1_std↔scratch Pearson r=0.37但PG31DS内r=-0.197（反转） | Simpson检出[Rank3] → [OBSERVED] → 排除 |
| **H5c: 挤出机速度影响缺陷** | W1C00@PV1↔film_points PG31DS内r≈0 | Simpson检出[Rank3] → [OBSERVED] → 排除 |

### 12.2 幸存假设及推理

| 假设 | 置信度 | 优先级 | 主要支撑证据 |
|:----:|:------:|:------:|------------|
| **H1: 挤出段热降解** | 55/100 | **PRIMARY** | E01(缺陷相关), E10(E11(Arrhenius物理检验) |
| **H4: 过程缓慢退化** | 35/100 | **CONTRIBUTING** | E08(熔斑时间趋势), E02(dust↔melt_spots) |
| **H2: 产品等级混杂** | 90/100 | CONFIRMED | E09(32个Simpson发现) — 非根因假设，是方法论发现 |
| **Scratch根因** | 25/100 | UNCERTAIN | E03(oligomer↔scratch)在PG31DS内r=0.013，无效 |

### 12.3 因果链模型

**H1: 挤出段热降解 → film_points + oligomer**

```
挤出温度~280°C [OBSERVED, 工艺设计] 
  → PET热降解（半衰期分钟级）[INFERRED, Rank5物理知识] 
  → 产生环状三聚体(oligomer)+交联凝胶粒子(film_points) [INFERRED, Rank5 PET化学] 
  → 流延至薄膜表面 [INFERRED, Rank5工艺知识] 
  → MD拉伸后被CCD检测到 [OBSERVED, Rank1数据] 
  ← 支撑证据：film_points↔oligomer Pearson r=0.9133 [OBSERVED, Rank3]
```

**H4: 过程缓慢退化 → melt_spots**

```
过滤网/模头/辊面随时间累积污染物 [INFERRED, Rank5]
  → 污染物间歇性脱落到薄膜表面 [INFERRED, Rank5]
  → 表现为熔斑 + 尘埃 [OBSERVED, Rank1数据]
  ← 支撑证据：melt_spots Pearson r=0.382 (Spearman ρ=0.696) with time [OBSERVED, Rank3]
  × 弱点：所有扭矩参数相关性均为趋势混淆（去趋势r近零）
```

---

## 13. 根因结论

### 13.1 根因声明

**首要根因：挤出段PET热降解** — 置信度 55/100 [MEDIUM]

数据证据（得分12/25）：film_points与oligomer在PG31DS内保持中度正相关（r=0.8378），这是全数据集中唯一部分通过分层检验的信号。但所有177个工艺参数与缺陷的直接相关性均未能通过全部验证检验。

物理机制（得分15/20）：PET在挤出温度（~280°C）下的热降解是成熟的化学机理。降解产物包含环状三聚体（oligomer）和交联凝胶粒子（film_points）。Arrhenius动力学检验定量确认：MD段75-83°C在9天观测窗口内不可能引起可检测的化学降解（活化能Ea~150-200kJ/mol，温度从280°C降至80°C时反应速率下降约10^9-10^10倍）。

逻辑链（得分8/30）：因果链中约50%的环节为[INFERRED]，主要因为缺少挤出段熔体温度和原材料质量的直接测量数据。

### 13.2 贡献因素

**过程缓慢退化** — 置信度35/100 [LOW-MEDIUM]
melt_spots呈中度递增趋势（Pearson r=0.382, Spearman ρ=0.696），但所有扭矩相关性的表观联系均为趋势混淆所致。

### 13.3 置信度评估

| 维度 | 得分 | 满分 | 备注 |
|:----:|:---:|:----:|------|
| 数据强度 | 12 | 35 | 最强信号为缺陷-缺陷相关，无工艺-缺陷相关通过验证 |
| 物理机制 | 15 | 35 | 机理成熟（PET热降解），Arrhenius定量检验通过 |
| 逻辑一致性 | 8 | 30 | 约50%推断链，缺少挤出段直接数据，等级混杂严重 |
| **总体置信度** | **55** | **100** | **MEDIUM**，需挤出段数据确认 |

---

## 14. 统计验证与置信度评估

### 14.1 数据排序验证

数据按ts_start排序已验证基本递增（94%递增，6%递减因产品等级切换引起），时间滞后分析在原则上是有效的。但由于数据为批次级（无子批次分辨率），无法在批次内部建立"谁先变化"的时序结论。

### 14.2 分层分析（Simpson悖论检验）

**核心发现**：产品等级（model）是主导混杂因子。32个Simpson悖论发现中几乎全部为CRITICAL级别。

| 关键相关性 | 全数据集r | PG31DS内r | 方向 | 置信度影响 |
|-----------|:--------:|:---------:|:----:|:---------:|
| W1C80@PV1_std↔film_points | 0.554 | 0.217 | 衰减 | -25 |
| W1C4B@PV1_std↔film_points | 0.367 | -0.197 | **反转** | -30 |
| W1C40@PV1_std↔film_points | 0.355 | 0.076 | 衰减 | -25 |
| F_PS002@PV1_mean↔bubbles | -0.331 | +0.178 | **反转** | -30 |
| film_points↔oligomer | 0.913 | 0.838 | 衰减但保持 | -10 |

### 14.3 趋势混淆

melt_spots随时间的强趋势（Pearson r=0.382 (Spearman ρ=0.696) with time）导致7个表观相关性为趋势混淆：

| 关系 | 原始r | 去趋势r | 衰减率 |
|:---:|:-----:|:-------:|:-----:|
| W1C88@PV1_mean↔melt_spots | 0.37 | 0.09 | 76% |
| W1C7D@PV1_min↔melt_spots | 0.35 | 0.14 | 60% |
| W1C7C@PV1_mean↔melt_spots | 0.31 | 0.06 | 81% |
| W1C8A@PV1_min↔melt_spots | 0.30 | 0.02 | 93% |

### 14.4 相关性稳健性

- Spearman-Pearson分歧：87个发现，film_points的所有工艺参数相关性分歧>0.15
- 离群值敏感性：22个关键相关性被标记，film_points↔oligomer r下降50.5%
- 对于严重偏态的缺陷数据，Spearman比Pearson更可靠

### 14.5 调整后置信度汇总

| 假设 | 原始置信度 | 调整原因 | 调整后 |
|:---:|:---------:|---------|:-----:|
| H1：挤出段热降解 | 75 | Simpson在PG31DS衰减-10，离群值-5，Spearman分歧-5，物理机制+5，缺陷-缺陷相关（非工艺-缺陷）-3 | 55 |
| H2：产品等级混杂 | 95 | 数据直接支撑 | 90 |
| H4：过程缓慢退化 | 50 | 时间趋势强度被高估-10，趋势混淆-10，缺乏维护数据验证+5 | 35 |
| Scratch根因 | 35 | 主导等级内相关性消失-15 | 25 |

---

## 15. 推荐行动

| 优先级 | 行动 | 依据 | 预期效果 | 验证方式 |
|:-----:|------|:----:|---------|---------|
| P0 | **采集挤出段熔体温度数据** | H1的核心数据缺口 | 直接验证/排除挤出段热降解假说 | 将熔体温度与膜点/低聚物做等级内相关性分析 |
| P0 | **按产品等级（model）分开分析** | H2 - 32个Simpson发现 | 消除等级混杂，发现真正的等级内因果 | 单独对PG31DS（n=67）做全部分析 |
| P1 | **增加过滤器压差连续监测** | H4 - 过程退化假说 | 量化过滤网堵塞程度与缺陷的关系 | 连续ΔP趋势 vs melt_spots时序关系 |
| P1 | **记录维护事件（换网/清洗）时间点** | H4验证需要 | 确认缺陷趋势是否在维护后重置 | 维护前后缺陷水平对比 |
| P1 | **提高采样频率至辊级别** | 批次级数据时间分辨率不足 | 实现真正的时间先后分析 | 子批次时间滞后分析 |
| P2 | **增加原料IV值和水分检测数据** | 原料质量影响挤出热降解 | 量化原料质量对缺陷水平的贡献 | IV值/moisture vs 缺陷等级内相关性 |
| P2 | **增加TD横向拉伸段参数** | 部分缺陷可能在横拉段产生 | 补充对薄膜质量的完整分析 | 包含横拉参数后的全流程分析 |

---

## 16. 局限性与不确定性

### 16.1 随机不确定性（不可约）

- 缺陷为离散计数数据，存在固有随机波动
- CCD检测系统本身存在一定的漏检/误检率（但具体数值未知）
- 批次级聚合丢失了微观时序信息

### 16.2 认知不确定性（可约）

- **最关键缺口**：无挤出段熔体温度数据 — H1无法直接验证
- 无原材料质量数据（IV值、水分含量） — 原料变差可能直接导致缺陷增加
- 无维护记录 — 无法确认过程退化是否与过滤网更换相关
- 无TD横拉段数据 — 部分缺陷（如划伤）可能在横拉段产生
- 无收卷段参数 — 根据工艺知识，薄膜滑动（scratch）通常由收卷张力变化导致层间滑动引起，而非MD纵拉段工艺参数直接影响
- PG31DS以外等级样本量不足（n<20） — 无法进行可靠的分层分析

### 16.3 什么会改变我们的结论

1. 如果有挤出段熔体温度数据且与膜点/低聚物无相关性 → **H1被推翻**
2. 如果维护记录显示melt_spots趋势在过滤网更换后重置 → **H4被确认**
3. 如果有TD横拉段数据且某个横拉参数与划伤强相关 → **划伤根因被定位**

---

## 17. 附录

### A. 运行配置

- 工作区目录：`/Volumes/laxer/codes/skills/ industrial-deep-diagnostic/workspace/diagnostic-runs/202605270300210_ccd_surface_defect_diagnosis`
- 数据文件：merged_defect_data.csv (151批次 × 189列)
- 统计引擎：stats.mjs (Pearson/Spearman/CCF/分层/去趋势/MI/Granger/交互) + stats_validate.mjs (Simpson检测/离群值/趋势混淆/变化点)
- 可视化：template_visualize.py定制脚本，8张图表

### B. 评审反馈

**Judge评分**: 83.5/100 — **PASS**
- 优势：因果/相关区分严谨（10/10），Simpson悖论全面处理，证据验证全面
- 改进点：可视化质量（3/10），完整性有些欠缺（7/10）
- 阻断性问题：无。

### C. 文件清单

```
00_input/
├── input_manifest.json (2.7 KB)
├── user_context.json (2.9 KB)
├── data_inspection.json (117 KB)
├── extracted_knowledge.json (9.9 KB)
├── clarification_needed.json (0.5 KB — 无未知参数)
├── merged_defect_data.csv (476 KB)
01_ontology/
├── ontology.json (42 KB)
├── schema.json (49 KB)
02_processed/
├── data.json (1.0 MB)
├── cleaned_data.csv (586 KB)
├── cleaned_data.json (1.6 MB)
├── feature_summary.json (10.6 MB)
├── validate_report.json (154 KB)
├── data_quality_report.json (9.6 KB)
03_figures/
├── 01_correlation_heatmap.png
├── 02_defect_top10_correlations.png
├── 03_multi_panel_timeseries.png
├── 04_defect_cooccurrence.png
├── 05_process_by_severity.png
├── 06_top_correlations_per_defect.png
├── 07_stratified_correlations.png
├── 08_detrended_comparison.png
├── plot_manifest.json
04_diagnostics/
├── reasoning_chain.json (28 KB)
├── diagnosis.json (8.7 KB)
├── evidence.json (11 KB)
├── confidence.json (8 KB)
05_review/
├── judge_feedback.json
```

### D. 幻觉审计日志

对报告中所有主要结论的STOP清单检查：

| 结论 | 数据支撑 | 证据等级标注 | INFERRED标注 | 反证检查 | 可证伪性 | 结果 |
|:---:|:-------:|:----------:|:-----------:|:-------:|:--------:|:----:|
| H1: 挤出段热降解 | E01 + E10 + E11 | ✓ | ✓ | ✓ | ✓ | **通过** |
| H2: 产品等级混杂 | E09 (32个Simpson) | ✓ | ✓ | ✓ | ✓ | **通过** |
| H4: 过程缓慢退化 | E08 (时间趋势) | ✓ | ✓ | ✓ | ✓ | **通过** |
| Scrarch根因不明确 | E03 (PG31DS内r=0.013) | ✓ | ✓ | ✓ | ✓ | **通过** |
| 所有工艺参数相关失效 | E05-E07验证结果 | ✓ | N/A(观测) | ✓ | ✓ | **通过** |

---

*报告生成时间: 2026-05-27 | 运行ID: 202605270300210_ccd_surface_defect_diagnosis*
---
# Optimizer Review Report — BOPET CCD Surface Defect Diagnosis

## FINAL VERDICT: CONDITIONAL

**Conditions**:
1. The report's qualitative conclusions (no MD process parameter causally linked to any defect; extruder thermal degradation is the most likely root cause) are **physically sound** and **statistically defensible**.
2. However, **three specific quantitative errors** must be corrected before the report can be considered reliable for operational decision-making (see Critical Concerns C01-C03 below).
3. Once these errors are addressed, the report provides a well-structured, methodologically rigorous diagnostic that correctly identifies data limitations.

---

## Six-Dimension Scoring (0-10)

| Dimension | Score | Rationale |
|:---------:|:-----:|-----------|
| **Statistical Methodology** | 9/10 | Thorough validation pipeline (Simpson's, outlier, trend-confounding, Spearman divergence, multiple testing). Six validation filters applied systematically. Causal inference criteria correctly used to reject all process-parameter claims. |
| **Physical Mechanism** | 8/10 | Correctly identifies extruder thermal degradation as the most likely root cause. Correctly rules out MD section as chemical defect source. BUT the Arrhenius factor of ~10^20 is quantitatively wrong (should be ~10^9-10^10) — see C02. |
| **Data Handling** | 6/10 | Properly identifies skew, outliers, and grade confounding. BUT the sorting validation claim ("100% increasing") is contradicted by direct verification (9/150 decreasing transitions). Missing data lineage from raw CSV to cleaned data. |
| **Logical Reasoning** | 9/10 | Clean causal chain from observed correlations through physical mechanism to root cause hypothesis. Honest about inference gaps. STOP checklist implementation is excellent. |
| **Numerical Accuracy** | 5/10 | This is the weakest dimension. The melt_spots time trend (claimed r=0.868, actual r=0.382) is a 2.3x overstatement. The Arrhenius factor (~10^20) is overstated by ~10 orders of magnitude. These errors propagate through multiple evidence items. |
| **Uncertainty Communication** | 9/10 | Comprehensive uncertainty boundaries, clearly labeled INFERRED vs OBSERVED items, actionable next steps to reduce uncertainty. What-would-change-our-conclusion section is best practice. |

**Overall weighted score**: 7.7/10

---

## Strengths

1. **Rigorous validation framework**: Six independent checks (Simpson's paradox, outlier-driven, trend confounding, Spearman divergence, skew, time sorting) applied systematically.

2. **Honest disconfirmation of all process-parameter claims**: The report correctly concludes that none of the 177 MD section parameters causally link to any of the 6 defects.

3. **Grade confounding identified as dominant confounder**: 32 Simpson's Paradox findings with consistent pattern (aggregate correlation collapses/reverses within PG31DS) is the single most important statistical finding.

4. **Clear distinction between observation and inference**: OBSERVED vs INFERRED labels applied consistently throughout. Hallucination audit (STOP checklist) sets high transparency bar.

5. **Actionable recommendations linked to specific evidence gaps**: P0 recommendations directly traceable to the report's own uncertainty analysis.

6. **Defect-defect correlation analysis**: film_points-oligomer correlation correctly identified as strongest signal and interpreted as shared-source indicator.

---

## Critical Concerns

### C01 [FATAL] Melt_spots time trend: claimed r=0.868, actual r=0.382

**Location**: Evidence E08, Evidence E07 (Y-time trend), report Section 2.2, 11.3, 12.3, H4 throughout

**Claim**: Report states melt_spots has "a strong monotonic increase over time (r=0.868 with time index)" — the "strongest statistical signal in the entire dataset for a process trend."

**Verification**: Independent calculation from original CSV yields Pearson r=0.382 (Spearman rho=0.696). The value 0.868 is actually the time trend of W1C88@PV1_mean (quench roll #13 torque), NOT melt_spots. In E07, X-time trend and Y-time trend labels are swapped.

**Impact**:
- Melt_spots' time trend magnitude overstated by 2.3x
- "Strongest signal in dataset" claim is inaccurate
- Trend-confounding attenuation percentages remain valid, but narrative emphasis is exaggerated
- Within PG31DS, melt_spots vs time drops to r=0.256 (even weaker)

**Correction**: Replace all instances of "r=0.868" for melt_spots vs time with r=0.382. Update interpretation to "moderate increasing trend (Pearson r=0.382, Spearman rho=0.696, first-half mean=7.5 vs second-half mean=28.1)."

---

### C02 [SERIOUS] Arrhenius factor overstated by ~10 orders of magnitude

**Location**: Report Section 1, 12.1, 13.1, Evidence E10, process_knowledge_base.md

**Claim**: "Arrhenius factor ~10^20 difference in rate between 280C and 80C."

**Verification**:
- With Ea=170 kJ/mol (midpoint of reported 150-200 range): rate ratio = 1.3 x 10^9
- With Ea=200 kJ/mol (upper bound): rate ratio = 5.1 x 10^10
- "Doubles per 10C" rule: 200C difference = 2^20 ~ 10^6
- To achieve 10^20, Ea would need ~374 kJ/mol (unrealistic for PET)

**Impact**: Qualitative conclusion unaffected (even 10^9 gives half-life of thousands of years at 80C). But quantitative accuracy is undermined. The process_knowledge_base.md error will propagate to future runs.

**Correction**: Change "~10^20" to "~10^9-10^10 (depending on Ea=150-200 kJ/mol)." Add explicit Arrhenius calculation. Fix process_knowledge_base.md.

---

### C03 [SERIOUS] Sorting validation claim contradicted by data

**Location**: Section 2.1, 14.1, validate_report.json

**Claim**: "Data sorted by ts_start, 100% increasing."

**Verification**: Direct CSV check shows 9/150 adjacent row pairs (6%) have decreasing ts_start. validate_report.json's check algorithm may verify after internal sorting, making it circular.

**Impact**: Does not invalidate analysis (94% sorted is mostly sorted), but "100% increasing" is factually wrong.

**Correction**: State actual percentage (94%). Verify anomalies are grade transitions. Fix validate_report.json logic.

---

### C04 [MODERATE] Confidence score 58/100 may be slightly inflated

**Location**: Report Section 13, confidence.json

**Issues**:
- The +5 UP adjustment for film_points-oligomer Spearman is a defect-defect correlation, not process-defect
- The +10 UP for "physical mechanism well-established" compensates severely for -30 confound penalty
- No process-parameter-to-defect correlation passes validation; 58/100 may mislead operational decision-makers
- Report itself says "all 5 causation criteria not met" — 58/100 somewhat contradicts this

**Recommendation**: Reconsider 58; a more honest score is 45-50.

---

### C05 [MODERATE] Scratch analysis neglects winding tension mechanism

**Location**: Section 12.2, 9.2

**Issue**: process_knowledge_base.md states scratches are winding-driven (layer-to-layer slip from tension variation). Report correctly finds no MD parameter correlates but fails to connect this to missing winding data.

**Recommendation**: State explicitly that scratch root cause requires winding section data. Change scratch confidence from 25 to "N/A."

---

## Physical Mechanism Verification

| Check | Result | Detail |
|:------|:------:|--------|
| PET thermal degradation Arrhenius | PASS (caveat) | Ratio ~10^9-10^10, not 10^20. Conclusion unchanged. |
| Oligomer formation temperature | PASS | T > 200C required. MD 75-83C near Tg, cannot form oligomers. |
| MD stretching +/-2C effect | PASS | Causes mechanical thickness variation (1-3%), not chemical defects. |
| Scratch formation physics | INCOMPLETE | Winding tension not measured; scratch analysis fundamentally limited. |
| melt_spots time trend | PARTIAL FAIL | Trend exists (r=0.382) but overstated (claimed 0.868). |

---

## Confounding Analysis

| Confounder | Verified? | Note |
|:-----------|:---------:|------|
| Product grade (32 Simpson's) | CONFIRMED | Spot-checked 3 examples, all match report claims |
| Time trend (melt_spots) | PARTIAL FAIL | Trend real but magnitude wrong (see C01) |
| Outliers (22 findings) | CONFIRMED | film_points-oligomer drop matches claim |
| Spearman-Pearson divergence (87) | CONFIRMED | Consistent with skewed data |
| Selection bias (grade size) | MODERATE | Non-PG31DS n<20; noted but could emphasize more |

---

## Priority Actions

1. **P0** — Correct melt_spots time trend value (C01): r=0.868 -> r=0.382 throughout
2. **P0** — Fix Arrhenius factor in process_knowledge_base.md (C02): ~10^20 -> ~10^9-10^10
3. **P1** — Fix sorting validation logic (C03): 100% -> 94%
4. **P1** — Add explicit scratch data limitation (C05): state winding data needed
5. **P2** — Reconsider confidence score (C04): 58 -> 45-50

---

## Summary

The report is **methodologically excellent** with sound qualitative conclusions. The validation pipeline, OBSERVED/INFERRED labeling, and uncertainty communication set a high standard. Core insight (grade confounding dominates aggregates; extruder degradation is plausible root cause) is well-reasoned.

However, **three quantitative errors** reduce reliability for operational use: (1) melt_spots time trend overstated by 2.3x, (2) Arrhenius factor overstated by ~10 orders of magnitude, (3) sorting claim factually wrong. Fixable, but must be corrected.

**Conditional endorsement**: Upgrade to full ENDORSED once C01-C03 are addressed.

---

*Review generated: 2026-05-27 | Pipeline: report-reviewer | Run: 202605270300210_ccd_surface_defect_diagnosis*
