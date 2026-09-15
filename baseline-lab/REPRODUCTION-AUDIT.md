# Benchmark 对照算法复现审计报告

> 审计对象：`industrial-deep-diagnostic` 仓库的 benchmark 评测流程
> 核心问题：**benchmark 是否真正复现了 baseline 与其他 LLM 诊断算法，并达到可投入测试的状态？**
> 结论载体：`baseline-lab/`（专用 Nuxt 工程，15 个可运行对照算法 + 复现验证门禁）

---

## 一、结论摘要

**没有。** 审计前，仓库里真正可运行的对照算法只有 **1 个**。

| 文档声称的对照 | 审计前实际状态 | 判定 |
|---|---|---|
| 经典 PCA 基线 | `scripts/benchmark/baseline_pca.mjs` 确定性脚本，实测可跑通 12 场景 | ✅ **可运行** |
| 同模型裸 LLM 基线 | 23 份**真实**模型回答归档 + 19 份提示词，但**没有执行通路**；`baseline_llm.mjs check` 只打印一段让人手工去跑的“执行契约”；25 份应有答案缺 2 份 | ⚠️ **仅有归档，不可执行** |
| FaultExplainer | `baselines/FaultExplainer` 是 commit `2fcfee9` 的**完整真实克隆**，但 `backend/.env` 的 `OPENAI_API_KEY` 为空、无 sklearn/fastapi 环境、`backend/results.txt` **0 字节** | ⚠️ **已克隆，不可运行** |
| CoT / ReAct / AutoGen 多代理 / XGBoost / LSTM | `docs/publication-strategy-report.md` §5.2 把它们列为对比矩阵的基线臂；仓库中**没有任何可运行实现** | ❌ **从未实现** |

也就是说：**“基线对比”在很大程度上是引用文献数字，而不是本仓库实测。**
`docs/benchmark/design.md` §4 的期刊 baseline 表本身就标注了大量“未核实”，
`docs/benchmark/AUDIT-2026-09-13.md` 也已记录 `A5/A7`“补本地 PCA 基线实测”为**未做**。

---

## 二、审计做了哪些实测（而不是读文档）

1. **实跑仓库自带脚本**
   - `node scripts/benchmark/baseline_pca.mjs` → 12/12 场景产出检测率，脚本确为真实确定性实现。
   - `node scripts/benchmark/baseline_llm.mjs check` → 退出码 0，但输出的是**人工执行契约**，不是执行。
   - `node scripts/benchmark/baseline_llm.mjs score` → 从归档重算：strict(no_cand) 9/9、fe_style 6/6、对照 2/2、误报 0。
     **注意：这只证明“归档答案能被重算”，不证明“算法可被运行”。**
2. **答案文件真实性抽查**（按 `docs/benchmark/reproduction-guide.md` §10 红线）
   - 逐字节验证为合法 UTF-8；内容为带真实数字引用的完整论证，非模板填充，**看起来是真实模型输出**。
   - 期望 25 份（TEP 6 故障 × 3 regime + d00 对照 × 2 + 非 TEP 5 × 1），实际 23 份，
     缺 `tep_d00_normal_control.no_candidates` 与 `.with_candidates`。
3. **FaultExplainer 克隆真实性**
   - `git remote -v` → `https://github.com/li-group/FaultExplainer.git`；`HEAD` = `2fcfee975a687c350f10909eeccd1ecdd60340be`。
   - 含 21 份带标签 TEP 运行（`backend/data/fault0..20.csv`）+ 21 份**自带处理产物**（`frontend/public/fault*.csv`）。
   - **不可运行**：无 API key、无 Python 依赖环境、无端到端执行记录。
4. **对照文档核对覆盖缺口**
   - `docs/publication-strategy-report.md` §4.2 写“6 个 baseline”，§5.2 矩阵含 CoT / ReAct / AutoGen / XGBoost / LSTM；
     仓库内均无实现。

---

## 三、审计后的动作：`baseline-lab/`

在**独立专用目录**下建成 Nuxt 4 工程，把对照算法做成**真正可执行**的模块（`meta` + `async run(ctx)`），
纯 JS、零外部依赖，直接读仓库的 12 场景与真实数据，**从不写入仓库其他位置**。

### 15 个可运行对照算法

**经典统计过程监测（确定性 / 离线，6 个）**
`pca-t2-spe` · `kpca-rbf` · `ica-fastica` · `spc-ewma-cusum` · `knn-fdd` · `iforest`

**监督 / 深度学习（确定性，用 FaultExplainer 真实带标签 TEP 训练，4 个）**
`xgb-gbdt` · `rf-forest` · `mlp-classifier` · `ae-reconstruction`
> 仅声明 `domains: ['tep']`；对 SKAB/IndPenSim 返回 `applicable: false` 与空结论，**不编造预测**。

**LLM 诊断算法（真实 provider 调用，5 个）**
`llm-direct`（裸单次）· `llm-cot`（思维链）· `llm-react`（4 个真实数据工具的 ReAct 循环）·
`llm-debate`（3 专家 + 反驳 + 主席裁决）· `fe-official`（FaultExplainer 官方协议复刻）

### 复现验证门禁（数字对不上即失败）

| 门禁 | 结果 |
|---|---|
| `scripts/verify-pca.mjs` | **12/12 PASS** —— 本实验室 PCA 与仓库归档 `baseline_pca_rca.json` 的检测率、保留主元数完全一致 |
| `scripts/check-fe-scaler.mjs` | **12/12 exact** —— 钉死 FE 的 StandardScaler 约定：**全部 500 行、总体标准差（ddof=0）** |
| `scripts/verify-fe.mjs` | **21/21 PASS** —— `t2_stat` 相对误差 ~**2e-12**、`anomaly` 标志 **500/500** 一致、52 个特征贡献 ~1e-13、**触发下标完全一致** |
| `scripts/verify-classical.mjs` | **60/60 PASS** |
| `scripts/verify-supervised.mjs` | **620/620 PASS** |
| `scripts/provider-selftest.mjs --live` | provider 真实调用 + **隔离校验通过**（CLI harness 在干净 cwd 且禁用工具） |

> **FaultExplainer 复刻的可信度**：`verify-fe.mjs` 把 FE **自己提交的**产物
> （`frontend/public/fault*.csv`）里的原始 52 列喂回本实验室的重实现，逐行比对
> `t2_stat` / `anomaly` / 52 个 `t2_<feature>` 贡献。21 个文件 × 500 行 × 52 特征全部在 1e-12 量级吻合——
> 这才有资格称“复刻了 FE 协议”，而不是“近似了 FE”。
>
> 该门禁还抓到一个关键细节：FE 对**每个主元项**先 `np.maximum(c_ji, 0)` 再求和；
> 若改成对总和截断，贡献值偏差约 **40%**。

---

## 四、实测结果（120 组确定性运行，26.4s）

**Top-1%** 是仓库 rubric 口径（rank-1 命中机制关键词**或**真实 IDV 编号）；
**精确 IDV** 要求 rank-1 明确写出真实 IDV 编号。二者必须并报——
因为 `{IDV4, IDV11, IDV14}` 等故障族共享同一批关键词，关键词命中**不等于**族内区分成功。

| 算法 | Top-1 | Top-1% | Wilson 95% | 精确 IDV | 对照通过 | 误报 | 弃权 |
|---|---|---|---|---|---|---|---|
| `pca-t2-spe` | 4/9 | 44% | [18.9, 73.3] | 1/6 | 3/3 | 0 | 4 |
| `kpca-rbf` | 4/9 | 44% | [18.9, 73.3] | 2/6 | 3/3 | 0 | 4 |
| `ica-fastica` | 4/9 | 44% | [18.9, 73.3] | 1/6 | 3/3 | 0 | 4 |
| `spc-ewma-cusum` | 4/9 | 44% | [18.9, 73.3] | 1/6 | 3/3 | 0 | 3 |
| `knn-fdd` | 4/9 | 44% | [18.9, 73.3] | 2/6 | 3/3 | 0 | 4 |
| `iforest` | 3/9 | 33% | [12.1, 64.6] | 0/6 | 3/3 | 0 | 5 |
| `xgb-gbdt` | 6/9 | 67% | [35.4, 87.9] | **6/6** | 2/3 | 1 | 3 |
| `rf-forest` | 6/9 | 67% | [35.4, 87.9] | **6/6** | **3/3** | **0** | 3 |
| `mlp-classifier` | 4/9 | 44% | [18.9, 73.3] | 4/6 | 2/3 | 1 | 3 |
| `ae-reconstruction` | 4/9 | 44% | [18.9, 73.3] | 2/6 | 2/3 | 1 | 3 |

**怎么读这张表**

- 经典方法看似 44%，但**精确 IDV 只有 17–33%**——它们给出了变量贡献，
  但“变量 → 机理”的那一步是外挂的知识映射，族内区分基本失败。
  这与 `docs/benchmark/design.md` §3A 记录的“IDV3/IDV4 属 PCA 不可检集”一致。
- 监督方法在 TEP 上**精确识别 6/6**，但 `xgb`/`mlp`/`ae` 各自在正常对照上误报 1 次；
  **`rf-forest` 是唯一同时做到 6/6 精确识别且 0 误报的算法**。
- 所有算法对 SKAB/IndPenSim 基本弃权——非 TEP 域缺少公开的变量→成因对照表，
  本实验室**明确拒绝**为这些域臆造映射。

---

## 五、LLM 基线实测（20 组真实调用，39 分钟）

范围限定在 4 个 TEP 场景（`d01` / `d04` / `d07` / `d00` 对照）——
`fe-official` 的成因清单与 `with_candidates` regime 本身只对 TEP 定义。

| 算法 | Top-1 | 精确 IDV | FE@3 | 对照通过 | 误报 | 每场景调用次数 |
|---|---|---|---|---|---|---|
| `llm-direct` | 1/3 | 0/3 | 0/3 | 0/1 | 1 | 1 |
| `llm-cot` | 1/3 | 0/3 | 0/3 | 0/1 | 1 | 1 |
| `llm-react` | 2/3 | 0/3 | 0/3 | 0/1 | 1 | ≤7 |
| `llm-debate` | 1/3 | 0/3 | 0/3 | 0/1 | 1 | 5 |
| `fe-official` | 2/3 | **2/3** | **3/3** | **1/1** | **0** | 1 |

**怎么读**

- **`fe-official` 最强，且是唯一在正常对照上不误报的 LLM 对照**——
  因为它的统计前端会**闸住**模型调用（没有连续 6 次 T² 越限 ⇒ 直接报正常，
  而不是让模型去编一个成因）。单纯靠提示词拿不到这个性质。
- **这批数字远低于归档基线的 9/9**，但这正是预期的：
  归档是 GLM 部署、本次是 Claude，**不同模型 = 不同实验**（见第五节混淆项）。
  不要把这一列读成“基线退化了”。
- 每份回答逐字归档（提示词、provider、模型、耗时、原始回复）于
  `results/answers/<case>/`；`llm-debate` 连 5 轮辩论（含反驳）全部留痕，可审计而非摘要。

---

## 六、必须声明的混淆项（否则数字会被误读）

**仓库归档的 LLM 基线由 GLM 家族部署产生**（`results/benchmark/baselines.json` 的 `model` 字段），
而本实验室在**当前机器上自动解析到的 provider 是 Claude**（`cli:claude`）。

> ⚠️ **二者不是同一个模型。因此本实验室新跑的 LLM 基线数字，不能与
> `results/benchmark/baselines.json` 直接比较**——那是在不同模型上的新实验。

实验室已把这条做成显式告警：侧边栏、Run 页、Results 页都会渲染 `model confound` 横幅，
CLI `node scripts/audit.mjs` 也会打印。若要与归档口径对齐：

```bash
BASELINE_LLM_PROVIDER=openai-compatible \
BASELINE_LLM_BASE_URL=https://<glm-endpoint>/v1 \
BASELINE_LLM_API_KEY=... \
BASELINE_LLM_MODEL=glm-4.6 \
npm run dev
```

---

## 七、诚实缺口（登记而非掩盖）

| 缺口 | 原因 | 本仓库替代 |
|---|---|---|
| FaultExplainer Python 管线原样运行 | 需 OpenAI key + 科学计算环境；上游未提供执行记录 | `fe-official` 逐式复刻，并与 FE 自带产物核对到 ~1e-12 |
| Gong et al. (JII 2026) 多代理系统 | FailureSensorIQ 是 MCQA 问答集，代理编排未开源；论文数字跨任务不可直比 | `llm-debate` 同构自实现（**不是**他们的系统） |
| AutoGen / CrewAI | 框架未安装，无工业诊断适配 | `llm-debate` 无框架依赖实现 |
| 文献 XGBoost / LSTM / BeatGAN 数字 | 逐样本检测任务，与根因任务口径不同 | `xgb`/`rf`/`mlp`/`ae` 同族模型在**本基准**上的实测 |
| 监督模型的已知缺陷 | 训练/评估窗口不一致（80 vs 800 样本）；XGB 训练精度 1.000（插值 336 样本）；AE 阈值在两种 TEP 编码间不可逐行迁移 | **如实报告，未调参掩盖** |
| `tep_d00_normal_control` 缺 2 份归档答案 | 仓库自身归档不全 | 实验室可现场真实执行补齐 |
| 12 场景样本量小 | 9 个故障无法支撑细粒度排序结论 | 全部指标报 Wilson 95% 区间 |

---

## 八、如何运行

```bash
cd baseline-lab
npm install
npm run dev            # → http://localhost:5190
```

页面：**复现审计** / **运行基线**（实时进度表）/ **结果对比**（逐场景×逐算法矩阵）/ **算法清单** / **场景与数据**

```bash
node scripts/sweep.mjs --list
node scripts/sweep.mjs --family classical
npm run verify           # 一键跑全部复现门禁
node scripts/audit.mjs   # 终端版审计报告
```

---

## 九、一句话回答

> benchmark **原先并没有**真正复现对照算法：只有一个可跑的 PCA 脚本，
> 裸 LLM 基线是冻结的答案归档，FaultExplainer 克隆了但跑不起来，
> 文档声称的 CoT / ReAct / 多代理 / XGBoost / LSTM **从未实现**。
>
> 现在 `baseline-lab/` 用 15 个可运行对照算法补上了这个缺口：
> 确定性算法离线可跑，LLM 算法走真实 provider 调用（**绝不编造答案**），
> FaultExplainer 协议复刻到 1e-12 且与上游自带产物逐行核对通过，
> 并且把“模型不同不可直比”这一混淆项显式做成了告警。
