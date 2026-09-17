# paper/reference — 对标文献库

为 IDD 论文（*Trustworthy agentic diagnosis for industrial processes*）收集的近期对标文献。
检索日期：**2026-09-16**。检索源：arXiv API、Crossref（AEI / IEEE-TII / IEEE-TIM / RESS / JMS / IEEE-TASE）、
OpenAlex、Semantic Scholar、Unpaywall、Elsevier 期刊 RSS。

---

## 1. 已下载（开放获取 PDF，24 篇）

全部来自 arXiv（arXiv 许可；每篇 PDF 内附原始许可）。文件名格式
`arXiv_<id>_<短标题>.pdf`。

| # | arXiv | 日期 | 标题 | 与 IDD 的关系 |
|:--|:--|:--|:--|:--|
| 1 | 2607.22385 | 2026-07-24 | Agentic Root Cause Analysis through Evidence-Grounded Reasoning (**AgentRCA**, Wei & Fink, EPFL) | **最接近**：零样本 agentic RCA + 证据接地 + 竞争假设 + TEP/多相流 |
| 2 | 2608.24570 | 2026-08-25 | EviDx: Evidence-Aware Active Diagnosis with Scaffolded LLM Agents | 证据感知主动诊断；不确定性驱动的**终止判据**（对应 IDD 三态裁决）|
| 3 | 2608.27182 | 2026-08-27 | TraceBench: Controlled Evaluation of LLM Agents for Time-Series Root-Cause Attribution | 时序 RCA agent 的**受控基准**（对应 IDD 评测契约 C1–C5）|
| 4 | 2608.25661 | 2026-08-26 | From General Agents to RCA Experts: A Self-Evolving Harness for RCA (**OpsHarness**, ByteDance/CUHK) | "harness"即外层适配层；自演化经验积累（对应 IDD 本体资产库复用/知识复利）|
| 5 | 2608.21412 | 2026-08-11 | The Abstention Protocol: RCA for Clos Fabrics (**CORESEC**, Microsoft) | **弃权代数（abstention algebra）**：证据模糊时确定性弃权（对应 IDD needs_data / competing_set）|
| 6 | 2508.11995 | 2025-08-16 | AgentCDM: Enhancing Multi-Agent Collaborative Decision-Making via **ACH**-Inspired Structured Reasoning | 直接沿用 ACH（竞争假设分析）——IDD 竞争假设协议的**思想同源**工作 |
| 7 | 2510.03815 | 2025-10-04 | A Trustworthy Industrial Fault Diagnosis Architecture Integrating Probabilistic Models and LLMs (**HCAA**) | "可信"工业诊断：贝叶斯网络 + LLM 仲裁 + 置信度校准(ECE)/风险评估 |
| 8 | 2607.22797 | 2026-07-24 | Physically Verifiable Evidence and LLM-Based Reporting for Bearing Fault Diagnosis (DENet, NWPU) | **物理可验证证据**记录 + LLM 报告；与 AEI 105205 **同一团队**，可作其代读本 |
| 9 | 2603.08048 | 2026-03-09 | S2S-FDD: Bridging Industrial Time Series and Natural Language for Explainable Zero-shot Fault Diagnosis | 信号→语义算子 + 多轮树状诊断 + 动态追加信道查询 |
| 10 | 2505.02076 | 2025-05-04 | Leveraging LLM Agents and Digital Twins for Fault Handling in **Process Plants** | 过程工厂故障处置闭环（LLM agent + 数字孪生）|
| 11 | 2606.04599 | 2026-06-03 | Plan First, Judge Later: A **DMAIC**-Inspired Agentic System for Industrial Anomaly Detection | SOP 前置 + 判决器模型；"先规划后判"对应 IDD Judge 门 |
| 12 | 2607.05805 | 2026-07-07 | Onnes: A Physics-Grounded Multi-Agent LLM Simulator for Cryogenic Fault Diagnosis | 物理接地数字孪生 + 零样本 agent 面板 vs 监督基线**头对头对照** |
| 13 | 2609.02805 | 2026-09-02 | LLMs for **Telecom** RCA: A Structured Reasoning Framework for Evidence-Grounded Diagnosis | 证据接地结构化推理 + 可验证推理（跨域同构）|
| 14 | 2605.02592 | 2026-05-04 | Foundation-Model-Based Agents in Industrial Automation: Purposes, Capabilities, Open Challenges | 领域综述（可作 related-work 定位锚点）|
| 15 | 2604.09889 | 2026-04-10 | In-situ process monitoring for defect detection in wire-arc AM: an agentic AI approach | 制造过程 agentic 监测（非 RCA）|
| 16 | 2605.03328 | 2026-05-05 | LLM-ADAM: A Generalizable LLM Agent Framework for Pre-Print Anomaly Detection in AM | 制造异常检测 agent |
| 17 | 2508.05503 | 2025-08-07 | AutoIAD: Manager-Driven Multi-Agent Collaboration for Automated Industrial Anomaly Detection | 管理器驱动的多 agent 流水线（对应 IDD 主编排）|
| 18 | 2509.23113 | 2025-09-27 | Exploring LLM-based Frameworks for Fault Diagnosis (Hitachi) | 单 LLM vs 多 LLM × 输入表示**消融**（对应 IDD 模型受控消融）|
| 19 | 2402.06695 | 2024-02-08 | Integrating LLMs for Explainable Fault Diagnosis in Complex Systems (Argonne) | 模型化诊断(PRO-AID, 核工程) + LLM 解释层 |
| 20 | 2511.03075 | 2025-11-04 | A Collaborative Reasoning Framework for Anomaly Diagnostics in Underwater Robotics (**AURA**) | LLM + 数字孪生 + **人在回路**；诊断回流为参考样本 |
| 21 | 2412.14492 | 2024-12-19 | FaultExplainer: Leveraging LLMs for Interpretable Fault Detection and Diagnosis | IDD 论文中的**主要对照基线**（TEP，per-fault baseline）|
| 22 | 2310.16340 | 2023-10-25 | RCAgent: Cloud RCA by Autonomous Agents with Tool-Augmented LLMs | agentic RCA 的早期范式（云运维域）|
| 23 | 2609.02649 | 2026-09-02 | Loom: Weaving Diagnostic Strands into Free-Text Consensus via Embedding-Space Reweighting | 多诊断线索在嵌入空间加权**收敛为共识**（对应 IDD 竞争假设→单一裁决）|
| 24 | 2606.00582 | 2026-05-30 | PropLLM: Propagation-Aware Scene Reconstruction for **Network Fault Diagnosis** | 传播感知的场景重建式故障诊断（跨域同构）|

---

## 2. 未能下载：期刊闭源候选（登记在案）

以下为 AEI / IEEE-TII / IEEE-TASE / RESS / JMS 上的近期强相关论文。经 Crossref + Unpaywall
逐篇核验均为 **closed access，无任何合法的 OA 副本**（Unpaywall `is_oa=False`，`oa_locations` 为空），
ScienceDirect / IEEE Xplore 对自动化访问返回 403 反爬页，故未下载。**元数据与作者已核验保留于此**，
请通过机构订阅获取原文。

| DOI | 期刊 | 在线日期 | 标题 | 与 IDD 的关系 |
|:--|:--|:--|:--|:--|
| [10.1016/j.aei.2026.105205](https://doi.org/10.1016/j.aei.2026.105205) | **Advanced Engineering Informatics** (Vol.77 Pt.1, 2027-01) | 2026-09-04 | **A trustworthy agentic AI framework for auditable label-free machinery fault diagnosis in safety-critical engineering systems**<br>Yuntong Chen, Binhao Liu, Yingqi Li, Ziang Wang, Liping Ma, Jianyu Liu, Xitian Tian, Lijiang Huang (NWPU) | ⚠ **标题层面最高重合度**："trustworthy agentic" + "auditable" + "fault diagnosis"；但对象是**机械（旋转设备）**、且是 *label-free*（免故障标签），非过程机理 RCA |
| [10.1016/j.aei.2026.105198](https://doi.org/10.1016/j.aei.2026.105198) | **Advanced Engineering Informatics** (Vol.77 Pt.1, 2027-01) | 2026-09-03 | Semantic-guided label-free multimodal fault diagnosis bridging time-series and textual data with language models<br>Yi Ding, Carman K.M. Lee, Xingchen Liu, Qiuzhuang Sun | 语义引导、免标签、时序+文本多模态 FDD |
| [10.1016/j.aei.2026.105181](https://doi.org/10.1016/j.aei.2026.105181) | Advanced Engineering Informatics | 2026-09-01 | A Physics-Informed Mahalanobis Informatics Framework for multi-sensor robust fault diagnosis with feature-level uncertainty awareness | 物理约束 + 特征级不确定性（IDD 的物理核验/门传播对照）|
| [10.1016/j.aei.2026.105192](https://doi.org/10.1016/j.aei.2026.105192) | Advanced Engineering Informatics | 2026-09-04 | Agentic AI for dynamic Aging & Test sampling optimization and High-Performance defect detection in TFT-LCD Industry | 工业 agentic AI（检测/抽样，非 RCA）|
| [10.1016/j.aei.2026.105056](https://doi.org/10.1016/j.aei.2026.105056) | Advanced Engineering Informatics | 2026-11 | Evidence-based Bayesian neural network for uncertainty quantification of industrial robots | 证据式不确定性量化 |
| [10.1109/tii.2026.3669353](https://doi.org/10.1109/tii.2026.3669353) | **IEEE TII** | 2026-03-18 | Zero-Shot Fault Diagnosis via LLM-Guided Complexity-Aware Fuzzy Boundary Learning | LLM 引导零样本 FDD（属性文本化 + 原型对齐），非机理 RCA |
| [10.1109/tii.2026.3660116](https://doi.org/10.1109/tii.2026.3660116) | **IEEE TII** | 2026-02-23 | CoMA-IKG: LLM-Driven Multiagent Framework for Automated Construction of Industrial Knowledge Graph | 多 agent 工业知识图谱构建（对应 IDD 本体层）|
| [10.1109/tii.2026.3678237](https://doi.org/10.1109/tii.2026.3678237) | **IEEE TII** | 2026-07 | WeldLLM: A Multimodal Framework for Welding Defect Detection and Automated Diagnostic Reasoning | 多模态诊断推理（焊接缺陷域）|
| [10.1109/tii.2026.3692514](https://doi.org/10.1109/tii.2026.3692514) | **IEEE TII** | 2026-09 | From Signals to Semantics: A Multilabel Power Quality Disturbance Identification Framework Using LLMs | 信号→语义（电能质量域）|
| [10.1109/tase.2026.3710929](https://doi.org/10.1109/tase.2026.3710929) | IEEE TASE | 2026 | Co-Integration Enhanced Causal Inference for Dual-Temporal Root Cause Diagnosis in Non-Stationary Industrial Processes | **因果推断式根因定位**（TEP + 多相流）；IDD 反伪相关过滤器的方法论对照 |
| [10.1016/j.ress.2026.113057](https://doi.org/10.1016/j.ress.2026.113057) | Reliability Eng. & System Safety | 2026-06-20 | A retrieval-augmented, domain-intelligent agentic framework for reliable decision support in safety-critical nuclear engineering (**RADIANT-LLM**) | 检索增强 + agentic + 可追溯性 + 幻觉抑制（安全关键域）|
| [10.1016/j.ress.2026.112932](https://doi.org/10.1016/j.ress.2026.112932) | Reliability Eng. & System Safety | 2026-06-11 | DI-AGENT: A domain-knowledge informed LLM framework for unified bearing health management | 领域知识注入 LLM（轴承健康管理）|
| [10.1016/j.jmsy.2026.08.012](https://doi.org/10.1016/j.jmsy.2026.08.012) | Journal of Manufacturing Systems | 2026-09-14 | Rec-PdM: Decision-calibrated recursive multi-agent systems for uncertainty-aware prescriptive maintenance | **决策校准** + 不确定性感知 + 多 agent 信念/溯源 |

> 说明：`10.1016/j.ress.2026.113057`（RADIANT-LLM）与 `10.1016/j.jmsy.2026.08.012`（Rec-PdM）
> 在 OpenAlex 中标为 OA，但 Unpaywall 查无实际 OA 落点，出版商页面仍受反爬保护——因此同样未下载。

---

## 3. 获取方式与复现

- arXiv PDF：`https://arxiv.org/pdf/<arXiv-id>`
- 元数据核验：Crossref `https://api.crossref.org/works/<DOI>`；
  Unpaywall `https://api.unpaywall.org/v2/<DOI>?email=...`；
  OpenAlex `https://api.openalex.org/works/doi:<DOI>`
- AEI 新目 RSS：`https://rss.sciencedirect.com/publication/science/14740346`

注：本机 HTTPS 出口经代理 `127.0.0.1:7890` 时为 TLS EOF，需绕开代理由直连访问上述公开 API。
