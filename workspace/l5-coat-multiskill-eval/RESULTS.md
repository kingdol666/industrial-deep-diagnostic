# L5 锂电涂布线多源异构场景 · 三任务端到端测试汇整

日期：2026-10-17 ｜ 数据：`data/L5_COAT_20261001-20261021/`（21 天真实工况量级）
出题真值（勿投喂 agent）：`workspace/l5-coat-multiskill-eval/ground_truth.md`

---

## 0. 一页结论

新建「锂电正极极片涂布线」多源异构场景（**4 类异构源**：向量随时间的面密度横向剖面、CCD 图像流、DCS 参数表、交接班备注 + 化验负样本），按需派发三个分析任务，全部真实 agent 跑完并入库：

| 任务 | intent / skill | 终态 | 核心结果 |
|---|---|---|---|
| ① 哨兵快筛 | quick-screen / industrial-sentinel | completed | **alert**；3 条 critical（EDGE-OS / WT-CV / YIELD）方向全对；敏感性分析排除计划降速；给出 GAP-OS 单侧 +0.33 μm/天（R²=0.991）物理链线索 |
| ② 稳定性评分 | stability-report / industrial-line-stability-report | completed | **65.1 分 / C 级（波动）**；LSR 门禁 **11/11 PASS**；风险链量化命中真值（GAP-OS +3.44 μm、EDGE-OS +1.31 pp、EDGE-DS 恒定） |
| ③ 根因诊断 | deep-diagnosis / industrial-analysis-auto | completed | Step 0-9 全链一次通过：Judge **90 pass（0 修复轮）**、审计 **ENDORSED**、HTML 审核 **91 pass**、finalize **PASS**、closure **PASS**、log-check **exit 0（issues=[]）** |

**根因命中**：三个任务独立收敛到注入真值 —— **操作侧涂布间隙机构缓慢漂移（GAP-OS 120→124.5 μm，+0.28 μm/天）→ OS 边部面密度渐进增厚 → CV 越限 → 优品率下滑**；浆料批次切换（10-12）与烘箱三段干燥退化（10-15 起）被正确判为次要/并行因素，测厚仪漂移被排除。

---

## 1. 场景数据（真实工况量级，确定性可复现）

生成器：`workspace/l5-coat-multiskill-eval/gen_l5_data.py`（seed=20261017）。7 类文件 + 63 张图像 + 3 份说明文档，共 2.4 MB：

| 文件 | 形态 | 规模 | 说明 |
|---|---|---:|---|
| `L5_coat_main_10min.csv` | 参数随时间（DCS） | 3024×25 | 浆料/间隙/速度/烘箱/在线质量 20 个数值通道 + 批次/班组/状态码；班组（甲乙丙丁 12h 轮转）为人员维度 |
| `L5_AREAL_PROFILE_10min.csv` | **向量随时间（PROF）** | 3024×43 | 时间 × 41 测点（距操作侧边 25–625 mm，间距 15 mm），单位 g/m²，pos_01=操作侧 |
| `L5_ccd_index.csv` + `L5_ccd_frame_*.png` | **图像流（IMG）** | 63 帧 160×120 灰度 | 8 h 一帧；10-08 起操作侧纵向亮纹渐宽渐亮（+10→+50 灰阶） |
| `L5_operator_notes.csv` | **时间锚定文本（TXT）** | 10 条 | 交接班/报警/报修/换批/校准事实记录（人员操作维度） |
| `L5_lab_quality_2h.csv` | 化验（负样本） | 252×6 | 5 项互不相关指标 —— 验证 PROF 相干门槛不误判 |
| 三份说明文档 | 背景语境 | — | 工艺背景 / 异常现象与已做排查 / 参数代号对照 |

**注入事件（真值）**：
- **E1 主因**：10-08 00:00 起 OS 间隙丝杆微松，GAP-OS 120→124.6 μm 线性缓开；剖面 OS 边缘带（pos_01-04，高斯 σ=85 mm）渐进增厚至 +3.3 g/m²（+1.5%）；EDGE-OS 0.15%→1.9%；CV 1.25%→2.2%；YIELD 滞后 6 h 降至 96.35%；**全幅均值恒 220.0**（泵总量补偿，质量守恒在剖面 mass_balance_integral=0.0002 得到验证）。
- **D1 干扰**：10-12 08:00 浆料批次 SL-2231→SL-2245（固含量 +0.25、粘度 +150；面密度 +0.35 g/m² 阶跃 24h 衰减，无空间选择性）。
- **D2 干扰**：10-15 02:00 起烘箱三段效率下降（HOUT3 45→75%、T3 118→116.5 ℃、MOIST 320→470 ppm，内控 ≤500 未超）。
- **计划降速**：10-05 / 10-12 / 10-19 三窗（MODE=2）。

**数据物理一致性（生成后核验）**：剖面 OS 边缘 -0.20%→+0.93%、DS 边缘稳定 -0.25%；剖面 EDGE-L vs 在线 EDGE-OS **r=0.995**；CCD 亮纹带均值 +0.09→+22 灰阶；两批次阶跃与降速窗按设计呈现。

---

## 2. 接入与门禁（E-1 / E-1H 预检）

- **E-1**：选主表 `L5_coat_main_10min.csv`（3024×25）；剖面因 +5 min 错位触发防膨胀门（6048 > 1.5×3024）**merge abandoned**，主表不被 41 个 pos 列污染。CCD PNG 被正确跳过（非表格）。
- **E-1H**：**恰好 4 源全识别** ——
  - `L5AREALPROFILE10MIN`：profile / featured / 3024 帧 / 18 特征
  - `L5CCDINDEX`：image_stream / featured / 63 帧 / 7 特征（MEAN/STD/ENTROPY/SATFRAC/DARKFRAC/FOCUS…）
  - `text-l5operatornotes`：text / featured / 10 条 / 5 特征（EVT-ALARM / EVT-CALIBRATION / EVT-STOP 事件窗 + 班次协变量）
  - `text-src`：背景文档散文事件 / 4 特征
  - **化验表未被误判**（PROF 相干门槛负样本回归通过）；总 34 列；**H1–H8 门禁 exit 0**。

---

## 3. 任务① 哨兵快筛（quick-screen）

- run：`202610170507508_L5_COAT_sentinel_screen`（DB completed，report + quick_screen_report.html 入库）
- 结论 **alert**：110 条告警；**3 条 critical** 全部方向正确 ——
  - EDGE-OS 最差 **1.942%**（内控 ±1.5%，首越 10-18 06:40）
  - WT-CV 最差 **2.229%**（内控 ≤2.0%，首越 10-18 11:00）
  - YIELD 最差 **96.267%**（目标 ≥98%，首破 10-09 20:10）
- **计划降速排除**：剔除 MODE=2 行后 109/110 条告警一致，计划降速窗内 **0 条 primary 告警**（三窗只造成速度 -23σ 瞬时偏离）。
- **物理链线索**：GAP-OS 单侧线性 +0.329 μm/天（R²=0.991），与 EDGE-OS r=0.992、CV r=0.992、YIELD r=−0.988；DS 恒 120.00、全幅均值恒 220.0。
- **D2 线索**：HOUT3 45→72.8%、T3 118→116.6 ℃ 与 MOIST 同步（r=0.983），提示三段干燥退化（判为线索不下结论，符合哨兵纯分析定位）。

## 4. 任务② 稳定性评分（stability-report）

- run：`202610170517532_L5_COAT_stability_report`（DB completed，`line_report/` 入库）
- **65.1 分 / C 级（波动）**；评估 40 参数、9421 个 SPC 违规剧集、19 项显著漂移；最需关注：WT-CV / EDGE-OS / EDGE-DS。
- **LSR 门禁 11/11 PASS**（schema/核心字段/分数-分级一致/zero_llm/sha256/HTML≥8KB/selfcheck/severity/无 autonomy）；HTML selfcheck 13 项全 true。
- **异构接入**：评分消费 `07_hetero/preprocessed_data_hetero.csv`（4 源），HX-PROF 均值/STD 进入 SPC 参数集；稳态口径正确（MODE=1 only，3000 行；早窗 1002 / 晚窗 996）。
- **风险链量化命中真值**：GAP-OS 早→晚 **119.999→123.441 μm（+2.87%）**，GAP-DS −0.002（阴性对照）；EDGE-OS +1.309 pp，EDGE-DS −0.001；2 个时间不变量通道如实披露剔除。

## 5. 任务③ 根因诊断（deep-diagnosis）

- run：`202610170505114_L5_COAT_areal_defect_diag`（DB completed；report.md / diagnostic-report.html / optimizer.md 入库，外部结果视图返回 md+html 路径）
- **全链一次通过，零修复轮**：Judge **90 pass（blocking 0）** → 审计 **ENDORSED** → HTML 审核 **91 pass（blocking 0）** → finalize **PASS** → closure **PASS** → log-check **exit 0，issues=[]**；manifest 11/11 步 completed。
- **本次 VLM 真实运行**（引擎具备视觉）：data-processor 派发 vlm-visual-analyzer 读图，报告证据组合标注 [L3]统计+[L2]离线+**[L4]VLM 视觉**。
- **主结论（与真值一致）**：`DETERMINED` —— **OS 侧涂布间隙通道缓慢漂移（+0.28 μm/天，MK p=1.6e-8，120.1→124.5 μm）→ OS 边部增厚 → CV 升高 → 优品率下滑**；物理机制落到狭缝 Poiseuille 流 Q∝h³；置信度 **79/100**，因"机械漂移 vs 间隙测量漂移"不可分而受 **80 上限**约束（诚实封顶）。
- **剖面证据实用化**：`profile_shape_analysis.json` 早/晚窗对比 —— OS 边带 **+2.11 g/m²**、DS 边带 −0.34、中心 −0.10、全幅均值 **+0.0003 g/m²**、质量守恒积分 ≈0；在线-离线 bias 0.0243 g/m²、剖面相关 r=0.9938。
- **判别矩阵全部正确**：
  - H2 浆料批次：10-12 阶跃无 OS/DS 选择性，换批后 EDGE-DS 不变 → 排除（ONE_SIDE_EXCLUDED）
  - H3 烘箱干燥：MOIST 变点 10-16 晚于 EDGE-OS 10-08、全幅对称 → 非起点（并行次要因素）
  - H4 测厚仪：bias 0.024 g/m² + 校准无台阶 + 剖面互证 → 排除
  - H5 剖面配准漂移：SHIFT-EST 中位 0（p=0.184）→ 排除
  - H6 刮刀：10-19 换刀 NO_RESET 且 EDGE-OS 反升 → 排除
- 置信度记账：五因子 25+15+16+13+10=79 ≤ 上限 80。

---

## 6. 验收对照（ground_truth.md 判分口径）

| # | 验收项 | 结果 |
|---|---|---|
| A1 | 数据完整性/确定性/格式合规 | **PASS**（seed 复现；E-1 选主表 3024×25；merge abandoned） |
| A2 | E-1H 恰好识别 PROF+IMG+TXT（+背景文本），化验表不误判 | **PASS**（4 源 34 列；gate exit 0） |
| A3 | ①快筛完成且方向正确、排除计划降速 | **PASS**（alert；3 critical 方向对；0 primary 告警落在降速窗） |
| A4 | ②评分完成、门禁全过、风险链提及 OS 边部/间隙 | **PASS**（65.1/C；11/11；GAP-OS/EDGE-OS 量化） |
| A5 | ③诊断完成 Step 0-9、Judge ≥90、审计 ENDORSED、finalize PASS、log-check 0 | **PASS**（90/ENDORSED/PASS/exit 0 issues=[]，零修复轮） |
| A6 | 结论命中 E1，D1/D2 正确降权 | **PASS**（H1 OS 间隙；H2 阶跃无选择性、H3 干燥为并行次要） |
| A7 | 剖面/图像/文本证据被实际使用 | **PASS**（profile_shape_analysis 早晚报+质量守恒；VLM 读 CCD；EVT 事件窗入 joined 表） |
| A8 | 置信度诚实、子机理不可分如实披露 | **PASS**（79/100 受 80 上限约束；"机械 vs 测量漂移不可分"明示） |
| A9 | 三任务结果入库且外部结果视图可取 | **PASS**（3 run DB completed；result 返回 md+html 路径） |
| — | 完全无人工介入 | **PASS**（本轮三个 run 全部由 backend 自主跑完，未手工补齐任何阶段） |

## 7. 观察与残留事项

1. **本轮 claude 引擎全程稳定**：三个 run 无提前 end_turn、无 resume；与上一个 BOPET 场景的偶发 end_turn 竞态相比，本轮（三任务并发 2+排队）未复现——进一步支持"偶发竞态"判断。
2. **VLM 可用性随引擎环境变化**：本轮 vlm-visual-analyzer 真实读图（L4 视觉证据入链）；BOPET 首轮则因 no_vision_model 跳过。依赖环境，两轮报告均如实标注。
3. **evidence.json 未直接引用 HX 列名**：诊断使用原始剖面文件做带分析（等效且可复算），HX 列主要被哨兵/稳定性评分消费。可接受；若要求诊断也走 HX 列口径，可在 data-processor 提示中显式点名。
4. **DB 行的 judge_verdict/score 字段为空**（judge_feedback.json 实为 90 pass）：engine result 解析未回填该两列，报告与工件一致，仅展示层小缺口。

## 8. 产物索引

- 场景数据：`data/L5_COAT_20261001-20261021/`（含 63 帧 CCD PNG）
- 生成器/真值：`workspace/l5-coat-multiskill-eval/gen_l5_data.py`、`ground_truth.md`
- 预检：`workspace/l5-coat-multiskill-eval/precheck/07_hetero/`
- ①快筛：`workspace/diagnostic-runs/202610170507508_L5_COAT_sentinel_screen/`（report.md、sentinel/alert.json、quick_screen_report.html）
- ②评分：`workspace/diagnostic-runs/202610170517532_L5_COAT_stability_report/`（line_report/stability_report.json + line_stability_report.html）
- ③诊断：`workspace/diagnostic-runs/202610170505114_L5_COAT_areal_defect_diag/`（report.md、diagnostic-report.html、optimizer.md、05_review/judge_feedback.json + html_review.json）
- 本汇整：`workspace/l5-coat-multiskill-eval/RESULTS.md`
