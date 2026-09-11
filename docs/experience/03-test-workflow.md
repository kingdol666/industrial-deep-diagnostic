# 端到端测试流程：从数据集到根因命中率报告

> 前置阅读：[02-analyzability-assessment.md](02-analyzability-assessment.md)。本流程已按"最小可跑通 → 放量"分层，任何一步失败都先停下排查，避免烧 token。

## 0. 环境准备

```bash
# 1) 后端 + 前端
ind-diag init && ind-diag backend   # http://localhost:3210

# 2) RAG 引擎（可选，不可用自动降级）
cd rag-retrieval-engine && python server.py   # :8764
curl -s localhost:8764/health || echo "RAG 不可用，将走 parameter_to_physics.json + Web 搜索降级路径"

# 3) Python venv（跑 prep 脚本用）
node .claude/shared/scripts/uv_env_setup.mjs
# → .claude/shared/scripts/.venv/Scripts/python.exe (Windows)
```

## 1. 数据准备（一次性）

```bash
PY=.claude/shared/scripts/.venv/Scripts/python.exe   # POSIX: .venv/bin/python

# TEP：7 个代表 CSV（正常 d00 + 故障 1/4/7/11/14/21，覆盖 step/random/valve-sticking/constant 四类机制）
$PY docs/experience/scripts/prep_tep.py \
    --src data/benchmark/tep_braatz_classic \
    --out data/benchmark/prepared/tep \
    --faults d00_te,d01_te,d04_te,d07_te,d11_te,d14_te,d21_te

# SKAB：全部 35 个文件 + ground_truth.json
$PY docs/experience/scripts/prep_skab.py \
    --src data/benchmark/skab/data --out data/benchmark/prepared/skab

# IndPenSim：演示 4 批（1 正常 + 91/94/99 故障）；全量 100 批用 --batches all
$PY docs/experience/scripts/prep_indpensim.py \
    --src data/benchmark/indpensim/Mendeley_data/100_Batches_IndPenSim_V3.csv \
    --out data/benchmark/prepared/indpensim --batches 1,91,94,99
```

产物自检：每个 CSV 首列时间戳严格递增（stats 有时间排序校验，乱序直接判 CCF 不可靠）；TEP 53 列、SKAB 9 列、IndPenSim 32 列。

## 2. 真值落位（沿用系统评测约定）

把真值文档放进 `data/truth/`（或为每数据集建 `data/eval_<name>/ground_truth.md`），`eval-assertions.mjs` 按此惯例断言：

```bash
cp docs/experience/ground-truth/tep-faults.md        data/truth/ground_truth_tep.md
cp docs/experience/ground-truth/skab-anomalies.md    data/truth/ground_truth_skab.md
cp docs/experience/ground-truth/indpensim-faults.md  data/truth/ground_truth_indpensim.md
```

同时准备变量语义表 `data/references/tep_variables.md`（从 ground-truth/tep-faults.md §1 复制），诊断请求时在 `process_description` 里引用。

## 3. 单 run 冒烟（先跑 1 个文件走通全管线）

```bash
curl -X POST localhost:3210/api/diagnosis/start -H "Content-Type: application/json" -d '{
  "dataPath": "D:/codes/myskills/industrial-deep-diagnostic/data/benchmark/prepared/skab/valve1_1.csv",
  "user_question": "诊断本次异常的根本原因",
  "process_description": "水循环试验台：水箱+离心泵+阀门回路。列含义：Accelerometer1RMS/Accelerometer2RMS=振动加速度RMS(g)，Current=电机电流(A)，Pressure=泵后回路压力(Bar)，Temperature=电机本体温度(℃)，Thermocouple=回路流体温度(℃)，Voltage=电机电压(V)，Volume Flow RateRMS=回路流量(L/min)。1Hz采样。"
}'
```

- 用 SSE/WebSocket 观察进度；完成后 run 目录在 `workspace/diagnostic-runs/<timestamp>_<scene>/`。
- 产物完整性两道门：

```bash
node .claude/skills/industrial-analysis-auto/scripts/artifact-check.mjs  <run_dir>
node .claude/skills/industrial-analysis-auto/scripts/pipeline-log-check.mjs <run_dir>/.pipeline_events.jsonl
```

- 验收点：`04_diagnostics/diagnosis.json` 的 conclusion_type ∈ {DETERMINED, COMPETING_SET, NEEDS_DATA}，根因描述与 ground truth（泵入口阀关闭）可匹配；`05_review/` judge 评分 ≥90。
- **冒烟矩阵建议**：每个数据集先各跑 1 个"有把握"的样本（SKAB valve1_1、TEP d01_te、IndPenSim batch_091），三绿后再放量。

## 4. 批量评测循环器（需自写，系统无现成批量 API）

约定：一次只启动一个 run（管线按单 run 设计），循环器负责 启动→轮询→解析→计分。骨架（Node，复用后端已有依赖）：

```javascript
// docs/experience/scripts/bench_runner.mjs （骨架，按需补全）
const BASE = "http://localhost:3210";
const CASES = [
  // { dataset: "skab", csv: "data/benchmark/prepared/skab/valve1_1.csv",
  //   truth: "泵入口流量阀门关闭", keywords: ["valve", "inlet", "关闭"], expect: "DETERMINED" },
];

for (const c of CASES) {
  const res = await fetch(`${BASE}/api/diagnosis/start`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ dataPath: c.csv, user_question: "诊断本次异常的根本原因",
                           process_description: c.process_description }),
  }).then(r => r.json());
  const runDir = res.run_dir;               // 轮询 SSE/状态接口至完成
  await waitUntilComplete(runDir);
  const dx = JSON.parse(await fs.readFile(`${runDir}/04_diagnostics/diagnosis.json`));
  const hit = matchTruth(dx, c.truth, c.keywords);   // 关键词匹配 + LLM-judge 双评
  console.log(c.csv, hit.top1, hit.top3, dx.conclusion_type, dx.confidence);
}
```

计分口径：
- **Top-1 命中**：根因结论与真值类型一致（关键词/机理同义匹配，或 LLM-judge 判"同根因"）；
- **Top-3 命中**：竞争假设集中含真值根因；
- **CDR**：Top-1 且 conclusion_type=DETERMINED 的比例（FDDBenchmark 口径）；
- **三态分开统计**：COMPETING_SET/NEEDS_DATA 不是错误 —— 对 3/9/15 这类难检故障，输出 NEEDS_DATA 是校准正确；另算"过度自信率"（结论 DETERMINED 但根因错）；
- SKAB/IndPenSim 额外评 **ADD**（诊断给出的故障起点 vs 标注起点）。

规模建议（对标 FaultExplainer 被批的样本量问题）：
- Exp-3（SKAB）：35 文件全跑，成本最低，先出第一张分类型命中率表；
- Exp-1（TEP）：经典版 20 故障 × 测试集 1 run 起步 → Rieth 版每故障抽 5 run（100 runs）做 mean±std；
- 每组 ≥3 次重复、固定种子、McNemar 或 bootstrap 显著性检验。

## 5. 实验 × 数据集 × 流程映射

| 实验 | 数据 | 用本库哪一步 | 额外工作 |
|---|---|---|---|
| Exp-1 主结果 CDR/Top-k | TEP Rieth/Reinartz | prep_tep.py 扩展到 RData/h5 批量导出 | RData 导出器（`pyreadr` 读 RData → 每 (fault,run) 一个 CSV） |
| Exp-2 抗记忆陌生故障 | TEP 仿真器自造扰动 | `tep_braatz_classic/` 自带 Fortran 仿真器（teprob.f） | 编译仿真器、参数化扰动组合 |
| Exp-3 真实试验台 | SKAB 35 文件 | **全部就绪，直接跑 §4** | — |
| Exp-4 批次泛化 | IndPenSim 100 批 | **全部就绪（indpensim_all/）** | — |
| Exp-5 反假相关压力集 | TEP/SKAB 注入混淆 | 在 prepared CSV 上注入 Simpson/时滞错位（自写扰动器） | 复用 stats.mjs 的 Simpson 检验做正向验证 |
| Exp-6 MCQA 对标 | FailureSensorIQ | 本地 jsonl 已就绪 | 接官方评测脚本 |
| Exp-7 消融×成本 | Exp-1 子集 | 同 Exp-1 | 记录每 run token 消耗（.pipeline_events.jsonl 有事件轨迹） |

## 6. 已踩过的坑（本次实操记录）

1. **SKAB 仓库地址**：`hndrec/SKAB` 已 404，现址 `waico/skab`。
2. **SKAB 标签是浮点格式**（`1.0`/`0.0`），按字符串 `== "1"` 匹配会全军覆没。
3. **IndPenSim 宽表坑**（官方未文档化，已实测破解，详见 prep_indpensim.py 头注释）：行块=批次、`PAT_ref` 列才是批次号权威来源（时间列重置点不可靠）、表头比数据行多 2 列（`Batch ID`/`Fault flag` 是脏列）、2200 个数字列是拉曼光谱波数（2400→201 递减）而非批次变量。
4. **Reinartz TEP 全量 143GB**：别整包拉，按需用 Rieth RData（1.4GB）或 fddbenchmark 加载器。
5. **经典 Braatz .dat 是空格分隔**（不是 tab），且无表头 —— 直接按 52 列解析即可。
6. **时间戳是合成的**：经典 TEP 无时间列，prep 脚本按 3 分钟间隔生成（与 Rieth 官方采样约定一致），故障起点固定在第 161 样本（8h）；论文报告时需声明这一约定。
