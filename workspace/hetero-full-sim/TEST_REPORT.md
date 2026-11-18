# 完整管线测试报告 — 连续热处理线模拟场景（2026-10-17）

- 场景：连续热处理线 10 天（**与 BOPET / 锂电涂布均不同题**），注入故障 = 三区后段加热管老化（day 4.5 onset → day 6.75 更换修复 → 恢复）
- 数据：`workspace/hetero-full-sim/raw/`（DCS 1440×10min + 剖面 480×12位/30min + 炉膛温度场 5×4/2h + CCD 图像 240帧/1h + 操作备注 9 条 + 实验室硬度 120/2h）；真值单独在 `ground_truth.md`（run 目录内不可见）
- 运行目录：`workspace/hetero-full-sim/runs/202610162036022_heat_treat_sim/`（mode=fast）

## 测试 1 — 多源异构预处理 skill 单测（E-1 → E-1H → 双门禁）

| 项 | 结果 |
|---|---|
| E-1（格式适配） | exit 0；主表=1440 行 DCS（map 长表触发 anti-bloat 中止合并——设计行为，异构形态归 E-1H） |
| E-1H（`build.py`） | **status ok、4 源全 featured、40 个 HX 列**（PROF 18 / MAP 11 / IMG 7 / TXT 4 含 2 个事件窗口列） |
| E-1H 门禁（H1-H8） | **exit 0**（schema/行序/HX 表尾/溯源/覆盖/零LLM/时间/白名单/命名全过） |
| 信号捕获（跨模态 vs Z3 温度偏差） | IMG-ENTROPY \|r\|=0.918、MAP-CENTROID-X 0.911、MAP-ASYM-LR 0.905、PROF-MEAN 0.885 |
| annotations.json | 9 条事件正确提取（含"怀疑加热管老化"原文本） |

## 测试 2 — 完整分析 skill（industrial-analysis-auto 全管线，fast 模式）

| Step | 执行者 | 关键产出 | 门禁 |
|---|---|---|---|
| 0/1 Setup+Inspect | 主控 | run 目录、run_config(data_path→joined)、input_manifest、事件 | CP-1 ✅ |
| 0.5 E-1+E-1H | 主控 | 同上测试1 | 双门禁 exit 0 ✅ |
| 2+2.5 本体 | context-builder | ontology.json 70KB；**40/40 HX 契约合并**（KNOWN 25/INFERRED 13/**UNKNOWN 0**）；RAG 走降级路径并记录 | CP-2 门禁 9/9 ✅ CP-3 AUTO_RESOLVED ✅ |
| 3+3.3 统计+可视化 | data-processor | 显式异构列全用（targets 20/predictors 20/excludes 9，**dropped_requested_columns=[]**）；变点/段均值/段内相关；5 图含**强制剖面热图**；plot_verification PASSED | CP-4 ✅ |
| 3.5 VLM 视觉 | vlm-visual-analyzer | **真视觉直读 4 图**（非 caption 回退）：热图带窗、叠加谷、事件响应、因果图；交叉一致性 + 冗余告警 | — |
| 4 诊断 | diagnostician | **DETERMINED / 置信度 76 / 证据 L1**：三区后段加热能力损失（加热管老化）；7 假设 6 排除（鉴别矩阵 6/6 DISCRIMINABLE）；时序先验（过程先于质量）+ 更换后恢复闭环 | CP-5 双检查 exit 0 ✅ |
| 5a 判官 | judge | **PASS 96/100 零阻断**（独立复算 7 组关键数字逐位吻合） | CP-6 ✅ |
| 6 报告 | reporter | report.md 46KB/409 行/9 节；判官 4 条警告全部在附录消解 | CP-7 ✅ CP-7L ✅（首跑 FAIL：步→时间换算；修复后 exit 0） |
| 7 终审 | report-reviewer | **ENDORSED**；独立复算 Arrhenius 0.9648 逐位吻合、Wien 稳健、空间指纹自洽 | **CP-8 exit 0** ✅ |
| 8 HTML | html-visualizer | diagnostic-report.html 81KB；ECharts 三源+离线降级；自检 8/8 | 质量门 V1-V6 ✅ |
| 8.5 审查 | html-reviewer | **pass 93/100**；12 行数据抽检逐位吻合；红线 15/15 | CP-9 ✅ |
| 9 终结 | 主控 | **finalize: PASS（exit 0）**：inventory 34/35、schema 15/15、证据闭环 PASS、判官交叉审计 PASS、事件归档 PASS；run_completed 记录 | ✅ |

**诊断结论 vs 真值**：完全一致——"三区后段加热管老化 → 温降 4.93℃ + 波动 ×4.85 → 出料温度 −2.24℃ / 收得率 −0.99pt；右/下侧空间指纹指向局部热源；更换加热管后全链恢复"。排除项（热电偶漂移/全局热损/速度/相机/炉压/事件瞬态）均按协议给排除置信度与复活条件。

## 管线门禁实抓的真问题（本轮修复闭环）

1. **CP-5**：`anomaly_report` 跨域链接为空但声明 analysis_performed=true → 生产者侧投影 10 条真实相关对，检查 exit 0。
2. **CP-7L**：报告把滞后步数换算为时间而 `time_lag_analysis` 声明不可换算 → 17 处换算清除、附录记录口径差异，lint exit 0。
3. **finalize 契约**：fast 模式 5b 跳过缺 skip 证据、`input_manifest` 缺 time_column、两个产物 schema 不合规（pruned 字符串化、causal map 字段形状）→ 全部修复至 exit 0。
4. 非阻断遗留（已披露）：判官 4 警告、审计 E1 符号笔误与 M1 run_summary size 快照、D-段残余波动 sd 1.70 vs 0.79（记录为 follow-up）。

## 交付物

`runs/202610162036022_heat_treat_sim/`：report.md、diagnostic-report.html（81KB）、optimizer.md(ENDORSED)、run_summary.json、evidence_closure_report.json、pipeline_finalize_report.json、04_diagnostics/*、05_review/{judge_feedback,html_review}.json、03_figures/（5 图 + 视觉分析）、07_hetero/*（40 HX 契约）；`.pipeline_events.jsonl` 48 事件、log-check PASS。
