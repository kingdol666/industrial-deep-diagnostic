# L5 锂电涂布产线 · 多源异构 E2E 验收标准与测试记录

> 目的：验证 `industrial-hetero-preprocessor`（E-1H）与 `industrial-line-stability-report`（产线报告）的
> 集成是**场景通用**的——用与 BOPET 完全无关的领域（锂电极片涂布）真实形态数据跑完整链。
> 数据：`data/`（DCS 主表 + 面密度剖面 + 辊压厚度 map + CCD 图像流 + 操作备注 + 化验辅助表）。
> 真值：`ground_truth.md`（注入故障 = 第 9 天起涂布辊右端轴承磨损，**不喂给分析端**）。

## 验收标准

| # | 断言 | 判据 |
|---|---|---|
| AC-E2E-1 | E-1 稳定模式主表选择不被异构源劫持 | `selected_table.file == L5_dcs_process_10min.csv`；profile/map/notes/lab 各有处置记录 |
| AC-E2E-2 | E-1H 全形态发现 | manifest `status=ok` 且 sources 覆盖 profile/map/image_stream/text 四形态；`07_hetero/preprocessed_data_hetero.csv` 存在且 3024 行 |
| AC-E2E-3 | 特征正确响应注入故障 | `HX-PROF-<SLUG>-EDGE-R-DEV` 在 10-03 前后均值符号/幅度翻转（前 ≈0，后显著为负）；`HX-IMG-<SLUG>` 缺陷相关特征后段抬升；`HX-TXT-*-EVT-*` 在备注时刻命中 |
| AC-E2E-4 | E-1H 门禁 | `quality_gate.mjs` exit 0，verdict ok |
| AC-E2E-5 | LSR 通用分析接通 | `stability_analyzer.py analyze --data <joined>` exit 0/1；`stability_report.json` + HTML 生成；LSR quality_gate exit 0（PASS） |
| AC-E2E-6 | 异构特征进入产线报告 | report 的参数/发现中含 ≥3 个 `HX-*` 通道；综合评分 <85（反映劣化）；场景主语自适应（锂电涂布，非 BOPET 残留） |
| AC-E2E-7 | 故障定位能力 | HX-PROF 边缘通道的漂移/SPC 发现时段与真值（第 9 天起）一致（±1 天）；报告能区分"浆料批次切换"（第 7 天）与主故障 |
| AC-E2E-8 | 场景通用性 | hetero/LSR 代码中无 BOPET/锂电场景专用字符串；LSR 未给本体时走 auto 模式并完成评估 |
| AC-E2E-9 | 溯源链 | 任一 HX 列可走通 列名→contract→features→source_sha256 回算 |

## 测试记录（2026-10-17 执行）

**AC-E2E 1–9 全部 PASS**（逐项证据见同目录 `TEST_REPORT.md` §3）。要点：
主表 DCS（3024×22, score 17.0）不被劫持；E-1H status=ok 4 源 40 HX 列、门禁 ok；
LSR 55 参数受评（35 个 HX）、20 发现（15 条 HX）、73.3/B、门禁 11/11 PASS、本体 auto；
故障响应：EDGE-R-DEV -0.17→-0.92（右缘）/左缘不动；MAP-P95 +0.69；IMG-ENTROPY +0.04；
真值根因 L5-CT-GAP-R01 同步 SPC high。本轮另修复 5 个通用性缺陷（见 TEST_REPORT §4）。

（见下方执行章节）
