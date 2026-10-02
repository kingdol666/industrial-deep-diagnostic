# 优化闭环报告 · OPT-20261001-006

> 本报告由 `optimizer.py converge` 确定性生成（零 LLM）；全部数字为脚本产出，
> agent 只做解读，绝不改写数值。IDD 为纯分析系统：本报告只产分析工件，不下发参数。

## 概要

- 阶段：**converged**（验证状态：verified）
- 目标：dev_pos07 · goal=minimize · target_range=None
- 预算使用：4/14 轮，
  19/80 试验点，
  重复 21 次

## 最优点（incumbent）

```json
{
  "die_bolt_T3_pct": 2.041175
}
```

{"dev_pos07": {"mean": 0.0226, "sd": 0.0, "n": 1}}

## 收敛判定（双门槛）

- m≥3 重复全落窗：True
- 单侧 95% CI 在限内：True
- D ≥ 0.8·D_max：True（D=1.0，
  D_max=1.0）

## 轮次历史

| 轮 | 阶段 | 方法 | 试验数 | best_D | 失败 |
|---|---|---|---|---|---|
| R001 | explore | lhs_fill | 6 | 1.0 | 0 |
| R002 | explore | rsm_augment | 6 | 1.0 | 0 |
| R003 | exploit | rsm_augment | 6 | 1.0 | 0 |
| R004 | confirm | confirm_replicates | 1 | 1.0 | 0 |

## 护栏事件

[
  {
    "code": "CONFIRM_EVAL",
    "ts": "2026-10-01T13:26:22.300485+00:00",
    "detail": "confirm round R004: values=[0.0459, 0.0328, 0.0535], ci_in_limits=True, desirability_gate=True"
  }
]

## 复用

见 `conclusions/recipe.json`（含 guardrails 包络与 usage_rules）与
`06_experience/kb_summary.md`（regime_key 场景化摘要，供 AWS 经 kb_agent 入库）。
