# 盲审循环 Round 4（确认轮，2026-09-20）— 终局：3/3 全席满意，零 blocking

## 判决汇总

| 席位 | publishable | recommendation | blocking | confidence |
|---|---|---|---|---|
| R1-methodology | **yes** | Minor Revision | 0 | 4 |
| R2-domain | **yes** | Minor Revision | 0 | 4 |
| R3-rigor (Devil's Advocate) | **yes** | Minor Revision | 0 | 4 |

**循环终止：共识规则（全席 publishable=yes 且零 blocking）已满足。**

## 抽查与核验记录（三席独立进行）
- R1：metrics.json（4/9、9/9、overconfident=0）、表2 全部 Wilson CI、rubric.json（94.58、85/85/65）、retest（seed 1003818694→IDV11）、consistency_audit（CONSISTENT、Δconf=2、overlap 0.14）、suite_determinism（45/45）、repro_report（153/153）、baselines（bare-LLM 严格命中）逐一复现相符。
- R2：FE Table 1 转录与 arXiv:2412.14492 一致（7/11、9/11、别名类、3/4 排除、8/11）；SKAB other/13 官方描述、IndPenSim 91–100、二值故障标志披露恰当；IDV4 能量平衡、IDV7 算术 (1/1.251)²≈0.64、IDV14 黏滞指纹正确；"冷却水入口温度未测量"与 TEP 测量表吻合。
- R3：kw_hits 证实 LOTO（IDV7 单 token "header"；batch93 命中"执行器/加热/偏差"）；consistency_audit（62/60、within-era 1/1、11 例 outstanding）；全部 CI 逐位一致；三层口径（摘要/正文/结论）无矛盾。

## 残余 MINOR 清单（非阻断，供 camera-ready 打磨）
1. R1：leave-one-token-out / forced-commitment / 随机排序期望三条派生读数，建议在文中或附录指明生成脚本与 JSON 路径。
2. R1：表2 行格式统一（"5 of 9" 行补区间或统一标注 instrument reading）。
3. R1：一致性判据 0.35 阈值补版本化出处/固定时点说明。
4. R2：fig_tep_perfault 的 "Candidates in prompt" 列后移并在 caption 注明仅指 FE 协议。
5. R2：摘要压缩至约 250 词（多重限定移正文）；ACP / LMTD 首现处展开全称。
6. R2：表5 加一句"bare-LLM 9/9 为家族级关键词命中，未施加 identity-strict 折扣"的口径说明。
7. R3：R3 检查的规则化变更标注生效版本/日期；Register A 首段与表 A1 补 recall-possible 提示；cost 中位数补 per-stage-span-sum 口径。
8. R3 最强反驳（已降级为观察）：头条在自设最坏读数下可退至 0/9——这是论文以诚实披露换来的立场，最终防线是已承诺的 neutralised-identifier re-run（≈16h），投稿前执行可彻底关闭该问题。
