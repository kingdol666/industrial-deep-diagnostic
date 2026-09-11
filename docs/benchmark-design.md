# Benchmark 设计与期刊 baseline 对标

> 2026-09-10 · 配套：`docs/dataset-experiment-research.md`（数据集调研·前序）、`docs/benchmark-plan.md`（执行计划）、`.claude/skills/industrial-benchmark-runner/`（复现编排）
> 目的：把这个系统的能力变成**可复现、可对标、审稿人认可**的实验结果。

---

## 1. 被评测系统：当前设计的回顾

| 层 | 组件 | 对 benchmark 的意义 |
|---|---|---|
| 编排 | 9 步主管线（Step 0-9）+ E0-E8 增强管线，14 个专职 agent、18 个 skill | 每个 case 的"被评测对象"就是一次完整 run；产物即证据 |
| 推理 | 竞争性假设协议（DETERMINED / COMPETING_SET / NEEDS_DATA）+ 四级反臆测 + 证据分级 L1-L7 + 置信度上限 | 产出"根因结论 + 置信度 + 推理链"，可与论文的分类输出对齐 | 
| 数据 | 标准化输入（时间戳 + 多传感器列 CSV）| 与全部候选数据集零改造适配 |
| 引擎 | 14 个 harness（默认 omp），同一契约 | **引擎可替换性本身是一个消融维度**（同一 case 换引擎） |
| 审计 | Judge 10 项评分门 + 物理审计 + `.pipeline_events.jsonl` 执行证明 | 提供论文需要的"执行可信度"证据，而非仅最终答案 |
| 服务 | REST API（`/api/harness`、`/api/diagnosis/*`）+ 14 引擎注册表 | benchmark 可用 API 驱动，结果落库可追溯 |

**关键结论（决定 benchmark 形态）**：本系统输出的是**每个 run 一个根因结论**，不是逐样本标签。因此对标必须采用**"每故障 run → 根因是否正确"**的口径（与 FaultExplainer、RCA 文献一致），而不能直接套用逐样本 F1。逐样本检测类指标只在"是否检出异常"这一子任务上与 FDD 文献对齐。

---

## 2. 期刊 baseline 对标表（可验证 DOI）

> 检索方式：Crossref/OpenAlex 核对书目 + doi.org 解析 + arXiv 全文核对实验细节。
> **透明度声明**：Elsevier 全文（AEI/MSSP/RESS）对自动抓取返回 403，凡未能读到实验章节的均在"实验细节"列标注 **未核实**——不猜测数字。

### 2.1 AEI（Advanced Engineering Informatics）— 目标期刊，优先对标

| # | 论文 | 年份 | DOI | 数据集 | Baseline | 实验细节 |
|---|---|---|---|---|---|---|
| A1 | He et al., Interpretable modulated differentiable STFT … freight train wheelset bearing cross-machine transfer | 2024 | `10.1016/j.aei.2024.102568` | 自采列车轴箱 + 实验室台架（BJTU/Ottawa） | EfficientNet-v2 · ResNet-18 · DenseNet-121 · WDCNN · DRSN-CW | 跨机迁移、20 kHz、900-2500 rpm（arXiv 预印本已核实）；**准确率数字未核实** |
| A2 | Wang & Liu, From anomaly detection to classification with graph attention and transformer for MTS | 2024 | `10.1016/j.aei.2024.102357` | 未核实 | 未核实 | 未核实 |
| A3 | Liu et al., Spatial-temporal adaptive causality graph fault root cause location (STACGG/EAGG) | 2025 | `10.1016/j.aei.2025.103765` | 时序工业过程（疑似 TEP 类） | GNN 因果基线（未核实） | 未核实 —— **与我们 RCA 任务最同源，必须优先读原文** |
| A4 | Liu et al., Label-free evaluation for performance of fault diagnosis model on unknown distribution | 2024 | `10.1016/j.aei.2024.102912` | 未核实 | 未核实 | 未核实（"无标签评估"思路可借鉴为我们的评估维度） |
| A5 | Pang et al., Fault vibration model driven fault-aware domain generalization for bearing FD | 2024 | `10.1016/j.aei.2024.102620` | 未核实（疑似 CWRU/Paderborn） | 未核实 | 未核实 |
| A6 | Yan et al., FTSDC: federated transfer learning for bearing cross-machine FD | 2024 | `10.1016/j.aei.2024.102499` | 未核实 | 未核实 | 未核实 |
| A7 | Yue et al., Root cause analysis for process industry using causal knowledge map under large group environment | 2023 | `10.1016/j.aei.2023.102057` | 过程工业案例（疑似 TEP） | 未核实 | 未核实 —— **知识图谱式 RCA，与我们本体层直接对标** |

### 2.2 其他优质期刊（含可复现数字的强对标）

| # | 论文 | 期刊/年 | DOI / 标识 | 数据集 | Baseline | 可核对数字 |
|---|---|---|---|---|---|---|
| B1 | Vieira et al., Towards a more realistic evaluation of ML models for bearing FD | **MSSP** 2026 | `10.1016/j.ymssp.2026.114640`（全文 arXiv:2509.22267） | CWRU · Paderborn · Ottawa(UORED) · HUST | WDCNN · CDCN · WDTCNN · 1D-ConvNet · ResNet1D · RF（手工特征） | **Macro AUROC**：UORED WDCNN 频域 93.12±4.26%；PU WDCNN 包络 79.56±13.07%；CWRU RF 85.06±8.92% vs WDCNN 74.51±9.43%；**分割级泄漏可虚高 +12.6%**。代码 `github.com/gama-ufsc/bearing-data-leakage` |
| B2 | Hendriks et al., Towards better benchmarking using the CWRU dataset | MSSP 2022 | `10.1016/j.ymssp.2021.108732` | CWRU | —（基准批评：划分泄漏） | CWRU 泄漏问题的奠基文献 |
| B3 | Li et al., GNN for intelligent fault diagnostics and prognostics: guideline & benchmark | MSSP 2022 | `10.1016/j.ymssp.2021.108653` | 未核实 | GNN 架构族 | 未核实 |
| B4 | Zhao, Zio, Shen, Domain generalization for cross-domain FD: application-oriented benchmark | **RESS** 2024 | `10.1016/j.ress.2024.109964` | 未核实 | DG 方法族 | 未核实 |
| B5 | Reinartz et al., Extended TEP simulation dataset for fault detection & DSS | **C&CE** 2021 | `10.1016/j.compchemeng.2021.107281` | **TEP 扩展版**（6 生产模式/含过渡/多扰动幅值） | PCA + T²/Q 控制图 | 指标 = **ARL**（平均运行长度）；数字未核实。数据 Harvard Dataverse `10.7910/DVN/6C3JR1`（自动抓取被 202 拦截） |
| B6 | Han et al., Maintenance-cost-oriented FD framework: TEP case study | RESS 2026 | `10.1016/j.ress.2026.112927` | **TEP** | 未核实 | 成本型指标；数字未核实 |
| B7 | Pozdnyakov et al., Adversarial attacks & defenses in FDD: benchmark on TEP | IEEE OJIES 2024 | `10.1109/OJIES.2024.3401396`（arXiv:2403.13502） | **TEP** | MLP · GRU · TCN | **干净准确率**：MLP 0.8873±0.0002 · GRU 0.9067±0.0041 · TCN 0.8985±0.0097；攻击下 0.75-0.90 |
| B8 | Hartung et al., Deep anomaly detection on TEP data | arXiv 2023 | `arXiv:2303.05904` | **TEP** | BeatGAN · TCN-S2S-AE · 重构/预测/VAE-GAN 家族 | **F1**：BeatGAN 0.9699（AUPRC 0.9896，第 1 名）；TCN-S2S-AE 0.9632 |
| B9 | Montesuma et al., Benchmarking DA for chemical processes on TEP | ECML-PKDD 2024 workshop | `arXiv:2308.11247` | **TEP** | 11 种域适应（MMD/DANN/最优传输） | 准确率（未核实）；代码 `github.com/eddardd/tep-domain-adaptation` |
| B10 | Tuli et al., TranAD | PVLDB 2022 | `10.14778/3514061.3514067`（arXiv:2201.07284） | NAB · UCR · SMAP · MSL · SWaT · SMD · PSM | USAD · GDN · OmniAnomaly · MSCRED · MTAD-GAT · LSTM-NDT | F1 最高 +17%、训练时间 −99%（逐方法表格未能完整解析） |
| B11 | Iliopoulos et al., Anomaly detection in MTS using ensembles | IEEE BigDataService 2023 | `10.1109/BigDataService58306.2023.00007`（arXiv:2308.03171） | **SKAB** | ConvAE · LSTM-AE · Feature Bagging · FB+Nested PCA · Stacking+LR | **F1/AUC**：stacking 半监督 0.85/0.88；ConvAE FB+NestedRot 0.7873/0.8315；ConvAE 朴素 0.7622/0.8117 |
| B12 | HiSTAR, Hierarchical spatial-temporal graph for robust multivariate industrial AD | IEEE TII 2023 | `10.1109/tii.2022.3216006` | 三个工业案例（名称未核实） | 未核实 | 未核实 |
| B13 | He & Shen, Individual generalization framework … more reasonable FD benchmark | Computers in Industry 2025 | `10.1016/j.compind.2025.104359` | 未核实 | 未核实 | 提出"独立样本泛化"协议，可作为我们的划分依据 |
| B14 | FaultExplainer（前序调研已收录） | C&CE 2025 | `github.com/li-group/FaultExplainer` | TEP 15 个有记载根因的故障 | GPT-4o 7/11 · o1-preview 9/11（含根因清单提示） | 通用推理 8/11"正确或相关"；**样本量小、教科书记忆污染**是它的两处软肋 |
| B15 | Pinet et al., Anomalies in MTS benchmarks are mostly univariate | arXiv 2026 | `arXiv:2606.02670` | 8 个公开 MTSAD 基准 | 元分析 | **重要警示**：跨通道断裂分析——选基准时必须报告通道耦合度 |

### 2.3 baseline 选择（我们的对比阵容）

| 层 | 对比对象 | 为什么选它 |
|---|---|---|
| LLM 直接推理（主对手） | FaultExplainer 式单轮 prompt（GPT-4o / o1-preview 数字取自 B14） | 同任务（TEP 根因）、同数据，直接可比 |
| 传统 FDD 检测 | PCA + T²/Q（B5）、MLP/GRU/TCN（B7） | 论文数字明确、覆盖统计与深度两族 |
| 深度异常检测 | BeatGAN / TCN-S2S-AE（B8，TEP）、Stacking 集成（B11，SKAB） | F1/AUC 标杆 |
| 轴承诊断 | WDCNN / RF（B1，CWRU/Paderborn，泄漏受控协议） | 唯一给出"泄漏受控"数字，避免被审稿人打 |
| 自身消融 | 本系统 × {有/无本体复用} × {有/无 E0-E8 增强} × {omp / claude / mock 引擎} | 证明增益来自方法而非模型 |

---

## 3. 数据集清单与获取状态

| 数据集 | 角色 | 规模 | 获取方式 | 状态 |
|---|---|---|---|---|
| **TEP**（Braatz/Rieth 切片） | 主战场（过程故障根因） | 52 列 × 20 故障 | `data/benchmark/prepared/tep/` | ✅ 已备（2.9 MB） |
| **SKAB** | 真实试验台、多传感器、含控制组 | 34 CSV / 8 传感器 / 1 Hz | GitHub `waico/SKAB` → `prepared/skab/` | ✅ 已备（4.1 MB） |
| **IndPenSim** | 批过程泛化（青霉素发酵） | 100 批 | Mendeley → `prepared/indpensim*` | ✅ 已备（19.7 MB） |
| **SECOM** | 半导体过程、强不平衡、591 特征 | 1567×591 | UCI `archive.ics.uci.edu/static/public/179/secom.zip` | ⬇️ 自动下载 |
| **C-MAPSS** | 涡扇退化（RUL 家族） | 4 子集 | NASA PCoE S3 | ⬇️ 自动下载（~60 MB） |
| **Paderborn KAt** | 轴承真实损伤（B1 使用） | K001/K002/KA04/KA15 | `groups.uni-paderborn.de/kat/BearingDataCenter/*.rar` | ⬇️ 自动下载 + bsdtar 解包 |
| **FEMTO/PRONOSTIA** | 轴承全寿命（run-to-failure） | 17 轴承 | NASA PCoE S3 | ⬇️ `--include-large`（~1.6 GB） |
| **CWRU** | 轴承诊断最常引基准 | 12 kHz .mat | 官网为下载表单门禁 | ⚠️ **手工步骤**（见 §5 已知缺口） |
| SWaT | ICS 异常检测 | SCADA | 仅申请制（NDA） | ⛔ 不可自动获取，报告中声明 |
| SMD/SMAP/MSL/PSM | TranAD 家族（无监督 AD） | 大 | 公开镜像分散 | ⏸ 可选（优先级低于本系统强项） |

数据清单指纹：`results/benchmark/dataset_manifest.json`（路径 + sha256 + 行列数）；新增下载记录：`data/benchmark/downloads.lock.json`。

---

## 4. 评估协议（可复现的关键）

### 4.1 任务定义

- **主任务（根因诊断）**：给一个含故障的 run（或控制组），系统需输出 `diagnosis.json` 的 `root_causes[0]`（Top-1）与候选集（Top-k），附带置信度与证据级别。
- **子任务 A（异常检出）**：控制组上不得报出确定性故障（假阳性），故障组上必须检出（漏报）。
- **子任务 B（校准）**：`confidence` 不得在证据不足时越级（overconfident 计数）。

### 4.2 案例集划分（防泄漏，遵循 B1/B2/B13）

1. **按实体划分，绝不按片段随机划分**：同一实验批次/同一轴承/同一故障 run 只出现在一个 split。
2. **控制组与故障组配对**：每个数据集 ≥1 个正常控制 case，用于假阳性度量。
3. **多重复**：每 case 重复 R 次（tier 配置），报 **均值 ± 标准差**；关键差异用配对检验。
4. **陌生故障**：TEP 用非教科书扰动组合（如"阀门部分卡涩 + 进料成分漂移"）单列一组，规避预训练记忆污染（直接针对 B14 的软肋）。

### 4.3 指标定义（本项目实现于 `scripts/benchmark/aggregate.mjs`）

| 指标 | 定义 | 对标文献 |
|---|---|---|
| `top1` | Top-1 根因命中率（关键词/机理双判定） | B7 准确率、B14 正确率 |
| `topk` | Top-k 命中率（k=3，含 COMPETING_SET 中的正确项） | B14"正确或相关" |
| `CDR` | Correct Diagnosis Rate = Top-1 且 `DETERMINED` | FDD 社区标准（FDDBenchmark） |
| `calibrated` / `overconfident` | 置信度与证据一致性 | LLM 论文增量维度（传统 FDD 没有） |
| `control_pass` / `false_alarms` | 控制组通过率 / 误报数 | B5 ARL 的简化对应 |
| `judge_score` | 管线质量门得分（10 项） | 我们的执行可信度证据 |
| `evidence_traceability` | 结论可回溯到 L1-L7 证据的比例 | 增量维度 |

### 4.4 与论文数字的**双口径**对照（评审必读）

- **口径 A（同任务直比）**：TEP 根因任务 vs B14（FaultExplainer，11 故障）；SKAB 检出 vs B11（F1/AUC）；两个口径都落在**"故障级"**而非"样本级"。
- **口径 B（跨任务参照）**：逐样本检测类数字（B7/B8/B10）与我们不同任务，仅作**参照量级**引用，不宣称胜出——这正是 §2.2 的 B15 警示所要求的诚实性。
- 所有对比表标注：数据集版本、划分方式、是否泄漏受控、指标是否阈值化。

---

## 5. 已知缺口（诚实声明，不进结论）

1. **CWRU 自动获取不可行**：官网为下载表单门禁（自动抓取 404/表单）。脚本登记为 `manual` 步骤并给出落地页；补齐前，轴承轨以 **Paderborn + FEMTO** 为准（两者均已在 B1 等论文中使用）。
2. **AEI 实验细节未核实**（A2-A7）：Elsevier 403。已在表中显式标注，**不得**在论文中引用未核实数字。
3. **TEP 扩展版（28 类故障 × 100 次）**：Harvard Dataverse 自动抓取被 202 拦截，当前使用经典 20 故障切片；扩展版需手工下载（已列入 plan 的 P1 动作）。
4. **SWaT**：仅申请制，本轮不纳入。
5. **FEMTO zip 体积 1.6 GB**：默认不下载（`--include-large` 开启），避免 CI/本地带宽消耗。

---

## 6. 复现入口

```bash
# 1) 取数据（含 URL/主机安全校验）
node scripts/benchmark/download-datasets.mjs --list
node scripts/benchmark/download-datasets.mjs --only secom,cmapss,paderborn

# 2) 数据指纹
node scripts/benchmark/make_dataset_manifest.mjs

# 3) 跑分层案例（详见 .claude/skills/industrial-benchmark-runner/）
node .claude/skills/industrial-benchmark-runner/scripts/run-tier.mjs --tier 0

# 4) 汇总指标 + 生成报告
node scripts/benchmark/aggregate.mjs --tier-file scripts/benchmark/cases/tier0_smoke.json

# 5) 复现性校验（指纹 + 门禁）
node .claude/skills/industrial-benchmark-runner/scripts/verify-repro.mjs
```
