# 管线执行规程 — 12 场景真实诊断作业手册（v2 · 真实管线执行）

> 读者：执行诊断的 agent（人或 LLM）。本规程定义如何对 12 个场景
> **真实启动 `industrial-analysis-auto` 管线（Step 0-9）**，由各子 skill 按各自
> 协议逐阶段执行，产出每个场景的 `report.md` + `diagnostic-report.html`，再进入独立评分。
> 复现者视角的分步命令见 [reproduction-guide.md](reproduction-guide.md)。

---

## 0. v2 变更（为什么废除了 note 扩写路径）

v1 的 S3"写 note → S4 脚本把 note 扩写成管线产物"已被**退役**（`zcode_direct_pipeline.mjs
diagnose` 现需 `--legacy` 才能运行）。原因：扩写路径由脚本代写了四个诊断 JSON、judge/审计
判定、HTML 乃至 `agent_start/agent_complete` 事件——执行证明是伪造的，HTML 是固定模板。
v2 的 S3 是**真实启动管线**：每个场景在其盲态 run 目录中执行 Step 2-9，每个子 skill 按
自己的协议干活；S4 只读取子代理真实写下的产物评分。实测（skab_valve1_1，2026-09-14），
finalize 门禁连续抓出并强制修复了 3 个真实契约违规（run_summary 漂移 / VLM 骨架署名 /
报告章节号）——门禁能失败，才是真门禁。

## 1. 总流程（六阶段）

```
S0 环境 → S1 prepare(确定性统计) → S2 brief(盲态留档+泄漏哨兵) → S3 真实管线执行(industrial-analysis-auto Step 2-9)
       → S4 grade(从真实产物评分) → S5 聚合+复现门禁 → S6 HTML 报告
```

一键入口自动执行全部阶段（S3 会因产物缺失而失败并列出缺口——设计行为）：

```bash
node scripts/benchmark/run-benchmark.mjs
```

## 2. S1 prepare：确定性统计（无 agent 参与）

对每个场景：

1. `setup.mjs` 创建 run 目录 `workspace/diagnostic-runs/<ts>_bench_<case_id>/`；
2. 拷贝场景 CSV → `00_input/data.csv`，写 `input_manifest.json`（sha256 + 行列数）、
   `user_context.json`（工艺描述；**真值一律不写入**）；
3. `inspect.mjs` 数据探查；`convert.mjs` 生成清洗副本；
4. **stats 包**执行 z 扫描、跨域相关、滞后 CCF、反假相关校验；失败时降级并诚实标注
   `engine: driver-js-fallback`（该退化会传导到 grading 的 `stats_degraded`，finalize 不给 PASS）；
5. 产出 `02_processed/*` 确定性产物 + `03_figures/fig_temporal_overview.png` +
   `prepare_digest.json`。

**本阶段完全确定性**：同一数据 + 同一代码 → 逐字节相同结果（复现性基础）。

## 3. S2 brief：盲态任务包（留档 + 泄漏哨兵输入）

`run-tier.mjs brief` 生成 `results/benchmark/briefs/<case>.brief.json`——只含统计证据与
工艺描述。v2 中 agent 不再从 brief 诊断（改为在 run 目录执行管线），brief 保留用途：
泄漏哨兵（check-leakage L1-L6）的扫描对象 + 评分 rubric R3 的"本场景可见数字"基准。

## 4. S3 真实管线执行（核心规程——按子 skill 约束逐阶段执行）

对每个 prepared run 目录，**执行 `skill://industrial-analysis-auto` Step 2-9**。
每个阶段由对应子代理按其 skill 协议执行（主 agent 只派发、等待、聚合）：

| Step | 子代理 | Skill（协议约束） | 关键产物 | 门禁 |
|---|---|---|---|---|
| 2 | context-builder | industrial-ontology-builder | `01_ontology/ontology.json` + clarification（AUTO_RESOLVED） | CP-2/CP-3 + publish 资产库 |
| 3 | data-processor | industrial-data-processor（Phase 0-6，ontology_first，Phase 1.2 假说→方法计划制，Phase 1.5 稳态过滤，Phase 5.5 无视觉模型时按官方降级：`visual_analysis.py` 署名骨架） | `02_processed/data_analysis_conclusion.json` | CP-4 + data-processor-finalize |
| 4 | diagnostician | industrial-diagnostician（7 步竞争假说协议，四条件反推测，≥3 假说 ≥2 排除，三态结论 + 置信帽） | `04_diagnostics/{diagnosis,evidence,confidence,reasoning_chain}.json` | CP-5（四 schema 零错误） |
| 5a∥5b | judge ∥ report-reviewer（唯一并行步） | industrial-judge（10 维门 + 结构化 repair_scope）∥ industrial-physical-auditor（预审计） | `05_review/judge_feedback.json` + `optimizer_preflight.md` | judge ≥90 或修复环（best-of-3，全局 5） |
| 6 | reporter | industrial-reporter（金字塔报告；规范章节契约：H1 含"工业诊断报告"，`## 4. 统计分析发现`、`## 6. 根因结论`、`## 7. 证据全景`，含 process-only/双驱动/数据交接结论） | `report.md` + `run_summary.json`（primary_finding 与 diagnosis.json 逐字一致） | CP-7 |
| 7 | report-reviewer（终审） | industrial-physical-auditor final（逐数字独立复算） | `optimizer.md`（须含 `ENDORSED`） | CP-8 |
| 8 | html-visualizer | industrial-html-visualizer（**v2 硬集成 diagnostic-html-visualizer 设计系统**） | `render_manifest.json`（先行）→ `diagnostic-report.html` → `html_selfcheck.json`（8 项） | CP-8A/8B |
| 8.5 | html-reviewer | industrial-html-reviewer（六目标独立评审 + 15 条红线 + manifest 对齐 + selfcheck 复核；verdict 只由评审者写） | `05_review/html_review.json`（verdict=pass） | CP-8C |
| 9 | main agent | pipeline-finalize.mjs + 事件收尾 | `pipeline_finalize_report.json`（overall=PASS）+ `evidence_closure_report.json` | Step 9 |

执行红线（违反即结果无效）：

- **真值隔离**：任何子代理不得读 `results/benchmark/`（legacy 归档除外）与
  `scripts/benchmark/cases/`；
- **禁止代写**：主 agent 不得替子代理执行其协议（红线黑名单 #2）；产物必须由对应
  子代理按协议写出；
- **无视觉环境**：Phase 5.5 走 `visual_analysis.py` 脚本署名的 metadata 骨架
  （pipeline-log-check 认可的非 VLM 契约），禁止伪造视觉观察；
- **HTML 禁止手写绕过 manifest**：先 `render_manifest.json` 后页面，页面计数与
  manifest 逐一对应（红线 #14），`05_review/html_review.json` 只能由 html-reviewer 写。

进度自查：`node scripts/benchmark/run-tier.mjs pipeline`（逐场景列缺口）。

## 5. S4 grade：从真实产物独立评分

`run-tier.mjs commit` → `zcode_direct_pipeline.mjs grade`：

1. 校验 run 目录含全部管线产物（`PIPELINE_ARTIFACTS` 14 项，缺一拒绝评分）；
2. `pipeline-log-check` 审计事件 + finalize overall=PASS（缺失时补跑 finalize）；
3. 从**子代理写下的真实产物**提取：`diagnosis.json`（类型/主结论/存活假设机理链）、
   `confidence.json`（总体置信）、`judge_feedback.json`（10 维分，来源标记
   `judge-agent-10-criteria`）、`optimizer.md`（ENDORSED，来源 `auditor-agent`）、
   `html_review.json`（verdict，来源 `html-reviewer-agent`）；
4. 对照 truth 判 `top1/topk/calibrated/overconfident/control_pass`（判据同 v1：
   机理关键词双判定；DETERMINED 且判错=过度自信）→ `results/benchmark/gradings/<case>.json`。
5. `judge-rubric.mjs`（v2）：R1-R7 全部从管线产物计算（本体/交接件/诊断四件套完整性、
   假说结构、证据 grounding 对 brief 数字、置信校准、可证伪性、物理核验、执行证明+
   HTML 门）→ 满分 100。

## 6. S5/S6：聚合与报告

- `aggregate.mjs` → `metrics.json`（Top-1/CDR/校准/对照/平均 rubric）+ Wilson CI；
- `verify-repro.mjs` 复现门禁（数据 sha256、场景覆盖、确定性阶段零漂移）→ REPRODUCIBLE；
- `build-report.mjs` → `experience/benchmark-report.html`（评分卡 + 口径 A/B baseline 对比）。

## 7. 场景输出速查（用户交付物）

每个场景跑完后，最终诊断报告位于：

```
workspace/diagnostic-runs/<ts>_bench_<case_id>/report.md
workspace/diagnostic-runs/<ts>_bench_<case_id>/diagnostic-report.html
```

对应评分位于 `results/benchmark/gradings/<case_id>.json`，
run 目录记录在 `results/benchmark/tier_state.json`。
v1（note 扩写）时代的结果已整体归档于 `results/benchmark/legacy_note_era/`，
不与 v2 口径混用。
