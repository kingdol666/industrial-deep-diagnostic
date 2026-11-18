# Round 33 — AEI 模拟审稿、裁决与修订记录（2026-09-22）

对象：paper/main.tex（标题已改 "Auditable agentic diagnosis…"）。流程：4 席资深审稿人独立评审
（R1 方法学统计 / R2 过程工业领域 / R3 AI 智能体系统 / R4 魔鬼代言人）+ 2 席排版质检 →
逐条裁决（VALID / PARTIAL / INVALID，带证据）→ 修订 → 复审。

## Round-1 结论：4/4 Major Revision（R1 conf5；R2/R3/R4 conf4）

## 收敛的 MAJOR 意见与裁决

| # | 意见（席位） | 裁决 | 处置 |
|---|---|---|---|
| 1 | 标识符中和重跑（≈16h agent 时间 + harness 扩展）必须在发表前执行，而非承诺（R1/R2/R3/R4 四席收敛） | **PARTIAL** | 本修订窗口内无法执行（需 16h+ 流水线运行与 hash-id 运行目录扩展）。论文的 claim 位置已与"未执行"对齐：摘要即明示 upper bound + joint floor 0/9 + identity-strict 3/9；recall-possible tier 保留。重跑保持"first post-revision execution"承诺。**任何已发表数字不依赖该实验**——这是本轮重新定界 claim 的核心。 |
| 2 | top-k 9/9 近似设计保证却占标题位（R1-M2、R4-M2） | **VALID** | 摘要改为 "a family-level instrument reading whose specificity the instrument does not test"；Table 6 增加 Branch-localised 8/9 行；Fig.4 图注声明 printed fractions 为 keyword-instrument readings 并指向 Table 6 的全部读法。 |
| 3 | n=1 重测稳定性证据力弱、摘要表述强于证据（R1-M1、R3-M4、R4-M3） | **VALID** | 摘要改为一对重测的个案描述（"One seeded re-execution (one repeat pair) reproduced…"），不再作为稳定性主张位；§7.5 的自我限定保持。 |
| 4 | 零误报主张证据薄弱（仅 1 盲对照）（R1-M4） | **PARTIAL** | 摘要与图注统一为 "(one of three blind)"；主张保持在所披露范围内（"does not fabricate faults under an honest brief" 的 n=1 声明不变）。 |
| 5 | 过程质量主张缺外部锚：script-only / filter-disabled 臂未执行（R1-M3、R2-M1、R3-M4、R4-M1 收敛） | **PARTIAL** | 归因论文已自认 hypothesis（§8）；新增 §5 机制/纪律边界句、§3.4 唯一实质性拦截实例显性化。两臂保持 pre-registered；同样遵守"无已发表数字依赖缺失实验"原则。 |
| 6 | "machine-checked" 措辞强于浅谓词（存在性/schema/阈值）的实际约束力（R3-M2） | **VALID** | §5 新增边界句：机器谓词=存在性/schema/阈值；认识论约束由评审阶段协议执行、算术审计（ceiling compliance）复核；指向 Table 8。 |
| 7 | 摘要超长（312 词）多重对冲嵌套（R1-m1、R3-m1、R4-m3） | **VALID** | 重写至 ~255 词；全部披露保留（upper bound / 0/9 floor / 3/9 strict / top-k 仪器读法 / 1-of-3 blind / 消融反转 / n=1 重测 / 45 文件字节复现 / trustworthy 定义）。 |
| 8 | 篇幅与重复 caveat（R3-M5、R4-M5） | **PARTIAL** | §2.4 谱系段压缩（删 Sheridan/Verplanck 句）、§8.1 轶事压缩、控制组披露去重（保留摘要/表 6/§6.1 三处必要位）。整体重构（14 引擎层移附录）涉及全文交叉引用重排，留到录用后修改稿执行。 |
| 9 | 标题 "Trustworthy" 超出证据（R4-m1） | **VALID** | 标题改为 **"Auditable agentic diagnosis for industrial processes…"**；正文 §1 的 trustworthy:=auditable+capped-honest 定义不变。 |
| 10 | R4-M1 "审计门零实质拦截" | **INVALID（部分）** | 事实错误：judge 对 TEP IDV3 的 75→90 修复即诊断层实质拦截。§3.5（Audit Infrastructure）已显性化该实例为 "the audit plane's single demonstrated catch of a substantive diagnosis defect, reported as the exception it is"。 |

## Round-1 值得采纳的 MINOR（已修）

- FE 引文统一为正式发表版（Computers & Chemical Engineering 2025）：正文 \cite、fig_forest/fig_tep_perfault 图内标注（R2-m4）。
- Table 6 列宽失衡 + hyphenation → \resizebox（排版席 p-25）。
- Table 1 caption 注明 IDD repro-gate 为 internal（R2-m1/R3-m2）。
- R4-m2 图缺陷三件：fig_forest 子标签行首 "n" 被裁（实锤；首修 L=462 不足以覆盖最长的 top-k/controls 子标签，复审发现后改为 L=540 并经像素复核确认）；fig_trace 底部被导出窗口截断（实锤，已修窗口高度，内容 2040px 完整）；fig_benchmark 左标签边距加大（L=170）。
- Fig.6 注释簇间距、Fig.10 旋转标签改单行消除交叠（排版席）。
- 由结果倒推的事后合理化句（§3.3）改为从属从句（R4-m4）。

## 未改动项（理由）

- R1-m3（metrics.json 将 verdict-type 折入 calibrated 字段）：脚注已披露；属发布仓库侧清理，随 Zenodo 存档修正。
- R1-m4/R3-m4（R3 控制场景误规范后豁免）：论文已如实定性为 check mis-specification 并预注册未来语料规则，改写反而弱化披露。
- R1-m6（expected-verdict-set 无外部时间戳）：已披露依赖仓库 edit history；Zenodo DOI 于录用时铸造。
- R2-m5（L1–L7 人工复核）：并入已计划的 blinded expert adjudication。

## 排版质检（2 席，54→55 页）

- p-23 Fig.3 底部截断（导出窗口不足）→ 已修。
- p-25 Table 6 折行断词 → resizebox 已修。
- p-30 Fig.6 注释叠印、p-39 Fig.10 标签成团 → 已修。
- Fig.2/Table 6 浮动距离 3 页：placeins [section] 约束下的已知权衡（导言有说明），复审复核。

## 修订后编译：55 页、0 错误、0 未定义引用、0 Overfull、摘要 ~255 词。

## 复审轮（Round-3b）补充修订（2026-09-22）

4/4 席 publishable=yes（R3 Accept；R1/R2/R4 Minor Revision）。Minor 条件全部关闭：

1. fig_forest 子标签裁切（R1/R2/R4 共同抓出的"已修未修"失实）→ L=540，行 5/6 "n = 9 ·…" 像素级复核完整。
2. fig_benchmark：(a) 图例第二行截断（PH 随 H 自增抵消加高的布局缺陷，解耦 PH=238 后修复）；(a) All-faults 条超出 xmax=6 坐标域 → 坐标域改为 9（All-faults 满尺度），4/9 标签入条内白晕，图注同步改 "(the all-faults row, nine faults, is full scale)"。
3. fig_calibration 数据集侧标签与行标签叠印 → 删除侧标签（行名自带数据集前缀）。
4. fig_casestudy plateau 注释簇加半透明衬底。
5. 摘要两处：whose→with a joint worst-case floor of 0/9（R3 语法）；byte-identically 补 (timestamps excluded)（R1）。
6. 回应文档勘误：IDV3 实例位于 §3.5 而非 §3.4（R4 指出，已更正本文件）。

修订后：55 页、0 错误、0 未定义引用。make_figures.py 与现行 PNG 不同源已在 figures-html/README.md 声明（provenance only）。
