# 优化闭环报告 · OPT-20261001-007

> 本报告由 `optimizer.py converge` 确定性生成（零 LLM）；全部数字为脚本产出，
> agent 只做解读，绝不改写数值。IDD 为纯分析系统：本报告只产分析工件，不下发参数。

## 概要

- 阶段：**converged**（验证状态：verified）
- 目标：dev_pos07 · goal=target · target_range=[0.0, 0.15]
- 预算使用：8/14 轮，
  25/80 试验点，
  重复 31 次

## 最优点（incumbent）

```json
{
  "die_bolt_T3_pct": 1.541242
}
```

{"dev_pos07": {"mean": 0.076333, "sd": 0.019324, "n": 3}}

## 收敛判定（双门槛）

- m≥3 重复全落窗：True
- 单侧 95% CI 在限内：True
- D ≥ 0.8·D_max：True（D=0.982222，
  D_max=0.982222）

## 轮次历史

| 轮 | 阶段 | 方法 | 试验数 | best_D | 失败 |
|---|---|---|---|---|---|
| R001 | explore | lhs_fill | 6 | 0.301333 | 0 |
| R002 | explore | rsm_augment | 6 | 0.525333 | 0 |
| R003 | exploit | rsm_augment | 6 | 0.829333 | 0 |
| R004 | confirm | confirm_replicates | 1 | 0.829333 | 0 |
| R005 | exploit | lhs_fill | 2 | 0.829333 | 0 |
| R006 | confirm | confirm_replicates | 1 | 0.829333 | 0 |
| R007 | exploit | lhs_fill | 2 | 0.829333 | 0 |
| R008 | confirm | confirm_replicates | 1 | 0.982222 | 0 |

## 护栏事件

[
  {
    "code": "CONFIRM_EVAL",
    "ts": "2026-10-01T13:05:58.383840+00:00",
    "detail": "confirm round R004: values=[0.0981, 0.085, 0.1057], ci_in_limits=True, desirability_gate=False"
  },
  {
    "code": "CONFIRM_EVAL",
    "ts": "2026-10-01T13:06:02.799689+00:00",
    "detail": "confirm round R006: values=[0.0559, 0.0917, 0.0256], ci_in_limits=True, desirability_gate=False"
  },
  {
    "code": "CONFIRM_EVAL",
    "ts": "2026-10-01T13:06:07.233444+00:00",
    "detail": "confirm round R008: values=[0.0543, 0.0904, 0.0843], ci_in_limits=True, desirability_gate=True"
  }
]

## 复用

见 `conclusions/recipe.json`（含 guardrails 包络与 usage_rules）与
`06_experience/kb_summary.md`（regime_key 场景化摘要，供 AWS 经 kb_agent 入库）。
