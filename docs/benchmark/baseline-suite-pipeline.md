# 双项目对照测试流程（Benchmark × Baseline Suite Pipeline）

> 目的：把"**IDD 管线诊断 × 复刻 baseline 诊断 → 随机抽查复测 → 对比基线报告**"固化为可照做的
> 流程。任何无记忆的 agent 或评审人按本文件执行，即可对仓库内已下载的数据场景完成
> **真实**诊断测试并再生成对比报告（MD + HTML）。
>
> 真实性红线（违反即无效）：不造假产物、不手改结果 json、不在 run 目录间拷贝产物、
> baseline 套件不读取任何真值/关键词、缺失答案以"执行契约 + 显式缺口"呈现而非编造。
>
> **一键入口（推荐）**：
> ```bash
> node scripts/benchmark/run-benchmark-pipeline.mjs          # 四步串联
> node scripts/benchmark/run-benchmark-pipeline.mjs --step 3 # 单步
> ```
> 逐步命令、门禁与执行契约见英文运行手册
> [benchmark-pipeline-runbook.md](benchmark-pipeline-runbook.md)。
> 任一阶段不完整即以退出码 1 结束，并打印 **EXECUTION CONTRACT**（明确列出 agent 还需执行什么）。

## 0. 前置条件（一次性）

| 项 | 位置 | 说明 |
|---|---|---|
| 数据（已下载） | `data/benchmark/prepared/{skab,tep,indpensim*}/` | 12 场景 prepared CSV，sha256 见 `results/benchmark/dataset_manifest.json` |
| 场景与统计摘要 | `results/benchmark/briefs/*.brief.json` | 盲态任务包（泄漏哨兵输入，无真值） |
| 对照算法上游仓库 | `baselines/FaultExplainer/` | 已 vendored：li-group/FaultExplainer @ `2fcfee9`（MIT），VENDOR.md 记录出处 |
| 对照算法复刻（无公开仓库者） | `baselines/baseline-suite/` | **Nuxt 项目**：经典 PCA（Chiang 2001/Qin 2012）、FE 协议复刻、同模型裸 LLM 协议 |
| IDD 两个子项目 | `app/backend/`（3210）· `app/frontend/`（5180） | Express + Vue3/Vite |
| 套件依赖 | `cd baselines/baseline-suite && npm install` | Nuxt 3（一次性；Step 2 会自动拉起 dev server） |
| Python venv | `.claude/shared/scripts/.venv/` | `node .claude/shared/scripts/uv_env_setup.mjs` |

## 1. 并行启动所有数据场景执行 industrial-analysis-auto（IDD 侧）

```bash
# 一键（S0 环境 → S1 prepare → S2 盲态brief → S3 真实管线验证 → S4 评分 → S5 复现门禁 → S6 报告）
node scripts/benchmark/run-benchmark-pipeline.mjs --step 1
node scripts/benchmark/run-benchmark.mjs   # 等价：审稿人一键入口（S0-S6 fail-fast）
```

- S3 校验每个场景 run 目录的**九阶段产物完整性**（14 项 artifact + finalize PASS 执行证明）。
  缺哪个场景就按 `docs/benchmark/reproduction-guide.md` §4 对该 run 目录**真实执行**管线
  （12 个场景可分批**并行**派发，每场景独立 run 目录 `workspace/diagnostic-runs/<ts>_bench_<case>/`）。
- 分步等价：`run-tier.mjs prepare → brief → (并行执行管线) → pipeline → commit`。
- 自查：`node scripts/benchmark/run-tier.mjs pipeline`（逐场景列缺口）。

当前状态：12/12 场景全部 finalize PASS（canonical 批次见 `results/benchmark/gradings/`）。

## 2. 启动 baseline 诊断（复刻套件侧，对同一批数据真实诊断）

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs --step 2
# 手动等价：Step 2 会自动探测/拉起套件（优先 5181，被占用时读取日志的实际端口）
#   ind-diag all                                        # IDD：backend 3210 + frontend 5180
#   cd baselines/baseline-suite && node node_modules/nuxt/bin/nuxt.mjs dev --port 5181
#   node baselines/baseline-suite/scripts/run-all.mjs --base http://localhost:5181
```

三臂说明（全部对 `data/benchmark/prepared/` 的真实数据计算）：

| 臂 | 内容 | 执行方式 |
|---|---|---|
| `pca` | 经典 PCA：对照训练 / 95% 方差 / T²+Q / 对照分布 99 分位报警 / SPE top-3 | 套件内置确定性引擎（纯 JS Jacobi） |
| `fe` | FE 协议复刻：PCA(0.9) + T²(α=0.01 F 限) + 6 连续触发 + 触发样本逐特征 T² top-6 + EXPLAIN_ROOT | 套件内置确定性引擎 |
| `llm` | 裸 LLM 单次调用协议（盲态摘要；无候选 / 含候选 / FE 官方 EXPLAIN_ROOT 三 regime） | 配置 `BASELINE_LLM_BASE_URL/KEY/MODEL` 时 **live 真实调用**（OpenAI 兼容；发请求前校验 host，拒绝 localhost/环回/私有/保留地址）；未配置时**回放同 GLM 部署的归档 raw 回答**（响应标 `mode:"recorded"`，来源 `results/benchmark/baseline_fe_answers/`） |

结果逐项落盘 `baselines/baseline-suite/runs/<case>.<arm>[_<regime>].json`（共 45 项）。
UI（http://localhost:5181 ）可单场景单臂交互执行并查看完整 JSON。

覆盖检查：`node scripts/benchmark/baseline_llm.mjs check`（缺失答案打印执行契约并退出 1；
tep_d00 对照的 LLM 臂为已记录的协议范围缺口，显式豁免）。

**确定性核验（step 2 自动执行）**：先快照上一次 `runs/`，重跑后逐文件比对（仅剔除
`executed_at`）。确定性臂必须逐字节一致；`recorded` 臂出现 diff 说明归档答案被改动（违规）。
结论写入 `results/benchmark/suite_determinism.json`。

## 3. **随机**抽取一个场景复测（一致性验证）

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs --step 3
# 等价：随机抽签 → 全量一致性审计 → 对该场景专项审计
#   node scripts/benchmark/select-retest-case.mjs --faults-only
#   node scripts/benchmark/consistency-audit.mjs
#   node scripts/benchmark/consistency-audit.mjs --case <抽中场景>
```

- **抽签不是自选**：`select-retest-case.mjs` 用 `mulberry32` 在声明池上做**均匀随机**
  抽取，并记录 seed / 均匀值 u / 索引到 `results/benchmark/retest_selection.json`（append-only）。
  评审可用同一 seed 精确复现：`--seed <n>`；查看上次结果：`--peek`。
  （旧流程把 `tep_d14` 及其两个 run 目录时间戳硬编码进报告生成器——那是选择偏倚，已废弃。）
- **一致性判据**：`consistency-audit.mjs` 把每个 `workspace/diagnostic-runs/*_bench_<case>`
  视为一次独立执行，执行之间**两两对比**（不含真值，故可在盲态协议内运行）。对比的是
  **结构化机理签名**：`diagnosis_type` + `primary_tag`（执行器 XMV_* > 测点 XMEAS_* > IDV*）
  + `mechanism_class`（WEAR/OPERATION/…）+ cause token 重叠度。

  | 判定 | 规则 |
  |---|---|
  | `CONSISTENT` | 判定类型相同 **且**（primary_tag 相同 **或** mechanism_class 相同且 cause 重叠 ≥0.35） |
  | `WEAK` | 判定类型相同，结构一致性较弱 |
  | `DIVERGENT` | 判定类型不同，或机理无关联 |
  | `UNPROVEN` | 缺 finalize 执行证明——列出但不计入 |

- **时代口径**：run 目录时间戳前缀 `< 20260914` 为 v1 时代（尚无防振荡/置信帽/判别通道
  缺失纪律）。跨时代翻转属**已记录的系统修订**而非随机不稳定，故头条指标为**时代内**一致性，
  跨时代对单列参照。
- **抽中场景同代执行不足 2 次时**，runner 打印执行契约：在**全新 run 目录 + 全新会话**对
  该场景再跑一次完整 `industrial-analysis-auto` Step 2-9（禁止拷贝产物、禁止手改 json），
  然后 `run-tier.mjs commit --only <case>` → `consistency-audit.mjs --case <case>`。
- **全量一致性**：`node scripts/benchmark/run-tier.mjs stability`（另一口径：时代内判定 + Top-1 一致性）。

## 4. 生成 benchmark 对比基线报告

```bash
node scripts/benchmark/run-benchmark-pipeline.mjs --step 4
# 或直接：node scripts/benchmark/build-english-benchmark-report.mjs
```

产出**英文** benchmark 标准报告（零硬编码判定，全部数字读自磁盘产物）：

| 文件 | 内容 |
|---|---|
| `results/benchmark/benchmark_report_en.md` | Markdown 版（协议 / 场景 / 指标 / 逐场景 / 基线 / 一致性 / 复现性 / 局限 / 产物索引 / 附录 A 真值） |
| `results/benchmark/benchmark_report_en.html` | 同内容的可汇报 HTML 版 |

> 附录 A 含真值。**禁止把该报告交给参与诊断的 agent**——会破坏盲态协议。

中文口径的配套报告（同源派生物，非英文交付物）：

```bash
node scripts/benchmark/build-baseline-suite-report.mjs   # → baseline_comparison_report.{md,html}
node scripts/benchmark/build-report.mjs                  # → experience/benchmark-report.html
```

## 5. 漂移决策树

| 症状 | 处置 |
|---|---|
| Step 1 报某场景缺产物 | 按 reproduction-guide §4 真实补跑该场景；禁止 `--force-prepare` 修复 |
| 套件 `run-all` 某臂失败 | 看 HTTP 错误体；数据文件缺失先查 `dataset_manifest.json` 的 sha256 |
| LLM 臂 unavailable | 属未配置 live 端点且无归档答案（当前仅 tep_d00 对照）；配置 env 后重跑即 live |
| 确定性臂复测出现 diff | 套件代码被改动——与 `scripts/benchmark/baseline_pca.mjs` 同协议互检 |
| `recorded` 臂出现 diff | 归档答案被改动（违规） |
| 时代内一致性报 DIVERGENT | 按 §3 对比两次执行的 `primary_tag` / `mechanism_class`；若数据确实无判别力，`COMPETING_SET` 才是诚实结论，置信帽生效 |
| 对比报告数字与 gradings 不符 | 报告是派生物——重跑 `run-tier.mjs commit` → `aggregate.mjs` → 本流程 §4 |

## 6. 四步产物速查

| 步骤 | 主产物 | 门禁 |
|---|---|---|
| 1 | `results/benchmark/gradings/*.json`、`metrics.json` | 12/12 finalize PASS；`REPRODUCIBLE` |
| 2 | `baselines/baseline-suite/runs/*.json`（45 项）、`suite_determinism.json` | 0 failure；确定性臂逐字节一致 |
| 3 | `retest_selection.json`、`consistency_audit.json` | 时代内 `divergent = 0` |
| 4 | `benchmark_report_en.md` + `.html` | 非空且可再生成 |

