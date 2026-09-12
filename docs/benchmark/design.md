# Benchmark 设计依据 — 任务口径、指标与期刊 baseline 对标

> 折叠自原 `docs/benchmark-design.md` + `docs/benchmark-plan.md`（2026-09-12 收敛为 8 典型场景后更新）。
> 配套：[README.md](README.md)（入口）、[execution-guide.md](execution-guide.md)（执行）、[reproduction-guide.md](reproduction-guide.md)（复现）。

---

## 1. 为什么是"每 run 一个根因结论"口径

被评测系统输出的是**每个 run 一个根因结论**（`diagnosis.json` 的竞争性假设 +
三态结论 + 置信度），不是逐样本标签。因此对标采用**"每故障 run → 根因是否正确"**
的口径（与 FaultExplainer 等 RCA 文献一致），逐样本检测类指标（F1/ARL）只在
"是否检出异常"子任务上作量级参照，不直接横比。

## 2. 指标定义（实现于 `scripts/benchmark/aggregate.mjs`）

| 指标 | 定义 | 对标来源 |
|---|---|---|
| `top1` | Top-1 根因命中（独立评分器按机理关键词双判定） | FaultExplainer 正确率口径 |
| `topk` | Top-k 命中（k=3，含 COMPETING_SET 中正确项） | FaultExplainer"正确或相关" |
| `CDR` | Correct Diagnosis Rate = Top-1 且结论类型 `DETERMINED` | FDD 社区标准（FDDBenchmark） |
| `calibrated` / `overconfident` | 结论类型是否落在场景允许集内；DETERMINED 且判错 = 过度自信 | LLM 评测增量维度（传统 FDD 无） |
| `control_pass` / `false_alarms` | 对照组判"正常" / 对照组误报故障 | 检测类文献 ARL 的故障级简化对应 |
| `judge_score` | 管线内 judge 质量门 10 维评分（0-100） | 执行可信度证据 |
| 比例指标区间 | Wilson 95% CI（小样本诚实区间） | 统计规范 |

评分协议要点（详见 execution-guide §5）：

1. **真值隔离**：truth/关键词只在评分器使用的 case 文件中，brief 与管线输入不含真值；
2. **独立评分**：评分器只读管线输出文件 + truth，不读诊断 note；
3. **门禁前置**：仅当 `.pipeline_events.jsonl` 通过 `pipeline-log-check` 且
   `pipeline-finalize` overall=PASS 的 run 才计分（无执行证明的结论无效）；
4. **判别力自证**：阴性对照——向评分器注入"plausible-but-wrong"诊断必须被打叉
   （留痕 `experience/results/scorer-discrimination-test.json`）。

## 3. 场景集选择依据（8 典型场景）

- **三工艺域**：连续化工（TEP）、泵阀试验台（SKAB）、批式发酵（IndPenSim）——
  覆盖系统的三类本体/机理域，避免单域过拟合；
- **每组对照**：每个数据集配 1 个正常批次作对照，度量误报；
- **难度分层**：含文献公认难检故障 TEP IDV(3)（允许 NEEDS_DATA 三态出口）与
  故障类型不下发的隐蔽场景（SKAB other_13），检验"承认不可判别"的校准能力
  而非逼出过度自信结论；
- **防记忆污染**：SKAB other 组文件故障类型不在场景描述中披露；IndPenSim 的
  Fault reference 标注列被显式排除出证据（`exclude_cols`）；
- **规模声明**：8 场景为"可发表的最小可复现核"，Top-1 比例指标一律报 Wilson CI；
  扩量路线见 §7。

## 4. 期刊 baseline 对标表（可验证 DOI）

> 检索方式：Crossref/OpenAlex 核对书目 + doi.org 解析 + arXiv 全文核对实验细节。
> **透明度声明**：Elsevier 全文对自动抓取返回 403，凡未能读到实验章节的均标注
> **未核实**——不猜测数字。

### 4.1 目标期刊 AEI（Advanced Engineering Informatics）

| # | 论文 | 年份 | DOI | 数据集 | 与本基准的关系 |
|---|---|---|---|---|---|
| A1 | He et al., 可调制可微 STFT 轴承跨机迁移 | 2024 | `10.1016/j.aei.2024.102568` | 列车轴箱+台架 | 迁移诊断协议参照（数字未核实） |
| A3 | Liu et al., STACGG/EAGG 因果图根因定位 | 2025 | `10.1016/j.aei.2025.103765` | 时序工业过程 | **RCA 任务最同源，对标本体+因果层**（细节未核实） |
| A4 | Liu et al., 无标签故障诊断评估 | 2024 | `10.1016/j.aei.2024.102912` | — | "无标签评估"思路 ↔ 本基准的盲评协议 |
| A7 | Yue et al., 大群体因果知识图谱 RCA | 2023 | `10.1016/j.aei.2023.102057` | 过程工业 | 知识图谱式 RCA ↔ 本体层对标 |

### 4.2 其他优质期刊（含可复现数字的强对标）

| # | 论文 | 期刊/年 | DOI | 数据集 | 可核对数字 |
|---|---|---|---|---|---|
| B1 | Vieira et al., 更真实的轴承 FD 评测（泄漏受控） | MSSP 2026 | `10.1016/j.ymssp.2026.114640`（arXiv:2509.22267） | CWRU/Paderborn/OURED/HUST | Macro AUROC：UORED WDCNN 93.12±4.26%；**分割泄漏可虚高 +12.6%** |
| B2 | Hendriks et al., CWRU 基准批评 | MSSP 2022 | `10.1016/j.ymssp.2021.108732` | CWRU | 划分泄漏奠基文献 |
| B5 | Reinartz et al., 扩展 TEP 数据集 | C&CE 2021 | `10.1016/j.compchemeng.2021.107281` | TEP 扩展 | 指标=ARL；数据 Harvard Dataverse `10.7910/DVN/6C3JR1` |
| B7 | Pozdnyakov et al., 对抗攻击 TEP 基准 | IEEE OJIES 2024 | `10.1109/OJIES.2024.3401396` | TEP | 干净准确率 MLP 0.8873 / GRU 0.9067 / TCN 0.8985 |
| B8 | Hartung et al., TEP 深度异常检测 | arXiv 2023 | `arXiv:2303.05904` | TEP | F1：BeatGAN 0.9699；TCN-S2S-AE 0.9632 |
| B11 | Iliopoulos et al., MTS 异常检测集成 | IEEE BigDataService 2023 | `10.1109/BigDataService58306.2023.00007` | **SKAB** | F1/AUC：stacking 0.85/0.88；ConvAE 0.7622/0.8117 |
| B14 | FaultExplainer | C&CE 2025 | `github.com/li-group/FaultExplainer` | TEP 根因 | GPT-4o 7/11、o1-preview 9/11（**prompt 含根因清单**）；通用推理 8/11"正确或相关" |
| B15 | Pinet et al., MTS 基准异常多为单变量 | arXiv 2026 | `arXiv:2606.02670` | 8 个 MTSAD 基准 | 警示：跨通道断裂——必须报告通道耦合度 |

### 4.3 双口径对照（评审必读的诚实性约定）

- **口径 A（同任务直比）**：TEP 根因任务 vs FaultExplainer（B14）——同为
  "每故障 run 一个根因结论"，可比；但 FaultExplainer 的 prompt 内含根因候选清单，
  IDD 不提供候选，对比时必须标注该差异。
- **口径 B（跨任务量级参照）**：逐样本检测/分类数字（B7/B8/B11）任务不同，
  仅作量级参照，不宣称胜出（落实 B15 的基准诚实性警示）。
- 所有对比表标注：数据集版本、划分方式、是否泄漏受控、指标是否阈值化。

## 5. 已知缺口（诚实声明，不进结论）

1. **CWRU 自动获取不可行**：官网下载表单门禁，脚本登记为 `manual`（`data/benchmark/downloads.lock.json`）。
2. **AEI 实验细节未核实**（A1/A3/A4/A7）：Elsevier 403，论文中不引用未核实数字。
3. **TEP 扩展版（Rieth 28 类 × 100 次）**：Harvard Dataverse 自动抓取被拦，当前用经典 20 故障切片；扩展需手工下载。
4. **SWaT**：仅申请制（NDA），不纳入。
5. **FEMTO 1.6 GB**：默认不下载（`download-datasets.mjs --include-large` 可选）。

## 6. 数据集清单与获取状态

| 数据集 | 角色 | 获取方式 | 状态 |
|---|---|---|---|
| TEP（Braatz 切片） | 主战场（连续化工根因） | `data/benchmark/prepared/tep/` | ✅ 已备（sha256 入 manifest） |
| SKAB | 真实试验台 + 控制组 | GitHub `waico/SKAB` → `prepared/skab/` | ✅ 已备 |
| IndPenSim | 批过程泛化 | Mendeley → `prepared/indpensim*/` | ✅ 已备 |
| SECOM / C-MAPSS / Paderborn / FEMTO | 扩量储备（§7 P2） | `scripts/benchmark/download-datasets.mjs` | ⬇️ 脚本可下载 |

数据清单指纹：`results/benchmark/dataset_manifest.json`（路径 + sha256），
复现门禁会逐一重哈希校验。

## 7. 路线图（8 场景之后的增量，P 序）

| 阶段 | 内容 | 验收 |
|---|---|---|
| **P2 · 扩量** | TEP 全 20 类（Rieth 扩展手工下载后接入）；每数据集扩至 6-10 场景；SECOM/C-MAPSS/Paderborn 切片接入 | ≥36 场景、每域 ≥6 故障 + 对照；Wilson CI 显著不含 50% |
| **P3 · 消融** | `{有/无本体复用} × {有/无反假相关校验} × {有/无门禁修复环}` 三组消融；`{omp/claude/mock}` 引擎维度 | 每消融臂 ≥12 grading，差异有方向性解释 |
| **P4 · 重复与检验** | 关键 case 重复 R 次报均值±标准差 + 配对检验；陌生故障组（教科书无记载扰动）单列 | 统计显著性表 + 负例分析 |
| **P5 · 盲测** | 由无记忆新会话 agent 按 reproduction-guide 盲诊协议独立执行全流程 | 独立第三方复现结果与本报告一致 |

## 8. 复现入口（详见 reproduction-guide.md）

```bash
node scripts/benchmark/run-benchmark.mjs        # 一键 S0-S6
node scripts/benchmark/run-tier.mjs status      # 分步查看场景状态
```
