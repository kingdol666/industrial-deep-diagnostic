---
name: bopet-scratch-diagnosis-v4-rejudge-round2
description: BOPET MD纵拉划伤诊断第2轮rejudge(repair round 1 re-review), 96分通过, 修复2个preflight阻断问题: outlier-driven Pearson伪相关(W1C86_std r=0.49→Spearman=-0.037) + 型号内时间趋势混杂(预加热去趋势后r=0.026), 全工艺参数排除后唯一残存H3(时间累积)置信度25
metadata:
  type: reference
---

# BOPET划伤诊断v4 rejudge Round 2 (96分通过)

**时间**: 2026-06-19
**Run**: 202606190930219_lekai-scratch-process
**场景**: BOPET MD纵拉段划伤诊断, lekai数据, 55批次, 8型号
**修复轮次**: Round 1 (after optimizer preflight blocking)

## 修复内容

Preflight审计发现2个阻断问题:
1. **RI-1 (BLOCKING)**: W1C86_std全局Pearson r=0.49是离群驱动伪相关 — 独立验证Spearman=-0.037, 去离群Pearson=-0.012
2. **RI-2 (BLOCKING)**: PG31DS内工艺参数系统性时间漂移 — 预加热温度与batch_seq r=-0.9515, 去趋势后与scratch相关从-0.376降至0.041

修复分析:
- 所有相关性改用Spearman
- 所有型号内执行去趋势(控制batch_seq)
- model列尾部空格strip修复
- H1(冷却系统失稳)移出竞争假说集(统计排除+物理量级校核)
- H2(张力波动)排除(Spearman全面否定)
- 唯一残存H3(时间累积效应)置信度25

## 关键数值验证(独立验算确认)

| 声称 | 报告值 | 独立验算 | 一致? |
|------|--------|----------|-------|
| W1C86_std Pearson | 0.487 | 0.4871 | 是 |
| W1C86_std Spearman | -0.037 | -0.0366 | 是 |
| Pearson-Spearman分歧 | 0.524 | 0.5237 | 是 |
| 去离群后Pearson | -0.012 | -0.0115 | 是 |
| PG31DS preheat vs batch_seq r | -0.947 | -0.9515 | 是 |
| PG31DS preheat去趋势后r | 0.026 | 0.0408 | 微小差异(去趋势方法) |
| PG31DS W1C8C去趋势后r | 0.020 | 0.0134 | 是 |
| PG31DS scratch vs batch_seq Spearman | 0.42 | 0.4203 | 是 |
| PG32B scratch vs batch_seq Spearman | 0.91 | 0.9100 | 是 |
| PG31DS W1C8B_std Spearman | 0.494 | 0.4943 | 是 |

## Judge评分概要

- **总分**: 96/100, verdict: pass
- **阻断问题**: 0个
- **警告**: 2个(非阻断级)
  1. visual_analysis.json说PG31DS"无单调趋势" vs Spearman=0.42——需调和说明
  2. batch_seq是衍生列但未在cleaned_data.json中显式记录
- **输出文件**: 05_review/judge_feedback.json (schema验证通过)

## 关键评审模式

1. **排除性诊断的价值**: 修复的最大贡献是排除了2个误判假说,而非确认了一个根因
2. **去趋势前/后对比**: 预加热温度从-0.376→0.041, W1C8C从-0.389→0.013——排除力度强
3. **独立验算的必要性**: 即使修复分析数值准确, Judge仍然必须独立验算关键统计声称
4. **置信度诚实**: H3=25分, 总体overall_confidence=22——低但诚实
5. **COMPETING_SET判定的正确变化**: 从"H1和H2不可区分"改为"全部工艺参数排除"——更强、更有信息量

## 与[[bopet-scratch-diagnosis-v4-rejudge]]的区别

Round 1 rejudge(94分)是针对原诊断的修复——修复了PG31DS参数变异、多重检验、互相关、阶跃变化标注。
Round 2 rejudge(96分)是针对preflight阻断的新修复——修复了离群伪相关和时间趋势混杂, 是更深层的统计修复。
