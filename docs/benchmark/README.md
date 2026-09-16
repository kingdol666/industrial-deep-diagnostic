# IDD 诊断基准（Benchmark）— 文档入口

> 本目录是诊断基准协议的**唯一文档入口**。按设计，基准编排脚本全部位于
> `scripts/benchmark/`（不做成 skill——基准是评测协议，不是作业技能；
> 被评测对象才是 skill 管线 `industrial-analysis-auto`）。

## 1. 基准测什么

被评测对象是 **一次完整的工业诊断 run**（`industrial-analysis-auto` 管线 Step 0-9），
而非逐样本标签。每个场景走完整管线，产出：

- `report.md` — MD 诊断报告（金字塔结构，Step 6 reporter）
- `diagnostic-report.html` — HTML 诊断报告（Step 8/8.5 可视化 + 审校）
- `04_diagnostics/diagnosis.json` 等全套产物 + `.pipeline_events.jsonl` 执行证明

然后由**独立评分器**读取管线输出，与标准答案（truth，仅存在于评分器侧）对照打分。

## 2. 场景集（12 个典型场景，TEP 子集逐故障文献可比）

| case_id | 数据集 | 角色 | 难点设计 | 逐故障文献基线 |
|---|---|---|---|---|
| `skab_valve1_1` | SKAB 水循环试验台 | 故障 | 阀门类机理判别 | 数据集级（检测类） |
| `skab_cavitation_13` | SKAB（other 组，故障类型不下发） | 故障 | 隐蔽故障，允许三态结论 | 数据集级（检测类） |
| `skab_normal_control` | SKAB anomaly-free | **对照** | 误报检验 | — |
| `tep_d01_ac_feed_ratio` | TEP d01 | 故障 | 进料比阶跃（IDV1） | FE：GPT-4o ✗ / o1 ✓ |
| `tep_d03_hard` | TEP d03 | 故障 | **文献公认难检 IDV3** | FE：未评分（PCA 不可检） |
| `tep_d00_normal_control` | TEP d00 | **对照** | 误报检验 | — |
| `tep_d04_reactor_cooling_step` | TEP d04 | 故障 | 反应器冷却水温度阶跃（IDV4） | FE：未评分（PCA 不可检） |
| `tep_d07_header_pressure` | TEP d07 | 故障 | C 集管压力降低（IDV7） | FE：GPT-4o ✓ / o1 ✓ |
| `tep_d11_reactor_cooling_random` | TEP d11 | 故障 | 冷却水温度随机波动（IDV11） | FE：GPT-4o ✓ / o1 ✓ |
| `tep_d14_reactor_valve_sticking` | TEP d14 | 故障 | 冷却水阀粘滞（IDV14） | FE：GPT-4o ✓ / o1 ✓ |
| `indpensim_batch093` | IndPenSim batch 93 | 故障 | 批过程工艺偏差 | 数据集级 |
| `indpensim_batch001_control` | IndPenSim batch 1 | **对照** | 误报检验 | — |

构成：9 故障 + 3 对照；TEP 子集 6 个场景带 **FaultExplainer 逐故障结果**（arXiv:2412.14492 Table 1）+
PCA 可检性（Chiang et al. 2001 标注）双文献基线，SKAB/IndPenSim 为数据集级参照。
**真值隔离**：故障场景的标准答案（truth + 判定关键词）只存在于评分器使用的
`scripts/benchmark/cases/benchmark_cases.json`，不在任何管线可见输入、brief 或本文档中出现。

## 3. 快速开始（审稿人 / 复现者）

```bash
node scripts/benchmark/run-benchmark.mjs
```

一键执行 S0→S6 六阶段（环境检查 → 确定性统计 prepare → 盲态任务包 brief →
**真实管线执行 S3**：每个场景在其盲态 run 目录启动 `industrial-analysis-auto` Step 2-9，
由 context-builder / data-processor / diagnostician / judge ∥ pre-audit / reporter /
final-audit / html-visualizer / html-reviewer 子代理按各自 skill 协议逐阶段执行 →
从真实产物评分 S4 → 聚合+复现门禁 → HTML 报告）。任一阶段偏离期望输出即失败退出。

> **v2 口径（2026-09-14）**：v1 的"写 note → 脚本扩写成管线产物"路径已退役
> （它伪造了产物与代理事件、HTML 是固定模板）。v2 只认子代理真实执行留下的产物；
> v1 结果整体归档于 `results/benchmark/legacy_note_era/`，不与新口径混用。
> 首个 v2 实测：skab_valve1_1 九阶段全通过，finalize 门禁抓出并强制修复 3 个真实
> 契约违规；诚实产出 COMPETING_SET（judge 98、HTML 评审 95）。

分步操作与每阶段期望输出见 [reproduction-guide.md](reproduction-guide.md)；
诊断 agent 的现场作业规程见 [execution-guide.md](execution-guide.md)。

### 3.1 一致性测试与基线对比（论文实验两件套）

```bash
# 多次运行一致性：自动扫描每个场景的全部独立管线执行，按"时代内"口径
# 报告判定类型 + Top-1 一致性（v2 现行系统缺重复的场景给出复跑契约）
node scripts/benchmark/run-tier.mjs stability

# 同模型基线横向对比：PCA 确定性重算 + 裸 LLM（同一 GLM 部署单次调用）归档
# 答案重打分 + FE 协议/官方代码 + IDD 逐场景对比表
node scripts/benchmark/run-tier.mjs baselines
```

两步均为零硬编码数字：一致性读 run 目录真实产物（同 `commit` 提取语义），
基线读留档 raw 回答重算。协议细节与真实性红线见
[reproduction-guide.md](reproduction-guide.md) §9/§10。

### 3.2 四步测试流水线（Agent 可执行 · 一键）

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs            # 全部四步
node scripts/benchmark/run-benchmark-pipeline.mjs --step 3   # 单步（1|2|3|4）
node scripts/benchmark/run-benchmark-pipeline.mjs --seed <n> # 复现同一次随机抽签
```

| 步骤 | 内容 | 脚本 |
|---|---|---|
| 1 | 对场景数据真实执行 IDD 诊断管线（prepare → brief → 真实 Step 2-9 → 评分 → 复现门禁） | `run-tier.mjs` + `aggregate.mjs` + `verify-repro.mjs` |
| 2 | 对**同一批数据**执行 LLM 复现基线套件（PCA / FE 协议 / 同模型裸 LLM），并核验套件确定性 | `baselines/baseline-suite/scripts/run-all.mjs` |
| 3 | **随机**抽取一个场景复测 + 结构化机理签名一致性审计（时代内口径） | `select-retest-case.mjs` + `consistency-audit.mjs` |
| 4 | 生成**英文** benchmark 标准报告（MD + HTML） | `build-english-benchmark-report.mjs` |

任一阶段不完整即以退出码 1 结束并打印 **EXECUTION CONTRACT**（明确列出 agent 还需执行什么）。
步骤 3 的抽签用记录 seed 的均匀随机——不接受自选场景。完整规程见
[benchmark-pipeline-runbook.md](benchmark-pipeline-runbook.md)（英文，Agent 运行手册）。

## 4. 文件地图

| 文件 / 目录 | 内容 |
|---|---|
| [design.md](design.md) | 设计依据：任务口径、指标定义、期刊 baseline 对标（可验证 DOI）、双口径声明、已知缺口、路线图 |
| [execution-guide.md](execution-guide.md) | 管线执行规程（v2）：prepare → brief → **真实管线执行（子 skill 分阶段契约）** → 从产物评分 → 门禁 → 报告 |
| [reproduction-guide.md](reproduction-guide.md) | 复现手册：逐步命令、期望输出、漂移决策树、真实性保障层 |
| [baseline-suite-pipeline.md](baseline-suite-pipeline.md) | 双项目对照测试流程：IDD 管线 × 复刻 baseline 套件并行启动 → **随机**抽查复测 → 对比基线报告（MD+HTML） |
| [benchmark-pipeline-runbook.md](benchmark-pipeline-runbook.md) | **Agent 运行手册（英文）**：四步测试流水线的逐步命令、门禁、执行契约与漂移决策树 |
| `scripts/benchmark/run-benchmark-pipeline.mjs` | **四步测试流水线一键入口**（1 管线诊断 / 2 基线套件 / 3 随机复测 / 4 英文报告） |
| `scripts/benchmark/select-retest-case.mjs` | 随机场景抽签（mulberry32 均匀随机；记录 seed/u/索引，可精确复现） |
| `scripts/benchmark/consistency-audit.mjs` | 一致性审计：结构化机理签名（判定类型 + primary_tag + mechanism_class + cause 重叠），时代内口径 |
| `scripts/benchmark/build-english-benchmark-report.mjs` | **英文** benchmark 标准报告生成器（→ `results/benchmark/benchmark_report_en.{md,html}`） |
| `scripts/benchmark/run-benchmark.mjs` | 审稿人一键入口（S0-S6 fail-fast） |
| `scripts/benchmark/run-tier.mjs` | 分步编排（prepare / brief / pipeline / commit / status / import-state / **stability** / **baselines**；notes/archive 已退役） |
| `scripts/benchmark/baseline_pca.mjs` | 经典 PCA 基线（确定性：对照训练 / 95% 方差 / T²+Q / 99 分位 / SPE top-3；纯 JS，无 venv 依赖） |
| `scripts/benchmark/baseline_llm.mjs` | 同模型裸 LLM 基线：prompts（幂等）/ score（确定性重打分 → baselines.json）/ check（缺失答案的执行契约） |
| `baselines/FaultExplainer/` | 上游对照算法 vendored 快照（li-group/FaultExplainer @ 2fcfee9，MIT） |
| `baselines/baseline-suite/` | 无公开仓库对照算法的 Nuxt 复刻套件（经典 PCA / FE 协议 / 裸 LLM 协议；可启动、可全量执行） |
| `scripts/benchmark/build-baseline-suite-report.mjs` | 双项目对比基线报告生成器（→ results/benchmark/baseline_comparison_report.{md,html}） |
| `scripts/benchmark/zcode_direct_pipeline.mjs` | 管线驱动：prepare（确定性统计）+ pipeline-check（完整性验证）+ grade（从真实产物评分）；diagnose（note 扩写）已退役需 `--legacy` |
| `scripts/benchmark/judge-rubric.mjs` | 确定性质量 rubric v2（R1-R7 全部从管线产物计算） |
| `scripts/benchmark/aggregate.mjs` | 指标聚合 → `results/benchmark/metrics.json` |
| `scripts/benchmark/verify-repro.mjs` | 复现性门禁（数据指纹 / 覆盖 / 指标零漂移 / 执行证明） |
| `scripts/benchmark/build-report.mjs` | HTML 评分报告生成（零硬编码数字，派生自 results） |
| `scripts/benchmark/cases/benchmark_cases.json` | 场景定义 + 标准答案（**评分器专用**） |
| `results/benchmark/` | 运行产物：briefs / gradings / tier_state（v1 结果在 `legacy_note_era/`） |
| `results/benchmark/benchmark_report_en.{md,html}` | **英文 benchmark 标准报告**（交付物；附录 A 含真值，禁止交给诊断 agent） |
| `experience/benchmark-report.html` | 最终评分报告（自动生成） |
| `experience/results/scorer-discrimination-test.json` | 阴性对照留痕：注入错误诊断 → 评分器判伪 |

## 5. 文档阅读顺序

1. 本 README → 2. [design.md](design.md)（为什么这样评）→
3. [execution-guide.md](execution-guide.md)（怎么跑管线）→
4. [reproduction-guide.md](reproduction-guide.md)（怎么复现与核对）
