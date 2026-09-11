# 数据集与实验设计专项调研 —— 对标已发表论文怎么写 Exp

> 2026-09-09 · 聚焦最关键问题：**已发表论文的数据从哪来、实验怎么写、哪些数据集能直接喂给我们的诊断系统**
> 结论先行：**TEP（Rieth/Reinartz 版）+ SKAB 为主战场，IndPenSim + SWaT 做泛化，FailureSensorIQ 做直接数字对比**。所有主选数据集都是"时间戳 + 多传感器列"的 CSV/parquet，与系统输入格式零改造适配。

---

## 1. 对标论文的实验章节是怎么写的（逐篇拆解）

### 1.1 FaultExplainer（**Computers & Chemical Engineering**, 2025 —— TEP 上 LLM 诊断的唯一直接对手）

它的实验章节结构（可直接模仿并超越）：

| 要素 | 它怎么写的 |
|---|---|
| 数据 | TEP 21 个预置故障，其中 **15 个有文献记载的根因**（引 Downs & Vogel 1993 + Chiang et al. 2001 教科书）；闭环仿真、每个故障一个 run（960 行 × 52 列） |
| 范围收缩 | 诚实声明只用 **PCA 可检测的 11 个故障**做定量评测 |
| 实验设计 | **两组对照**：Prompt A"根因清单包含在提示里" vs Prompt B"通用推理（模拟未见故障）" |
| 定量结果 | GPT-4o 7/11 正确，o1-preview 9/11；通用推理下 8/11"正确或相关" |
| 定性案例 | 各给 1 个成功案例（Fault 7）+ 2 个失败案例（Fault 10/13），展示幻觉 |
| 开源 | github.com/li-group/FaultExplainer |

**审稿人指出的两个死穴（我们的机会）**：
1. **预训练记忆污染**：TEP 15 个故障的根因写在教科书里，GPT-4o 大概率背过——"去掉根因清单"不等于"未见故障"。
2. **样本量太小**：11 个故障、每个 1 个 run，无统计显著性。

**我们的超越设计**（写进论文就是两个审稿人无法拒绝的贡献）：
- 用 **Reinartz 扩展版 TEP（28 类故障，每类 100 次仿真）**，把评测样本从 11 → 100+，可报均值±标准差与显著性检验；
- **参数化"陌生故障"**：用 TEP 仿真器生成教科书里不存在的扰动组合（如"阀门 X 部分卡涩 + 进料成分漂移"），从根上规避记忆污染；
- 报告 **CDR（Correct Diagnosis Rate，FDDBenchmark 标准指标）+ Top-1/Top-3 RCA 命中率**，与 FDD 社区指标体系对齐。

### 1.2 Gong et al.（JII 2026，多代理 LLM 诊断最近邻）

实验写法：FailureSensorIQ MCQA 上"框架开启前后"对比（Llama3.1-8B：36.5%→54.6%）+ 路由机制消融 + 准确率-成本权衡曲线。**全部数字来自现成问答基准，没有真实时序数据**——这就是它的软肋，也是我们"真实数据端到端"叙事的立足点。

### 1.3 FDD 社区的标准指标体系（用它们的词，审稿人才认）

FDDBenchmark（AIRI-Institute，pip 可装）定义了三组指标，建议全文采用：
- **诊断类**：`CDR`（正确诊断率）、`TPR_i / FPR_i`（分故障检测率/误报率）
- **检测类**：Detection TPR/FPR、`ADD`（平均检测延迟）
- 我们额外增加 LLM 特有指标：**Top-1/Top-3 RCA 命中率、证据可追溯率、假相关拦截率、ECE 置信度校准**（这几项 FDD 传统文献没有——是 LLM 论文的增量维度）。

---

## 2. 可发表级数据集清单（按适配度排序）

### ★★★ TEP 家族 —— 主战场，零改造适配

| 版本 | 来源 | 规模 | 真值 | 许可 |
|---|---|---|---|---|
| **Rieth TEP** | Harvard Dataverse `doi:10.7910/DVN/6C3JR1`；HuggingFace `foundation-models/golden-batch-sentinel-data`（parquet 现成） | 52 变量 × 20 故障 × 21000 runs（1.84 GB）；small_tep 18.9 MB 可先跑通 | 20 类故障编号 + 15 类有教科书根因 | Public domain |
| **Reinartz TEP**（推荐主用） | MIT Braatz 组 links 页 | 52 变量 × **28 类故障** × 每类 100 次仿真（每次 2000 样本，3min 采样，前 30h 正常后 70h 故障） | 同上 + 扩展故障 | 公开 |
| 经典 Braatz 版 | github.com/camaramm/tennessee-eastman-profBraatz | d00…d21_te.dat（500/960×52） | 同上 | 公开 |

**适配方式**：每个故障 run 导出为一个 CSV（`timestamp + 52 列`）→ 正是系统 `POST /api/files/data/upload` 的标准输入；`user_question = "诊断本次异常的根本原因"`；ground truth = 故障编号对应的机理描述，LLM-as-judge + 关键词匹配双评。**系统唯一的适配工作是变量名列名映射（XMEAS_1 → 官方变量描述），可由 Step 2 本体层自动完成——这本身就是论文里 RAG/本体层的卖点实验。**

### ★★★ SKAB（Skoltech Anomaly Benchmark）—— 真实试验台、直接是 CSV

- 来源：github.com/hndrec/SKAB（GPL-3）或 Kaggle；**34 个带标签 CSV + 1 个无异常文件**，8 传感器（振动×2/电流/电压/压力/本体温度/流体温度/流量），1Hz，共 3.7 万行
- 真值：每文件一种**已知人为异常**（阀门部分关闭、转轴不平衡、电机功率下降、气蚀、流量扰动）——天然就是"根因标签"
- 适配度：**满分**。每个 CSV 直接上传即可诊断；规模小、成本低，可跑大量重复实验做统计检验；异常类型多样，适合验证 COMPETING_SET 的校准诚实性
- 已被多篇时序异常检测论文使用，引用无争议

### ★★ IndPenSim —— 真实工业级发酵批次（泛化性证据）

- 来源：Mendeley Data（CC BY 4.0）；HuggingFace golden-batch 仓库有 parquet 版
- 100 批次 × 37 变量（90 正常 / 10 故障），0.2h 采样，发表于 Comput. Chem. Eng. 2019
- 适配：批次数据转 CSV 后同样直连；用于证明"连续过程 → 批次过程"的通用性（AEI 喜欢跨场景验证）

### ★★ SWaT / WADI（新加坡 iTrust 水处理试验台）—— 36 类攻击 = 36 个已知根因

- 需填表申请（免费，学术常规流程）；SWaT 51 传感器 11 天（7 正常+4 攻击），WADI 123 传感器 16 天 15 类攻击
- 优势：**真实物理试验台**（非仿真），攻击点文档即根因真值；大量顶刊论文用它，可信度高
- 劣势：申请有延迟（1-2 周），列为第二梯队

### ★ FailureSensorIQ（IBM，开源）—— 与 Gong (JII 2026) 的直接数字对比

- github.com/IBM/FailureSensorIQ + HF leaderboard；MCQA 问答，不需要改系统——把系统管线首尾接上 MCQA 适配器即可，或直接引用系统内 LLM 的分数做"组件能力"佐证

### 其他备用：MetroPT-3（UCI，轨道交通空压机 1.5M 行 15 通道，故障模式有文档）、Damadics（阀门执行器 19 类故障，工业现场）、Paderborn 轴承（FDDBenchmark 内置 lessmeier_bearing）

---

## 3. 推荐的实验组合（兼顾成本、覆盖、审稿人偏好）

| 实验 | 数据集 | 规模 | 回答的问题 |
|---|---|---|---|
| **Exp-1 主结果：RCA 命中率** | Reinartz TEP（28 故障 × 抽 5 run = 140 runs） | 140 次完整诊断 | 全管线 vs 6 个基线的 Top-1/Top-3/CDR |
| **Exp-2 抗记忆"未见故障"** | TEP 仿真器自造扰动组合 + Rieth 未入选故障 | 30+ 场景 | 回应 FaultExplainer 被批的记忆污染问题 |
| **Exp-3 真实试验台泛化** | SKAB 全部 34 文件 | 34 次诊断 | 仿真→真实的迁移；报告分异常类型的命中率 |
| **Exp-4 批次过程泛化** | IndPenSim 10 故障批次 | 10 次诊断（+90 正常抽检误报率） | 跨过程形态通用性 + 误报率 |
| **Exp-5 反假相关压力集（自建，核心贡献）** | 基于 TEP/SKAB 注入混淆变量、Simpson 结构、时滞错位 | 每类 20 场景 | 拦截率：裸 LLM 预期 >40% 失败 vs 本管线 |
| **Exp-6 MCQA 对标** | FailureSensorIQ | 官方全集 | 与 Gong (JII 2026) 同表对比 |
| **Exp-7 消融 × 成本** | Exp-1 子集 | 40 runs | 去 Judge/审计/证据分级/RAG/反假相关；token 成本-精度帕累托 |

统计要求（FaultExplainer 被批的教训）：每组 ≥3 次重复、报 mean±std、McNemar 或 bootstrap 显著性检验、固定随机种子、开源全部 run 的审计轨迹。

---

## 4. 实验章节写作模板（模仿 FaultExplainer 表结构 + 补其短板）

```
5. Experimental Setup
  5.1 Datasets（表：数据集/变量数/故障数/真值来源/许可证 —— 一张表说服审稿人）
  5.2 Baselines（单 LLM / CoT / ReAct / AutoGen / FaultExplainer / PCA / XGBoost / LSTM）
  5.3 Metrics（CDR、Top-1/3、假相关拦截率、ECE、成本；引 FDDBenchmark 定义）
  5.4 Protocol（每 run 独立上传→全管线→结论解析→双评[LLM-judge+机理关键词]；3 次重复；显著性检验）

6. Results and Discussion
  6.1 Main results（Table: 主结果矩阵，含一个 X%→Y% 记忆点）
  6.2 Unseen-fault generalization（Exp-2，直接引用并回应 FaultExplainer 的局限）
  6.3 Real-testbed transfer（Exp-3/4，SKAB/IndPenSim 分类型命中率热力图）
  6.4 Anti-spurious stress test（Exp-5，本文独有，放三联图：时滞 CCF/Simpson/leave-one-out 拦截前后对比）
  6.5 Ablation & cost（消融表 + 帕累托曲线）
  6.6 Case study（一个完整 run 的证据链：假设→区分性证据→排除→结论 + 审计轨迹表）
```

**叙事主线（一句话）**：FaultExplainer 证明了 LLM 能"解释"TEP 故障但受限于 11 个样本和预训练记忆；Gong 证明了多代理能提升 MCQA 但没碰真实数据；**我们是第一个在多数据集、大样本、真值完备条件下，用质量门禁+证据分级把 LLM 诊断做成可审计工程的系统**。

---

## 5. 落地清单（W2-W3 具体动作）

1. `pip install fddbenchmark` 拿 rieth_tep 加载器 + CDR 评测器（或直接从 HF `golden-batch-sentinel-data` 下 parquet 转 CSV）
2. 写 `scripts/tep_export.mjs`：parquet → 单 run CSV（时间戳列 + 52 传感器列）→ 批量上传
3. 写 `scripts/eval_parse.mjs`：从 `04_diagnostics/diagnosis.json` 抽取结论 → 与故障真值表匹配（关键词+LLM-judge 双评）→ 汇总 CDR/Top-k
4. SKAB：直接 clone（CSV 现成）；IndPenSim：HF parquet 转 CSV
5. TEP 仿真器陌生扰动：用 Georgia Tech/Braatz Fortran 仿真器或现成 Python 重实现（github 有多个）生成 30 个组合故障
6. SWaT 申请表现在就提交（1-2 周审批）
