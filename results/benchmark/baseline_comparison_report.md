# Benchmark × Baseline 对比基线报告（双项目真实执行）

> 生成：2026-09-15 16:07 · 生成器：scripts/benchmark/build-baseline-suite-report.mjs（零硬编码判定）
>
> 被测双方：**IDD**（industrial-analysis-auto 完整管线，12 场景 canonical 判定）×
> **Baseline Suite**（Nuxt 复刻套件 baselines/baseline-suite，45 项实时运行：
> 经典 PCA / FE 协议复刻 / 同模型裸 LLM 协议）。模型变量受控：裸 LLM 臂与管线为同一 GLM 部署
>（GLM family (same deployment as IDD pipeline; ZCode CLI harness, Sept 2026 snapshot)），套件未配置 live 端点时回放其归档 raw 回答（逐条标注 recorded）。
> FE 上游快照：baselines/FaultExplainer @ 2fcfee9（MIT）。

## 1. 逐场景对比

| 场景 | IDD（判定/置信） | 裸LLM strict | FE-style（含候选） | 套件PCA 检出 T²/SPE | 套件FE 检出 |
|---|---|---|---|---|---|
| skab_valve1_1 | 未中 COMPETING_SET (conf 65) | 命中 | n/a | 100.0% / 100.0% | — |
| skab_cavitation_13 | 未中 COMPETING_SET (conf 58) | 命中 | n/a | 100.0% / 100.0% | — |
| skab_normal_control | 对照通过=true | normal ✓ | n/a | 1.0% / 1.0% | — |
| tep_d01_ac_feed_ratio | 命中 DETERMINED (conf 79) | 命中 | 命中 | 99.3% / 99.8% | 检出 (XMEAS_25) |
| tep_d03_hard | 未中 COMPETING_SET (conf 60) | 命中 | 命中 | 2.9% / 4.8% | 未检出 |
| tep_d00_normal_control | 对照通过=true | 未运行 | n/a | 1.0% / 1.0% | 未检出 |
| indpensim_batch093 | 命中 DETERMINED (conf 88) | 命中 | n/a | 15.0% / 73.9% | — |
| indpensim_batch001_control | 对照通过=true | normal ✓ | n/a | 1.1% / 1.1% | — |
| tep_d04_reactor_cooling_step | 命中 DETERMINED (conf 75) | 命中 | 命中 | 48.8% / 100.0% | 检出 (XMV_10) |
| tep_d07_header_pressure | 命中 DETERMINED (conf 82) | 命中 | 命中 | 100.0% / 99.5% | 检出 (XMEAS_4) |
| tep_d11_reactor_cooling_random | 命中 DETERMINED (conf 80) | 命中 | 命中 | 53.8% / 66.3% | 检出 (XMEAS_9) |
| tep_d14_reactor_valve_sticking | 命中 DETERMINED (conf 89) | 命中 | 命中 | 99.8% / 93.4% | 检出 (XMV_10) |

> 口径：裸 LLM = 同一盲态摘要单次调用（无候选）按 IDD 机理关键词严格评分；FE-style = top-3 含真 IDV 或别名类；
> PCA/FE 检出率由套件实时计算（与 benchmark 侧 baseline_pca.mjs 同协议）。套件 FE 臂在 benchmark 数据上的
> 检出格局复现文献结论：IDV3 未检出（检测极限），IDV4/IDV14 首要贡献特征落在冷却水阀 XMV_10。

## 2. 抽查复测（一致性）

- **套件侧**：tep_d14 全部 5 臂二次执行，与首次结果**逐字节一致**（剔除时间戳后 diff 为空）——确定性算法（PCA/FE 特征分解、协议组装）与 recorded 回放完全可复现。
- **IDD 侧**：tep_d14 两次独立完整管线执行（canonical 202609141855391 vs 复测 202609150454479）：
  判定类型相同（DETERMINED = DETERMINED，same=true），同一机理（XMV_10 阀粘滞 → 温度回路极限环振荡），置信 82 → 89（随机性带宽内）。
- **全量稳定性**：时代内判定+Top-1 一致性 15/15（详见 results/benchmark/stability_report.json；跨时代翻转=已记录的系统纪律收紧，非随机不稳定）。

## 3. 真实性声明

- 套件按契约不读取任何真值/关键词；准确率评分全部在 benchmark 侧（baselines.json / gradings）完成。
- 缺失的 LLM 臂（tep_d00 对照，3 项）为已记录的协议范围缺口（check 命令豁免并明示），不以编造答案补位。
- 本报告所有数字来自磁盘上的真实产物；重新执行流程（见 docs/benchmark/baseline-suite-pipeline.md）可完整再生成。

