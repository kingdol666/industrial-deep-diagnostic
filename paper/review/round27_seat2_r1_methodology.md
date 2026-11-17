# Peer Review Report — Peer Reviewer 1 (Methodology)

## 稿件信息

- **标题**：Trustworthy agentic diagnosis for industrial processes: evidence-graded competing-hypothesis reasoning evaluated against per-fault literature baselines
- **稿件**：`paper/main.tex`（682 行 LaTeX 源文件；编译约 50 页；elsarticle 预印本格式）
- **系统**：Industrial Deep Diagnostic (IDD) —— 九阶段 agentic 诊断流水线 + 机器可校验的评估框架
- **基准测试**：12 个场景（9 个故障 / 3 个对照组），来自 SKAB / TEP / IndPenSim；单次记录执行 + 一次种子抽取重执行
- **已检查的工件**：`results/benchmark/` 下的 `metrics.json`、`rubric.json`、`baselines.json`、`consistency_audit.json`、`retest_selection.json`、`repro_report.json`、`suite_determinism.json`、`gradings/*.json`（已获数字保真性豁免；本次评审仅将工件用于研究设计核查）

## 评审员身份与关注点

过程系统工程与数据驱动故障诊断方向教授。评审专长与偏好：统计严谨性、评估协议设计、可复现性；特别警惕循环论证（circularity）、样本量撑不起的结论、以及不可复现的评估。本次评审仅针对方法学，不涉及会议适配度（venue fit）。

## 总体评估

- **建议**：**大修 (Major Revision)**
- **置信度**：**4**（通读全文，并对发布工件做了针对性抽查；未审计仓库源码本身，故不给 5）

**总评摘要**：这是我在 LLM 故障诊断方向见过的少见的、以"对自己不利"为纪律的论文：它主动报告了 bare single-call LLM 9/9 高于流水线 4/9 的消融结果、identity-strict 3/9、leave-one-token-out 3/9–4/9、联合最坏情形 1/9，甚至披露了内部完整性审计删除 artifact 伪造捷径的历史。评估契约（truth isolation、gate-graded scoring、append-only draw record）在同类工作中是真实的进步。但方法学上仍有三处结构性问题：其一，n=9 目的性抽样 + 每场景单次执行之下，Wilson CI 的可交换性（exchangeability）解读恰恰是论文自己声明放弃的那种解读，区间既不度量场景抽样也不度量 run-to-run 变异；其二，identifier channel 的披露范围过窄——我核查发布工件发现 9 个故障 case id 中 7 个在 run 目录名中直接嵌入机制名，包括被论文作为"blind-set robustness"核心证据的 `skab_cavitation_13`，而论文将该通道仅限定于 TEP，联合最坏情形界（1/9）也因此不完整；其三，稳定性证据是 n=1 且抽中论文自认"接近机械性一致"的易例。上述问题多数已被论文部分披露并有预注册的补救路径，但补救（neutralized-identifier re-run、k≥3 repeats、filter-disabled 臂）均未执行，而头条数字直接受其影响，故为大修而非小修。

### 优势

1. **罕见的负结果披露纪律**（Abstract；Table 4；Sec 6.3；Sec 7）：bare-LLM 9/9 vs pipeline 4/9、identity-strict 3/9、LOTO 3/9–4/9、联合最坏 1/9、伪造捷径史、RAG 全程不可用、VLM 降级——不利数字全部进正文而非脚注。
2. **Model-controlled ablation 的设计认识论正确**（Sec 6.3；Table 4）：同模型家族、同 blind digest 的 bare-call 臂把"准确率优势"这类不可证伪的叙事转化为"过程质量 vs 准确率"的可检验取舍，这是本文最有价值的实验设计。
3. **机器强制执行的评估契约**（Sec 5，C1–C5）：双向 leakage sentinel、SHA-256 fingerprint、expected-verdict-set 预执行固定、且唯一的 allowed-set 违例（SKAB valve）被计为 miss 而非叙述为成功（Sec 5.4）。
4. **评分工具的敏感性分析诚实且可复现**（Sec 5.2/5.3）：identity-strict、leave-one-token-out、branch-localised、clean-subset 3/7 多读数并列，token 集全部发布（我在 `gradings/*.json` 中逐项核对属实）。
5. **Draw-then-re-execute 协议的程序正义**（Sec 6.4）：seed 可重放、append-only 抽取记录、supersession rule 在比较前固定、11 个未重跑场景列为 outstanding contracts 而非默认稳定。
6. **跨系统比较的克制**（Sec 6.1–6.2）：Register A/B 分离、明确声明不做显著性检验、协议差异逐条枚举。

### 不足

**主要问题：**

- **W1（统计解读，Table 2 全列；Sec 5.2；Sec 7.1）**：在目的性抽样、场景难度高度异质、每场景单次执行的设计下，二项/Wilson 区间所需的可交换性假设不成立。论文自己说区间 "read as measurement uncertainty on this corpus, not sampling generalisation"——但对一个被执行一次的固定 corpus，4/9 这个计数没有抽样变异，唯一可能的变异源（stochastic reasoning layer 的 run-to-run 变异）恰恰是 n=1 未测量的。区间于是既不是场景抽样不确定度（被否认），也不是执行变异（未测量），目前的表述留下了没有清晰频率学派含义的数字。
- **W2（identifier channel 披露范围，Sec 7 "Prompt-knowledge contamination"；Sec 5.2 blind-set）**：论文称 "every **TEP** case id and run-directory name embeds the documented mechanism"，联合最坏情形 1/9 只折扣 TEP 派生结果 + batch-93。但发布工件显示 run 目录为 `<timestamp>_bench_<case_id>`，而 9 个故障 case_id 中 7 个直接命名机制：包括 `skab_cavitation_13`（被论文作为"fault label is withheld"的 blind-set 唯一证据）、`skab_valve1_1`、以及全部 6 个 TEP id。且架构上每次 dispatch 向 sub-agent 传递绝对路径 `RUN_DIR`（Sec 3.1），该通道对每个会话结构性存在。blind-set robustness 叙事与 1/9 最坏情形界均需重述。
- **W3（中心成本声明的推断链，Sec 6.3；Sec 5.3）**：9/9 vs 4/9 的"放弃 resolution 换取可审计性"量化建立在一个 recall 污染的工具上（bare 臂的 released 答案逐字复述目录条目如 "IDV(1): A/C feed ratio step change in Stream 4"），且两侧 typing 要求不对称（bare 臂无 verdict typing、无 cap）；forced-commitment 反事实 6/9 使用了 capped 集合内 recorded ordering，而论文在 Sec 5.3 明确声明 "the cap separates equally-evidenced mechanisms, not a truth-relevance ordering"——两处对 ordering 的认识论地位不一致。我核算的随机 ordering 期望值为 4 + (1/3+1/2+1/4+1/2+1/2) ≈ 6.1/9，与 6/9 巧合接近，但论文应自行说明这一稳健性而非留给读者。filter-disabled 与 forced-commitment 臂缺失，使"resolution 损失定位在 cap policy 而非 orchestration"停留在推断（论文已承认）。
- **W4（稳定性证据强度，Sec 6.4；Abstract）**：n=1、且抽中的是论文自认 "structural agreement close to mechanical" 的 IDV11；Δconf 0.02 的稳定性部分是 0.65 INDISTINGUISHABLE cap 压缩方差的结果而非校准稳定性的证据；consistency rule（`CONSISTENT = same type AND (same equipment tag OR mechanism_class ≥0.35 token overlap)`）为作者事后设计且 mechanism_class 词表粗粒度（工件中两个 SKAB 故障均为 "OPERATION"）。1/1 within-era agreement 作为稳定性证据目前接近零信息量。
- **W5（评分工具的 in-sample 校准，Sec 5.1 C1）**：keyword sets "calibrated ... against the v1-era corpus"——即在同一 12 个场景的更早执行上调校、再冻结、再用于当前执行评分。尽管跨 era 且披露完整，这仍是对被评语料本身的工具拟合（over-generic tokens 的移除与 synonyms 的添加都以这些场景的执行行为与对比目标文献为参照）；out-of-sample 主张因此受限，而 held-out 校准未做。

**次要问题：**

- **W6（top-k 定义，Sec 5.2 Metrics；Table 2；Sec 6.1）**：k 并非固定（survivor set 2–4 且自产），集合大小不受惩罚；"approximates candidate-list membership" 混用了生成的 ≥3 个 hypotheses 与存活的 2–4 个；与 FE 的固定 top-3 不是同类量。
- **W7（Abstract 层的读数选择，Abstract vs Sec 5.3/Sec 7）**：Abstract 给出 4/9 与 top-k 9/9，但 identity-strict 3/9 与联合最坏 1/9 未出现；"no control raises a false alarm" 未注明 3 个 control 中仅 1 个是 blind。
- **W8（Sec 3.3 "Why nine stages" 的轻度过度声明）**："the model-controlled ablation independently supports each" 三个分解规则——bare-LLM 消融只支持 deterministic/semantic split，不支持"两独立审计师"或 stage 边界本身。

## 详细意见

### 1. 基准设计（n=9 目的性抽样、单次执行、修复循环选择效应）

抽样规则（"every scenario corresponds to a publicly documented fault episode"，Sec 5.1）被诚实披露，其后果（difficulty 向下偏置、无场景总体推断）在 Sec 7.1 有正面陈述，这是对的。但有一个未被讨论的二级效应：选择规则使 TEP 子集与文献**三重绑定**——ground truth（Chiang cause table）、对比目标（FaultExplainer 同表）、keyword synonyms（论文承认 "the published per-fault baselines contributed the mechanism synonyms"）同源。这放大了 W5 的工具拟合问题：同一张发表表格同时充当了真值、baseline 和评分器词源。另外 "mechanism diversity across families"（Sec 7.1）与 cooling trio（3/9 同一物理通道）之间存在张力，论文以 form discrimination 价值自辩，可以接受，但 diversity 声明应限定在 family 层级。

单次执行问题归入 W1/W4。修复循环选择效应：13 次运行中 12 次零诊断层修复、唯一例外（IDV3）一轮且 "no verdict text changed"（Sec 5.3 配置披露；Sec 3.4）——本文 corpus 中该效应经验上有界且已披露，无进一步要求；但注意其成立依赖"本轮恰好没触发"，作为设计属性它依然存在（best-of-N 结构上允许 verdict 因 judge 门槛而重掷），建议在 Sec 7.1 的表述中把"本轮未触发"与"结构上不存在"分开。

### 2. 统计与推断

**Wilson CI 的解读**：见 W1。补充一点正面观察：论文没有做跨系统显著性检验且反复声明（Sec 6.1、Fig forest caption），这种纪律高于领域常规。但 Fig forest 把 3/6、4/9、9/9、7/11、9/11 的区间并排画出，视觉上邀请读者做论文文本所拒绝的比较——建议图内直接加 "descriptive only; sets differ" 水印式标注。

**top-k**：见 W6。核心问题是自产集合 + 变长 k + 无大小惩罚使 top-k 接近"生成足够多 family 级 hypothesis 即可得分的 recall 度量"；所有臂在此度量上接近饱和（bare 臂 top-1 即 9/9，FE-replication 6/6），说明其判别力有限——这一点论文可用一句元评论明说，反而是加分项。建议改名（如 truth-in-survivor-set rate）、随附 survivor-set 大小分布（数据已在 Sec 5.3 分散给出：2/2、3/3、4 中第 3 等）。

**多重读数**：identity-strict 3/9、LOTO 3/9–4/9、branch-localised 8/9、clean-subset 3/7 的并列是诚实的工具不确定度分析，我在 `gradings/` 中核实：IDV7 的 kw_hits 确为 `["header"]` 单 token（移除即降为 3/9，与正文一致），IDV1 为两个拼写变体（'进料配比'/'配比'），batch-93 为 `['加热','执行器','偏差']`。问题只在呈现层级（W7）：Abstract 的 4/9 未携带 identity-strict 折扣，最坏情形 1/9 藏在 Sec 7。另建议 Table 3 增加 kw_hits 列，让单 token 脆弱性（IDV7）在正文可见。

### 3. 循环性风险

**Rubric**：作者自建 conformance 检查、9/12 场景 ceiling、论文自称 "circular by construction"（Sec 5.3 对 ceiling；Sec 7 对 rubric）并声明 "correctness claims rest on the truth comparison, never on the rubric"——定位正确。残余问题：Table 2 中 "Ceiling compliance, capped 5/5 (gate-enforced by construction)" 这类构造性保证的行占据证据表的位置，应移注或合并。非-CS 行 5/7 vs machine 0.90 gate 不是循环的（它是两个自产 cap 集合之间差距的测量，论文称之为 "a consistency finding about our own two cap artifacts"，准确）。

**Keyword-hit 与知识污染**：见 W2 与 W5。我要强调 W2 的严重性：论文的 identifier 披露以 TEP 为界，且以 neutralized re-run 作为已承诺补救；但 `skab_cavitation_13` 是全文唯一被赋予"blind-set robustness"证据地位的场景（Sec 5.2、Sec 7 两处），其目录名即答案。公平地说，有一个反向证据论文可以利用：若 identifier recall 在起作用，cavitation 应被排到 survivor set 首位，而实际排在 valve-side 之后（第二/二，conf 0.60）——这是**反对** recall 主导的行为证据，建议论文明确引用它。但这不能替代 disclosure 的修正与 neutralized 重跑对 SKAB id 的覆盖。

**Ceiling compliance**：定位准确（构造性），无进一步要求。

### 4. 消融逻辑

bare-LLM 9/9 vs pipeline 4/9 作为"中心成本声明"的认识论框架（放弃 resolution 换取可审计过程）是本文最好的一个想法，且论文主动承认该量化 "is inferred from this counterfactual, not tested by an arm"。三点残余：(a) 9/9 是 recall 污染工具上的读数——论文承认 "neither arm's absolute TEP numbers measure contamination-free ability"，那么"成本 = 5 个 resolution"的算术也应同等地标注为污染工具上的下界式估计；(b) typing 不对称——bare 臂的 strict_top1_hit 是对其自排序 top-3 首项的 keyword 命中（我在 `baselines.json` 中核实，如 IDV1 首项逐字复述目录条目），pipeline 的 4/9 则要求 DETERMINED typing；forced-commitment 反事实正是为弥合此不对称而设，方向正确，但其 ordering 依赖见 W3（建议补一句随机 ordering 期望 ≈6.1/9 的稳健性说明）；(c) 缺失的 filter-disabled 臂影响具体：3 个 capped 判决（IDV11 的 lag-0 sign flip 屏蔽、两个 cooling fork）都可能因 filter 放宽而改变 survivor 结构，没有该臂，"resolution 损失在 cap policy"的归因只对 SKAB valve（其 fork 是通道缺失而非 filter 屏蔽）是直接的。engine-substitution 臂对本文声明影响较小（论文未做跨引擎质量声明），可继续留在 future work。

### 5. 一致性验证

retest 协议的程序设计（seeded draw、append-only、supersession 前置固定、outstanding contracts 枚举）是同类工作的规范做法，值得肯定；seed 来自 harness 而非外部 randomness beacon 已披露。但证据强度见 W4：n=1、易例、confidence 一致性部分由 cap 压缩造成、consistency rule 与 mechanism_class 词表为作者事后设计且粗粒度（"OPERATION" 同时覆盖 valve 与 cavitation 两案）。45/45 byte-identical 只覆盖确定性层，论文每次提及均如实限定（Sec 6.3、Conclusion），无保留意见。两点补充：retest pool 排除 controls 未给理由（重跑一个 control 对 false-alarm 稳定性同样有信息量）；IDV11 的 run1 出自并发 batch、run2 出自顺序执行，批处理 vs 顺序执行的环境差异未作为两-run 比较的潜在混杂讨论。

### 6. 预注册与纪律声明

Execution contract、fail-fast gates、append-only draw record、expected-verdict-set 固定、伪造捷径的删除史与"脚本只验证不创作"的分工——这些构成本文方法学贡献的实体，且多数确实机器可执行（`repro_report.json` 的 153 fingerprints、12/12 execution proof 与 `suite_determinism.json` 的 45/45 与声明一致）。缺口：(a) keyword 校准发生在同语料 v1-era 执行之后（W5）；(b) consistency rule 与 allowed-verdict-sets 的"预执行固定"只有断言，只有 supersession rule 给出了时间锚点，建议像 draw record 一样给 commit 锚点；(c) 预注册消融矩阵中恰好缺失的两臂（filter-disabled、forced-commitment）是对中心机制声明最要紧的两臂。

### 7. CIKM Demo Track 短文形态（方法学内容的取舍）

必须保留在正文：(i) 单次执行 + 目的性抽样披露；(ii) 9/9-vs-4/9 消融及其"过程质量非准确率"框架——这是论文的诚实性锚点与差异化核心；(iii) identifier-recall caveat **含量化最坏情形**（若按我的 W2 修正则须覆盖 SKAB）；(iv) C1–C5 契约中 truth isolation 与 gate-graded scoring 的定义（可复用贡献）；(v) rubric 是 conformance 非 correctness 的定位声明。可移附录/仓库文档：CP 谓词表（Table 3）、14-artifact 完整表（可压缩为一句+引用）、Algorithm 1 伪代码、成本分解、deployment prospects（Sec 7.2 整节）、per-stage wall-clock。多重读数（identity-strict / LOTO / branch-localised / clean-subset）应合并为一张小表而非分散在两节。这样正文可缩减约 40% 而方法学完整性不损失——venue 适配本身由别的评审负责，我只指出上述内容是方法学上不可牺牲的最小集。

## 改进建议（按优先级）

1. **[P1] 执行已承诺的 neutralized-identifier re-run，且扩展到 SKAB case-id**（W2）：opaque hash 目录 + identifier-stripped brief headers 应覆盖 `skab_cavitation_13`/`skab_valve1_1`，否则 blind-set 叙事不能保留；在此之前，headline 数字须以 recall-possible tier 呈现，最坏情形界重述（当前 1/9 低估）。
2. **[P2] 修正 CI 的解读框架**（W1）：或明示 super-population/exchangeability 假设及被放弃的解读；或以原始计数 + 每场景难度注释呈现，待 k≥3 repeats 预注册完成后单独报告 run-to-run 变异。
3. **[P3] 补 forced-commitment 执行臂**（或最低成本：在 Sec 6.3 加一句随机 ordering 期望 ≈6.1/9 的说明，说明 6/9 对 ordering 假设稳健）。
4. **[P4] 执行 filter-disabled 臂**（预注册已在案），或把"resolution 损失定位在 cap-and-elimination policy"的表述降为假设。
5. **[P5] Abstract 层的读数公平性**（W7）：给出 identity-strict 3/9（或声明 Top-1 为 3/9–4/9 区间读数）；"zero false alarms" 附注 1/3 blind control。
6. **[P6] top-k 度量修正**（W6）：改名、附 survivor-set 大小、停止与 FE top-3 直接并排（保留描述性对照）。
7. **[P7] 工具冻结纪律**（W5）：对未来新增场景，keyword 集在任何执行前冻结；consistency rule 与 allowed-set 给 commit 锚点。
8. **[P8] 表格卫生**：Table 2 移除/标注构造性行；Table 3 增加 kw_hits 列；Sec 3.3 的 "independently supports each" 改为仅指 deterministic/semantic split。

## 次要问题

1. Abstract 未含 identity-strict 计数；"no control raises a false alarm" 缺 blind-control 限定（与 Sec 5.1 不一致）。
2. Table 2 中 "gate-enforced by construction" 的两行占据证据表空间（Sec 5.3 已自认循环）。
3. retest pool 为 faults-only，排除 controls 未说明理由（Sec 6.4；`retest_selection.json` `pool_filter` 字段）。
4. IDV11 run1（并发 batch）与 run2（顺序）的执行环境差异未讨论（Sec 6.4）。
5. Fig forest 建议图内标注 "descriptive only; sets differ, no significance test claimed"。
6. `consistency_audit.json` 的 mechanism_class 词表粗粒度（"OPERATION"），应在正文或附录定义该分类法，否则 "mechanism class agreement" 的含义不明。
7. bare-LLM 臂答案逐字复述目录条目（`baselines.json` 中 "IDV(1): A/C feed ratio step change in Stream 4"）——建议作为 recall caveat 的直接证据引用，强化论文自身的论证。
8. "top-k" 术语与固定-k candidate-list 惯例冲突（Sec 5.2 Metrics 段）。
9. Table 4 caption 已注明 "recorded replays of live runs"，但 bare 臂 9/9 同样是单次执行、同样暴露于 run-to-run 变异——建议与 pipeline 侧的单次执行限定并列表述。
10. ≈2.0h 成本数字来自唯一一次顺序执行（n=1），median 1.9h 来自 event log 汇总——两个估计的独立性宜说明（Sec 7 Cost）。

---

**结论重述**：数字保真性（已豁免项）与内部一致性经抽查无问题；论文的披露纪律在同类工作中处于最高档。但 identifier channel 的披露边界（SKAB 目录名）、CI 的解读框架、forced-commitment 反事实的 ordering 依赖、n=1 稳定性证据四处触及论文的三项头条性质，且论文自己开出的补救处方（neutralized re-run、repeats、filter-disabled 臂）尚未执行——按方法学标准，**大修 (Major Revision)**，置信度 4。
