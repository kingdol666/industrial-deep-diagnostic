# Peer Review Report — Journal-Fit Reviewer (CIKM Demo Track)

## Manuscript Information

- **标题**：Trustworthy agentic diagnosis for industrial processes: evidence-graded competing-hypothesis reasoning evaluated against per-fault literature baselines
- **稿件 ID**：IDD-2026-Demo-01（内部编号）
- **作者**：ZhangHaoZheng（USTC，单作者）
- **当前形态**：elsarticle preprint 10pt，681 行 LaTeX 源文，编译约 50 页；`\journal{}` 字段指向 Advanced Engineering Informatics（main.tex L44）
- **审稿轮次**：Round 1
- **日期**：2026-09-20
- **目标去向（作者指定）**：ACM CIKM 2026 Demo Track（约 4 页正文，ACM 双栏，不含参考文献）

## Reviewer Identity & Focus

本人长期担任 CIKM/SIGIR 应用型 Track 的资深编辑，研究方向为工业 AI 与知识系统。本次评审聚焦五个维度：(1) venue fit——工作内容与 CIKM（尤其是 Demo Track 的"可现场演示的系统"定位）的匹配度；(2) 篇幅与格式改造的可行路径；(3) 新颖性声明的定位与表述；(4) demo 可演示性（演示什么、怎么演、在线系统与仓库支撑）；(5) 可复现性声明与社区价值。数字核验已由独立核验完成，本报告不重复。

## Overall Assessment

### Recommendation

**Major Revision**（针对"以当前形态投 CIKM Demo Track"这一目标；以当前形态投出会被 desk reject——格式与篇幅完全不合规，但工作内容本身经改造后是有竞争力的 demo 素材）。

### Confidence

5（本人通读全文与全部图件，且长期评审同类系统型投稿）。

### 总评摘要

这是一篇异常诚实、工程完成度极高的系统长文：IDD 以九段 gated agentic pipeline 交付可审计的工业 RCA（evidence grading L1–L7、三态 capped verdict、物理验证、机器可查的 evaluation contract），并以 12 场景 benchmark、model-controlled ablation（bare LLM 9/9 vs pipeline 4/9）、seeded re-execution 与 byte-identical 确定性套件支撑其主张。作为 CIKM Demo Track 投稿，其"活系统"（web app + REST API + 14 engines + audit plane）与远超平均水准的可复现性是真实资产。但当前稿件是 50 页 Elsevier 期刊格式，与 4 页 ACM 双栏 demo 论文之间隔着一整次 re-platforming（acmart、约 92% 内容裁剪、`\journal{}` 移除、参考文献格式重排）；且现有 9 张图全是示意图与数据图，没有一张 web UI 截图，无 hosted demo、无视频、无 Docker 打包说明——这些是 demo track 的硬性期待。核心叙事（"pipeline 准确率低于 bare LLM，卖点是可审计过程"）在 demo 语境下需要重写为积极框架。改造路径清晰可行，故判 Major Revision；同时建议认真评估 CIKM Applied Research Track 是否更利于保住 evaluation-contribution 这一更深层的贡献。

### Strengths

1. **真实的活系统，而非幻灯片软件**：架构图（Fig. 1, fig_architecture）与 §2.1（L130–141）显示的 web application（Vue 3 + Express，SSE/WS）、版本化 REST API（§7.1, L601）、14 个可替换 engine 与 mock engine 的 CI 路径（§3.4, L215）构成可现场演示的完整软件。Demo track 的第一条硬要求可以满足。
2. **可复现性纪律远超 demo track 平均线**：truth isolation、SHA-256 fingerprinting（C2, §5）、14-artifact completeness gate（Table 5, L296–323）、确定性套件 45/45 byte-identical 复跑（§6.3, L566）、seeded random draw（seed 1003818694, §6.4, L569）、仓库随稿发布（Data availability, L630）。这段几乎可以原样裁进 demo 论文的 reproducibility 段。
3. **诚实且自缚的主张**：作者主动报告 bare-LLM 9/9 高于 pipeline 4/9（§6.3）、identity-strict Top-1 3/9（§6.2, L387）、identifier-recall 最坏情形可至 1/9（§7, L588）。这种自我设限在审稿中极具信用，也是 demo 演讲的差异化卖点。
4. **清晰的新颖性定位**：Table 1（tab:related, L99–118）把 IDD 与 FaultExplainer、AgentRCA（2026-07 同期工作）在五个维度上对齐，"cap-enforced three-state verdict + machine-verifiable evaluation contract 为全部引用系统中独有"的声明有据可查，且 §2.4（L124）对 Heuer ACH / Hill / Chow / Parasuraman 的思想源流逐项致谢，避免了 over-claim。
5. **demo 叙事天然存在**：capped verdict "命名那个能裁决分歧的测量"（IDV4 案例链，§6.5, L581；fig_trace 的 stage-by-stage 执行解剖）是现场演示中最有戏剧性、最容易在 5 分钟内讲清的内容。
6. **图件质量高**：fig_trace 与 fig_architecture 信息密度与可读性俱佳，可直接作为 demo 论文的主图候选。

### Weaknesses

1. **格式与篇幅完全不匹配（致命，必须重建）**：当前为 elsarticle preprint、约 50 页、含 CRediT / competing interest / funding 等 Elsevier 专版块（L620–633），`\journal{Advanced Engineering Informatics}`（L44）直接暴露期刊目标。CIKM Demo 要求 acmart `sigconf`、约 4 页正文 + 参考文献。这不是删减问题，是重排平台问题。
2. **缺少 demo track 的标准配套物**：9 张图（figures/ 目录）均为流程示意与 matplotlib 数据图，无一张 web UI 截图；无 hosted demo URL、无演示视频、无 Docker/一键复现说明（Data availability 只给 GitHub 链接，Zenodo DOI 承诺"接收后 mint"，L630）。对 demo track 而言 UI 截图与演示入口近于硬性期待。
3. **现场演示的时效矛盾未处理**：全 pipeline 单场景约 2.0 h agent time（§7 Cost, L594），demo session 内不可能现场跑完整推理层。稿件没有（也不可能有）一段"如何在 10–20 分钟内演示这套系统"的设计；mock engine 的 CI 快速路径（L603 末句提及）是实现现场全流程演示的关键杠杆，但从未被组织成 demo 方案。
4. **核心结果的 demo 语境风险**：headline 数字（4/9 Top-1、bare LLM 9/9）是防御性、负面倾向的结果。4 页 demo 论文没有空间展开 identity-strict / LOTO / branch-localised 多重读数（§6.2, L387），若压缩不当极易被 demo 评委误读为"系统不如一次裸调用"。demo 版需要一条一句话级别的重述（如 "we demonstrate the auditability that a bare LLM call cannot provide, and quantify its resolution cost"）。
5. **相关工作体量期刊级**：§2 全节约 2.5 页 + Table 1 + 三段 FE 协议细节（L94, L97），demo 版只能保留 AgentRCA/FE 各一句的定位句；多重 scoring register 的方法论讨论（§5.3 Comparison Protocol）在 demo 版基本放不下。
6. **作者信息与匿名政策待核对**：单作者真实署名（L50–52）+ 指向真实 GitHub 账号（L630）。CIKM 近年 research track 为 anonymous 评审，demo track 政策历年有别——投稿前必须对照当年 CFP 确认 demo track 是否要求匿名化，当前稿件两边都不靠。

## Detailed Comments

### 1. Venue fit

CIKM Demo Track 要的是"对 CIKM 社区有价值的、可现场演示的系统"。本工作的知识管理属性其实相当贴合：ontology asset store 与 schema-fingerprint 快速复用（§3.2, L139）、stage-authored provenance-labelled artifacts（C3）、evidence grading 作为知识质量策略、event log → 单一 PASS 裁决的 audit plane——这些本质上是"agentic 知识工作的可审计治理"，对 CIKM 的 knowledge systems 读者比对纯工业过程控制读者更有吸引力。工业 RCA 只是载体，demo 论文应把"知识 artifact 的机器可查治理"提到第一行来卖。

需要警惕的一点：demo track 不为"负结果 + 评估方法论"留篇幅。稿件的另一半贡献（evaluation contract、多重 instrument 读数、contamination 披露）在 demo 里只能压成一段 + 仓库链接。这引出第 7 点的方向性问题。

### 2. 篇幅与格式改造路径

50 页 → 4 页约需 92% 裁剪，但结构是清楚的，4 页 demo 论文的合理骨架为：

- **0.5 栏**：问题 + 系统一句话 + 新颖性声明（§1 的三障碍压成一段）；
- **1 栏**：架构——fig_architecture 需重绘为单栏宽（现为全页横图，ACM 双栏下需拆分或改竖排）或改用 fig_trace 简化版；Table 3（checkpoints）可压成一句"9 个机器谓词门"；
- **1 栏**：demo walkthrough——**必须新做一张 web UI 截图**（运行视图/证据链视图/HTML 报告三选一或拼图），配 5 步演示脚本；
- **0.75 栏**：结果-in-brief——只保留一个数字组（4/9 resolved、9/9 top-k、0/3 false alarm、bare-LLM 9/9 对照）+ 一句 capped-verdict 命名测量的案例（引用 IDV4 链）；
- **0.5 栏**：reproducibility 声明 + 仓库/视频/打包链接；
- **0.25 栏**：limitations 一段（contamination、单模型族、author-designed rubric 三句）。

技术动作：`\documentclass[screen,review,nonacm]{acmart}`（按 CFP 选 anonymous 与否）；删除 L44 `\journal{}` 与全部 Elsevier 版块；`elsarticle-num` → ACM-Reference-Format；标题需从 18 词压到 10 词左右（现标题是期刊句法）。algo（Algorithm 1, L242–258）与 Table 5（14 artifacts）建议只留后者的一句话概括。

### 3. 新颖性 / 贡献定位

demo 论文的新颖性声明必须一句话可复述："首个把工业 LLM-RCA 做成 cap-enforced 三态结论 + 机器可查证据链 + 执行证明的可现场演示系统"。这个声明在 §2.2/Table 1 已有支撑，迁移时注意两点：(a) AgentRCA（L97）必须保留一句，因为它是最近邻同期工作且 demo 评委可能当场提及；(b) 不要把 top-k 9/9 写成 demo 的主指标——demo 语境下评委只看一行字，top-k 是 set-membership bound（L56 摘要已自我限定），单独出现会误导；主指标应写 resolved Top-1 与 zero false alarms，并直接挂上"以分辨率换可审计性"的框架。

### 4. Demo 可演示性（演示什么、流程、在线系统与仓库）

这是当前稿件最大的可执行缺口，建议按如下脚本设计并在 demo 论文中明写：

- **演示 1（秒级）**：engine 层预检——前端切换 engine，触发 `400 HARNESS_UNKNOWN` / `409 HARNESS_UNAVAILABLE`（L215），展示 typed error contract；
- **演示 2（分钟级，现场全流程的关键）**：用 `mock` engine 跑通完整 9 段 gated pipeline——稿件自己披露"benchmark protocol 与 scripted mock engine 完全一致地执行"（L603），这意味着现场可以跑出一次真实过 gate 的完整执行而无需 2 小时与外部模型；这是现成的 demo 杠杆，目前埋在一句防御性披露里，应升格为演示主桥段；
- **演示 3（主体）**：浏览预计算的 TEP IDV4 run——fig_trace（L378–383）的每一行对应一个可点击的 artifact（diagnosis.json、judge_feedback.json、capped verdict 0.63 与被命名的 cooling-water inlet thermocouple、ENDORSED 报告、html_review pass），落到 `diagnostic-report.html` 交付物收尾；
- **演示 4（可选加分）**：确定性统计 stage 现场跑单场景（秒级，L366），展示 byte-reproducible 层。

配套要求：2–3 分钟视频（demo track 惯例，以当年 CFP 为准）；Docker Compose 一键起 backend+frontend+mock engine（仓库 AGENTS.md 已有 `ind-diag` 一键脚本，包装成本很低）；若可能提供限时 hosted 实例。Zenodo DOI 应在投稿时 mint（"接收后 mint" 在 demo track 是减分项，L630）。

### 5. 可复现性声明

demo 论文要求一段明确的 reproducibility statement，本稿素材现成且强：released repo（含 scenario 定义、grading keywords、编辑史）、SHA-256 fingerprints、seeded draw 可重放、45/45 byte-identical 确定性套件、两层 reproducibility semantics 的诚实区分（§5 末, L325）。建议 demo 版逐条压缩为一个四句段落 + 仓库链接，并补一句 license 与一键复现命令（当前稿件通篇未提 license）。

### 6. 目标读者价值

对 CIKM 读者：这是一套"如何让 agentic LLM 系统的产出可审计、可复现、可退回（escalate）"的完整参考实现，其 artifact/provenance/gate 设计可移植到任何高风险域的 agentic 系统；对工业读者：demo 直接回答"这东西在我的 historian 导出上怎么跑"（§7.1）。demo 论文应对两类读者各给一句明确的 takeaway。

### 7. 其他发表选项（应向作者明确提示）

以本稿的深度（方法 + 评估框架 + benchmark + 诚实消融），**CIKM Applied Research Track（full paper）可能是比 Demo 更有利的去向**：demo 的 4 页装不下 evaluation contract 与多重 instrument 读数，而这些恰是稿件最强的学术贡献；research track 版只需压到 CIKM 正文页限（约 9 页双栏），裁剪压力小得多，且完整保留与 AgentRCA/FE 的方法论对比。Demo track 的优势是早期曝光与系统复用。第三个选项是维持现状投期刊（`\journal{}` 已指向 AEI，且 L97 引了同刊近期工作，匹配度合理）。三者取一取决于作者优先级：求快求曝光 → Demo（按本报告改造）；求学术贡献完整 → CIKM applied research；求篇幅自由 → AEI。**不建议**把本稿先投 demo 再扩写成 research 的同届双投（违反 CIKM 政策，需二选一）。

## Suggestions for Improvement（可执行清单，按优先级）

1. **P0 — 决断去向**：在 Demo 与 Applied Research Track 之间做出选择；若选 Demo，接受"evaluation contract 降为一段 + 链接"的代价。
2. **P0 — Re-platform**：迁移到 acmart `sigconf`，4 页正文；删 `\journal{}`（L44）与 Elsevier 版块；参考文献转 ACM-Reference-Format；对照 CFP 确认匿名要求后处理 L50–52 与 L630 的身份信息。
3. **P0 — 补 demo 配套物**：制作 2–3 分钟演示视频；截取 web UI 运行视图/证据链视图截图（至少 1 张，建议与 fig_trace 呼应）；Docker Compose 一键启动（backend+frontend+mock engine）；投稿时 mint Zenodo snapshot；补 license 声明。
4. **P0 — 撰写演示脚本入文**：按 Detailed Comments §4 的四段式（engine 预检 → mock-engine 现场全流程 → 预计算 IDV4 证据链浏览 → 确定性统计现场跑）写明"demo session 内演示什么、各环节耗时"。
5. **P1 — 重写新颖性与主指标表述**：一句话新颖性声明；主指标行写 resolved Top-1 4/9 + 0 false alarms + "以分辨率换可审计性（bare-LLM 9/9 对照）"；top-k 9/9 必须带 set-membership 限定词或移入仓库注记。
6. **P1 — 图件改造**：fig_architecture 重绘为双栏单栏宽版本；fig_trace 简化为 demo walkthrough 主图（或替换为 UI 截图）；只保留 1 张结果图（建议 fig_suite_matrix 或 fig_calibration 的简化版）。
7. **P1 — 压缩标题与摘要**：标题 ≤10 词；摘要 ≤150 词，删除 identity-strict/LOTO 等多重读数（移入仓库 README 或附录链接）。
8. **P2 — limitations 压缩段**：三句——TEP 标识符 recall 通道（L588）、单模型族单部署（L368）、rubric/keywords 为 author-designed 且专家锚定待做（L592）。
9. **P2 — 保留一句 AgentRCA 与 FaultExplainer 定位句**（L94/L97 浓缩），防止 demo 答辩被最近邻工作问倒。

## Minor Issues

- L56 摘要约 340 词且单段，远超 demo/ACM 常规；即使投 research track 也建议分段或精简。
- L50–52 作者名 "ZhangHaoZheng" 拼写连写，且单作者投稿在 demo track 需注意 CFP 对作者资格无额外要求（核对即可）。
- Table 4（tab:overall, L391–419）行 "Capped competing_set verdicts, true mechanism ranked in all five — 5 of 9 faults" 与上一行 top-k 9/9 信息重叠，压缩版中应合并。
- fig_architecture.png（1.2 MB）等图件体积偏大，ACM 出版流程下建议控制位图尺寸或转矢量。
- L441 注释 "% review-mode double spacing..." 为内部工作注释，投稿版应清理；同类内部注释（L153–154、L217–218、L468–469、L654–655）一并清理。
- L603–606 之间存在连续空行（两处多余空白），排版源文件应整理。
- 正文使用 British spelling（behaviour/localisation/favour），ACM 不强制美式，但需全文一致——目前一致，迁移时保持。
- 附录 Table A1（L656–678）在 demo 版中无立足之地，其信息（FE 逐 fault 对照）应留在仓库的机器可读版本并在文中链接。
- Data availability（L630）"will be minted on acceptance" 改为投稿时提供 snapshot DOI（见 P0 清单第 3 条）。
- 视频与仓库 URL 建议在 demo 论文首页脚注（ACM 格式的 link 约定）给出，而非仅在正文末尾。

---

**一句话结论**：这是一份罕见地诚实、工程上无可指摘的系统长文，但其当前形态（50 页 Elsevier 期刊稿）与 CIKM Demo Track（4 页 ACM 双栏 + 活演示 + 视频/UI 截图/打包复现）之间需要一次彻底的 re-platforming 与内容重选；工作内容本身值得做成 demo（mock-engine 现场全流程 + IDV4 证据链浏览是现成的演示主线），但作者应先在 Demo 与 Applied Research Track 之间做出战略选择——若追求学术贡献的完整表达，applied research track 是更优归宿。
