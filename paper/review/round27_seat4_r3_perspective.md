# Peer Review Report — Peer Reviewer 3 (Perspective)

## Manuscript Information

- **Title**: Trustworthy agentic diagnosis for industrial processes: evidence-graded competing-hypothesis reasoning evaluated against per-fault literature baselines
- **Manuscript ID**: （单作者投稿）main.tex，682 行 LaTeX，约 50 页长文
- **Manuscript 内声明的主 venue**: Advanced Engineering Informatics（`main.tex` 第 44 行 `\journal{Advanced Engineering Informatics}`，elsarticle 格式）
- **作者声明的投稿意向**（来自委托方）： ACM CIKM Demo Track
- **System/Artifact**: Industrial Deep Diagnostic (IDD) pipeline；12-scenario benchmark（SKAB / TEP / IndPenSim），评测仓库随稿公开
- **Figures inspected by this reviewer**: fig_trace.png（Fig. 3, `sec:anatomy`）、fig_casestudy.png（Fig. 6, `sec:calibration`）
- **数字保真**：已由另一位评审独立核验（CI、judge 均值、bare LLM 9/9 vs pipeline 4/9 等），本报告信任该核验，不复算数字。

## Reviewer Identity & Focus

模拟国际审稿流程中的 Perspective 评审。背景：人机信任（trust in automation）与 LLM agent 系统方向的跨学科研究（HCI + AI 安全 + 工业信息化交叉）。关注：审计与问责、自动化等级（Sheridan-Verplanck / Parasuraman / FAA levels）、agent 评估方法论对社区的外溢价值、demo 论文的"演示叙事"；我的职责是挑战论文的底层假设并评估实践影响，而非复核实验正确性。

## Overall Assessment

### Recommendation

**Major Revision**

（附注：所需修改绝大部分是文本与结构性补写，不是新实验；若作者将 venue 明确为期刊长文（AEI），修改路径短。若坚持 CIKM Demo Track，则本稿在格式层面完全不可送审，需要另写一篇独立的 4 页 demo paper——见 Detailed Comments 焦点 5。）

### Confidence

**4**（精读全文与两张关键图，未独立复算指标；数字保真由他评覆盖）

### 总评摘要

这是一篇披露纪律罕见严格的系统论文。作者主动写出了通常由审稿人逼问才承认的内容：identifier-recall 最坏情形可将 Top-1 拉到 1/9、agent-side 与 machine-side 两套 cap 集的 0.01/0.03 缺口、曾被内部审计发现的 artifact 伪造捷径、human sign-off 仅为程序性占位、RAG 在全部 13 次运行中不可用。模型受控消融把"accuracy 换 process quality"变成了可计算命题（bare LLM 9/9 vs pipeline 4/9，强制承诺的反事实是 6/9 带三个错误判定），这是对 LLM-agent 评估文化的一次示范性姿态。

然而从 trust-in-automation 的视角看，论文的中心词与它自己的证据之间存在未调和的张力：标题宣称 "Trustworthy"，而 Discussion 自评 process-quality margins 为 "architectural properties, not yet measured outcomes"；全文从未定义 trustworthy。可审计性解决的是事后问责与复现，不等于事前正确性与校准；承载 "trustworthy" 的测量工具（作者自建 rubric、自建 cap 算术）是循环的，审计平面止步于内部信任边界，而"人"的一侧——操作员拿到 0.60 置信度竞争集后该做什么——完全缺失。这些是结构性缺口，需补写而非润色，故给 Major Revision。

## Strengths

1. **罕见的主动披露**（§5 C4、§7.2、§7.4、§9、§9.1）：fabrication-shortcut 历史、两套 cap 集缺口、identifier-recall worst case、sign-off 程序性缺口、RAG 全程不可用——全部由作者先行写入正文并量化。这本身就是一个 trust 声明应当有的样子。
2. **中心 trade-off 被诚实量化**（§8.3、§10）：bare same-model call 9/9 vs pipeline 4/9，加"若强制承诺 top-ranked survivor 则 6/9 且三个错误判定"的反事实分解（cap 用三个 false determination 换两个 foregone resolution）。作者拒绝在不利证据上含糊，这在 agent 论文中不多见。
3. **Verdict typing 是评估方法论的真正增量**（§6.2、§4.1 Eq. 2）：per-scenario allowed verdict set 先验声明每个场景可接受的结论状态，使 overconfidence 成为一等公民的可机检错误。这一设计对更广的 agent 评估社区有直接外溢价值。
4. **"Named discriminating measurement" 把评估维度从 accuracy 扩展到 actionability**（§7.3、§8.5 case study）：capped verdict 输出的是 instrumentation work order 而非一个弱化后的标签，这是论文最接近"工程可用"的部分，IDV4 案例链（Fig. 3）质量很高。
5. **智力谱系自觉且不掠美**（§2.4）：Parasuraman types/levels、Lee & See appropriate reliance、Heuer ACH、Hill causation criteria、Chow reject option 均被准确归位，并明言 IDD 的贡献是 "machine-checked instantiation... not their invention"。
6. **负结果作为实践证据**：film-line 部署返回 NEEDS_DATA（180 组关联未过 FDR 后显式列数据需求，§9.1）与 SKAB blind 场景的 capped 判定（§7.3）比任何 accuracy 数字都更能支撑其可信叙事。

## Weaknesses

1. **"Trustworthy" 标题与论文自评的张力未被调和**（title、abstract；§9 "Inference authorship and provenance" 段："the 'process quality' margins claimed for the pipeline are architectural properties, not yet measured outcomes"）。§1 从未定义 trustworthy，正文实际支持的词是 auditable。
2. **人的一侧完全缺失**：全文没有任何操作员消费 capped verdict 的操作语义（拿到 0.60 的 COMPETING_SET 后、装上 discriminating measurement 之前，工厂做什么？）；Lee & See 被引用于 §2.4 但 appropriate reliance 未被操作化，无任何 human-side 测量。
3. **Cap 内排序的呈现与语义冲突**（Fig. 6，"0.65 ‖ 0.60"；§7.4 "the cap separates equally-evidenced mechanisms, not a truth-relevance ordering"）：cap 内排名在协议上无置信含义，但图文呈现方式会诱导人类读出 ranking signal——这是一个人机界面信任陷阱，论文未处理。
4. **UQ 缺口**：caps（0.70/0.65/0.50）是 policy constants，reported confidence 无任何频率学派语义；与 conformal prediction 仅一次引用式对话（§2.4）；ceiling compliance 自认 circular（§7.4），但论文没有说出其直接推论。
5. **审计的信任边界止于内部且无补救路线图**（§3.4、§5 Execution form 段、§9）：event log 为 pipeline-internal records、无外部可验证性；judge 与被审者同一 model family（correlated failures 可能）；rubric 自建且 9/12 场景 ceiling（§6.2、Table 6）。"谁审计审计者"被披露但未被设计解决。
6. **Deployment prospects 中 projected 显著多于 demonstrated**（§9.1 全节："design-level/not measured" 出现四次；14 engines 仅一个执行过全 pipeline；RAG 层 untested；amortisation 未测）。自评诚实，但比例失衡未被显式承认。
7. **Venue-format 错位**（第 44 行 vs 投稿意向）：50 页 AEI 期刊格式与 CIKM Demo Track 不兼容。
8. **实践边界未量化**：约 2.0 h/场景的 task-fit 边界（哪些任务值得 2 h）、并发吞吐模型、10 万行/500 MB 级以上的数据规模极限与失效模式，论文均未给出（§6.4、§9 Cost 段）。

## Detailed Comments

### 焦点 1：底层假设挑战——审计痕迹等于可信吗？谁来审计审计者？

**1a. 标题的 "Trustworthy" 超出了论文自己的证据状态。** 论文内部的诚实工作做得非常好：§9 明言 process-quality margins 是 architectural properties 而非 measured outcomes，§3.4 明言 "Events are pipeline-internal records, not externally signed attestations"，§7.4 明言 ceiling compliance "circular by construction"。但标题与 abstract 以 "Trustworthy" 领衔，§1 的三个障碍（unauditable、wrong target、correlation≠causation）从未定义 trustworthy。目前的证据状态是：架构性质 + 内部一致性（C5）+ n=1 的 repeat pair + 尚未完成的外部专家锚定 + 一个从未可用的 RAG 层。这支撑的是 **auditable**，而 auditability 是 trust 的必要非充分条件：可审计解决事后问责与复现，不解决事前正确性与校准。建议二选一：(a) 在 §1 末尾显式定义 "trustworthy := auditable + capped honesty（凡数据不可分则不强迫结论）"，并声明 correctness 不在声明范围内（正文各处其实已这样实践，只差把这一定义立起来）；(b) 改标题为 "Auditable agentic diagnosis..."。以本文的披露风格，(a) 完全成立，但必须写出来。

**1b. 机器评分 rubric 能否承载 trustworthy 声明。** rubric（§6.2 R1–R7）是作者自建的 conformance 仪器，论文自己承认"nine of the twelve scenarios score at ceiling"（Table 6：9 个 100、两个 85、一个 65）且判别力有限；ceiling compliance 是协议算术的自环。这意味着 rubric 的 94.6 不能作为 trust 的证据使用——论文也确实没有这样用（"correctness claims rest on the truth comparison, never on the rubric"，§6.2），这个边界划得很对。剩余的问题是结构性的：**审计者的审计者是作者**。内部 integrity audit 发现并移除 fabrication shortcut（§5 C4）是好的治理故事，但它是 self-audit；judge 是同一 model family 的 LLM（§5 Execution form 段作者披露 correlated failures 可能）。论文的补救（judge 不作为 benchmark metric、改用 deterministic rubric；scripts verify、never author）是正确的第一层，但缺第二层：**外部可验证性**。最低成本且与本系统哲学一致的三件事：(i) event log 哈希链化/签名（append-only，使 §3.4 的 "compromised execution layer could still fabricate events" 缺口有针对性补救）；(ii) 把 grader 的 verify-only 重放做成第三方可一键执行的入口（仓库已具备大部分条件）；(iii) 在论文中加一张"假设 → 机制 → 残余风险 → 补救"的信任边界表，把散布于 §3.4、§5、§9 的材料集中呈现——目前读者需要跨三个 section 拼出完整信任模型。

**1c. L1–L7 自声明是整个 cap 算术的单点依赖。** §9 已披露："the L1--L7 levels are asserted by the reasoning stage itself; the machine gate checks ceiling arithmetic and grounding, not the correctness of a label, so a mislabelled evidence item could inflate its own ceiling"。这是全文 trust 结构里最锋利的洞，而 mechanical binding（L1/L3→统计文件、L5→ontology 节点）被列为 next step。建议做一个哪怕单案例的对抗性微实验：人为把一条 L3 证据标成 L1，看 gate 是否能抓到——若抓不到，这一事实本身应写进论文（它限定了所有 confidence 数值的可信层级）；若抓得到，是一段便宜而有力的证据。

### 焦点 2：自动化等级与问责框架

**2a. §2.4 的文献对话是"致谢谱系"式的，未完成定位工作。** 一句话一引用（Parasuraman、Lee & See、Heuer、Hill、Chow）作为 ancestry credit 是得体的，但从 perspective 评审看缺三块：(i) **Sheridan-Verplanck 10 级量表**未被引用或使用——而 COMPETING_SET 恰好可以精确定位到"把选项缩小到少数几个"这一级，DET 则接近"生成决策但不执行"，这个定位一句话就能说清，且能把三状态协议从"我们的设计"升格为"自动化等级空间中的一个明确坐标"；(ii) **Bainbridge (1983) Ironies of Automation** 缺席——本系统恰好是它的当代实例：自动化了诊断中机器擅长的部分，把机器最不确定的时刻（capped set）留给可能已被去技能化的人类去裁决，这是任何 trust-in-automation 评审都会提出的经典视角；(iii) **automation bias / trust miscalibration / trust repair** 文献缺席——冗长而权威的审计链对人类信任的影响是双向的（可以诱发 overtrust），论文只论证了"痕迹使结论可核查"，没有讨论"痕迹是否使操作员更愿意核查"。FAA/过程工业的 alarm management 背景（alarm flood 下一次并发几十个 scenario）也未提及。

**2b. Capped COMPETING_SET 的"消费语义"缺失——这是论文最大的结构性缺口。** §9 说 capped verdicts 是 "work orders for targeted instrumentation"，这个重构很漂亮；但 instrumentation 是以周/月计的资本开支，而异常正在发生。在安装 cooling-water inlet thermocouple 之前的运营窗口里，操作员拿到 0.60 的竞争集该做什么？论文没有给出：interim operating guidance（应对两个 survivor 分别成立时的保守操作包络）、monitoring escalation 触发条件、或 maintenance decision-rights 矩阵（DET→什么审批路径？CS→延期观察的验收标准？ND→何时停机？）。与之相关的还有 **5/9 的 capped base rate**：如果一个部署中一半的 verdict 都是竞争集，操作员对 DET verdict 的信任会被如何塑造（trust spillover /"狼来了"效应的反面——过度保守导致的系统性不信任）？Lee & See 的 appropriate reliance 恰恰是这个问题的理论工具，引用了却没用上。建议在 §9 或 §9.1 增加一小节 "Operating semantics of capped verdicts"，哪怕只是定性的决策表。

**2c. Under-capping 的成本不可见。** §7.4 诚实披露 verdict typing 是 one-directional（"compliance can flag over-capping but never under-capping"），SKAB valve 是唯一的 compliance miss。但从运营角度，过度保守（本该 DET 而 CS）有真实成本：延期维护、异常暴露窗口拉长、以及 2c 中说的信任侵蚀。benchmark 看不见这类错误。建议加一段 miss-cost asymmetry 讨论：协议用三个 false determination 换两个 foregone resolution（§8.3 反事实），这个交换在高后果场景（GxP batch deviation）与低后果场景（一般偏差）下的最优比显然不同——而协议目前是常数 cap，不随后果调整。这不是要求改协议，是要求把这一点写出来。

**2d. 问责链。** §9.1 披露 sign-off 仅为 procedural（无独立 human-endorsement artifact，13 次运行全自动）——披露得好。但"human engineer signs off"本身不是问责答案：当工程师在 CS 的两个 survivor 中批准了错的那个、且后续测量证明排序在 cap 内并无语义时，责任如何分配？这引向焦点 6。

### 焦点 3：实践影响

**3a. 2 h/场景的成本需要 task-fit 边界。** §9 的成本核算（117 min 事件跨度、分阶段中位数、批量并发 ≈6 h span 是编排效应）清晰且诚实；对 expert hours 的比较框架也是对的。缺的是适用性边界：对 episodic、高后果的 RCA（batch deviation 调查、GxP 偏差调查）2 h 完全可接受——专家 RCA 本就以小时到天计；对 alarm-response（报警风暴后分钟级响应）不可行。论文从未画出这条线。建议一个三行表：task type / 是否适配 / 证据状态（如 GxP deviation investigation: 适配，有 §9.1 案例；alarm triage: 不适配；startup/shutdown transient: 未测）。

**3b. 数据规模与吞吐边界未量化。** deterministic 阶段是 streaming（§6.4），blind digest 机制事实上把 agent context 与数据规模解耦，这应该能支撑远超 10 万行的数据——但论文没有给出实测边界（最大 rows × channels、内存曲线、高频振动数据的失效模式）。§9.1 的 historian 集成叙事（"export job plus API integration"）对一个年度全厂数据量的导出是否成立，读者无从判断。建议给出一条实测的数据规模上限及超限行为。

**3c. RAG 从未可用：一个被埋没的正面发现与一个未验证的卖点。** §3.2 披露全部 13 次运行 RAG probe 失败、全部本体走 fallback、corpus 中不存在任何 L6 证据项。这其实是论文污染叙事的最强证据之一（所有结果在无外部知识通道的 degraded 模式下取得），值得在 §9 contamination 段显式引用——目前该段只顺带一提。反面是：deployment 章节中 semantic-knowledge 层的卖点是 untested 的。建议：要么补一个 RAG-on 单臂，要么在 §3.2 与 §9.1 双向标注 "unvalidated optional layer"。

**3d. Deployment prospects 的自评结构对了，比例失衡要显式化。** §9.1 开头声明区分 demonstrate 与 project，且每项都诚实标注（data sovereignty 是 design-level、amortisation 未测、无第二个 engine 执行过全 pipeline）。但 demonstrated 栏实际上只有 film-line 一个案例，projected 有五项。建议把 §9.1 改排为 demonstrated / projected / untested 三栏并明示这一比例——对本文的读者群（工程师）而言，这种自我审计的彻底性恰恰是卖点，藏着反而可惜。

### 焦点 4：跨学科借鉴与外溢价值

**4a. 对 agent 评估社区的外溢价值被 scope 得太窄。** Table 1 把贡献定位在 industrial process diagnosis 内部，但 §5 的 C1–C5 契约与 §6.2 的指标设计中有至少三个可移植模式，值得在 §5 或 §10 用一段明示：(i) **truth-isolation sentinel**（双向机检：ground-truth 字符串不得进入 agent 可见 brief、fault 词汇不得进入 user-context——泛化为"任何 agent benchmark 的泄漏哨兵"）；(ii) **verdict typing + per-scenario allowed set**（先验声明可接受结论状态，使 overconfidence 可机检——适用于任何带弃权/分级的 agent 输出协议）；(iii) **anti-fabrication division of labour**（scripts verify、never author；完整性 gate 使作弊路径 "permanently unreplayable"——C4 是对整个 agent-benchmark 生态的教训）。CIKM 的信息/知识管理读者对 provenance 与可复现性有天然亲切感，这段外溢声明会显著提升论文的社区价值。

**4b. 与正式 UQ 的对话缺口。** §2.4 引了 Angelopoulos et al. 一次（"whose statistical counterpart is modern selective prediction"）就停了。结构上，COMPETING_SET 就是一个 **prediction set**：top-k 9/9 即 "true mechanism ∈ set" 的经验 coverage=100%（n=9 上的单样本）；conformal risk control / risk-controlling prediction sets 恰好是给这种 set-valued 输出发 distribution-free guarantee 的框架，且比"psychometric calibration study"（§7.4 列为 future work）更接近本文已有的机检架构。同样直接的是：论文应说出那句它绕开了的结论——**reported confidence 目前没有任何频率学派语义**（0.60 不是 60% 正确概率，不是 coverage 保证，只是 protocol ordinal）。§7.4 承认 ceiling compliance circular，但把这一推论留给读者。一段 200 字的 "Semantics of reported confidence" 小节（协议序数语义 + conformal 校准作为 future work 的具体路径）就能补上，且与论文的诚实风格一致。

**4c. LLM-as-judge 的自偏好偏差文献缺席。** judge 与被审者同族模型的问题论文用"judge 不作为 metric"规避了（正确的规避），但没有引用 self-preference bias 等文献把规避的动机讲透；同样的，verbalized confidence 校准文献（LLM 报告置信度系统性过信）与 §7.4 的 0.91/0.93 发现直接相关，值得对话。

### 焦点 5：Demo 叙事（针对 CIKM Demo Track 计划）

**5a. 首要问题：venue-format 错位。** 本稿是 `elsarticle` 格式、面向 Advanced Engineering Informatics 的 50 页长文（第 44 行）；CIKM Demo Track 要求约 4 页的 demo short paper 加一个可现场运行的系统演示。二者不可互相替代。建议：本稿按 AEI 路径走完评审；另写一篇独立 demo paper，以本稿的 Fig. 3（audit trace）与 §8.3 的对比为素材。以下建议以"如果做 demo"为前提。

**5b. 最能打动 IKM 社区的三个演示。** (i) **审计链漫游 + 现场篡改实验**：Fig. 3 本身就是 demo storyboard——从 run directory 点开任一 artifact、展示 provenance label、回放 log checker；然后当着观众改一个 artifact 里的数字，让 artifact-consistency gate 当场 FAIL。"Tamper it live" 是对审计主张最强的 30 秒论证，比任何 slide 都有效。(ii) **cap 场景对比**：同一 blind digest 双屏——bare LLM 的 9/9 关键词命中（无 verdict typing、无证据链）对 pipeline 的 capped set + named discriminating measurement；把论文的中心 trade-off 变成一次视觉对比。(iii) **活的事件流 + seed 重放**：SSE/WebSocket 实时事件流（系统已有）与 draw-then-re-execute 的 seed 重放（§8.4），reproducibility 对 CIKM 观众是母语。

**5c. Demo 中应避免的过度声明。** 不用 "trustworthy" 作 demo 标题词（用 "auditable"）；不演示 RAG（从未跑通，被问即失分）；避免 TEP-only 演示——"模型背过 TEP"的质疑在 demo 现场无法用论文里的 form-discrimination 论证来得及招架，首选 SKAB blind 场景与 film-line NEEDS_DATA 案例（负结果叙事在 demo 中最能建立信任）；不暗示 human sign-off 已存在（§9.1 已披露为程序性占位）；cap 内的 0.65‖0.60 排序按焦点 2/3 的建议做无序并列或显式标注"序无置信含义"，否则现场必然被问"为什么把错的排前面"。

### 焦点 6：伦理与社会视角

**6a. 已有的治理材料是真实的**：decision-support 定位、sign-off 缺口披露、GxP/ALCOA+/GAMP 5 的文档对齐（且明确声明这不是 computerised-system validation claim，§9.1）、model-change management（§9.1）、AI 辅助写作声明。这些超出同类论文的平均水准。

**6b. 仍缺一段 ethics/governance 讨论**，建议含五点：(i) **与安全仪表系统（SIS, IEC 61511）的边界**：一句话声明 pipeline 是 off-line advisory layer，不得进入任何 interlock/安全联锁路径——工业安全读者会立刻找这句话，目前没有；(ii) **decision-rights 矩阵**：DET/CS/ND 各自对应的审批路径与"操作员采纳错误 survivor"情形的责任框架（"human signed off" 不是答案）；(iii) **系统自身的 model card**：模型家族、协议版本、已知失效模式（identifier recall、under-capping、cap-set gap）——论文其实已具备全部素材，缺的是按模型卡格式集中；(iv) **single human-AI loop 的自指承认**：AI 声明披露了作者用 AI 工具构建评测 harness 并辅助写作，而系统的审计协议也诞生于同一 human-AI 回路——一句 "independent deployment validation is a precondition for safety-relevant use" 级别的承认，与论文的整体诚实度相称；(v)（可选）**去技能化**一句带过即可：长期使用后组织内独立验证诊断的能力退化，正是 Bainbridge 讽刺的组织版本。

## Suggestions for Improvement（优先级排序）

**P1 — 必改（全部为文本/结构性工作，无需新实验）**
1. 调和 trustworthy 声明：在 §1 定义 "trustworthy := auditable + capped honesty"，或将标题改为 "Auditable..."；abstract 相应收敛。
2. 新增小节 "Operating semantics of capped verdicts"（§9 内）：interim guidance、decision-rights 矩阵、capped base rate 对信任校准的影响；Fig. 6 与 demo 呈现中修正 cap 内排序的语义暗示。
3. 新增 "Semantics of reported confidence" 段：显式声明 confidence 为 protocol ordinal、无频率语义；以 conformal risk control 形式化 COMPETING_SET 为 future work 的具体路径。
4. 加一张信任边界表（假设 → 机制 → 残余风险 → 补救），集中 §3.4/§5/§9 的分散披露。
5. 解决 venue 决策：AEI 长文按本稿推进；CIKM Demo 另写 4 页 demo paper（内容见焦点 5b/5c）。

**P2 — 应改**
6. §2.4 扩为两段：补 Sheridan-Verplanck 定位、Bainbridge、automation bias/trust repair；为三状态 verdict 给出自动化等级坐标。
7. 新增简短 ethics/governance 小节（SIS 边界、model card、single human-AI loop 承认）。
8. §5/§10 加一段面向 agent 评估社区的外溢声明（sentinel、verdict typing、anti-fabrication division of labour）。
9. §9.1 改排 demonstrated / projected / untested 三栏；RAG 层双向标注 unvalidated；补 2 h 成本的 task-fit 边界表与数据规模上限。

**P3 — 建议（低成本实验）**
10. L1–L7 mislabel 对抗微实验（单案例即可），验证 gate 对 level 标签错误的敏感性，结果无论正负都写入论文。
11. RAG-on 单臂（或正式声明为 untested layer）；外部专家锚定（作者已承诺）加速执行。
12. Event log 哈希链/签名，使 §3.4 的内部信任边界有针对性补救。

## Minor Issues

1. 第 44 行 `\journal{Advanced Engineering Informatics}` 与 CIKM Demo 投稿意向冲突，投稿前需明确。
2. Abstract 超过 340 词，接近多数期刊上限，远超 demo track 要求；建议压缩。
3. Table 8（`tab:ablation`）中 "FE-protocol replication 6/6" 与 "FE official prompts (GLM) 5/6" 两行并列易误读，建议加一行脚注说明差异来源（T²-contribution 特征 vs 完整复制的特征提取）。
4. §7.2/§7.4 的多分支 disclosure 句（每句含三个以上从句）建议拆分；50 页长文可以承担，demo/短文不可。
5. "cap / ceiling / bound" 三个词混用，agent-side 与 machine-side 两套 cap 集已有文字披露但可表格化（一行两列即可）。
6. `wei2026agentrca`（AgentRCA, July 2026）为 contemporaneous work，投稿时请核对其发表状态并更新引用形式。
7. Table 6 的 precision 4/4 未脚注说明 0.91/0.93 两个 R4-flagged verdict 仍计入 determined 集（flag-deduct-but-not-invalidate 是一个政策选择，值得一行说明）。
8. Data availability 中 Zenodo DOI "will be minted on acceptance"——建议投稿时即 mint，便于评审验证（对本文这类以 released artifacts 为支柱的投稿尤其如此）。
9. Fig. 6 底部证据链中 "0.65 ‖ 0.60" 建议在 caption 中补一句 "ranks within the cap carry no confidence meaning"（与 Weakness 3 相关的最小修正）。
10. §2.4 若补引 Sheridan-Verplanck 与 Bainbridge，注意与现有 Parasuraman 引用分工，避免谱系段膨胀。

---

**给编辑的一句话总结**：这是一篇披露纪律罕见、中心 trade-off 量化诚实的系统论文；其主要缺陷不在实验而在叙事与结构——"Trustworthy" 标题超出自评证据、操作员消费层完全缺失、UQ 语义未言明、venue 错位。所列修改均可在不加新实验的前提下完成，完成后这将是一篇对我所在社区（trust in automation / agent evaluation）真正有对话价值的论文。
