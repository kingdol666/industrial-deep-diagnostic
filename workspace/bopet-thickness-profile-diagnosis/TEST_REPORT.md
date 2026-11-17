# BOPET 双拉薄膜「膜厚剖面」诊断测试报告

日期：2026-10-17 ｜ 场景：BOPET L3 双向拉伸薄膜线（GP12，12 μm 包装级光膜）
数据窗口：2026-09-20 00:00 ～ 2026-10-10 23:50（10 min 主表，+08:00）

---

## 0. 结论摘要

1. **已给 BOPET 模板数据新增独立膜厚横向剖面 CSV**：`时间 × 单位 × 63 个横向测点`，10 min 一帧，pos_01=北侧边缘、pos_63=南侧边缘，单位 μm；并同步接入生成脚本、生成清单、数据说明与模板文档。
2. **剖面被 E-1H 正确识别为 PROF 异构源**：真实 run 中 E-1H 共识别 2 个源（膜厚剖面 + 操作备注文本）、24 个 `HX-*` 特征；18 个剖面特征全部 `stats_eligible=true`、单位 μm；H1–H8 门禁 exit 0。剖面没有被 E-1 误合并进主表。
3. **诊断结论与注入真值一致**：两轮完整诊断都判定 **H1 = TDO 北侧第 4 分区（Z4）加热/送风效能下降 + 执行器饱和**；北侧 0–650 mm 窄带增厚、南侧稳定、全幅平均厚度基本不变，原料/回料、环境降温、换网等候选被降权或排除。
4. **两轮都跑到终态**：
   - 自动 run（UI/DB 当前指向）：`202610170348389_BOPET_L3_profile_diag`，Judge **90 pass**、物理审计 **ENDORSED**、HTML 审核 **94 pass**、finalize **PASS**、log-check exit 0（仅 VLM 缺失警告）。
   - 手工补齐 run：`202610170255216_BOPET_L3_profile_diag`，Judge 首评 68（major_issues）→ 按协议修复后复评 **90 pass**、审计 **ENDORSED**、HTML 审核 **91 pass**、finalize **PASS**。该 run 用于验证“引擎提前 end_turn”后的协议级补齐路径。
5. **发现并修复了一个真实工程缺陷**：化验表（8 项互不相关指标）曾被 PROF 检测器误判为“剖面”，生成 18 个伪特征；已在宽表回退判据中加入“相邻列时序相干性”门槛（median adjacent r ≥ 0.25），新增回归用例，49 用例 / 506 断言全绿，双镜像同步。
6. **仍需知道的限制**：VLM 阶段因无视觉模型被跳过（L4 只有 caption_fallback）；剖面的“边缘带偏差/横向不匀率”与在线 GA 口径不同（在线 CV 有约 +1.06 pp 尺度偏置，两轮报告均披露或由工件可复算）；H1 的子机理（加热器老化 / 风道风阀堵塞 / 换热器结垢）在现有空气侧测点下不可区分。

---

## 1. 新增数据：膜厚横向剖面

### 1.1 文件与格式

文件：`workspace/bopet-data-template/02_data/L3_GA_TH_PROFILE_10min.csv`
同时放入测试场景：`data/L3_GP12_20260920-20261010_profile/L3_GA_TH_PROFILE_10min.csv`

| 项目 | 说明 |
|---|---|
| 规模 | 3024 行 × 65 列（时间 + 单位 + 63 个位置列） |
| 时间列 | `时间`，`YYYY-MM-DD HH:MM:SS`，10 min 一帧 |
| 时间偏移 | 扫描完成时刻比 DCS 采样点晚 5 min（如主表 00:00 ↔ 剖面 00:05） |
| 位置列 | `pos_01` … `pos_63`，距北侧切边 50–6250 mm，间距 100 mm |
| 方向约定 | **pos_01 = 北侧边缘，pos_63 = 南侧边缘** |
| 单位列 | `单位 = μm`（供 E-1H 识别量纲，contract 中 unit=μm） |
| 数值 | 该位置膜厚，3 位小数；无缺失 |
| 语义 | 一行 = 一次全幅扫描；63 个值构成该时刻的横向厚度向量 |

关键点：这是**独立文件**，不并入主表的 54 列；E-1 因时间轴错开 5 min、联合后 6048 行 > 1.5×3024 而放弃合并，主表保持 3024 行 × 54 列，剖面由 E-1H 作为 PROF 源单独处理。

### 1.2 生成逻辑与故障注入

生成脚本：`workspace/bopet-data-template/05_生成脚本/generate_template_data.py`（固定 seed，确定性可复现）。

剖面 = 12.0 μm 基准 + 常态横向弓形（中心略薄、两侧略厚，±0.03 μm）+ 小幅 3 波横向驻波 + 测点固定增益误差 + 逐帧测量噪声 + 北侧故障场：

- 故障与主表共用同一时间进度：2026-09-28 00:00 起 TDO 北侧 Z4 加热能力以 0.15 ℃/天缓降，累计 1.95 ℃；HOUT-N 由 44.5% 升到 80% 上限。
- 剖面故障场为 `0.114 μm/℃ × fault × exp(-(距北边距离/1200mm)²)`，末端北边缘约 **+0.22 μm（≈+1.85%）**，中心约 +0.02 μm，南侧几乎不变。
- 全幅平均厚度始终保持在 **11.98–12.05 μm**，与在线平均厚度“正常”一致。

### 1.3 物性一致性核验（生成后）

| 指标 | 基线（9/20–9/27） | 末 7 天（10/4–10/10） |
|---|---:|---:|
| 剖面左边缘带偏差 EDGE-L | +0.69% | +1.96% |
| 剖面右边缘带偏差 EDGE-R | −0.12% | −0.41% |
| 剖面横向不匀率（行 std/mean） | 0.50% | 0.93% |
| 全幅平均厚度 | 12.000 μm | 12.029 μm |

与主表交叉验证（逐行 merge_asof）：

- 剖面 EDGE-L vs 在线 `L3-GA-EDGE-N01`：**r = 0.994**
- 剖面 EDGE-L vs 在线 `L3-GA-TH-CV01`：**r = 0.997**
- 剖面 EDGE-L vs 北侧 `L3-TDO-N-ST-Z4-TE01`：**r = −0.970**
- 剖面 EDGE-L vs 南侧 `L3-TDO-S-ST-Z4-TE01`：**r = 0.019**
- 剖面 EDGE-L vs `L3-TDO-N-Z4-HOUT01`：**r = 0.980**

注：剖面行 CV 绝对值低于在线 GA-CV（约 0.5→0.9% vs 1.4→2.2%），因为 63 个 100 mm 测点无法表达扫描仪的高频横向不匀；两者相关性 0.997，趋势与空间选择性一致。两轮报告均把这一口径差列为已知限制。

---

## 2. 接入与预检（E-1 + E-1H）

### 2.1 E-1 主表选择

`data_preprocessor.py --data-path data/L3_GP12_20260920-20261010_profile`：

- 选中主表：`L3_line_main_10min.csv`（3024 行 × 54 列，10 min 栅格）
- 合并策略：**abandoned** — 剖面 3024 行（时刻错开 5 min）+ 化验表 252 行与主表外连接后 6048 行 > 1.5×3024，按防膨胀门放弃合并，保留最大单表
- 结果：主表不被 63 个位置列污染；剖面留给 E-1H

### 2.2 E-1H 结果

`build.py --raw-path data/L3_GP12_20260920-20261010_profile --run-dir <run>`：

- `status: ok`，sources = 2
  - `L3GATHPROFILE10MIN`：shape=profile，featured，3024 snapshots
  - `text-src`：shape=text，featured，6 annotations
- 24 个 contract 列：18 个 PROF 特征 + 6 个 TXT 特征
- PROF 18/18 `stats_eligible=true`，unit=μm（N 为无量纲），coverage=1.000，n_inputs=63
- `preprocessed_data_hetero.csv`：3024 行，与锚表行序一致，HX 列仅追加在表尾
- 质量门 `hetero_quality_gate`：**exit 0**（H1–H8 全过）
- 剖面特征示例（真实 run）：
  - `HX-PROF-...-EDGE-L-DEV`：min 0.0748 → max 0.2947 μm
  - `HX-PROF-...-EDGE-R-DEV`：min −0.0683 → max −0.0062 μm
  - `HX-PROF-...-MEAN`：11.9795 → 12.0523 μm
  - EDGE-L vs GA-EDGE-N r=0.9943；vs GA-CV r=0.9973

### 2.3 发现并修复：化验表被误判为 PROF

首次预检出现 **3 个源、42 列**：除剖面外，化验表 `L3_lab_quality_2h.csv`（雾度/晶点/收缩率/拉伸强度/含水率等 8 项互不相关指标）被宽表回退判据误判为“剖面”，生成 18 个无意义特征。

根因：回退判据只看“时间列 + ≥8 个数值列 + 量级比 ≤1e4”，而 8 项化验指标的量级比约 150，足以通过；但这些列是不同物理量，不是同一物理量沿位置的扫描。

修复（`.claude/skills/industrial-hetero-preprocessor/scripts/heterocore/shapes/prof.py`）：

- 新增 `ADJ_COHERENCE_MIN = 0.25`：宽表回退必须同时满足“相邻列在时间上相干”（median adjacent Pearson r ≥ 0.25）
- 位置命名命中 `pos_*` 的宽表不受此门槛影响
- 实测：剖面相邻列中位相关 0.501（min 0.412，100% > 0.3）；化验表中位相关 0.086（min −0.010）；主表 0.018
- 新增回归用例 `p1b-fallback-coherence`：不透明列名的真剖面仍被识别；8 项化验表不再被识别，拒绝原因明确写“not spatially coherent”
- 测试：**49 用例 / 506 断言 / 0 失败**；`.agents/skills` 与 `.hermes/skills` 双镜像 555 文件一致

修复后重跑：2 个源、24 列、门禁 exit 0。此缺陷已同步写入 `references/method_notes.md` §2 与 `SKILL.md` 输入说明。

---

## 3. 诊断执行过程

### 3.1 自动 run（当前 UI/DB 指向，主结果）

| 阶段 | 时间（本地） | 结果 |
|---|---|---|
| run 创建 / setup | 11:48 | `202610170348389_BOPET_L3_profile_diag` |
| E-1H + inspect | 11:49–11:50 | 2 源 / 24 列；主表 3024 行 |
| 本体 / 数据处理器 | 11:50–12:06 | 8 张图、profile_analysis、time_lag、anti_spurious 等 |
| 诊断 | 12:14 | DETERMINED H1；overall 76 / MEDIUM；L5 |
| Judge | 12:17 | **90 pass**，0 blocking |
| 报告 | 12:24 | report.md 25 KB |
| 物理审计 | 12:30 | **ENDORSED** |
| HTML + HTML 审核 | 12:35–12:40 | diagnostic-report.html 57 KB；审核 **94 pass** |
| finalize / run_completed | 12:40–12:41 | PASS；log-check exit 0（仅 VLM 警告） |

该 run 的 manifest：11/11 步全部 completed；`diag_iters_total=0`、`repair_spawn_count=0`（Judge 首评即通过）。DB 状态 `completed`，外部 run 视图返回 `report_md_path` 指向该 run 的 `report.md`。

### 3.2 手工补齐 run（原 run，用于验证引擎失败后的协议路径）

| 阶段 | 时间（本地） | 结果 |
|---|---|---|
| run 创建 / 前四阶段 | 10:55–11:18 | E-1H 2 源/24 列；数据处理器完成 |
| 诊断 | 11:18–11:28 | 首版 diagnosis（later judge 发现 5 项 blocking） |
| 引擎 end_turn | 11:29 | claude 在进入 Judge 前结束回合，未产出 report.md → 任务标 failed |
| 手工 Judge | 11:50–11:57 | **68 / major_issues**，B1–B5 |
| 修复轮 | 11:59–12:08 | B1–B4 改写诊断；B5 补 canonical wrapper；H1 80 / overall 76 |
| 复评 | 12:08–12:14 | **90 pass**，0 blocking |
| 报告 / 审计 / HTML | 12:14–12:50 | report.md 85 KB；审计 **ENDORSED**；HTML **91 pass**（移动端溢出后已修至 scrollWidth=390）；finalize **PASS** |

该 run 的 `run_manifest` 最终 `status=completed`、`diag_iters_total=2`、`repair_spawn_count=2`；log-check exit 0，但保留 2 个警告：VLM ontology grounding weak（VLM 跳过）、timestamp non-monotonic（手工 resume/repair 事件顺序）。

### 3.3 两轮结果对照

| 项 | 自动 run | 手工补齐 run |
|---|---|---|
| 主结论 | H1 TDO 北侧 Z4 加热/送风效能下降 + 执行器饱和 | 同 |
| 诊断类型 | DETERMINED（bounded） | DETERMINED |
| H1 / 整体 | 76 / 76（MEDIUM） | 80 / 76（H1 HIGH 下沿） |
| H2 / H3 | 60 / 54（并行/放大） | 44 / 54（次要/放大） |
| 证据等级 | L5 | L1+L3+L5 |
| Judge | 90 pass | 68 → 修复 → 90 pass |
| 审计 | ENDORSED | ENDORSED |
| HTML 审核 | 94 pass | 91 pass |
| finalize | PASS | PASS |
| 报告规模 | 25 KB | 85 KB |

两轮在**根因方向、空间形态、关键数字、排除项**上收敛；差异主要在 H2 的权重口径（自动 run 把 9/27 配方切换后的约 0.476 pp 过渡段计入 H2 的并行贡献，手工 run 更保守地标为次要光学因素）与 H1 置信度（76 vs 80）。两种表述都没有把 H1 写成 PROVEN，也没有声称子机理已确定。

---

## 4. 诊断结果

### 4.1 主结论（自动 run 原文摘要）

> TDO 北侧 Z4 拉伸区（第 4 区）加热/送风效能下降并进入执行器饱和（HOUT-N 44.5%→77.8%，末端触及 80% 上限），在共用 240.0℃ 设定下北侧实际温度较南侧低约 1.4–1.9℃，导致北侧核心增厚带约 0–650 mm（pos_01–pos_07；受影响带延伸至 pos_01–pos_12 约 0–1150 mm）局部横向拉伸不足而增厚；YIELD 总降 1.652 pp 中约 0.476 pp 发生在 9-27 配方/回料切换后的过渡段，H1 主要解释 10-04 后的降幅与横向劣化，是全幅平均厚度正常而横向分布劣化的主导原因；原料切换/回料提高与环境降温分别解释光学/热性能变化和放大斜率，不能解释北侧单侧空间形态。

### 4.2 关键证据（自动 run，P0→P2 / 末 24 h）

| 指标 | 数值 |
|---|---|
| YIELD | 98.658% → 98.182% → 97.006%（末 24 h 约 96.5%） |
| EDGE-N | 0.351% → 0.662% → 1.453% |
| EDGE-S | −0.311% → −0.340% → −0.365%（稳定） |
| CV | 1.400% → 1.640% → 2.208% |
| HOUT-N | 44.507% → 55.443% → 77.775%（末端 78.7–81.0%，触 80% 上限） |
| TE-N / TE-S | 239.99 → 239.59 → 238.56℃ / 240.00℃；南北温差扩大至约 −1.9℃ |
| 剖面北带均值 | +0.1678 μm（核心 7/63 点，约 11% 幅宽） |
| 剖面全幅均值 | +0.0287 μm（约为 ±0.20 μm 公差的 14%） |
| 均值增量分解 | 核心北带贡献约 65.0%；含北过渡带合计约 93.5%；南带几乎不贡献 |
| 剖面方差 | 核心带贡献约 61.5%，CV 越过 2.0% |

### 4.3 竞争假设

自动 run：H1 主导；H2 原料切换 + 回料 8%→12%（60，并行贡献，解释光学/收缩与部分过渡段）；H3 环境降温（54，放大器，非触发）；H4–H10（换网/测厚仪/链铗/模头/MDO/风机/扫描时差）排除置信度 92–96。

手工 run 的 Judge 额外要求并已修复：删除“42 个批次方向一致”的不实表述（实际 25 正/17 负、批内 pooled r=0.082）；删除不存在的 ENV 变点时间；把 YIELD 从“阈值型判废”改为 INFERRED 连续剂量-响应；修正均值-分布分解的加权算术（北带 +0.0186、北过渡 +0.0095、中部 +0.0007、南过渡 +0.0014、南带 −0.0017 μm）。

### 4.4 与注入真值对照

| 真值（生成脚本 `generation_manifest.json`） | 诊断结果 | 判定 |
|---|---|---|
| 2026-09-28 起 TDO 北侧 Z4 加热能力缓降，设定 240℃ 不变，HOUT-N 44.5%→80% 饱和 | H1 完全相同；HOUT-N 44.5→77.8%（末端 80%）、TE-N 低于设定约 1.9℃ | ✅ |
| 北边缘厚度偏差 +0.35%→+1.85%，CV 1.40%→2.50%，均值正常 | EDGE-N 0.351→1.453%（末段 1.799%）、CV 1.400→2.208%（末段 2.453%）、均值 +0.0287 μm | ✅ |
| 剖面北带渐进增厚、南侧基本不变 | 北带 +0.1678 μm，峰值 pos_04 +0.1753 μm；南带 −0.0178 μm | ✅ |
| 干扰项：9/27 配方/回料切换、9/29 与 10/6 换网、10/4 降温 | H2 并行贡献（含 0.476 pp 过渡段）、H4 排除、H3 放大器 | ✅ |
| 子机理（加热器老化/风道/换热器）未给出唯一答案 | 报告明确“不可区分”，未把 H1 写成 PROVEN | ✅ 诚实 |

---

## 5. 验收标准与结果

| # | 验收标准 | 结果 | 证据 |
|---|---|---|---|
| A1 | 剖面 CSV 独立、格式合法、可重复生成 | **PASS** | 3024×65；generator + manifest sha256；确定性 seed |
| A2 | 剖面与主表时间对齐、物性一致 | **PASS** | EDGE-L vs GA-EDGE-N r=0.994；vs GA-CV r=0.997；南侧 r=0.019 |
| A3 | E-1 不把剖面误合并进主表 | **PASS** | merge abandoned，6048 > 1.5×3024；主表 3024×54 |
| A4 | E-1H 识别 PROF 并产出可用特征 | **PASS** | 2 源/24 列；18/18 stats_eligible；unit=μm；gate exit 0 |
| A5 | 化验表不再被误判为 PROF | **PASS** | 回归用例 + 49/506 全绿；真实 run 2 源 |
| A6 | 完整诊断按 skill 流程跑到终态 | **PASS（自动 run）** / **PASS（手工补齐 run）** | 两 run manifest 11/11 completed；finalize PASS；log-check exit 0 |
| A7 | Judge 质量门 ≥90 且无 blocking | **PASS** | 自动 90；手工 68→修复→90 |
| A8 | 物理终审 ENDORSED | **PASS** | 两 run optimizer.md 均含 ENDORSED |
| A9 | HTML 页面可渲染且审核通过 | **PASS** | 自动 94；手工 91；1440×900 与 390×844 实测；手工页移动端溢出已修（scrollWidth=390） |
| A10 | 诊断结论命中注入真值 | **PASS** | H1 方向、空间形态、量级、时间线、干扰项均一致 |
| A11 | 不确定性如实披露 | **PASS** | 子机理不可区分、VLM 跳过、CV 口径差、批内弱、H2/H3 权重差异 |
| — | 完全无人工介入的“单 run 一键到底” | **PARTIAL** | 首个 run 在 Judge 前 end_turn；backend 续跑自动产生第二个完整 run；第一个 run 由协议手工补齐 |

---

## 6. 观察到的系统问题与处理

1. **claude 引擎提前 end_turn**：首个 run 在写完诊断后、Judge 前结束回合，未产出 report.md，任务被守卫标为 failed。两次 resume 时旧会话在同一个 tool_result 后静默结束（转录 18 min 无增长、CPU 空闲）。backend 的第二次 continue 新建了第二个 run 并自动跑完（主结果）。建议排查 claude SDK 的 resume/end_turn 语义与重试策略。
2. **task 条目与 run 状态不同步**：run 视图已 completed，但 `GET /api/external/v1/tasks/TASK-MVBT01Y5-IFHY` 仍返回 failed + null result（task 条目未随新 run 更新）。建议 task manager 在 run 完成时按 runId 回填结果。
3. **上游 schema 漂移**：首个 run 的 `validate_report.json`/`feature_summary.json`/`ontology.json` 不符合 canonical schema；已用真实数据生成 wrapper（保留原有检查于 `checks`）并通过 validate.mjs。建议在 data-processor/context-builder 源头修复，避免每次靠 wrapper。
4. **finalize 依赖 `input_manifest.time_column`**：首个 run 的 inspect 产物缺该字段，导致时序图被判 MISSING；补 `time_column=时间` 后 finalize PASS。建议 inspect 固定写入该字段。
5. **VLM 阶段被跳过**：引擎无视觉模型，`vlm_analysis` 记录 `no_vision_model`，L4 仅 caption_fallback；两 run 报告均如实披露。若需要像素级视觉复核，需配置 vision 模型或把关键图交给支持视觉的 harness。
6. **PROF 误判**：已在 skill 内修复并加回归用例（见 §2.3）。

---

## 7. 产物索引

### 主结果（自动 run，UI/DB 指向）
- 报告：`workspace/diagnostic-runs/202610170348389_BOPET_L3_profile_diag/report.md`
- HTML：`workspace/diagnostic-runs/202610170348389_BOPET_L3_profile_diag/diagnostic-report.html`
- 物理审计：`.../optimizer.md`
- Judge：`.../05_review/judge_feedback.json`（90 pass）
- HTML 审核：`.../05_review/html_review.json`（94 pass）
- 证据闭环：`.../evidence_closure_report.json`（PASS）
- 异构合同：`.../07_hetero/column_contract.json`、`hetero_manifest.json`、`features/PROF-L3GATHPROFILE10MIN.csv`
- 运行摘要：`.../run_summary.json`

### 手工补齐 run（引擎失败验证路径）
- 报告：`workspace/diagnostic-runs/202610170255216_BOPET_L3_profile_diag/report.md`（85 KB）
- HTML：`.../diagnostic-report.html`（81 KB）
- Judge：`.../05_review/judge_feedback.json`（68 → 90）
- 审计：`.../optimizer.md`（ENDORSED）
- 闭环：`.../evidence_closure_report.json`（PASS）

### 数据与模板
- 模板剖面：`workspace/bopet-data-template/02_data/L3_GA_TH_PROFILE_10min.csv`
- 生成脚本：`workspace/bopet-data-template/05_生成脚本/generate_template_data.py`
- 生成清单：`workspace/bopet-data-template/05_生成脚本/generation_manifest.json`
- 剖面说明：`workspace/bopet-data-template/02_data/膜厚剖面数据说明.md`
- 测试场景数据：`data/L3_GP12_20260920-20261010_profile/`
- 预检：`workspace/bopet-thickness-profile-diagnosis/precheck/07_hetero/`
- 本报告：`workspace/bopet-thickness-profile-diagnosis/TEST_REPORT.md`

---

## 8. 建议

1. **数据侧**：真实产线导出时保留 pos_01→pos_63 的顺序与北/南方向说明；若测点数量不同，仍按 `pos_01..pos_N` 宽表或 `时间,位置,值` 长表给出，并在《参数代号对照说明》里写清位置轴。
2. **诊断侧**：把“剖面边缘带 vs 在线边缘偏差”的口径差写入常规数据说明；在线 CV 与剖面重算 CV 的尺度偏置应作为固定披露项。
3. **工程侧**：优先修复 claude resume/end_turn 与 task manager 回填；把 upstream schema、`input_manifest.time_column` 的生成责任放回对应 producer，减少 finalize 前的手工 wrapper。
4. **视觉侧**：若需要 VLM 参与，配置 vision 模型并在 run_config 中声明；否则继续保留 `caption_fallback` 与“无独立视觉证据”的披露。
