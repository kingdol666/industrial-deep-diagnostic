# Benchmark 执行计划（可在后续真正落地）

> 2026-09-10 v1 · 前置阅读：`docs/benchmark-design.md`（设计与期刊对标）、`.claude/skills/industrial-benchmark-runner/SKILL.md`（复现编排）
> 目标：把当前 tier0 冒烟（9 case）推进到**可发表规模**，且每一步都可复现、可审计、可增量停表。

---

## 0. 当前起点（已完成，勿重复做）

| 项 | 状态 |
|---|---|
| 评估框架（case 定义 → prepare → note → diagnose → grading → aggregate） | ✅ 已实现并跑通 |
| tier0 冒烟 9 case（SKAB/TEP/IndPenSim × 故障+控制） | ✅ 已执行：Top-1 2/6、Top-k 6/6、控制组 3/3 零误报 |
| 复现性门禁 | ✅ `REPRODUCIBLE`（46 数据集 hash / 9 9 覆盖 / 指标零漂移 / 9 9 执行证明 PASS） |
| Skill 编排 | ✅ `industrial-benchmark-runner`（prepare/notes/commit/status/import-state + verify-repro） |
| 数据集 | ✅ TEP · SKAB · IndPenSim 已备；SECOM · C-MAPSS 新增下载；Paderborn 下载中；FEMTO 按需 |
| 期刊 baseline 表 | ✅ AEI 7 篇 + MSSP/RESS/C&CE/IEEE 8 篇，含可验证 DOI |

**因此本计划的起点是"扩规模 + 补算力口径"，不是重建框架。**

---

## 1. 三档规模（按性价比递进，可随时停）

| 档 | case 数 | 构成 | 估计机时（串行） | 产出用途 |
|---|---|---|---|---|
| **T1 · 冒烟**（已完成） | 9 | 3 数据集 × {2 故障 + 1 控制} | ~1 h | 框架自检、CI 回归 |
| **T2 · 主结果** | 36 | 6 数据集 × {4-5 故障 + 1 控制}：SKAB(6) · TEP(6) · IndPenSim(6) · SECOM(6) · C-MAPSS(6) · Paderborn(6) | 8-20 h | 论文主表、与 B5/B7/B8/B11 对标 |
| **T3 · 大样本 + 消融** | 120+ | T2 × 3 重复 + 消融（有/无本体复用 × 有/无 E0-E8 × 3 引擎）+ 陌生故障组 | 40-80 h | 统计显著性、消融表、稳健性 |

成本口径（按实测 tier0 单 case 约 6-8 分钟、单 case ≈ 20-40k tokens）：T2 ≈ 36 × 8 min ≈ 5 h 实测（保守 2 倍余量 → 8-20 h），T3 约 5 倍 T2。

---

## 2. 分阶段动作（每阶段有明确验收）

### P0 · 数据补齐（0.5 天，无算力）
1. 完成 Paderborn 下载 + `bsdtar` 解包 → 写 `prepared/paderborn/*.csv`（降采样到 1 s 窗，与 SKAB 口径一致）。
2. CWRU 手工补齐：按 `data/benchmark/downloads.lock.json` 的 manual 指引下载 12 kHz 驱动端 .mat → 转 CSV。
3. SECOM / C-MAPSS 切片：SECOM 保留全部特征但按时间窗切 6 个 run；C-MAPSS 选 FD001 的 6 台发动机（含真实 RUL 标签，作为"退化类"对照）。
4. FEMTO：仅在需要 run-to-failure 轨时 `--include-large` 下载。
5. `node scripts/benchmark/make_dataset_manifest.mjs` 刷新指纹。
   **验收**：`downloads.lock.json` 中每个数据集 `status=ok` 或显式 `manual`；manifest 覆盖全部 prepared CSV。

### P1 · T2 case 集与真值（1 天，无算力）
1. 依 P0 数据写 `scripts/benchmark/cases/tier2_main.json`：每数据集 4-5 故障 + 1 控制；填 `truth` / `keywords` / `expect_type_set` / `process_description`（真值只存在于 case 文件与评分器，严禁进入管线可见目录）。
2. 陌生故障组（针对 FaultExplainer 的记忆污染软肋）：用 TEP 组合扰动构造 4 个"教科书无记载"case，单列 `tier2_novel.json`。
3. 控制组扩展：每数据集 ≥1（T2 共 ≥6）。
   **验收**：`run-tier.mjs status --tier <file>` 能列出全部 case；case 文件通过 JSON 校验。

### P2 · T2 执行（8-20 h 机时）
1. `run-tier.mjs prepare --tier tier2_main.json`（确定性，分钟级）
2. `run-tier.mjs notes` → 诊断 agent 逐 case 填 note（**唯一的人工/LLM 环节**）
3. `run-tier.mjs commit` → 门禁 + 评分 + journal
4. `aggregate.mjs --tier-file tier2_main.json` → metrics.json + report.md
5. `verify-repro.mjs` 必须 `REPRODUCIBLE`
   **验收**：36/36 有 grading；控制组零误报或误报可解释；`repro_report.json` 无 FAIL。

### P3 · 消融与引擎维度（8-16 h）
- 消融矩阵：`{ontology: auto|full} × {enhancement: auto|on} × {harness: omp|claude|mock}`，在 12 个代表 case（每数据集 2 个）上跑 → `tier_ablation.json`。
- 产出消融表：证明增益来自**方法**（本体+RAG+竞争假设+增强）而非模型，且引擎可替换性成立。
  **验收**：每个消融臂 ≥12 个 grading；主结果与消融的差异有方向性解释。

### P4 · 论文结果与对标（1-2 天，无算力）
1. 生成双口径对标表（口径 A 同任务直比 / 口径 B 跨任务量级参照），严格按 `docs/benchmark-design.md` §4.4 的诚实性要求标注。
2. 统计检验：对重复运行报 均值 ± 标准差 + 配对检验（T3 阶段提供样本）。
3. 负例分析：列出失败 case 与机理（如 IndPenSim 批次的弱可分辨性），呼应 B15 的基准警示。
   **验收**：结果表每个数字都能追到 `gradings/<case>.json` + `run_dir` + 数据集 sha256。

---

## 3. 集成到系统的方式（真正落地，不是离线脚本）

| 集成点 | 方式 | 状态 |
|---|---|---|
| 案例执行 | Skill `industrial-benchmark-runner` 直接调用既有确定性工具链（setup/inspect/convert/stats/validate/finalize） | ✅ 已通 |
| 在线作业 | `POST /api/diagnosis/start {harness, dataPath}` 可用 API 驱动同一批 case（引擎维度消融走这条路） | ✅ API 已就绪（含默认 omp 与错误契约） |
| 结果落库 | grading → `results/benchmark/`；如需入库可经 `/api/history` 与 SQLite（runs 表已含 harness 字段） | ✅ 结构就绪 |
| 复现门禁 | `verify-repro.mjs` 可挂 CI：非零退出即阻断 | ✅ 已通（当前 REPRODUCIBLE） |
| 报告生成 | `aggregate.mjs` → `report.md`；HTML 版可复用 `industrial-html-visualizer` | 部分（MD 已通） |
| 经验沉淀 | 已验证 run 可经 RAG `/accumulate` 沉淀（受路径白名单约束，需在 storage 白名单内配置） | 待配置 |

---

## 4. 风险与处置

| 风险 | 影响 | 处置 |
|---|---|---|
| 真值泄漏（case 文件被管线读走） | 结果无效、审稿人质疑 | case 文件置于 `scripts/benchmark/cases/`，run dir 只写 `process_description`；note 模板显式警告；grading 与 case 分离 |
| 预训练记忆污染（TEP 教科书故障） | 高估能力 | 陌生故障组 P1-2 单列；对照组报告"已知/未知故障"分层结果 |
| 分割泄漏（轴承类） | 指标虚高 | 按实体划分 + 报告泄漏受控口径（对齐 B1/B2 的 Macro AUROC 协议） |
| 样本量不足 | 无统计显著性 | T2 起每类 ≥4 故障，T3 重复 3 次报均值±标准差（直指 B14 的样本量软肋） |
| 依赖外部 LLM 配额 | 执行中断 | 支持 `mock` 引擎跑通链路；omp 为默认引擎，失败可换引擎重跑同一 case |
| 数据集源失效（CWRU/Paderborn 已出现过 404） | 数据缺档 | 下载脚本记录候选 URL + manual 步骤；manifest 记录 sha256，可校验来源一致性 |

---

## 5. 里程碑与验收清单

- [ ] M0（已完成）框架 + tier0 + 复现门禁 `REPRODUCIBLE`
- [ ] M1 P0 数据补齐：6 数据集 prepared CSV + manifest 刷新，CWRU/Paderborn 缺口显式记录
- [ ] M2 P1 case 集：`tier2_main.json` 36 case + `tier2_novel.json` 4 case
- [ ] M3 P2 执行：36/36 grading，`verify-repro` REPRODUCIBLE，metrics.json 生成
- [ ] M4 P3 消融：≥12 grading/臂，消融表产出
- [ ] M5 P4 论文表：双口径对标表 + 失败分析 + 全部数字可追溯

**M3 是"能不能写论文"的分水岭；M1/M2 不耗算力，可先做。**
