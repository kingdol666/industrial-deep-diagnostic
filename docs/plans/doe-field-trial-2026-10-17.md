# DOE 分析能力 × AgentWorkShop 抓数 — 完整测试报告

- 日期：2026-10-17
- 被测：`feat/doe-ontology-first`（工作树 `D:/codes/myskills/idd-doe-impl`）
- 平台：AgentWorkShop v0.7.66（`D:/codes/ABO/AgentWorkShop`，只读）
- 场景：BOPET 12 µm 薄膜线，一条连续时间线上同时覆盖异常、波动、DOE 三类任务
- 结论：**IDD 侧“抓数 → 本体 → 分析 → 可执行推荐 → 可检索”的 DOE 闭环已跑通；平台侧仍有 1 个 P0 与 4 个一等公民缺口（见 §6）。**

---

## 0. 六个问题的直接回答

| 问题 | 结论 | 证据 |
|---|---|---|
| 能否分析 AgentWorkShop 抓到的数据，得到调参优化依据？ | **能**。新增 `aws_capture.py` 把“每节点时序导出 + 试验设计 + QC”装配成 `run_table`，DOE 分析恢复出植入效应（误差 ≤ 5%），给出带 `platform_ref` 的联合作业点与 recipe patch | §3.1、§4 |
| 能否针对多种任务场景？ | **能**。同一份抓数分别跑通 quick-screen（异常）、stability-report（波动）、doe-analysis（试验），三套产物与证据链齐全 | §3.2–3.3 |
| 能否支持多源异构数据？ | **能**。63 点横向剖面 + 22 条操作备注经 E-1H 变成标量特征并入 DOE；剖面边缘特征与植入信号相关 0.976，剖面均值与植入厚度相关 0.999997 | §3.4 |
| 能否与本体模型构建结合？ | **能**。`built → reused`（同一 context 第二次 ≤60s 复用），coverage 3/3 + 5/5，一致性校验 15 项、2 条 advisory 矛盾（不阻断结论） | §3.5 |
| 能否与 AgentWorkShop 集成，做异常/波动/DOE？ | **IDD 侧能，平台侧部分**。六意图对齐 5/5；平台 `diag_run` 的缺省问题会把 DOE 业务问题写成“深度根因诊断”（P0，见 §6） | §3.7 |
| 能否按真实场景选用合适的 skill 流程并检索结果？ | **能**。20/20 路由检查；12 条结果索引，7/7 关键词查询命中；artifact manifest 15 件、后端 API 可读 | §3.6–3.7 |

---

## 1. 本次新增/修复

| 类型 | 内容 |
|---|---|
| 新能力 | `industrial-doe-analyzer/scripts/aws_capture.py`：`inspect` / `pivot` / `build`；把平台抓数装配成 run table + `doe_context`，含稳态聚合、状态过滤、排除项、E-1H 特征 join、平台引用 |
| 新测试 | `tests/test_aws_capture.py` 46 条（inspect/pivot/build/context/exclude/errors/repeat）；后端 `artifact-manifest.test.mjs` 7 条 |
| 合同修复 | `doe_context` / `analysis_context` schema 支持 `linear` 约束（`coefficients + rhs`，无 `factor`）；约束引擎把 `rhs` 翻译成 `max`，不再静默丢弃 |
| 合同修复 | `current_setpoint` 现在是 `current_baseline` 的首选来源（以前被试验中位数覆盖，recipe patch 的 `from` 错成设计中心） |
| 缺陷修复 | `aws_capture` 的 provenance 文件改名 `capture_manifest.json`（旧名会被 00_input 扫描误当数据表） |
| 缺陷修复 | 本体 brief 的 confounders 去重（声明 covariate 曾被列两次） |
| 互操作修复 | 稳定性报告读取 v1.1 `operating_windows`（`factor` + `range` + `window_role`），不再把每条窗解析成 null；同时读取 `joint_setpoints` 并在 HTML/发现中披露 |
| 可视化修复 | DOE 报告 §11 的联合点表新增“联合设定值 / D / 逐响应预测 + PI95”，执行者不再需要去翻 JSON |
| API 修复 | `/api/external/v1/analyze` 透传 `ontologyMode/Scene/Source/DataStage/DevOverride` |
| 文档 | `references/data-formats.md`（数据格式全量）、`references/platform-integration.md`（平台合同/缺口）、本报告、demo README |

---

## 2. 场景与数据

### 2.1 一条线，三段任务

| 段 | 数据 | 任务 | 植入真值 |
|---|---|---|---|
| `history/` | 2026-10-15 00:00–06:00，8 节点 × 1440 行（15 s） | sentinel 基线 | 稳定，无调整 |
| `line/` | 2026-10-16 08:00–14:00，8 节点 × 1440 行 | quick-screen + stability | Z4 温度 +0.9 °C/h；60% 处张力 +8 N、环境 +1.5 °C；厚度 3 个尖峰；冷冻水压力 40–50% 冻结 |
| `campaign/` | 2026-10-17 起 22 次执行，每次一个 DAQ 导出 | DOE（CCD） | 3 因子面心 CCD α=1，8 角点 + 6 轴向 + 6 中心 + 2 重复；厚度/雾度/拉伸/在线测厚/剖面边缘 5 响应 |

抓数按平台真实格式组织：每个执行一个 `manifest.json` + `nodes/<node>.csv`
（`ts_iso,ts_ms,value,state`），另有 `trial_design.csv`、`qc_measurements.csv`、
`hetero/profiles.csv`、`hetero/notes.csv`、`mapping.json`。生成器
`generate_capture.py` 是 seeded 的，`scenario_truth.json` 记录植入曲面、驻点、异常时刻。

### 2.2 植入曲面（编码尺度）

```
thickness = 50 + 1.20 z_t − 0.90 z_m − 0.35 z_r − 1.10 z_t² − 0.80 z_m²
                − 0.30 z_r² + 0.50 z_t z_m
haze      = 2.0 + 0.16 z_t − 0.11 z_m + 0.04 z_r + 0.07 z_t²
tensile   = 185 + 6 z_t − 4 z_m + 2 z_r − 3 z_t²
```

试验开始时的配方（`current_setpoint`）是角点 (196 °C, 330 m/min, 3.1)，实测厚度
44.79 µm（低于 LSL 48）——这是一次“为救厚度而做”的 DOE，而不是“在中心点附近微调”。

---

## 3. 实测结果

### 3.1 DOE：设计识别、效应、驻点、可执行点

| 项 | 真值 | 分析结果 | 判定 |
|---|---|---|---|
| 设计类型 | rsm_ccd, α=1 | `rsm_ccd`，中心 6、轴向 6、mode=designed | ✅ |
| 温度主效应 | +1.20 | **+1.2511**（CI 1.104–1.398，q=1.4e-7） | ✅ |
| 车速主效应 | −0.90 | **−0.9375**（CI −1.077–−0.798，q=5.4e-7） | ✅ |
| 拉伸比主效应 | −0.35 | **−0.3597**（CI −0.502–−0.218，q=6.3e-4） | ✅ |
| 温度² | −1.10 | −1.3089（q=1.3e-5） | ✅ 同号同量级 |
| 车速² | −0.80 | −0.7494（q=9.5e-4） | ✅ |
| 温度×车速 | +0.50 | +0.4606（q=4.4e-4） | ✅ |
| R² / adj R² / Q² | — | 0.9928 / 0.9832 / 0.9319 | ✅ |
| 失拟 | 无 | p=1.0（pure-error df=7） | ✅ |
| 厚度驻点（编码） | (0.450, −0.422) | **(0.390, −0.472)**，域内，max | ✅ |
| 厚度驻点（原始） | 201.80 °C / 315.78 m/min / 3.0 | **201.56 °C / 315.28 m/min / 2.947** | ✅ |

联合推荐点（`joint_setpoints[0]`，网格 9³）：

| 因子 | 当前配方 | 推荐 | 硬限 |
|---|---:|---:|---|
| TDO Z4 温度 | 196.0 °C | **200.0 °C** | 195–205 |
| MDO 车速 | 330.0 m/min | **317.5 m/min** | 300–340 |
| TDO 拉伸比 | 3.10 | **3.075** | 2.7–3.3 |

预测（v1.1 四类区间分离）：厚度 **49.96**（均值 CI 49.72–50.21，PI95 49.45–50.48，d=0.982）；
雾度 **2.064**（PI 1.91–2.22，≤ USL 2.2）；拉伸 **188.7**（PI 184.3–193.0，≥ LSL 170）；
D=0.861；可行、硬约束违例 0；`actionable=true`。

`optimization_guidance.recipe_patch` 三条全部 `platform_ref` 完整、`within_limits=true`、
`actionable=true`；`from` 正确取当前配方（196/330/3.1），不是设计中心。

**有用性判断（对照实测）**：当前配方角点实测厚度 44.79 µm（不合格）；推荐点预测 49.96 µm
（PI 下限 49.45，仍在 48–52 内），同时雾度 2.06 < 2.2、拉伸 188.7 > 170。也就是说，这份分析
不仅指出了“温度升、车速降”的方向，还给出了**可直接落 recipe 的三参数联合值**与不确定区间。
这是“支撑调参优化”而不是“描述相关性”。

其他产物：

- `association_screen.json`：35 对设计校正/边际关联，`causal_claim=none`，
  `window_emission=forbidden`——相关不进入任何窗口。
- `ontology_consistency.json`：15 项检查、13 匹配、2 条 advisory 矛盾
  （`tdo_ratio → haze/tensile` 先验写成负向，实测为正）；只作提示，不改统计结论。
- `next_design.json`：`recommended_action=none`（设计无失拟、无别名、随机化充分，现有设计
  足够）；这是规则化结论，不是“没有下一轮能力”；有确认/补点触发时同文件会给出可执行 runs。
- 证据等级 **A**，gate **25/25**，artifact manifest **15 件、missing 0**。

### 3.2 异常：quick-screen

| 检测 | 结果 | 对真值 |
|---|---|---|
| C1 SPC（Nelson R1/R2/R3/R5/R6） | 199 个触发 | 厚度 3 个尖峰、漂移段均命中 |
| C2 漂移投影（用 DOE 操作窗） | Z4 当前 204.71 °C > 窗 [198, 203]；斜率 **0.896 °C/h**；`hours_to_edge=0`；critical | 植入 0.9 °C/h ✅ |
| C3 变点 | 7 个新变点 | 60% 处张力/环境台阶 ✅ |
| C4 稳健 z / 马氏 | 110 个离群；冷冻水压力冻结段 144 点被标记 | 冻结段位置一致 |
| 下一步建议 | 投影告警 `suggested_next_skill=industrial-doe-analyzer` | 异常 → DOE 的正确路由 |

224 条原始告警（同 key 合并后 59 个事件）通过 6/6 门禁；对 6 小时窗口，这个量级合理，
报告用 `checks_summary`/`projection_summary` 给出可读摘要，而不是让用户翻 224 条。

### 3.3 波动：stability report

- 综合评分 **53.9 / C 级（波动）**，8 个参数，20 条发现（16 high / 1 warn / 3 info）。
- 关键发现：`tdo_z4_temp` 显著漂移（Theil-Sen p<0.01，相对漂移 10.6%/天）、
  `thickness_gauge` 显著漂移并偏离历史基线（robust z −7.54）、
  `tdo_z4_temp` 偏离基线（robust z +15.07）、`ambient_temp`/`line_tension` 台阶。
- 协同：sentinel 基线（用于基线偏离）、**DOE 3 条推荐操作窗**（`window_role=marginal_diagnostic`）
  与 `joint_setpoints` 已载入；本体模式 `ontology`（显式路径）。
- HTML 325 KB、HTML 自检 pass、门禁 **11/11**。
- 诚实性：时段**中位**仍落在 Z4 操作窗内，因此没有伪报“中位超窗”；漂移由 drift 发现与
  sentinel 的当前值投影分别表达，两者不冲突。

### 3.4 异构：E-1H

- 输入：22 个 63 点横向剖面 + 22 条操作备注（交接班/边缘波动）。
- 输出：2 个源、20 列特征契约、22 行特征；`annotations.json` 22 条事件。
- 剖面均值 vs 植入厚度：**r=0.999997**；剖面边缘特征 vs 植入边缘信号：**r=0.976**。
- 选 5 列（MEAN/STD/EDGE-L/EDGE-R/CURV）按 `run_id` join 进 DOE；`edge_dev` 作为附加响应
  进入联合 desirability（d=0.492），不改变主效应结论。

### 3.5 本体

- 第一次 `doe_ontology_prepare`：`built`（v1，context_fp `5145e…`）；第二次：**`reused`**。
- brief 覆盖：因子 3/3、响应 5/5、未匹配 0，coverage ratio 1.0；data_stage=collected。
- confounders 去重后每条变量只出现一次（ambient_temp）。
- 15 条关系参与一致性校验；2 条 advisory 矛盾按设计只提示、不阻断，并写回
  `ontology_consistency.json` 供下一轮本体修订。

### 3.6 检索

`results_index.json` 12 条（DOE 7 + 异常 1 + 波动 2 + 异构 1 + HTML 2 类合并计数），
7/7 查询命中：

| 查询 | 命中 |
|---|---|
| 厚度 | effect_table、recommendations |
| 漂移 | sentinel alert、stability report |
| 联合设定点 | recommendations、optimization_guidance |
| 剖面 | E-1H column_contract |
| 稳定性评分 | stability report |
| 下一轮 | next_design |
| 本体 | ontology_brief、ontology_consistency |

后端 `buildArtifactManifest` 对同一 run 读出 `source=analyzer`、15 件、sha256 完整；
tasks API 与 external API 共用这一份 manifest（`artifact-manifest.service.mjs`）。
离线检索工具：`python docs/plans/demo/aws-capture-doe/query_results.py <关键词>`
（索引里的路径指向 `evidence/`，克隆后无需重跑分析即可检索）。

### 3.7 场景 → skill 路由

`routing_check.mjs`：IDD **20/20**。
- 六意图 resolve 正确；未知意图返回 null（400），不静默降级。
- 五个非默认意图的 directive 都绑定正确 skill；quick-screen 额外带 HTML 步骤。
- DOE directive 的硬门顺序 `prepare → brief → plan` 正确；design_only 拒绝统计。
- AgentWorkShop intent 目录与 IDD **5/5** 对齐；`defaultQuestionFor('doe-analysis')` 是 DOE 模板。
- **平台 P0（披露，不计入 IDD 失败）**：`diag_run` 在 `question` 缺省时先写“深度根因诊断”，
  顶掉了 `defaultQuestionFor(intent)`；IDD 的 intent directive 仍会绑定 DOE skill，但业务问题文本
  是错的。修法见 `references/platform-integration.md` §6。

---

## 4. 结果是否“真正有用” — 判定

| 判据 | 结果 |
|---|---|
| 能否从平台抓数直接得到分析？ | ✅ 一条命令装配 run table；无需人工拼表 |
| 能否恢复已知物理关系？ | ✅ 三个主效应误差 ≤ 5%，二次项/交互同号同量级，驻点误差 ≤ 0.06 编码单位 |
| 推荐是否可执行？ | ✅ 联合点 + `platform_ref` + 硬限检查 + recipe patch；当前配方 44.79 µm → 预测 49.96 µm |
| 是否给出不确定性与边界？ | ✅ 四类区间分离；PI95 宽度正确；可行域/失效条件/影响点（Cook's D）披露 |
| 异常/波动是否有证据链？ | ✅ 漂移斜率 0.896 vs 0.9；稳定性评分 53.9/C；SPC/变点/基线偏离逐项证据 |
| 结果能否被下游检索？ | ✅ manifest 15 件 + 12 条索引 + 7/7 查询；后端 manifest 可读 |
| 多源异构是否真的参与分析？ | ✅ 剖面特征进入联合 desirability；备注被事件化，不伪造数值 |

**结论：对“调参优化支撑依据”这个问题，答案是肯定的。** 这份 DOE 不只是“哪些因子显著”，
而是“从当前不合格配方 196/330/3.1 改到 200/317.5/3.075，厚度 49.96（PI 49.45–50.48），
雾度 2.06，拉伸 188.7，D=0.861，三条 patch 均在硬限内”。这就是可执行的调参依据。

### 4.1 一个必须说清的限制

本报告验证的是**确定性分析内核 + 真实数据契约 + 真实路由**；三类任务的 agent 编排是在
directive/合同层验证的，没有在本次试验里再跑一遍 1.5–2 小时的完整 LLM harness 任务。
LLM 只负责读 brief/写 plan/解释，数值全部由脚本产生；因此这一层的确定性证据是充分的，
但“agent 在真实长任务中不偏离协议”仍由 IDD 既有 E2E 与上一轮 BOPET demo 覆盖。

---

## 5. 测试矩阵（全部实跑）

| 套件 | 结果 |
|---|---|
| `industrial-doe-analyzer/tests/run_tests.py all` | **199/199** |
| `test_ontology_phase1.py all` | **68/68** |
| `test_phase2_stats.py all` | **130/130** |
| `test_phase3_design.py all` | **82/82** |
| `test_gate_v11.mjs` | **44/44** |
| `test_aws_capture.py all`（新增） | **46/46** |
| `industrial-line-stability-report/tests/run_tests.py all` | **117/117** |
| `industrial-sentinel/tests/run_tests.py all` | **107/107** |
| `app/backend npm test`（含新增 artifact-manifest 7 条） | **146/146** |
| `docs/plans/demo/aws-capture-doe/run_demo.py --fresh` | **100/100** |
| `routing_check.mjs` | **20/20** |
| DOE gate / sentinel gate / stability gate（demo 内） | 25/25 · 6/6 · 11/11 |

合计 **1,059** 条断言，全绿。

---

## 6. 仍未闭合（平台侧）

| 优先级 | 缺口 | 影响 | 建议 |
|---|---|---|---|
| P0 | `diag_run` 缺省问题覆盖 intent 模板 | 业务问题文本错误；执行仍被 directive 绑定 | 只在 intent=deep-diagnosis 时填根因模板，否则用 `defaultQuestionFor` |
| P1 | 无 run-level 导出 / DOE 实体 | 平台不能原生组装试验表 | 增加 experiment/factor/response/run 表 + run-scoped export |
| P1 | `diag_status` 不拉 artifact manifest | 平台拿不到 `recommendations.json`/`next_design` | 幂等 outbox，键 `(run_id, kind, sha256)` |
| P1 | 无 DOE 结果页/台账 | 人不能在平台内复核 | 读 manifest 的 effect/joint/guidance 三张卡 |
| P2 | E-1H 不解析 ISO ms/Z | 原始 AWS 时间戳直接进 E-1H 会 0 源 | 归一化，或在 E-1H 时间目录加 `%Y-%m-%dT%H:%M:%S.%f` |

平台源码本轮未改动；上述 P0 有精确行号与修法，见 `references/platform-integration.md` §6。

---

## 7. 复现

```bash
# 全量（会重新生成 capture、DOE、sentinel、stability、E-1H、索引与证据）
python docs/plans/demo/aws-capture-doe/run_demo.py --fresh

# 单独检查
python .claude/skills/industrial-doe-analyzer/tests/test_aws_capture.py all
node docs/plans/demo/aws-capture-doe/routing_check.mjs
node .claude/skills/industrial-doe-analyzer/scripts/quality_gate.mjs \
  workspace/aws-capture-e2e/doe --skill-path .claude/skills/industrial-doe-analyzer \
  --shared-path .claude/shared
```

证据：`docs/plans/demo/aws-capture-doe/evidence/`（DOE/stability HTML、manifest、
recommendations/guidance/next design、sentinel alert、结果索引、路由 JSON、汇总）。

> 真值文件 `scenario_truth.json` 只用于验收，不得提供给诊断 agent。
