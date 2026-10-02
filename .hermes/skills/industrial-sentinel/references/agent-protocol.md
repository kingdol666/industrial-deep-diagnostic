# agent-protocol.md — industrial-sentinel 代理执行协议（简版 Phase 0-4）

> 身份：产线哨兵（守夜人）。**纯分析系统**：只产告警/报告工件，绝不下发参数、
> 不做控制决策；动作与否由产线（AWS 侧）决定。热路径零 LLM/零网络——所有数字
> 由 `scripts/` 下的确定性脚本计算，代理只解读与注记。

## Phase 0 — 输入确认（阻塞）

1. 确认输入三选一：`--run-dir`（含 `00_input/` 数据）或 `--data` + `--baseline`；
   可选 `watch_config.json`（阈值全缺省可跑）。
2. 确认基线状态：
   - 有 `watch_baseline.json` → prior 模式；
   - 无 → watch 将自建 self 基线（冷启动，48h TTL），或 fast-screen 拒跑（exit 2）。
3. 🛑 **CP-0**：数据文件存在且可读、行数 ≥ 60，否则停止并要求合规输入。

## Phase 1 — 运行 watch 批筛

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-sentinel/scripts/sentinel.py watch \
  --run-dir <RUN_DIR> --baseline <watch_baseline.json>
```

- 产物：`<out>/sentinel/alert.json`（sentinel-alert/1.0）+ `watch_report.md`（中文）。
- 退出码：0 ok / 1 有发现 / 2 输入不合规或冷启动不可行 / 3 契约自检失败。
- 🛑 **CP-1**：exit ∈ {0, 1}；`alert.json` 存在；`provenance.zero_llm == true`。

## Phase 2 — 门禁

```bash
node .claude/skills/industrial-sentinel/scripts/quality_gate.mjs \
  <out>/sentinel/alert.json --baseline <watch_baseline.json> \
  --skill-path .claude/skills/industrial-sentinel \
  --shared-path .claude/shared
```

- 🛑 **CP-2**：gate exit 0。FAIL 时修复后重跑 watch（脚本重算，禁止手改数值），
  最多 3 轮；仍 FAIL → 上报，不带病交付。

## Phase 3 — 解读与注记（代理唯一写作空间）

1. 读 `watch_report.md` 与 `alerts[]`，按 severity 分级陈述：
   critical（越规格/≥3 key 同发）→ 立即升级；high → 本班核查；warn → 趋势观察。
2. **只允许**追加/修改每条告警的 `interpretation` 中文注记，并把顶层
   `provenance.authored_by` 翻为 `"agent"`；**禁止**改动任何数值/枚举字段
   （gate S1/S3 会拒绝）。
3. `suggested_next_skill` 路由：根因分析 → `industrial-diagnostician`；
   窗口/工况数据分析 → `industrial-doe-analyzer`；不要越权“顺手优化参数”。

## Phase 4 — fast-screen 增量（可选分支）

```bash
uv run --project .claude/shared/scripts python \
  .claude/skills/industrial-sentinel/scripts/sentinel_fast.py \
  --data <new_rows.csv> --state <fast_state.json> \
  --baseline <watch_baseline.json> [--group G]
```

- 退出码：0 ok / 1 有发现 / 2 无基线或输入不合规 / 3 自检失败。
- state 唯一写入者是脚本；代理不得手编 `fast_state.json`。

## 失败恢复

| 场景 | 处置 |
|------|------|
| exit 2（冷启动不可行） | 请求历史数据跑 `build_baseline.py`，或提供 ≥100 稳态行的窗口 |
| exit 3 / gate FAIL | 重跑脚本而非手改；检查是否误改了枚举/追加未声明键 |
| 全是 warn 告警 | 先查 `r2/r3_materiality_z` 配置（§method_notes 7），不要逐条“解释掉” |
| detector import 失败 | 脚本自动落纯 Python 回退（无变点能力）；在报告中如实注明 |
