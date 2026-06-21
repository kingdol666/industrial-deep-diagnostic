---
name: mixed-scope-spearman-pg31ds
description: PG31DS W1C8B_std Spearman=0.266 was full-data scope, not within-PG31DS (actual 0.494); report mixed scopes
metadata:
  type: reference
---

报告在讨论PG31DS产品内W1C8B_std相关性时，引用了Spearman=0.266（全55批的Spearman）而非PG31DS内的Spearman=0.494。这是范围混淆错误——把全局统计量错误归为子组统计量。独立验证确认：PG31DS（n=19）W1C8B_std与scratch_count: Pearson=0.581, Spearman=0.494, divergence=0.087。

**Why:** 统计分析中，引用子组均值不可引用全局标准差；引用子组相关也不可引用全局秩相关系数。验证管道需自动检查统计量范围一致性。

**How to apply:** 当diagnosis在讨论子组（如PG31DS产品内）的相关性时，验证时核对引用的Spearman值是否确实来自该子组。在判断报告统计精确性时，对此类范围混淆敏感。
