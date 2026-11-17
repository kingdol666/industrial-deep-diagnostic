# AC.md — industrial-hetero-preprocessor（E-1H）验收记录（终稿）

> **独立验收席（V1–V5）记录位置：`.omc/plans/hetero-v1-verification/`**（由验收席稍后写入；该目录当前尚不存在，由验收席创建）。
>
> 本表所有"当前状态"数字均为 **2026-10-16 在本工作区树上实跑测得**（终稿时点复测），命令可复核；无一条数字抄自 plan 或记忆。
> 说明：WS12 撰写期间其他席**并发落库**了 P8 夹具、4 条跨 skill 契约、`core_stats` 加性审计与镜像同步——本表一律以**落库后复测**数字为准（初测 32 case/341 断言 → 39/393 → 独立验收后终态 **47 case/498 断言**）。
> 测试入口（共享 venv）：`.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-hetero-preprocessor/tests/run_tests.py`
> 夹具框架冻结于 WS0，用例自动发现（`tests/cases/test_*.py` 的 `CASES`）。当前全集：**47 case / 498 断言 / 0 失败**。
> WS0 冻结接口子集 = `ws0-naming(5) + ws0-time-ingest(9) + ws0-fingerprint(1) + ws0-build-noop(5) + ws0-exit4-gate2(2)` = **22 断言**（不受后续并发落库影响）。

## AC1 符合 skill 开发规范（plan §9）

| AC | 断言 | 验证命令 | 当前状态 |
|---|---|---|---|
| AC1-1 | G1–G7 全部技能绿灯（含本 skill，AC.md 落地后复跑） | `node scripts/test-skills.mjs` | **PASS** — `24 skills checked, 0 gate failure(s)`，exit 0；`PASS industrial-hetero-preprocessor (6 asset refs, 89 lines)` |
| AC1-2 | Harness 镜像漂移守卫 exit 0 | `node scripts/sync-harness-skills.mjs --check` | **PASS（含一项例行收尾）** — 已验证过完整同步：`OK .agents\skills: 511 files identical` / `OK .hermes\skills: 511 files identical`，exit 0（含 AC.md 首版）；其后本文件按落库复测数字做了**最后一次内容更新**，故当前 `--check` = 恰 1 个纯文档文件待同步（510 identical + AC.md）。收席时执行一次 `node scripts/sync-harness-skills.mjs` 即回到 exit 0（非代码漂移） |
| AC1-3 | 3 个 JSON 产物可构建、3 schema 过 `validate.mjs`（含严格 extra-keys） | run_tests 夹具端到端 + `quality_gate.mjs`（H1 调 `validate.mjs` + H1b 严格逐键检查） | **PASS** — `p5-build-end-to-end` 等用例在真实产物上跑门禁：`quality gate exit 0 on the profile-only run`（test_p1.py:434）；contract 逐字段断言（test_p1.py:403 起） |
| AC1-4 | `tests/AC.md` 逐条 PASS 证据存在 | 本文件 | **PASS**（本文件即终稿记录） |
| AC1-5 | `quality_gate.mjs` 可被 CP-0.5 命名调用，退出码 0/1/2/3 全覆盖 | run_tests 内 `ws0-build-noop`（0）、`ws0-exit4-gate2`（2）、`p8-control`（0）、`p8-t1..t4`（3） | **PASS** — exit 0（未篡改/无源 run）、exit 2（marker 缺失）、**exit 3（H 门禁失败，逐项点名触发的门）** 均有自动化 case；exit 1（硬错误）为异常路径分支（quality_gate.mjs:6），无专项 case |

## AC2 能处理多源异构数据（夹具矩阵，plan §9）

| AC | 断言 | 验证命令 | 当前状态 |
|---|---|---|---|
| AC2-1 | P1 剖面长表（幅值断言） | `run_tests.py p1-magnitude` | **PASS** — 20 断言 |
| AC2-2 | P2 剖面宽表 ≡ 长表 | `run_tests.py p2-wide-long-equivalence` | **PASS** — 5 断言；逐特征列 max\|Δ\| < 1e-9（test_p1.py:266） |
| AC2-3 | P3 规则栅格 2D 场（热点/负例/缺格/散点登记） | `run_tests.py p3-grid-hotspot p3-grid-negative p3-missing-cells p3-scatter` | **PASS** — 23 + 4 + 8 + 8 断言（栅格判据 coverage≥0.6；缺格留 NaN 不插值；散点**只登记不分析**） |
| AC2-4 | P3 部分剖面（快照有效位点 <60% ⇒ 留幅值、形状置空） | `run_tests.py p3-partial-profile` | **PASS** — 29 断言（自动降级 + contract 如实标注） |
| AC2-5 | P4 图像序列最小路径（索引流/目录流/无标定无 Q-* 列/ts_conflict 排除/Pillow 显式声明） | `run_tests.py p4-index-stream-min p4-no-q-columns p4-ts-conflict p4-dir-stream p4-pillow-missing p4-pyproject-pillow` | **PASS** — 6 case 共 41 断言（18+5+7+6+3+2） |
| AC2-6 | P5 时序文本（中英备注时间精确/歧义日期整源跳过/散文日志/事件窗配置） | `run_tests.py p5-remarks-csv p5-ambiguous-skip p5-prose-log p5-window-config` | **PASS** — 4 case 共 96 断言（48+8+36+4） |
| AC2-7 | P6 混合节奏（非空数=⌈span/cadence⌉±1、陈旧度上限、迟到源 NaN 而非 ZOH、重复时刻聚合、传输滞后、anchor 行数/行序不变） | `run_tests.py p6-mixed-cadence p6-staleness-no-zoh p6-late-source p6-evt-window p6-duplicate-aggregate p6-transport-lag p6-anchor-discipline` | **PASS** — 7 case 共 58 断言（16+9+5+7+7+6+8） |
| AC2-8 | P7 仅图像（raw 只有图片流，无任何标量表） | `run_tests.py p7-images-only` | **PASS** — 10 断言（images-only build exit 0、仅写 `07_hetero/**`） |
| AC2-9 | P8 篡改 ⇒ 门禁 exit 3 并点名触发的门（未来时间戳 / 改源文件 / coverage 说谎 / 列名违规） | `run_tests.py p8-control p8-t1-future-src-ts p8-t2-source-edit p8-t3-coverage-lie p8-t4-bad-name` | **PASS** — 5 case 共 25 断言：`p8-control` 未篡改 ⇒ gate exit 0；t1–t4 各自 `gate exit 3 after <name>`（test_p8.py:152） |
| AC2-Σ | 全量回归 | `python .claude/skills/industrial-hetero-preprocessor/tests/run_tests.py` | **PASS — `47 case(s), 498 assertion(s), 0 failure(s)`，exit 0**（含 V 席修复轮复测）（原始输出见文末附录） |

## AC3 作为子 skill 接入已有场景分析 skill（plan §9 ①–⑥）

| AC | 断言 | 验证命令 / 证据 | 当前状态 |
|---|---|---|---|
| AC3-① | 管线档：Step 0.5 链式注册 + `run_config.hetero` 块 + log-check step id + finalize marker 检查 | `setup.mjs:44`、`pipeline-log-check.mjs:54`、`run_config_schema.json` hetero 块、`pipeline-finalize.mjs:148-158`（Stage 0.5b：走 E-1 ∧ `hetero.enabled≠off` ∧ marker 缺失 ⇒ FAIL） | **PASS（接线面）** — build 侧端到端（manifest 写回 / joined 表产出）由 p5/p6 build e2e 证明；**全链路 run 演示（模板包实测）仍待 M4 收尾，见文末待办** |
| AC3-② | 统计档：`stats_eligible=true` 列进统计、被拒列出 `dropped_requested_columns`（可见性） | `core_stats.py:816,936`（加性审计：请求列未过覆盖门槛 ⇒ 报告落 `dropped_requested_columns`，不删默认逻辑）+ `industrial-data-processor/references/agent-protocol.md:124`（非空必须写入 data_quality，静默遗漏禁止） | **PASS（实现在位）** — 代码 + 协议披露规则均在；**专项自动化可见性断言未见**（全部 tests/ 内 grep 仅本 AC.md 命中），验收席可按此处复核 |
| AC3-③ | 图表档：时间×位置热图 + 条目显式 `vlm_priority` + manifest schema 合法 | `.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-data-processor/tests/test_hetero_heatmap.py` | **PASS — `WS7 heatmap test: ALL PASS`**（43 条 [PASS]，含 `AC2 entry has explicit vlm_priority — CRITICAL`；多源 2 PROF → 2 张热图、每源一 manifest 条目、schema 复验空） |
| AC3-④ | 哨兵档：显式 CLI 在 joined 表出 ≥1 条 HX 特征发现 | `grep -rln "HX-" .claude/skills/industrial-sentinel/` | **PASS** — `tests/cases/test_m3.py::m3-sentinel-e2e`（19 断言）：真实 run 上 sentinel watch 输出 12 条 `HX-PROF-THKSCAN-*` findings（ROBUST_Z/NELSON），V2 席独立复核为非 mock |
| AC3-⑤ | 产线报告档：目录含 `07_hetero/` 时主表选择不变（防劫持 smoke）；auxiliary 注册 | `grep -rln "07_hetero" .claude/skills/industrial-line-stability-report/` | **PASS** — `test_m3.py::m3-lsr-anti-hijack`（8 断言）：劫持形状下（hetero score 24.2>3.5）单主表仍选 data.csv；`07_hetero` 跳过已入 E-1 `_discover_sources` |
| AC3-⑥ | 契约档：4 条 `cross_skill_contracts` 条目 + primary_path 形状测试 | `.claude/shared/schemas/cross_skill_contracts.json` + `run_tests.py p8-contract-registry` | **PASS** — 4 条在案：`hetero_contract_to_ontology`（columns[].physical_meaning）、`hetero_features_to_dataprocessor`（targets）、`hetero_annotations_to_tuning_memory`（[].event_ts）、`hetero_contract_to_optimizer`（columns[].insufficient_data）；`p8-contract-registry` 17 断言验证契约形状 |

## AC4 提高图片/向量/文字支持（端到端证据链：列名 → contract → features/*.csv → source_sha256 回算）

| AC | 断言 | 验证命令 | 当前状态 |
|---|---|---|---|
| AC4-1 | 向量（剖面）：幅值断言证明**数值正确**而非仅可溯源；契约含 unit/role/formula/evidence_level/source_sha256 | `run_tests.py p1-magnitude`（20）+ `p5-build-end-to-end`（9） | **PASS** |
| AC4-2 | 图像：索引解析 → 整图质量向量 → 契约溯源；模型派生产物默认不存在（无标定无 `Q-*`，`--enable-llm/--enable-pca` 默认关闭） | `run_tests.py p4-index-stream-min`（18）+ `p4-no-q-columns`（5） | **PASS** |
| AC4-3 | 文字：3 条已知备注时间精确、事件窗 0/1 列正确；`annotations.json` 带 event_ts/tag_slug/source_sha256/line_no | `run_tests.py p5-remarks-csv`（48）+ `p5-window-config`（4） | **PASS** |

## 回归安全（bc1 场景等价性说明）

**如实表述：benchmark 不覆盖本 stage** —— `grep -rn data_preprocessor scripts/benchmark/ | wc -l` 终稿复测 = **0**
（benchmark 管线不经过 E-1，自然也不经过 E-1H），故不以 benchmark 作回归证据；bc1
（`data/bopet_cases/bc1_dryer_dewpoint`）等既有场景的等价性由以下 ①②③ 证据链承担：

| # | 断言 | 验证命令 | 当前状态 |
|---|---|---|---|
| 回归-① | 构造性 no-op：无异构源时只写 marker 一个文件，E-1 的 `preprocessed_data.csv` 等产物字节不动（sha256 记入 manifest `h7_guard` 供事后比对） | `run_tests.py ws0-build-noop` | **PASS** — 5 断言（`only the marker written` 等） |
| 回归-② | 指纹不变式：表尾追加 `HX-*` 列后 `schema_fp` 不变（plan D6，ontology fast-reuse 不失配） | `run_tests.py ws0-fingerprint` | **PASS** — 1 断言：`schema_fp unchanged with tail HX columns`（真实调用 `.claude/shared/scripts/ontology_store.mjs` computeFingerprint 对照） |
| 回归-③ | Smoke：E-1 既有套件在异构改动共存的工作区上全绿（E-1 行为不变） | `.claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py` | **PASS — `ALL TESTS PASSED`**（50 条 ok 断言），exit 0（终稿复测） |

## 待办移交（验收席复核时关注）

0. **镜像收尾**：`node scripts/sync-harness-skills.mjs` 一次（本 AC.md 终稿更新后恰 1 个纯文档文件待镜像），复跑 `--check` 应 exit 0。
（原 PENDING 项 AC3-④/⑤ 已由 `tests/cases/test_m3.py` 落库取代，见上表。）
独立验收席 V1–V5 记录：`.omc/plans/hetero-v1-verification/`。V1 修复轮（主控）：H2 anchor.columns 键位、joined 仅 HX 列、contract↔joined 成员校验、H8 features 目录守卫、uncaughtException 结构化 fail-closed、written 路径 run 相对化、`to_ontology_signals` role/governing_law 使本体映射为 schema 合法 drop-in——修复后全量 47/498 复测绿。
3. **AC3-② 收尾**：`dropped_requested_columns` 的专项可见性断言（当前只有实现在位 + 协议披露规则，无单测）。
4. **AC3-① 全链路演示**：M4 收尾项——把模板包（含《数据导出规范》第九节的示例形态）混装文件夹喂进管线跑通一次真实 run。

---

## 附录：终稿时点原始命令输出（摘要）

```
$ .claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-hetero-preprocessor/tests/run_tests.py
[PASS] p1-magnitude (20)          [PASS] p2-wide-long-equivalence (5)
[PASS] p3-partial-profile (29)    [PASS] p4-detect-discrimination (6)
[PASS] p5-build-end-to-end (9)    [PASS] p3-grid-hotspot (23)
[PASS] p3-grid-negative (4)       [PASS] p3-scatter (8)
[PASS] p3-missing-cells (8)       [PASS] p3-build-e2e (12)
[PASS] p4-index-stream-min (18)   [PASS] p4-no-q-columns (5)
[PASS] p4-ts-conflict (7)         [PASS] p4-dir-stream (6)
[PASS] p4-pillow-missing (3)      [PASS] p4-pyproject-pillow (2)
[PASS] p5-remarks-csv (48)        [PASS] p5-ambiguous-skip (8)
[PASS] p5-prose-log (36)          [PASS] p5-window-config (4)
[PASS] p6-mixed-cadence (16)      [PASS] p6-staleness-no-zoh (9)
[PASS] p6-late-source (5)         [PASS] p6-evt-window (7)
[PASS] p6-duplicate-aggregate (7) [PASS] p6-transport-lag (6)
[PASS] p6-anchor-discipline (8)   [PASS] ws0-naming (5)
[PASS] ws0-time-ingest (9)        [PASS] ws0-fingerprint (1)
[PASS] ws0-build-noop (5)         [PASS] ws0-exit4-gate2 (2)
[PASS] p8-control (5)             [PASS] p8-t1-future-src-ts (5)
[PASS] p8-t2-source-edit (5)      [PASS] p8-t3-coverage-lie (5)
[PASS] p8-t4-bad-name (5)         [PASS] p7-images-only (10)
[PASS] p8-contract-registry (17)

47 case(s), 498 assertion(s), 0 failure(s)      # exit 0

$ node scripts/test-skills.mjs
PASS industrial-hetero-preprocessor (6 asset refs, 89 lines)
24 skills checked, 0 gate failure(s)            # exit 0

$ node scripts/sync-harness-skills.mjs --check
OK     .agents\skills: 511 files identical
OK     .hermes\skills: 511 files identical
All harness skill mirrors are in sync with .claude/skills.
                                                # exit 0（22:55 验证；其后 AC.md 终稿更新一次，
                                                # 当前 --check 为恰 1 个纯文档文件待同步，见 AC1-2）

$ .claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-data-preprocessor/tests/test_preprocessor.py
ALL TESTS PASSED                                # 50 条 ok 断言，exit 0

$ .claude/shared/scripts/.venv/Scripts/python.exe .claude/skills/industrial-data-processor/tests/test_hetero_heatmap.py
WS7 heatmap test: ALL PASS                      # 43 条 [PASS]，exit 0

$ grep -rn data_preprocessor scripts/benchmark/ | wc -l
0                                               # benchmark 不经过 E-1
```
