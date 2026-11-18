# Peer Review Report — Peer Reviewer 2 (Domain Expert)

## Manuscript Information

- **Title**: Trustworthy agentic diagnosis for industrial processes: evidence-graded competing-hypothesis reasoning evaluated against per-fault literature baselines
- **Manuscript**: `paper/main.tex`（682 行 elsarticle 长文；\journal 声明为 Advanced Engineering Informatics；作者告知拟投 ACM CIKM Demo Track——venue 适配问题由他人负责，本报告只做领域审查）
- **Figures inspected**: figures/fig_tep_perfault.png、figures/fig_suite_matrix.png（另核对 supplementary_fe_table1_transcription.md）
- **References**: refs.bib（48 条）

## Reviewer Identity & Focus

化工过程系统工程（PSE）与故障诊断（FDD）方向研究者，TEP 基准使用者，熟悉 SKAB / IndPenSim 数据集、经典多元统计监测与近年 LLM-for-engineering 文献。本次评审聚焦六个方面：数据集使用得当性、与 FaultExplainer 的 Register A 对比公允性、Register B 使用、文献覆盖、术语与机理正确性、对 CIKM 受众的自足性。评审前本人独立核验了以下外部事实（仅在此声明，均只读）：FaultExplainer（arXiv:2412.14492v1）全文 HTML、SKAB 官方 GitHub 仓库（waico/SKAB）README 与目录结构、IndPenSim（Goldrick et al. 2019）批次结构文献记录、本仓库 `scripts/benchmark/cases/benchmark_cases.json` 与 `workspace/diagnostic-runs/` 的场景定义及 run 目录命名。

## Overall Assessment

- **Recommendation: Minor Revision**
- **Confidence: 4**（已独立复核 FE 转录与数据集官方结构；未重算流水线统计量，数字一致性按要求信任已有核验）

**总评摘要**

论文以三数据集 12 场景基准评估一个证据分级、带门禁的 agentic 诊断流水线，并按场景粒度对照 FaultExplainer 的 per-fault 结果。总体印象：领域工作扎实、罕见地诚实——论文主动给出对自身最不利的读数（bare LLM 9/9 vs 流水线 4/9、identity-strict 3/9、top-k 的 token 依赖）。本人逐行核对 FE Table 1 转录，全部准确（含 FE 原文内部 8/11 与失败清单 9 的不一致被论文如实标注）；SKAB 官方标签使用（valve1 吸入侧节流、other/13 两相流气蚀）与官方命名一致；TEP 检测限论述与 Russell/Chiang 文献相符，IDV7 的阀增益-压降算术自洽，IDV4 能量平衡必要性论证物理上正确。主要问题：SKAB "盲测"情景的 run 目录名仍嵌入 "cavitation"，论文对 identifier 通道的披露仅限 TEP，盲测稳健性结论需同等限定；batch 93 文档偏差与流水线冷却水判定之间的机理关系未调和、官方 per-batch 故障描述未引一手出处；stiction、TEP 模型修订、云端 RCA 等方向存在可指名的文献缺口；术语（T²/SPE/UA/XMV/IDV）对非 PSE 受众未作定义。以上均可通过有界修改解决，故建议 Minor Revision。

## Strengths

1. **Register A 转录准确且公允（已独立验证）**。本人对照 arXiv:2412.14492v1 原文逐项核对：IDV1（GPT-4o "6,7,4" wrong / o1-preview "6,1,7" correct）、IDV3/IDV4 反斜杠 unscored、IDV7/IDV11/IDV14 correct（IDV11/14 属 alias class 命中）、聚合 7/11 与 9/11、alias classes {IDV1,2,8}、{IDV3,9}、{IDV4,11,14}、{IDV5,12,15}，以及 General-Reasoning 8/11——与 main.tex 第 94 行及 Table A1 完全一致。论文甚至准确指出 FE 原文内部矛盾（GR 段列 faults 10、13 失败却报 8/11，11−2=9≠8），并选择转录其报告值——这是教科书级的对比公允性处理（§2.2）。
2. **TEP 子集选取逻辑有原则且领域上聪明**（§5.1）：四个故障映射 FE scored outcome、两个故意取 PCA screen 之外（IDV3/4）、冷却水三胞胎（IDV4/11/14）把"形式判别"与"标签回忆"解耦——§6.3 的三形式统计指纹对照（step 指纹 / variance burst with frozen means / quantised limit cycle）是全文最有力的领域证据。
3. **检测限叙事与经典文献及自身复现三方一致**（§1、§7.1、§7.3）：IDV3 弱信号（T² 2.9%/SPE 4.8%）、IDV4 "T² 弱、SPE 强"（48.8% vs 100%）既复现 Russell/Chiang 的经典结论，又顺带解释了 FE 的 T²-only 触发器为何漏掉 IDV4——逻辑闭环完整。
4. **物理机理论证质量高**（§7.5 case study）：IDV4 的能量平衡必要性论证（流量上升+温度守恒 ⟹ 入口温度阶跃或 UA 骤降）正确；UA 子情形以 approach temperature <1.5 K / coolant inlet >93 °C 的定量界收紧排序而非强行消除，是 UA 与 inlet temperature 不可分性的正确表述；IDV7 的 +25.1% 开度 ⟹ 增益 −20.1% ⟹ ΔP 比 0.64 算术自洽（1/1.251≈0.80，0.80²≈0.64）。
5. **对不利结果的诚实核算**（§6.2、§7.3）：bare-LLM 9/9 对流水线 4/9 的中心成本陈述、强制承诺反事实（6/9 但 3 个错误判定）、verdict-type miss（SKAB valve）按 miss 计数而非叙述为成功。
6. **SKAB 官方标签使用忠实**：valve1 = "closing the valve at the flow inlet to the pump"（即 suction-line restriction）与 other/13 = "Two-phase flow supply to the pump inlet (cavitation)" 均与官方仓库一致，论文对 verdict 与排名的描述（truth ranked second）如实。

## Weaknesses

1. **SKAB 盲测的 identifier 通道未披露（主要问题，有实证）**。论文在 §6.3（"Blind-set robustness"）与 §8（"Prompt-knowledge contamination"）反复强调 cavitation 标签 "withheld entirely from all natural-language brief content"。本人核验 `benchmark_cases.json`：brief 级别确实干净（process_description 明示"故障类型不下发"）。但 released run 目录名为 `bench_skab_cavitation_13`——与论文自己为 TEP 披露的 identifier 通道（`tep_d14_reactor_valve_sticking`）完全同构，而 §8 的 identifier 披露仅 scope 到 "every TEP case id"。因此 "cavitation-type 机制排名在幸存集中" 这一盲测结论同样 recall-possible。要求：在 §6.3/§8 将 identifier 通道披露扩展到 SKAB cavitation 情景，把该情景纳入承诺的 neutralised-identifier re-run 范围（或将"最坏 1/9"界的推导同步覆盖此情景），并相应弱化 "blind" 措辞（建议改为 "brief-blind, not identifier-blind"）。
2. **batch 93 的文档-判定机理关系未调和**（§5.1、§6.2）。论文披露 documented deviation 为 acid-dosing 与 heating-water flow 驱动，而流水线判为 cooling-water actuator pinned at minimum flow。IndPenSim 温度控制中加热与冷却水同属一个夹套回路，文档偏差（heating-side）与观察到的冷却侧 pinning 究竟是"下游补偿"还是"独立故障"，二者对 identity-strict 折扣的合理性判断完全不同，但论文未给出这一句机理调和。另外该 "documented deviation" 措辞未给出一手出处（IndPenSim 的 Mendeley 记录/官网 per-batch fault 表），仅称 "taken from the benchmark case definition"；本人两次检索未能从公开文献单独确证 batch 93 的官方故障描述（建议核实），务必引用官方 per-batch 故障清单原文。
3. **文献缺口（可指名）**：valve stiction 检测经典文献缺失（Horch 的 slip-jump/振荡交叉相关法；Choudhury, Shah & Thornhill 的 stiction 专著）——IDV14 的 "actuator fingerprint / limit cycle" 论证（§6.3、Table 5）目前无任何 stiction 文献支撑；TEP 模型修订（Bathelt, Ricker & Jelali 2015）未引，而这决定跨研究可比性（FE 用 Rieth 数据，IDD 的 TEP 数据来源与 onset 约定也应与之对齐陈述）；软件/云 RCA 的 agentic LLM 谱系（论文 §2.2 用一句无引用的话将其 scope out）至少应引 1–2 篇。详见 Missing References。
4. **top-k 仪器的报告粒度在附录不同步**。Table A1 caption 断言 "TEP-subset top-k = 6/6"，但 §5.2/§6.2 的 branch-localised 读数下 IDV3 记 miss（全局 8/9，即 TEP 子集 5/6）。caption 未随附该限定，读者单独读附录会得到最强读数。要求：caption 加一句 branch-strict 读数。
5. **Register B 两处归引需核实**（§7.2）："anomaly-detection F1 of 0.970 (BeatGAN [hartung2023deep])"——BeatGAN 原始出处是 Zhou et al. (IJCAI 2019)，需确认 Hartung et al. 确实在 TEP 上复现了 BeatGAN 并给 0.970（建议核实，必要时双引）；"MLP/GRU/TCN on the 28-class extended TEP taxonomy of Rieth et al."——Rieth 扩展数据集通常表述为 20 类扰动，"28-class" 应核对是否为 Pozdnyakov et al. 的评测类目数而非 Rieth 分类法（建议核实）。Register B 作 reference-only 的定位本身公允、无误用。
6. **术语对目标受众不自足**（§4.2/§5.2 起）：$T^2$、SPE/Q、contribution plot、stiction、UA（总传热系数）、XMV\_n（manipulated variable）、IDV 编号、Stream 4 等对 IM/KM 背景读者均未定义即使用。CIKM Demo 受众需要一段 3–5 句的 TEP/PCA 术语框或脚注（详见 Detailed Comments 焦点 6）。
7. **证据基础的单执行性**（作者已充分披露，仍列为接受条件）：n=9 单执行 + 仅 1 个 repeat pair + expert anchoring 未完成。论文将其 scope 为 "measurement uncertainty on this corpus"，措辞已收敛；但接受应以承诺中的 neutralised-identifier re-run 实际执行（并按 Weakness 1 扩展覆盖 SKAB）为条件。

## Detailed Comments

### 焦点 1：三个数据集的使用

**SKAB**（§5.1、Table 3、§6.3、Fig. casestudy）。官方结构核对无误：valve1 组是"关闭泵入口阀"（论文称 "official label file names suction-line valve restriction"，与 README 语义等价，可接受，但建议注明措辞来自 README 描述而非逐字标签）；other/13 = "Two-phase flow supply to the pump inlet (cavitation)"，论文 "two-phase-flow cavitation" 命名忠实。盲测构造在 brief 层面成立（已核 benchmark_cases.json 的 process_description："本文件来自other实验组（故障类型不下发……）"），但如 Weakness 1 所述，run 目录名 `bench_skab_cavitation_13` 泄漏机制家族名，盲测结论必须加 identifier 限定。另一个应披露的点：SKAB v0.9 的 "other" 组标注精度低于 valve 组（官方 README 自述 v1.0 才计划更精细标注），机制级命名来自 README 文字而非行级 anomaly 列——建议加脚注说明 ground truth 的这一层级差异。verdict-type miss（期望 DETERMINED-only、实际 CS）按 miss 计数，处理诚实。

**TEP**（§5.1、§6.3、§7.1、Table A1、Fig. perfault）。IDV1/3/4/7/11/14 的选取逻辑（每故障映射 FE scored outcome + 两个 screen 外故障 + 冷却三胞胎）是合理且有辩护力的非随机设计，论文对 non-random selection 的后果在 §8 有交代。检测限论述与 Russell et al. 2000 / Chiang et al. 2001 对应准确（IDV3/9/15 处于检测限、IDV4 的 T² 弱检出是文献共识性结论）。onset 处理（row 161 / idx 160 zero-based，§5.1）与经典 TEP 数据惯例一致（fault introduced at sample 160 的 1-based 下一行）；建议加脚注说明该约定，避免读者与 "sample 160" 的常见表述混淆。需要补一句的对照细节：FE 的检测是 90% 方差 PCA + α=0.01 + **T²-only** 的六连触发，而 IDD 复现用了 T²+SPE——这正是 FE 把 IDV4 排除在评分外而 IDD 复现 SPE 100% 检出的原因，建议在 §2.2 或 §7.1 明示这一实现差异，否则读者可能误以为两者对 "PCA-detectable" 的定义一致。

**IndPenSim**（§5.1、§6.2）。batch 93 确属官方 fault batches 91–100（数据集文档 "Batches 91:100: Contain faults resulting in process deviations"，已核实），选其为唯一 IndPenSim 故障场景并配 batch 1 对照，构造成立。但如 Weakness 2：官方 per-batch 故障清单中 batch 93 的准确措辞需一手引用（建议核实：Mendeley 记录 / indpensim.com 批次表 / indpensim_run.m 的 fault reference），并且 acid/heating 驱动 vs 冷却水 pinning 的机理关系需要一句话调和（补偿还是独立故障）。论文对该判定按 identity-strict 折扣（3/9）处理是诚实的，这句调和不会推翻折扣，只会让它可判读。

### 焦点 2：与 FaultExplainer 的 Register A 对比

协议差异披露充分且准确：候选列表、top-3 + alias 接受、PCA 可检测性筛选、基座模型差异均已在 §2.2、§5.2、§5.1 与 Table A1 caption 交代，且用同模型 FE-protocol 复刻（6/6 与 official-prompt 5/6）部分控制了模型混杂——这在同类论文中高于平均水准。"Descriptive, no significance test" 的定位恰当：场景集不同（11 vs 6）、评分协议不同、基座不同，任何显著性检验都会是伪精确；论文连成本不对称（分钟级 vs ≈2 h/场景）都披露了。转录准确性本人已逐项独立验证（见 Strengths 1），包括最容易被转录错的 IDV11/14 的 "correct (within alias class)" 语义与 FE 原文的 "(alias 4,14)/(alias 4,11)" 标记完全对应。唯一建议：Table A1 的 top-k 6/6 需按 Weakness 4 加 branch-strict 限定；Fig. perfault caption 引用 "arXiv:2412.14492" 而 refs.bib 已是 CCE 2025 正式版，建议统一引正式版。

### 焦点 3：Register B

公允、无误用。四个文献数字（TEP 分类 0.887–0.907、BeatGAN F1 0.970、SKAB ensemble 0.85/0.88、leakage-controlled bearing AUROC 0.75–0.93）均以 reference-only 呈现，明确声明 "must not be ranked against our scenario-level metrics"，并给出 detector+RCA 级联的部署读法——这是对 sample-level 与 scenario-level 两个不同问题的正确处理方式。需处理的仅是 Weakness 5 的两处归引核实（BeatGAN 出处、"28-class" 表述）。

### 焦点 4：文献覆盖

三支经典谱系（Venkatasubramanian 三部曲、Qin 2012、Kano 2002、Iri 1979、Yuan/Bauer 因果定位）与信任/自动化谱系（Parasuraman、Lee & See、Heuer、Hill、Chow）覆盖良好，§2.4 的"智力谱系自查"是加分项。缺口集中在四处（详见 Missing References）：stiction 检测、TEP 模型修订与基准使用规范、软件域 agentic RCA（论文 scoping 一句话无引用）、以及 2024–2026 LLM4Diag 的增量覆盖——现有 LLM 列表（FaultExplainer、AgentRCA、Gong、FD-LLM、CausalKGPT、Wen、Xu、Alsaif、Merkelbach、FailureSensorIQ、agentic review）已不薄，但近两年 LLM 应用于过程报警 rationalisation、传感器故障 QA 之外的过程数据诊断的工作仍在快速增长，建议投稿前做一次 6 个月窗口的增量检索并在 §2.2 补 2–3 篇（方向见下，作者/年份不确定者请核实）。

### 焦点 5：术语与机理表述

- **stiction/limit cycle（IDV14，§6.3、Table 5）**："self-excited stiction limit cycle"、"quantised valve stepping at 633/800"、"lag structure tightens 1→5" 的用法方向正确；但 stiction 的经典可辨识特征是 slip-jump 与阀杆运动的 bow-tie 模式，"quantised stepping" 与 slip-jump 的对应关系值得一句说明，并引 stiction 文献支撑 "actuator fingerprint no thermal hypothesis reproduces" 这一关键判别主张。机理结论本身无错。
- **cavitation 通道论证（§6.3）**：间歇流崩 + 泵负载不变 + 双加速度计振动上升的组合论证合理；但 "stagnation heating of +0.23 K" 术语不当——"stagnation heating" 在流体力学中指驻点温升，闭式水回路中 0.2 K 量级温升更自然的解释是泵功耗散或气泡溃灭能量局部耗散，建议改名并加 cavitation 监测（振动/声发射）文献一句支撑。
- **能量平衡必要性论证（§7.5）**：物理正确。冷却剂流量上升且反应器温度受控保持 ⟹ 入口温度上移或 UA 骤降，这一必要性论证成立；UA 子情形用 "UA loss can redistribute LMTD rather than move the observed temperatures" 解释为何不达消除阈值、只收紧排序，是对 UA–inlet temperature 结构不可分性的正确且克制的表述，是全文最好的物理段落。
- **IDV7 算术**：+25.1% 开度 ⟹ 单位开度增益 1/1.251=0.799（−20.1%）⟹ 恒流量下 ΔP 比 0.799²≈0.64，自洽。
- **IDV1 命名**：Table A1 写 "A/C feed-ratio step (Stream 4)"，省略官方表述的 "B Composition Constant" 半句；建议补全以免与 IDV8 混淆。

### 焦点 6：CIKM 受众自足性

论文的领域叙述对 PSE 读者自足，对 IM/KM 读者不自足。具体缺口：(a) $T^2$/SPE 首次出现在 §1 且无定义；(b) IDV 编号在 §1 直接使用，仅靠 §5.1 的故障清单间接可解，建议在首次出现处加一句 "IDV(n): the documented disturbance catalogue of TEP"；(c) UA（§6.3）、XMV\_10（§7.5 首现）、Stream 4（Table A1）无解释；(d) contribution plot（§5.2 提及 SPE-contribution diagnostics）未解释其在经典 FDD 中的角色。这些是 3–5 个脚注的工作量，不动主线。venue 判断不在本报告范围，仅提示：若确投 Demo Track，682 行长文与 elsarticle 格式的适配是另一个量级的问题。

## Missing or Suggested References

| # | 方向（作者/年份/主题） | 用途 | 确定性 |
|---|---|---|---|
| 1 | Horch (1999/2000), Control Engineering Practice, control-valve stiction detection via oscillation cross-correlation | 支撑 IDV14 stiction/limit-cycle 判别论证（§6.3、Table 5） | 高（文献存在；具体卷期请核实） |
| 2 | Choudhury, Shah & Thornhill (2008), Springer, *Diagnosis of Process Nonlinearities and Valve Stiction* | 同上：slip-jump / bow-tie 签名与 "quantised stepping" 的对应 | 高 |
| 3 | Bathelt, Ricker & Jelali (2015), TEP 模型修订（DYCOPS/IFAC） | TEP 模拟版本与跨研究可比性声明（§5.1） | 中高（作者/主题确定，venue 请核实） |
| 4 | Yin, Ding, Xie & Luo (2014), J. Process Control, TEP 上基本数据驱动监测方法对比 | §2.1 "TPM 方法在 TEP 上的对比传统"与 TEP 基准使用规范 | 高 |
| 5 | 云/软件域 LLM agentic RCA：Chen et al. (2024) cloud-incident automatic RCA（Microsoft）；RCAgent (2024)；mABC (2024) | 支撑 §2.2 末句对 software-microservice RCA 谱系的 scope-out，目前该句无引用 | 中（方向确定，具体 arXiv 号请核实） |
| 6 | 泵气蚀振动/声发射监测，如 Alfayez, Mba & Dyson (2005), acoustic emission for incipient cavitation detection | 支撑 SKAB cavitation 场景的振动+温升通道论证（§6.3） | 中（方向确定，作者/年份请核实） |
| 7 | Acosta-Pavas et al. (2024), Computers & Chemical Engineering, IndPenSim 软传感器/批次 91–100 使用 | §5.1 IndPenSim 故障批次的社区使用先例 | 中（检索可见，卷页请核实） |
| 8 | 2024–2026 LLM4Diag 增量：过程报警 rationalisation 与 LLM、传感器故障 QA 之外的时序诊断应用（建议做 6 个月增量检索后补 2–3 篇） | §2.2 覆盖完整性 | 方向确定，具体条目建议核实 |
| 9 | （可选）Zhou et al. (2019, IJCAI), BeatGAN 原始文献 | §7.2 Register B 中 BeatGAN 数字的双引 | 高 |

## Minor Issues

1. refs.bib 键 `agentic2025review` 的年份字段为 2026（Processes 14(13)），键名与年份不一致——仅影响可读性。
2. Fig. perfault caption 引 "arXiv:2412.14492"，正文与 refs.bib 用 CCE 2025 正式版——统一为正式版引用。
3. Table A1 caption "TEP-subset top-k = 6/6" 缺 branch-strict 读数限定（对应全局 8/9 的那个读数），与 §5.2 不同步。
4. §5.1 "sample 161, idx 160 zero-based" 建议加脚注说明与经典文献 "fault introduced at sample 160" 的对应，避免读者误读为不同数据约定。
5. §5.1 未描述 SKAB prepared 文件的构造（valve 情景 "rows 621–927" 暗示长于单个官方 valve1 文件的连续段，应说明 prepared CSV 的来源文件与行范围拼接方式）。
6. §6.3 "stagnation heating of +0.23 K" 建议改名（泵功耗散/气泡溃灭局部耗散），见焦点 5。
7. §7.2 "28-class extended TEP taxonomy of Rieth et al." 的类目数与 "BeatGAN F1 0.970" 的归引请核实（Weakness 5）。
8. §2.2 对 AgentRCA 的数字引用（40.0% Top-1 / 61.5% Top-2）与 "excludes IDV3/9/15 及 IDV16–20" 的表述无法由本人独立核验（contemporaneous preprint），请在 camera-ready 前按其最终版核对。
9. §2.2 "FE's own text names faults 10 and 13 as failing yet reports 8/11"——本人核实属实（FE GR 段明言 faults 10、13 失败且报 8/11），建议把 "9 vs 8" 的差值点破一句，免得读者自己算。
10. Table 6（tab:related）给 FE 的 "Repro. gate: no" 依据的是论文自定义口径（machine-replayed end to end），口径已定义、判定可辩护，但建议脚注说明 FE 评测脚本有公开仓库，避免读者误读为"不可复现"。
11. 仓库工作区中存在 2026-09-17 与 2026-09-18 两个 era 的完整 12 场景 run 目录（与论文 era 纪律一致），camera-ready 的 Data availability 建议明确发布哪个 era 为 canonical，避免审稿人混淆。
