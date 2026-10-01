# industrial-doe-analyzer 完整端到端测试报告

- 日期：2026-10-01 · 执行方式：headless 脚本 + 真实 subagent + 独立核验（不信任自报）
- 结论：**四组 E2E 全部通过；过程中抓出并修复 6 个真实缺陷；回归 53/53 保持全绿**

## E2E-1 designed 档全流程（68 行 × 7 列，2 响应带规格限 + 中文类别因子 + 区组）

| 项 | 结果 |
|---|---|
| 数据 | 3 数值因子 + 类别因子「助磨剂」+ 区组 batch；2^4 全因子 × 4 重复 + 4 中心点；植入主效应/交互/区组效应（seed 88） |
| 设计识别 | **full_factorial**（4 中心点自动剥离后 16 组合 × 4 重复，balanced）✔ |
| 统计 | 效应表：media_fill/sep_speed/助磨剂/交互显著（q<1e-26 级），moisture 不显著；model R²=0.996 |
| 窗口 | OW-001 media_fill [24,29]（Δ比能耗 −0.387/单位）、OW-002 sep_speed [912.5,1000]；端点触边界 → **extrapolation:true 正确标记** |
| 类别因子 | setpoint「助磨剂=高」（与植入效应方向一致）✔ |
| 门禁 | **15/15 ALL PASS** · grade A · 用时 4.8s |

## E2E-1b 真实 agent 按协议增强（Phase 3-6）

| 项 | 结果 |
|---|---|
| 执行 | 独立 subagent 读协议→增强结论/建议→过门禁→写 report.md→交接卡 |
| **数字不变性（独立 diff 核验）** | effect_table/model **逐字节不变**；recommendations **31 个数值字段不变**（watchlist 2→5 为协议允许的补充条目）；doe_conclusion 仅 statement 改写 + limitations 0→7 + n_watchlist 计数同步 2→5（与实际条数一致） |
| 红线 | authored_by script→agent 两处翻转 ✔；confirmation_needed/confidence/range 未触碰 ✔ |
| 门禁 | 本人独立复跑 **15/15**（非自报）✔ |
| 报告 | report.md 8836 字符，三层结构（10 秒卡/1 分钟证据/深读审计）11 节，数字全部标注来源工件 ✔ |
| 事件 | .pipeline_events.jsonl 合法 JSONL（agent_start/agent_complete），append-pipeline-event.mjs 兼容 ✔ |

## E2E-2 observational 档用户上下文全流程（5000 行 × 20 列 + 规格限）

| 项 | 结果 |
|---|---|
| 执行 | 用户 analysis_context（2 响应带 LSL/USL/target/weight、16 因子、时间列）→ 全流程 2m41s |
| 能力（诚实口径） | fineness 非正态 → **Cpk 标 INDICATIVE + Cnp=0.1997** ✔；specific_energy 正态单侧规格 → Cp=None、Cpk=Cpu=38.38（within, MR̄/d2）✔ |
| 稳定性 | 10 稳态段（选 3）、2 变点 ✔ |
| 相关 | 32 对，4 对 q<0.05 且全部防伪 PASS ✔ |
| 窗口 | 4 窗全部 **confidence=low + confirmation_needed=true**（G4）✔ |
| 门禁 | **14/14 ALL PASS** |

## E2E-3 边界与安全电池

| 用例 | 结果 |
|---|---|
| 空 CSV（0 行） | **exit 1**，干净报错 `INSUFFICIENT_DATA`（修复前会错误产出 0 行合同） |
| 路径穿越 `--data ../../..` | **exit 2**，干净报错 `path outside allowed roots`（无 traceback） |
| 零方差因子 | exit 0，caveat ZERO_VARIANCE 入档，保守无窗口 |
| 事件日志 | run_manifest → append-pipeline-event.mjs 写入成功、JSONL 合法 |
| 夹具回归 | **53/53 ALL GREEN**（每次修复后全量重跑，共 3 轮） |
| 镜像 | `sync --check` exit 0 |

## E2E-4 下游消费模拟（模拟调参 Agent 依合同行动）

两份合同均可自描述消费：designed 档 → OW-001/002 判入"需工艺确认（外推端点）"，无窗可直接盲执行；observational 档 → 4 窗全部强制进"需确认试验"通道 → CF-001。适用域/失效条件/使用规则/move 指令全部可机读执行。**CONTRACT SELF-DESCRIBING: OK**

## 过程中抓出并修复的缺陷（6 个）

1. `designed_windows` 对类别显著因子 KeyError（网格假设 mean/half_range）→ 类别因子改走 setpoint 建议，网格仅数值因子
2. 混合（类别+数值）设计带中心点被误判 observational → 新增"剥离中心点重试"检测通道
3. 剥离后连续列的"每组合恰一次"被误判平衡全因子 → 离散判定加硬守卫（每因子 ≤8 水平、组合积 ≤256、k≥2）
4. 空 CSV 产出 0 行合同 → INSUFFICIENT_DATA/NO_NUMERIC_COLUMNS 守卫，exit 1
5. 路径穿越裸 traceback → main() 统一干净错误出口 exit 2
6. 合同 schema 不允许类别 setpoint 字符串值 → `setpoints.value` 扩为 number|string|null

## 已知行为（非缺陷）

- 同一 RUN_DIR 先后跑两种模式时，前一种模式的 02_analysis 遗留工件不会被删除；agent 协议要求在报告中标注其"非本报告依据"（本次 E2E-1b 已演示）。清理策略留待用户决策。
- E2E-1 的两窗口均带 extrapolation:true（最优可行域触设计边界）——按 W5 规则如实标记，工艺上提示"当前设计域可能不够宽"。
