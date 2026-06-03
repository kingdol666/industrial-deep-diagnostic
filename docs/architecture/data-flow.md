# Data Flow

## 诊断主数据流

```text
input data
  -> inspect
  -> ontology/context build
  -> data processing + figures
  -> VLM visual evidence
  -> diagnosis
  -> judge
  -> report
  -> audit
  -> final artifact checks
```

## 关键运行产物

- `00_input/`：输入清单、运行配置、上下文
- `01_ontology/`：本体与语义结构
- `02_processed/`：数据分析与中间结论
- `03_figures/`：图像与视觉证据
- `04_diagnostics/`：诊断工件
- `05_review/`：审查结果
- `06_scripts/`：场景特化脚本

## 关键证明链

- `.pipeline_events.jsonl`：执行证明
- `run_manifest.json`：运行状态快照
- `evidence_closure_report.json`：证据闭环证明
