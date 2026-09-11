# industrial-deep-diagnostic 投稿策划报告

> 生成日期：2026-09-09 · 基于对 `v4-AgentWorkShopIntegrate` 分支代码全量核查 + 相似文献检索
> 结论先行：**主投《Advanced Engineering Informatics》(AEI)，备选《Journal of Industrial Information Integration》(JII)**。当前系统的差异化卖点（质量门禁 + 证据分级 + 反假相关）在已发表文献中尚属空白，但投稿前必须补齐 benchmark 与对比实验，并修复已知的可复现性缺口。

---

## 1. Skill 诊断执行完整流程核查结论

### 1.1 流程全貌（已逐项核对 SKILL.md 与代码）

```
输入(CSV/Excel/JSON) → Step 0/1 接入与清单 (main-agent, CP-1)
  → Step 0.5 自适应预处理（数据源无关性门控）
  → Step 2/2.5 本体构建 (context-builder + RAG 深度理解, CP-2/3；‖ 2P 数据剖析可选并行)
  → Step 3/3.3 统计分析 + VLM 视觉分析 (data-processor/vlm-visual-analyzer, CP-4)
  → Step 4 竞争性假设根因诊断 (diagnostician, CP-5)
  → Step 5a Judge 十维质量门 (∥) Step 5b 物理预审计 —— 管线唯一并行对
  → Step 6 金字塔报告 (reporter, CP-7)
  → Step 7 物理终审 ENDORSED (report-reviewer, CP-8)
  → Step 8/8.5 HTML 可视化 + 审校 (CP-9) → Step 9 证据闭环
  → Step 10 E0-E8 增强分析（零 LLM 脚本链，条件触发）
```

核心机制：**竞争性假设协议**（DETERMINED / COMPETING_SET / NEEDS_DATA 三态结论）、**证据等级 L1-L7**（结论受限最低证据等级）、**反假相关四条件**（时间先后+统计显著+物理机制+无矛盾）、**修复循环**（Judge<90→重诊断≤3；终审未过→全链重跑≤2；全局重诊断≤5，反振荡→置信度封顶≤50）、**CP-1~CP-9 检查点**、**HITL 人审接入**。

### 1.2 可发表性视角的三个缺口（投稿前必须修复）

| 缺口 | 现状 | 对论文的影响 |
|---|---|---|
| Step 5b 事件上报缺 `audit_mode:pre_report` | 被 `PIPELINE_ORDER_VIOLATION` 拦截 | 论文声称的 5a/5b 并行设计无法复现 → 审稿人要求开源复现时暴露 |
| 自愈循环/CP-1~9 大部分为文档层 | best-of-3、振荡判定、置信度封顶无独立脚本强制 | "self-healing" 若写进贡献点必须可量化验证，否则删减表述 |
| 无公开 benchmark 评测 | 只有内部案例 | **这是被拒的头号原因**，见第 5 节实验方案 |

---

## 2. 竞争格局：五篇最接近的对标论文

| # | 论文 | 期刊/年份 | 做了什么 | 与本文差异 |
|---|---|---|---|---|
| 1 | Gong et al., *Harnessing collective intelligence of multi-agent LLM systems for sensor failure reasoning* | **JII** 49:101012, 2026 (IF≈10) | 多代理 LLM 传感器失效推理；难度感知路由（简单直答/复杂辩论共识）；**FailureSensorIQ benchmark** 上 Llama3.1-8B 36.5%→54.6% | 最接近的对标。但它只在 **MCQA 问答集**上评测，无真实时序数据管线、无质量门禁、无物理审计。我们强在"真实数据端到端 + 可验证证据链" |
| 2 | Liu et al., *Machine tool fault reasoning… data-knowledge empowered LLMs + AR* | **AEI** 66:103460, 2025 | 场景图 + Llama3 提示微调 + 多代理协同故障检测 + AR 维修引导 | AEI 收这类"系统+案例"文章的实证。它面向机床/维修推荐，我们面向过程工业根因分析，赛道不撞车 |
| 3 | *FaultExplainer* | arXiv 2024.12 | LLM + PCA 故障检测 + TEP 上生成可解释故障说明；指出 LLM 幻觉局限 | **最直接的 TEP 上 LLM 基线**。它只做"解释"，无诊断管线、无质量门；可作为我们 TEP 实验的直接对比方法 |
| 4 | *Agentic AI for Safety-Aware Process Monitoring and FDD: A Review* | MDPI Processes, 2025 | 综述：过程工业 agentic FDD 处于早期，LLM/多代理证据稀缺（2024 前几乎为零） | **这是我们的"时机论证"金句来源**：综述明确指出该方向是空白，支持我们论文的 novelty 声明 |
| 5 | Constantinides et al., *FailureSensorIQ* | arXiv 2025 (IBM) | 工业资产失效模式 MCQA 基准 + 扰动/不确定性/复杂度分析 | 可直接用作我们实验的一个评测集（有 HF leaderboard，数字可比） |

**格局判断**：LLM/多代理工业诊断在 2024-2026 刚起步，"把 LLM 诊断变成**可验证、可审计、抗幻觉**的工程化管线"这一角度（质量门禁+证据分级+反假相关+自愈循环）**尚无发表论文覆盖**——这是本文最大的 novelty 空间。

---

## 3. 期刊/会议定位推荐

| 优先级 | 期刊 | IF(近似) | 匹配理由 | 风险 |
|---|---|---|---|---|
| ★ 主投 | **Advanced Engineering Informatics (AEI)** | ~8 | 2025 年刚发过同类型多代理 LLM 故障诊断（对标#2）；偏爱"信息系统架构 + 工业案例 + 工程可用性"；对本体/RAG/知识驱动叙事友好——正好是本文的 Step 2 本体层 | 需要 1-2 个真实工业案例 + 完整消融 |
| ★ 备选1 | **Journal of Industrial Information Integration (JII)** | ~10 | 最接近的对标#1 发在这里；如果 TEP benchmark 结果强、且补齐与 Gong 等人的直接对比，JII 更能体现"集成"卖点 | 竞争者同刊，必须正面回应其工作 |
| 备选2 | Journal of Manufacturing Systems (JMS) | ~12 | 若做出真实产线部署 + OEE/停机时间等业务指标 | 门槛最高，周期长 |
| 备选3 | Robotics & Computer-Integrated Manufacturing (RCIM) | ~9-10 | 偏制造执行场景 | 与本文"过程+机理"叙事稍偏 |
| 会议保底 | IEEE CASE / PHM Society / IEEE ICMLA | — | 快速占坑引用 | 非必要不走 |

> 与你三条投稿线的分工：**AgentWorkShop→IEEE TII**（数字孪生+Agent 主框架）、**本文→AEI**（工业诊断纵深）、**rag-knowledge→CIKM**（RAG 方法论）。三者互引形成体系，避免自我重复投稿。

---

## 4. 论文写作方案（按 AEI 惯例 IMRaD+，8-9 千词）

### 4.1 标题建议（三选一）
1. *Evidence-graded multi-agent diagnosis: a quality-gated LLM pipeline for trustworthy industrial root-cause analysis*
2. *From correlation to causation: an auditable multi-agent LLM pipeline for industrial root-cause diagnosis*
3. *Trustworthy agentic diagnosis for industrial processes: competitive-hypothesis reasoning with physical audit gates*（推荐，突出两个独有机制）

### 4.2 章节模板与页数分配

| 章节 | 内容要点 | 篇幅 |
|---|---|---|
| 1 Introduction | 三个痛点：①单 LLM 诊断幻觉/无结构（引 MDPI 综述）②传统 ML/DL 黑箱+重训练悖论（引 Gong 等的表述）③"相关性≠因果"在工业 RCA 中致命（本文反假相关动机）。贡献点 4 条 | 1.5 页 |
| 2 Related Work | 三条线：a) 数据驱动 FDD（PCA→DL→TEP 系列）；b) LLM 用于工业诊断（FaultExplainer、Gong、FailureSensorIQ）；c) 多代理编排框架（AutoGen/CrewAI 类，说明通用框架为何不满足工业可审计性） | 1 页 |
| 3 System Architecture | 分层叙事（与 drawio 五层架构图一致）：接入层→本体/RAG 层→分析层→诊断推理层→质量与审计层。**重点写三个独有机制**：竞争性假设协议、证据分级 L1-L7 与门禁传播、反假相关四条件（含 CCF 时滞补偿、Simpson 检验、leave-one-out 杠杆点、稳态过滤） | 2.5 页 |
| 4 Implementation | Skill/Agent 编排（14 agents, 18 skills）、双 harness、修复循环状态机、Web 平台与 HITL。放系统时序图 | 1 页 |
| 5 Experimental Setup | 三个 benchmark（第 5 节）+ 6 个 baseline + 指标定义 | 1 页 |
| 6 Results | 主结果表 + 消融表 + 成本/时延 + 案例研究（一个完整 run 的证据链展示，放审计轨迹截图/表格） | 2.5 页 |
| 7 Discussion & Limitations | 坦白：LLM 成本、5b 并行依赖 harness 能力、COMPETING_SET 场景的人工价值 | 0.5 页 |
| 8 Conclusion | — | 0.25 页 |

### 4.3 图表清单（AEI 偏好：架构图精、证据链实）
- Fig.1 系统五层架构（复用 drawio A3 横版）
- Fig.2 诊断管线流程（本报告上方流程图的英文版）
- Fig.3 反假相关机制示意（时滞 CCF + Simpson + leave-one-out 三联图）
- Fig.4 TEP 案例证据链（假设→区分性证据→排除→结论）
- Fig.5 消融柱状图；Fig.6 成本-精度帕累托曲线；Fig.7 HTML 报告截图（系统可用性证据）
- Table 1 与现有工作对比；Table 2 主结果；Table 3 消融；Table 4 成本/时延；Table 5 案例审计轨迹摘录

---

## 5. Benchmark 与实验设计（决定命中率的核心）

### 5.1 三个 benchmark + 一个压力测试集

| Benchmark | 用途 | 数据规模 | 可比对象 |
|---|---|---|---|
| **B1: Tennessee Eastman Process (TEP)** | 主战场：20 类故障的 RCA。_fault 真值已知，文献基线丰富 | riotee/rif 上面向 FDA 公开数据（500×52×20），抽 8-12 类可归因故障 | FaultExplainer(LLM)、PCA 贡献图、XGBoost/LSTM 分类器（只给类别不给根因，凸显 RCA 差异化） |
| **B2: FailureSensorIQ (IBM)** | 直接与 Gong et al. (JII 2026) 数字对比 | 官方 MCQA + HF leaderboard | 其论文数字：GPT-4o-mini、Llama3.1-8B 36.5%→54.6% |
| **B3: CWRU 轴承 / 自建产线多模态集** | 展示 VLM 视觉分析 + 振动/工艺双驱动诊断 | CWRU 公开 + 你实验室产线 2-3 个真实案例 | 单模态基线（纯数值 vs 数值+图像） |
| **B4: Anti-spurious 压力集（自建，本文亮点）** | 构造 5 类"假相关陷阱"：混淆变量、辛普森悖论、时滞错位、批次混杂、离群杠杆点 | 每类 20 个合成场景 | 无防护的裸 LLM 诊断（预期幻觉率 >40%）vs 本管线（应拦截绝大多数） |

> B4 是**审稿人最容易记住的贡献**：它把"LLM 工业诊断不可信"这个领域公认痛点变成了可量化、可复现的测试集，并可随论文开源——这是 AEI/JII 审稿人最喜欢的高杠杆贡献。

### 5.2 对比实验矩阵（Table 2 的骨架）

| 方法 | 类型 | RCA 准确率 | 证据可追溯 | 幻觉/假相关率 | 置信度校准(ECE) | 成本 |
|---|---|---|---|---|---|---|
| GPT-4o 直接提问 | 单 LLM | 中低 | ✗ | 高 | 差 | 低 |
| GPT-4o + CoT | 单 LLM | 中 | 部分 | 高 | 差 | 低 |
| ReAct + 工具调用 | 单代理 | 中 | 部分 | 中 | 中 | 中 |
| AutoGen 多代理讨论 | 多代理 | 中 | ✗ | 中 | 差 | 高 |
| FaultExplainer (TEP) | LLM+PCA | 中 | 部分 | 中 | 无 | 中 |
| PCA / XGBoost / LSTM | 传统/DL | 分类高、根因弱 | ✗ | — | — | 极低 |
| **本文全管线** | 多代理+门禁 | **目标最高** | ✓ 全链 | **最低** | **最好** | 中高 |
| **本文 (无门禁消融)** | — | 中 | 部分 | 中 | 中 | 中 |

**关键叙事**：不要只拼"准确率最高"（拼不过 99% 的监督分类器，且它们不给根因），而要拼**"准确率×可验证性×抗幻觉"的三维权衡**——这恰是 Gong 等人没做的维度。

### 5.3 消融实验（Table 3，五组足够）
① 去 Judge 门禁 ② 去物理审计(5b/7) ③ 去证据分级约束 ④ 去 RAG 本体（降级路径）⑤ 去反假相关层。每组报：RCA 准确率、假相关拦截率、平均成本、重诊断次数。

### 5.4 报告指标
主指标：**RCA Top-1/Top-3 准确率**、**COMPETING_SET 判定的精确率**（该说"无法区分"时敢说——这是诚实性指标，没人做过）；辅助：幻觉率（与 ground-truth 机理冲突的陈述比例）、ECE 校准误差、Token 成本/端到端时延、修复循环触发分布。

---

## 6. 提高命中率的十条策略

1. **贡献点只写四个**，且每个都能被一个实验表证：①质量门禁多代理管线 ②证据分级与门禁传播 ③反假相关机制+压力测试集 ④TEP/多基准系统评测。
2. **正面引用并对比 Gong (JII 2026)**：审稿人大概率知道它。差异句式："prior MCQA-based evaluations assess reasoning *in the abstract*; we evaluate *end-to-end on real process data with verifiable evidence chains*"。
3. **把 MDPI 综述的"agentic FDD 证据稀缺"作为时机论证**——引用其统计数字（2024 前 LLM 记录≈0）。
4. **开源 + 可复现声明**：开 GitHub（脱敏数据+配置+管线），AEI/JII 对可复现文章有明显偏好；先修掉第 1.2 节三个工程缺口。
5. **COMPETING_SET 是特色不是弱点**：把它包装成"calibrated honesty"——诊断系统敢输出"证据不足"，并给出补数据建议，比强行给结论更可信。配一个真实案例展示。
6. **案例研究要"全链路审计轨迹"**：放一个真实 run 的 judge 评分变化、审计意见、证据等级传播表——AEI 审稿人吃"工程严谨性"这一套。
7. **数字记忆点**：主表至少一个 "X%→Y%" 级别的强对比（对标 Gong 的 36.5%→54.6% 句式），建议来自 B4 压力集的假相关拦截率。
8. **图表即审美**：沿用你现有 drawio 五层 A3 架构图 + 浅色 HTML 报告截图，AEI 排版审美偏工程精致感。
9. **Limitations 主动写**：LLM 成本、并行依赖 harness、COMPETING_SET 需要专家复核——主动坦白能显著降低 major revision 概率。
10. **投稿信点三句**：领域空白（综述佐证）、与最近邻工作的差异（一句话）、可复现（仓库链接）。

## 7. 建议时间线（8 周）

| 周 | 任务 |
|---|---|
| W1 | 修三个工程缺口（5b 并行 bug、自愈循环脚本化、CP 网关统一） |
| W2-3 | B1 TEP 实验：数据管线打通 + 裸 LLM/CoT/ReAct 基线 |
| W3-4 | B4 反假相关压力集构建 + 拦截率实验 |
| W4-5 | B2 FailureSensorIQ 复现对比 + B3 案例整理 |
| W5-6 | 消融五组 + 成本曲线 |
| W6-7 | 论文初稿（LaTeX, Elsevier elsarticle 模板）+ 全部图表英文重绘 |
| W8 | 内审（按 AEI 审稿人视角自查）→ 投稿 |

---

## 附：检索到的关键文献清单（写 Related Work 直接用）

1. Gong, W. et al. Harnessing collective intelligence of multi-agent LLM systems for sensor failure reasoning in smart manufacturing. **J. Ind. Inf. Integr.** 49 (2026) 101012.
2. Liu, C. et al. Probing a novel machine tool fault reasoning and maintenance service recommendation approach through data-knowledge empowered LLMs integrated with AR-assisted maintenance guidance. **Adv. Eng. Inform.** 66 (2025) 103460.
3. *FaultExplainer: Leveraging LLMs for Interpretable Fault Detection and Diagnosis.* arXiv:2412.14492 (2024). [TEP]
4. Constantinides, C. et al. FailureSensorIQ: A Multi-Choice QA Dataset for Understanding Sensor Relationships and Failure Modes. arXiv:2506.03278 (2025). [IBM, HF leaderboard]
5. *Agentic AI for Safety-Aware Process Monitoring and Fault Diagnosis: A Review.* **Processes** 14(13):2112 (2025).
6. Lyu, N. et al. Benchmarking ML Fault Detection Methods on the TEP Dataset. ChemRxiv (2026). [DL 基线数字来源]
7. Jiang, W., Hu, F. AI Agent-Enabled Predictive Maintenance: Conceptual Proposal and Basic Framework. **Computers** 14(8):329 (2025).
8. Patel, K. Agentic AI for Self-Healing Production Lines. **JISEM** 9(4s) (2024). [低档，仅引出概念]
