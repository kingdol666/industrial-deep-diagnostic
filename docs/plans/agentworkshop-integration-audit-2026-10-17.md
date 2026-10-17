# IDD API × AgentWorkShop 插件：集成审计与端到端实测

- 日期：2026-10-17
- IDD：`D:/codes/myskills/idd-doe-impl`（`feat/doe-ontology-first` + 本轮修复）
- AgentWorkShop：v0.7.66（只读审计；其 80 条并行变更未被触碰）
- 关联：`doe-field-trial-2026-10-17.md`（DOE 能力实测）、`demo/doe-generality/GENERALITY.md`（12 行业泛化语料）

---

## 0. 结论（TL;DR）

| 问题 | 结论 |
|---|---|
| IDD 能否作为“数据分析引擎”被 API 调用？ | **能**。约 103 个路由处理器，统一 Bearer 鉴权，6 个分析意图全部走真实 agent；任务生命周期、结果、SSE、artifact manifest 均已实测 |
| 多场景是否真的都能分析？ | **能**。12 个行业 × 12 种设计/数据形态，12/12 case、132/132 断言全绿；支持全因子/部分因子/CCD/BBD/OA/LHS/观测/设计-only/多响应/单位冲突/约束 |
| AgentWorkShop 当前能否正常投入使用？ | **部分**。`diag-bridge` 的异步任务链可用；但 DOE 集成有 **P0 问题覆盖**、缺 run-level 输入/结构化结果；`idd-closedloop-bridge` 的 10 个工具全部指向**已退役端点**（实测 404）；项目级 `diag-bridge` 副本**导入即失败**（缺 `exports.mjs`） |
| 是否“能当数据分析引擎、针对多种场景发挥作用”？ | **IDD 引擎侧是**；**平台侧还不是**。需要修 3 个 P0（问题覆盖、closedloop 端点、项目副本缺文件）+ 2 个 P1（DOE 输入/结果回传）才算可投产 |
| 本轮是否发现并修复了真实缺陷？ | 是。2²+中心点设计识别、观测模式 manifest、`readDataFile` 泄露 JWT 密钥/DB、上传目录穿越等；后端 150/150 通过 |

---

## 1. IDD API 全量盘点

10 个路由模块，约 **103 个处理器**；除 `GET /api/health`、`POST /api/auth/register|login` 外，所有 `/api/*` 都要求 `Authorization: Bearer <session JWT | idd_ token>`。

| 模块 | 端点数 | 关键端点 | 用途 / 契约 |
|---|---:|---|---|
| `auth.routes` | 6 | `register/login/me/tokens` | 用户、JWT（HS256，24h）、`idd_` API Token（仅存 SHA-256）；首个用户 admin |
| `diagnosis.routes` | 16 | `start`、`tasks`、`tasks/:id`、`stream/:id`、`status`、`snapshot`、`stop`、`chat`、`continue`、`hitl`、`answer`、`enhance`、`session` | 真实 harness 运行；`analysisIntent` 六选一；strict harness 预检（unknown 400 / unavailable 409） |
| `external.routes` | 9 | `v1/capabilities`、`v1/analyze`、`v1/tasks/:id`、`v1/tasks/:id/result`、`v1/analyze/:runId/stream`、`v1/chat`、`v1/analyze/:runId/stop` | 稳定对外面；任务管理器（TASK-…）+ 统一结果（score/verdict/report_md/files/artifacts） |
| `files.routes` | 13 | `data/*`、`data/upload`、`workspace/report|html|asset` | 数据浏览/上传、运行产物与 HTML 资产；本轮修了 realpath containment |
| `harness.routes` | 10 | `harness`、`availability`、`:id/health`、`:id/runs*` | 14 引擎发现、可用性、只读运行浏览 |
| `omp.routes` | 7 | `omp/runs*` | OMP 原生运行/产物浏览（只读） |
| `ontology.routes` | 25 | `store/assets/graph/metrics/diff/publish/clone/adopt` | 本体资产库 CRUD 与图谱/指标 |
| `history.routes` | 3 | `runs`、`runs/:id` | 运行历史；`/runs/:id` 返回 `user_question`、`analysis_intent`（本轮用于取证） |
| `chat.routes` | 13 | 会话/流/目录 | 工作台对话 |
| `analysis.routes` | 1 | `chart-data/:runDirName` | 图表数据 |

### 契约要点

- **意图**：`deep-diagnosis` / `stability-report` / `quick-screen` / `doe-analysis` / `experience-mining` / `optimizer-campaign`；未知意图 400 `ANALYSIS_INTENT_UNKNOWN`，不会静默降级。
- **任务**：`POST /api/diagnosis/tasks` 接收 `dataPath` / `dataPaths` / `folderPath`、`sceneName`、`analysisIntent`、`harness`、`ontologyMode/Scene/Source/DataStage/DevOverride`；立即返回 `task_id`。
- **结果**：`GET /api/diagnosis/tasks/:id` 在 completed 时给 `summary/verdict/score/report_md_path/artifacts`；external 的 `result` 还带 `files`（md/html 绝对路径 + URL）。
- **artifact manifest**：15 种 DOE 工件（ontology/brief/coverage/feedback/consistency/profile/plan/effect/model/association/conclusion/recommendations/next_design/guidance/report），tasks 与 external 共用一份。
- **SSE**：`GET /api/diagnosis/stream/:runId` 与 external `…/stream`；事件为 status/message/tool_use/tool_result/result。
- **路径沙箱**：`validateDataPath` 用 realpath + relative containment，拒绝项目根外路径。

### 实测（真实后端 3211 + 真实 token）

| 检查 | 结果 |
|---|---|
| `GET /api/health` | 200 |
| 无 token 访问 `/api/diagnosis/list` | **401**（鉴权生效） |
| 未知意图 | **400 ANALYSIS_INTENT_UNKNOWN** |
| 未知 harness | **400 HARNESS_UNKNOWN** |
| 项目外路径 `D:/Windows` | 404 `DATA_NOT_FOUND`（拒绝，但错误码不是 403，建议修正语义） |
| `POST /api/diagnosis/tasks`（mock, DOE） | 200，task_id，completed，score=96 |
| `POST /api/external/v1/analyze`（mock, DOE） | 202 accepted → completed → result 含 report_md + files/artifacts |
| 6 意图 capabilities | 200，六意图与 skill 映射正确 |
| harness availability | 14 引擎全部 binary available；默认 omp |

---

## 2. 本轮安全修复（API 审计发现）

| 问题 | 影响 | 修复 |
|---|---|---|
| `readDataFile` 只用 `startsWith` 前缀判断 | 可读 `data/.auth-jwt-secret`（JWT 签名密钥）与 `data/diagnostic.db` | 改为 realpath containment + 拒绝任意 `.` 段 + 拒绝系统 DB 名；实测三类均 **403**，正常 workspace 文件 200 |
| `/api/files/data/upload` 的 `folder` 用 `startsWith` 判断 | 前缀相同的兄弟目录可穿越；`originalname` 未取 basename | `resolve + relative` containment；`basename(originalname)`；实测 `folder=../e2e-escape` → **400** |
| `/api/files/data/:folder` 用 `join + startsWith` | 同类前缀绕过 | 改用已有 realpath containment 的 `listDataFolder` |

回归：`app/backend npm test` **150/150**（新增 4 条文件安全用例）。

仍建议（未改，属于部署/架构取舍）：

- `app.use(cors())` 允许任意 Origin；生产应收紧到控制台域名。
- `AUTH_ENABLED=0` 是调试旁路；生产必须确保未设置。
- 登录/注册/ token 无速率限制；建议网关限流。
- external 任务表在内存（`Map`），后端重启后 TASK-id 丢失（run 本身仍在 DB）；建议持久化或文档声明。
- **一个 DB 只能跑一个后端**：本轮在 3211 运行时另起 3212 做安全测试，3212 初始化把 3211 的活动 run 标成 `interrupted`（`Server restarted — diagnosis interrupted`）。部署必须单实例或加 PID/DB 锁。
- harness `available` 只探二进制，不探模型凭据；真实调用仍可能因 key/额度失败。

---

## 3. AgentWorkShop 插件设计审计

### 3.1 设计范式（优点）

- **目录**：`index.mjs` 一行转发到 `host/`；`host/{plugin,diagnosis,sweep,snapshot,helpers,constants,intents}.mjs` 按职责拆；`client.mjs` 前端面板；`i18n.json` 双语。
- **插件对象**：`{name, version, auth, client, configGroups, settings, setup(ctx)}`；声明式设置 + `ctx.config.defineGroup/defineField` 运行时扩展，保存即热生效。
- **运行时能力**：`ctx.omp.registerTool` 暴露 Agent 工具、`ctx.kv` 状态、`ctx.timer.setInterval` 15s 轮询、`ctx.hooks.on('daq:sample')` 事件、`ctx.http`、`ctx.services.get('notify')` 回执、`ctx.route` 插件页路由。
- **安全**：`base_url` 仅允许 `127.0.0.1/localhost`；Bearer token；诊断 token 失效时给出可操作提示。
- **异步范式**：提交即返 task_id → KV 跟踪 → sweep 轮询 → 完成回执/`diag_status` 查询 → Agent 调 `kb_agent` 入库。

### 3.2 实测发现

| 发现 | 证据 | 级别 |
|---|---|---|
| `diag_run` 在缺省 `question` 时写死“深度根因诊断”，顶掉按意图的模板 | 用真实 builtin 插件 + 真实 IDD：`diag_run(data_path, analysis_intent=doe-analysis)` 创建 run `2bea2a03`，`/api/history/runs/2bea2a03` 的 `analysis_intent=doe-analysis`，但 `user_question="offline-data 产线该时窗数据深度根因诊断"` | **P0** |
| 项目级 `diag-bridge` 副本导入失败 | `.AgentWorkShop/plugins/diag-bridge/host/plugin.mjs` 引用 `./exports.mjs`，但该文件只存在于 builtin 副本；`import()` 报 `Cannot find module …exports.mjs` | **P0** |
| `idd-closedloop-bridge` 全部工具指向已退役端点 | 10 个工具注册成功；`sentinel_screen(data_path)` → `sentinel_screen 失败: 404`；常量指向 `/api/sentinel|experience|optimizer/*`，当前 IDD 路由已整体退役 | **P0** |
| DOE 输入没有 run-level 契约 | `diag_run` 只支持 line 快照 / 单文件 `data_path` / DAQ `export_id`（多文件时序）；没有 `folderPath`、`doe_context`、试验设计表、`ontologyScene` 参数 | **P1** |
| 结果只回文本 + report path | `diag_status` 不拉 artifact manifest / `recommendations.json` / `next_design`；external result 的 artifact `url` 仍为 null | **P1** |
| 平台无 DOE 实体/UI | 无 experiment/factor/response/run 表 | P1 |
| builtin 与 project 两份代码漂移 | project 缺 `exports.mjs`；builtin 完整可导入 | P0（同步或只保留一份） |

### 3.3 插件实测细节

- builtin `diag-bridge` 载入成功，工具：`diag_run`、`diag_status`；`diag_run` 异步提交 → `diag_status` 查到 `completed`、意图 DOE、评分 96（mock）、报告绝对路径。
- 项目 `diag-bridge` 载入失败（缺文件）。
- `idd-closedloop-bridge` 载入成功，工具 10 个（sentinel ×4、experience ×3、optimizer ×3）；`sentinel_screen` 404。
- 两个插件都正确读取 Bearer token；`baseOf` 限制 localhost；`ctx.kv` 状态/轮询逻辑可用。

---

## 4. 端到端实测

### 4.1 外部 API（mock，契约验证）

- `POST /api/external/v1/analyze` → `TASK-MVCFN5RP-306Z` / run `11995a0a` → `completed`。
- result：`score=96`、`verdict=ENDORSED`、`report_md`、`files.report_md_path`；DOE artifacts 为空（mock 引擎不产出真实工件），但 manifest 结构存在。
- `GET /api/external/v1/tasks/:id/result` 200。

### 4.2 内部 tasks API（mock）

- `POST /api/diagnosis/tasks`（DOE + mock + 单文件 run_table）→ `4fd15214` → `completed`，score 96。
- 说明：`dataPath` 单文件模式可用；但 DOE 的 specs/constraints/ontology scene 需要 `doe_context`/`folderPath`，当前 `diag_run` 不暴露。

### 4.3 真实 OMP harness（最终 run `e4fe8557` / `TASK-MVCG2AJ9-STNH`）

**结果：agent 真实执行了 ontology + analysis plan + DOE 分析，但 OMP 的父/子 agent 编排没有收尾；最终 report/gate 由确定性脚本在同一 run dir 完成。**

已由 agent 产出（run dir `workspace/diagnostic-runs/202610171341000_api-omp-doe-final`）：

- `01_ontology/{ontology,ontology_brief,ontology_coverage}`：场景 `heat-treat-furnace3-4140`，coverage 3/3 + 2/2；
- `01_profile/analysis_plan.md`；
- `02_analysis/{effect_table,model,association_screen,ontology_consistency}`；
- `conclusions/{doe_conclusion,recommendations,next_design,optimization_guidance}`：**grade A**、3 条边际窗、联合点 **859.384 °C / 44.787 min / 0.5008**、D=1.0、可行、硬约束 0；
- 与 12 行业语料中同一 case 的确定性结果**逐值一致**（联合点完全相同），说明 agent 没有改写数值。

编排观察：

- 父 agent 先完成 ontology/plan，然后 spawn 了 `DoeAnalysis` 子任务；子任务写出了全部分析工件，但父 agent 在 `Waiting for DOE analyst` 处停滞（此前还出现过一次 `Task DoeAnalysis failed preflight: Invalid caller output schema: boolean false schema rejects all outputs`）。在观察窗口内 run 一直 `running`，`report.html` 未生成。
- 处理：通过 external stop 停止该 run，然后在**同一 run dir** 上执行 `analyze.py report` + `quality_gate.mjs`：报告 148,665 B、gate **25/25**、artifact manifest **15 件 missing 0**。
- 因此：**IDD skill 协议与分析内核在真实 OMP agent 中可执行**；**OMP harness 的 task/subagent 收尾契约不稳定**，是平台接入的一个 P1 引擎侧问题。
- artifact 检索实测：`GET /api/files/workspace/asset/202610171341000_api-omp-doe-final/conclusions/recommendations.json` → 200 JSON；`/workspace/files/<run>` 列出全部工件；`/workspace/html/<run>` 在 report 生成后可见。

此前两次尝试暴露的两个输入契约问题：

1. `folderPath` 指向含 `00_input/` 的 run-dir 布局 → **`No data files found in folder`**（文件夹模式只扫顶层文件，不递归）。
2. 第一次把语料 `cases/<id>` 直接作为 folderPath，顶层含 `truth.json`，agent 读到验收真值 → 已立即停止；随后使用**去掉 truth.json** 的扁平输入目录。真值文件绝不能进诊断输入。

### 4.4 插件 → IDD（真实代码路径）

- builtin `diag-bridge` + 真实 IDD 3211：`diag_run` 提交成功，`diag_status` 轮询到 completed；**stored question 是深诊文案**（P0 证据）。
- `sentinel_screen` 404（P0 证据）。
- 项目 `diag-bridge` 导入失败（P0 证据）。

---

## 5. 多场景泛化（12 行业）

`docs/plans/demo/doe-generality/GENERALITY.md`：**12/12 case、132/132 断言**。

覆盖：注塑全因子（含类别因子/缺失单元）、热处理 CCD、化工 BBD（线性约束）、半导体部分因子、食品 L9 正交表、电池 LHS、涂布双响应冲突、塑料单位冲突/缺 platform_ref、机加工纯噪声响应、面板 10 响应 × 5 因子高通量、设计-only 拒统计、造纸 600 行观测模式。

级联修复：

- `design_detect` 的 2²+中心点：中心剥离重试门槛从 `max(6,2k)` 改为 `max(4,2k)`。
- 观测模式 artifact manifest 不再把 designed-only 的 `ontology_feedback/consistency` 标 missing。
- 饱和部分因子（16-run 2⁵ + 默认 2FI）需要中心/重复才能有误差自由度；报告会披露 `no pure-error replicates`。

---

## 6. HTML 报告解读（热处理 CCD，`evidence/heat_treat_ccd_report.html`）

报告的结构与读法（对照实际数字）：

1. **10 秒结论**：等级 **A**、`designed · 中心复合设计 (CCD)`；前三条发现：
   - `aust_temp` 对硬度 **+1.57** 编码系数（q=2.4e-8，partial η²=0.995）；
   - `hold_min` 对硬度 **+0.72**（q=2.1e-6）；
   - `aust_temp` 对畸变 **+0.0291**（q=4.9e-8）。
   右侧 3 个操作窗口、0 个确认试验、2 条观察清单；红框提示 Cook's D=0.820 > 4/n（单点影响大，删点可能改结论）。
2. **§1 数据概貌**：18 行 × 16 列；3 个因子各 3 水平（CCD 的角点/轴点/中心），`hardness_hrc`、`distortion_mm` 为响应；`quench_temp` 为协变量；无重复行、无高缺失列。
3. **§3 效应与 ANOVA**：硬度 R²=0.9976、Q²=0.984、失拟 p=0.765（pure-error df=3）；畸变 R²=0.9965、Q²=0.969、失拟 p=0.277。效应区间与 BH q 值都在表里。
4. **§4 模型与残差诊断**：Pareto、残差、Cook's D；报告明确“个别点影响过大”。
5. **§5 响应面与驻点**：硬度/畸变的二次面；**驻点被判为 saddle / 域外**（硬度驻点 raw 872.8 °C / 50.0 min / 0.807% C，碳含量超出 0.4–0.6 设计域）。报告没有把驻点当推荐点，而是给 `W3/W5` 警告。
6. **§6 操作窗口**：3 条边际窗（`window_role=marginal_diagnostic`），只作诊断。
7. **§10 局限与确认实验**：Cook's D 超限、驻点域外、适用域（观测范围 ±20% 失效）、失效条件。
8. **§11 本体依据与联合推荐点**：
   - 本体覆盖 3/3 因子、2/2 响应，未匹配 0；
   - **JS-001：aust_temp=859.4 °C；hold_min=44.79 min；carbon=0.5008**，D=1.0，可行/可执行，硬约束违例 0；
   - 预测硬度 **58.0**（均值 CI 57.86–58.14，PI95 57.67–58.33，d=1.0）；畸变 **0.0976**（PI95 0.0908–0.1045，d=1.0）；
   - **下一轮设计：space_filling，8 次**——因为驻点在域外/鞍点，系统建议用空间填充补点探索，而不是外推。
9. **附录 工件索引**：每个 JSON 的 sha256（篡改检测锚点）+ plot manifest ink 检查。

**怎么读**：先看 10 秒结论的等级/三条发现/窗口数；再用 §3 的 q 值与 R²/Q² 判断“效应可信度”；用 §5/§10 判断“能不能外推”（这里不能，驻点鞍点/域外）；最后只看 §11 的 `joint_setpoints` 执行，逐因子窗口不能单独执行。这个案例没有 `platform_ref`，所以 §11 没有 recipe patch——这是“能分析但不能自动落参”的明确边界，补上 platform_ref 才有平台动作。

---

## 7. 投产判定

### IDD 作为数据分析引擎

**可以投产（本地/受控网络），但需遵守约束**：

- API 面完整，鉴权/路径沙箱/任务生命周期/结果/manifest/SSE 均实测；
- 六意图 + 12 行业泛化通过；确定性内核 + 门禁；
- 注意：单 DB 单后端；CORS/限流/任务持久化按部署补；外部 artifact URL 需要 API 层补全。

### AgentWorkShop 作为调用方

**当前不能算“正常投入使用”**：

1. P0：`diag_run` 的问题覆盖——DOE/其他意图的业务问题文本错误（实测）。
2. P0：项目级 diag-bridge 副本缺 `exports.mjs`，导入失败。
3. P0：closedloop bridge 10 个工具全部 404（端点已退役）。
4. P1：DOE 没有 run-level 输入（folderPath/doe_context/设计表）与结构化结果回传（recommendations/next_design/artifact manifest）。
5. P1：无 DOE 实体/UI/台账。

修完 1–3 可恢复“六意图异步分析”的基本可用；修完 4–5 才能把 IDD 真正当平台的 DOE 数据引擎。

---

## 8. 证据与复现

- 泛化语料：`docs/plans/demo/doe-generality/`（`generate_cases.py`、`run_cases.py`、`GENERALITY.md`、`evidence/`）。
- API/插件探针：`docs/plans/demo/integration/plugin_probe.mjs`、`plugin_probe.json`；`workspace/aws-capture-e2e/{api_contract.json,api_mock_result.json,omp_task_final.json}`。
- 安全回归：`app/backend npm test` 150/150。
- 真实 OMP 任务：`e4fe8557` / `TASK-MVCG2AJ9-STNH`（结果见 §4.3 更新）。

> 注：本轮曾因在同一个 SQLite DB 上另起 3212 后端做安全测试，触发“Server restarted — diagnosis interrupted”，使一次 OMP 运行被污染并停止；最终 run 使用单后端 3211 重新发起。该行为本身已作为部署约束记录在 §2。
