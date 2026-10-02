# 优化闭环报告 · OPT-20261001-001

> 本报告由 `optimizer.py converge` 确定性生成（零 LLM）；全部数字为脚本产出，
> agent 只做解读，绝不改写数值。IDD 为纯分析系统：本报告只产分析工件，不下发参数。

## 概要

- 阶段：**converged**（验证状态：verified）
- 目标：yield_pct · goal=target · target_range=[98.0, 100.2]
- 预算使用：5/10 轮，
  20/30 试验点，
  重复 24 次

## 最优点（incumbent）

```json
{
  "press": 0.559759,
  "temp": 82.0
}
```

{"yield_pct": {"mean": 99.1053, "sd": 0.0, "n": 1}}

## 收敛判定（双门槛）

- m≥3 重复全落窗：True
- 单侧 95% CI 在限内：True
- D ≥ 0.8·D_max：True（D=0.862697，
  D_max=0.995182）

## 轮次历史

| 轮 | 阶段 | 方法 | 试验数 | best_D | 失败 |
|---|---|---|---|---|---|
| R001 | explore | lhs_fill | 8 | 0.933909 | 0 |
| R002 | exploit | rsm_augment | 8 | 0.995182 | 0 |
| R003 | confirm | confirm_replicates | 1 | 0.995182 | 0 |
| R004 | exploit | lhs_fill | 2 | 0.995182 | 0 |
| R005 | confirm | confirm_replicates | 1 | 0.995182 | 0 |

## 护栏事件

[
  {
    "code": "CONFIRM_EVAL",
    "ts": "2026-10-01T14:24:20.486089+00:00",
    "detail": "confirm round R003: values=[98.6396, 98.8891, 99.0174], ci_in_limits=True, desirability_gate=False"
  },
  {
    "code": "CONFIRM_EVAL",
    "ts": "2026-10-01T14:24:25.690528+00:00",
    "detail": "confirm round R005: values=[98.7972, 99.1047, 98.945], ci_in_limits=True, desirability_gate=True"
  }
]

## 复用

见 `conclusions/recipe.json`（含 guardrails 包络与 usage_rules）与
`06_experience/kb_summary.md`（regime_key 场景化摘要，供 AWS 经 kb_agent 入库）。
