# Quick Start — 5 分钟上手

本文档帮助你在 5 分钟内理解如何运行 `industrial-deep-diagnostic` 并解读结果。

---

## 1. 前置要求

- Node.js 18+
- Python 3.9+（脚本会自动通过 `uv` 管理 venv）
- 可选：RAG 检索引擎运行在 `localhost:8765`（不可用时会降级到本地本体构建）

---

## 2. 触发 Skill

在 Claude Code 对话中输入：

```
/industrial-deep-diagnostic
```

然后上传你的数据文件（CSV/XLSX/Parquet），并描述问题：

> "这是我们 BOPET 薄膜划伤产线的传感器+检测数据（CSV，约 2000 行），最近划伤不良率上升，帮我诊断根因。"

---

## 3. 管线自动执行

Skill 会自动执行以下 9 步：

| Step | Agent | 关键动作 |
|:----:|-------|---------|
| 0 | 主 Agent | 创建运行目录、Python venv |
| 1 | 主 Agent | 流式检测数据格式 |
| 2 | 王教授 | RAG + 本体构建 |
| 2.5 | 主 Agent | 处理未知参数 |
| 3 | 张工 | 统计验证、异常检测、可视化 |
| 3.5 | 老孙 | VLM 图像分析 |
| 4 | 刘总工 | 竞争假说 + 物理推理 |
| 5a | 陈主任 | 10 项质量门审查 |
| 5b | 孙审计 | 预报告物理审计（并行） |
| 6 | 周工 | 生成 `report.md` |
| 7 | 孙审计 | 物理真相审计 |
| 8 | 林工 | 生成 `diagnostic-report.html` |
| 8.5 | 赵审阅 | HTML 可视化审校 |
| 9 | 主 Agent | 最终产物校验 |

---

## 4. 三种运行模式

| 模式 | 触发方式 | 用途 |
|------|---------|------|
| `auto` | 默认 | 零提问，自动推断所有参数 |
| `interactive` | 用户要求讨论 | 最多 4 个澄清问题 |
| `minimal` | 用户要求简单 | 只问 1-2 个关键问题 |

---

## 5. 输出在哪里

运行目录通常位于：

```
workspace/diagnostic-runs/<timestamp>_<scene>/
```

关键文件：

| 文件 | 内容 |
|------|------|
| `report.md` | 中文诊断报告，面向决策者 |
| `optimizer.md` | 优化建议、审计意见、下一步计划 |
| `diagnostic-report.html` | HTML 可视化讲解页 |
| `04_diagnostics/diagnosis.json` | 结构化诊断结论 |
| `04_diagnostics/reasoning_chain.json` | R1-R8 推理链 |
| `05_review/judge_feedback.json` | Judge 评分与修复意见 |

---

## 6. 如何阅读结果

1. **先看 `report.md` 执行摘要**：问题、根因、置信度、建议。
2. **再打开 `diagnostic-report.html`**：首屏应在 10 秒内显示结论、位置、动作。
3. **如果结论不确定**：查看 `COMPETING_SET` 表格和 `optimizer.md` 的下一步计划。
4. **如果要审计结论**：查看 `reasoning_chain.json` 和 `evidence.json`。

---

## 7. 常见命令变体

```bash
# 跳过数据导入，直接分析已有数据
/industrial-deep-diagnostic analyze

# 对已有结果重新评审
/industrial-deep-diagnostic review

# 从已有产物重新生成报告
/industrial-deep-diagnostic report

# 只运行审计
/industrial-deep-diagnostic audit
```

---

## 8. 跳错 HTML 可视化

如果只需要 `report.md`，在会话开始时说：

> "不要 HTML 页面，只要 report.md。"

Skill 会创建 `00_input/html_opt_out` 标记文件并跳过 HTML 构建。

---

## 9. 第一次运行失败的常见原因

| 现象 | 原因 | 解决 |
|------|------|------|
| RAG 引擎连不上 | `localhost:8765` 未启动 | Skill 会自动降级到本地本体构建，无需处理 |
| Python 依赖缺失 | venv 未创建 | 主 Agent 自动调用 `uv_env_setup.mjs` |
| Agent 超时 | 数据量大或网络慢 | 等待重试，或见 [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) |
| Judge 评分 <90 | 诊断质量不达标 | 自动进入修复循环，最多 3 次 |

---

## 10. 下一步

- 了解完整协议：[SKILL.md](./SKILL.md)
- 排查问题：[TROUBLESHOOTING.md](./TROUBLESHOOTING.md)
- 理解架构：[ARCHITECTURE.md](./ARCHITECTURE.md)
- 扩展 eval：[EVAL.md](./EVAL.md)
