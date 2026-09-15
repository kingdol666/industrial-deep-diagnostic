# 复现手册 — 审稿人逐步执行与核对（v2 · 真实管线执行）

> 目标：审稿人（或任何无记忆的 agent）按本手册执行，在本仓库**真实复现**
> **12 场景**诊断基准：对每个场景**真实启动 `industrial-analysis-auto` 管线
> （Step 0-9）**，由各子 skill 按协议完成诊断作业，产出每场景
> `report.md` + `diagnostic-report.html`，然后从真实产物评分、聚合、输出评价报告。
>
> ⚠️ **"可复现"的正确定义（2026-09-15，v2）**：可复现的是**测试流程**——
> 按本手册执行，管线会被真实启动、子代理会真实推理、门禁会真实拦截。它**不是**
> "重跑一个脚本重放出固定数字"。推理层每次执行的内容可能措辞不同（LLM 非确定性），
> 但结论由同一条证据链与同一套门禁约束；确定性统计层（prepare）逐字节可复现。
> v1 的"写 note → 脚本扩写成产物"路径**已删除**（它伪造产物与代理事件，
> 见 `zcode_direct_pipeline.mjs` 头注释）；不要寻找或恢复它。
>
> 配套：[execution-guide.md](execution-guide.md)（逐阶段派发契约）、[design.md](design.md)（口径）。

---

## 0. 前置条件

```bash
node .claude/shared/scripts/uv_env_setup.mjs   # Python venv（stats 包需要）
# 数据已在仓库内：data/benchmark/prepared/{skab,tep,indpensim*}/（sha256 见 dataset_manifest）
```

## 1. 场景契约（先核对这一条，全部数字都依赖它）

```bash
node -e "const c=require('./scripts/benchmark/cases/benchmark_cases.json').cases;
console.log('cases',c.length,'fault',c.filter(x=>!x.control).length,'control',c.filter(x=>x.control).length)"
# 期望：cases 12 fault 9 control 3
```

## 2. 真值隔离检查（**先跑这个**）

```bash
node scripts/benchmark/check-leakage.mjs
# 期望：RESULT: PASS — no truth leakage detected in agent-visible briefs
```

哨兵校验：brief 无 truth/关键词键（L3）、process_description 无故障身份（L2）、
brief 无逐字真值（L1）、关键词非全通用词（L4）、run 目录 user_context 无故障词（L6）。
历史教训：2026-09-13 审计曾发现 5/6 TEP 场景的题面直接写出答案——这类缺陷只有机械哨兵能拦住。

## 3. 一键复现（含真实管线执行）

```bash
node scripts/benchmark/run-benchmark.mjs
```

六阶段串行、fail-fast：

```
S0 环境 → S1 prepare（确定性统计，默认复用既有 run 目录）→ S2 brief（盲态留档）
       → S3 真实管线执行验证（12 场景九阶段产物完整性，缺一个都失败退出）
       → S4 从真实产物评分 + 确定性 rubric → S5 聚合 + 复现门禁 → S6 HTML 评价报告
```

**S3 会中断**（`N scenario run dir(s) lack full pipeline artifacts`）——这是设计行为：
它表示"该你（执行 agent）真实启动管线了"。按 §4 对每个缺失场景执行**完整管线**，
完成后**重跑同一条命令**继续。

> ⚠️ 绝不要用 `--force-prepare` 去"修复"S3——它会重建 run 目录、**销毁已完成的管线产物**。
> （2026-09-14 曾因 S1 默认 force 的逻辑反转 bug 触发过一次，靠 S3 门禁 fail-fast 拦截，
> 从 gradings 的 run_dir 记录用 `run-tier.mjs import-state` 恢复。）

## 4. 真实管线执行操作（S3，核心环节）

对每个 prepared 盲态 run 目录（`workspace/diagnostic-runs/<ts>_bench_<case>/`，
run 路径见 `results/benchmark/tier_state.json`）：

**执行 `skill://industrial-analysis-auto` Step 2-9**，每个阶段由对应子代理按其
skill 协议执行（由主 agent 派发；执行编排代理无法派发子代理时，可内联执行但必须
严格按各阶段协议角色隔离，并在 `run_completed` 事件中披露 harness 模式）：

| Step | 阶段 | 产物 | 门禁 |
|---|---|---|---|
| 2 | context-builder（可先试 `ontology_store.mjs fast-reuse`，命中即秒级复用） | `01_ontology/ontology.json` + clarification | CP-2/CP-3 |
| 3 | data-processor（Phase 0-6；无视觉环境走 `visual_analysis.py` 脚本署名契约） | `02_processed/data_analysis_conclusion.json` | CP-4 |
| 4 | diagnostician（7 步竞争假说，三态结论 + 置信帽） | `04_diagnostics/` 四件套（4 schema 零错误） | CP-5 |
| 5a∥5b | judge ∥ 物理预审 | `judge_feedback.json` + `optimizer_preflight.md` | judge ≥90 或修复环 |
| 6 | reporter（规范章节契约见 execution-guide §4） | `report.md` + `run_summary.json`（primary_finding 与 diagnosis.json 逐字一致） | CP-7 |
| 7 | 物理终审（独立复算 ≥8 个数字） | `optimizer.md` 含 ENDORSED | CP-8 |
| 8+8.5 | html-visualizer（render_manifest 先行）+ html-reviewer（独立，红线 + manifest 对齐） | HTML 三件套 + `html_review.json`=pass | CP-9 |
| 9 | `pipeline-finalize.mjs` | `pipeline_finalize_report.json` overall=PASS | Step 9 |

自查：`node scripts/benchmark/run-tier.mjs pipeline`（逐场景列缺口）。

**真实性红线（违反即无效）**：
- 任何子代理不得读 `results\benchmark\` 与 `scripts\benchmark\cases\`（评分器真值）；
- 主 agent/编排代理不得代写子代理产物、不得伪造 `agent_start/agent_complete` 事件；
- 无视觉模型环境禁止伪造视觉观察（走脚本署名骨架 + L4 captions 降级）；
- HTML 禁止手写绕过 render_manifest；`html_review.json` 只能由 html-reviewer 写；
- 场景身份（故障/对照）不下发——数据无异常就诚实判正常，数据不可判别就诚实 COMPETING_SET/NEEDS_DATA。

## 5. 分步执行（与一键等价）

| 步骤 | 命令 | 期望输出 |
|---|---|---|
| S1 | `node scripts/benchmark/run-tier.mjs prepare --tier scripts/benchmark/cases/benchmark_cases.json` | 12 个盲态 run 目录 + `prepare_digest.json`（**勿加 --force 除非确认要销毁重建**） |
| S2 | `node scripts/benchmark/run-tier.mjs brief --tier …` | `results/benchmark/briefs/*.brief.json`（12 份，泄漏哨兵输入） |
| S3 | 按 §4 对 12 个 run 目录真实执行管线 | `run-tier.mjs pipeline` 全部 COMPLETE |
| S4 | `node scripts/benchmark/run-tier.mjs commit --tier …` + `node scripts/benchmark/judge-rubric.mjs --tier …` | `[commit] … ×12` + `[rubric] … ×12` |
| S5 | `node scripts/benchmark/aggregate.mjs --tier-file …` → `verify-repro.mjs --tier …` | `metrics.json` + `report.md`；`status: REPRODUCIBLE` |
| S6 | `node scripts/benchmark/build-report.mjs` | `experience/benchmark-report.html` |

状态总览：`node scripts/benchmark/run-tier.mjs status`（prepared / graded 两态表）。

## 6. 逐项核对清单（评审验收点）

- [ ] **场景契约**：12 = 9 故障 + 3 对照
- [ ] **真值隔离**：`check-leakage.mjs` 退出码 0
- [ ] **真实管线执行**：`run-tier.mjs pipeline` 12/12 COMPLETE；每 run 目录含
      `01_ontology/`、`04_diagnostics/` 四件套、`render_manifest.json`、
      `html_selfcheck.json`、`05_review/html_review.json`、`report.md`、`diagnostic-report.html`
- [ ] **执行证明**：`.pipeline_events.jsonl` 过 `pipeline-log-check.mjs`；
      grading `checks.finalize_passed=true`（12/12）
- [ ] **产物为代理所写**：`diagnosis.json`/`judge_feedback.json`（source=judge-agent）/
      `optimizer.md`（ENDORSED）/`html_review.json`（verdict=pass）齐备且互相一致
- [ ] **独立评分可追溯**：`results/benchmark/gradings/<case>.json` 给出
      top1/topk/calibrated/kw_hits 与 run_dir；truth 只在 case 文件
- [ ] **总体指标**：`metrics.json`（Top-1 带 Wilson CI）；HTML 报告同源
- [ ] **复现门禁**：`repro_report.json` status = REPRODUCIBLE
- [ ] **关键词标定**：case 文件 `keyword_revision` 记录在案（2026-09-15 统一标定，
      先于最终聚合 uniform 应用，含删词收紧）

## 7. 漂移决策树（失败时）

| 症状 | 诊断 | 处置 |
|---|---|---|
| S0 报缺 venv | Python 环境未建 | `node .claude/shared/scripts/uv_env_setup.mjs` |
| S0 报 case contract | 场景集被改动 | `git checkout scripts/benchmark/cases/benchmark_cases.json`（保持 12 场景） |
| `check-leakage` 报 L2/L6 | 故障身份写回了题面或 run 目录 | 删故障句重新 brief；run 目录重新 prepare |
| S3 列场景 INCOMPLETE | 该场景管线未真实执行完 | 按 §4 在该 run 目录补跑缺失阶段（`pipeline` 命令看缺什么）；**不要**造假产物、**不要** --force-prepare |
| S3 全部 INCOMPLETE 且 gradings 有旧 run_dir | run 目录被重建（如误 --force-prepare） | `run-tier.mjs import-state` 从 gradings 恢复 tier_state 指向完成的 run 目录 |
| S4 报 "run dir incomplete" | 同 S3 | 同上 |
| S4 某场景 finalize 非 PASS | 产物契约违规 | 按 finalize 报告逐项修复（对齐/格式类可修；内容类回炉对应阶段） |
| S5 metrics 漂移 | 评分与聚合不一致 | 查 `gradings/` 单场景 json；重跑 aggregate |
| S5b 非 REPRODUCIBLE | 数据/指标/证明漂移 | `repro_report.json` 的 failures 逐条处理 |
| 重跑后单场景结论类型变化 | 推理层非确定性 | 预期行为：结论仍受同一门禁与真值对照约束；确定性统计层逐字节不变 |

## 8. 真实性保障层（v2）

| # | 保障 | 实际强度 |
|---|---|---|
| 1 | 真值隔离 | ✅ `check-leakage.mjs` 机械校验（brief + run 目录双层） |
| 2 | 真实管线执行 | ✅ S3 十四项产物完整性门禁 + finalize 执行证明；脚本扩写路径已物理删除，无"捷径"可走 |
| 3 | 评分独立性 | ✅ 评分器只读子代理产物；judge/审计/HTML 评审均为独立子代理判定并带 provenance 标记；质量底线 = 确定性 rubric v2（R1-R7 产物机算） |
| 4 | 执行证明 | ✅ 无事件日志 / finalize PASS 的 run 不计分 |
| 5 | 确定性底座 | ✅ prepare 统计逐字节可复现；S5 指标可从 gradings 独立重算（verify-repro） |
| 6 | 对照组 | ✅ 3 个正常对照（每数据集 1 个），误报直接计入 metrics |
| 7 | 阴性判别 | 评分器对 plausible-but-wrong 注入判伪（历史留痕 `experience/results/scorer-discrimination-test.json`） |
| 8 | 统计降级可见性 | ✅ grading 记录 `statistics_engine`/`stats_degraded`；降级 run `finalize_passed=false` 不计满分证明 |

> **统计效力边界**：n=9 故障场景，Top-1=6/9 只支持 Wilson 95% CI [35.4%, 87.9%]，
> 不支持"普遍胜任"。区间已计入报告。
>
> **可复现性的两层语义**：确定性统计层逐字节可复现；**推理层复现的是"流程可复现"**——
> 同一流程真实启动管线、同上门禁、同套评分，结论可重新到达（数值措辞可有差异）。
> 任何"复现"声明必须把这两层分开陈述。

## 9. 多次运行一致性测试（stability，判定稳定性研究）

> 目的：检验"每次诊断结果是否一致"。同一场景每次**独立完整管线执行**计一次 run；
> 本步骤自动扫描全部历史 run 目录并对照判定一致性——不需要（也不允许）复用或拷贝任何产物。

```bash
node scripts/benchmark/run-tier.mjs stability --tier scripts/benchmark/cases/benchmark_cases.json
# 输出 results/benchmark/stability_report.json（逐 case × 逐 run × 逐时代）
```

**口径（必读）**：

- proven run = run 目录含 `.pipeline_events.jsonl` 且 `pipeline_finalize_report.json overall=PASS`；
  未过 finalize 的残缺 run 一律列为 unproven，不计入一致性。
- **头条指标 = 时代内一致性**。时代边界 `20260914`：之前为 v1（无反振荡/置信帽纪律的旧版
  系统），之后为 v2（现行基准系统）。跨时代的判定翻转（3 个敏感场景 v1 过度自信
  DETERMINED → v2 置信帽 COMPETING_SET）是**记录在案的系统纪律收紧**，不是运行间随机
  不稳定；只有**同版本内的分歧**才构成稳定性问题。
- 判定提取与 `commit` 完全同语义（diagnosis.json primary_finding + 存活假设 deep-flat
  文本 → 真值关键词命中），不存在第二套口径。

**当前实测**（2026-09-15）：时代内判定+Top-1 一致性 **15/15**（v1 12/12、v2 已有配对 3/3）；
v2 现行系统 9 个场景尚只有 1 次 canonical run → 报告自动标记 `INSUFFICIENT-RUNS` 并给出
复跑契约。

**复跑契约（补齐 v2 重复次数的唯一合法方式）**：按 §4 在**全新会话**对同一 case 的既有
盲态 run 目录重跑完整管线（Step 2-9），产出**新的** run 目录。禁止在 run 目录间拷贝产物、
禁止 `--force-prepare`、禁止手改任何 json。补跑后重跑同一条 stability 命令即可自动重算。

## 10. 同模型基线横向对比（baselines，模型变量受控）

> 目的：与"其他论文的 LLM 诊断算法"和经典基线在**同 harness、同 LLM provider、同场景
> 数据**下对比。模型变量受控：基线与管线使用**同一 GLM 部署**（ZCode CLI harness）。

```bash
node scripts/benchmark/run-tier.mjs baselines --tier scripts/benchmark/cases/benchmark_cases.json
# 一步完成：PCA 基线重算 → 裸LLM prompts（幂等）→ 归档答案重打分 → 覆盖检查 → 对比表
```

组成与真实性契约：

| 臂 | 执行方式 | 产物 |
|---|---|---|
| 经典 PCA | **确定性脚本** `scripts/benchmark/baseline_pca.mjs`（Chiang 2001/Qin 2012 协议：正常对照训练、95% 方差、T²+Q、对照分布 99 分位报警、SPE 贡献 top-3；纯 JS Jacobi，无 venv 依赖） | `results/benchmark/baseline_pca_rca.json` |
| 裸 LLM（单次调用，无候选 / FE 含候选 / FE 官方 EXPLAIN_ROOT） | **同一 GLM 部署的真实单次调用**；提示词 = 同一盲态 brief（泄漏哨兵输入）；raw 回答留档 | `results/benchmark/baseline_fe_{prompts,answers}/` |
| FE 官方代码管线 | `baselines/FaultExplainer`（commit 2fcfee9）复刻 PCA(0.9)+T²+EXPLAIN_ROOT | `baselines.json.fe_official_code` |

- **答案文件真实性红线**：`baseline_fe_answers/*.json` 只能是模型对提示词的真实回复存档；
  缺失时 `baseline_llm.mjs check` 打印执行契约并退出 1，**禁止手写/编造答案**。
- 评分确定性：`baseline_llm.mjs score` 从归档 raw 回答重算 strict（rank-1 机理关键词或真
  IDV 编号）与 FE-style（top-3 内含真 IDV 或别名类）→ 重写 `baselines.json`；已核对与
  原型期归档旗标 0 硬分歧（唯一差异：5 处 no-candidates FE-style 由旧打分器的子串匹配
  缺陷修正为正则提取，"IDV(1)" 形态不再漏判）。
- **PCA 数字口径（2026-09-15 换代）**：原型期 PCA 脚本已丢失且其 T² 实现不可复原；现行
  正式产物由上述确定性脚本生成（其 SPE 口径与原型产物 **10/10 精确一致**，T² 细结构在
  IDV3/4/11 上有差异）。原型期旧数字冻结于 `results/benchmark/legacy_pca_prototype.json`
  仅供审计，论文 §8.4 已同步为可复现值。
- 报告落点：`report.md` §7 + `experience/benchmark-report.html` §4B/§5B（由
  aggregate.mjs / build-report.mjs 自动读取，无硬编码数字）。

## 11. 从场景报告到论文证据

- 单场景证据链：`00_input/data.csv` → `01_ontology/ontology.json`（机理）→
  `02_processed/validate_report.json`（统计）→ `03_figures/`（视觉）→
  `04_diagnostics/diagnosis.json` → `05_review/{judge_feedback,html_review}.json` →
  `report.md` / `diagnostic-report.html` / `optimizer.md`；
- 汇总证据链：`gradings/*.json` → `rubric.json` → `metrics.json` → `repro_report.json` →
  `results/benchmark/report.md` + `experience/benchmark-report.html`；
- v1（note 扩写）历史结果：`results/benchmark/legacy_note_era/`（仅作审计对照，不与本口径混用）；
- 期刊对标表与双口径声明：[design.md](design.md) §4。
