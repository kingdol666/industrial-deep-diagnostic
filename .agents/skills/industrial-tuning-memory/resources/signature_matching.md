# Signature Matching（本地签名匹配 · playbook 检索）

脚本：`scripts/match_playbook.mjs recommend`。数据源 = IDD 本地经验库
（`06_experience/tuning_experience.jsonl`）——**本地匹配，无任何外部服务调用**；
KB 侧宽知识检索由 AWS Agent 经 kb_agent 负责（双通道，编排权在 AWS）。

## 输入签名（fault_signature.schema.json v1.0）

```
anomalous_params: [{parameter, direction: high|low|unknown, severity?}]
regime: {product, machine, regime_label}   degraded_metric   source_ref
```

## 两阶段匹配

### 阶段 1：工况硬过滤逐级放宽

`regime → product → machine → generic`（match_scopes，来自 closedloop_enums.json）：

- regime：条目 `regime_key == 查询 regime_key`（`product|machine|regime_label` 复合键）
- product / machine：对应槽位相等且查询槽位非空
- generic：全部条目

逐级尝试，**在某级找到 score≥0.55 即停**（match_scope = 该级）；每一级的尝试结果都
写入 `degradation_path`。

### 阶段 2：参数重叠分（阈值 0.55）

```
score = 0.5 × direction_hit + 0.3 × Jaccard + 0.2 × regime_overlap
```

- **direction_hit**：查询异常参数中，方向与条目记录方向一致（且双方非 unknown）的比例。
  方向语义按条目类型双轨（见下）。
- **Jaccard**：参数名集合 |Q∩E| / |Q∪E|。条目参数集 = action_sequence 参数
  ∪（fault_control_recipe 的）fault_signature 异常参数。
- **regime_overlap**：查询 regime 非空槽位与条目 regime_key 槽位的吻合比例；查询无工况
  信息时计 0。

**方向语义双轨（重要）**：

| 条目类型 | 记录的方向 | 语义 |
|----------|-----------|------|
| fault_control_recipe | fault_signature.anomalous_params.direction | 故障形态方向（与查询直接同形比较） |
| tuning_action_effect | sign(to − from) | 已实施动作的方向；from 缺失记 unknown |

两者都编码在 entry 的 `action_sequence` / `fault_signature` 上；match_score 是检索启发式，
**advisory only**，不构成执行授权。

## 四级降级链（status → artifact）

```
playbook_hit（某级 score≥0.55）
  → direction_only（有候选、有方向命中，但 score<0.55：仅方向知识）
    → fallback_generic（参数重叠不足：回落 + doe-analyzer 提示 fallback.doe_analyzer_hint）
      → no_playbook_hit（本地经验库为空；提示同样给出）
```

`degradation_path` 数组记录每一级的候选数/最佳分与最终落点，供上游审计。

## 执行回执链（ack）

- `match_playbook.mjs ack --ack-file ack-{ts}-{seq}.json`：
  `{recommendation_id, status: received|executed|rejected, executed_action_log_id, note}`
  → 写入 `conclusions/recommendation.json` 的 `ack` 字段。
- 超时未回执：`ack` 保持 null → 该 recommendation 视为 **unconfirmed**，不参与佐证晋升。
- AWS 执行动作必须以 action_log 回写（actor_type=aws_executor，携带 recommendation_ref）；
  缺 recommendation_ref 或 ack 未到 → 经验条目 `confirm_status=unconfirmed`，封顶 E1。

## v1.4 提醒

recommendation 的 `evidence_grade`（E0-E3）只是建议强度；下发策略（dispatch policy）
由 AWS 侧决定。冻结契约保留 `playbooks[].autonomy_level` 字段作为 AWS 侧
dispatch-policy 载体——**IDD 恒写 null**，绝不设 suggest/approve/auto 任何策略值。
