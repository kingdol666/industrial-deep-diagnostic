# IDD 实地测试场 — fieldtest-20261004

多 Agent 协同的实地功能测试，遵循本仓库 benchmark 纪律：**出题与解题隔离、真值盲态、独立批改**。

## 角色

| 角色 | 承担者 | 职责 |
|---|---|---|
| 出题人 Examiner | subagent A | 生成 5 个场景数据集 + 任务简报（brief.md），真值写在 `truth/`（测试者禁读） |
| 测试者 Tester | subagent B | 只读 `brief.md` + 数据，盲态调用各功能真实 CLI，产物写 `results/` |
| 批改人 Grader | subagent A（续） | 对照 `truth/` 与最佳实践清单批改，产出 `scorecard.md` |

## 用例

| # | 场景 | 被测功能 | 对应真实使用场景 |
|---|---|---|---|
| T1 | **在线数据接驳箱**：模拟 3 批次投放的混合格式文件夹（CSV/TSV/JSON/XLSX/MD表/HTML表，含 GBK 中文导出与分号分隔） | `industrial-data-preprocessor` 目录模式 | 后续在线数据落盘到一个文件夹后的自适应分析入口 |
| T2 | **产线常驻监控**：历史建档 → 正常窗 / 缓慢漂移窗 / 阶跃变点窗 / 无基线 | `industrial-sentinel`（build_baseline + watch + fast-screen） | 运行中产线的 SPC/漂移/变点监控与增量快筛 |
| T3 | **调参归因与经验检索**：动作日志 → 归因（可估与不可估）→ playbook 检索 → 佐证回填 | `industrial-tuning-memory`（attribute/build/recommend/feedback） | 调参经验沉淀、检索、跨 run 佐证晋升 |
| T4 | **闭环小试寻优**：2 因子黑箱响应面（藏已知最优点 + 噪声），design→plant→ingest 轮次 | `industrial-optimizer-loop`（init/design/ingest/converge） | 目标驱动多轮布点寻优到收敛配方 |
| T5 | **DOE 设计分析**：已知主效应/交互的因子表 → 效应/ANOVA/操作窗 | `industrial-doe-analyzer`（designed 模式） | 实验设计与工艺参数窗口分析 |

## 目录

```
cases/T1..T5/brief.md   ← 测试者唯一入口（不含真值）
cases/T1..T5/<data>     ← 场景数据
cases/T4/plant_sim.py   ← 黑箱产线模拟器（测试者按接口查询，不知参数真值）
truth/                  ← 出题人真值 + 批改依据（测试者禁读）
results/T*/             ← 测试者产物：结果 + 逐条命令台账
scorecard.md            ← 批改成绩单
```

## 纪律（违反即结果无效）

1. 测试者**不得**读取 `truth/` 下任何文件。
2. 全部走真实 CLI（venv python / node），不许手算替代；每条命令与退出码记入台账。
3. 有界：数据 ≤500 行/文件（T2 history 720 行为例外，已备案）、optimizer ≤6 轮、单用例 ≤10 分钟、零 LLM 引擎 spawn。
4. 遇文档/CLI 不清：如实记录阻塞点即为测试结论之一，不猜测硬编。

## 结果（2026-10-04）

- **成绩单：`scorecard.md`** — 5/5 PASS，测试者盲态自判全部成立，无一处改判；T4 附设计层发现（in-tolerance 收敛符合契约但驻点信息未被利用）。
- 执行台账 `results/ledger.md`，逐用例报告 `results/T*_result.md` 与 `results/T*/T*_report.md`。
- 9 项毛边发现 + Top-5 修复建议见成绩单末节（最重要：sentinel `_io.hours_axis` 的 pandas 3.0.5 时间单位 bug）。
