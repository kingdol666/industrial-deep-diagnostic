# 优化闭环报告 · OPT-20261014-001

> 本报告由 `optimizer.py converge` 确定性生成（零 LLM）；全部数字为脚本产出，
> agent 只做解读，绝不改写数值。IDD 为纯分析系统：本报告只产分析工件，不下发参数。

## 概要

- 阶段：**converged**（验证状态：verified）
- 目标：优品率 · goal=maximize · target_range=None
- 预算使用：4/12 轮，
  12/15 试验点，
  重复 14 次

## 最优点（incumbent）

```json
{
  "TDO定型区温度CX6": 190.908707,
  "TDO拉伸区温度CX4": 243.24442,
  "纵拉拉伸速度": 53.137229
}
```

{"优品率": {"mean": 99.05, "sd": 0.105105, "n": 3}}

## 收敛判定（双门槛）

- m≥3 重复全落窗：True
- 单侧 95% CI 在限内：True
- D ≥ 0.8·D_max：True（D=0.998721，
  D_max=1.0）
- **达标收敛 ≠ 全局最优**：模型驻点（max，盒内）距 incumbent 相对距离 24.9%（>2%）；驻点设定点见 optimization_conclusion.json 的 `recommended_refinement`，建议补一轮 confirm_replicates 后再决定是否切换配方
## 轮次历史

| 轮 | 阶段 | 方法 | 试验数 | best_D | 失败 |
|---|---|---|---|---|---|
| R001 | explore | lhs_fill | 9 | 1.0 | 0 |
| R002 | exploit | gp_ei | 1 | 1.0 | 0 |
| R003 | exploit | gp_ei | 1 | 1.0 | 0 |
| R004 | confirm | confirm_replicates | 1 | 1.0 | 0 |

## 护栏事件

[
  {
    "code": "CONFIRM_EVAL",
    "ts": "2026-10-14T03:43:48.562781+00:00",
    "detail": "confirm round R004: values=[99.002, 98.544, 99.225], ci_in_limits=True, desirability_gate=True"
  }
]

## 复用

见 `conclusions/recipe.json`（含 guardrails 包络与 usage_rules）与
`06_experience/kb_summary.md`（regime_key 场景化摘要，供 AWS 经 kb_agent 入库）。
