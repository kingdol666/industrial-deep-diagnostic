# Evidence ↔ Autonomy 权威对齐表（closed-loop suite）

- 生效：2026-10-01 · 依据：plan industrial-closedloop-skills-v1 §2 + 互通复用席评审 v1.1
- 地位：**唯一权威**。三件套（sentinel / tuning-memory / optimizer-loop）与既有诊断体系的所有分级词汇以本表为准；机器可查字面值在 `.claude/shared/schemas/closedloop_enums.json`。
- 已知历史歧义声明：诊断体系内部有两套 "L" 词汇——`agent-protocol.md` 的 L1-L7（证据来源层级）与 `physics_inference_framework.md` 的 L1-L5（物理推理阶梯）——互不相干，本表不改动它们，只对齐闭环套件新增词汇。

## 主对齐表

| 原料（现有等级） | 语义 | RAG confidence_label | 新 E 级 | sentinel severity | urgency | autonomy |
|---|---|---|---|---|---|---|
| L1 直接测量 / L2 用户文档 | 事实记录 | — | （E 级原料，非 E 级） | info（记录级） | routine | — |
| L3 统计+验证（弱：CI 跨 0 / confirmation_needed:true 窗） | doe-analyzer grade B 观测窗 | observation | E1 observed | warn（R2/R3、投影<24h；观测窗投影封顶 warn=契约一致，见下） | same_shift | suggest |
| L3 统计+验证（强：单次 estimable，CI 不跨 0） | — | observation | E1 observed | high（R1/R5/R6/马氏/投影<8h） | same_shift/immediate | suggest |
| L3 × 同工况佐证 ≥2 | RAG corroboration_count≥2 → verified | verified | **E2 confirmed** | —（经验条目不进告警） | — | approve_required |
| L3 × 跨工况方向一致（≥2 regime_key） | cross_regime_consistent 派生 | verified | **E3 cross_regime** | — | — | approve_required；auto_within_guardrails 仅 opt-in ∧ 非外推点 |
| L5 领域推断 / retro 反推 / truncated / confound / compromised | 歧义即真相（NEEDS_DATA 同源思想） | observation（retro）或降级 | **E0 weak**（锁 suggest，永不参与 E2 晋升） | — | — | suggest（锁死） |
| 越规格 / 物理限直接测得违规 | spec violation | — | — | critical（或 ≥3 条不同 key 的 high 同发） | immediate | 人工动作 |

## 两条"契约一致"声明（从巧合升格为契约）

1. doe-analyzer 观测窗 `confirmation_needed:true`（G4 硬门）↔ sentinel 窗口投影告警 `advisory:true` + severity 封顶 warn——同一语义在两个 skill 的强制一致。
2. RAG 既有 `corroboration_count≥2 → verified` ↔ tuning-memory E2 晋升条件（同工况佐证≥2 ∧ CI 不跨 0 ∧ 无混杂）——E2 的机器判据就是 RAG verified 状态加统计门。

## 升降级规则（唯一通路）

- 一切新条目/建议从 `suggest` 起步。
- 升级只由计数与统计门驱动：corroboration_count（/experience/accumulate 佐证）、refutation_count（feedback 反证）、CI 判定——**LLM 永远不参与升降级判断**。
- 任何 refutation 事件（ineffective|harmful）即时降回 suggest；refutation≥2 → verified 降 observation。
- `auto_within_guardrails` 三重前置缺一不可：AWS 侧配置 opt-in ∧ evidence_grade==E3 ∧ 当前点非外推（extrapolation=false）。

## 契约 #6 裁决（确认试验→窗口升级）

**禁止原地翻转 doe-analyzer recommendations 的 `confirmation_needed` 字段**——该字段受 doe-analyzer G4 硬门保护，翻转即 gate FAIL。正确路径：确认试验结果作为 designed 模式新数据 → 重跑 doe-analyzer → 产出**新版本 recommendations（版本化 supersede）**。归属：optimizer-loop confirm 段数据 / tuning-memory 执行回写动作 + doe-analyzer 重分析；里程碑 v2 立项。
