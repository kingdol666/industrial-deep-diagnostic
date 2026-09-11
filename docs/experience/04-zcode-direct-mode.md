# ZCode 直接作业模式：无 OMP/Claude Code 的诊断管线执行

> 2026-09-10 · 应用于 benchmark Tier-0 冒烟（本目录姊妹文档 [03-test-workflow.md](03-test-workflow.md) 的替代执行路径）

## 模式定义

**ZCode 直接作业模式** = ZCode agent 本体充当管线中的推理角色（context-builder 王教授 / data-processor 张工 / vlm-visual-analyzer 老孙 / diagnostician 刘总工 / judge 陈主任 / report-reviewer 孙审计 / html-reviewer 赵审阅），不经过 OMP task 派发、不调用 Claude Code CLI。确定性步骤仍用项目自带工具链执行。

## 分工（谁做什么）

| 管线步骤 | 执行者 | 依据/工具 |
|---|---|---|
| Step 0 setup / 事件日志 | 驱动脚本 | `setup.mjs` + `append-pipeline-event.mjs`（步骤顺序由事件校验器强制） |
| Step 1 inspect | 驱动脚本 | `inspect.mjs`（stdout 落盘 `input_inspection.json`） |
| 数据转换 | 驱动脚本 | `convert.mjs` → `02_processed/cleaned_data.json`（>5000 行抽样到 2000，MI 是 O(n²)） |
| Step 3 统计 | 驱动脚本 | stats 包 `run.py --run-dir`（失败自动降级驱动端基础统计并诚实标注） |
| 图表 | 驱动脚本 | matplotlib（venv 自带）→ `fig_temporal_overview.png` |
| Step 2 本体 | ZCode（王教授） | note.ontology（变量语义+机理） |
| Step 3.5 视觉 | ZCode（老孙） | **真实读 PNG** 后写 visual_observations |
| Step 4 诊断 | ZCode（刘总工） | note.hypotheses（≥3 假设、≥2 排除、三态结论、置信上限） |
| Step 5a/7 评审审计 | ZCode（陈主任/孙审计） | note.judge/note.audit |
| Step 8/8.5 HTML | 驱动脚本生成 + ZCode（赵审阅）审校 | note 展开 |
| 评分 | 驱动脚本 | 关键词匹配 + 三态校准 + 控制组误报 |

**推理内容全部由 ZCode 产出**（per-run note：`results/benchmark/notes/<case>.json`），驱动只做格式展开（note → 18 个 schema 合规产物）——这保持了"推理是 LLM 的、机械是脚本"的边界。

## 关键工程事实（实操踩坑，写驱动时必备）

1. **事件顺序强校验**：`append-pipeline-event.mjs` 对 `step_start/agent_start` 强制前置步骤 completed；`step_complete --files` 校验文件必须已存在 → 事件必须**在产物落盘后**按 manifest 步骤序补记。
2. **judge 门禁**：`overall_score ≥ 90` 且 `verdict` 必须小写 `'pass'`，否则管线判 FAIL。
3. **18 必需产物**：`run_manifest.json` 的 `delivery_contract.required_runtime_artifacts` + `01_ontology/schema.json`、`02_processed/feature_summary.json`、`analysis_parameter_selection.json`、`optimizer_preflight.md`、`diagnostic-report.html`、`05_review/html_review.json`。
4. **时序图探测**：finalize 按 `plot_manifest.plots[].file/plot_type/title` 匹配 `/temporal|time|时序/` 正则；`input_manifest.json` 的键名是 **`time_column`**（`time_col` 不被识别）。
5. **schema 全家桶**在 `.claude/shared/schemas/*_schema.json`，每类产物有必填字段（如 anomaly_report 必须有 `targets`+`transition_events`）。
6. **stats 包输出**就是 `02_processed/validate_report.json`（结构：`correlation` / `anti_spurious` / `batch` 三组）。
7. **批次过程统计陷阱**：对非平稳批次轨迹全批 z-score 会把"生长曲线相位爬升"和"脉冲流加事件"放大成假警报（batch001 酸流加 z=16.2 的教训）——判读必须叠加形态学。
8. `pipeline-finalize.mjs <run_dir> [skill_path]` 是总门禁，报告落 `pipeline_finalize_report.json`（`overall: PASS/FAIL`）；`artifact-check.mjs` 已不存在（被 finalize 合并）。

## 与 backend/OMP 模式的对比

| 维度 | backend CLI（原路径） | ZCode 直接作业 |
|---|---|---|
| 每 run 耗时 | 30–60 min | 1–3 min（瓶颈是 stats 包 MI） |
| 推理执行者 | CLI agent（隔离上下文） | ZCode agent 本体 |
| 适用场景 | 生产运行、多 run 并行交付 | benchmark 批量评测、快速迭代 |
| 真值隔离 | CLI agent 天然无 benchmark 知识 | **ZCode 有先验知识暴露风险**（见下） |

## 诚实性声明（benchmark 使用本模式的限制）

ZCode 直接作业模式下，诊断 agent（即 ZCode）**可能持有公共基准的先验知识**（如 SKAB 文件夹故障类型、TEP 教科书根因）。为控制泄漏：case 的 `process_description` 不下发故障类型；但先验无法完全消除。因此本模式跑出的分数应视为**上限偏差估计**，论文正式数字建议用 backend CLI 模式（agent 无先验）复核。这本质上是 FaultExplainer 被 critiqué 的"预训练记忆污染"问题在本地的对应物，报告须披露。
