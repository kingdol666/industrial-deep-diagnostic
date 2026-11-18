# 分析计划 — heat_treat_sim（连续热处理线，10 天 @10min 锚定 + 异构 HX 尾部列）

- RUN_DIR: `workspace/hetero-full-sim/runs/202610162036022_heat_treat_sim`
- DATA_PATH: `07_hetero/preprocessed_data_hetero.csv`（1440 行 × 48 列 = 8 基列 + 40 HX 列）
- MODE: fast（图表预算 ≤8）；E-1/E-1H 已由前置阶段完成，本轮不重跑预处理，只做数据处理器自身的清洗/统计/可视化。

## 数据视图模式（Phase 0.2 / 1.2）

**detected_data_view_mode = `process_plus_inspection`**

| 侧 | 代表列 | 依据 |
|----|--------|------|
| 过程侧 | FUR-Z1/Z2/Z3-TEMP, FUR-SPEED, FUR-PRES, HX-MAP-*（炉膛温度场） | DCS 10min 锚定表 + 温度场快照 |
| 检查/质量侧 | FUR-OUT-TEMP, FUR-YIELD, HX-PROF-*（带材横向温度剖面 17 项） | ontology role=target；explicit_cols.targets |

## 六问（Phase 0.2）

1. **物理过程类型**：连续退火/均热热处理线；三区炉温 + 线速 + 炉压 → 带材出口温度 → 硬度/收得率。
2. **质量目标**：FUR-YIELD（%）、FUR-OUT-TEMP（°C）、HX-PROF-L1BANDTEMPPROFILE30M-{MEAN,STD,MIN,MAX,P05,P50,P95,RANGE,IQR,MAD,SLOPE-LSQ-PER100,CURV-LSQ,ZONE-1-3-MEAN,EDGE-L-DEV,EDGE-R-DEV,ARGDEV-NBR,SHIFT-EST}（18 项，explicit_cols.targets 全量并入）。
3. **候选原因**：三区（尤其后段）加热管老化掉温 / 热电偶漂移（02-05、02-06 备注）；炉膛左右不对称 → 横向剖面边部偏差；炉压异常 → 表面氧化；维护/升温事件后的过渡扰动。
4. **时间结构**：10min 锚定，2026-02-02 00:00 → 2026-02-11 23:50（1440 行）；HX 源粒度 30min（PROF）/1h（IMG）/2h（MAP）/事件（TXT）。
5. **特殊数据结构**：① 时间×位置剖面（PROF 12 位点，`07_hetero/features/PROF-*.csv` 480 快照）；② 炉膛 5×4 网格温度场（MAP 120 快照）；③ 事件锚定窗（MAINTENANCE 02-06 06:40、HEATUP 02-08 10:00）；④ 后向合并（merge_asof_backward，无插值/无前向填充）→ HX 列在锚定行上呈阶梯常量。
6. **无用的分析**：LAB-HRC 未并入锚定主表（不可与 FUR-* 直接相关，只作外部参照）；IMG 灰度未标定（只做相对漂移）；对阶梯常量 HX 列算逐行 p 值会因伪重复而虚高 → 必须按快照级（去重）复核。

## Phase 0.4 Ontology-Guided Analysis Architecture（本体引导的分析架构）

- 参数物理分组、Tier 划分、PRUNED 清单见 `analysis_parameter_selection.json`（本目录）。
- Tier 1（必须分析）：FUR-Z3-TEMP、FUR-OUT-TEMP、FUR-SPEED、FUR-YIELD、HX-PROF-MEAN/STD/EDGE-R-DEV/SHIFT-EST、HX-MAP-MEAN/ASYM-LR/CENTROID-X、HX-IMG-DarkFrac（因果链核心）。
- Tier 2：FUR-Z1/Z2-TEMP、FUR-PRES、其余 PROF 形状项、MAP-P95/HOTAREA/COLDAREA/POSMAX-*、IMG-MEAN/STD/ENTROPY/SATFRAC/FOCUS。
- PRUNED：`HX-IMG-*-N`、`HX-MAP-*-N`（整源常量计数）、`HX-MAP-*-GRAD-P95`（contract: stats_eligible=false, sparse）、4 个 TXT 协变量列（HOUR-OF-DAY/SHIFT-BUCKET-ID 作混杂对照，不进相关筛选；EVT-* 只作事件窗，不做连续预测子）。

## 假设-方法映射（Phase 1.2）

| 假设 | 陈述 | 方法 | 判别证据 |
|------|------|------|----------|
| H1 | 三区（尤其后段）炉温漂移/掉温使带材温度水平与出料温度下降 → 收得率/剖面异常 | M1+M2+M5+M6+M7 | Z3↔OUT-TEMP/PROF-MEAN 显著且 detrended 不衰减；变点与 02-06 事件对齐 |
| H2 | 维护/升温事件窗（02-06~02-08）为非稳态期，使全域统计被 regime 塌缩污染 | M5+M2+M11 | 稳态/非稳态分段相关对比；事件前后均值差 |
| H3 | 炉膛左右不对称（MAP ASYM-LR/CENTROID-X 偏移）→ 带材剖面边部偏差（EDGE-L/R-DEV） | M1+M6+M7 | ASYM-LR↔EDGE-*-DEV 滞后 CCF 显著、方向符合热流 |
| H4 | 炉压异常 → 表面氧化（IMG DARKFRAC/SATFRAC） | M1+M2 | FUR-PRES↔DARKFRAC 原始 r 与 detrended r |
| H5 | 剖面形状变化部分由横向配准漂移（SHIFT-EST）伪装配，先看 SHIFT 再解释 EDGE | M1+M2+M13 | SHIFT-EST≠0 的时间占比；SHIFT 与逐位点热图错位对照 |

Battery 判定：**不跑 `--mode full`**（无 batch 身份列 → M3 按跳过留痕）；执行 `--mode correlation` + `--mode spurious`（= M1+M2 合并管线，含 CCF/Simpson/变点/去趋势/LOO）。

## 产品分组策略

无产品/牌号分组列（单产品连续生产，batch_id 为运行级常量）→ M8 per-product 不适用；分组替代 = **运行 regime 分段**（维护前 / 维护-升温窗 / 恢复后）。

## Adaptive Decision Audit（自适应决策审计）

| 候选分析 | 决定 | 理由 |
|----------|------|------|
| M1 相关筛选（目标×预测子，显式列清单） | EXECUTE | 有 20 质量候选 + 20 预测子 |
| M2 反伪相关电池（去趋势/Simpson/变点/LOO） | EXECUTE | 时间列存在；HX 阶梯常量+趋势混杂风险高 |
| M3 批次完整性 | SKIP | 无逐行 batch/lot 身份列（batch_id 为 metadata 常量） |
| M4 异常检测（dp_toolkit anomaly） | EXECUTE | 基线方法 |
| M5 regime 检测 + 稳态过滤 | EXECUTE | 时间列 + 事件锚定（v6.5 强制） |
| M6 滞后 CCF | EXECUTE（stats 内 --time-col, max-lag 20≈200min；另跑 time_lag_compensator） | 过程+检查双驱数据 |
| M7 物理约束检查（physics_check.py） | EXECUTE | ontology relationships 可数值核对 |
| M8 per-product | NOT_APPLICABLE | 无分组列 |
| M11 事件响应对齐（自定义） | EXECUTE | EVT 列 + 时间列 |
| M13 自定义：快照级去重相关 + regime 分段相关 + 时间×位置热图 | EXECUTE | 阶梯常量伪重复与 regime 塌缩是本数据集两大伪相关源 |
| LAB-HRC 与在线量相关 | SKIP | 未并入主表（evidence gap，写入结论） |
| 全区块 `--mode full` | SKIP | 无 batch 列；不需要 batch 模式 |

## Analysis Coverage Matrix（分析覆盖矩阵）

| 维度 | 覆盖 |
|------|------|
| 纯过程 | FUR-* 过程列相关/趋势/变点（M1/M2） |
| 双驱（过程↔检查） | FUR-Z3/SPEED ↔ PROF/OUT-TEMP；MAP ↔ PROF；（M1/M2/M6） |
| 分组/混杂 | regime 分段（维护前/维护窗/恢复后）；班次/时刻协变量对照；阶梯常量伪重复披露 |
| 时序/regime | 变点 + 事件响应 + 滞后 CCF + 稳态过滤 |
| 场景专属 | 时间×位置剖面热图（PROF）；炉膛场左右不对称→边部偏差链路 |

## 明确不做（What we will NOT do）

- 不做 LAB-HRC 与在线量的相关（未并入主表，避免编造对齐）。
- 不对 IMG 灰度做绝对标定解释（只作相对漂移）。
- 不把 index 轴当真实时间（时间列真实解析）。
- 不对 HX 阶梯常量直接下"逐行显著"结论而不披露伪重复放大。
- 不生成与假设无关的装饰性图（fast 预算 8 张）。

## Baseline Script Findings and Gaps（Phase 2.7）

- **validate_report.json**（统计输入=稳态 1367 行）：400 对中 236 对显著；趋势混杂检查 0 对（spurious 聚合口径），但**逐对去趋势载荷标记 50 对存在衰减/趋势印记**，且有明显的 Pearson–Spearman 背离（Z3~YIELD r=0.899 vs ρ=0.510）→ 相关主体为 regime 水平偏移。变点：FUR-OUT-TEMP 2 个（549.90→546.36→549.96 °C），FUR-YIELD 12 个；PROF 系列 108+ 个变点为阶梯常量块边界（伪变点，已披露）。
- **expert_findings.json**（自定义 M11/M13）：分段内相关 A 0.027 / B 0.855 / D 0.739（Z3~YIELD）→ 耦合仅在维护窗与恢复段成立；水平偏移 B−A：Z3 −4.93 °C、OUT-TEMP −2.24 °C、YIELD −0.99 pt；SHIFT-EST 恒 0（H5 refuted）；DARKFRAC/SATFRAC 恒 0（H4 通道不可测）。
- **anomaly_report.json**：8 个区间；主形态是台阶/平台（由变点捕捉），非孤立点异常。
- **physics_check.json**：2 项检查（thermal_expansion 未检出耦合 r=-0.2365；arrhenius_kinetics 合理，rate ratio 32.05）；无物理不可能配置。
- **Gaps（人工工艺工程师会追问的）**：① LAB-HRC 未并入主表 → 硬度侧闭环缺失；② 相机无暗帧/标定 → IMG 通道无法与过程辐射分离（H6 indeterminate）；③ 速度方差 ±1.4% → t_res=L/v 机理无功效（indeterminate）；④ 无冷却段参数与来料记录。均已写入 `rag_validation_report.json` 与 `data_analysis_conclusion.json.handoff_to_diagnostician.evidence_gaps`。
- **图表修正记录**：adaptive_charts.py 误检 2D 场（FUR-Z1-TEMP × HX-MAP-POSMAX-Y），产出 6 张垃圾等高线图 → 已删除文件并在 `plot_manifest.json.metadata.excluded_charts` 留痕；plot_verification = PLOT_VERIFICATION_PASSED（5 张，含 CRITICAL 剖面热图）。
