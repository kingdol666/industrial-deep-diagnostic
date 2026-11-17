# Agent Protocol — industrial-hetero-preprocessor (E-1H)

> 主 agent 在管线 Step 0.5 内联执行本 skill（无独立 sub-agent）。Phase 0-N 为执行检查单；
> 一切数值由 `scripts/` 确定性计算，LLM/VLM 只解读且必须标记 `model_derived`。

## Phase 0 — 前置与守卫

- [ ] 0.1 确认 E-1 已在同一链式命令中运行（`00_input/preprocessed_data.csv` 存在），或本次为 `--images-only`。
- [ ] 0.2 解析 `--raw-path`（解析链：CLI → run_config.raw_data_path → input_manifest.raw_data_path →
      preprocessing_report.input_path）。解析失败 ⇒ **exit 4**，向用户报告"无法定位原始数据文件夹"，
      **禁止**当作 no_hetero_sources 静默继续。
- [ ] 0.3 读取 `07_hetero/hetero_config.json`（可选）：`enabled: off` ⇒ 写 `status: off` marker 并退出 0。

## Phase 1 — 发现与形态判定

- [ ] 1.1 `discover_sources`（默认只扫顶层；`--recursive` 才递归，且跳过 run 目录各阶段目录）。
- [ ] 1.2 形态模块按序探测（`image_stream > map > profile > text`），**一个文件只归属一个形态**。
- [ ] 1.3 无任何来源 ⇒ 写 `status: no_hetero_sources` marker（**只写这一个文件**）⇒ exit 0；
      管线维持 `DATA_PATH = 00_input/preprocessed_data.csv`。

## Phase 2 — 提取与对齐

- [ ] 2.1 逐源 `extract()`；失败源记 `disposition: skipped` + reason，**不得中断整体**。
- [ ] 2.2 时间解析只用 `heterocore/time_ingest.py` 的显式格式清单；`ambiguous_date_order` 的源**跳过**并记录；
      文件名时间与索引时间偏差 >1 快照 ⇒ `ts_conflict` 排除。
- [ ] 2.3 `align.anchor_join()`：`merge_asof(backward)` + `max_age = 3×cadence`（`ts_source=camera` 放宽 6×）；
      越界记 NaN；**禁插值/禁 ZOH 冒充**；joined 表行数/行序必须等于 anchor（H2）。
- [ ] 2.4 逐列落 `coverage/effective_n/sparse/stats_eligible`（判据：anchor 行非空覆盖 ≥0.5 ⇒ stats_eligible）。

## Phase 3 — 写盘（只写 07_hetero/**）

- [ ] 3.1 `features/<SHAPE>-<SLUG>.csv`（`ts,_src_ts,n_inputs[,原位矩阵],<派生列>`）；PROF 必须保留 pos 矩阵。
- [ ] 3.2 `column_contract.json` + `explicit_cols.json` + `annotations.json`（如有）。
- [ ] 3.3 `status: ok` 时写 `preprocessed_data_hetero.csv`（HX 列**只在表尾**）。
- [ ] 3.4 最后写 always-marker `hetero_manifest.json`（含 h7_guard.written 全清单）。

## Phase 4 — 门禁与管线回写

- [ ] 4.1 `quality_gate.mjs --run-dir $RUN_DIR --raw-path <raw>`；exit 3 ⇒ 修复后重跑，**不得**带病继续。
- [ ] 4.2 仅当 `status: ok` 且 `joined_table` 非空：
      - `run_config.json` 写 `hetero{enabled:"auto", anchor_path, manifest, anchor_sha256}` 且 `data_path` 指向 joined 表；
      - `input_manifest.json` 追加 `hetero` 溯源块；
      - `DATA_PATH` 后续步骤（inspect/fast-reuse/ontology/data-processor）一律用新路径。
- [ ] 4.3 记 `step_start/step_complete --step hetero_preprocess` 事件（--files 见 SKILL.md）。
- [ ] 4.4 有 PROF 特征时：data-processor 的 `adaptive_charts` 会产出时间×位置热图
      （`fig_hetero_profile_heatmap.png`，`vlm_priority` 必须显式设置）。

## Phase 5 — 消费者约定（写入下游 dispatch prompt 的一句话）

- ontology-builder：合并 `heterocore.contracts.to_ontology_signals(contract)` 的确定性映射，
  **禁止**对 HX 列重新推断或留 UNKNOWN。
- data-processor：Phase 1.2 方法计划必须包含 explicit_cols.targets（若非空）；
  `dropped_requested_columns`（core_stats 审计字段）非空时必须在结论里披露。
- sentinel / tuning-memory：`HX-*` 不进 baseline 与 `fault_signature.anomalous_params`。
