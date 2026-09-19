# 2026-09-18 全清重测 → AEI 论文深度优化蓝图

## 权威数字（source: results/benchmark/*，paper/workbench/new_run_numbers.json）

Headline: Top-1 **4/9 = 44.4%** Wilson[18.9,73.3] · top-k **9/9=100%**[70.1,100] · 对照 3/3[43.8,100] 零误报 · 过度自信 0 · 判定类型合规 8/9（唯一 miss=skab_valve1_1，期望 DETERMINED-only 判了 CS）· rubric 均值 **94.6**（10×100, tep_d01=85, skab_valve=85, batch001=65）· judge 均值 **94.7**（90–98）· finalize 12/12 PASS · REPRODUCIBLE · suite 45/45 双跑逐字节一致 DETERMINISTIC · 一致性 tep_d11 两轮 CONSISTENT（1/1, divergent 0）

Per-scenario（canonical grading；conf 为 0-100）:
| case | type | conf | judge | top1 | topk | rubric | 备注 |
|---|---|---|---|---|---|---|---|
| skab_valve1_1 | CS | 60 | 95 | F | T | 85 | R4 type miss；flow plateau −3.13% rows 621–927 p=5.7e-158; current −0.115A p=0.10; 压力量化 0.327 bar |
| skab_cavitation_13 | CS | 60 | 90 | F | T | 100 | 76 行塌落/40 爆发 1–3s; 泵负载保持 2.338v2.396A; 双振动 +5%/+3% |
| skab_normal_control | DET(normal) | 86 | 97 | — | — | 100 | 稳态 99.71%; 强相关全证伪 |
| tep_d01_ac_feed_ratio | DET | 91 | 96 | T | T | 85 | R4: conf 0.91>机器 0.90 顶棚 1 分; XMV_3/XMEAS_1 +18.5σ; lockstep r≈0.9996 |
| tep_d03_hard | CS | 55 | 90 | F | T | 100 | 立管汽提蒸汽环 std×2.5–2.7(方差×4.3–7.4); 反应器平; 分叉不可判 |
| tep_d00_normal_control | DET(normal) | 90 | 96 | — | — | 100 | 漂移 ≤0.268σ; 反馈签名 |
| indpensim_batch093 | DET | 82 | 96 | T | T | 100 | Fc 钉 2.0 L/h 72/72 行; T→301.44K; 90.2h 释放→2.4h 回带 |
| indpensim_batch001_control | DET(normal) | 93 | 94 | — | — | 65 | R3 归地(−20)+R4 0.93>0.90(−15) |
| tep_d04_reactor_cooling_step | CS | 63 | 97 | F | T | 100 | 冷却三联征 XMEAS_9 z=+10.47/XMV_10 +6.82σ; 能量平衡; H1 Tin 阶跃 vs H6 UA |
| tep_d07_header_pressure | DET | 78 | 98 | T | T | 100 | XMV_4 +25.13% z=12.35 流量恒; 增益 −20.11%→ΔP 0.638 |
| tep_d11 (retest canonical) | CS | 60 | 93 | F | T | 100 | XMV_10 ×6.33/XMEAS_9 ×4.04 均值钉住; lag-5 r=−0.636; T21 ×1.03 |
| tep_d14_reactor_valve_sticking | DET | 80 | 94 | T | T | 100 | ×189/×116/×222 方差爆均值冻; 633/800 量化步进; lag1→5; ACF(7)≈0.512 |

基线臂（baselines.json 重生成 + 45 suite runs）: bare-LLM strict 9/9（对照覆盖 2/2）· FE 协议 6/6 · FE official 5/6（miss=IDV4）· PCA 同文献（IDV3 2.9/4.8; IDV4 SPE100/T2 48.8）· IDD TEP 子集 3/6=50%[18.8,81.2]; 共有可检子集(IDV1/7/11/14) IDD 3/4。

一致性: 13 个现时代执行；Step3 随机抽 tep_d11（seed 1003818694 可回放）→ 全新目录 202609172247007 九阶段独立重跑 → **CONSISTENT**（type CS=CS, tag XMV_10=XMV_10, class ENVIRONMENT=ENVIRONMENT, Δconf=2 分 0.62→0.60）；其余 11 场景单执行= INSUFFICIENT-RUNS 契约（诚实缺口）。

执行形态: **真子代理派发**（ZCode harness spawn 工具；每阶段独立会话、工件通信；judge∥pre-audit 真并行）；脚本只验证不代写。12 场景并发批处理墙钟 6.0–6.3h（批量编排）; 顺序单场景（复测 tep_d11）事件跨度 **117 min ≈2.0h**。执行窗口 2026-09-17/18（UTC）。修复披露: tep_d03 一轮 judge 驱动诊断修复（75→90）；两场景报告层终审修复（skab_normal B1/B2、tep_d07 G1）；其余为 schema/路径规范化；无判定变更。RAG: 13/13 run 探测失败→文档化 fallback，全部本体全新构建（full 模式，无 fast-reuse 命中），无 L6 证据。VLM: 非视觉部署，全 skeleton（source_agent=visual_analysis.py）。

已删除/失效的旧叙事（必须从论文移除）: 6/9、5/9 pre-revision、TEP 5/6、rubric 97.9、judge 93.1、IDV4 DET 0.75 case study 旧数字、IDV11 flip 故事、IDV1/IDV14 稳定性对、41 run 目录、15/16 case-version、五次 draw 历史、keyword 切换时间线（tab:kwtimeline）、旧 run 目录时间戳引用（20260912/14/15 全不存在了）。

## 换血执行
- 配图: 9 幅全 HTML 生成（architecture / pipeline / benchmark / calibration / tep_perfault / forest / suite_matrix / consistency / casestudy），Edge headless 3x PNG 600dpi → paper/figures/*.png，tex 改 \includegraphics{...png}，删除两个 TikZ figure 环境。
- main.tex: 按上表逐节换血 + 执行过程/模块集成叙事强化 + round16/17 should-fixes（harness/execution-form 精确化、cost 句、TEP CI n=6 标注）顺手折入。
- 完整性门: 子代理逐数字对照 results/benchmark 审计。
