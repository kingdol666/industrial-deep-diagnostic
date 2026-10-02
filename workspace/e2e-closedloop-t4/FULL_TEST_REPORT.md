# 全功能真实完整测试报告（2026-10-01）

> 分支 `v4-AgentWorkShopIntegrate` @ 6e16c92 · 全部测试为本机真实执行（无 mock 桩，除注明）。

## 总览

| # | 测试域 | 结果 |
|---|--------|------|
| T1 | 闭环三件套 + doe-analyzer 脚本测试电池 | ✅ 55/55 + 159/159 + 55/55 + 124/124 |
| T1b | data-preprocessor / deep-analysis 单元测试 | ✅ ALL TESTS PASSED ×2 |
| T2 | 13 个新 schema + enums/contracts 元验证 + 实例双验 | ✅ 15/15 合法，实例全过 |
| T3 | 后端 npm test | ✅ 160/160（含 closedloop-routes + idd-closedloop-bridge.integration） |
| T3b | 前端 vite build | ✅ built in 3.9s |
| T3c | regression-gate.mjs | ✅ PASS (all gates hold their teeth) |
| T3d | 镜像漂移守卫 | ⚠️→✅ 发现 24 skill 漂移 → 已同步修复，复检 OK |
| T4 | **闭环全链 E2E（文件轨）** | ✅ **42/42 ALL GREEN (24.7s)** |
| T4b | **闭环全链 E2E（API 轨 live）** | ✅ **11/11 ALL GREEN** |
| T5 | 文档同步（AGENTS.md / .omp/AGENTS.md） | ✅ 19→22 skills、15→16 agents 修正 |
| T6 | 完整 9 阶段诊断流水线（claude 真实引擎） | ✅ 管线全流程走通（含修复循环）；⚠️ 执行证明门禁抓到引擎竞态缺口（见 T6 节） |
| T7 | RAG 引擎 | ✅ healthy, kb_ready 111 chunks (port 8764) |
| T8 | AWS 桥插件部署核验 | ✅ 10×registerTool 于 host/plugin.mjs（HTTP 侧契约由 T4b 证明） |

## T4 文件轨闭环 E2E（42/42）

驱动脚本：`workspace/e2e-closedloop-t4/run_e2e.py`（seed 20261001，零 LLM）
植物真值：`yield(temp, press) = 100 − 0.25·(temp−84)² − 60·(press−0.60)²`

| 阶段 | 关键结果 |
|------|----------|
| S1 doe-analyzer 真实运行 | designed 模式识别物理单位 2³ 析因；gate 21/21；recommendations v1.0 |
| S2 sentinel 基线 | build_baseline 逐值搬运 doe 产物（operating_windows/合同版本进 generated_from） |
| S3 sentinel watch | 注入漂移（row 3000 起 +0.0006/行）→ exit 1，10 条 temp 告警全部落漂移后区间；gate 6/6 |
| S4 fault_signature | 从 alert 派生（temp/high），schema 双验通过 |
| S5 归因 | 两个动作均 estimable：Δ=−3.55（错误方向加温）/ +3.99（纠正降温），与真值 −3.75/+4.0 吻合 |
| S6 经验入库 | tuning_action_effect ×2 + fault_control_recipe ×1；隐私别名 eng_03 |
| S7 playbook 检索 | playbook_hit，score=1.0（阈值 0.55），autonomy_level=null（AWS 侧策略载体保持空），ack 回执链 |
| S8 optimizer campaign | init O-G1 → design/ingest 轮次推进 → **R002 收敛**（target 语义：99.11 ∈ [98.0,100.2]，verified） |
| S9 recipe | 6 产物齐 + optimizer gate 16/16 |
| S10 feedback 闭环 | effective → corroboration_count=2，**E1→E2 晋升**；重跑 recommend 刷新后 T7 一致性门禁通过；gate 8/8 |

额外验证的门禁牙齿：T7 抓住 feedback 后未刷新的陈旧 recommendation.json（协议"重跑脚本步骤"路径修复）。

## T4b API 轨 live E2E（11/11）

对运行中的后端（3210）真实 HTTP 调用，脚本 `api_live_test.mjs`：

- A0 认证（register/login → Bearer）
- A1 `POST /api/sentinel/baseline`（异步任务 SNB→completed）
- A2 `POST /api/sentinel/tasks` watch（异步任务 SNW→completed）
- A3 `POST /api/experience/actions` → 归因 job completed → `POST /api/experience/recommend` **playbook_hit**
- A4 `POST /api/optimizer/campaign` → design/ingest 轮 → **3 轮收敛**（与 plan T4"3 轮→converged"一致）
- A5 `GET /api/optimizer/state` 回读 converged

补充实测：`POST /api/sentinel/screen`（fast-screen）对 10000 行输入诚实拒绝（exit 2, 限 1-500）；
300 行漂移切片 → exit 1 + 5 条告警（robust z=11.4）。`GET /api/experience/library`、`GET /api/optimizer/campaigns` 正常。

## T6 完整 9 阶段诊断流水线（claude 真实引擎）

**运行**：`d09e3a4f`（scene `e2e_full_pipeline_heat_exchanger`，数据 `data/eval_heat_exchanger_scaling/data.csv`，45 天/2160 点壳管式换热器）
**运行目录**：`workspace/diagnostic-runs/202610010000000_e2e_full_pipeline_heat_exchanger`（junction，实体 `D:\codes\idd-run-archive\...`）

### 管线本体：真实完整走通 ✅

- Step 0/1 → Step 2（本体复用 fastpath：`ontology_hit=reused`，`shell_and_tube_heat_exchanger_scaling/v1`）→ 澄清门 **AUTO_RESOLVED**（带诚实注记："出口温度偏低是前提不是事实，须双通道检验"）
- Step 3 data-processor：6 分析 JSON + 6 SVG（U 双窗精确均值 809.16→943.96、压降窗 +0.03 无恢复、premise 对账）
- Step 4 diagnostician → **Step 5a/5b 并行**（judge + 预审）→ **真实修复循环触发**：judge R1 <90 → `repair_spawn diagnostician`（持久计数器登记）→ R2 **93/100 PASS**
- Step 6 reporter（金字塔中文报告）→ Step 7 终审 **独立复算**（optimizer.md，对照 04_diagnostics/02_processed 重新计算关键数值）
- Step 8 HTML 可视化（diagnostic-report.html，18 处 ECharts/SVG 引用）+ 自检 → Step 9 finalize（evidence_closure_report.json：`PASS`，COMPETING_SET，overall_confidence 68）
- `.pipeline_events.jsonl` 29 事件，含 `run_completed`；`repair_spawn_count=1`（≤3 上限内）

**诊断内容质量**（人工抽查）：诚实 COMPETING_SET——热路退化已确证（U 块中位 1022→883，−21%，串联热阻机制）+ 压降 +180~274% 与热路解耦、A1-A4 四机制无法唯一判别；2026-08-28 02:00 离线除垢干预使热路四指标同步阶跃恢复而压降纹丝不动（判别性证据）；再结垢 18 天回吐 1/3 收益。

### 执行证明门禁与引擎层发现 ⚠️

`pipeline-log-check.mjs` → **FAIL**（门禁有牙齿，抓到真实缺口）：

| 级别 | 发现 | 根因 |
|------|------|------|
| **P1 引擎竞态** | 引擎在 16:27:49 消费一个 end_turn 时 report.md 尚未落盘（16:32:04 才写），防假成功守卫按当时状态判 failed；但 claude.exe 未终止、继续完成 Step 7/8/9 全部产物并记 `run_completed`。DB 记录与磁盘真相背离；编排事件日志出现缺口（reporter 无 agent_start 等） | claude 引擎多 turn 流中把中间 result 当终结；守卫本身工作正常（没有假成功） |
| P2 分数解析 | 引擎 score 正则 `Judge Score: N/100` 与 reporter 实际输出 `**诊断评级**: 93/100 — pass` 不匹配（成功路径 score 也会解析为 null） | 模板/解析器格式漂移 |
| P2 agent JSON | `html_selfcheck.json` evidence 字段含未转义内引号 → 非法 JSON；finalize 前无解析校验兜底 | agent 写盘未过 validate |
| P3 resume 语义 | `POST /continue` 对已完成 run 的 follow-up 触发**整条管线重跑**（即使明示"勿重跑"）——resume 协议缺"产物已齐→只核对"短路路径 | 协议设计项 |

**结论**：管线全功能（9 阶段 + 修复循环 + 并行审 + 本体复用 + 澄清门 + HTML）在真实引擎上**已实现且内容质量达标**；执行证明门禁按设计拦截了竞态造成的日志缺口——**该 run 不应引用为"干净认证通过"**，引擎竞态修复后应复跑一轮拿干净记录。

## 环境事件记录

- 起测时 3210 上的旧后端进程（3.5h 前启动）不含闭环路由 → 重启后 404 消除。
- RAG 引擎（8764）起测时未运行 → 已启动（healthy, 111 chunks）。

## 修复项（本次测试中发现并处理）

1. **镜像漂移**：`.claude/skills` 改动后 24 个 skill 未同步至 `.agents/`、`.hermes/` 镜像 → 执行 sync 后复检一致。
2. **文档漂移**：AGENTS.md 仍写 19 skills × 15 agents（实际 22 × 16）→ 已更新（含闭环三件套触发词与 optimizer-pilot 角色行）、`.omp/AGENTS.md` 同步。

## 待流水线完成后补：T6 结果
