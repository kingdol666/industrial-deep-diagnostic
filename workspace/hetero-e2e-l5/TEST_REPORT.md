# L5 锂电涂布产线 · 多源异构 E2E 测试报告

- **日期**: 2026-10-17（本轮）
- **被测对象**: `industrial-hetero-preprocessor`（E-1H）× `industrial-line-stability-report`（产线报告）集成
- **数据场景**: 锂离子电池极片涂布产线 L5（与 BOPET 零关联的领域，用于证明接入的场景通用性）
- **执行方式**: 全部命令真实执行；本文所有数字来自 `run/` 下的实际产物

---

## 1. 数据集（`data/`，生成器 `generate_l5_dataset.py`，seed=20261017）

| 源 | 文件 | 形态 | 规模 |
|---|---|---|---|
| DCS 主表 | `L5_dcs_process_10min.csv` | anchor 时序 | 3024 行 × 22 列（21 天 @10min） |
| 面密度横向剖面 | `L5_ad_scan_30min.csv` | PROF（时间×pos_01..24） | 1008 快照 @30min |
| 辊压厚度场 | `L5_calender_map_2h.csv` | MAP（时间,x,y,值） | 252 快照，5×4 网格 |
| CCD 表面检测 | `ccd_frames/*.png` + `L5_ccd_index.csv` | IMG（索引+文件名双时间） | 60 帧 @8h |
| 操作备注 | `L5_operator_notes.csv` | TXT | 5 条带时间备注 |
| 化验 | `L5_lab_electrode_2h.csv` | 低频辅助 | 252 行 @2h |
| 参数对照 | `L5_参数对照说明.md` | 文字背景（context） | 列表体，无大表格 |

**注入真值（`ground_truth.md`，未喂给分析端）**：第 9 天（2026-10-03）起涂布辊右端轴承磨损 →
右间隙 +0.008mm 渐进 → 右缘面密度偏薄 -1.5% → 横向 CV 1.25→2.15%（超内控）→ 优品率 98.5→96.6%（滞后 6h）；
CCD 缺陷斑 2→6/帧；辊压厚度场右侧 +1.5μm。混杂项：第 7 天浆料批次切换；第 14 天计划保养降速 2h。

## 2. 执行链（四步，全部真实命令）

```
① E-1 稳定模式   data_preprocessor.py --data-path data --output run/00_input
                 --stability-single-primary --recursive
② E-1H           build.py --raw-path data --run-dir run --recursive
③ E-1H 门禁      quality_gate.mjs --run-dir run --raw-path data
④ LSR 产线报告   stability_analyzer.py analyze --run-dir run
                 --data run/07_hetero/preprocessed_data_hetero.csv --time-col 时间
                 → report_builder.py → LSR quality_gate.mjs（11 项检查）
```

## 3. 验收结果（AC-E2E 全 9 项 PASS）

| # | 断言 | 结果 | 证据 |
|---|---|---|---|
| 1 | 主表不被异构源劫持 | **PASS** | `selected_table.file = L5_dcs_process_10min.csv`（3024×22, score 17.0）；剖面/map/索引/备注/化验全部 `excluded_from_scoring` 并留处置记录；参数说明进 context |
| 2 | E-1H 全形态发现 | **PASS** | `status=ok`，4 源：image_stream(60)/map(252)/profile(1008)/text(5)，40 个 HX 列；joined 表 3024 行（行序不变） |
| 3 | 特征响应注入故障 | **PASS** | `HX-PROF-…-EDGE-R-DEV` -0.17→**-0.92**（右缘偏薄），左缘 -0.17→-0.09（不动=单侧证据）；`HX-MAP-…-P95` 188.43→**189.12**；`HX-IMG-…-ENTROPY` 3.047→**3.084**；EVT-CLEANING 命中 6 行 |
| 4 | E-1H 门禁 | **PASS** | verdict=ok，0 fails |
| 5 | LSR 通用分析接通 | **PASS** | analyze 32s exit 0（ok）；HTML 375KB self-check pass；**LSR 门禁 11/11 PASS** |
| 6 | 异构特征进入产线报告 | **PASS** | 55 参数受评中 **35 个为 HX 通道**；20 条发现中 **15 条指向 HX 通道**（PROF/MAP 全家族 SPC 违规 high）；评分 **73.3/B（亚稳定）** 反映劣化 |
| 7 | 故障定位与区分 | **PASS** | DCS 侧同步抓到真值根因 `L5-CT-GAP-R01`（右间隙）SPC high 与 `L5-QM-YIELD01` high；混杂项 `L5-SL-SC01`（浆料切换）也被单独列出可辨；24h 滚动越限起点 10-05（注入斜率 0.12/天下的物理一致滞后，真值起点 10-03） |
| 8 | 场景通用性 | **PASS** | E-1H/LSR 代码 grep `bopet|涂布|锂电|coating|calender` 零命中（唯一命中是 LSR 文档引用的历史案例文件名）；LSR 本体走 **auto 模式**完成评估（未给任何领域本体） |
| 9 | 溯源链 | **PASS** | 门禁 H3 携带 `--raw-path` 回算 source_sha256 全过；列名→contract→features→源文件四步闭合 |

## 4. 本轮发现并修复的缺陷（全部为通用性缺陷，非场景特设）

1. **E-1 稳定模式选表被宽矩阵劫持**（AC-E2E-1 初测 FAIL）：24 列剖面靠"数值列计数"压过 3024 行 DCS。
   修复：`_score_table` 按**列族**计分——≥4 列同前缀的测量矩阵族最多计 3 个数值列、列数项改按族数。
   场景无关（纯列名结构规则）；E-1 既有套件 ALL TESTS PASSED。
2. **anchor 原始源表被文本探测误认领**（产生 3024 条垃圾注释）：主表是 E-1 的输出副本，
   按路径排除无效；改为从预处理报告 `selected_table.file`（按 raw 目录解析相对名）排除。
3. **图像索引与目录流重复认领**（同一批帧进两个源）：索引认领只读了探针前 50 行 → 改为全量认领。
4. **map 小网格被绝对阈值全灭**（5×4=20 格 < 30 格下限）：改相对下限 `max(10, 50% 格数)`，
   GRAD-P95 单独保留 30 格绝对下限（小网格梯度噪声主导）。
5. **m3 防劫持测试前提过期**：评分修复后"宽表分更高"的前提不再成立——改为双层防御断言
   （评分层不再劫持 + 递归发现层跳过 `07_hetero/`）。

## 5. 回归与一致性

- 全量单测：**47 case / 498 断言 / 0 失败**（含修复后复跑）；E-1 既有套件 ALL TESTS PASSED；
  `test-skills` 24/0；镜像 `--check` exit 0。
- LSR 对**无 07_hetero 的目录**行为不变（m3 用例含该断言）；benchmark 路径不经过 E-1（隔离声明不变）。

## 6. 产物位置

- 数据与真值：`workspace/hetero-e2e-l5/{data, ground_truth.md, generation_manifest.json}`
- 运行产物：`workspace/hetero-e2e-l5/run/{00_input, 07_hetero, line_report/}`
  - `07_hetero/hetero_manifest.json`（4 源处置）/ `column_contract.json`（40 列语义）/ `features/`（各源原生节奏特征表）
  - `line_report/line_stability_report.html`（375KB 中文落地页）/ `stability_report.json` / `charts.json` / `html_selfcheck.json`
- 修复涉及：`data_preprocessor.py`（选表评分）、`build.py`（anchor 源排除）、`shapes/img.py`（索引全量认领）、`shapes/map.py`（相对格下限）、`tests/cases/test_m3.py`（前提更新）

## 7. 已知边界（如实）

- 跨模态相关性：LSR v1 的相关性对上限 10 对，本轮未出现 HX↔DCS 跨模态对（HX 以"受评参数+发现"进入报告，
  而非相关对）——跨模态因果联动属深度诊断管线（data-processor 显式列）的职责。
- 缓变故障的发现滞后与注入斜率一致（0.12 g/m²/天 → 24h 滚动 ~2.8 天越限）；这是物理决定的，非检测缺陷。
- LSR 场景主语在未给 context/本体时回退"对象"（通用默认）；给 `report_context.json` 即显示产线名。
