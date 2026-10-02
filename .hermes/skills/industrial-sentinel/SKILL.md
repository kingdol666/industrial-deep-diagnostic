---
name: industrial-sentinel
description: "Production-line sentinel (产线哨兵) — a PURE-ANALYSIS standing watch over industrial time-series windows. Two deterministic modes, zero LLM / zero network on the hot path: (a) watch — batch screening of a 1k-100k-row window against a frozen statistical baseline: C1 SPC Nelson R1/R2/R3/R5/R6 (sigma = MRbar/1.128), C2 operating-window drift projection (last-25% vs first-25% steady-row slope -> hours_to_edge, direction-aware, confirmation_needed windows hard-capped at warn+advisory), C3 regime/change-point mapping (in-process reuse of the data-processor fast detector + significance-filtered z-mean segmentation; known_change_points difference -> REGIME_CHANGE_NEW; abnormal share >0.15 -> high, >0.3 -> critical), C4 robust z (0.6745*(x-median)/MAD > 3.5) + Mahalanobis (pre-stored Cholesky, online triangular solve, Wilson-Hilferty chi-square, four-level degradation ladder); (b) fast-screen — incremental 1-500-row screening (<=5s) carrying a ring-buffer state file. Anti-alert-storm trio: 60-min same-key merge with repeat_count, 5-point hysteresis downgrade, 30-row post-change-point quiet zone with center-line re-estimation. Cold start without a baseline builds a SELF baseline (>=100 steady rows, Mahalanobis skipped, 48h TTL reminder). Outputs schema-validated sentinel/alert.json (sentinel-alert/1.0) + Chinese watch_report.md; exits 0 ok / 1 findings / 2 undetermined / 3 gate-fail. Pure analysis: emits alerts and reports ONLY — never dispatches parameters or makes control decisions (v1.4 ruling); evidence grades are advisory strength for the consumer. Trigger: production sentinel, 产线监控, production monitoring, watch mode, fast screening, 增量快筛, SPC alerting, Nelson rules, 控制图告警, drift projection, 漂移投影, regime change alert, 工况变化告警, alert storm suppression, 告警风暴, production data screening, 产线数据巡检. Do NOT use for root-cause diagnosis (use industrial-diagnostician), for DOE / experiment / operating-window ANALYSIS (use industrial-doe-analyzer), as Step 3 inside the 9-stage diagnosis pipeline (use industrial-data-processor), for parameter optimization or any control-action dispatch (use industrial-optimizer-loop — and note IDD never dispatches parameters), or for one-off deep analysis of a single dataset (use industrial-deep-analysis)."
---

# Industrial Sentinel（产线哨兵）

Standing production watch: deterministic screening of sensor/process windows against a frozen
statistical baseline. **Pure-analysis system** — it produces alerts/reports only and NEVER
dispatches parameters or makes control decisions (v1.4 ruling; evidence grades are advisory
strength, action policy belongs to the production/AWS side). All numbers come from
numpy/scipy/pandas scripts (zero LLM, zero network, no subprocess on the hot path); the agent
only interprets and may append Chinese `interpretation` notes — numeric fields are untouchable.

## Modes

| Mode | Entry | Input | Latency | Exit codes |
|------|-------|-------|---------|------------|
| watch（批筛） | `scripts/sentinel.py watch` | 1k–100k 行数据窗 + baseline + config | 1 万行 ≤ 120s（实测 ~1s） | 0 ok / 1 findings / 2 undetermined / 3 gate-fail |
| fast-screen（增量快筛） | `scripts/sentinel_fast.py` | 1–500 新行 + fast_state.json + baseline | ≤ 5s（实测 ~10ms） | 0 / 1 / 2（无基线或输入不合规）/ 3 |

Four checks (watch): C1 SPC Nelson R1/R2/R3/R5/R6 · C2 window drift projection (hours_to_edge)
· C3 regime/change-point mapping (known_change_points difference → REGIME_CHANGE_NEW) ·
C4 robust z + Mahalanobis (four-level degradation ladder). Anti-storm trio: 60-min same-key
merge (repeat_count), 5-point hysteresis downgrade, 30-row post-change-point quiet zone with
center-line re-estimation. See `references/method_notes.md` for every formula and default.

## Inputs / Outputs

| File | Role |
|------|------|
| `schemas/{alert,watch_baseline,watch_config,fast_state}.schema.json` | frozen M0 contracts（枚举以 `.claude/shared/schemas/closedloop_enums.json` 为唯一来源，v1.4 已移除 autonomy） |
| `scripts/build_baseline.py` | doe-analyzer run_dir（recommendations + stability_report **逐值搬运**）+ 历史 CSV → `watch_baseline.json`（median/MAD/q10/q90/相关阵+Cholesky，仅稳态行，≥100 行/组） |
| `scripts/sentinelcore/` | `_io` 加载+路径校验 · `spc` Nelson · `projection` 窗口投影 · `regime_map` 稳态映射 · `robust` 稳健z+马氏 · `suppress` 防风暴 |
| `<out>/sentinel/alert.json` | sentinel-alert/1.0 contract（schema + gate 双验） |
| `<out>/sentinel/watch_report.md` | 中文巡检报告（模板渲染） |

## Dispatch（调用卡）

```javascript
Agent({
  task: `RUN_DIR=<run-dir>
SKILL_PATH=<path-to-.claude/skills/industrial-sentinel>
SHARED_PATH=<path-to-.claude/shared>

Read "$SKILL_PATH/references/agent-protocol.md" and execute Phase 0-4.

Hard constraints (PURE ANALYSIS SYSTEM):
- NEVER dispatch parameters, setpoints, or control actions; alerts are advisory findings only
- Baseline first: no watch_baseline.json -> run scripts/build_baseline.py on history data
  (cold-start SELF baseline is a fallback with 48h TTL, not a substitute)
- watch/fast-screen numbers are script-authored; you may ONLY add alert.interpretation
  notes in Chinese and flip provenance.authored_by to "agent" — never touch numbers/enums
- quality_gate.mjs must exit 0 before reporting done (fix = rerun scripts, max 3 rounds)
- watch_report.md is written in Chinese; JSON enum fields stay English
`,
  effort: "hi"
})
```

Headless (no agent):

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-sentinel/scripts/build_baseline.py \
  --history-csv <history.csv> [--doe-run-dir <doe_run_dir>] --out watch_baseline.json

uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-sentinel/scripts/sentinel.py watch \
  --data <window.csv> --baseline watch_baseline.json --out-dir <out>

node .claude/skills/industrial-sentinel/scripts/quality_gate.mjs \
  <out>/sentinel/alert.json --baseline watch_baseline.json \
  --skill-path .claude/skills/industrial-sentinel --shared-path .claude/shared
```

## Severity semantics (frozen, from evidence-autonomy-alignment.md)

| severity | 语义 | 典型规则 |
|----------|------|----------|
| info | 记录级 | 远期投影（>24h） |
| warn | 趋势 / 待确认 | R2/R3、投影 <24h；confirmation_needed 窗封顶 |
| high | 统计异常 | R1/R5/R6、马氏、投影 <8h |
| critical | 越规格 / ≥3 个不同 key 的 high 同发 | WINDOW_OUT_OF_RANGE |

`urgency`: critical → immediate · high → same_shift · 其余 routine。
`suggested_next_skill`: 根因 → industrial-diagnostician；窗口/工况 → industrial-doe-analyzer。

## Verification

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-sentinel/tests/run_tests.py all
# -> ALL GREEN (F1-F6 + gate tamper battery + performance)
```

## Failure Recovery

| Scenario | Recovery |
|----------|----------|
| 无基线（watch） | self 基线冷启动（48h TTL），同时用 build_baseline.py 固化正式基线 |
| 无基线（fast） | exit 2 拒跑——先建基线 |
| 分组未登记 | UNSEEN_GROUP 告警；扩充历史后重建基线 |
| detector import 失败 | 自动纯 Python 回退（无变点能力），报告中注明 |
| 全窗口 warn 刷屏 | 先调 `thresholds.r2/r3_materiality_z`（method_notes §7），不要逐条“解释掉” |
| gate FAIL | 脚本重算，禁止手改 alert.json 数值/枚举；最多 3 轮 |
