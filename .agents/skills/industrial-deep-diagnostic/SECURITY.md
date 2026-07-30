# 安全与隐私说明

## 1. 数据敏感性

`industrial-deep-diagnostic` 处理的典型数据包括：

- 工业传感器时序数据
- 工艺参数（温度、压力、速度等）
- 质量检测数据
- 设备运行状态
- 可能包含产品批次、生产线编号等运营信息

这些数据通常属于企业生产数据，可能涉及商业机密或工艺保密信息。

## 2. 本地化处理原则

| 环节 | 处理方式 |
|------|---------|
| 数据文件 | 本地存储于 `workspace/diagnostic-runs/`，不自动上传 |
| Python venv | 本地创建 `scripts/.venv/`，依赖本地安装 |
| RAG 检索 | 默认连接本地 `localhost:8764`，不强制外网 |
| 网络搜索 | 仅在知识缺口明显且用户未禁止时执行，最多 5 次 |
| VLM 图像分析 | 本地 PNG 文件由本地 Python 脚本处理 |

## 3. 不建议提交的内容

请勿将以下文件提交到 git：

```gitignore
workspace/diagnostic-runs/
*.csv
*.xlsx
*.parquet
.env
credentials.json
knowledge_base/chroma_db/
```

> 实际 `.gitignore` 已包含 `workspace/diagnostic-runs/` 等目录。

## 4. 用户控制项

- 数据文件由用户主动上传
- RAG 引擎为可选依赖
- 网络搜索为可选行为
- HTML 可视化为默认行为，但可前置 opt-out

## 5. 审计与可追溯

所有执行步骤记录在 `.pipeline_events.jsonl` 中，便于审计：

- 哪个 Agent 执行了哪一步
- 输入/输出文件路径
- 修复循环历史
- 失败与恢复事件

## 6. 共享与分发

如需共享诊断结果：

- 优先共享脱敏后的 `report.md` 和 `diagnostic-report.html`
- 避免直接共享原始数据文件
- 共享产物前检查是否包含敏感设备编号或工艺参数
