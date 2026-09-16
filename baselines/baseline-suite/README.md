# IDD Baseline Suite（Nuxt 复刻套件）

复刻 IDD 论文对照算法的**可启动**项目。被对照的算法分两类放置：

| 类别 | 位置 | 说明 |
|---|---|---|
| 有公开仓库者 | `baselines/FaultExplainer/`（上级目录） | 上游 **vendored 快照**：li-group/FaultExplainer @ `2fcfee9`（MIT，VENDOR.md 记录出处，含 load-bearing 的 TEP 语料） |
| 无公开仓库者 | 本目录（Nuxt 3） | 按论文 §8.4 的对照算法**协议复刻**：经典 PCA、FE 协议复刻、同模型裸 LLM 单次调用 |

## 三条基线臂

1. **经典 PCA 监测**（Chiang 2001/Qin 2012）：正常对照训练、95% 累计方差（纯 JS Jacobi 特征分解）、
   T²+Q 统计、报警阈 = 对照分布 99 分位、检出窗 = TEP 第 161 样本起（其余数据集全文件）、
   诊断 = SPE 贡献 top-3（无机理判决——这正是论文强调的检测-诊断鸿沟）。
2. **FE 协议复刻**：PCA(0.9) + T²(α=0.01，F 限含 (n+1)/n 因子，与上游 model.py 一致) +
   6 连续触发 + 触发样本逐特征 T² 分解 top-6 + EXPLAIN_ROOT 提示（15 故障公开病因清单）。
   已记录偏差：模型在 benchmark 的正常对照记录上训练（上游用其 500 样本 fault0 语料）。
3. **同模型裸 LLM 单次调用**：盲态统计摘要 → 单次补全（无本体/无管线/无门禁），三种 regime
   （无候选 / 含候选 / FE 官方提示）。执行模式：
   - **live**：配置 `BASELINE_LLM_BASE_URL` + `BASELINE_LLM_API_KEY`（+ `BASELINE_LLM_MODEL`，默认 glm-4.6）
     后走 OpenAI 兼容 `/chat/completions`；发请求前校验 host——仅允许 http/https，拒绝
     localhost/环回/私有/保留地址；
   - **recorded**（默认）：回放与 IDD 管线同 GLM 部署的归档 raw 回答
     （`results/benchmark/baseline_fe_answers/`，2026-09 ZCode CLI 快照），响应显式标注。

## 真值隔离契约

本套件**不读取任何真值/关键词/评分**：场景路由只取 `{case_id, dataset, csv, control}` 四个
无真值字段；统计证据来自盲态 brief（`results/benchmark/briefs/`，经 check-leakage 哨兵）。
准确率评分全部在 benchmark 侧完成（`scripts/benchmark/baseline_llm.mjs score`）。

## 启动与全量执行

```bash
npm install        # 一次性
npm run dev        # http://localhost:5181
npm run run-all    # 12 场景 × 全部臂 → runs/*.json（可 --only <case> 或 --base <url>）
```

完整四步测试流程（IDD × 套件双项目、抽查复测、对比报告）：见
`docs/benchmark/baseline-suite-pipeline.md`。
