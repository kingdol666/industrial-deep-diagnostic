# 人工复核与记忆复用（HITL）

这项功能补充的是**分析完成后的现场验证**，与运行中的 `awaiting_input`、自动 Judge 和本体提案审批不同。

## 控制台

- **分析结果库 → 详情** / **报告 → 人工复核与记忆**：记录实际效果、验证评论、后续可复用经验，可选填人工修订摘要。仅有明确任务归属的报告可原地复核。
- **产线记忆 → 人工复核与记忆**：筛选和编辑已留痕的记录，包括无效或已撤销的记录。查看修订历史可核对状态、作者和时间。
- 原报告、工件、模型评分和自动摘要不被覆盖。二次摘要将已有分析摘要、人工反馈与经验分区归纳，不生成额外事实；可人工改写，清空人工摘要则恢复系统版。修改反馈或经验时，旧人工摘要仍在历史中，不自动沿用。
- 本体资产编辑沿用本体管理页的校验和新版本发布流程。人工复核不会直接修改本体或把评论冒充正式证据。

## API

`{base}` 为 `/api/results` 或 `/api/external/v1/results`。`id` 为已完成、非模拟的分析的 `run_id`。

| 方法与路径 | 用途 |
|---|---|
| `GET {base}/{id}/review` | 当前复核；未写入过的记录为 `unreviewed`、`revision: 0` |
| `PATCH {base}/{id}/review` | 提交下一版；登录会话才可写入，API Token 可按权限读取 |
| `GET {base}/{id}/review/history?before=N` | 逆序版本分页，`next_before` 为下一页游标 |
| `GET /api/line-memory/reviews?status=ineffective&offset=0` | 人工复核记忆列表，按调用者权限过滤；`status` 可省略 |
| `GET /api/diagnosis/review-context/{runId}` | 按该任务的归属与登记产线别名预览符合条件的人工先验；不是实际启动注入快照 |

```json
{
  "revision": 0,
  "status": "confirmed",
  "comment": "调整后连续三批复测改善，尚无长期数据。",
  "takeaway": "同工况先排查测温校准，再用独立批次复验。",
  "reuse_enabled": true
}
```

`revision` 是读到的版本；其它字段按需提交。`comment`、`takeaway` 与可选 `summary` 可传 `null` 清空。过期版本返回 `409 REVIEW_REVISION_CONFLICT`；重新获取版本后再提交。外人和已删除任务按不存在处理。撤销提交 `status: "unreviewed"`，不是删除版本。`stale: true` 表示任务重新完成，旧确认须复核后才重新进入人工先验。

## 复用规则

- `confirmed` 且 `reuse_enabled: true`：匹配同归属、同场景或同产线别名的新任务时，最多优先带入 3 条 L5 历史参考。引用标明来源任务和人工修订版本；人工状态不改变自动证据等级。
- `ineffective` 或关闭复用：保留原始记录和人工审计，但过滤该任务对新诊断先验的贡献，再计算自动共性，不让它变成共性、候选、线索或最新状态。
- `unreviewed`：不进入人工确认参考；若未关闭复用，原始自动证据仍按普通规则参与。
- 仅对新启动构造上下文；已发送给模型的历史上下文不会被追溯修改。实际注入内容及人工版本可见于后续完成任务的 `00_input/context/line_memory.json`。
