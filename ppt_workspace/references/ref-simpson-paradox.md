# Simpson悖论在工业数据分析中的应用

## 摘要
Simpson悖论（又称Yule-Simpson效应）指在聚合层面上表现出的相关性在按某个混杂因子（confounder）分层后发生反转或消失的现象。在工业数据分析中，产品等级/型号（product grade/model）、班次（shift）、操作人员（operator）、设备（asset/fixture）是常见的混杂因子。本诊断报告的32个Simpson悖论发现表明**产品等级（model）是主导混杂因子**，几乎所有工艺参数-缺陷相关性均为等级间差异的产物。

## 关键数据点

| # | 数据/论断 | 来源 | 可信度 |
|---|----------|------|--------|
| 1 | 制造车间实例：夜班FPY 81.9% vs 白班93.0%，但分层后夜班在"简单"和"困难"两类产品中均优于白班——悖论因夜班处理了900件困难产品vs白班100件 | Material Model "Simpson's Paradox on the Shop Floor" | 高 |
| 2 | 本报告检测到32个Simpson悖论，全部与产品等级（model）相关，聚合相关性在主导等级PG31DS内衰减或反转 | 诊断报告 Section 14.2 (用户材料) | 高 |
| 3 | W1C80@PV1_std↔film_points: 全数据集r=0.554 → PG31DS内r=0.217（衰减61%），且Spearman=-0.1071（符号反转） | 诊断报告 Section 14.2 (用户材料) | 高 |
| 4 | W1C4B@PV1_std↔film_points: 全数据集r=0.367 → PG31DS内r=-0.197（方向完全反转） | 诊断报告 Section 14.2 (用户材料) | 高 |
| 5 | film_points↔oligomer：全数据集r=0.913 → PG31DS内r=0.838——这是极少数在分层后"衰减但保持"的案例 | 诊断报告 Section 12.2 (用户材料) | 高 |
| 6 | Shmueli & Yahav (2018) 提出用分类回归树（CART）自动检测大数据中的Simpson悖论，可用于制造业运营管理 | Production and Operations Management | 高 |
| 7 | 制造环境中典型的混杂因子：产品型号/等级（mix）、设备/夹具（asset）、操作员技能等级（skill）、时间周期（time） | Material Model 分析 | 高 |
| 8 | D'Errico (2014) 在《Measurement》期刊上讨论了工业工程中的Yule-Simpson悖论，包括质量功能展开、零件比较数据合并、潜在混杂交互作用 | Measurement期刊论文 | 中 |

## 详细内容

### 什么是Simpson悖论

Simpson悖论是指：当数据按某个第三变量分层后，各层内部的统计关系与合并后的聚合关系方向不同（甚至完全相反）的现象。

```
聚合视角： 白班 93% > 夜班 81.9% → 白班表现更好
分层视角： 简单产品  夜班 96.1% > 白班 93.6%  → 夜班表现更好
           困难产品  夜班 87.0% > 白班 85.0%  → 夜班表现更好
```

本例中，产品难度（product mix）是混杂因子。夜班接受了大比例的困难产品，聚合时被"拉低"，掩盖了其实际优势。

### 工业应用中的典型场景

| 场景 | 聚合关系 | 混杂因子 | 真相（分层后） |
|:----:|:-------:|:--------:|:-------------:|
| 班次绩效对比 | A班 > B班 | 产品组合难度 | B班在各类产品中更优 |
| 供应商质量评级 | 供应商X > 供应商Y | 操作员技能 | 相同操作员下Y更好 |
| 设备效率对比 | 设备A > 设备B | 产品类型 | 相同产品下B更优 |
| 工艺参数优化 | 温度↑ → 缺陷↓ | 产品等级 | 同等级内无效果 |

### 本报告中的Simpson悖论检测

诊断报告对全部177个工艺参数-缺陷相关性进行了分层分析：

1. **发现数量**：32个Simpson悖论发现
2. **最严重级别**：CRITICAL（部分出现方向反转）
3. **主导混杂因子**：产品等级（model），9个等级，PG31DS占44%（n=67）
4. **置信度影响**：-20至-30分

#### 典型案例

| 相关性对 | 聚合r | PG31DS内r | 变化 | 结论 |
|---------|:----:|:---------:|:---:|:----:|
| W1C80_std↔film_points | 0.554 | 0.217 | 衰减61% | 无效 |
| W1C4B_std↔film_points | 0.367 | -0.197 | **反转** | 无效 |
| F_PS002_mean↔bubbles | -0.331 | +0.178 | **反转** | 无效 |
| film_points↔oligomer | 0.913 | 0.838 | 衰减8% | **保持** |

### 为什么要向客户强调Simpson悖论

1. **直观易懂**：用"盲人摸象"类比，客户能快速理解
2. **直接指导行动**：P0推荐行动就是"按产品等级单独分析"
3. **体现专业度**：展示了超越简单相关分析的严谨统计方法
4. **可操作建议**：产品等级混杂不是统计问题，而是工艺设定问题——不同等级使用不同的工艺参数设定值，导致聚合层面产生虚假相关性

### 避免Simpson悖论的方法

1. **分层分析（Stratification）**：按潜在混杂因子分层计算
2. **实验设计（DOE）**：在每个等级内做独立的实验设计
3. **倾向评分匹配**：平衡各等级间的协变量分布
4. **多水平模型（Mixed-effects model）**：将等级作为随机效应

## 来源列表
- Material Model Blog. "Simpson's Paradox on the Shop Floor: Segment Before You Decide." (https://www.materialmodel.com/blog/simpson-factory-paradox)
- Shmueli, G. & Yahav, I. (2018). "The Forest or the Trees? Tackling Simpson's Paradox with Classification Trees." *Production and Operations Management*, 27(4), 796-810.
- D'Errico, G.E. (2014). "Aggregation of comparisons data and reversal phenomena of metrological interest." *Measurement*, 55, 390-396.
- UBC MDS Course DSCI 554. "Lecture 2: Confounding and Randomized vs Non-randomized Studies." (https://ubc-mds.github.io/DSCI_554_exper-causal-inf/notes/lecture2_simpson_confounding.html)
- 诊断报告 Section 7, 14.2 (用户材料) — 32个Simpson悖论发现详情
