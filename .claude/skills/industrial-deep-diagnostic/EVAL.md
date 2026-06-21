# Eval 运行与扩展说明

## 1. Eval 文件位置

| 文件 | 用途 |
|------|------|
| `evals/evals.json` | 正式 eval 场景定义 |
| `test-prompts.json` | 快速测试提示词 |
| `results.tsv` | eval 运行结果记录 |

## 2. 当前 Eval 覆盖

`evals/evals.json` 包含 5 个工业场景：

1. CNC 主轴轴承剥落
2. BOPET 薄膜厚度异常
3. 化学反应釜温度失控
4. 换热器结垢
5. 轧钢厚度波动

每个场景验证：根因识别、过渡事件分析、混淆因素排除、统计验证完整性、置信度合理性。

## 3. 运行 Eval

```bash
# 使用 eval-assertions.mjs 验证单次运行产物
node scripts/eval-assertions.mjs <RUN_DIR> <eval_id>

# 示例：验证 CNC 场景
node scripts/eval-assertions.mjs workspace/diagnostic-runs/<run> 1
```

## 4. 新增 Eval 场景

### 4.1 在 evals.json 中添加

```json
{
  "id": 6,
  "name": "new_scenario",
  "prompt": "...",
  "expected_output": "...",
  "files": ["data/eval_new/data.csv"],
  "metadata": {
    "scenario_type": "...",
    "expected_diagnosis_type": "DETERMINED",
    "expected_confidence_floor": 80
  },
  "assertions": [
    {
      "name": "...",
      "jsonpath": "$.diagnosis.root_cause[*].name",
      "expected_type": "contains_any",
      "expected_values": ["..."],
      "weight": "critical"
    }
  ]
}
```

### 4.2 在 test-prompts.json 中添加

```json
{
  "id": 6,
  "prompt": "...",
  "expected": "...",
  "category": "anti_speculation"
}
```

### 4.3 准备测试数据

将数据文件放入 `data/eval_new/data.csv`。

### 4.4 运行并记录

运行后更新 `results.tsv`：

```tsv
timestamp	commit	skill	old_score	new_score	status	dimension	note	eval_mode
2026-06-21T10:00	<commit>	industrial-deep-diagnostic	<old>	<new>	keep	<dimension>	<note>	full_test
```

## 5. 推荐补充的 Eval 类型

| 类型 | 目的 |
|------|------|
| `COMPETING_SET` 场景 | 验证数据无法区分时诚实输出竞争集 |
| `NEEDS_DATA` 场景 | 验证证据不足时拒绝下结论 |
| RAG 不可用场景 | 验证 RAG 降级后仍完成诊断 |
| HTML 失败降级场景 | 验证 HTML 生成失败时正确交付 report.md |
| 大文件采样场景 | 验证 >500MB 数据采样分析正确性 |
| Batch 完整性场景 | 验证重复 batch_id 检测机制 |

## 6. Eval 断言类型

| 类型 | 说明 |
|------|------|
| `contains` | 字段包含指定值 |
| `contains_any` | 字段包含任一指定值 |
| `equals` | 字段等于指定值 |
| `greater_than` | 数值大于指定值 |
| `exists` | 字段存在 |

## 7. 权重定义

| 权重 | 说明 |
|------|------|
| `critical` | 不通过则整个 eval 失败 |
| `high` | 显著影响评分 |
| `medium` | 中等影响 |
| `low` | 轻微影响 |
