# 根因可分析性评估：这些数据集能否被当前诊断系统分析出根因？

> 评估基准日 2026-09-10，代码版本 `v4-AgentWorkShopIntegrate`。
> 系统能力边界全部来自代码审查（引用 文件:行号），非推测。

## 结论总表

| 数据集 | 能否进管线 | 能否出根因 | 预期表现 | 适配工作量 |
|---|---|---|---|---|
| TEP（经典版，已拉取） | ✅ 零改造 | ✅ 能（15/21 类有真值可评） | 8/11 可检故障预期 DETERMINED；3/9/15 预期 COMPETING_SET/NEEDS_DATA（这是校准正确的表现） | 小：外供变量语义表 |
| SKAB（已拉取） | ✅ 零改造 | ✅ 能 | 阀门类最易，气蚀/转子不平衡类次之；COMPETING_SET 校准可在此验证 | **零** |
| IndPenSim（已拉取） | ✅ 已适配 | ✅ 能（真值最完整：窗口级） | 曝气/流加类故障预期可判；离线 NaN 列需 processor 正常降级 | 中：已由 prep 脚本完成 |
| SWaT（未拉取，申请制） | ⚠️ 可进但建议预切 | ✅ 能（攻击文档即真值） | 51 列相关矩阵 O(51²) 无压力；>10 万行触发 50K 抽样会压缩时滞分辨率 | 中：申请 + 攻击段切片 + P&ID 语义映射 |
| FailureSensorIQ | ❌ 不进管线（形态不同） | — | MCQA 组件评测，与 Gong (JII 2026) 同表对比 | 小：首尾适配器 |

**总体判断：三个已拉取的数据集（TEP/SKAB/IndPenSim）当前系统都可以直接做根因分析，不需要改管线代码。** 真正的缺口是两件工程件：① 变量语义映射表需要随数据外供（见 §5）；② 批量评测循环器需要自写（见 03-test-workflow.md §4）。

---

## 1. 判定框架

"能被分析出根因"拆成四个可验证条件：

1. **数据可达**：文件能进入管线（格式、大小、列数在系统限制内）；
2. **统计可检测**：异常/故障在数据中有统计信号（stats 引擎有对应分析手段）；
3. **机理可解释**：变量语义能被本体层映射成物理含义，支撑竞争假设的"物理机制"要件；
4. **真值可比**：存在公认根因标注，能对系统输出做 CDR/Top-k 评分。

## 2. 系统能力边界（代码审查结论）

### 2.1 数据可达性 — 全部达标

| 环节 | 实测能力 | 证据 |
|---|---|---|
| 接入 | `POST /api/files/data/upload`（单文件 500MB、单次 50 个）或直接放 `data/` 目录用绝对路径启动诊断 | `app/backend/src/routes/files.routes.mjs:78`、`config/default.yaml:74-76` |
| 格式 | csv/tsv/xlsx/xls/parquet/json 白名单（`config/default.yaml:67-73`）；inspect.mjs 分隔符探测 tab→分号→逗号（`inspect.mjs:37-41`），xlsx/parquet 委托 Python/pandas（`:123-153`） | `.claude/skills/industrial-analysis-auto/scripts/inspect.mjs` |
| 规模 | >10 万行自动转 50K 系统抽样（`inspect.mjs:165-167`）；**readFileSync 全量载入内存**（`:188`）—— 几百 MB 文件可用但建议预切 | |
| 时间列 | 按名称关键词 time/timestamp/datetime/date 探测（`inspect.mjs:92-103`）；preprocessor 统一为 ISO 并支持目录合并、编码回退 utf-8→gb18030→latin-1 | `industrial-data-preprocessor/SKILL.md:61-68` |
| 时间有序 | stats 有显式时间排序校验，>95% 递增才算有序，乱序直接判 CCF 不可靠 | `stats.mjs:341-369` |

### 2.2 统计可检测性 — 信号类型全覆盖

| 数据中可能存在的信号 | 系统对应手段 | 证据 |
|---|---|---|
| 变量间相关/时滞因果 | 全滞后 CCF（`full_lag_ccf`，默认 `--max-lag 20`）、lag window 一致性 | `core_stats.py:279`、`stats.mjs:237-265` |
| 混淆/分层效应 | 分层相关 + Simpson 检验（子组 <10 跳过） | `stats.mjs:295` |
| 假相关拦截 | 去趋势校验、Bonferroni 多重检验、离群敏感度 leave-one-out | `stats.mjs:375-411` |
| 非线性依赖 | 互信息（Kraskov，O(n²) 双重循环 —— 大样本必须走抽样路径） | `stats.mjs:447-467` |
| 因果方向 | Granger（要求 n ≥ maxLag+10） | `stats.mjs:508` |
| 状态切换/阶跃 | 变点检测、生产状态识别（regime detection 三算法融合） | `industrial-data-processor/SKILL.md:193` |

### 2.3 机理可解释性 — 主要缺口在这里

- 诊断强制走竞争性假设协议：**≥3 个竞争假设、≥2 个被排除**（排除置信 ≥90），每假设必须给物理机制（governing equation）+ 证伪条件（`industrial-diagnostician/SKILL.md:101-109`）。这意味着**变量语义映射质量直接决定可解释性上限**。
- 变量→物理含义映射**没有硬编码词典**：本体层由 LLM 按映射框架推断，未匹配参数回退模式库 `parameter_to_physics.json`（"PATTERN LIBRARY"，含 synonyms/governing_law/causal_chains，可扩展）。**全库 grep 无任何 XMEAS/TEP/SWaT 内置映射**。
- RAG（localhost:8764）是加速器不是硬依赖：Step 0 有 3 秒快失败预检，不可用时降级到 `parameter_to_physics.json` + 网络搜索（`industrial-analysis-auto/SKILL.md:227-232`）。
- 交接硬门禁：`02_processed/data_analysis_conclusion.json` 缺失即不可诊断（`industrial-diagnostician/SKILL.md:170`）。

### 2.4 真值可比性 — 约定已存在，批量器需自写

- 系统已有"一个数据集 + 一份 `ground_truth.md`"的评测约定（`data/eval_reactor_catalyst/`、`data/truth/`），配套断言器 `eval-assertions.mjs`（对已完成 run 输出 grading.json）。
- 结论三态枚举 `DETERMINED / COMPETING_SET / NEEDS_DATA`（`.claude/shared/schemas/diagnosis_schema.json:24-28`），置信度上限：INDISTINGUISHABLE ≤65、COMPETING_SET ≤70 —— 评测时**必须把三态分开计分**，不能只算二分类对错。
- **没有现成批量诊断 API/脚本**：`POST /api/diagnosis/start` 一次一个 run，循环器需自写（模板见 03-test-workflow.md §4）。

## 3. 逐数据集判定

### 3.1 TEP — ✅ 能分析出根因（评估分最高的"主战场"）

- **数据可达**：52 列 × 960 行 ≈ 1MB，距 500MB 上限差 3 个数量级；转换后的 `prepared/tep/*.csv` 带 ISO 时间戳、3 分钟间隔、行序严格递增（时间排序校验必过）。
- **统计可检测**：文献共识 21 类故障中 **18 类可检测、3 类（IDV 3/9/15）极难**（FaultExplainer 论文因此只取 PCA 可检测的 11 个做定量）。预期管线行为：可检故障 DETERMINED；3/9/15 输出 COMPETING_SET/NEEDS_DATA —— 按系统协议这是**诚实校准**而非失败，评测表应单列。
- **机理可解释**：唯一实质性缺口。系统无 XMEAS 词典 → **必须随数据外供变量映射表**（即 [ground-truth/tep-faults.md](ground-truth/tep-faults.md) §1，42+11 个变量官方描述），放进 `data/references/` 或诊断请求的 `user_context`/`process_description`。这一步本身可作为论文中"本体/RAG 层卖点"的消融实验：有映射 vs 无映射的 CDR 对比。
- **真值可比**：IDV(1)-(15)+21 有教科书根因，可做机理关键词 + LLM-judge 双评；IDV(16)-(20) 官方 Unknown，**评测集必须排除**（或只评"检测"不评"根因"）。
- **规模化路径**：Reinartz 版 143GB h5 无法整体拉取；建议用 Rieth RData（1.4GB，55 列含 faultNumber/simulationRun/sample）按 (fault, run) 切片导出 CSV，或 `pip install fddbenchmark` 自带加载器与 CDR 评测器。

### 3.2 SKAB — ✅ 完全可分析，适配成本为零

- **数据可达**：8 传感器 + ISO 时间戳，与现有冒烟数据 `data/smoke.csv` 形态完全一致；prepared 版已剥离标签列（标签列若保留会被当普通数值列参与相关分析，属于无害但浪费）。
- **统计可检测**：1Hz 采样下 CCF `--max-lag 20` 覆盖 20 秒滞后 —— 对阀门关闭（秒级压力/流量响应）足够；转子不平衡（振动 RMS 直接显性）与气蚀（压力脉动）信号直接。系统自带稳态识别会把异常前的正常段过滤，有利于时窗定位。
- **机理可解释**：振动/电流/压力/温度/流量是 `parameter_to_physics.json` 模式库的典型对象；泵-阀-回路是最常见工艺拓扑，本体层第一性原理推断可靠性高。
- **真值可比**：文件夹级故障类型明确（见 [ground-truth/skab-anomalies.md](ground-truth/skab-anomalies.md)），13,067 个标注异常点可用于 ADD（平均检测延迟）评分。**坑**：标签值是 `1.0` 浮点格式（不是 `1`），自写评测解析时注意；个别文件无标注时段。
- **竞争假设协议的契合点**：每文件单故障设定天然匹配"多假设竞争→排除→结论"；other/ 类（气蚀 vs 泄漏 vs 不平衡的区分）正是检验 COMPETING_SET 校准诚实性的好素材。

### 3.3 IndPenSim — ✅ 能分析出根因（适配已完成，真值最完整）

- **数据可达**：prep 脚本拆出的批次 CSV（Time (h) + 30 过程列 + Fault reference）单批 ~1000 行，无任何限制触碰。`Time (h)` 是相对时间列，名称含 "Time" 可被 inspect 识别；若要绝对时间可在 user_context 中说明"起始时刻"或预先加 8 小时偏移转 ISO。
- **统计可检测**：曝气故障（DO2/尾气 O2/CO2/OUR/CER 联动）、pH 漂移（pH/Base flow 联动）都是多变量联动型故障，正是相关+CCF+变点的强项。离线列（PAA_offline 等）NaN 率高，processor 保留 NaN 并在分析边界声明 —— 诊断时会正确降级。
- **机理可解释**：发酵过程变量语义直白（Aeration rate、Dissolved oxygen、Penicillin concentration…列名自带物理含义），本体层无需外供词典，这是三个数据集中**语义映射最容易**的。
- **真值可比**：**窗口级真值** —— `Fault reference` 列给出故障激活的精确小时区间（如批次 91：20–30.2h / 76–92.2h / 200–214.2h），可以评"根因时间定位"而不只是"根因类型"；批次级 0/1 真值在 Statistics CSV。
- **建议用法**：Exp-4 用 10 个故障批 + 抽 10 个正常批测误报率；每批喂全段（1000+ 行无压力），或在 user_context 中给出"关注后半段"以贴近真实排障场景。

### 3.4 SWaT — ⚠️ 有条件可分析（卡在数据获取，不卡管线）

- 管线侧无障碍：51 列相关矩阵 O(51²) 可承受；但 11 天连续数据（~95 万行 @1s）远超 10 万行抽样阈值，且全量 readFileSync 内存峰值高 → **必须预切攻击窗口段**（每段 ~1-2 小时）再喂管线，否则 CCF 滞后分辨率被压到抽样粒度。
- 需要外供 P&ID 传感器语义表（LT301=液位、PIT501=压力、AIT=分析仪…），iTrust 官方文档自带。
- 真值完备（36 类攻击点文档），是"真实物理试验台"泛化证据的最佳来源。**行动项：现在就提交申请表（1-2 周审批），不阻塞前三个数据集的实验。**

### 3.5 FailureSensorIQ — 不进管线，用于组件对标

- MCQA 问答与"时序数据→根因"管线形态不同；正确用法是把系统内 LLM 接上官方评测脚本拿分数，与 Gong (JII 2026) 的 36.5%→54.6% 同表对比，作为"组件能力"佐证。`eval_data/*.jsonl` 已在本地。

## 4. 诚实的风险清单（评测设计必须覆盖）

| 风险 | 影响 | 缓解 |
|---|---|---|
| **预训练记忆污染**：TEP 15 类故障根因写在教科书里，LLM 可能"背过" | CDR 虚高 | Exp-2 用 Braatz Fortran 仿真器（已在 `tep_braatz_classic/` 内）自造教科书不存在的扰动组合；报告"参数化陌生故障"命中率 |
| 3/9/15 难检故障 | 若计入 CDR 会拉低主结果 | 主表用可检测集，难检集单列并展示三态校准 |
| IDV 16-20 无真值 | 无法评根因 | 排除出根因评测，可只评检测 |
| inspect/stats 全量内存载入 | 大文件（SWaT 级）内存峰值 | 预切片；>50 万行用 `file_inspect.py --sample 50000` |
| MI O(n²)、全量相关 O(P²) | 大样本超时 | 依赖 >10 万行自动抽样路径；控制喂入段长度 |
| 批量评测无现成工具 | Exp-1 的 140 runs 无法一键跑 | 按 03-test-workflow.md §4 自写循环器（一天工作量） |
| token 成本 | 每个完整 run 消耗可观 | 分层抽样（Reinartz 每故障抽 5 run）、先 SKAB/TEP 小集冒烟再放量 |
| 评分者偏差（LLM-judge） | 评测可信度 | 机理关键词匹配 + LLM-judge 双评，分歧样本人工仲裁 |

## 5. 让管线"认识"数据的最低配置（每个数据集一份）

诊断请求除 `dataPath` 外建议显式提供：

```json
{
  "user_question": "诊断本次异常的根本原因",
  "process_description": "<该数据集的工艺背景段落，见各 ground-truth 文档头部>",
  "variable_mapping_ref": "data/references/<数据集变量表>.md",
  "user_objective": "<质量目标列，如 IndPenSim 的 Penicillin concentration>"
}
```

- TEP：贴 `ground-truth/tep-faults.md` §1 变量表（XMEAS/XMV 官方描述）；
- SKAB：8 传感器描述（见 ground-truth 文档）；
- IndPenSim：列名自解释，给"批次发酵、0.2h 采样、Time 为相对小时"说明即可；
- SWaT：贴 iTrust P&ID 传感器表。
