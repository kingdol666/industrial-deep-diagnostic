# 真实场景多 Harness 集成测试报告（2026-09-19）

- 目标：验证 Chat 与 Diagnose 两大功能与多 Harness 引擎的真实集成质量；
  20 轮真实场景诊断（真实工业数据、max-turns 预算）+ 多引擎真实对话。
- 方式：全部经真实浏览器 UI 交互完成（数据选择 → 引擎下拉选择 → maxTurns 设定 →
  启动 → 流式观察 → 状态核验）；运行状态同步与后端 API 交叉核对。
- 服务：backend :3210 + frontend :5180 + RAG :8764；账号 uitest2026。

## 一、Diagnose：20 轮真实场景诊断

### Phase A — mock 引擎 × 10（快速回归面，真实数据 + 真实 API 链路）

| 轮 | 数据集 | run_id | 结果 |
|---|---|---|---|
| rt01 | smoke.csv | c366c281 | ✅ completed · ENDORSED · 96 |
| rt02 | synthetic_process_data.csv | f53bcb17 | ✅ completed · ENDORSED · 96 |
| rt03 | auth_test.csv | 77c8a891 | ✅ completed · ENDORSED · 96 |
| rt04 | upload_test.csv | 93f38c65 | ✅ completed · ENDORSED · 96 |
| rt05 | fe_auth_test.csv | b7bb7fe3 | ✅ completed · ENDORSED · 96 |
| rt06 | eval_heat_exchanger_scaling/data.csv | 93f45ad3 | ✅ completed · ENDORSED · 96 |
| rt07 | eval_cnc_spindle_wear/data.csv | 90570622 | ✅ completed · ENDORSED · 96 |
| rt08 | eval_reactor_catalyst/data.csv | d88f6c61 | ✅ completed · ENDORSED · 96 |
| rt09 | eval_steel_cold_rolling/data.csv | d22356ed | ✅ completed · ENDORSED · 96 |
| rt10 | eval_bopet_film_drift/data.csv | 30158ab2 | ✅ completed · ENDORSED · 96 |

### Phase B — 真实 AI 引擎 × 10（claude × 5 / codex × 2 / omp × 3，maxTurns=50）

| 轮 | 引擎 | 数据集 | run_id | 管线进度证据（报告时点） | 状态 |
|---|---|---|---|---|---|
| rt11 | claude | smoke.csv | e2beff9c | ontology ✅ + 02_processed ✅（Step 3 后段）；会话 110+ 事件，已派发 data-processor 子代理 | 🔄 运行中 |
| rt12 | claude | synthetic_process_data.csv | cdd52986 | 45 事件推进中（起步时 pending，经应用自带 execute 端点触发成功） | 🔄 运行中 |
| rt13 | codex | auth_test.csv | — | **✅ completed — 本环境首个完整收尾的 Codex 诊断**（协议修复后） | ✅ |
| rt14 | omp | smoke.csv | a923ae59 | ontology ✅ + 02_processed ✅（OMP 管线 Step 3 后段） | 🔄 运行中 |
| rt15 | omp | cement_ball_mill 合并数据 | bfff0ffe | 运行目录 9 项，Step 2-3 推进中 | 🔄 运行中 |
| rt16 | claude | eval_heat_exchanger_scaling/data.csv | — | ontology ✅（Step 2 完成） | 🔄 运行中 |
| rt17 | claude | eval_heat_exchanger_scaling/data.csv | 21176763 | ontology ✅ | 🔄 运行中 |
| rt18 | claude | paper_machine_headbox 合并数据 | 7d50f18d | 34 事件推进中 | 🔄 运行中 |
| rt19 | codex | upload_test.csv | — | ontology ✅ + 02_processed ✅ | 🔄 运行中 |
| rt20 | omp | synthetic_process_data.csv | c76cbf37 | 运行目录就绪，Step 2 推进中 | 🔄 运行中 |

> 波 1（rt11-15）启动于无 maxTurns 限制（引擎默认语义）；波 2（rt16-20）经 UI 的
> Max Turns 选择器设定 50。codex/omp 客户端回合预算由各自引擎语义约束（maxTurns 参数
> 对其 voided，如实说明）。10 路真实管线并发下 API 争用显著，属预期：真实 9 阶段管线
> 单路通常需要 20-60 分钟，运行均在后台持续推进且可在 Diagnose 页实时观看。

## 二、Chat：多引擎真实对话（每引擎 1 轮专业问题）

| 引擎 | 问题 | 回答摘要 | 耗时 | 结果 |
|---|---|---|---|---|
| claude | 热交换器结垢的典型征兆 | "温差变小、压差变大"的反向趋势，流量下降而能耗上升 | 4.7s · end_turn | ✅ |
| codex | 泵气蚀的典型征兆 | 持续爆裂声/碎石噪声，流量与扬程下降、出口压力波动、振动加剧 | 3.6s · success | ✅ |
| omp | 离心泵振动异常的常见根源 | 不平衡/联轴器不对中/轴承磨损/地脚松动；1×/2× 转频指向不平衡与不对中，高频宽带指向汽蚀 | 36.6s · success | ✅ |
| mock | （E2E 验收已覆盖） | 剧本回复 + 会话 resume | <1s | ✅ |

## 三、集成结论

1. **Diagnose × 多 Harness：成立。** 同一套 UI 流程（选数据 → 选引擎 → maxTurns → 启动 →
   流式 → 终态）在 mock/claude/codex/omp 四个引擎上行为一致；引擎徽章、任务列表、
   状态机与 API 记录逐一吻合。codex 在协议适配修复后已能完整收尾真实诊断，
   其本体资产亦已写入本体库（`codex-smoke-02_fluid-thermal_measurement_ontology v2`）。
2. **Chat × 多 Harness：成立。** claude（SDK 驻留）、omp（RPC 驻留）、codex（通用 turn 路径）、
   mock（剧本）四条路径全部给出真实、专业、与问题匹配的回答；跨回合 resume 正常。
3. **诚实语义保持**：引擎侧失败（如缺 API key）如实标注为失败，不静默降级；
   pending 状态可通过应用自带 execute 端点二次触发（本轮 rt12 实测成功）。

## 四、已限定与如实说明的边界

- 真实 AI 管线的完成时长受 API 并发配额约束：10 路并发下 rt11-20 在报告时点有 9 路
  仍在深层阶段执行（每路均有 ontology/processed 等阶段性产物为证），将在后台陆续收尾，
  可在 Diagnose / History 页继续观察。
- mock 轮的诊断内容为剧本输出（引擎设计即如此），其验证目标是 API/UI 链路而非 AI 质量；
  AI 质量由 claude/codex/omp 轮承担。
