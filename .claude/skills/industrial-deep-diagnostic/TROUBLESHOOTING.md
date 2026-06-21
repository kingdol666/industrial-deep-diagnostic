# 故障排查手册

本手册汇总 `industrial-deep-diagnostic` 运行中最常见的问题、检测方式和恢复动作。

---

## 1. 运行目录结构速查

```
workspace/diagnostic-runs/<timestamp>_<scene>/
├── 00_input/                 # 输入
├── 01_ontology/              # 本体
├── 02_processed/             # 分析产物
├── 03_figures/               # 图表
├── 04_diagnostics/           # 诊断
├── 05_review/                # 审校
├── .pipeline_events.jsonl    # 执行日志（最重要）
├── run_manifest.json         # 运行清单
├── report.md
├── optimizer.md
└── diagnostic-report.html
```

**排查任何问题，第一步都是查看 `.pipeline_events.jsonl`**：

```bash
node scripts/pipeline-log-check.mjs <RUN_DIR>
```

---

## 2. 通用检查清单

| 检查项 | 命令 |
|--------|------|
| 产物完整性 | `node scripts/artifact-check.mjs <RUN_DIR> <SKILL_PATH>` |
| 证据闭环 | `node scripts/evidence-closure-check.mjs <RUN_DIR> --write` |
| 执行日志 | `node scripts/pipeline-log-check.mjs <RUN_DIR>` |
| Judge 门 | `node scripts/judge-gate-check.mjs <RUN_DIR> --skip-summary` |
| 诊断质量 | `node scripts/diagnostic-quality-check.mjs <RUN_DIR>` |

---

## 3. 按问题分类

### 3.1 RAG 引擎不可用

**检测**：

```bash
curl -s http://localhost:8765/docs
```

**现象**：context-builder 报告 `RAG_UNAVAILABLE`。

**恢复**：
- Skill 自动降级到 `resources/parameter_to_physics.json` + 网络搜索。
- ontology.json 仍可完整构建，只是缺少特定产线的检索知识。

### 3.2 uv / Python venv 创建失败

**检测**：

```bash
which uv
node scripts/uv_env_setup.mjs
```

**恢复**：
- 若无 uv，安装：`curl -LsSf https://astral.sh/uv/install.sh | sh`
- 若 uv 已安装但失败，降级使用系统 Python：`pip install -r scripts/requirements.txt`
- 所有 Python 调用应使用 `scripts/.venv/bin/python`，禁止裸 `python3`

### 3.3 输入数据超大（>500MB）

**现象**：`inspect.mjs` 超时 >300s 或内存不足。

**恢复**：

```bash
python scripts/file_inspect.py --sample 50000 <data_path>
```

- 只读取前 5 万行 + 均匀采样 5 万行
- 内存不足时加 `--low-memory`

### 3.4 Agent 超时（stall >600s）

**恢复**：
1. 检查产物文件是否部分生成
2. 若有可用输出 → 继续下一步
3. 若无输出 → 等待 60s 后重试 1 次
4. 仍失败 → 标记 `[AGENT_TIMEOUT]` 并跳过该步骤

### 3.5 API 连接断开

**现象**：系统返回 `socket connection closed` 或 `API Error`。

**恢复**：
1. 等待 30s 后重启同一 Agent，传递相同 prompt
2. 连续 2 次失败 → 标记 `[API_ERROR]` 并降级到本地脚本执行

### 3.6 产物文件缺失

**检测**：每步完成后检查 expected outputs。

**恢复**：
- `ontology.json` 缺失 → 主 Agent 用 `resources/parameter_to_physics.json` 构建最小有效本体
- `diagnosis.json` 缺失 → 标记 `[DIAGNOSIS_FAILED]` 并写入失败报告

### 3.7 Schema 验证失败

**检测**：

```bash
node scripts/validate.mjs <schema> <file>
```

**恢复**：
1. 将 schema 错误追加到 Agent prompt，重新启动 1 次
2. 仍失败 → 标记 `[SCHEMA_FAIL]` 并记录到 `.pipeline_events.jsonl`

### 3.8 图片生成失败（PNG 缺失）

**恢复**：
1. 先按 Phase 2.2.5 + Phase 5.9 修复数据重画（string-type 重定型 / raw 回退）
2. 仍失败 → 生成 `image_captions.json` 作为文本回退
3. `visual_analysis.json` 标记 `observation_mode=metadata_backed_inference`

### 3.9 HTML 可视化失败

**检测**：

```bash
test -f <RUN_DIR>/diagnostic-report.html
```

**恢复**：
1. 运行 `diagnostic-html-visualizer` skill 重新生成
2. 连续 2 次失败 → 仅交付 `report.md`，在 `evidence_closure_report.json` 标注 `HTML_DELIVERY_FAILED`
3. **禁止主 Agent 自己拼 HTML**（红灯动作 #1）

### 3.10 Judge 评分 <90

**现象**：`judge_feedback.json` verdict 为 `needs_repair` / `major_issues` / `fail`。

**恢复**：
1. 读取 `repair_instructions`
2. 重新启动 diagnostician（最多 3 次）
3. Judge 重评
4. 若修复指令与上一轮重叠 >70% → 触发反振荡规则，第三次直接 halt

### 3.11 Report-Reviewer REJECTED

**恢复**：
1. 完整重跑 `diagnostician → judge → reporter → report-reviewer`
2. 最多 2 个周期
3. 全局修复计数 `diag_iters` ≤ 5

---

## 4. 深层兜底协议

任一恢复动作执行后若仍失败，必须执行：

1. 记录 `[RECOVERY_FAILED]` 事件到 `.pipeline_events.jsonl`
2. 将当前可用产物写入对应目录，标注 `_partial` 后缀
3. 向用户显式报告：哪个 Agent、哪个场景、一线修复是什么、为什么失败、已有哪些产出、缺失哪些产出
4. 用户决定「跳过该步骤继续」或「终止运行」

---

## 5. 调试技巧

### 5.1 快速定位最后执行到的步骤

```bash
tail -20 <RUN_DIR>/.pipeline_events.jsonl
```

### 5.2 查看 Judge 为什么不通过

```bash
cat <RUN_DIR>/05_review/judge_feedback.json | jq '.blocking_issues'
```

### 5.3 查看诊断置信度分解

```bash
cat <RUN_DIR>/04_diagnostics/confidence.json | jq '.confidence_assessments'
```

### 5.4 查看 HTML 审校结果

```bash
cat <RUN_DIR>/05_review/html_review.json | jq '.verdict, .blocking_issues'
```

---

## 6.  still stuck?

如果以上方法都不能解决问题：

1. 收集 `.pipeline_events.jsonl`、`run_manifest.json`、最近的 Agent 输出文件
2. 记录你尝试过的恢复动作
3. 提交 issue 时附上：数据规模、触发命令、错误现象、已尝试的修复
