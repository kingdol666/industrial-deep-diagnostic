# 数据集清单：文献来源、获取渠道、真值体系

> 对应调研文档 `docs/dataset-experiment-research.md` 中 Exp-1 ~ Exp-6 的数据集。全部信息经 2026-09-10 实际拉取验证。

## 1. TEP — Tennessee Eastman Process（主战场，Exp-1/2/5/7）

| 项 | 内容 |
|---|---|
| 起源文献 | Downs & Vogel, "A plant-wide industrial process control problem", *Comput. Chem. Eng.* 17(3), 1993 |
| 经典 Braatz 版（已拉取） | `github.com/camaramm/tennessee-eastman-profBraatz`（UIUC 1998-2002 版权声明，公开）。`d00/d00_te`=正常，`d01–d21(_te)`=21 类故障；训练 480 行、测试 960 行 × 52 列，空格分隔无表头；采样 3 分钟（测试 960 样本 = 48h），故障在测试文件第 161 样本（8h）注入 |
| Rieth 版（大规模评测用） | Harvard Dataverse `doi:10.7910/DVN/6C3JR1`（Public Domain）。4 个 RData 共 ~1.4GB；55 列 = faultNumber + simulationRun + sample + 52 变量；20 故障 × 500 runs；3 分钟采样，训练 25h/测试 48h，故障在训练 1h/测试 8h 注入 |
| Reinartz 扩展版（推荐主用） | Reinartz, Kulahci, Ravn, *Comput. Chem. Eng.* 149:107281, 2021。DTU Data <https://data.dtu.dk/articles/dataset/Tennessee_Eastman_Reference_Data_for_Fault-Detection_and_Decision_Support_Systems/13385936>。**6 个 h5 文件（TEP_Mode1-6）每个 ~23.9GB（共 ~143GB，本地拉取不现实，需按需导出）**；28 故障 × 6 操作模式 × 500 seeds |
| 变量 | 52 列 = XMEAS(1-41)（22 连续测量 + 19 气体成分）+ XMV(1-11)（操纵变量）。官方变量表见 [ground-truth/tep-faults.md](ground-truth/tep-faults.md) |
| 根因真值 | IDV(1)-(15) 与 IDV(21) 有教科书级根因记载（Chiang, Russell & Braatz 2001）；IDV(16)-(20) 官方标注 **Unknown**。故障 3/9/15 是文献公认 PCA 难检测（对 LLM 管线预期输出 COMPETING_SET/NEEDS_DATA） |
| 许可 | 公开/公有领域（Rieth 版显式 Public Domain） |
| 引用 | 时序 FDD 论文标准基准（FaultExplainer、FDDBenchmark 均用） |

## 2. SKAB — Skoltech Anomaly Benchmark（真实试验台，Exp-3）

| 项 | 内容 |
|---|---|
| 官方仓库 | **`github.com/waico/skab`**（⚠️ 调研文档里写的 `hndrec/SKAB` 已失效，仓库已迁移） |
| 论文 | Katser et al., "Skoltech Anomaly Benchmark (SKAB)", 2021（DOI: 10.34740/KAGGLE/DSV/1693952） |
| 规模 | 35 个 CSV（34 含集体异常 + 1 无异常），分号分隔，8 传感器列 + anomaly/changepoint 两列标签，1Hz，共 ~3.7 万行 |
| 传感器 | Accelerometer1RMS、Accelerometer2RMS（振动 g）、Current（A）、Pressure（Bar，泵后回路）、Temperature（电机本体 ℃）、Thermocouple（回路流体 ℃）、Voltage（V）、Volume Flow RateRMS（L/min） |
| 试验台 | 水箱 + 阀门 + 离心泵闭环回路（Skoltech 实物试验台，非仿真） |
| 根因真值 | 每文件夹一种人工注入故障：valve1（泵入口阀关闭）、valve2（泵出口阀关闭）、other/1-4（流体泄漏/添加）、other/5-9（转子不平衡五形态）、other/10-11（水量缓增/突增）、other/12-13（排水至气蚀/入口两相流气蚀）、other/14（高温供水）。完整表见 [ground-truth/skab-anomalies.md](ground-truth/skab-anomalies.md) |
| 标签覆盖 | ⚠️ 实测 34/35 文件有 anomaly 标签（共 13,067 个异常点），标签值为 `1.0`/`0.0` 浮点格式；个别文件（如 valve1/0 在部分目录）无标注时段 —— **评测真值以"文件夹级故障类型"为准，标签只用于检测时窗评分** |
| 许可 | GPL-3.0 |

## 3. IndPenSim — 工业级青霉素发酵基准（批次过程泛化，Exp-4）

| 项 | 内容 |
|---|---|
| 论文 | Goldrick et al., "Modern day monitoring and control challenges outlined on an industrial-scale benchmark fermentation process", *Biotechnol. Bioeng.* 2019（数据集配套 *Comput. Chem. Eng.* 127:247-258） |
| 官方数据 | Mendeley Data `pdnjz7zz5x` v2（CC BY 4.0），单 zip 504MB：<https://data.mendeley.com/datasets/pdnjz7zz5x/2>；镜像 <http://www.industrialpenicillinsimulation.com/> |
| 规模 | `100_Batches_IndPenSim_V3.csv`：2,566MB，表头 2,239 列，113,935 数据行 |
| **实测文件布局（重要，官方未文档化）** | ① 行块纵向堆叠，每批一个连续行块（895–1390 行），**field[35] `2-PAT control(PAT_ref:PAT ref)` = 批次号 1–100，是权威批次标识**；② field[0..30] 为过程变量（Time (h) + 曝气/搅拌/糖流加/酸碱流加/冷却水/注入水/罐压/DO2/青霉素浓度/体积/重量/pH/温度/产热/尾气 CO2·O2/OUR/CER 等），field[31] `Fault reference` = 故障激活时段标志；③ field[37..38]（表头名 Batch ID/Fault flag）是遗留脏列，忽略；④ field[39..2238] = 拉曼光谱通道（表头名 2400→201 递减的波数 cm⁻¹），行内平滑谱线 |
| 真值 | Statistics CSV：批次 1–90 正常（0），**91–100 故障（1）**；`Fault reference` 列给出故障激活的精确时间窗（已实测提取：如批次 91 有 20–30.2h / 76–92.2h / 200–214.2h 三窗）。故障类型（曝气故障、pH 传感器漂移、DO2 下降等）见 Goldrick 2019 原文表 |
| 控制策略分段 | 批次 1–30 recipe 驱动；31–60 操作员控制；61–90 Raman-APC；91–100 故障批 |
| 采样 | 0.2h（12 分钟），批次时长 200–258h |
| 注意 | 离线分析变量（PAA_offline、NH3_offline、X_offline、P_offline、Viscosity）大量 NaN —— preprocessor 保留 NaN、processor 正常处理 |

## 4. SWaT / WADI — iTrust 水处理试验台（第二梯队，Exp-3 补充）

| 项 | 内容 |
|---|---|
| 来源 | Singapore University of Technology & Design, iTrust 实验室：<https://itrust.sutd.edu.sg/itrust-labs_datasets/> |
| 获取方式 | **填表申请制**（学术免费，审批 1–2 周，需签 EULA）——本次未拉取 |
| SWaT | 51 传感器（LT/PIT/AIT/FIT/LS/PG 系列），11 天连续（7 天正常 + 4 天攻击），**36 类攻击 = 36 个已知根因**（攻击点与手法有官方文档） |
| WADI | 123 传感器，16 天，15 类管网攻击 |
| 文献 | Goh et al., "A Dataset to Support Research in the Design of Secure Water Treatment Systems", CRITIS 2016 |
| 论文使用 | 大量顶刊用它做 FDD/异常检测，攻击文档即真值，可信度高 |

## 5. FailureSensorIQ — MCQA 对标集（Exp-6，对标 Gong JII 2026）

| 项 | 内容 |
|---|---|
| 官方仓库 | `github.com/IBM/FailureSensorIQ`（已拉取 `eval_data/` 全部 jsonl） |
| 论文 | IBM, FailureSensorIQ（HF Leaderboard）；Gong et al. 2026（JII）的多代理诊断框架即在此基准上报告 36.5%→54.6% |
| 形态 | MCQA 问答 jsonl：`{question, options[5], option_ids, correct[bool×5], asset_name, relevancy, question_type}`，覆盖 ISA 资产（电机、空压机、风机等）× 故障模式 × 传感选择/失效模式推理。文件：`eval_data/fmsr_processed/quiz_relevant.jsonl`、`quiz_irrelevant.jsonl`、`filtered_data_all_Mar_30_2025*.jsonl`、`industrial_mcp_original.jsonl`（perturbed 版反记忆评测） |
| 用法 | 不进诊断管线；接管线首尾做组件能力评测，与 Gong 同表对比 |

## 6. 其他备选（未拉取）

| 数据集 | 来源 | 备注 |
|---|---|---|
| MetroPT-3 | UCI（轨道交通空压机，1.5M 行 × 15 通道） | 故障模式有文档，可作轨道交通域泛化 |
| Damadics | 阀门执行器 19 类故障，工业现场 | 经典阀门诊断基准 |
| Paderborn 轴承 | FDDBenchmark 内置 `lessmeier_bearing` | `pip install fddbenchmark` 可取 |
| FDDBenchmark | `pip install fddbenchmark`（AIRI-Institute） | 附带 rieth_tep 加载器 + CDR 评测器，可省自写导出器 |
