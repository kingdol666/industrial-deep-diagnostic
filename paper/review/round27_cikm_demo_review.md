# Round 27 — CIKM Demo Track 投稿前审稿包（五席 + 编辑合成）

- 日期：2026-09-20
- 评审对象：`paper/main.tex`（682 行 elsarticle 长文，编译 50 页；`\journal{}` 指向 Advanced Engineering Informatics）
- 目标去向（作者指定）：ACM CIKM Demo Track
- 审稿团：Journal-Fit Reviewer (EIC) + R1 方法学 + R2 领域 + R3 跨学科视角 + 魔鬼代言人（DA），编辑合成 1 份
- 数字保真预检：论文全部实验数字在审稿前已逐项对照 `results/benchmark/` 发布产物核验一致（见文末附录 A），审稿席对此豁免数字复核

---

## 编辑决定信（Editorial Decision）

### 决定：Major Revision（针对"以当前形态投 CIKM Demo Track"）

五席建议：EIC **Major**（venue）/ R1 **Major**（方法学）/ R2 **Minor**（领域）/ R3 **Major**（视角）/ DA **1 CRITICAL + 5 MAJOR（阻断直接接收）**。

仲裁说明：R2 的 Minor 是仅就领域质量而言；但 R2 自己把"neutralised-identifier re-run（扩展到 SKAB）实际执行"列为接受条件，属实质性新执行，与 Major 一致，故 editorial 取 Major。

### 共识发现（跨席归并）

**[CONSENSUS-4] Venue/格式错位（最优先）**
50 页 elsarticle 期刊长文 vs CIKM Demo 约 4 页 ACM 双栏 + 活演示 + 视频/UI 截图/打包复现。当前形态送审即 desk-reject。EIC 与 R3 均建议：先决定去向——求快求曝光→按 EIC 清单做 demo 改造；求学术贡献完整→CIKM Applied Research Track（约 9 页，evaluation-contribution 这条最强贡献能保住）；求篇幅自由→AEI（`\journal{}` 已指向）。不建议同届双投。

**[CONSENSUS-3] Identifier 通道披露范围过窄（有实证，必须修）**
论文仅对 TEP 披露 run 目录名嵌入机制名；R1 与 R2 独立核验 `benchmark_cases.json`/run 目录：9 个故障 case_id 中 7 个直接命名机制，包括被论文赋予"blind-set robustness"唯一证据地位的 `skab_cavitation_13`。要求：(i) §6.3/§8 披露扩展到 SKAB；(ii) 承诺的 neutralised-identifier re-run 覆盖 SKAB case-id；(iii) "最坏 1/9"界同步重述（当前低估）；(iv) "blind" 措辞改为 "brief-blind, not identifier-blind"。反向行为证据（若 recall 主导，cavitation 应排首位，实际排第 2/2）应在文中引用作为缓和。

**[CONSENSUS-3] "no control raises a false alarm" 的证据实为 n=1 blind control**
3 个对照中 2 个的 brief 直接告知"无故障基线"。摘要/Table 6/Fig 4 以未限定 3/3 呈现，高估判别证据约 3 倍。要求摘要补 "(1 of 3 blind)" 或等价限定（DA MAJ-2 同此，补注即降 MINOR）。

**[CONSENSUS-3] 摘要/正文 register 落差（对己不利的限定只留在正文）**
DA MAJ-5 + R1 W7 + R3（trustworthy 标题）。三处核心：(i) 摘要 4/9 未带 identity-strict 3/9 与 LOTO 3/9–4/9；(ii) 摘要/结论以已确立口吻卖 "process quality"，而 §9 自评 "architectural properties, not yet measured outcomes"；(iii) 标题 "Trustworthy" 全文未定义、证据支撑的是 auditable。修法：摘要携带限定语；§1 末显式定义 trustworthy := auditable + capped honesty（或改标题）。

**[CONSENSUS-2+] top-k 仪器问题（含 DA CRITICAL，见下裁决）**
R1 W6（自产变长 k、无大小惩罚、判别力近饱和、建议改名 truth-in-survivor-set rate 并附 survivor-set 大小分布）与 DA CRIT-1（specificity 未测）叠加。

**[CONSENSUS-2] Capped verdict 的"消费语义"缺失**
R3 主攻（操作员拿到 0.60 竞争集后的 interim guidance / decision-rights / capped base rate 对信任的塑造）+ DA 盲区 1。要求 §9 增补 "Operating semantics of capped verdicts" 小节；Fig 6 的 "0.65 ‖ 0.60" 呈现需注明"cap 内排序无置信含义"。

**[CONSENSUS] 优点（各席一致）**
披露纪律在同类工作中处于最高档（5/5 席）；model-controlled ablation 的"过程质量 vs 准确率"框架是本文最好的想法（R1/DA/EIC）；C1–C5 评估契约 + verdict typing 对 agent 评估社区有外溢价值（R1/R3）；FE Table 1 转录经 R2 逐项独立核对准确、包括指出 FE 原文内部 8/11 与失败清单的不一致；form-discrimination（冷却三胞胎）是全文最有力的领域证据（R2）；可复现性素材（seed 重放、45/45 字节级确定性、SHA-256、leakage sentinel）远超 venue 平均线（EIC/R1）。

### DA CRITICAL 显式裁决（Iron Rule #4）

**CRIT-1（top-k 无 specificity 控制，却承载"失败是 resolution 而非 localisation"的核心二分与 "lower bound on resolution" 表述）——裁决：VALIDATED（未解决），阻断直接接收，列为修订 P1。**
裁决理由：论文确已披露 top-k 的结构性偏置（family-level membership、≥3 假设强制、token 源自同一 cause table），但披露止于"读作 family-level"；全文无 enumeration null / specificity 对照，而 line 586 仍称 9/9 为 "a lower bound on resolution"、line 387 由此建立 dichotomy。strictness ≠ specificity 的指控成立：低特异性仪器评分再严格也不构成 resolution 下界。修复路径（择一或并行）：(a) 报告 enumeration/对照条件下的 top-k 期望值；(b) 将 dichotomy 全面改写为 family-level set membership 并撤回 "lower bound on resolution" 表述；(c) 补一个 specificity mini-control。此修复为表述层，不动摇论文披露底座，故不升级为 Reject，而作为 Major Revision 的核心修订项。

### DA MAJOR 逐条去向

- MAJ-1（line 432 "只有统计能复现三形式" vs line 588 "记忆 cause table 即可复现标签" 直接矛盾）→ 采纳为 P1：改写 line 432 为弱声明（"与数据一致的读数不依赖对 channel label 的单独回忆"）或就地披露记忆含动态形式。
- MAJ-2（blind control n=1 未限定上摘要）→ 采纳为 P1（与 CONSENSUS-3 合并）。
- MAJ-3（缺 script-only/identifiability 对照臂）→ 采纳为 P2：或补臂、或将 §9 "most transferable finding" 归因降为假设。指出 IDV4 UA-fork 量化是反例级推理增量（DA 自认），可作辩护但单例不归因五案例。
- MAJ-4（determination 阈值/自由常数无敏感性分析）→ 采纳为 P2：加阈值敏感性小实验或在 limitation 明列；forced-commitment 反事实建议补一句随机 ordering 期望 ≈6.1/9 的稳健性说明（R1 核算，与 6/9 接近，说明结论对 ordering 假设稳健——对作者有利，值得写）。
- MAJ-5（摘要 register）→ 采纳为 P1（与 CONSENSUS-3 合并）。

---

## 修订路线图（Revision Roadmap，优先级排序）

### P0 — 去向与载体（投稿前必须）
1. 在 CIKM Demo / CIKM Applied Research / AEI 三者间做出决断（EIC §7 给出三者取舍逻辑；不建议同届双投）。
2. 若走 Demo：acmart `sigconf` 重排平台、压 4 页；删 `\journal{}` 与 Elsevier 版块；补 demo 配套物——2–3 分钟视频、≥1 张 web UI 截图、Docker Compose 一键启动、投稿时即 mint Zenodo DOI、license 声明；演示脚本入文（EIC 四段式：engine 预检 400/409 → **mock engine 现场跑通全 pipeline（现成杠杆，L603 一句防御性披露应升格为演示主桥段）** → 预计算 TEP IDV4 证据链漫游 → 确定性统计现场秒级跑）。R3 补充：现场"篡改 artifact 让 gate 当场 FAIL"是审计主张最强的 30 秒论证；demo 不演 RAG、不以 trustworthy 为标题词、首选 SKAB 场景而非 TEP-only。
3. 若走 research/AEI：按 R1 §7 的"最小不可牺牲集"压缩方法学内容（单次执行披露、9/9-vs-4/9 消融、identifier caveat、契约定义、rubric 定位声明）；多重读数合并为一张小表。

### P1 — 声明与披露修正（全部为文本工作）
4. CRIT-1：specificity 报告或 dichotomy 改写（见上裁决）。
5. MAJ-1：line 432 与 line 588 矛盾调和。
6. Identifier 披露扩展至 SKAB（含 1/9 界重述、"brief-blind" 措辞、cavitation 排位反向证据入文）。
7. 摘要/Table 6/Fig 4：identity-strict 3/9 与 "(1 of 3 blind control)" 限定；"process quality" 携带 "architectural, not yet measured" 限定。
8. trustworthy 定义或改标题；§1 末一句话立起定义。
9. 执行已承诺的 neutralised-identifier re-run（扩展覆盖 SKAB case-id）——R1 P1 / R2 接受条件。

### P2 — 结构性补写与小实验
10. "Operating semantics of capped verdicts" 小节（interim guidance、decision-rights、capped base rate 与信任校准；Fig 6 排序语义脚注）。
11. "Semantics of reported confidence" 段：confidence 为 protocol ordinal、无频率语义；conformal risk control 作为 COMPETING_SET 的形式化 future work。
12. 信任边界表（假设→机制→残余风险→补救），集中 §3.4/§5/§9 分散披露。
13. 阈值敏感性说明或小实验；forced-commitment 的随机 ordering 稳健性一句。
14. script-only/identifiability 对照臂（或降格归因表述）；filter-disabled 臂（已预注册）。
15. L1–L7 mislabel 对抗微实验（单案例即可，正负结果都有价值）。
16. §9.1 改排 demonstrated/projected/untested 三栏；RAG 双向标注 unvalidated（其 13/13 失败反而是污染叙事的最强证据，应在 contamination 段显式引用）；2h 成本的 task-fit 边界表。
17. §2.4 补 Sheridan-Verplanck 定位、Bainbridge、automation bias/trust repair；ethics/governance 小节（SIS/IEC 61511 边界一句话、model card、human-AI 同回路承认）。
18. 文献补引（R2 清单）：Horch / Choudhury-Shah-Thornhill（stiction）、Bathelt-Ricker-Jelali 2015（TEP 修订）、Yin et al. 2014、云 RCA 谱系 1–2 篇、气蚀声发射、BeatGAN 双引 Zhou et al. 2019；"28-class" 归引核实；6 个月 LLM4Diag 增量检索。
19. 术语框（T²/SPE/UA/XMV/IDV/Stream 4）3–5 句给 CIKM 受众。

### P3 — 图面与卫生（本次一致性核对发现的 3 处 + 各席 minor）
20. fig_calibration 图例文字重叠（"DETERMINED (non-CS)" 与 "capped COMPETING_SET" 挤压）。
21. fig_casestudy y 轴标签截断（"Volume Flow RateRMS (L/min" 缺右括号、"RateRMS" 连写）。
22. fig_benchmark / fig_suite_matrix 图内大段 prose 与 LaTeX caption 重复，建议裁剪图内文字（demo 版尤其）。
23. Table A1 caption 补 branch-strict 读数限定（6/6 → 同步 §5.2 的 8/9 口径）；fig_tep_perfault 的 "PCA detectable: no"(IDV4) 与正文"我们复现 SPE 100% 检出"之间加半句澄清（列指 FE 的 T²-only 筛）。
24. 内部注释清理（L441、L153–154、L217–218、L468–469、L654–655）；L603–606 连续空行；refs.bib `agentic2025review` 键名年份不一致；British spelling 保持全文一致；二 era run 目录的 canonical 指针在 Data availability 明示。

---

## 附录 A：数字与绘图一致性预检（审稿前已完成）

### 数字层：论文实验部分 ↔ results/benchmark/ 产物 — 全部命中
- **metrics.json**：Top-1 4/9 (44.4%) CI[18.9,73.3]；top-k 9/9 CI[70.1,100]；controls 3/3 零误报；calibrated 8 / overconfident 0；verdict-type 8/9；rubric 94.6（9×100、2×85、1×65）；分数据集 0/2、3/6、1/1 ✓
- **全部 Wilson 95% CI 独立复算正确**：4/9→[18.9,73.3]、3/9→[12.1,64.6]、8/9→[56.5,98.0]、9/9→[70.1,100]、3/3→[43.8,100]、4/4→[51.0,100]、7/11→[35.4,84.8]、9/11→[52.3,94.9]、3/6→[18.8,81.2] ✓
- **gradings/*.json（12 场景）**：verdict 与置信度逐一吻合（DET 0.91/0.78/0.80/0.82；CS 0.60/0.60/0.55/0.63/0.60；对照 0.86/0.90/0.93 →"0.86–0.93"）✓；judge 均值 94.67→"94.7"、range 90–98 ✓
- **baselines.json**：bare-LLM strict 9/9；对照覆盖 2/2 零误报（TEP 对照未跑 bare）；FE-replication 6/6；FE-official 5/6（miss=IDV4）；FE 12 场景 PCA 检测率与 fig_suite_matrix 六列逐一相符（IDV3 2.9/4.8、IDV4 48.8/100、对照 1.0–1.1%）✓
- **retest**：seed 1003818694（mulberry32）抽中 tep_d11；run1 202609171639527=0.62 / run2 202609172247007=0.60；Δconf 0.02；XMV_10；ENVIRONMENT；CONSISTENT；11 个 re-run contract outstanding ✓
- **suite_determinism.json**：45/45 identical、DETERMINISTIC ✓；**repro_report.json**：153/153 fingerprint、零 drift ✓
- forced-commitment 反事实 6/9-with-3-wrong 与 capped 集排序记录逻辑自洽 ✓

### 绘图层：六张数据图 ↔ 产物 — 全部一致
fig_benchmark（分数据集条 + 12 个 rubric/judge 点）、fig_calibration（12 根置信度条 + 0.70/0.90 线 + 两处越线标注）、fig_consistency（13 markers + retest 对 + 审计表）、fig_forest（6 行 CI）、fig_tep_perfault（对照矩阵）、fig_suite_matrix（全矩阵）与正文及产物无一处数值冲突；fig_casestudy 标注数字（−3.13%、p=5.7e-158、rows 621–927、0.327 bar、H1 0.65/H2 0.60）与正文一致。

### 图面瑕疵（不影响数据正确性）
1. fig_calibration 底部图例两条目文字重叠；
2. fig_casestudy y 轴标签截断/连写；
3. fig_benchmark、fig_suite_matrix 图内嵌大段说明文字与 LaTeX caption 重复。

---

## 五席报告全文（独立文件，未改动）

- [round27_seat1_eic.md](round27_seat1_eic.md) — Journal-Fit Reviewer（CIKM Demo venue 适配）：Major Revision，confidence 5
- [round27_seat2_r1_methodology.md](round27_seat2_r1_methodology.md) — R1 方法学：Major Revision，confidence 4
- [round27_seat3_r2_domain.md](round27_seat3_r2_domain.md) — R2 领域专家：Minor Revision，confidence 4
- [round27_seat4_r3_perspective.md](round27_seat4_r3_perspective.md) — R3 跨学科视角：Major Revision，confidence 4
- [round27_seat5_devils_advocate.md](round27_seat5_devils_advocate.md) — 魔鬼代言人：1 CRITICAL + 5 MAJOR
