---
name: bopet-scratch-diagnosis-v4-rejudge
description: BOPET MD纵向划伤诊断lekai数据第2轮评审(Repair Round 1)，94分通过。关键模式：BETWEEN_PRODUCT_ONLY、COMPETING_SET、PG31DS内工艺变异但不相关
metadata:
  type: reference
---

BOPET纵拉划伤诊断lekai数据第2轮(repair round 1)评审结果：94分通过。

**Repair修复了4个问题:**
1. PG31DS内W1C88参数恒定的误声称 → 改为CV=16.3%但有变异不相关(rho=-0.11, p=0.37)
2. 多重检验校正缺失 → 添加Bonferroni 327测试p<0.000153标注
3. W1C87物理含义精确化和W1C88-W1C7C互相关 → 添加Spearman rho=-0.534全局共线 + PG31DS内rho=0.06独立
4. PG31DS内W1C88阶跃变化 → 前4批19Nm过渡态标注

**评分要点:**
- 整体94/100，无BLOCKING问题
- 证据(10/10)、因果辨析(10/10)、不确定度(10/10)、无过度声称(10/10)满分
- 数据区分度INDISTINGUISHABLE，置信度天花板65正确应用
- W1C87(纯热收缩) Spearman rho=-0.099弱于W1C88 -0.162，不支持参数替换
- PG31DS型号内W1C88 30Nm变异但scratch不相关(rho=-0.11)是核心发现
- 第一原理magnitude BORDERLINE(预测<100% vs 观测>10000%)

**执行验证:** schema验证通过(0 errors)，judge-gate-check通过(ok=true, min_score=90)
