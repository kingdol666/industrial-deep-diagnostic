# DOE 端到端演示 · BOPET 12 µm TDO/MDO 工况试验

这一目录不是测试夹具，而是**一次真实跑完的 DOE 分析**：从模拟的真实试验数据出发，
走完整条 flow（数据入口 → 本体 → 分析 → 统计 → 结论 → 渲染），产物全部留在目录里，
可以直接打开看、也可以一键重跑。

- **给人看**：`report.html`（交互式报告，19 张图 + §11 本体依据与下一轮设计）
- **给 Agent 看**：`conclusions/recommendations.json`（v1.1 合同）、`conclusions/next_design.json`、
  `conclusions/optimization_guidance.json`、`02_analysis/effect_table.json`、
  `02_analysis/association_screen.json`、`artifact_manifest.json`
- **真值**：`scenario_truth.json`（分析前就写好的植入真值，不是分析结果的转录）

## 1. 场景

产线反馈 12 µm 膜厚波动偏大、雾度偶发超上限，于是做了一轮工况试验：

| 项 | 内容 |
|---|---|
| 因子 | `tdo_z4_temp` 196–204 °C · `mdo_speed` 310–330 m/min · `tdo_ratio` 2.90–3.10 |
| 响应 | `thickness_um` 目标 50、规格 48–52；`haze_pct` 越小越好、上限 1.8 |
| 设计 | **面心 CCD（α = 1）**，8 角点 + 6 轴向点 + 6 次中心点执行 |
| 重复 | dp-02 / dp-07 各多做 1 次独立重复（纯误差） |
| 区组 | 3 个生产班次 B1/B2/B3 |
| 执行 | 22 次，顺序随机化后分班 |
| 异常 | `doerun-006` 测厚仪读数丢失，留空未插补 |

**为什么是面心而不是可旋转 CCD**：安全窗口有硬限（TDO Z4 195–205 °C），
可旋转 CCD（α = 1.682）会把轴向点放到窗口外，实际工艺不会这么干。这一点也写在
`00_input/experiment_notes.md` 的试验记录里，供本体阶段当先验知识读。

数据里还故意埋了两个"看着像因子、其实不是"的列：

- `chiller_pressure`：几乎是 `tdo_z4_temp` 的线性函数（仪表随温度联动）→ 相关分析会"发现"它；
- `shift_handover_min`：交接班时长，纯噪声；
- `ambient_temp`：车间温度，**声明为协变量**，真实效应为 0。

三者都不得进入任何窗口、推荐点或配方补丁。

## 2. 怎么重跑

```bash
cd <repo>
A="uv run --project .claude/shared/scripts python"

# 重新生成数据（确定性，改不动就是没变更）
$A docs/plans/demo/doe-bopet/generate_scenario.py

# 跑完整 flow + 60 条断言（--fresh 清掉本地本体 store，走完整先验构建）
$A docs/plans/demo/doe-bopet/run_demo.py --fresh
```

`run_demo.py` 逐步执行并断言：

```
1 doh_context_adapter      doe_context + run_table -> analysis_context（col 合同）
2 doe_ontology_prepare     context_fp -> store 查询 -> reuse/extend/build
3 （Agent 步骤）            读 ontology_brief.md，写 01_profile/analysis_plan.md
4 analyze.py all           profile -> 统计 -> report.html
5 quality_gate.mjs         G1–G11
6 断言                     设计识别 / 植入效应 / 驻点 / 可执行联合推荐点 /
                          相关筛查纪律 / 下一轮布点 / 平台 handoff / 工件清单 / 报告章节
```

`--fresh` 与不带 `--fresh` 的区别只在本体阶段：不带时命中 store 走 `reused`
（快路径，无 RAG/web）。

## 3. 这次跑出来的结果

- 设计识别：`rsm_ccd`，6 个中心点、6 个轴向点，模式 `designed`
- 证据等级 **A**（纯误差 df=7、失拟检验 p=1.0、MDE 可见）
- 效应恢复（编码系数，与植入值对照）：

| 项 | 估计 | 植入 |
|---|---|---|
| `tdo_z4_temp` | +1.218 | +1.30 |
| `tdo_z4_temp^2` | −1.095 | −1.10 |
| `mdo_speed` | −0.973 | −0.95 |
| `tdo_z4_temp:mdo_speed` | +0.845 | +0.60 |
| `mdo_speed^2` | −0.787 | −0.85 |
| `tdo_ratio` | −0.456 | −0.35 |
| `tdo_ratio^2` | −0.490 | −0.45 |

- 驻点（编码）：`tdo_z4_temp` +0.41、`mdo_speed` −0.45、`tdo_ratio` −0.57，
  全部落在设计域内
- **可执行推荐点**：`tdo_z4_temp 201.0 °C / mdo_speed 322.5 m/min / tdo_ratio 2.925`，
  预测厚度 50.00 µm（规格内）、雾度 1.57 %（≤1.8），硬约束 0 违例，`actionable=true`
- 配方补丁：三项均有 `platform_ref`（`TDO_Z4_SP` / `MDO_SPEED_SP` / `TDO_RATIO_SP`），
  `within_limits=true`
- 相关筛查：`chiller_pressure` → `held_constant`（与设计列共线）；
  `shift_handover_min` → `unmodeled`（调整后 p=0.29）；`ambient_temp` → `non_factor`
  （调整后 p=0.81）；**三者均未进入任何推荐**
- 一个诚实的细节：`ambient_temp` 在效应表的 extra-SS 检验里 p=0.026（q=0.035）——
  这是一个 α=0.05 下的偶然显著（该列边际相关 r=0.016）。它的标准化效应只有 0.14，
  而真实因子在 0.41–0.64，且没有进入任何窗口/推荐点/配方补丁。demo 因此断言的是
  **"噪声变量不得变成可执行建议"**，而不是"噪声变量必须不显著"——后者不是统计上成立的性质。

## 4. 目录

```
doe-bopet/
├── README.md                 本文件
├── generate_scenario.py      确定性场景生成器（数据 + 真值）
├── run_demo.py               端到端驱动 + 60 条断言
├── scenario_truth.json       植入真值（先于分析产生）
├── 00_input/
│   ├── doe_context.json      平台导出的因子/响应/规格/硬限/平台映射
│   ├── run_table.csv         一行 = 一次执行（22 行）
│   ├── experiment_notes.md   试验记录（本体阶段的先验知识来源）
│   └── analysis_context.json 适配器产物（解析后上下文，含 provenance.assigned_by）
├── 01_ontology/              ontology.json / ontology_brief.json(.md) / coverage
├── 01_profile/               data_profile.json / analysis_plan.md
├── 02_analysis/              effect_table / model / association_screen / consistency
├── 03_figures/               PNG 图 + plot_manifest.json
├── conclusions/              doe_conclusion / recommendations / next_design /
│                             optimization_guidance
├── artifact_manifest.json    工件清单（kind/path/sha256/schema_version）
└── report.html               人读交互报告（本目录可直接打开）
```

## 5. 与验收套件的关系

`run_demo.py` 是**端到端演示**，`tests/run_tests.py`（199 条）是**回归+夹具套件**。
两者互补：套件用固定小夹具守住行为不漂移，demo 用一份有区组、有协变量、有重复、
有缺失值、有共线列的"像真事"的数据走一遍全流程，并按植入真值核对结论。
demo 的断言口径与计划里的 DS-01/02/03/04/05/06/08/10/11、AR-01/02、RG-03 一致。
