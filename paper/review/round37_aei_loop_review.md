# Round 37 — AEI 最严格标准多轮评审循环（loop skill）

日期：2026-09-24。目标：按 AEI（Advanced Engineering Informatics）当前 Guide for Authors 的最严格审稿标准，
对 `paper/main.tex`（终稿候选）做多轮"审稿→修改→重编译→复审"循环，直至全席通过。

## 循环 0：合规预扫（审稿前自检，发现两处系统性缺陷）

1. **refs.bib 16 处缺逗号 → BibTeX 静默跳过 16 条文献**。Round-36 批量补 DOI 时每条新 `doi` 字段前的
   `year`/`note` 行都缺尾逗号；`bibtex main` 报 16 errors（"skipping whatever remains of this entry"）。
   既往构建靠旧 `.bbl` 掩盖（jobname=main_r32 + cp bbl），实际处于"一次干净重编译就会出现 16 个断引"的
   隐患状态。全部修复后 `bibtex` 0 错误。
2. **英式/美式拼写混用 57 处**（AEI 明文禁止混用）。统一定稿为美式：behaviour/colour/favour/analysed/
   organises/summarises/labelled/generalisation/memorised/localis*/formalis*/amortis*/Conceptualisation 等。

AEI 硬要求复核（官网 Guide for Authors，2026-09-24 抓取）：无页数上限；摘要 ≤250 词（现 234）；关键词 1–7
（现 7，新增 Process ontology）；highlights 3–5 条 ≤85 字符（全过）；五项声明齐全（CRediT/利益冲突/资助/
数据可用性/生成式 AI 使用）；组合图 ≥500 dpi（547–638 达标）；scope 门槛"显式知识表示与使用"。

## 循环 1：五席并行审稿（不同品味，盲审纪律）

| 席位 | 结论 | 关键实锤发现 |
|---|---|---|
| A 方法论怀疑者 | Major | 四→三笔误（"all four TEP-derived outcomes"）；混评分口径的 9/9-vs-4/9 并置；n=1 稳定性限定词缺失 |
| B 可复现性审计者 | Major | **CRITICAL：数据可用性声明超范围**（GitHub 仓库并无 artifacts 层）；盲控简报描述失实（12 份 user_context 共享"诊断本次异常"预设问题，已对照 user_context.json 逐字核实）；"repair counts" 不在 grading records；Table 6 caption 指错工件 |
| C 范围/实践者 | Major | 知识层从未展示（AEI scope 门槛风险）；缺 Reiter 模型诊断源流；摘要一处数字四种读法 |
| D 视觉编辑 | Minor(通过) | fig_consistency 标签碰撞（.78/.80 叠成".780"、.86 被遮）；fig_casestudy 注释无底衬；图例断开 |
| E 文献 integrity | Major(可发表) | **CRITICAL：`@article@article{` 双头畸形 ×2**（yin2014review、alfayez2005detection 渲染成无刊名 stub，bibtex 仅 warning 故漏检）；yoon2001 记录错误（应 AIChE J. 46(9) 2000:1813-1824，Crossref 核实） |

## 修复（循环 1 → 循环 2）

**Bibliography**：双头 ×2 修复；yoon 修正；{T}ennessee {E}astman / {GxP} 专名保护；新增 4 条经 Crossref
核实文献：Reiter 1987（AI 32:57-95）、de Kleer & Williams 1987（AI 32:97-130）、GLM（ChatGLM, arXiv
2406.18871，基础模型引用补缺）、ISO 15926-2:2003；sheridan1978 从未引用变为 §2.4 引用；IEC 61511 全称补入。
**正文**：摘要重写（234 词：provisional 上界标记、同口径 9/9-vs-9/9、单次重复限定、专家锚定待完成条款、
删除摘要内 (Section 1) 自引）；贡献 4 限定（one of three blind、batch-93-excluded 3/8）；§2.4 补模型诊断
源流段（Reiter/de Kleer/ISO 15926/Sheridan）；§6.1 盲控描述改为与工件逐字一致；§3.4 新增真实本体摘录段
（SKAB valve 01_ontology，C1 scope 门槛修复）；数据可用性声明重写（声明=仓库源码+随稿 supplementary 工件
层，修复 B-CRITICAL）；表注四处（rubric.json/04_diagnostics 指针、CI 二阶性质、gate-by-construction、
FE 8/11 reported-figure 注）；§9 四→三 + 悬挂枚举修复。
**图**：fig_consistency 五处标签重定位；fig_casestudy 注释块 0.94 不透明底衬 + 图例 nowrap；
fig_pipeline 字号 +13% 重渲染（后被证明引入碰撞，回退）。

## 循环 2：五席复审

A **Accept**、B **Minor**（两条一行修复）、C **Accept**、E **Accept**、D **Major**——
D 撤回 round-1 的 run-id 主张（页尺度误读，2× 变焦证实 202609171630389 正确），但抓到字号增大在固定尺寸
drawio 盒子内引入的标题/代理行/门禁标签三层叠印（Steps 8/8.5 CRITICAL）。**回退字号**至原验证布局重渲染。

## 终验（循环 3）

D 终验 **Accept**：全部碰撞位 CLEAN、裁切无缺损、p-11/30/40/58 无浮动回归。
十项文本修复逐一 PASS（独立校验代理，PDF+源双确认）：表注归位、Three qualifications、悬挂枚举消除、
贡献 4 措辞对齐、数据声明"exactly the thirteen canonical run directories + 排除中断批"、
"translated from the released bilingual artifact"、GXP 大写渲染、76 条文献、0 个 "??"、摘要四要素无回归。
另修复 deposits README 的"completed"判据歧义（4 reached final-audit / 2 closed all gates）。

## 终态

**五席全部通过（publishable=yes，建议 Accept/Minor→已修）。** 58 页，0 编译错误，76 条文献全渲染（含 DOI
超链），bibtex 0 警告级错误，0 未解析引用，0 英式拼写残留，摘要 234 词，7 关键词，五声明齐全。

## 记录在案的否决/延后（含理由）

- 执行 neutralized-identifier 重跑（~16h）与盲评专家锚定：预注册的 post-revision 执行，本轮不可执行；
  已按 A 席给出的替代路线把所有受污染数字标记 provisional 并写明"no headline claim depends on them"。
- 深度压缩 engine/web/enhancement 层：该层叙述承载 A/B 席需要的审计链披露，仅做措辞精简。
- Table 4 备选读法移附录：它们是承重的诚实性装置，保留。
- 作者姓名 family/given 切分：作者身份决定事项，需通讯作者在投稿系统元数据中确认（ZhangHaoZheng）。
- 已发表 ICLR/NeurIPS 论文的 arXiv DOI 保留（作者明确要求"有 DOI 尽量放"）。
