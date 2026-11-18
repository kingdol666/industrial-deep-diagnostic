# Devil's Advocate Report

（评审对象：`paper/main.tex`，682 行；行号均指该文件。章节号按正文顺序：§5 = Evaluation Framework，§6 = Experimental Setup，§7 = Results，§8 = Comparison/Ablation/Stability，§9 = Discussion。）

## Strongest Counter-Argument

论文的全部数字由同一作者、同一模型族自建、自评、自证的仪器产生：grading keywords 源自与被测系统共用的同一份文献 cause table（line 282、551），rubric 与 allowed sets 度量的是对自定协议的服从，audit plane 的信任边界是内部的（line 592）。核心正命题——"失败是分辨率失败而非定位失败"（line 387）——唯一支柱 top-k 9/9 来自一个被论文自己承认带结构性偏置、却从未做 specificity 对照的仪器：协议强制 ≥3 个族级假设（line 261），token 集又来自真值文档，"定位"接近设计保证，而 line 586 仍将其升格为 "a lower bound on resolution"。作者自己的消融显示 bare call 精度更高，body 又承认 process quality 边际是 "architectural properties, not yet measured outcomes"（line 592）。于是论文实际交付的是：一个服从性工件生成器、一个被记忆污染但被诚实标注的精度边界、一组 n=1 且近乎机械的复现。诚实是真的；但被诚实披露的缺陷之和，在缺乏任何外部锚点时并未自动转化为可信度。

## Issue List

### CRITICAL

**CRIT-1【维度：④逻辑链验证 + ②拣选证据（仪器构造层）】top-k 仪器无 specificity 控制，却承载"resolution 而非 localisation"这一核心正命题**
- **位置**：Abstract（line 56）；§7.2 line 387（"failures of *resolution*, not of *localisation*"）；§6.2 Metrics line 358（top-k 定义与结构性偏置披露）；Contribution 4 line 82；§9 line 586（"the top-$k$ bound (9/9, [70.1%,100%]) is the stronger statement the current sample size can support, and it is a lower bound on resolution"）；token 来源 §5(C1) line 282、§8.3 line 551；强制 ≥3 假设 §4.2 line 261。
- **论述**：top-k 的三重结构性偏置——(i) 协议强制每场景生成 ≥3 个假设（line 261）、(ii) 计分 token 是族级的（"reactor cooling" 三场景共享，line 358）、(iii) token 集由与被测模型共享的同一 documented cause table 校准而来（line 282、551）——均被论文披露。但披露止于 "read it as family-level membership, not specific-form identification"（line 358）；全文没有任何该仪器的特异性证据：无 enumeration null、无错误管道 negative control、无"假设集不含真值族时仪器是否扣分"的演示。在此条件下，line 586 把 9/9 称为 "a lower bound on **resolution**" 是无效推理：strictness（评分严格）不等于 specificity（低特异性仪器评分再严格也不构成 resolution 下界）。论文内部已有反例：SKAB cavitation 由管道自己的排序把真值排在 2 名幸存者的**第 2 位**（line 436、484），五个 capped 案例中真值第一仅 2 个、第二 3 个（line 484）——即管道自己声明这些是不可分 fork，top-k 仍全部计入"定位成功"面，dichotomy 因此把自认 coin-flip 的案例记入成功栏。
- **论据**：若 specificity 低（设计上很可能：家族清单短 + ≥3 假设强制），则"9 个失败全是分辨率失败"退化为"协议强制生成的假设集几乎必然含有真值族 token"——这是设计性质而非经验发现。修复路径明确：报告一个 enumeration/对照条件下 top-k 的期望值，或将 dichotomy 全面改写为 "family-level set membership" 并撤回 "lower bound on resolution"。

### MAJOR

**MAJ-1【维度：④逻辑链验证】§7.3 与 §9 在"记忆能否复现机制标签"上直接矛盾，且未被调和**
- **位置**：§7.3 line 432（"Recalling the textbook label ``cooling-water fault'' cannot produce these three different mechanism pictures; **only the per-recording statistics can**"）对比 §9 line 588（"The documented cause table records not only the disturbed channel but each fault's dynamic form (IDV4 step, IDV11 random variation, IDV14 stiction), so **recall of that table alone could reproduce the observed mechanism labels**"）。
- **论述**：同一三联案例（IDV4/11/14），Results 断言记忆不可能复现、只有统计能复现；Discussion 让步记忆（含动态形式的完整 cause table）可以复现。由于被记忆的有效对象恰是含动态形式的 cause table，5.3 的全称否定是经由稻草人指称（"textbook label"）建立的过度声明，而 form-discrimination 又被论文定位为污染混淆的"主证据支撑缓解"（line 588）。推理链引用了 digest 中的统计量（R3 只锚定数字存在性，不锚定推理方向，line 360）只能证明输出与数据**一致**（data-consistent），不能证明由数据**驱动**（data-driven）——一个 recalled 答案配上相符统计同样是 data-consistent 的。
- **论据**：需将 line 432 改写为与 line 588 一致的弱声明（"与数据一致的读数不依赖对 channel label 的单独回忆"），或在 5.3 就地披露记忆含形式。修复成本低，但当前文本在承载污染防御的位置自相矛盾。

**MAJ-2【维度：②拣选证据 + ⑦利益相关者】"no control raises a false alarm" 的证据基础实为 n=1 blind control，摘要/表格/图注未限定**
- **位置**：Abstract line 56（"no control raises a false alarm"）；Table 6 line 412（"Control pass (no false alarm; n=3) 3/3"）；Fig 4 caption line 424；披露处 §6.1 line 333（"the TEP and IndPenSim control briefs state that the segment is the fault-free baseline… **Only the SKAB control is therefore blind**"）与 §7.2 line 389（括号限定）。
- **论述**：3 个 control 中 2 个的 brief 直接告知"这是无故障基线"，输出"正常"对它们是服从而非判别；真正的假警报抑制证据只有 1 个 blind control 加上 IndPenSim 的 recipe-impulse 复核（但该 control 同样被告知正常，refutation 是推理质量而非判别证据）。§6.1/§7.2 的限定是诚实的，但摘要与 Table 6/Fig 4 以未限定的 3/3 呈现，使读者高估判别证据量约 3 倍。正确呈现是 "3/3（其中 1 个 blind）"。
- **论据**：paper 自己的重述（line 333："shows that the pipeline does not fabricate faults under an honest brief"）才是该结果能支撑的最强命题。

**MAJ-3【维度：⑥替代路径】缺 script-only / 可辨识性对照臂：五个 capped verdicts 的内容可能不需要 agentic 推理**
- **位置**：§8.3 line 524（消融矩阵仅有 PCA / FE-replication / bare LLM 三臂）；pre-registered 未做臂仅 filter-disabled 与 engine-substitution（line 551、566、586）；capped verdicts 的"命名缺失测量"内容（line 434 IDV3 steam-header/feed temp、line 432/436 cooling inlet、valve-position 等——全部是 fork 子系统中**本就不存在**的通道）；§9 line 590（"the benchmark's most transferable finding" 归因于协议）。
- **论述**：论文从未排除如下替代解释：capped verdicts 的两个内容成分（子系统定位 + 缺失通道点名）可由"确定性统计定位子系统 + 从 ontology 枚举该子系统未测量通道"的纯脚本规则复现——这几乎是一个 identifiability 检查。若成立，"most transferable finding" 的功臣是 sensor 配置与 ontology，而非 competing-hypotheses 推理；而检验它的那个对照臂（scripts-without-LLM）既没做也没列入 pre-registered 清单。
- **论据**：IDV4 的 UA-fork 量化（line 581）是反例级的推理贡献，说明 LLM 推理**有**增量；但单例不构成对五个 capped 案例的归因。

**MAJ-4【维度：④逻辑链 + ②拣选证据】determination 阈值是作者设定的自由常数，4/9 与 "cap 避免 3 次错误断言" 全部条件于它，无敏感性分析且未列入预注册臂**
- **位置**：§4.1 line 231（"machine-checked floor is ≥2 eliminations, exclusion confidence ≥0.90, and a citation per elimination"）；cap 常数 0.70/0.65/0.50（line 231、240）；five-factor 权重 25/25/20/20/10（line 240）；反事实 line 551；IDV4 案例 line 581（"stays below the quantitative elimination threshold"——阈值直接决定 verdict state）。
- **论述**：4/9 的分母侧（多少案例被 cap）与 line 551 的"3 false vs 2 foregone"交易比，都由这些从未被变动过的阈值决定。line 551 的反事实只变动了 commitment 策略（强制取 top-ranked），未变动更现实的替代——放宽 elimination/exclusion 阈值后管道能在证据上正当 commit 多少。若阈值略松即可在不出错前提下 commit IDV4/IDV11，"pipeline 以分辨率换审计"的成本叙事的量级就不稳。论文的预注册清单（filter-disabled、engine-substitution、12×k≥3 repeats）不含 threshold-relaxation 臂，也未把阈值常数列为 limitation。
- **论据**：这是 4/9 这一 headline 数字背后的隐藏自由度，属于拣选检测的常观数值。

**MAJ-5【维度：⑧"So what?" + ⑤过度概括】摘要以已确立口吻出售"process quality"边际，而 body 承认它是"未测量的架构属性"**
- **位置**：Abstract line 56（"so the pipeline's margins are process qualities, not accuracy"）；Conclusion line 616（"the contribution is the auditable process rather than the accuracy"）对比 §9 line 592（"the 'process quality' margins claimed for the pipeline are **architectural properties, not yet measured outcomes**"）；无任何 expert/user/下游决策研究（line 592 末承认 expert blind test 仅 "planned"）。
- **论述**：body 的让步是充分的，但它恰恰撤回了摘要与结论的断言强度：论文证明的只是"管道产出服从性工件"，从未证明这些工件改善任何人的决策、审计效率或诊断结果。按论文自己的测量，process quality 的边际价值目前是零证据。这不是要求删除卖点，而是要求摘要携带 "architectural, unmeasured" 限定——当前 abstract-register 与 body-register 的落差正是本文批评 FE/AgentRCA 时所用的同类问题。
- **论据**：line 592 原文已给出正确表述；修复是 register 对齐问题。

### MINOR（简表）

| # | 位置 | 问题 | 处置依据 |
|---|---|---|---|
| 1 | Abstract line 56 | "Top-1 44.4%" 未带 identity-strict 3/9 与 leave-one-token-out 3/9–4/9 边界 | body line 387 已完整披露 |
| 2 | Fig 5 caption line 473 | "overconfidence 0" 平铺陈述，identity-strict 下为 ≥1 | line 387 明示 "reported rather than quoted" 惯例 |
| 3 | Table 6 line 413 / §6.2 line 360 | Rubric 94.6 为自建 conformance checklist | "author-designed"、"limited discriminative power" 已披露 |
| 4 | §7.4 line 484 | ceiling-compliance 循环性 | "circular by construction" 自认 |
| 5 | §5 line 282 | keywords 在 v1-era 同十二场景语料上校准（轻度 double-dipping） | "truth-adjacent…quantifies" 已披露 |
| 6 | §2.2 line 94 | FE 8/11 转录其内部不一致的数字 | "we transcribe the reported figure" 已披露 |
| 7 | Table 6 caption line 392 | Judge 94.7 为 post-threshold 选择效应均值 | "carry no benchmark weight" 已披露 |
| 8 | §8.4 line 569/571 | seed 出自 harness 而非外部 beacon；supersession 无外部承诺；n=1 且选中"结构性一致近乎机械"的场景 | abstract 标注 "one repeat pair"；body 多处自认（自 MAJOR 降级） |
| 9 | §8.3 line 566 | 45/45 byte-identical 仅覆盖确定性 suite arms | 边界已明示（"not the stochastic reasoning layer"） |
| 10 | §7.4 line 488 | verdict-type compliance 单向（只罚 over-cap 不罚 under-cap，cap 过度保守在 4/5 场景不可测） | 已披露 |
| 11 | Table 8 line 544 | bare arm 未跑 TEP control（2/3 覆盖） | "coverage gap" 已标注 |
| 12 | §9 line 599 | film-line deployment 为匿名单例、不可核验 | 已声明不属发布语料 |
| 13 | §3.2 lines 137/139/141、§6.3 line 368 | 评估配置为降级模式（RAG 13/13 探针失败、VLM 全部非视觉 fallback、单 engine、store 零复用、enhancement 层在测路径外），逐项披露充分但无一处聚合陈述"被评估的是降级配置" | 逐项披露到位；缺一句聚合（自 MAJOR 降级） |

## Ignored Alternative Explanations

1. **Sensor-set identifiability 足以产生 capped verdicts**："named discriminating measurement" 可能只是"fork 子系统缺失通道清单"，任何脚本化 identifiability 分析（无 LLM）都能给出（对应 MAJ-3）。
2. **Digest 是双臂命中的 common cause**：bare 9/9 与 pipeline top-k 9/9 读的是同一份 blinded digest；两臂共享全部判别信号，管道的净贡献可能仅剩 verdict typing——这比"审计换精度"更激进也更简省。
3. **Recall-then-rationalise**：假设可由记忆生成、再以 digest 统计量合理化；anti-spurious filter 审查相关性引用，R3 只锚定数字存在性——两者都不审查假设的来源方向。
4. **置信复现的算术解释**：retest Δ0.02 可能主要来自两次都落入 0.65-band INDISTINGUISHABLE 的 cap 算术加上相同 digest 下 five-factor 的相似算术，而非推理层"信念稳定"。
5. **阈值 artifact**：4/9 可能主要是 ≥2 eliminations / 0.90 exclusion confidence 的产物而非认识状态（对应 MAJ-4）。
6. **Batch-93 的 cascading 解释（对管道有利）**：文档化的 acid/heating 驱动与观察到的 cooling-pin（2.0 vs 193–700 L/h → 301.4K）可同为级联因果的两环；identity-strict 折扣可能系统性低估管道在这类"文档未覆盖偏差"上的真实表现——论文的折扣读法未考虑此替代。

## Missing Stakeholder Perspectives

1. **现场工程师/最终用户**：≈2h/场景（line 594）的可用性、三个状态输出的人因决策影响零评估；"named measurement" 隐含仪器购置建议，却无成本-效益分析。
2. **未文档化故障的操作方**：真实 RCA 的多数场景没有 documented truth 与作者定制 keywords——评估框架恰好在部署象限（新故障）不可用，仅有 "under construction" 的 novel-disturbance suite（line 588）。
3. **复现者/benchmark 社区**：reasoning layer 因 provider snapshot（2026-09）与无温度控制而永久不可复现（line 368 披露）；keyword/allowed-set 的作者中心设计不可扩展、无 inter-annotator 协议。
4. **监管方**：ALCOA+/GAMP 引用（line 607）虽已声明非 validation claim，仍可能被合规读者过度解读。
5. **人因/安全**：three-state escalation 接口无 human-factors 评估；human sign-off 为 procedural gap（line 609 已披露但无补救时间表）。

## Observations (Non-Defects)

1. **披露护甲**：本文对攻击面的预让步密度罕见地高（n=1、单向 typing、循环 rubric、内部信任边界、自建仪器……），系统性攻击后仅剩仪器效度类问题——这本身是论文质量的证据，也是 CRITICAL 仅一条的原因。
2. line 387 的 "the asymmetry is reported rather than quoted in each metric's most favourable lens" 是明示的呈现惯例；建议把该惯例前移至摘要，可同时化解 MAJ-2/MAJ-5 的 register 落差。
3. 反事实 6/9-with-3-wrong（line 551）与"自报唯一 compliance miss"（line 488、590）属于少见的自我不利披露，值得保持。
4. 投稿匹配度（非论文缺陷）：稿件为 Elsevier/AEI 格式、50 页量级（`\journal{Advanced Engineering Informatics}`，line 44）；若按计划投 CIKM Demo Track（通常 2–4 页 + 现场 artifact 演示），需要完全重写为演示叙事并另立 artifact 主张。

## Surface-Form Parity Self-Check

- **CRIT-1**：论文已披露 top-k 的 structural favouring 与 family-level 定位（line 358、484），但**从未披露 specificity 未测/null 对照缺失**，且在 line 586 与 line 387 将 9/9 升格为 "lower bound on resolution" 与 dichotomy——披露不覆盖指控核心，**维持 CRITICAL**。
- **MAJ-1**：Discussion line 588 已让步 recall-of-table 可复现 labels；但 line 432 的全称否定未在任何处收回或限定，矛盾本身未披露——**维持 MAJOR**（若改写 line 432 则降 MINOR）。
- **MAJ-2**：§6.1 line 333 与 §7.2 line 389 已披露并就地限定，未限定残留仅在 abstract/Table 6/Fig 4；因 evidentiary base 实为 n=1 blind，**降半维持 MAJOR**（若 abstract 补 "(1 of 3 blind)" 即降 MINOR）。
- **MAJ-3**：filter-disabled 与 engine-substitution 臂已预注册（line 551/566/586），但 script-only/identifiability 对照**从未被点名**——**维持 MAJOR**。
- **MAJ-4**：全文无阈值敏感性讨论，预注册清单亦不含——**维持 MAJOR**。
- **MAJ-5**：body line 592 已逐字承认 "architectural properties, not yet measured outcomes"；按"已披露且处置得当应降级"原则，本应降 MINOR，但 abstract（line 56）与 conclusion（line 616）以未限定口吻把 process quality 定为已确立贡献，register 落差使披露失效于最高可见层——**维持 MAJOR（低档）**；摘要加限定即降 MINOR。
- **原 MAJ 候选"降级配置聚合" → MINOR 13**（逐项披露充分）；**原 MAJ 候选"n=1/作者自持 seed" → MINOR 8**（abstract 已标注 "one repeat pair"，body line 569/571 自认 seed 来源与"近乎机械"）；**"45/45 仅确定性臂" → MINOR 9**（边界处处明示）；**"rubric/judge/单向 typing/FE 转录/keyword 校准" → MINOR 3–7、10**（均已在文中主动披露并给出正确解释）。

**结论**：1 项 CRITICAL（top-k 仪器 specificity 未测却承载核心 dichotomy）、5 项 MAJOR。按本席规则，CRIT-1 阻断"直接接收"；但全部发现的修复路径都是表述与对照实验层面的（补一个 specificity/null 报告、改写 line 432、对齐 abstract register、加 threshold 敏感性或 script-only 臂），不动摇论文已披露的诚实底座。
