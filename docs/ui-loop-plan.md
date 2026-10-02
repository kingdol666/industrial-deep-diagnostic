# UI Loop — 前端全功能测试与优化（持续）

- 循环模式：dynamic（每轮结束布一次性心跳，继续下一轮，直到全部功能无 bug）
- 目标：http://localhost:5180（后端 3210 / RAG 8764）
- 基线：后端单测 125/125 PASS（2026-09-20）

---

## Round 1 测试结果（2026-09-20）

### 已验证通过 ✅
| 功能域 | 覆盖点 | 结果 |
|---|---|---|
| Data | Preview 弹窗（开/内容/关）、勾选计数、双击进文件夹、面包屑返回 | PASS |
| Data→Diagnose | Analyze 跳转、文件挂载（Selection 芯片）、场景名自动填充 | PASS |
| Diagnose | 引擎下拉 14 引擎全枚举、Max turns/语言/本体策略/深度四个下拉、Start Diagnosis | PASS |
| Diagnose | Mock 全流程：3 阶段 SSE 流式、turns/tools 指标、ENDORSED·96、耗时与成本显示 | PASS |
| Diagnose | 追问输入→Send to session→mock 回包（+1 turn） | PASS |
| Reports | 列表渲染、状态/工件条件按钮、Read Report 正文渲染、View raw、Copy、Download | PASS |
| History | 175 条列表、Refresh、Delete（原生 confirm + DELETE 200 + 列表刷新） | PASS |
| Ontology/Chat | 页面加载、清单/版本/会话列表渲染 | PASS |
| 全局 | 语言切换（中/EN 往返）、Realtime Connected 状态、无 JS 错误/无 404/401 泄漏 | PASS |

### 本轮发现并已修复的 Bug 🔧（6 项）
1. **Load charts 静默无效**：`reportPath` 缺失时直接 `return`，无请求、无空态提示。→ 改为三级回退（reportPath→run_dir→空态文案）。
2. **图表接口 401**：DiagnosisView 与 ReportViewer 的 `chart-data` 用裸 fetch 不带 Bearer 头，认证部署下图表**永远加载失败**。→ 新增 `api.getChartData()`（带鉴权），两处调用改写；回归确认 200。
3. **Run Dir 事件裸 JSON 渲染**：`{"type":"system","subtype":"run_dir",...}` 直接显示给用户。→ MessageStream 增加 run_dir 分支，渲染为"运行目录：<basename>"（详情折叠完整路径）。
4. **Reports 列表伪日期**：`formatRunName` 把 13 位 epoch 目录名（1789839637950_smoke）误当紧凑时间戳解析成 "(1789-83-96 37:95)"。→ 增加 epoch-ms 分支（真日期）+ 紧凑时间戳合法值守卫。回归：显示 "smoke (2026-09-20 02:07)" ✓。
5. **删除运行后打开陈旧详情 → 僵尸页**：`openRun` 未捕获 hydrate 404，停留在 "Pending" 空壳页并抛未处理 ApiError。→ catch 后回任务列表 + 显示 "Run #id not found" 提示（en/zh）。
6. **（随 2 顺带）** ReportViewer/DiagnosisView 图表目录名解析统一支持正/反斜杠与 `diagnostic-runs` 段定位。

### 遗留（Round 2 待查/待修）
- [ ] 删除运行后，SPA 内存中的陈旧目录项点击（view-report 路径）仍有 2 个未处理 `ApiError: Run not found` 拒绝——需抓 `reason.stack` 定位确切来源（怀疑 ReportViewer 选中即发链路之外的一处；本轮所有 `.then` 链已确认有 catch）。
- [ ] History 行内 Session / Report / Deep enhance / Continue 四按钮的深度行为验证。
- [ ] Ontology 深操作：Validate (CP-2)、Version diff、Model health、Graph/Structure/JSON 切换、Adopt candidate。
- [ ] Chat：+New Chat、会话重命名（✎）、删除（✕）、active 会话发消息。
- [ ] Data：Upload File 完整链路（IAB 不支持 file chooser，需后端直传+前端刷新验证）、New Folder 内联表单正向流程。
- [ ] 引擎层错误路径 UI 呈现（400 HARNESS_UNKNOWN / 409 HARNESS_UNAVAILABLE 的可见反馈）。
- [ ] 产物构建警告：chunk >500kB（建议 manualChunks 分包 echarts/monaco 等重依赖）。
- [ ] onPastRunClick 对已删除 run（report_path 存在但文件已删）的 view-report 路径兜底。

### 优化 PLAN（按优先级）
- **P1 正确性**：Round 2 清掉上表遗留第 1 项（未处理拒绝）与第 8 项（view-report 兜底）；给 History 的 Deep enhance/Continue 增加进行中状态防重入（若实测缺失）。
- **P2 健壮性**：全局统一"运行目录名解析"工具函数（现 DiagnosisView/ReportViewer 两处各写一遍）；`fetchFails` 全局拦截器（开发模式 toast 化 4xx/5xx）。
- **P3 体验**：Load charts 对确无图表的运行默认自动加载（省一次点击）；Reports 列表 epoch 名统一走 formatRunName 后可按日期排序；History Delete 后 toast 确认。
- **P4 性能**：前端构建分包（echarts ~1MB chunk），首屏加载可观改善。
