# 优化计划核查结论与验收规范（2026-10-17）

- 依据：`docs/optimization-plan-2026-10-16.md`（47 条）
- 核查方式：3 路并行独立审计（backend / skills / shared+deploy+docs）+ 主控逐条复核 P0
- **核查结论：44 条证实存在，3 条已变化**（详见 §1 修正表）
- 执行原则：不动方法论内核；每波结束必须 `cd app/backend && npm test` 全绿（基线 135/135）+ `node scripts/sync-harness-skills.mjs --check` 通过；所有改动不 commit（等用户决定）

---

## 1. 核查修正表（与计划的差异）

| # | 计划表述 | 核查结论 |
|---|---|---|
| P0-10 | 后端测试 44/40pass（红） | **已不成立**：当前 135/135 全绿（Node v24，ABI 问题已在多引擎工作中解决）。剩余动作：修 README 数字漂移（归入 N1） |
| P0-5 | "queued 状态枚举已存在" | **不准确**：`diagnostic_runs` 状态仅有 pending/running/awaiting_input/completed/failed/stopped/expired；`'queued'` 只是外部任务 progress.phase 与前端 i18n 标签。实现需新增 `queued` 状态 |
| P0-4 | 无启动清理 | **部分已有**：`index.mjs` init 已把 stale runs 标记 failed（"Server restarted"）；缺的是 uncaught/unhandled 守卫、全局错误中间件、SIGTERM 优雅关闭 |
| S1 | 13 个 skill 无门禁 | **实为 10 个**：deep-analysis/enhance-auto/enhanced-html-reviewer/data-processor/diagnostician/reporter/analysis-auto 已有门禁相邻脚本。真无门禁：darwin-skill、diagnostic-html-visualizer、data-preprocessor、enhanced-html-visualizer、html-reviewer、html-visualizer、ontology-builder、physical-auditor、physics-bridge、rag-knowledge-builder |
| S2 | 17 有 protocol / 7 有 tests / 3 有 AC | 现为 **18 / 9 / 4**（异构 skill 新增所致）；analysis-auto 无 protocol、无 tests 表述仍然成立 |
| N3 | 空目录 `industrial-deep-diagnostic/` | **已不存在**（commit abefd16 删除）；darwin 有 README/AGENTS/smoke 引用（"零外部引用"不成立）；rag 隐式依赖成立 |
| B3 | "崩溃路径永不清理" | **部分**：questionSessions 在 catch/stop/answer 均清理；准确的是 activeQueries 在诊断崩溃路径不清理 + runs Map 仅 >100 时清理 |
| C1 | readIndex 静默清零 | 成立，但 `writeIndex` 本身是 tmp+rename 原子写；风险点是"外部损坏的 index 被下一次写回持久化成空" |
| P0-7 | .env 未 ignore | 成立（`git check-ignore .env` rc=1）。附带：`config/local.yaml` 被 ignore、当前 default.yaml 无 `${}` 占位符 |

---

## 2. 验收规范（每条 = 可执行命令 + 期望）

### 阶段 0（止血）
| # | 验收命令 | 期望 |
|---|---|---|
| P0-1 | `grep -c "alias /app" nginx.conf` | 0（静态 alias 已删，全部走鉴权后的 /api/files） |
| P0-2 | `cd app/backend && npm test` 中 pathGuard 用例 | `../`、`data-evil` 前缀兄弟目录、绝对路径、URL 编码 4 向量全拒 + 上传文件名净化 |
| P0-3 | npm test 中 engine timeout 用例 | 假挂起 CLI 在 timeout 后被 kill，run 进 failed(timeout) 终态 |
| P0-4 | `grep -n "uncaughtException\|unhandledRejection\|SIGTERM" app/backend/src/index.mjs` + 重启演练 | 三守卫存在；`docker restart` 后无孤儿进程、非终态 run 有明确终态 |
| P0-5 | npm test 中并发用例 + 手动连发 5 个 start | 上限 2 执行、3 queued；终态后会话 Map 清理；external tasks Map 有淘汰 |
| P0-6 | 阶段 1 双账号隔离测试 | A 建 run，B 全接口不可见；非 admin 不能删他人资源 |
| P0-7 | `git check-ignore .env` | rc=0；`git log --all -- .env` 无历史提交 |
| P0-8 | `grep "client_max_body_size 600m" nginx.conf` + `proxy_read_timeout 3600s` | 均存在；安全头存在 |
| P0-9 | npm test 中 WS/CORS 用例 | 1MB 以上 WS 帧被拒/连接关闭；非白名单源 CORS 被拒；WS token 走子协议 |
| P0-10 | `cd app/backend && npm test` | 135+ 全绿（已达成，保持） |

### 阶段 1（多租户与授权）
- **验收**：双账号隔离测试进后端套件（A 的 run/ontology/token → B list/get/download/delete 全 404/403）；HITL 死代码已删；token 不出现在 URL（需前端改造完成）；登录限流 5/min 生效；迁移框架：`schema_version` 表 + 事务化，重复启动幂等。

### 阶段 2（skills 整合）
- **验收**：`node scripts/test-skills.mjs` 24/0；所有 skill 有负面边界；24 个 skill 均有确定性门禁（或显式声明由协议门禁覆盖）；`docs/skill-routing-matrix.md` 与 `docs/input-contract.md` 存在；`sync-harness-skills --check` 通过。

### 阶段 3（共享脚本并发安全）
- **验收**：两进程并发 publish 100 次无版本冲突（脚本化测试）；损坏 index 走"备份+硬失败"而非静默清零；append-pipeline-event 的 manifest 写入 temp+rename，损坏 manifest 可从 JSONL 重建；validate.mjs null+enum bug 修复并有用例。

### 阶段 4（测试与 CI）
- **验收**：根 `npm test` 聚合 backend+skills；`.github/workflows/ci.yml` 存在且含 lint/test/mirror-check/secret-scan 步骤；`node scripts/check-doc-numbers.mjs` 通过（README/CLAUDE/AGENTS 数字与实物一致）。

### 阶段 5（运维）
- **验收**：health 拆 liveness/readiness；Dockerfile 非 root + 多阶段；compose 有资源限制 + nginx 服务 + local.yaml 目录挂载；config 缺 `${VAR}` 启动即告警/失败。

---

## 3. 执行追踪

| 波次 | 内容 | 状态 |
|---|---|---|
| W1 | P0-1 nginx、P0-7 .gitignore（主控）；0.2 pathGuard（Agent）；0.3 引擎超时（Agent）；0.4+0.9 index/transport 加固（Agent） | **完成**：nginx 静态 alias 已删+限流头+超时；.env 入 ignore（历史无泄露）；`utils/pathGuard.mjs` + 3 文件接入（含 4 绕过向量测试）；`withTimeout` + 5 引擎接入（修复 win32 killTree 树杀缺陷 + omp 30s 泄漏定时器）；`lifecycle.mjs`/`cors.mjs` + 全局错误中间件 + SIGTERM 优雅关闭 + WS maxPayload/背压/子协议 token。合并后 **186/186 全绿** |
| W2 | 0.5 并发治理 + B1 HITL 清理 + B3 崩溃清理 + `ontology.service.mjs:1303` 路径漏洞（Agent-C）；阶段 3 共享脚本并发安全（Agent-D 并行） | **完成**：`runQueue.mjs` FIFO + `MAX_CONCURRENT_RUNS`（env→config→2）在 triggerDiagnosis 执行准入，超限入新 `queued` 状态（HTTP 实测 2 running+2 queued→排空）；HITL 注册表/超时/respond 处理器删除（保留信息性 hitl_request 事件）；external tasks 24h/200 条淘汰；崩溃/流结束统一 closeAllEngines；adoptCandidate 路径守卫。共享层：`withStoreLock`（wx 锁+30s 接管+nonce 释放）+ readIndex 损坏备份硬失败 + manifest temp+rename + JSONL 重建 + validate.mjs null 语义修复（964 对差分零回归）；`node scripts/test-shared-scripts.mjs` 71 PASS。合并后 **199/199 全绿**（两次） |
| W3 | 阶段 0 独立验收（verifier）+ 复跑 npm test | **完成**：25+ 路径穿越向量实测零逃逸（含 live HTTP 探测）；引擎超时 OS 级死亡验证；SIGTERM 优雅路径（in-process SIGTERM）exit 0 + WAL checkpoint + 引擎回收；并发实测 2 running+queued→排空序列精确吻合；WS 4401/1009/子协议/回退全测；CORS evil-origin 无 ACAO；199/199 + 71 PASS + 镜像一致。**发现新缺陷 D1-D8**（见 §4） |
| W3.5 | V1 缺陷小修批（D1/D2/D3/D4/D5/D7/D11）+ skills 门禁补齐 G1/G2 | **完成**：D4 每-run 超时持久化（gemini 0.02min 实测 failed/timeout 1.5s）、D5 omp 探测/拉起同源、D7 队列 ack 诚实、D3 跨 run 资产读关闭、D1/D2/D11 pathGuard 纵深；**215/215 绿**。G1：ontology-builder 28/28、physical-auditor 36/36、physics-bridge 28/28；G2：data-preprocessor 25/25、deep-analysis 19/19、enhance-auto 29/29；analysis-auto CP 行接入新门禁 |
| W4 | 阶段 1 多租户核心（E-A 迁移框架+cookie+CSRF+限流+归属助手；E-C 前端 cookie 化+F1/F2；SA HTML 家族收敛+4 门禁；SB 9 边界+路由矩阵+输入契约+darwin/rag 门禁） | **完成**：E-A 249/249（真实库迁移回填 v3）；E-C vite build 过、token 全面出 URL/存储；SA 16 块共享内容归一、wrapper 190→120 行、测试 8/12/11/12；SB 门禁 26/24、`docs/skill-routing-matrix.md` + `docs/input-contract.md`（修正 E-1 <100 行为合并门槛而非常量丢弃） |
| W4b | E-B 归属过滤+RBAC+泄漏修复+HITL 纯删+ontology 硬化+限流接线 | **完成**：278/278；双账号隔离 11 用例（11 诊断端点+9 workspace+6 chat+6 external 全部对外 404）；ontology 损坏映射 12 用例；external token 绑定 owner |
| W6 | P4a 测试聚合+CI+文档守卫（含 flake 隔离）；P5a 运维（Dockerfile 多阶段非 root/nginx 服务/资源限制/配置校验/健康拆分——**真实构建+容器冒烟**） | **完成**：`run-all-tests.mjs` 26/26；`.github/workflows/ci.yml`+gitleaks；文档守卫 31 处漂移修正后 OK；隔离 90/90×3；容器 healthy、uid=1000、health/ready 200；**修复 3 个"镜像从来无法启动"的历史缺陷**（venv 排除丢 .claude 资产/根 package 未安装/data/*.py 空拷贝） |
| W6b | Agent-F：WS 订阅归属 + trust proxy + 慢跑看门狗 | **完成**：288/288；ws-tenancy 6/6（含变异测试：禁用 viewer 即 6/6 失败）；修 run_chat 未 await 的历史 bug；`run_stalled` 事件 + 60s 扫描 |
| W6c | Agent-SLIM：巨文件瘦身（N4） | **完成**：analysis-auto 747→196、diagnostic-html-visualizer 736→202；零信息丢失审计（449/449、524/524 行全保留）；前 8000 字符窗口含全部硬规则+三处门禁调用 |
| W7 | V2 终局独立验收 | **完成**：288/288 + 26/26 + 20 对抗探测 0 泄露（cookie/CSRF/限流/迁移幂等/容器/前端全实测）。**发现 2 缺陷**：D2 高危（readDataFile 可读 SQLite/.auth-jwt-secret → **已修**：dot 段+系统库族+ontology store 全拒，20 用例；连带 D2b 上传覆盖 JWT 密钥写侧同类漏洞**已修**，47/47）；D1 中危（电池写回受管夹具 147 文件 → **已修**：5 个 runner 改 repo-tmp 暂存，全夹具还原，电池×2+镜像守卫保持绿） |
| W8 | 终局回归 + 交付 | **完成**：**310/310** 后端全绿；doc guard / test-skills 24/0 / 镜像 555 文件一致 / 夹具 0 脏；本会话遗留进程已清；**master-validate 199/199 = 100% 全过**（修复其自身 3 项：agent 数 14→16 硬编码、`.mimosa` 点目录漏排、optimizer-pilot `spawns=*` 缺 task 工具） |
| W3 | 阶段 0 独立验收（verifier）+ 复跑 npm test | 待开始 |
| W4 | 阶段 1 多租户（迁移框架 → 归属列 → 路由过滤/RBAC → 前端 cookie → 限流） | 待开始 |
| W5 | 阶段 2 skills 整合（HTML 收敛 / 门禁补齐 / 触发词 / 契约文档） | 待开始 |
| W6 | 阶段 4 测试与 CI + 阶段 5 运维 | 待开始 |
| W7 | 终局验收：全量回归 + 文档守卫 + 交付报告 | 待开始 |

### 进行中发现（滚动记录）
- `ontology.service.mjs:1303 adoptCandidate` 接受任意（含绝对路径）runDir → W2 并入修复（pathGuard 类漏洞，P0-2 同源）。
- 测试隔离缺陷（P4 候选）：`ontology-api.e2e.test.mjs` 与 `ontology-control.test.mjs` 共享本体库 data 目录 + node --test 并行运行 → 偶发指纹竞争/ms 时间戳比较 flake（两个独立代理各观察到 1 次）；且 mock-e2e 固定端口 3977 在并行套件时冲突。→ 归入阶段 4 测试隔离修复。
- `killTree` win32 缺陷：原实现先杀根进程导致 `taskkill /T` 失效（孙进程逃逸）→ 已修（taskkill 同步树杀先行），有 OS 级死亡断言测试。
