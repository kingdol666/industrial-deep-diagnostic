# 性能与成本指南

## 1. 运行时间估算

| 数据规模 | 预计时间 | 主要耗时环节 |
|:---------|:---------|:-------------|
| <1 万行，<20 列 | 5-10 分钟 | context-builder、data-processor 统计分析 |
| 1-10 万行，20-50 列 | 10-20 分钟 | 统计验证、VLM 图像分析、竞争假说诊断 |
| 10-100 万行，50+ 列 | 20-40 分钟 | 大规模统计计算、多图生成、HTML 渲染 |
| >100 万行 | 可能 >40 分钟 | 需要采样或分块处理 |

> 以上为典型估算，实际时间受网络、模型响应、修复循环次数影响。

## 2. Token 成本影响因素

| 因素 | 影响 |
|------|------|
| Agent 数量 | 9 个子 Agent 各需读取长协议 |
| 修复循环 | 每次修复重新调用 diagnostician / judge / reporter |
| 数据行数 | 大表格直接传入 prompt 会显著增加 token |
| 图表数量 | VLM 读图消耗额外 token |
| HTML 生成 | Three.js / ECharts 代码量大 |

## 3. 降低成本的建议

1. **使用 auto 模式**：减少交互轮次
2. **避免不必要修复**：确保输入数据质量良好
3. **前置 opt-out HTML**：如不需要 HTML，提前声明
4. **限制参考文档大小**：REFERENCE_DIR 中只放最相关的文档
5. **合理采样**：超大文件使用 `--sample` 参数

## 4. 性能优化方向

| 优化点 | 说明 |
|--------|------|
| 并行化 | 目前仅 Step 5a/5b 并行，未来可考虑更多独立检查并行 |
| 协议精简 | 部分 Agent 协议较长，可提取核心摘要 |
| 缓存本体 | 同类型产线可复用 ontology 模板 |
| 增量分析 | 仅对新数据或变更列重新分析 |

## 5. 资源监控建议

在 `run_summary.json` 中建议增加以下字段（未来版本）：

```json
{
  "performance_profile": {
    "total_duration_seconds": 1200,
    "agent_durations": {
      "context-builder": 180,
      "data-processor": 360,
      "diagnostician": 240
    },
    "repair_loop_count": 1,
    "html_render_duration": 120
  }
}
```

## 6. 故障性能权衡

本 skill  prioritizes 诊断准确性而非速度。以下设计会牺牲性能换取可靠性：

- 多 Agent 串行 + 审计
- Schema 验证 + Checkpoint 门
- 修复循环 + 反振荡
- 物理机制定量验证

对于需要亚分钟响应的场景，不建议使用本 skill。
