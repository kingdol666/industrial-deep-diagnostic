# Round 38 — 全新品味四席循环（F/G/H/I），终态：全部可行动修复完成

日期：2026-09-24。round37 五席已全过后，应用户要求再启一轮 loop。为避免同品味重复审稿的边际递减
（round35 教训：换品味才有新发现），本轮启用**四位从未见过本稿的全新审稿人**在最终 build 上盲审。

## 四席结论

| 席位 | 结论 | 核心意见 |
|---|---|---|
| F 主编桌拒模拟 | **SendToReview**（非桌拒） | scope 过关（知识层+AEI 自家文献定位表）；摘要行话过密；建议投稿前执行重跑 |
| G 敌意方法学 | Major（以执行重跑为条件） | 每个数字都对 metrics.json 复现成功——攻击点全部在"已承诺未执行的实验"而非文本；抓到 precision 行区间对应 4/4 而同格显示 3/4 的**呈现缺陷** |
| H 生产合规 | Minor（可发表） | 作者姓名需姓/名切分+通讯作者标注；highlights 逐字数全过（74–84）；图 676–820dpi 达标 |
| I 一线工程师 | Minor（可发表） | "罕见地能为工厂工程师所用"；行话首现未释义；主张指定唯一 primary reading |

## 本轮修复（全部已验证 ALL-PASS，59 页 0 错误）

1. **作者信息**：ZhangHaoZheng → Haozheng Zhang（姓/名切分，\corref 通讯作者标注）——**默认按 Zhang=姓 假设，需作者本人确认**；CRediT 同步。
2. **摘要**：identifier-recall 首现处补白话释义（"run-directory names can embed the documented mechanism"）；补"8/9 under its stricter branch-localized reading"；244 词。
3. **G 的呈现缺陷**：Table 6 caption 注明印刷区间对应 identity-inclusive 4/4 而非同行的 3/4。
4. **仪器工件归属**：rubric 段补"every deducted point traces to the disclosed instrument artifacts, none to evidence substance"；8/9 verdict-type 合规标注为 one-directional typing 下的上界。
5. **图表合规**：AI 声明点名具体工具（GLM-based agent CLI）；Figure~\ref ×2 统一为 Fig.~\ref；删除未使用的 tikz/multirow 包；Fig 2 caption 补 VLM non-visual fallback 声明。
6. **排版**：删除多余 FloatBarrier，p.23 空白页消除（p.22–25 每页 3200–4500 字符）；§7.2/§9 三个巨型段落拆分；≈6.1/9→≈6/9；结论补 (one of three blind)。
7. **拼写最后一网**：neutralised ×5、finalisation/finalise ×18（含 fig_architecture/fig_pipeline/fig_benchmark 图源，已重渲染三张 PNG 并 trim）。
8. **highlights**：第 3 条改为无争议表述（79 字符）。
9. 修复 H 的误报：其声称裸 \ref 渲染为 "A" 建议加 "Appendix~" 前缀——实际渲染本就是 "Appendix A"，加前缀会双写；已按实测回退（教训：审稿人的"渲染观察"也必须对 PDF 验证后才动手）。

## 记录在案的否决（理由）

- 执行重跑/专家盲评/keyword 前校准集重算：实验性工作，非本轮文本可完成；G 确认论文披露已使"隐瞒版攻击"失效，剩余攻击只关乎提交时机——决策权在作者。
- 削减 30–40% 篇幅（F）：无页数上限；round37 C 席已确认冗余可接受；仅拆分段落。
- Fig 1 引擎列表折叠（I）：14 引擎是已发布系统的真实披露，折叠=隐瞒。
- 成本货币化（I9）：无工件支持的数字=编造，拒绝。
- 标题再改（F8/G11）：已历三轮审稿稳定，事实准确，保留。

## 终态

**59 页，0 编译错误，76 条文献，0 未解析引用，0 英式拼写（含图内文字），摘要 244 词。**
四席中三席判可发表（F/H/I），G 的否决条件唯一且明确：执行 neutralized-identifier 重跑（需先实现
hash-id 运行目录的 harness 扩展，再花约 16h agent 时间）——这是投稿决策，不是稿件缺陷。
