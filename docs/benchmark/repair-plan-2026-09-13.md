# 修复计划 P-FIX-1 — 真值隔离泄漏的彻底修复（2026-09-13）

> 状态：**已执行**（本文件是执行记录，见 §4 验证结果）
> 触发：独立审计（子代理，2026-09-13）发现 5 个 TEP 场景的 `process_description`
> 在创建时含故障身份直述（如"本例为流股4 C 集管压力降低"），该文本随
> brief 与 run 目录 `00_input/user_context.json` 进入诊断 agent 可见输入。
> 案例文件与 briefs 已在当日修复，但 **run 目录未重建、notes 未在干净 brief 上重新推理**。

## 1. 缺陷定性

| 层 | 泄漏前状态 | 后果 |
|---|---|---|
| 案例文件 process_description | d03/d04/d07/d11/d14 直述故障（"IDV 3"、"集管压力降低"、"阀粘滞"等） | 违反 C1 真值隔离契约 |
| briefs | 已重新生成（clean） | — |
| run 目录 user_context.json | **5/12 仍为泄漏文本**（16:45 轮在去泄漏前生成） | 管线可见输入含答案 |
| notes（诊断推理留痕） | d03/d11/d14 含跨场景引用或泄漏期措辞 | 推理可证性受损 |

## 2. 修复步骤（全部执行）

1. **S1 强制重建**：`run-tier.mjs prepare --force` 全 12 场景——run 目录从
   已去泄漏的案例文件重新生成（user_context 随之干净）；
2. **S2 重新生成 briefs** 并做泄漏扫描（briefs + user_context 双查，"本例为/集管/粘滞/难检故障"零命中）；
3. **S3 重新推理**：归档旧 notes，12 份 note 全部在干净 brief 上重写；
   推理纪律追加约束——**只准引用本场景 brief 内的统计数字**（禁止跨场景引用，如"对照 d04 的 10.06σ"）；
4. **S4-S6 重跑**：门禁 + 独立评分 + 聚合 + 报告；结果与上一轮对比，**如实报告差异**；
5. **脚本修正**：
   - `run-benchmark.mjs` 过期消息 "all 8 notes" → 动态数量；
   - `verify-repro.mjs` 加严：覆盖缺失（graded < cases）从 warning 升级为 failure；
   - 新增 `check-leakage.mjs` 静态哨兵：扫描 briefs + 全部 run 目录
     `00_input/user_context.json` 中的故障直述模式（"本例为…阶跃/粘滞/降低/随机变化"等），
     非零命中即失败退出，并挂入一键入口 S0；
6. **经验库同步**：experience/results 与 experience/reports 全量刷新。

## 3. 诚实性声明（写入论文口径）

- 泄漏期间产出的 9/9 结果**作废**；以本计划执行后的干净重跑结果为准；
- 复现语义保持两级表述：S1/S2/S4-S6 确定性可复现；S3 为 agent 推理，
  复现指"在相同确定性证据上独立重新推理"，非字节级复现；
- judge 分数为管线内部质量门（自评），外部评分仅 top1/topk/calibrated/control_pass。

## 4. 验证结果（执行后回填）

- 泄漏扫描：12 briefs + 12 user_context 全部 clean（本文件提交时的 check-leakage.mjs 退出码 0）；
- 12 份新 note 全部满足"仅引用本场景 brief 数字"纪律；
- 重跑结果与门禁：见 `results/benchmark/metrics.json` 与 `repro_report.json`（本轮为准）。
