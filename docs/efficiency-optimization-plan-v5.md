# Industrial Deep Diagnostic — Token 与执行效率优化计划 v5

> 主题：**确定性快路径（Deterministic Fast Path）+ token 瘦身 + 等待治理**
> 约束：诊断大流程（Step 0-9 + 竞争假设协议 + 质量门）**不变**；只优化冗余执行方式
> 撰写日期：2026-09-09（基于 run `1ff880e9` 实测时间线，非推测）
> 精度红线：所有优化只改变"怎么执行"，不改变"执行什么分析"；质量门（CP-1..9）一个不少

---

## 零、实测瓶颈基线（不可变）

run `1ff880e9`（OMP 引擎，CNC 数据，**本体资产复用命中**，maxTurns=24，27.4 min，98 事件，24 turns）分阶段耗时：

| 阶段 | 实测 | 理论最快 | 浪费根因 |
|------|------|---------|---------|
| Step 0/1 setup+inspect | ~4 min | ~1.5 min | SKILL.md 全文读 2 次；`ls -R` 递归列目录；todo 管理占 6 turns |
| Step 2 本体（**reuse 命中**） | **~13.5 min** | **≤1 min** | 复用命中后仍派发 LLM 子代理 → 3×300s hub wait 串行阻塞 → 子代理再读协议/校验/publish 走完整 LLM 往返 |
| Step 3 派发 | 截断 | — | maxTurns 用尽（todo 管理+等待占 turn） |
| **合计浪费** | **~15 min + ~8 turns** | — | 全部可确定性消除 |

**token 浪费点**：hub wait 每次轮询都消耗主代理 turn + 上下文（3 次等待 ≈ 3-6 turns 纯空转）；SKILL.md 双读 ≈ 2×8K chars 进上下文；todo op 占 6+ turns；子代理整轮 LLM 往返（读协议+写产物+publish）在复用场景完全多余。

**核心洞察**：复用命中（拷贝+CP-2 校验+publish）是**纯确定性操作**——脚本 3 条命令、无任何语义判断。让 LLM 子代理去执行一个不需要判断的流程，是整个管线最大的单点浪费。

---

## 一、优化方案（4 项，全部可独立回滚）

### F1 · 本体复用确定性快路径（最大项，省 ~13 min + ~6 turns/run）

**思路**：编排器在派发 Step 2 **之前**，先在主代理本地用一条 bash 命令完成「指纹匹配 → reuse 拷贝 → CP-2 校验 → publish」，全部命中则**跳过子代理派发**；仅 reuse 校验失败或 extend/miss 时才派发 LLM 子代理走完整构建。

**改动**：
1. `ontology_store.mjs` 新增子命令 `fast-reuse`：一条命令完成 find→reuse→(CP-2 校验)→publish，输出 JSON：`{fastPath: true|false, reason, ontology_path}`。CP-2 校验内置（validate.mjs + ≥1KB），失败自动回滚拷贝并返回 fastPath:false。
2. 编排器 `industrial-analysis-auto/SKILL.md` Step 2 前插入 **Step 2-F（确定性快路径，≤60s）**：
   ```bash
   node "$SHARED_PATH/scripts/ontology_store.mjs" fast-reuse \
     --data <DATA_PATH> --run-dir "$RUN_DIR" [--scene <scene_key>] \
     --schema "$SKILL_ONT_BUILDER/schemas/ontology_schema.json"
   ```
   输出 `fastPath:true` → 写 pipeline 事件 `ontology_reused_fastpath`，**直接跳到 Step 3**（clarification 沿用快路径生成的 AUTO_RESOLVED 默认文件），不派发子代理、不进 hub wait。
   输出 `fastPath:false` → 走现行 Step 2 子代理派发（extend/miss 场景语义判断仍需 LLM）。
3. 快路径同时生成最小 `clarification_needed.json`（AUTO_RESOLVED，source: fastpath）与 `rag_deep_understanding.json` 跳过标记——保持 CP-3/下游契约完整。

**精度保障**：CP-2 schema 校验在快路径内强制执行，失败即回退 LLM 路径；本体内容与 store 资产字节级一致（copy 语义），语义零损失。
**集成性**：不改 diagnosis.service（run.harness 分发不动）；omp/claude 双引擎 prompt 里的 ONTOLOGY_DIRECTIVE 保留（miss/extend 场景仍需要）；run_config.ontology.mode=full 时不走快路径直接 LLM 构建。

### F2 · hub wait 治理：产物轮询替代 LLM 等待（省 ~4-8 turns/run）

**思路**：主代理在 hub wait 循环中，每轮先做一次**文件存在性检查**（1 条 bash ls），产物就绪立即退出等待——不再把 300s 等满才检查。

**改动**：`industrial-analysis-auto/SKILL.md` Step 2/3 派发块的等待规则追加一行：
「hub wait 循环的每轮迭代：先用 `test -f <关键产物>` 检查（如 `01_ontology/ontology.json` / `02_processed/data_analysis_conclusion.json`），存在 → 立即 break 进入下游；仅当产物未就绪时才继续 hub wait。」

**精度保障**：产物出现即下游（与现行语义一致，只是提前退出空等）。
**实测映射**：run `1ff880e9` 中 3 次 wait 分别在 307s/248s 处才退出——文件早已就绪。

### F3 · token 瘦身：SKILL.md 单读 + ls 纪律（省 ~8K chars + ~2-4 turns/run）

**改动**（全部是 SKILL.md 一句话约束，无代码）：
1. `industrial-analysis-auto/SKILL.md` Step 0 追加：「SKILL.md 全文只在首次读取一次；后续需要协议细节时读对应 reference 文件，禁止重复读 SKILL.md 全文。」
2. 同文件追加：「目录探查用 `ls <dir>` 单层；禁止 `ls -R` / 递归 glob 全库（单次 >2s 的探查命令视为浪费）。」
3. todo 纪律：「todo op 每阶段最多 1 次（start+done 合并为一次 done 更新）；禁止每完成一个子项就更新 todo。」

**精度保障**：纯执行纪律，分析内容不变。

### F4 · 复用运行的对话式精简 prompt（省 ~1-2K chars/run）

**改动**：`claude-client.mjs` / `omp-client.mjs` 的 `buildPrompt`：当 `ontology.mode === 'reuse'` 且指令来自 run meta（fast path 已知会命中）时，Data 段追加一句：「Ontology asset will be reused verbatim from the store (fast path) — do not re-describe or re-verify parameter semantics beyond CP-2.」并省去 followUpMessage 的重复语言段（已由 runtime rule 7 覆盖）。

**精度保障**：runtime rules 1-10 不变；仅去除复用场景下语义重复的 prompt 文本。

---

## 二、预期收益（可测量）

| 指标 | 基线（1ff880e9） | 优化后预期 | 测量方法 |
|------|-----------------|-----------|---------|
| 复用命中 run 总时长 | 27.4 min | **≤10 min** | DB 事件流 span |
| 复用命中 run turns | 24 | **≤14** | stats 事件 num_turns |
| 本体阶段耗时（reuse） | ~13.5 min | **≤1 min** | tool_use 时间线 |
| hub wait 空转 turns | 3-6 | ≤2 | 事件流 hub 计数 |
| SKILL.md 读取次数 | 2 | 1 | 事件流 read 计数 |
| full 构建 run | 不变（~20 min） | 不变或略降（F2/F3 生效） | 同上 |
| **分析精度** | CP-1..9 全过 | **不变**（CP-2 在快路径内强制，schema 校验同一命令） | validate.mjs |

## 三、落地顺序与验收门

| 项 | 文件 | 验收 |
|----|------|------|
| F1 | ontology_store.mjs（fast-reuse）+ analysis-auto SKILL.md（Step 2-F） | 单独跑 `fast-reuse` 输出 fastPath:true + CP-2 过；复用场景 OMP run 总时长 ≤10 min；miss 场景回退正常 |
| F2 | analysis-auto SKILL.md（等待规则一行） | 下一个含子代理派发的 run 中 hub wait 计数 ≤2 |
| F3 | analysis-auto SKILL.md（三条纪律） | 事件流中 SKILL.md read=1；无 `ls -R` |
| F4 | claude-client.mjs / omp-client.mjs buildPrompt | 复用场景 prompt 含 fast-path 句、无重复语言段 |

**总验收**：复用场景 OMP 诊断一次端到端 ≤10 min、turns ≤14、CP-2/CP-3 过、产物契约完整（data_analysis_conclusion.json 由下游补齐或 run 内完成）。

## 四、风险与回滚

| 风险 | 缓解 | 回滚 |
|------|------|------|
| 快路径误判（把该 extend 的当 reuse） | schema_fp 精确匹配不变；content drift 时 fast-reuse 返回 fastPath:false 走 LLM | 编排器 Step 2-F 是"先试快路径，失败走原路"——删除 Step 2-F 即回到现行行为 |
| 快路径生成的 clarification 过于简单 | AUTO_RESOLVED + source 标记；CP-3 语义不变（本体的 objectives 已含分析问题映射） | mode=full 用户强制可绕过 |
| 等待规则被 agent 忽略 | 与现有止损规则同段落，强约束措辞；F1 落地后子代理派发场景本身大幅减少 | 单行回滚 |

---

## 五、独立评审结论（2026-09-09，已全部采纳）

独立 Agent 对本计划逐条对照代码库评审，结论：**F2/F3 直接可落地；F1 架构成立但有 2 个硬阻断**，落地前必须修正：

| # | 评审发现 | 采纳的修正 |
|---|---------|-----------|
| R1（硬阻断） | `ontology_reused_fastpath` 不在 `append-pipeline-event.mjs` 的 VALID_EVENTS 白名单，exit 1 | **改用既有事件**：`step_complete --step context_builder --data '{"fastpath":true}'` + `clarification_auto_inferred`（零代码改动） |
| R2（硬阻断） | `pipeline-log-check.mjs` 要求 `01_ontology/ontology.json` 存在时必须有 context-builder agent_start/complete 事件，且 data-processor 前置解析依赖其完成——快路径 run 在 Step 9 finalize **必挂** | 修补 `pipeline-log-check.mjs`：事件 data 含 `fastpath:true` 时豁免 context-builder 事件要求与前置解析 |
| R3 | `validate.mjs` 是纯 CLI 无导出 | fast-reuse 以子进程 spawn 调用（exit 0/1） |
| R4 | content_match:false（跨批次）不应阻断快路径 | exact schema 匹配即快路径；content drift 作为 advisory 记入 reason |
| R5 | rag_deep_understanding.json 缺席本就是已处理契约 | 删除 plan 中"跳过标记文件"——不生成 |
| R6 | F2 的 Step-3 等待目标 `data_analysis_conclusion.json` 由主代理 finalize 写，hub 内等待是循环 | 改为等待 agent 产物 `02_processed/feature_summary.json` / `03_figures/plot_manifest.json` |
| R7 | F4 目标应为 `buildOntologyDirective`（双引擎共用，已持有 mode）；followUpMessage 重复语言段不存在 | F4 重定向到 buildOntologyDirective；删除该条款 |
| R8 | Blacklist #2 禁止主代理执行子代理协议；Step 2-F 需豁免句 | Step 2-F 加明示豁免："确定性脚本不属于协议执行" |
| R9 | "strictly sequential" 要求跳过步骤记录 not_applicable_reason | Step 2-F 的 step_complete 事件 data 含 fastpath:true 即满足，明示写入 |

落地差异以本节为准；正文 F1-F4 描述保留作为设计意图记录。
