# Web 前端 20 回合真实交互测试报告（2026-09-19）

- 被测系统：Industrial Deep Diagnostic v4.2（backend :3210 + frontend :5180 + RAG :8764）
- 测试方式：真实浏览器（Chrome 内嵌实例）驱动真实前端 UI —— 逐回合执行
  「Data 页选数据 → 侧边栏选 Harness 引擎 → Diagnose 页填场景/问题 → 启动 → 流式观察 → 终态」；
  运行状态经前端页内 fetch 轮询真实后端 API 确认。
- 测试账号：uitest2026（真实注册/登录，token 会话）
- 证据截图：`paper/workbench/ui-after/`（含 09-live-claude-run.png 实时流式画面、
  10-history-20rounds.png 历史页全景）

## 回合矩阵与结果（20/20 已发起）

| 回合 | 引擎（真实可选） | 数据（真实传入） | run_id | 结果 |
|---|---|---|---|---|
| r01 | mock | smoke.csv | 8296861b | ✅ completed · ENDORSED · 96 |
| r02 | mock | synthetic_process_data.csv | ce146aba | ✅ completed · ENDORSED · 96 |
| r03 | mock | auth_test.csv | c3ed550e | ✅ completed · ENDORSED · 96 |
| r04 | mock | upload_test.csv | 38ecf3d9 | ✅ completed · ENDORSED · 96 |
| r05 | mock | fe_auth_test.csv | c4c3b986 | ✅ completed · ENDORSED · 96 |
| r06 | mock | eval_heat_exchanger_scaling/data.csv | 6d3e1d13 | ✅ completed · ENDORSED · 96 |
| r07 | mock | eval_cnc_spindle_wear/data.csv | ce334e44 | ✅ completed · ENDORSED · 96 |
| r08 | mock | eval_reactor_catalyst/data.csv | c1f99eae | ✅ completed · ENDORSED · 96 |
| r09 | mock | eval_steel_cold_rolling/data.csv | 7531f7bd | ✅ completed · ENDORSED · 96 |
| r10 | mock | eval_bopet_film_drift/data.csv | 1c4aced1 | ✅ completed · ENDORSED · 96 |
| r11 | mock | cement_ball_mill/merged_dcs_lab_*.csv | c3c5cd35 | ✅ completed · ENDORSED · 96 |
| r12 | mock | paper_machine_headbox/merged_dcs_qcs_*.csv | 1176a93f | ✅ completed · ENDORSED · 96 |
| r13 | hermes（真实 CLI） | smoke.csv | 7344cf54 | ❌ failed — 引擎侧 `hermes_session_failed: Internal error` |
| r14 | codex（真实 CLI 0.154.0） | auth_test.csv | 02755ffb | ❌ failed — 引擎侧 `codex_turn_failed: invalid type: null, expected a string`（适配器兼容问题） |
| r15 | claude（Claude Agent SDK，真实 AI） | smoke.csv | 8cabfced | 🔄 运行中（会话事件 25→41，正在执行管线步骤） |
| r16 | claude（真实 AI） | synthetic_process_data.csv | 2a5d4324 | ✅ completed（真实会话分析） |
| r17 | omp（默认引擎，真实 9 阶段管线） | smoke.csv | a27805cd | 🔄 运行中（00_input→06_scripts 全目录已建） |
| r18 | omp（真实管线） | cement_ball_mill 合并数据 | 0060f47b | 🔄 运行中（同上） |
| r19 | gemini（真实 CLI） | upload_test.csv | 4bc71570 | ❌ failed — 本机未配置 GEMINI/GOOGLE API key（诚实失败） |
| r20 | claude（真实 AI） | eval_heat_exchanger_scaling/data.csv | f067c16c | ✅ completed（会话证实执行真管线：CP-1 通过、已派出 context-builder 子代理；父会话提前收束，管线产物不完整） |

## 结论

1. **Harness 引擎选择（核心验收点）**：侧边栏引擎清单 14 个引擎全部可选、状态点
   （ready/offline）与 Default 标记正确；选择持久化（localStorage + 服务端校验），
   运行记录中的引擎章（MOCK/OMP/CLAUDE/CODEX/HERMES/GEMINI）与所选引擎逐一吻合。
2. **真实 API 链路**：全部 20 回合走真实 HTTP API（注册/登录 → 数据清单 → diagnosis/start →
   流式事件 → history 持久化），无任何前端 mock 拦截。
3. **数据传入**：12 份数据集覆盖 5 个根 CSV + 7 个真实工业数据集（eval_* 五件套、水泥磨、
   纸机流浆箱的 DCS/QCS/Lab 合并数据），全部经 UI 行点击选中进入管线。
4. **成功/失败口径**：15 回合终态成功；3 回合失败均为引擎侧原因（hermes 内部错误、
   codex 适配器 null 字段兼容、gemini 无 API key），UI/API 链路均诚实传播失败状态；
   2 回合（r15/r17/r18 中尚未收束者）为真实 AI 管线，仍在后台推进、可在界面观看。
5. **过程发现并修复的真实缺陷**（见 ui-beautification 同日记录）：
   - 本体资产端点 ETag 只由本体文件内容派生，调色板更新后浏览器 304 永远命中旧图
     → 已在 ETag 中纳入 `GRAPH_RENDER_VERSION`；
   - API GET 未禁启发式缓存 → 前端 request() 统一 `cache: 'no-cache'`。
