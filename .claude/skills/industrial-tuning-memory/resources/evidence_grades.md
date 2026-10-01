# Evidence Grades E0-E3（建议强度标注 · v1.4）

权威来源：`.claude/shared/references/evidence-autonomy-alignment.md` +
`.claude/shared/schemas/closedloop_enums.json`（机器可查字面值）。三件套共用同一份。

## 判据（机器门）

| 级 | 判据 | 语义 | confidence_label |
|----|------|------|------------------|
| E0 | retro-mined ∨ attribution_status=truncated ∨ confound_detected ∨ attribution_compromised ∨ direction_uncertain | weak——仅参考（reference only） | observation |
| E1 | 单次 estimable 归因（CI 可跨 0） | observed | observation |
| E2 | 同工况佐证 corroboration_count≥2 ∧ CI95 不跨 0 ∧ confound_detected=false ∧ attribution_status=estimable ∧ 非反推 ∧ 非 unconfirmed | confirmed | verified |
| E3 | E2 ∧ cross_regime_consistent（≥2 个 regime_key 方向一致，且全部 E2） | cross_regime | verified |

## 升降级唯一通路（计数 + 统计门，LLM 永不参与）

- 一切新条目从 observation / E0-E1 起步。
- 升级：同工况二次提交（不同 action_log_id、同 action 签名）→ corroboration+1；
  E2 门全满足 → verified；跨工况方向一致 → E3。
- **任何 refutation 事件（ineffective|harmful feedback）即时封顶 E1**；
  refutation≥2 → verified 降 observation。
- `unconfirmed`（aws_executor 动作缺 recommendation_ref，或对应 recommendation 无
  received/executed ack）→ 排除在佐证晋升之外（封顶 E1）。
- 反推条目（retro_mined）**永久锁定 E0**，不参与 E2 晋升；工程师 `confirmed` 反馈只补归属
  （记录 confirm_status），解锁须由工程师以本人身份新录动作日志形成非反推条目再佐证。

## v1.4 裁决（必读）

IDD = 纯分析系统。**证据分级是给消费方的"建议强度"标注，不是授权级别**。是否执行、
如何执行（suggest / approve_required / auto_within_guardrails 的 dispatch policy）完全由
AWS 侧决定；冻结契约保留 `playbooks[].autonomy_level` 字段作为 AWS 侧载体，IDD 恒写
`null`，绝不设任何策略值。
