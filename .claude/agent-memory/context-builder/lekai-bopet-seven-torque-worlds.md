---
name: lekai-bopet-seven-torque-worlds
description: BOPET leKai scratch: 7 torque "worlds" per roll driven by model not physics — 9 models/55 batches with bimodal torque signatures
metadata:
  type: reference
---

BOPET乐凯纵拉段数据有55批次/9种型号，扭矩分布呈**多重双峰/多峰**分布，每个辊上的模式由**产品型号**决定而非物理异常。关键发现：

- FP21和PG系列在**所有18个扭矩辊上**分布完全不重叠（如W1C80: FP21~77%, PG系列~2-20%; W1C7D: FP21~17-27%, PG系列~60-75%）
- 这是工艺设定导致的——不同型号有不同的速度设定(W1C40: FP21~12m/min, PG~16-20m/min)，扭矩是速度-张力-摩擦耦合的结果
- PG22C在部分参数上有极端值（如W1C82@PV1_mean=-4.3 vs PG系列正常~55-79）
- 急冷段(MD_TH013-015)温度std在PG32M批次H2652620出现3.69-3.78极端值，是急冷系统异常信号
- PG32D批次scratch_count=76（全数据最高），但其扭矩/温度参数并非最极端

**诊断建议**: 所有关联分析必须先按model分层，否则FP21和PG系列的系统性差异会制造大量spurious correlation

**Why:** model confound覆盖了所有扭矩参数的方差——扭矩的型号间差异远大于型号内波动，直接全样本分析会被型号效应主导
**How to apply:** 在BOPET乐凯数据分析中，始终以model为首要分层变量；FP21、PG31DS、PG22C、PG32D/M应视为独立子数据集
