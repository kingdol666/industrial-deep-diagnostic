---
name: bopet-scratch-diagnosis-v4-judge-86-needs-repair
description: BOPET MD纵拉划伤诊断lekai数据(新run) Judge评审，86分needs_repair，3项修复：proof_strength降级、time_lag引用、regime_filter引用
metadata:
  type: reference
---

# BOPET划伤诊断v4新run Judge评审 (86分 needs_repair)

RUN_DIR: 202606210328579_lekai_scratch
Score: 86/100, Verdict: needs_repair

## 关键模式

- **诊断类型**: COMPETING_SET, H1扭矩std→划伤(62), H2挤出波动(30), H3产品切换(25)
- **数据**: 55批次, 8种产品, 批次级聚合(无秒级时序), BOPET MD纵拉+挤出场景
- **时间**: time_sorted=true (96.3%), 但批次级数据无子批次分辨率

## 发现的问题 (无阻断, 3项warning)

1. **H1 proof_strength标签过高**: 标注STRONG_EVIDENCE但全局r=0.47-0.49中等且缺定量物理方程。应改为PLAUSIBLE。
2. **time_lag_analysis.json未引用**: 虽然_std参数未在lag分析中(仅_mean)，但诊断未说明此缺口。应在R2或H1中补注。
3. **production_regime_filter.json未引用**: 全局相关(r=0.47-0.49)包含20% transition行未说明。PG31DS产品内分析(100%稳态)不受影响但应显式标注。

## 通过检查的项目

- **Simpson处理**: 5个CRITICAL温度参数被三重排除(Simpson+outlier+Spearman分歧)
- **区分性评估**: INDISTINGUISHABLE对正确识别，COMPETING_SET输出，H1置信度62<65上限
- **reasoning_chain**: R1-R8完整, falsification条件具体可测试
- **置信度可追踪**: H1的62=50+5+8+3-2-2, adjustment_log完整
- **spot_check**: W1C86_std r=0.4871核验一致; PG31DS内r=0.5813核验一致; FP21方向反转(r=-0.2049vs+0.49)已隐含处理

## 修复指令

修复后预计可达92-95分。修复项:
1. 调整H1 proof_strength为PLAUSIBLE
2. 在R2中引用time_lag_analysis.json说明_std不在scope
3. 引用production_regime_filter.json说明全局相关含transition行

## 交叉引用

- 本次评审的judge_feedback: `05_review/judge_feedback.json`
- 与[[bopet-scratch-diagnosis-v4]]对比: 本次为新run(20260621), 数据相同但诊断器输出不同
- 与[[bopet-scratch-diagnosis-v4-rejudge]]对比: 本次为首次评审而非rejudge
