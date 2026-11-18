# Round 34 — 实验补全、审稿与修订记录（2026-09-22）

对象：paper/main.tex（56 页）。本轮主题：**实验部分讲述完整**——把 baseline 对比的逐场景结果
（仓库已有但未入文的数据）写入论文，随后 4 席资深 AEI 审稿人独立评审 → 裁决 → 修订 → 复审。

## A. 实验补全内容

1. **§8.3 新增逐场景 baseline 解读段**（3 组对比，全部溯源自 released records）：
   - SKAB 空化：bare-LLM 将空化排第一，IDD 封顶为 2/2（空化次位、阀门侧统计优先）——同一机理，但只有封顶形式说明了"无法分离"并命名缺失通道；
   - IndPenSim batch-93：bare 命名 acid-feed pH 环路、PCA 贡献榜首为加热水流量——都比 IDD 的 cooling-loop 读法更贴近文档化偏差描述，这正是 identity-strict 折扣的原因；三臂分歧即三态协议要暴露的歧义；
   - PCA 贡献为变量级：IDV4/11 的执行器 XMV_10 浮现；IDV14 的列表由 XMEAS_21（受影响环路）领衔但执行器 XMV_14 本身缺席——detection–diagnosis gap 最具体的形态；SKAB 阀门流量列第三；无置信度/判定态/排除链。
2. **附录新增 Table A2**（12 行 × 4 列）：逐场景 bare-LLM 实际 top-1 答案（缩略英文 gloss，注明原文含一条中文）+ PCA SPE 贡献 top-3 + IDD 判决并排；覆盖缺口如实标注（TEP 对照未跑 bare）；对照行标注名义误报窗。

## B. Round-34 首轮审稿结论：4/4 Minor Revision（R1 conf4、R2 conf4、R3 conf4、R4 conf4）

四席实验完整性判定一致："基本完整+缺口"；数字抽查（含 Wilson CI 复算、seed 重放、45/45、
逐场景置信度、IDV4 SPE 100% 等）全部吻合。缺口集中于已预注册实验未执行
（identifier 重跑 ≈16h、script-only 臂、k≥3 重复、专家锚定）——与前轮相同，已披露且无已发表数字依赖。

## C. 本轮裁决与修订（11 项全部落地）

| 意见 | 裁决 | 处置 |
|---|---|---|
| R4-M1 bare 臂输入契约不精确（brief 内嵌 stats digest） | **VALID**（经核实 briefs/*.brief.json 确嵌 evidence 块） | §8.3(iii) 一次性精确定义："identical blinded brief, whose evidence block is the pipeline's deterministic statistical digest (per-column anomaly profile and top correlations; no ontology, no stages, no gates)" |
| R4-m4 / R1 "45 output files" vs "45-run suite" 口径 | **VALID** | 摘要改 "their 45 recorded run outputs"；§8.3 改 "all 45 run outputs" |
| R4-m5 Table 6 "5 of 9 faults" 行标签易误读 | **VALID** | 改 "5/5 (five of the nine faults capped)" |
| R4-m6 A2 batch-93 gloss 截去 bare 自身不确定尾巴，不公 | **VALID** | 补回 "consistent with acid-pump malfunction or pH-probe drift" |
| R1-m1 bare 臂缺对称 clean-subset 读数 | **VALID** | §8.3 补 "(on the same token-excluded clean subset as §7.2's Top-1 reading, the bare arm is 7/7)" |
| R1-m2 LOTO 删 token 语义含糊 | **VALID** | 改为 "the single token on which IDV7's hit rests---is removed from that scenario's grading set" |
| R2-m2 A2 的 XMEAS 无物理释义 | **VALID** | A2 caption 补 TEP 通道映射（XMEAS_2/9/21 具名；25–38 为组成分析通道；XMV_n 定义） |
| R2-m6 AgentRCA 未入 per-fault 对比需说明 | **VALID** | §7.1 补 "not per-fault alignable with ours, so it enters Table 1 rather than this comparison" |
| R3-m1 Table 8 行计数语义不对称 | **VALID** | Table 6 caption 补 "``strict'' for those arms counts any keyword hit, whereas the Top-1 row counts resolved verdicts only" |
| R4-m3 fig_calibration "＋3.3 K" 不可溯源 | **VALID** | 图内标注改 "CW loop pinned, 72/72 rows"（与 Table 7 一致） |
| R2-m4 fig_casestudy "Δp<0.025 bar" 无推导 | **VALID** | 图内改 "expected head change is an order of magnitude smaller"（与正文口径一致） |
| R3-m2 IndPenSim 真值锚不对称 | **PARTIAL→已加读法** | Table 6 新增 "Batch-93 excluded alone (truth anchor under-determined) 3/8" 行；§6.1 原有披露保留 |
| R1-M1/R2-M2/R3-M1/R4-M2（identifier 重跑、script-only、k≥3、专家锚定未执行） | **PARTIAL（维持 round33 立场）** | 无已发表数字依赖缺失实验；headline 以条件化上界发表；重跑保持 first post-revision execution 承诺 |
| R4-m1/R3-m4 摘要词数（R4 称 430 词） | **INVALID（数字错误）** | 实测 ~257 词（pdftotext 计数含页眉）；嵌套问题 round33 已重写为并列结构 |
| R2-m5 SKAB 控制段长度/R3-m3 统计阶段双跑/R2-m1 FE no-candidate per-fault | **记录不改** | 产物级细节，随 Zenodo 存档与工具链维护处理 |

## D. 排版质检

新增内容区域（§8.3 段落、Table A2）渲染合格；发现并修复：
"(Appendix Appendix A)" 交叉引用重复 ×3（elsarticle \appendix 下 \ref 自带 "Appendix" 前缀）。

## E. 修订后编译

56 页、0 错误、0 未定义引用、0 Overfull。main.pdf 已替换。

## F. 复审轮（Round-34b）结果：4/4 publishable=yes

- **R1：Accept（conf 4）**——m1–m5 全部 RESOLVED（bare 7/7 对称读数、LOTO 澄清、45 口径、3/8 行均经算术复核）；预注册立场维持可接受。
- **R2：Accept（conf 4，附一处图注交付条件）**——11 项核验全部 RESOLVED 或可接受维持；A2 caption 通道映射经其按 TEP 通道表核对无误。
- **R3：Minor Revision→条件已闭合（conf 4）**——仅限一处图内标注截断（本轮 Δp 措辞修改引入）；A2 逐字抽查（含中文原答）与 released 记录吻合。
- **R4：Accept（conf 4，附两条校样期强制修正）**——绑定条件重新裁决不触发："修订稿已消除无条件精度读法的全部承重点……以 Major 惩罚一个已披露、预注册、有成本核算的承诺实验不成比例"；并撤回其"摘要 430 词"的错误计数（实测 ~254）。

### 复审提出的校样期修正（已全部落实并验证）

1. fig_casestudy 右上注释改写后超宽截断（R2/R3/R4 共同发现）→ 拆为三短行 + 加高衬底框，像素级复核完整；
2. 引言贡献 4 的 "resolves 4/9" 补上界限定从句 "an upper-bound reading under the disclosed identifier channel (Section 9)"（R4：全文唯一未条件化数字位）；
3. 修复过程中发现并修正一处 shell 转义损坏的 `\ref`（渲染为 "Section efsec:discussion"，已修复为 "(Section 9)" 并全文扫描确认无同类损伤：CR=0、孤儿宏=0、`??`=0）。

### 终态

56 页、0 错误、0 未定义引用、0 Overfull、摘要 ~254 词；四席 publishable=yes（R1/R2/R4 Accept，R3 Minor 条件已闭合）。
