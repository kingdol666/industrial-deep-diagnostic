# T3 任务简报 — 调参归因与经验检索（industrial-tuning-memory）

## 场景

夜班在压延机 calender-03（产品 PVC-M）上做了 3 次调参动作，动作日志与
1 分钟级时序数据已导出。工艺备注：该回路（温控/压力/速度）大约 30 个采样
步内完全整定（settling ≈ 30 samples）。另有一份故障签名来自昨天的告警，
需要检索历史处置经验；检索到的处置如果被现场执行并确认有效，要回填佐证。

## 输入（只读）

- `cases/T3_tuning_memory/data.csv`（200 行：t, temp_c, pressure_mpa,
  speed_rpm, feed_rate_kgh, yield_pct；t 为 ISO UTC 时间戳，Δt=1 分钟）
- `cases/T3_tuning_memory/action_log.json`（3 条动作日志，action_log schema v1.0）
- `cases/T3_tuning_memory/fault_signature.json`（故障签名）
- `cases/T3_tuning_memory/playbook_seed/tuning_experience.jsonl`
  （2 条历史经验条目，tuning_experience 信封格式——这是既往运行沉淀的本地
  经验库，需要先作为本地经验库种子使用）

## 环境（已验证的入口）

- 工作目录：`workspace/field-tests/fieldtest-20261004/`
- venv Python：
  `D:\codes\industrial-deep-diagnostic\.claude\shared\scripts\.venv\Scripts\python.exe`
  （下称 `$PY`）；Node 用系统 `node`
- 脚本目录：
  `D:\codes\industrial-deep-diagnostic\.claude\skills\industrial-tuning-memory\scripts\`
  - `tune_stats.py`：子命令 `attribute`，参数 `--run-dir --data --time-col
    --metric --action-log --settle-steps …`（归因按"动作日志为单元"逐条产出
    `06_experience/attribution/{action_log_id}.json`）
  - `experience_build.mjs`：子命令 `build`（`--run-dir [--action-log …]`）与
    `feedback`（`--run-dir --chunk-id ID --result
    effective|ineffective|harmful|confirmed [--note …]`）
  - `match_playbook.mjs`：子命令 `recommend`（`--run-dir [--signature
    00_input/fault_signature.json] [--out conclusions/recommendation.json]
    [--top 3]`）
  - `quality_gate.mjs`：`node quality_gate.mjs <RUN_DIR> --skill-path
    <skill目录> --shared-path D:\codes\industrial-deep-diagnostic\.claude\shared`

## 要求（RUN_DIR = `results/T3/run`，全部命令与退出码记入
`results/T3/commands.log`）

1. **搭建 RUN_DIR**（这是 skill 的 RUN_DIR 契约布局）：
   - `results/T3/run/00_input/`：拷入 `data.csv`、`action_log.json`、
     `fault_signature.json`；
   - `results/T3/run/06_experience/tuning_experience.jsonl`：用
     `playbook_seed/tuning_experience.jsonl` 作为本地经验库初始内容（直接拷贝）。

2. **归因**：运行 `tune_stats.py attribute`，`--metric yield_pct`，
   `--time-col t`，并按工艺备注传 `--settle-steps 30`（其余参数用默认）。
   逐条记录 3 个 action_log 的 `attribution_status`（**逐字**）、
   `reason_code`、`effect.delta`、`effect.ci95`、`direction_established`、
   `evidence_grade`（从产出的 attribution JSON 里读）。

3. **入库**：`experience_build.mjs build`。记录每条 action 的入库事件
   （created / corroborated / idempotent_noop / SKIP 及原因）与最终库内条目
   总数。

4. **检索**：`match_playbook.mjs recommend`。记录
   `recommendation_status`、`match_scope`、命中 playbook 的 `experience_id`
   （chunk_id）、`match_score`、`evidence_grade`，以及 `degradation_path`。

5. **佐证回填**：对第 4 步命中的 top playbook 条目执行
   `experience_build.mjs feedback --result effective`。记录命令打印的
   corroboration/refutation 计数与 grade/label 变化，并从
   `06_experience/tuning_experience.jsonl` 与
   `06_experience/accumulated/state.json` 中引用回填后的对应字段值。

6. **复检与门禁**：回填后重跑一次 `recommend`（刷新
   `conclusions/recommendation.json` 与最新经验库一致），再运行
   `quality_gate.mjs`，记录逐项 PASS/FAIL 与退出码。

7. 写中文报告 `results/T3/T3_report.md` 汇总以上记录（数字全部来自命令
   产物，不得手算或手改）。
