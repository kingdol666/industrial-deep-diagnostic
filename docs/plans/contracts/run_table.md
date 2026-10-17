# `00_input/run_table.csv` 契约（冻结）

- Date: 2026-10-17
- 归属：`docs/plans/contracts/README.md` §1
- 方向：**行 = 一次执行**（不是一次因子组合）。重复执行 → 新的 `run_id`。

## 1. 列定义

| 列 | 必填 | 类型 | 语义 | 备注 |
|---|---|---|---|---|
| `run_id` | ✅ | string，唯一 | 单次执行标识。建议 `doerun-<seq>` 或平台 `RecipeRun.id` | 缺列 → 拒绝 |
| `design_point_id` | 推荐 | string | 同一因子组合的分组键（重复点共享同一 id） | 缺失时由 adapter 按因子列元组生成 |
| `replicate_group` | 推荐 | string | **独立重复**分组（用于纯误差、区组内重复） | 与 `design_point_id` 不同：它标"独立重复"，`design_point_id` 标"同一点" |
| `replicate_kind` | 推荐 | enum `repeat`/`replicate`/`center` | 重复性质；`repeat`=同批次内重复测量（不算独立重复），`replicate`=独立重跑，`center`=中心点 | 缺失时按是否中心点推断 |
| `run_order` | 推荐 | integer | 执行顺序。用于随机化检验（Spearman ρ factor×order） | 缺失 → 无法判定非随机化 |
| `block` | 可选 | string/int | 区组（批次/天/机台） | 映射到 `analysis_context.blocks` |
| `<factor_1..k>` | ✅ ≥2 列 | number/string | 因子列。列名必须等于 `factors[].col` | 缺任一列 → 拒绝 |
| `<response_1..m>` | ✅ ≥1 列 | number | 响应列。**单元格允许为空**（未测/失败） | 空值计缺失并披露，不静默填 0 |

## 2. 合法性规则

1. **缺列拒绝**：`factors[].col` 或 `responses[].col` 指向的列不存在 → `adapter` 非零退出并报 `MISSING_COLUMN: <col>`。不静默丢弃。
2. **重复 `run_id`** → `DUPLICATE_RUN_ID`。
3. **因子列常量**（方差 0）：合法但降级为 `zero_variance`，该因子不可估计（不报错）。
4. **响应全空列**：合法，但进入 `data_stage=design_only` 路径（只允许 ontology/profile/build）。全空 → `RESPONSE_ALL_MISSING`。
5. **行数下限**：< 5 行或 < 2 列可用数值列 → 分析器拒绝（`INSUFFICIENT_DATA`，既有行为）。
6. **编码/分隔**：UTF-8（允许 BOM）；逗号分隔；首行表头。其他编码需在 `doe_context` 中显式声明——本期不支持，遇非 UTF-8 报错退出。

## 3. 目录约定

```
00_input/
├── run_table.csv            ← 唯一数据表（文件名由 doe_context.data_file 指定）
├── doe_context.json         ← 平台/用户输入
├── analysis_context.json    ← adapter 产物（解析后上下文）
└── exclusions/
    └── run_exclusions.csv   ← 被剔除的 run（不进数据发现候选集）
```

- 数据发现（`analyze.py:_find_data`）**不得**把 `doe_context.json` / `analysis_context.json` / `exclusions/**` / `*_manifest.json` / `README*` 当作数据表。
- `exclusions/` 必须是**子目录**，保证目录级 fallback 扫描不会命中。

## 4. 示例

见 `examples/run_table.csv`（设计阶段，响应空）与 `examples/run_table_collected.csv`（已收集，含重复/区组/空单元）。
