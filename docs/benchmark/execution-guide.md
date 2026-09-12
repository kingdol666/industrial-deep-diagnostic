# 管线执行规程 — 8 场景真实诊断作业手册

> 读者：执行诊断的 agent（人或 LLM）。本规程定义如何对 8 个典型场景
> **真实跑通** `industrial-analysis-auto` 管线（Step 0-9），产出每个场景的
> `report.md` + `diagnostic-report.html`，并进入独立评分。
> 复现者视角的分步命令见 [reproduction-guide.md](reproduction-guide.md)。

---

## 1. 总流程（六阶段）

```
S0 环境 → S1 prepare(确定性统计) → S2 brief(盲诊任务包) → S3 现场诊断(agent) 
       → S4 commit(产物展开+门禁+评分) → S5 聚合+复现门禁 → S6 HTML 报告
```

一键入口自动执行全部阶段：

```bash
node scripts/benchmark/run-benchmark.mjs
```

S3 是唯一的 agent-in-the-loop 环节：一键入口在该阶段会**因 note 缺失而失败并列出
缺 diagnosed 的场景**——这是设计行为，表示"该你上场诊断了"。

## 2. S1 prepare：确定性统计（无 agent 参与）

对每个场景：

1. `setup.mjs` 创建 run 目录 `workspace/diagnostic-runs/<ts>_bench_<case_id>/`
   （00_input … 05_review 标准结构）；
2. 拷贝场景 CSV → `00_input/data.csv`，写 `input_manifest.json`（sha256 + 行列数 +
   列语义）、`user_context.json`（工艺描述；**真值一律不写入**）；
3. `inspect.mjs` 数据探查；`convert.mjs` 生成清洗副本；
4. **stats 包**（`.claude/skills/industrial-data-processor/scripts/stats/run.py`，
   项目 venv）执行单变量 z 扫描、跨域相关、滞后 CCF、反假相关校验（Simpson/
   去趋势/离群敏感度/多重检验）；stats 包失败时驱动端降级计算并在产物中诚实标注
   `engine: driver-js-fallback`；
5. 产出 `02_processed/{validate_report,anomaly_report,feature_summary,
   scenario_classification,analysis_parameter_selection}.json`、
   `03_figures/fig_temporal_overview.png`（matplotlib 时序网格图，±3σ 阈值线）；
6. 汇总为 `prepare_digest.json`（异常列谱 + 强相关对 + 引擎标识）。

**本阶段完全确定性**：同一数据 + 同一代码 → 逐字节相同结果（可复现性基础）。

## 3. S2 brief：盲诊任务包

`run-tier.mjs brief` 把每个 run 的 `prepare_digest` 转写为
`results/benchmark/briefs/<case>.brief.json`，内容**仅有**：

- 场景 id、数据集、角色（故障调查 / 对照）、工艺描述、行列数；
- 统计证据：每列 max|z| 与超 3σ 占比、最强跨域相关对（含 |r|）；
- `_rules`：只准依据 brief 证据 + 工艺领域知识推理；**禁止读取**
  `results/benchmark/gradings/*`、`scripts/benchmark/cases/*` 真值字段、其他 note。

## 4. S3 现场诊断（核心规程——真实性红线）

对每个 brief，诊断 agent 按 `industrial-diagnostician` skill 协议现场推理：

1. `node scripts/benchmark/run-tier.mjs notes` 生成 note 骨架
   `results/benchmark/notes/<case>.note.json`（含填写说明，填完删除 `_instructions`）；
2. **只依据 brief**：生成 ≥3 个竞争假设（机理类枚举见模板）→ 逐假设比对判别证据
   → 排除项必须给出矛盾证据 → 存活项给出机理链（logic_chain 逐级引用 brief 数字）；
3. 三态结论：唯一假设存活 → `DETERMINED`；多假设不可分辨 → `COMPETING_SET`
   （置信上限 70%）；证据不足以判别 → `NEEDS_DATA`；
4. **对照场景**：若统计证据无异常（各列 max|z| 处于正常波动、无跨域联动异常），
   结论必须是"正常运行"且置信校准——不许编造故障；
5. **真实性红线**（违反即结果无效）：
   - 每条证据声明必须引用 brief 中出现的**具体数字**；
   - 不读真值文件、不读其他场景的 note、不读历史 gradings；
   - 不为了"得到正确答案"反推证据——判错并诚实标注边界，好于凑对。

## 5. S4 commit：产物展开 + 门禁 + 独立评分

`run-tier.mjs commit` 调用管线驱动把每份 note 展开为 **schema 合规的完整管线产物**：

| 产物 | 说明 |
|---|---|
| `01_ontology/ontology.json` | 本体（变量语义 + 物理原理，context-builder 角色） |
| `02_processed/data_analysis_conclusion.json` | 数据分析结论（data-processor → diagnostician 强制交接件） |
| `02_processed/physics_check.json`（或 `physics_manual_verification.md`） | 物理可行性核验（自动列匹配失败时给 L1-L5 手工量级核对，不静默） |
| `04_diagnostics/{diagnosis,evidence,confidence,reasoning_chain}.json` | 诊断四件套（diagnosis_schema.json 运行时校验） |
| `03_figures/visual_analysis.json` | VLM 视觉分析（直接读图模式） |
| `05_review/judge_feedback.json` | judge 10 维评分（<90 触发修复循环语义） |
| **`report.md`** | Step 6 金字塔诊断报告（MD） |
| **`diagnostic-report.html`** | Step 8 HTML 诊断报告 |
| `optimizer_preflight.md` / `optimizer.md` | Step 5b 预审计 / Step 7 终审计 |
| `run_summary.json` / `evidence_closure_report.json` | Step 9 收尾 |
| `.pipeline_events.jsonl` | 全程事件日志（执行证明） |

随后：

1. `pipeline-log-check.mjs` 审计事件日志 → `pipeline-finalize.mjs` 终门禁
   （overall 必须 PASS，否则该 run 不计分）；
2. **独立评分器**读取管线输出与 truth 对照打分 → `results/benchmark/gradings/<case>.json`
   （判 `top1/topk/calibrated/control_pass/false_alarm`），追加 `journal.jsonl`。

## 6. S5/S6：聚合与报告

- `aggregate.mjs` → `results/benchmark/metrics.json`（总体 + 分数据集 + 逐 case）
  与 `results/benchmark/report.md`；
- `verify-repro.mjs` 复现门禁：数据 sha256 重哈希、场景覆盖、指标零漂移、
  执行证明四查 → `repro_report.json`（必须 `REPRODUCIBLE`）；
- `build-report.mjs` → `experience/benchmark-report.html`（评分卡 / 分数据集 /
  逐场景表 / 口径 A+B baseline 对比 / 复现命令，零硬编码数字）。

## 7. 场景输出速查（用户交付物）

每个场景跑完后，最终诊断报告位于：

```
workspace/diagnostic-runs/<ts>_bench_<case_id>/report.md
workspace/diagnostic-runs/<ts>_bench_<case_id>/diagnostic-report.html
```

对应评分位于 `results/benchmark/gradings/<case_id>.json`，
run 目录记录在 `results/benchmark/tier_state.json`。
