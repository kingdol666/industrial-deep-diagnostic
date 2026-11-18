---
name: industrial-hetero-preprocessor
description: "Heterogeneous multi-dimensional data preprocessing (pipeline stage E-1H, runs immediately AFTER industrial-data-preprocessor's E-1 in the same Step-0.5 chained command). Turns NON-scalar industrial data into deterministic scalar features anchored to the canonical time axis: profile/vector-over-time scans (时间×位置 film-thickness TD profiles, long or wide layout), regular-grid 2D field/map snapshots (x,y,value), image streams over time (WAXS/SAXS diffraction, CCD inspection, thermal — image files + timestamp→filename index CSV), and time-anchored free-text annotations (operator remarks, handover notes, lab comments). numpy/pandas/Pillow only, zero LLM/network by default; every derived column carries formula + physics_basis + evidence_level + n_inputs + source_sha256 provenance, named HX-<SHAPE>-<SRC>-<FEATURE> (ASCII); never interpolates, never forward-fills, never invents rows; writes ONLY 07_hetero/** plus one always-marker manifest (status ok|no_hetero_sources|off) so 'stage skipped' can never masquerade as 'stage ran'. Consumers read 07_hetero/column_contract.json + explicit_cols.json — the ontology builder copies semantics verbatim (physical_meaning_confidence is KNOWN/INFERRED, never UNKNOWN), the stats layer gets explicit --target-cols/--predictor-cols/--exclude-cols. Trigger: profile data, vector over time, 剖面数据, 膜厚剖面, 时间×位置, 横向剖面, TD profile, 扫描数据, map data, 2D field, 二维场, 温度场, 浓度场, 网格数据, 空间分布, image sequence, image time series, 图像序列, 图片索引, 图像数据, 衍射图像, WAXS, SAXS, CCD 检测, 热成像, 快照特征, snapshot features, 时间锚定文本, 操作备注, 交接班记录, 现场记录, 批注, 异构数据, 多源异构, 多模态数据, multimodal industrial data. Do NOT use for format adaptation / encoding / multi-sheet Excel / directory normalization into the canonical table (use industrial-data-preprocessor); do NOT use for statistics, cleaning, correlation, CCF or charts other than the profile heatmap (use industrial-data-processor); do NOT use for designed-experiment / ANOVA / operating-window analysis (use industrial-doe-analyzer); do NOT use to build HTML reports or dashboards (use industrial-html-visualizer); do NOT use for root-cause diagnosis or pipeline orchestration (use industrial-analysis-auto / industrial-diagnostician)."
---

# Industrial Hetero Preprocessor（E-1H · 多源异构数据前处理）

把"剖面/2D 场/图像序列/时序文本"四类**非标量**工业数据，投影成锚定在主时间轴上的**确定性标量特征**，
让既有九步管线与哨兵/产线报告在**不改默认逻辑**的前提下读懂它们。

## 何时运行（管线位次）

Step 0.5 的**同一条链式命令**内，E-1 之后立刻执行（两者一体，杜绝"跳过 E-1H"）：

```bash
uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/../../industrial-data-preprocessor/scripts/data_preprocessor.py" \
    --data-path <用户数据文件夹> --output "$RUN_DIR/00_input" --name <scene> \
&& uv run --project "$SHARED_PATH/scripts" python "$SKILL_PATH/scripts/build.py" \
    --raw-path <用户数据文件夹> --run-dir "$RUN_DIR" \
&& node "$SKILL_PATH/scripts/quality_gate.mjs" --run-dir "$RUN_DIR" --raw-path <用户数据文件夹>
```

**状态为 `status: ok` 时**（且仅此时），`DATA_PATH` 指向 `07_hetero/preprocessed_data_hetero.csv`，
并把 `hetero{enabled, anchor_path, manifest, anchor_sha256}` 写回 `run_config.json`；
其余情况（`no_hetero_sources` / `off` / gate 不过）**一律维持 `DATA_PATH = 00_input/preprocessed_data.csv`**，
管线行为与今天逐字节一致。

## CLI 与退出码

```bash
build.py --raw-path <file|dir> [--anchor 00_input/preprocessed_data.csv] [--run-dir RUN_DIR] \
         [--config 07_hetero/hetero_config.json] [--images-only] [--enable-vlm] [--enable-llm] [--enable-pca]
# exit: 0 ok|no_hetero_sources | 1 hard error | 2 undetermined | 3 gate-fail | 4 raw_path_unresolved
```

## 输入形态与特征（全部确定性）

| 形态 | 输入布局 | 特征（节选） |
|---|---|---|
| PROF 剖面 | `时间,pos_01..pos_N` 宽表；`时间,位置,值` 长表；规则栅格 | MEAN/STD/P05/P50/P95/RANGE/IQR/MAD、SLOPE-LSQ-PER100、CURV-LSQ、ZONE-means、**EDGE-L/R-DEV、ARGDEV-NBR、DEV-POS\<i\>、SHIFT-EST** |
| MAP 场 | `时间,x,y,值`；覆盖率≥0.6 栅格 | MEAN/P95、HOTAREA-P90/COLDAREA-P10、CENTROID-X/Y、GRAD-P95、ASYM-LR |
| TXT 文本 | `时间,备注` CSV；散文 .md/.txt | `annotations.json`（event_ts/recorded_ts/tag_slug）+ 事件窗 0/1 列 + shift/hour 协变量 |
| IMG 图像流 | 图片文件 + 索引 CSV（或文件名内嵌时间） | M1 最小路径：整图质量向量（MEAN/STD/ENTROPY/SATFRAC/DARKFRAC/FOCUS）；M2 深路径：RADIAL-Pk/AZIM-Pk/参考帧差/DEFECT-*/SHIFT-X/Y（无标定禁 Q-*） |

宽表列名不符合 `pos_*` 时走回退判据：各列量级相近 **且相邻列时序相干**（median adjacent r ≥ 0.25）才认作剖面——防止把化验室多指标窄表误判成剖面（见 method_notes §2）。

对齐：`merge_asof(backward)` + 陈旧度上限（默认 3×节奏）+ 可选 `transport_lag_s`；**禁插值/禁外推/禁越界前向填充**；
时间解析用本 skill 自带格式清单（**不复用 E-1 的 `_normalize_cn_datetime`**——它丢时分秒且解析率仍显示 1.0，见 method_notes R4）。

## 输出（只写 `07_hetero/**`）

| 文件 | 内容 |
|---|---|
| `hetero_manifest.json` | **always-marker**：status/逐源处置 reason/time_ingest/对齐策略/h7_guard。无源/关闭也必写（区分"没跑"与"跑了没源"） |
| `column_contract.json` | 逐列 unit/role/**physical_meaning/formula/physics_basis/evidence_level**/n_inputs/coverage/stats_eligible/source_sha256 |
| `explicit_cols.json` | `{targets,predictors,excludes}` —— 统计层显式列清单（`stats_eligible` 判据：anchor 覆盖 ≥0.5） |
| `features/<SHAPE>-<SRC>.csv` | 原生节奏一行一快照：`ts,_src_ts,n_inputs[,原位矩阵…],<派生列>`（PROF 保留 pos 矩阵供热图） |
| `annotations.json` | 时间锚定文本事件 |
| `preprocessed_data_hetero.csv` | 仅 ok 时：anchor + **表尾**追加 HX 列（行数/行序不变） |

## 消费方式（数据工件接线，不做代码 import）

- **ontology-builder**：Phase 1 读 `column_contract.json`（或调用 `heterocore.contracts.to_ontology_signals`）逐列照抄语义，
  `auto_inferred:true`、`physical_meaning_confidence ∈ {KNOWN, INFERRED}` —— **禁止留 UNKNOWN**（UNKNOWN 会让诊断置信度封顶 50）。
- **data-processor**：Phase 0 读 `explicit_cols.json`；只把 `stats_eligible=true` 的 HX 列传入 `--target-cols/--predictor-cols`，
  其余进 `--exclude-cols`；稀疏列的分析表面 = `features/*.csv` + 时间×位置热图 + VLM。
- **sentinel**：显式 `--data 07_hetero/preprocessed_data_hetero.csv --time-col … --parameters … --config … --out-dir …`
  （不要依赖 `data_path.parent` 的默认发现）；`HX-*` **不进**基线与 `fault_signature`。
- **线体稳定性报告**：目录模式含 `07_hetero/` 时主表选择必须不变（smoke 断言）；M3 起异构源登记 auxiliary。

## 事件日志（管线执行证明）

```bash
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_start --agent main-agent --step hetero_preprocess
# …链式命令…
node "$SHARED_PATH/scripts/append-pipeline-event.mjs" "$RUN_DIR" \
  --event step_complete --agent main-agent --step hetero_preprocess \
  --files 07_hetero/hetero_manifest.json,07_hetero/column_contract.json,07_hetero/explicit_cols.json
```

## 门禁与验证

```bash
node "$SKILL_PATH/scripts/quality_gate.mjs" --run-dir "$RUN_DIR" --raw-path <raw>
# exit 0 ok | 1 hard error | 2 undetermined(无 marker) | 3 gate-fail   （H1–H8，见 method_notes）
uv run --project .claude/shared/scripts python "$SKILL_PATH/tests/run_tests.py"   # 全部夹具与断言
```

完整协议（Phase 0-N 检查单）见 `references/agent-protocol.md`；公式与口径见 `references/method_notes.md`。
