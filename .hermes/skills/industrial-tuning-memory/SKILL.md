---
name: industrial-tuning-memory
description: "Closed-loop tuning experience library (B-line of the closedloop skill suite; standalone — NOT a pipeline stage). Deterministic action→effect attribution: places baseline/effect segments around a logged parameter action (dead-time aware, truncated at the next action), computes Welch before/after deltas with AR(1) effective-n correction, optional group-stratified deltas (formula-aligned with doe-analyzer), and a lightweight anti-spurious chain (detrend shrink check, leave-one-out outlier gate) into an honest attribution state machine (estimable|direction_uncertain|truncated|not_estimable with reason_code; effect=null when not estimable — never fabricated). Maintains an IDD-local experience store (06_experience/tuning_experience.jsonl + accumulated feedback counters) with two entry types (tuning_action_effect, fault_control_recipe), corroboration/refutation driven evidence grades E0-E3 (advisory strength only — dispatch policy is AWS-side, v1.4), local fault-signature playbook matching (regime→product→machine→generic relaxation + 0.5 direction + 0.3 Jaccard + 0.2 regime scoring, threshold 0.55) with a four-level degradation chain, execution-ack anchoring, and a step_detector cold-start path that retro-mines setpoint steps into E0-locked advisory entries. Produces kb_summary.md (regime_key-scenarioized Chinese digest) for the AWS agent to hand to kb_agent — IDD NEVER connects to any knowledge base and NEVER dispatches parameters. All statistics are deterministic numpy/scipy/node scripts (zero LLM). Trigger: 调参经验, 调优经验库, tuning experience, action attribution, 动作归因, 参数调整效果, playbook retrieval, 经验检索, recommendation playbook, retro mining, step detection, 经验入库, corroboration, 佐证. Do NOT use for fault root-cause diagnosis (use industrial-diagnostician), DOE designed-experiment analysis (use industrial-doe-analyzer), target-driven optimization campaigns (use industrial-optimizer-loop), or live anomaly watching (use industrial-sentinel)."
---

# Industrial Tuning Memory（调优经验库）

闭环三件套 B 线：**动作→效果归因 → 本地经验库 → 本地签名检索 → kb-ready 交接**。
纪律继承自诊断体系：**所有数字由确定性脚本计算（零 LLM、零新 Python 依赖），agent 只解读；
确定性门禁以退出码裁决；证据分级仅是建议强度（advisory），下发/执行策略完全归 AWS 侧**。

**架构裁决（v1.4）**：IDD = 纯分析系统。本 skill 的经验存储是 IDD 本地经验库
（`RUN_DIR/06_experience/`），本地完成签名匹配；KB 侧宽知识由 AWS Agent 经 rag-bridge
kb_agent 场景化入库/检索——本 skill **不连任何外部服务**，只产 `kb_summary.md`（kb-ready）交接。

## Inputs / Outputs

### Inputs（`RUN_DIR`）

| 文件 | 说明 |
|------|------|
| `00_input/data.csv` | 时间有序时序数据（Δt = 1 行；时间列 + 指标列 + 可设定列 + 可选 group 列） |
| `00_input/action_log.json` | 调参动作日志（对象/数组/JSONL/目录皆可；schema=`action_log` v1.0；幂等 id = ts8+sha256(canonical)[..8]） |
| `00_input/fault_signature.json` | *(recommend 时)* 故障签名（异常参数集+方向+工况） |
| `00_input/actor_alias_map.json` | *(可选)* 隐私别名映射 `{"raw_id": "eng_01"}`；缺省按 sha 确定性派生 eng_NN |

### Outputs

| 文件 | 门禁 |
|------|:----:|
| `06_experience/attribution/{action_log_id}.json` | 归因报告（schema=`attribution_report`；诚实状态机；not_estimable 必带 reason_code 且 effect=null） |
| `06_experience/tuning_experience.jsonl` | 本地经验库（schema=`tuning_experience` + 本地信封字段 `chunk_id`/`action_signature`/`retro_mined`，交 KB 前剥离） |
| `06_experience/accumulated/state.json` | 佐证/反证台账（feedback 历史 + 计数镜像） |
| `06_experience/kb_summary.md` | kb-ready 中文摘要（regime_key 场景化标题，供 AWS Agent 交 kb_agent） |
| `06_experience/retro_action_log.json` | step_detector 冷启动反推动作日志（E0 锁定、advisory「仅参考」） |
| `conclusions/recommendation.json` | 检索结论（schema=`recommendation`；playbook 命中或四级降级；ack 执行回执锚点） |

## Dispatch

```javascript
Agent({
  agent: "tuning-memory",
  task: `RUN_DIR=<run-dir-path>
SKILL_PATH=<path-to-.claude/skills/industrial-tuning-memory>
SHARED_PATH=<path-to-.claude/shared>

Read "$SKILL_PATH/references/agent-protocol.md" and execute Phase 0-6.

Key constraints:
- Every number comes from scripts — never hand-compute or edit computed values
- attribution_status=not_estimable is a VALID, honest outcome (effect=null) — never fabricate
- evidence_grade E0-E3 is advisory strength ONLY; playbooks[].autonomy_level is the
  frozen contract's AWS-side dispatch-policy carrier — IDD always writes null and
  never sets a policy; never draft dispatch instructions
- KB ingestion happens AWS-side via kb_agent on kb_summary.md — never call any KB/RAG API
- Phase 5 gate (quality_gate.mjs) must pass before reporting done; fix loop max 3
- Reports in Chinese; JSON enums in English
`,
  effort: "hi"
})
```

## Verification

```bash
SKILL_PATH="<path-to-.claude/skills/industrial-tuning-memory>"
SHARED_PATH="<path-to-.claude/shared>"

# 全链：T1-T8（schema×5 + 严格键 + 诚实性 + 枚举字面值 + 库一致性 + 隐私）
node "$SKILL_PATH/scripts/quality_gate.mjs" "$RUN_DIR" \
  --skill-path "$SKILL_PATH" --shared-path "$SHARED_PATH"

# 测试电池 B1-B14
uv run --project "$SHARED_PATH/scripts" python \
  "$SKILL_PATH/tests/run_tests.py" all
```

## Evidence Grades（advisory strength only — dispatch policy is AWS-side）

| 级 | 判据 | 语义 |
|----|------|------|
| E0 | retro 反推 / truncated / confound_detected / attribution_compromised / direction_uncertain | weak，仅参考（advisory） |
| E1 | 单次 estimable 归因（CI 可跨 0） | observed |
| E2 | 同工况佐证 ≥2 ∧ CI95 不跨 0 ∧ 无混杂 ∧ estimable ∧ 非反推 ∧ 非 unconfirmed | confirmed |
| E3 | E2 ∧ 跨工况方向一致（≥2 regime_key） | cross_regime |

升降级**只由计数与统计门驱动**（corroboration/refutation/CI），LLM 永不参与。任何 refutation 事件
即时封顶 E1；refutation≥2 → verified 降 observation。

## Failure Recovery

| 场景 | 处置 |
|------|------|
| 指标列缺失 / 基线 <10 有效点 / 效果段 <2 点 | `not_estimable`（reason_code=metric_missing / min_points），effect=null — 这是诚实结论，不是失败 |
| 调用方无法提供死区时间 | `--dead-time unknown` → `not_estimable/dead_time_unknown`；缺省 0 则在经验条目注记降级 |
| 效果窗被下一动作截断 | status=truncated（E0），truncated_by 记录截断源 |
| 同参数重叠动作 | attribution_compromised=true（E0，reason=overlapping_action） |
| 本地经验库为空 / 无命中 | 四级降级链 regime→product→machine→generic → direction_only → fallback_generic（doe-analyzer 提示）→ no_playbook_hit |
| 无动作日志冷启动 | step_detector 反推 → E0 advisory 条目（不参与 E2 晋升；工程师 confirmed 反馈补归属） |
| Gate FAIL | 重跑对应脚本步骤修正（禁止手改 JSON 数字），最多 3 轮 |
