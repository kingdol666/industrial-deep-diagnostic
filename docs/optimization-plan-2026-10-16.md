# IDD 系统全面审计与优化方案

- 日期：2026-10-16
- 审计范围：`.claude/skills/`（23 个 skill）、`app/backend`、`app/frontend`、`.claude/shared/scripts`、部署配置（Dockerfile / docker-compose / nginx / config）、测试体系、文档一致性
- 审计方法：三路并行深度扫描 + **关键结论逐条人工复核**（本文所有 P0 条目均已亲自验证，附文件:行号证据）
- 结论先行：**方法论层（诊断管线、确定性脚本、门禁纪律）是优秀且不需要动的；风险集中在"应用层外壳"——它还没有配得上内核的工程强度。**

---

## 一、问题总览

| 层 | P0（事故级） | P1（可靠性） | P2（一致性） | 合计 |
|---|:---:|:---:|:---:|:---:|
| Skills 层（23 个） | 0 | 3 | 8 | 11 |
| 后端 | 6 | 4 | 2 | 12 |
| 前端 | 1 | 2 | 2 | 5 |
| 部署/配置 | 2 | 3 | 3 | 8 |
| 测试/CI | 1 | 2 | 2 | 5 |
| 文档 | 0 | 0 | 6 | 6 |
| **合计** | **10** | **14** | **23** | **47** |

---

## 二、P0 —— 生产事故级问题（全部已人工复核）

### P0-1 nginx 静态别名绕过全部鉴权（数据裸奔）
- **证据**：`nginx.conf:21-27` — `location /data-files/ { alias /app/data/; }` 与 `location /workspace-files/ { alias /app/workspace/; }`，无任何鉴权指令。
- **后果**：API 层辛苦做的 JWT/API Token 鉴权（`docs/api.md:9`）被 nginx 完全架空。任何能访问 80 端口的人可直接下载**全部原始数据、全部诊断报告、SQLite 数据库文件**（`data/diagnostic.db` 就在 alias 目录下）。
- **修复**：删除这两个 location，改为经 `/api/files/*` 的鉴权代理返回；或用 `auth_request` 转发到后端校验 token。
- **验收**：`curl http://host/data-files/diagnostic.db` 返回 401/404，而不是文件内容。

### P0-2 路径穿越：数据目录前缀检查可绕过
- **证据**：`app/backend/src/routes/files.routes.mjs:49,93` — `folderPath.startsWith(DATA_DIR)`。原始字符串前缀匹配，`data-evil/` 这类同级目录可通过；上传文件名未净化直接 join（`files.routes.mjs:108`）；`omp.service.mjs:192,209,245` 将未净化的 `:run` URL 参数 join 进 `RUNS_DIR`。
- **后果**：认证用户可读写数据目录之外的宿主机文件；上传可写任意路径。
- **修复**：统一封装 `resolveInside(baseDir, userInput)`：`path.resolve` 后用 `path.relative` 判断，`rel.startsWith('..') || path.isAbsolute(rel)` 即拒绝；上传文件名过 `sanitize()`（复用 `claude-client.mjs:138` 已有的净化器）。
- **验收**：单测覆盖 `../`、`data-evil`、绝对路径、URL 编码四个绕过向量，全部拒绝。

### P0-3 挂起的引擎进程永不超时（进程泄漏）
- **证据**：`app/backend/src/engine/claude-client.mjs:329` — `const timeout = timeoutMinutes || config.claude.timeout_minutes;` 计算后**全文再无引用**（grep 仅 2 处：参数解构 + 此赋值）；`acp-client.mjs:309`、`codex-client.mjs:240`、`opencode-client.mjs:373` 显式 `void timeoutMinutes`。仅 `one-shot.mjs:204-212` 真正实现超时。
- **后果**：Claude/ACP/Codex/OpenCode 引擎一旦卡死（LLM 供应商挂起已有实测记录），子进程永久存活，run 永远停在 running。
- **修复**：把 `one-shot.mjs` 的超时-kill 机制提取为 `withTimeout(child, minutes, onTimeout)` 公共层，四处引擎统一接入；超时后 run 置 `failed: timeout` 并清理子进程树。
- **验收**：mock 一个永不返回的假 CLI，在 `timeout_minutes` 后被 kill，run 进入 failed 终态。

### P0-4 无全局错误处理与优雅关闭（进程崩溃 + 孤儿任务）
- **证据**：`app/backend/src/index.mjs` — 无 `uncaughtException`/`unhandledRejection` 处理器、无全局错误中间件 `app.use((err,req,res,next))`；`grep -r SIGTERM app/backend/src/` = **0 处**。`docker-compose.yml:23` 配置了 `restart: unless-stopped`。
- **后果**：Express 4 不会捕获 async 路由的 rejected promise，一次未处理异常可杀进程；每次重启/滚动发布都会**遗弃正在跑的 agent 子进程**，run 卡死在 running，且无清理路径。
- **修复**：① 全局错误中间件 + 两个 process 级守卫（记日志、按环境决定退出）；② SIGTERM/SIGINT → 停止接新任务 → 通知存活子进程树 → flush 事件与 WAL checkpoint → 退出；③ run 启动时先把"上次非终态"的 run 标记为 `interrupted`（已有该终态枚举）。
- **验收**：`docker restart` 后无孤儿子进程，中断的 run 有明确终态与可续跑入口。

### P0-5 无全局并发上限（资源耗尽 / DoS）
- **证据**：`app/backend/src/services/diagnosis.service.mjs:132` — `executingRuns` 是 Set，仅做同 run 去重（:775-779）；无任何总量上限。`external.service.mjs:111` 的 `tasks` Map 从不淘汰。
- **后果**：`POST /api/diagnosis/start`/`/tasks` 可无限制拉起 agent 子进程；每次跑 35–115 分钟，几发请求即可打满 CPU/内存。`tasks` Map 无限增长是慢性内存泄漏。
- **修复**：`MAX_CONCURRENT_RUNS`（env，默认 2）+ 超出进入 `queued`（状态枚举已存在）；`tasks` Map 加 LRU/时间淘汰；`activeQueries`、`questionSessions`、`hitlRequests` 在 run 终态时统一清理。
- **验收**：连发 5 个启动请求，2 个执行、3 个 queued；终态后内存中的会话 Map 归零。

### P0-6 RBAC 有定义无执行 + 数据库无归属列（数据互相可见）
- **证据**：`app/backend/src/middleware/auth.middleware.mjs:41` — `requireRole()` 定义后**全仓库零调用**；`db/database.mjs` 中 `diagnostic_runs(:23)`、`chat_sessions(:81)`、`data_folders(:72)`、`diagnosis_logs(:45)` 均无 `user_id`/`tenant_id` 列。任意认证用户可删除任意本体场景（`ontology.routes.mjs:232-238`）、任意 run。
- **后果**：多部门/多客户共用时数据全裸；`docs/api.md` 暗示的权限分级并不存在。这是对外交付的硬门槛。
- **修复**：见阶段 1（需要迁移 + 路由过滤 + RBAC 接入三步，单列方案）。
- **验收**：用户 A 创建的 run，用户 B 的 list/查询/下载均不可见；非 admin 无法删除他人资源。

### P0-7 `.env` 未被 gitignore（密钥可入库）
- **证据**：`git check-ignore .env` 返回未忽略（已实测）。`.env.example` 存在但真实 `.env` 无防护，且其中可含 `ANTHROPIC_API_KEY` / `DEEPSEEK_API_KEY`。
- **修复**：立即加入 `.gitignore`；`git log` 排查历史中是否已提交过，若有可能泄露则轮换密钥；仓库加 pre-commit 钩子或 CI 密钥扫描。
- **验收**：`git status` 不再显示 `.env`；CI 有 secret 扫描步骤。

### P0-8 无 TLS、无安全头、上传被 nginx 静默拦截
- **证据**：`nginx.conf:7` 仅 `listen 80`，无 HSTS/CSP/X-Frame-Options；无 `client_max_body_size`（nginx 默认 **1MB**，而应用允许 500MB 上传）→ 上传全部 413；`/api/`（:29-38）无 `proxy_read_timeout`（默认 60s）→ 长思考阶段的 SSE 流可能被掐断。
- **修复**：`client_max_body_size 600m`；`/api/` 加 `proxy_read_timeout 3600s`；补安全头；提供 TLS server 块模板（`webfrp` 已有 Cloudflare Tunnel 方案可兼容）。
- **验收**：500MB 文件可上传成功；SSE 流 10 分钟无数据不断开。

### P0-9 CORS 全开 + WebSocket 裸奔
- **证据**：`index.mjs:53` — `app.use(cors())` 允许任意源；`ws-server.mjs:444` 的 `WebSocketServer` 未设 `maxPayload`（ws 默认 100MB 帧）；`safeSend`（:31-34）不检查 `bufferedAmount`（无背压）；token 走 query string（`ws-server.mjs:462`）会泄漏进日志/代理。
- **修复**：CORS 改 allowlist（env 配置）；WS 设 `maxPayload: 1MB`、`safeSend` 检查缓冲并丢弃低优先级帧；token 改子协议或首帧鉴权。
- **验收**：跨域请求被拒；1MB 以上 WS 帧被关闭连接。

### P0-10 后端测试在当前环境是红的（CI 信号失真）
- **证据**：实测 `cd app/backend && npm test` → **44 tests / 40 pass / 1 fail / 3 cancelled**。`files.service.test.mjs`、`mock-e2e.test.mjs`、`ontology-api.e2e.test.mjs`、`ontology-control.test.mjs` 因 `better-sqlite3` ABI 与 Node 22 不匹配（`ERR_DLOPEN_FAILED`）加载失败。
- **后果**：README 的 "116 passed" 与现实脱节（见 P2 文档漂移），团队对"测试绿"失去信任基线。
- **修复**：按 managed Node 版本 rebuild `better-sqlite3`（或锁定 Node 版本 + `npm rebuild`），恢复全绿后再谈 CI。
- **验收**：`npm test` 全绿且数字可复现，README 数字由脚本生成而非手写。

---

## 三、P1 —— 可靠性与工程质量

### Skills 层（S1–S3）

**S1. 门禁覆盖严重不均：13/23 个 skill 无确定性门禁**
- 有正式 `quality_gate.mjs` 的仅 5 个（doe-analyzer、line-stability-report、optimizer-loop、sentinel、tuning-memory）+ judge 的专用 check。
- **无任何门禁的 13 个**：darwin-skill、diagnostic-html-visualizer、analysis-enhance-auto、data-preprocessor、deep-analysis、两个 enhanced-html、两个 html、ontology-builder、physical-auditor、physics-bridge、rag-knowledge-builder。
- 讽刺的是：** ontology-builder 是 CP-2/CP-3 两道管线的关卡的执行者，自己却没有门禁脚本**；physical-auditor 背负 CP-8 却同样裸奔。
- 修复：见阶段 2-2。

**S2. 17 个 skill 有 agent-protocol.md，6 个缺失**；`tests/` 只有 7 个 skill 具备（data-preprocessor、deep-analysis、doe-analyzer、line-stability-report、optimizer-loop、sentinel、tuning-memory），16 个无任何测试；仅 3 个有 `tests/AC.md`。**analysis-auto 这个全系统唯一的编排入口，自己既无 protocol 文件也无 tests**（711 行 SKILL.md 自含协议）。

**S3. 触发词边界冲突：12 个 skill 无负面边界声明**，包括总编排器 analysis-auto（触发词含 "fault diagnosis, root cause analysis"，与 diagnostician 直接竞争）；"HTML visualization" 在 **5 个** SKILL.md 中重复出现；judge（"audit/review"）与 physical-auditor（"physical audit, review"）语义重叠。HTML 家族实际是"一个协议、四份拷贝"：`diagnostic-html-visualizer`（731 行，协议权威）+ `html-visualizer`（自称 Step 8）+ `html-reviewer`（重抄 15 条黑名单）+ enhanced 一对克隆。

### 后端（B1–B4）

**B1. HITL 是半成品死代码**：`hitlRequests` 只被读（`ws-server.mjs:668`、`diagnosis.service.mjs:523`）从不被写入；危险命令只 emit `hitl_request` 事件；`diagnosis.service.mjs:817` 的 `hitlTimeoutMs` 计算后未引用——"超时自动拒绝"从未生效。要么实现（写入请求 + 审批路由 + 超时兜底），要么删除（推荐先删，`run_config` 的 interaction_mode 已覆盖此需求）。

**B2. 数据库迁移非事务、无版本**：`database.mjs:111-208` 用 `PRAGMA table_info` 快照做 ad-hoc ALTER，无 `schema_version` 表、无事务包裹，代码注释（:178-181）自己承认快照会过期。多副本并发启动可能损坏 schema。

**B3. 会话/查询 Map 泄漏**：`diagnosis-engine.mjs:19-31` 仅在 `runs.size>100` 且 run 完成且零订阅时才清理；崩溃路径上的 `activeQueries`/`questionSessions`/`hitlRequests` 永不清理。

**B4. 错误响应泄漏内部信息**：多个路由直接把 `err.message` 以 500 返回（`diagnosis.routes.mjs:38`、`files.routes.mjs:119`、`ontology.routes.mjs:27`）；健康检查（`index.mjs:87`）只查 DB，不含引擎探活。

### 共享脚本（C1–C2）

**C1. `ontology_store.mjs` 并发写无锁**：所有变更器（`addVersion`→`nextVersion` :219-224、`reuse` :569-579、`deprecate` :584-591、`removeVersion` :670-679）都是无锁的读-改-写。并发 publish 会算出**相同的 nextVersion**，然后在 mkdir/写文件处冲突或互相覆盖；`readIndex`（:157-159）遇到损坏的 index.json **静默返回空数组**——资产库等于一键清零。
- 修复：`.lock` 文件（`fs.openSync(flag: 'wx')` + 超时自释放）串行化写；`readIndex` 损坏时改为备份损坏文件 + 硬失败。

**C2. `append-pipeline-event.mjs` 同样无锁**：JSONL 追加基本原子（小行），但 `run_manifest.json` 是读（:259）-改-写（:446）非原子；`readJson` 失败即硬退出（:260-263），损坏的 manifest 会让修复回路全部失灵。修复：manifest 写入改 temp+rename；损坏时从 `.pipeline_events.jsonl` 重建。

### 前端（F1–F2）

**F1.** `main.js:5` 无 `app.config.errorHandler`、无 `errorCaptured`——任一组件异常即白屏。
**F2.** `api/index.js:16-24` token 存 localStorage（注入脚本可读）；SSE/iframe URL 里再拼 token（:261,264,280-283）。`App.vue:204-211` 静态 import 全部视图，无路由分割。

### 配置/部署（D1–D3）

**D1.** `config/loader.mjs:133-136` 深合并无 schema 校验；`:16` 缺失的 `${VAR}` 静默变空串——**密钥缺失不报错**。`config/default.yaml:35-36` 明文 api_key 槽位。
**D2.** Dockerfile 以 root 运行、构建工具（g++/make/python3）留在运行镜像；docker-compose 无资源限制、无 nginx 服务（尽管有 nginx.conf）、`config/local.yaml` 以单文件 bind-mount（文件不存在即报错）。
**D3.** 零 CI：无 `.github/workflows` 或任何流水线；根 `package.json` 的 test 脚本是 `echo "Error: no test specified" && exit 1`。

---

## 四、P2 —— 一致性与可维护性

**N1. 文档数字漂移（中英文同步地错）**

| 声明 | 出处 | 实测 |
|---|---|---|
| skill 数量 18 | `README.md:144,523`、`README-zh.md` 同步、`CLAUDE.md:9`、`docs/architecture/system-overview.md:14` | **23**（`ls -d .claude/skills/*/SKILL.md \| wc -l`）；README 自带表格漏列 doe-analyzer/sentinel/tuning-memory/optimizer-loop/line-stability-report 这 5 个专家 skill |
| agent 数量 14 | `README.md:553,808`、`CLAUDE.md:9` | **16**（`.omp/agents/*.md`；AGENTS.md 正确） |
| 后端测试 116 passed | `README.md:19` 徽章 | 实测 44 tests / 40 pass（AGENTS 的 45 接近但也不准） |
| `ind-diag all` / `ind-diag backend` | `AGENTS.md:43-45` | **无效命令**——`commands/cli.mjs:120-127` 只接受 start/stop/status/restart/init/build/version |
| 引用已退役脚本 | `CLAUDE.md:157-159` | `stats.mjs`/`stats_validate.mjs`/`artifact-check.mjs` 已不存在 |
| `engines.mjs` 注释"14-engine table" | `engines.mjs:19` | 该表实际 12 条（claude/omp 在 dispatch 表另列），注释误导 |

**N2. 命名三类不统一**：`industrial-*`（20 个）/ `diagnostic-html-visualizer` / `darwin-skill` / `rag-knowledge-builder`；analysis-auto 内部用短名（"context-builder" 对应 skill 实为 `industrial-ontology-builder`）。
**N3. 孤儿与残骸**：`darwin-skill` 零外部引用且自述"不属于诊断管线"；存在**空目录 `.claude/skills/industrial-deep-diagnostic/`**（仅 workspace/，无 SKILL.md）——第 24 个目录；`rag-knowledge-builder` 被 ontology-builder 的 4 个 reference 文件隐式依赖，但 SKILL.md 从未点名。
**N4. 巨型 SKILL.md**：`diagnostic-html-visualizer`（731 行）与 `industrial-analysis-auto`（711 行）约为中位数（~150 行）的 5 倍，协议文本应下沉到 `references/`。
**N5. 校验器三份**：`validate.mjs`（零依赖、功能完整、支持 $ref/allOf/oneOf/if-then-else）与 `master-validate.mjs`、`schema_conformance.mjs` 意图重叠。**且 validate.mjs 有 bug**：L139-140 `if (value === null) return;` 使 nullable 检查不可达，enum 对 null 跳过。
**N6. 编排器与叶子重复入口**：`enhance-auto` 脚本硬编码叶子路径（`enhance_orchestrator.mjs:274/292/309/332/451/466`），而 `deep-analysis`/`physics-bridge` 又各自有 SKILL.md 与触发词——同一能力两个门。

---

## 五、优化方案（五阶段，可并行处标注）

> 原则：**不动方法论内核**（9 阶段管线、确定性脚本算数、门禁裁决、诚实降级、单一事实源 + 镜像 drift guard——这些是护城河，全部保留）。所有改造围绕"外壳配得上内核"。

### 阶段 0：止血（P0-1~P0-9，约 4~6 人日，1 周内）

| # | 动作 | 涉及文件 | 工作量 |
|---|---|---|:---:|
| 0.1 | nginx：删两个静态 alias → 走 `/api/files` 鉴权代理；`client_max_body_size 600m`；`/api/` 加 `proxy_read_timeout 3600s`；安全头 | `nginx.conf` | 0.5d |
| 0.2 | 路径守卫：新建 `utils/pathGuard.mjs`（resolve+relative 判定），替换 3 处 `startsWith` + omp `:run` 净化 + 上传文件名净化；补 4 个绕过向量的单测 | `files.routes.mjs`、`files.service.mjs`、`omp.service.mjs` | 1d |
| 0.3 | 引擎超时统一：提取 `withTimeout`，接入 claude/acp/codex/opencode；删除 HITL 死代码（B1） | 4 个 engine client + `diagnosis.service.mjs` | 1d |
| 0.4 | 进程韧性：全局错误中间件 + uncaught/unhandled 守卫 + SIGTERM 优雅关闭 + 启动时清理非终态 run | `index.mjs`、`diagnosis.service.mjs` | 1d |
| 0.5 | 并发治理：`MAX_CONCURRENT_RUNS` + queued 排队 + `tasks` Map 淘汰 + 终态会话清理（B3） | `diagnosis.service.mjs`、`external.service.mjs`、`diagnosis-engine.mjs` | 1d |
| 0.6 | 基础安全：`.env` 入 gitignore + 历史排查；CORS allowlist；WS maxPayload/背压/token 移出 query | `.gitignore`、`index.mjs`、`ws-server.mjs` | 0.5d |

**阶段 0 验收**：P0 清单 9 项逐条按各自"验收"复核通过；`npm test` 恢复全绿（0.7 与 P0-10 合并处理，约 +0.5d）。

### 阶段 1：多租户与授权（P0-6，约 8~10 人日）

1. **迁移机制先行**（0.5~1d）：建 `schema_version` 表 + 事务化迁移框架，替换 ad-hoc PRAGMA 判断（B2）。这是后面所有列变更的地基。
2. **归属列**（1d）：四张表加 `owner_user_id`（NOT NULL DEFAULT 指向存量数据的管理员）+ 可选 `tenant_id`。
3. **路由过滤**（2~3d）：list/get/download/delete 全部按 owner 过滤；`/api/external/v1/*` 的 API Token 绑定归属（token 表加 owner）。
4. **RBAC 接入**（1d）：`requireRole` 落到写操作路由（admin/user/readonly 三级）；删除类限 admin。
5. **前端**（1~2d）：token localStorage → httpOnly cookie（后端 set-cookie + CSRF 防护）；SSE/WS 走 cookie 或首帧鉴权；加全局 errorHandler + 路由懒加载（F1/F2）。
6. **限流**（0.5d）：登录 5 次/分钟、上传与诊断启动按用户配额。

**验收**：双账号隔离测试用例（A 建 run → B 全接口不可见）进后端测试套件；token 不再出现在 URL。

### 阶段 2：Skills 整合（S1–S3，约 8~10 人日，可与阶段 3/4 并行）

1. **HTML 五件套收敛为"一协议 + 薄包装"**（2~3d）：`diagnostic-html-visualizer` 保留为唯一协议权威；`html-visualizer`/`html-reviewer`/enhanced 一对改为 100 行内的参数化包装（引用同一 protocol + 各自 mode）；reviewer 的 15 条黑名单只存一份。
2. **补门禁**（3d）：按风险排序——ontology-builder（CP-2/3 执行者）、physical-auditor（CP-8）、physics-bridge、deep-analysis、data-preprocessor、enhance-auto；门禁形态统一为 `scripts/quality_gate.mjs`（5 个已有 skill 的既有范式，直接复制骨架）。
3. **触发词矩阵**（1d）：12 个缺负面边界的 skill 补 "Do NOT use for..."；产出 `docs/skill-routing-matrix.md`（意图 → 唯一 skill），把 5 处 "HTML" 冲突和 judge/auditor 重叠一次裁决。
4. **清理残骸**（0.5d）：`darwin-skill` 移出 skills 目录归档到 `docs/archive/`（或给触发词）；删除空目录 `industrial-deep-diagnostic/`；`rag-knowledge-builder` 改名 `industrial-rag-knowledge-builder` 或在 ontology-builder SKILL.md 显式声明依赖。
5. **输入契约文档**（1d）：新增 `docs/input-contract.md` 一张总表——格式支持矩阵、时间列/数值列要求、各 skill 行数下限（50/100/1k）、编码回退；README 链接它。
6. **巨型 SKILL.md 瘦身**（1d）：`diagnostic-html-visualizer` 与 `analysis-auto` 的协议正文下沉 `references/`，SKILL.md 保留 ≤200 行的调度视图。

**验收**：`sync-harness-skills.mjs --check` 通过（改动后必须重跑镜像）；23 个 skill 全部具备 frontmatter+负面边界；13→0 无门禁；`input-contract.md` 覆盖全部六条路径。

### 阶段 3：共享脚本并发安全（C1–C2，约 2~3 人日）

1. `ontology_store.mjs`：`.lock` 文件（`fs.openSync('wx')` + 过期自释放）串行化全部变更器；`readIndex` 损坏 → 备份 + 硬失败；补并发 publish 竞争测试。
2. `append-pipeline-event.mjs`：manifest 写入改 temp+rename；损坏 JSONL 行容错（跳过 + 记告警，不硬退）。
3. 校验器合并：`master-validate`/`schema_conformance` 退役或降级为 `validate.mjs` 的薄封装；顺手修 nullable bug（N5）。

**验收**：两个进程并发 publish 100 次无版本冲突、index 无损坏；损坏 index 恢复流程演练通过。

### 阶段 4：测试与 CI（P0-10、T 层，约 4~5 人日，可与阶段 2/3 并行）

1. 修 `better-sqlite3` ABI（锁定 Node 版本 + rebuild），恢复后端全绿（0.5d）。
2. 根 `package.json` 建 `test` 聚合入口：backend + 各 skill tests + `tests/*.mjs`（0.5d）。
3. **GitHub Actions**（1~2d）：lint → backend test → skill gates（逐个跑 quality_gate 的测试电池）→ `sync-harness-skills --check` → secret 扫描。
4. **文档数字守卫**（1d）：`scripts/check-doc-numbers.mjs`——从实际目录数、`.omp/agents` 数、`metrics.json`、测试输出生成事实，与 README/AGENTS/CLAUDE 断言比对，不一致 exit 1（把 N1 的六处漂移纳入 CI，防止再次腐化）。
5. 高风险 skill 补测试（1d，可分期）：analysis-auto（编排契约）、diagnostician、ontology-builder、physical-auditor。

**验收**：CI 全绿 + 文档守卫通过；README 的 116/18/14 全部改为生成值。

### 阶段 5：运维与可观测性（D 层收尾，约 3~4 人日）

1. 健康检查拆分 liveness/readiness（DB + 引擎探活 + 磁盘水位）。
2. Dockerfile：`USER node`、构建工具留在 builder 阶段；docker-compose 加 `mem_limit`/`cpus`、补 nginx 服务、`config/local.yaml` 改目录挂载；TLS 终结方案（与 webfrp Cloudflare Tunnel 二选一写清）。
3. config loader 加 schema 校验 + 缺失 `${VAR}` 启动即告警；`default.yaml` 的明文 key 槽位移到 env-only。
4. run 级 trace id 贯穿日志（winston 已在），慢事件（单 agent >10min 无产出）告警。

**验收**：非 root 容器 + 资源限制下压测通过；配置缺 key 时启动失败并指明变量名。

---

## 六、明确不做的事（防止过度工程）

1. **不重构 9 阶段管线与竞争假设协议**——benchmark 已验证（12/12、rubric 94.6），动它风险远大于收益。
2. **不引入 Kafka/Redis 等重型中间件**解决并发——当前 SQLite + 内存队列的规模（单机、产线级）足够，阶段 0.5 的轻量队列即可。
3. **不把 23 个 skill 合并成几个"大 skill"**——只收敛 HTML 家族与校验器；skill 粒度本身是这套系统的可组合性来源。
4. **不做在线闭环控制**——架构裁决 v1.4（纯分析系统）是正确且应坚持的。
5. **暂不扩展业务域 skill（人员/排产）**——先把外壳修好；等阶段 0-4 完成后再按"统计内核通用化 + mechanism 抽象"另立方案。

## 七、里程碑建议

| 里程碑 | 内容 | 出口条件 |
|---|---|---|
| M1（1 周） | 阶段 0 + P0-10 | P0 清单全部验收；测试全绿 |
| M2（+1.5 周） | 阶段 1 | 双账号隔离测试通过；token 不进 URL |
| M3（+2 周，可并行） | 阶段 2+3+4 | 23 skill 门禁全覆盖；CI 绿；文档守卫通过 |
| M4（+1 周） | 阶段 5 | 容器硬化 + 健康检查分级 |

总计约 **6~7 周**（并行可压到 4~5 周）。M1 完成即可安全地在**单团队内网**交付使用；M2 完成具备**多部门/多客户**隔离能力；M3/M4 是长期可维护性的分水岭。
