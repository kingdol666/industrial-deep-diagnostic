# IDD（industrial-deep-diagnostic）计划：面向数字员工闭环的分析引擎

- 日期：2026-10-01
- 定位：三项目联创中 IDD 只做"**分析引擎**"——深度诊断、哨兵统计（SPC/漂移/变点）、调优归因与 playbook、寻优 campaign。不碰知识持久化（KB 负责）与下发审批（AgentWorkShop 负责）。
- 协作对手：AgentWorkShop（枢纽，diag-bridge 插件 base=3210，token 已互通）+ rag-knowledge（KB，8771）。
- 今日实测：平台 diag_run 异步受理 ✓、快照上传 ✓（token 桥接后）、任务生命周期含诚实失败 ✓；**deep 诊断执行依赖 omp harness，当前外部 LLM 供应商挂起即无法出报告**（"Agent ended without producing report.md"）。

## 1. P0（机器契约最后一公里，预计 3~5 天）

### 1.1 结构化结论出口（最关键）
- task result 增加 `conclusion` 字段：直接复用 `.claude/skills/industrial-diagnostician/schemas/diagnosis_schema.json`（diagnosis_type/primary_finding/hypotheses/根因/建议/置信度/证据 L1-L7），管线落盘的 diagnosis.json 已有数据，只差 API 通道。
- 消费方：AgentWorkShop 的 diag→KB 确定性管线与 Agent 直消费（不再让 Agent 读 md 自己猜）。
- 验收：`GET /api/diagnosis/tasks/:id` 返回 `result.conclusion`（固定 JSON Schema，中文叙述+英文枚举）。

### 1.2 幂等提交与产物 URL 化
- `POST /api/diagnosis/tasks` 增加 `Idempotency-Key`（重复提交返回原 task）与可选 `callback_url`；docs/api.md 收录 /tasks 契约。
- result.artifacts：`{report_md, report_html, diagnosis_json}` 全部给 HTTP 回读 URL（`/api/files/...` 带 token 可取），不交付宿主机裸路径。

### 1.3 机器 token 通道
- service-account bootstrap：env 种子或 admin 一次性铸造**长效/永久** `idd_` API key（当前最长 365 天，对长驻产线服务偏短）；供 AgentWorkShop 免人工注册续期。

### 1.4 对象模型最小集
- task body 增 `object{type: 'line'|'experiment', id, name}`，落库入 `diagnostic_runs` 并进 conclusion——支撑产线与**实验**两类诊断对象；实验对象接通 `industrial-doe-analyzer` 的 API 触发通道（当前只有 skill 入口）。

## 2. P1（显著增强，预计 4~6 天）

1. **预算档位**：`profile=fast|standard|deep` 映射 maxTurns/timeout/E0-E8 增强开关；task view 上报实际消耗（时长/turns）——产线在线诊断用 fast，复盘用 deep。
2. **同对象演化对比**：按 object id 聚档 `objects/:id/history` + 结论 diff（复用 ontology diff 能力）——"同一产线第 N 次诊断 vs 上次"是闭环最有价值的输出。
3. **AML/MPC 数据契约**：结论→训练数据标注包（根因标签+稳态窗+工况切片），对接 AgentWorkShop 的 dataset 构建与归因。
4. **多租户**：runs 加 owner/tenant 列、list 过滤、token 绑定租户（当前 listRuns 全局可见）。
5. harness 韧性：LLM 供应商不可用时 task 明确报 `harness_unavailable` 并支持恢复重跑（当前失败语义已诚实，补"从断点续跑"）。

## 3. P2（远期）

1. 签名 webhook 与事件订阅（替代纯轮询）。
2. 全局并发/优先级队列（多产线同时诊断的资源争抢治理）。
3. 置信度在线校准（延伸 benchmark 一致性审计）。

## 4. 协作契约（IDD 对外承诺）

1. 提交：`POST /api/diagnosis/tasks {object, dataPath|snapshot, profile, idempotency_key}` → `{task_id}`。
2. 状态：`GET /api/diagnosis/tasks/:id` → `{status, result:{conclusion(Schema v1), artifacts(URL 集), score, verdict}}`。
3. 鉴权：仅 `idd_` API Token（Bearer 或 x-api-token）；快照 CSV 列约定不变（timestamp+节点列）。
4. kb-ready 包：IDD 保证结论包可校验（schema+证据可回读），**入库动作归平台 kb_agent/平台编排**——维持"IDD 不连 KB"的既有架构裁决。
