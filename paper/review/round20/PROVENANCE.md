# Provenance Audit — Experiments & Baselines (2026-09-24)

三个问题的产物级核验：实验是否用同一 LLM provider？baseline 是否真实复现？系统是否真实运行？

## Q1 — 管线与 baseline 是否同一 LLM provider？

**是，同一套 ZCode CLI harness + 同一 GLM 部署（2026-09 快照）。**

证据链：
1. 管线：13 个 benchmark run 经 ZCode agent CLI 派发（config `claude.binary` = ZCode 兼容 CLI；事件日志记录每 stage 子代理会话）。
2. baseline 录答：`baseline-lab/results/answers/**/*.json` 逐字归档，含
   `provider: "cli:claude"`、`model: "claude"`（CLI 的 provider 标签；底层为部署的 GLM
   模型族）、prompt 全文、`raw_reply` 全文、延迟与时间戳（2026-09-15 10:14 起的 live 采集）。
3. suite 回放：`baselines/baseline-suite/runs/*.json` 标 `mode:"recorded"` +
   `recorded_source:"archived raw replies of the same-GLM deployment as the IDD
   pipeline (ZCode CLI harness, Sept 2026 snapshot)"`；与论文 §8.3/Table 5 的
   "recorded replays of live runs" 表述一致。
4. suite 亦支持 live 模式（`BASELINE_LLM_BASE_URL/KEY/MODEL`，OpenAI 兼容，带 SSRF
   守卫，`server/utils/llm.mjs`），本轮未启用。
   残余披露（论文已有）：CLI 不暴露温度/top-p 与具体模型 id，故按部署快照表述。

## Q2 — baseline 是否真实复现（而非抄文献数字）？

**是。审计史与验证门禁均为数值级。**

- 审计起点：`baseline-lab/REPRODUCTION-AUDIT.md`（commit 221d061）——审计时
  仓库仅 1 个可运行对照；FE 官方 clone（li-group/FaultExplainer@2fcfee9）因无
  API key/环境不可运行 → 据此把 FE-protocol 在同一 GLM 部署上**复刻**（这正是论文
  Table 8 的 "FE-protocol replication (GLM)" 臂，如实命名）。
- 复刻验证门禁：`verify-fe.mjs` **21/21** 对 FaultExplainer 自带提交输出达到
  t2 相对误差 ~2e-12、异常旗标 500/500、贡献量 ~1e-13、触发索引全同；并发现
  FE 逐分量先 clip 再求和的真实约定。`verify-pca.mjs` 12/12 对照归档 PCA 数字；
  `verify-classical.mjs` 80/80；`verify-supervised.mjs` 620/620。
- PCA 臂：`scripts/benchmark/baseline_pca.mjs` 确定性脚本，12 场景实跑，数字
  （IDV3 T²2.9%/SPE4.8%、IDV4 48.8%/100%、对照 ≈1%）在 `baselines.json` 可复核。
- 真实性契约（代码强制）：LLM 失败→`skipped_no_provider`/空 top3，绝不编造；
  20 份盲态摘要 + 3 regime 提示词归档于 `results/benchmark/baseline_fe_prompts/`。

## Q3 — 两套系统是否真实运行？

**是。**
- IDD 管线：13 个 run 目录（`D:/codes/idd-run-archive/diagnostic-runs/`）含完整
  14 件产物集、`.pipeline_events.jsonl` 事件日志、finalize PASS；round-19 DA 审计
  59/60 数字逐项 MATCH（117.1 分钟事件跨度等均自事件日志复算）。
- baseline suite：45 份 run 记录带 `executed_at`（2026-09-17T22:42Z 起）；
  连续双跑 `suite_determinism.json` 45/45 字节一致（时间戳除外）。
- 唯一注意点：suite 的 LLM 臂在 suite 运行时是**回放**归档答案（recorded），
  归档本身来自 live 调用——论文以 "recorded replays of live runs" 如实披露；
  determinism 检查覆盖确定性臂的重执行，不覆盖随机推理层（论文 C5 亦如实界定）。
