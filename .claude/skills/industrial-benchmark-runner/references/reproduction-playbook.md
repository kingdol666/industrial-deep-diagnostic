# Reproduction Playbook — 基准结果复现执行手册（Agent 可直接执行）

> 目标读者：任何 Agent（或工程师），从零开始复现 `experience/` 中的全部 benchmark 结果。
> 原则：**每一步都有可机检的期望输出；任何一步不符合即停止并按 §7 决策树处理；禁止跳步、禁止手改结果文件。**
> 权威脚本位于 `scripts/benchmark/`；编排契约见本 skill 的 `SKILL.md`。

## 0. 前置状态检查（<1 分钟）

```bash
node scripts/benchmark/download-datasets.mjs --list          # 应列出 5 个数据集（cwru 标记 MANUAL）
node .claude/skills/industrial-benchmark-runner/scripts/verify-repro.mjs --tier scripts/benchmark/cases/tier_all.json
```

期望：第二条输出 `status: REPRODUCIBLE`（若当前环境已有完整结果）；否则进入 §1 全量复现。

## 1. 数据完整性（~2 分钟）

```bash
node scripts/benchmark/make_dataset_manifest.mjs
```

期望输出包含 `manifest: 153 entr(ies)`（或更多——随数据集增加）。153 条 = prepared CSV + 下载归档的 sha256。
若首次运行无数据：`node scripts/benchmark/download-datasets.mjs --only secom,cmapss,paderborn`（CWRU 为手工步骤，见 `data/benchmark/downloads.lock.json` 内 manual 指引）。

## 2. 场景定义与真值隔离检查（~1 分钟）

```bash
python scripts/benchmark/make_tier2.py        # 重建 tier2_main.json（23 case），输出 "23 cases = 19 fault + 4 control"
python -c "import json; t=json.load(open('scripts/benchmark/cases/tier_all.json',encoding='utf-8')); f=sum(1 for c in t['cases'] if not c.get('control')); print(len(t['cases']),'cases =',f,'fault +',len(t['cases'])-f,'control')"
```

期望：`32 cases = 25 fault + 7 control`。
真值隔离红线：`truth`/`keywords` 字段只允许存在于 `scripts/benchmark/cases/*.json`（评分器读取）；
**严禁**把 truth/keywords 写入 run 目录、note、user_context 或任何管线可见输入。

## 3. 诊断推理记录（Agent 的工作步骤，~20-40 分钟）

两条路径，二选一：

- **重建已有推理**（复现本次结果，推荐）：`author_notes_t0.py` / `author_notes_t2.py` 重放已记录的诊断 note。
  ```bash
  python scripts/benchmark/author_notes_t0.py    # → "9 notes written"
  python scripts/benchmark/author_notes_t2.py    # → "23 tier2 notes written"
  ```
- **全新推理**（盲测模式）：对每个 case 执行 `run-tier.mjs prepare --tier <tier文件>`，阅读该 case run 目录的
  `prepare_digest.json`（统计证据：异常列谱/强相关对），按 `SKILL.md` §Workflow 第 4 步撰写 note
  （**只依据 digest 统计值与过程本体知识，禁止读取 `results/benchmark/gradings/*` 与 cases 真值**），
  `run-tier.mjs notes` 生成的骨架即 note schema 契约。

Authenticity 规则：note 中每个 evidence 必须能在对应 `prepare_digest.json` 找到出处；
mechanism_class 必须来自 note 骨架中列出的枚举；hypotheses ≥3 且 eliminated ≥2（DETERMINED 时）。

## 4. 管线执行与评分（~15-25 分钟，确定性）

```bash
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs prepare --tier scripts/benchmark/cases/tier0_smoke.json
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs prepare --tier scripts/benchmark/cases/tier2_main.json
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs commit  --tier scripts/benchmark/cases/tier0_smoke.json
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs commit  --tier scripts/benchmark/cases/tier2_main.json
```

期望：commit 输出 32 行 `[commit] <case> — top1=... judge=...`，无 `skipped`。
每行 grading 自动落盘 `results/benchmark/gradings/<case>.json` 并追加 `journal.jsonl`。
注意：commit 为确定性重放——同一 note 重跑产生**逐字节一致**的 grading（run_dir/时间戳除外，已验证）。

## 5. 聚合与核对（<1 分钟）

```bash
node scripts/benchmark/aggregate.mjs --tier-file scripts/benchmark/cases/tier_all.json
```

期望 `metrics.json` 关键值（第二实现独立重算应逐字段一致）：

| 字段 | 期望值 |
|---|---|
| total_cases / executed | 32 / 32 |
| top1 / topk | 25 / 25 |
| cdr | 1.0 |
| calibrated / overconfident | 25 / 0 |
| control_pass / false_alarms | 7 / 0 |

## 6. 复现门禁（最终裁决，~1 分钟）

```bash
node .claude/skills/industrial-benchmark-runner/scripts/verify-repro.mjs --tier scripts/benchmark/cases/tier_all.json
```

期望：**REPRODUCIBLE**，四项全绿（dataset integrity 153 verified / coverage 32=32 / metric repro matches / execution proof 32=32 且 finalize PASS）。
该门禁检查含 `finalize_passed`——任何场景管线门未过（如 judge<90 未修复）都会 FAIL。

一键执行 §1→§6：

```bash
node scripts/benchmark/reproduce-all.mjs            # 全链路，任何一步失败即停止
node scripts/benchmark/reproduce-all.mjs --skip-prepare   # 跳过重 prepare（用已有 run dir）
```

## 7. 漂移决策树

| 症状 | 含义 | 处置 |
|---|---|---|
| `dataset hash drift` | 输入数据被改动 | 恢复原数据（git/下载脚本）；**禁止**改 manifest 迁就数据 |
| `metrics drift vs metrics.json` | gradings 与聚合不一致 | 重跑 §5；若仍漂移，检查是否有手改的 grading（禁止） |
| `finalize_overall != PASS` | 场景管线门未过 | 查该 run 的 `pipeline_finalize_report.json`：judge<90 → 走 §3 修复循环（补强证据后重评）；schema/事件缺失 → 修管线后重跑该场景 |
| commit 出现 `skipped` | note 缺字段/未 prepare | 按 §3 补 note 或先 prepare |
| judge score < 90 | 质量门未过（修复循环触发条件） | 按 judge warnings 实质性补强假设证据（不得无依据抬分），重跑该 case commit |

## 8. 结果落位（复现完成后）

| 产物 | 位置 |
|---|---|
| 聚合指标 | `results/benchmark/metrics.json`（同步副本 `experience/results/`） |
| 逐场景评分 | `results/benchmark/gradings/*.json`（32 份） |
| 复现门禁结论 | `results/benchmark/repro_report.json` |
| 执行证明 | 每个 run 目录的 `.pipeline_events.jsonl` |
| 论文/报告支撑映射 | `experience/paper-support.md` |

复现完成后如需更新 `experience/` 副本与 HTML 报告数字，必须先通过 §6 门禁，并把新旧差异写入 decision log（`.omc/autoresearch/aei-paper/`）。
