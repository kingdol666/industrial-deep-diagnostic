# 优化闭环轮次报告 · R{round_id} · {campaign_id}

> 本文件为轮次模板（agent 解读用）。全部数字来自脚本产出（authored_by=script），
> agent 只做解读，绝不改写数值。IDD 为纯分析系统：本报告只产分析工件，不下发参数。

## 本轮设计

- 轮次/阶段/方法：{round_id} / {phase} / {method}
- 批量：{n_trials} 个布点（重复 {replicates} 次；重复单独计数，不占 max_trials）
- 建议布点（**建议，非指令**；是否执行由 AWS/人工决定）：

| trial_id | 设定点 | 预测 D | EI | 外推标记 | 选择理由（脚本原文） |
|---|---|---|---|---|---|
{trial_rows}

## 模型摘要

- kind: {model_kind} · fallback_active: {fallback_active}
- log ML: {log_ml} · cond(K): {cond_K} · noise_source: {noise_source}
- lengthscales（编码）: {lengthscales}

## 状态

- phase: {state_phase} · stall: {stall} · max_EI: {max_ei} · dup_ratio: {dup_ratio}
- 下一步（脚本判定）：{next_action}

## Agent 解读（唯一允许的自由文本区）

- {interpretation_zh}

## 外推与安全披露

- extrapolation=true 的布点：{extrapolation_list}（越数据支撑，执行风险由 AWS/人工评估）
- 安全约束核查：{safety_note}
