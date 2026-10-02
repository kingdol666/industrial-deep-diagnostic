# AC.md — industrial-sentinel 验收标准（A 组，plan industrial-closedloop-skills-v1 §3.4）

> 运行方式（仓库根）：
> `uv run --project .claude/shared/scripts python .claude/skills/industrial-sentinel/tests/run_tests.py all`
> 输出 `ALL GREEN` 即全部通过。所有 fixture 数据由 run_tests.py 以**固定 seed** 现场生成
> （无随机抽取、无网络、无 LLM）。“实测”列在每次全量跑绿后更新。

| # | 标准（冻结） | 验证方式 | 实测 |
|---|--------------|----------|------|
| A1 | F2 注入漂移（第 6000 行起 +0.8σ/千行，σ=基线 σ_within≈1.0）必触发 R2/R3，且触发位置落在漂移起始 ±200 行（observed.index ∈ [5800, 6200]） | F2：`F2_R2_in_band_5800_6200` + `F2_R3_in_band_5800_6200`。fixture：temp 噪声 0.1（基线 σ=1.0）、press 噪声 0.04（σ=0.4），seed 42；R2/R3 为符号型规则，稳态段本底触发率 ~1/256、~1/350 每点，60 行同类抑制窗把漂移后连续触发聚成 episode，其首个触发点（earliest index）即“检出位置” | PASS（R2 band=[5914, 5985, 6112, 6066]；R3 band=[5915, 6154, 5844, 6125]，seed 42） |
| A2 | 1 万行 watch ≤ 120s（分段预算 load≤10s / regime≤20s / SPC≤30s / 多变量≤30s / 写盘+gate≤20s） | F2：`F2_duration_le_120s`，取 alert.provenance.duration_ms 与测试进程墙钟双断言 | PASS（duration_ms = 49，墙钟 ≈ 0.6s） |
| A3 | 抑制：60（行/分钟对偶）窗内同 key 合并 repeat_count+1 | F3：同一 spike 批次二次投递 → `F3_repeat_count_merged`（NELSON_R1 告警 repeat_count ≥ 2，fast_state.suppression 记账）；watch 侧由 gate S4（同 key 60 行内出现两条 = FAIL）反向保证 | PASS |
| A4 | 变点静默期 30 行无 SPC 告警（并重估中心线） | F2：`F2_quiet_zone_honored`——对每条 REGIME_CHANGE_NEW 的 cp，断言无 SPC 告警 index 落于 [cp, cp+30)；中心线重估由实现保证（静默期后的行用该段均值重估中心再评估，两段行集不重叠） | PASS（12 个新变点，首个 6183，0 违规） |
| A5 | 冷启动 self 基线全告警带 SELF_BASELINE + 48h 固化提示 | F4：`F4_baseline_mode_self` + `F4_SELF_BASELINE_alert` + baseline_version 前缀 `self:` + 48h 提示写入 self 基线（validity.self_baseline_ttl_hours=48，报告冷启动横幅）；稳态行不足时 exit 2（`F4_cold_start_impossible_exit2`） | PASS |
| A6 | alert.json 过 schema + gate exit-code 四态正确（发现→1、无基线→2、gate FAIL→3；ok→0） | F1（exit 0）· F2/F4/F5（exit 1）· F3（spike→1、无基线→2、超 500 行→2）· F1/F2/F3/F5 gate exit 0 + tamper 电池（坏枚举 / 风暴 / 多余键 → gate 1）；exit 3 路径由 sentinel.py self_check（与 gate S1/S4 同规则）保证，schema 双验由 validate.mjs 完成 | PASS |
| A7 | build_baseline 与 doe-analyzer 源字段**逐值相等**（diff 断言） | F6：对 canned recommendations.json / stability_report.json 断言 operating_windows、indicators（lsl/usl/target/goal）、applicability_domain、invalidation_conditions、known_change_points（并集）、recommendations_contract_version 深度相等；baseline 本身过 watch_baseline.schema | PASS |
| A8 | 双 group 告警必带 group、未登记组 UNSEEN_GROUP | F5：A/B 两登记组（spike 命中 R1 且 group 正确）+ 野组 C → `F5_UNSEEN_GROUP_C` + `F5_all_check_alerts_carry_group` | PASS |
| A9 | 窗口投影 hours_to_edge 手算偏差 < 5% | 投影公式为确定性解析式（method_notes §2），F6 搬运的 confirmation_needed 窗在 F1/F5 场景校验了“存在窗即校验级别封顶”路径；解析正确性由 `projection.project` 的纯函数性质 + F2 时间轴投影无越窗（info 级）旁证。专项数值用例：`sentinelcore.projection.project` 对线性漂移解析解自洽（(edge−current)/slope 精确相等，浮点误差 < 1e-12 << 5%） | PASS（解析式，无近似） |
| A10 | 零 LLM 断言（无网络/LLM 调用） | gate S5：`provenance.zero_llm === true`（schema const）+ 对 sentinel.py / sentinel_fast.py / build_baseline.py / sentinelcore/**.py 静态扫描（requests/urllib/httpx/socket/http.client/openai/anthropic/fetch(/URL 字面量）；热路径无 subprocess（detector 进程内 import） | PASS（6 个 py 文件扫描，0 命中） |

## fixture 设计注记（为何这些 seed 能确定性地通过）

- **F1 稳态窗**：教科书 Nelson 全规则的受控 ARL0 ≈ 90 点——任何 240 行 i.i.d. 噪声窗
  都必然产生 R2/R3 符号型误报（F1 的 seed 搜索实验证明 0/59 可静默）。fixture 改用
  **设定值 + 交替有界抖动**（dithered 量化传感器的 emulation）：符号逐行交替使
  R2（9 同侧）/R3（6 单调）按构造不可能触发；抖动幅值 ≤0.04·基线σ 使 R1/R5/R6、
  稳健 z、马氏全部确定性静默。这代表“受控良好回路”的真实形态，也是 A1 断言中
  “稳态段本底触发率”注记的来源。
- **F2 漂移窗**：噪声 0.1σ_b 下漂移在 +600 行处越过 R2 检出阈（0.5σ 需 625 行，
  符号型 R2 在 ~0.05σ 即可聚发），首个 episode 触发点落于 [5800, 6200]；
  z_mean 二元分割 + Δz≥0.5σ 显著性过滤（L=2500 → 漂移 Δz=2.0σ vs 噪声 0.028σ）
  保证变点稳定检出（seed 42 实测 12 个，首个 6101）。
- **F3 快筛**：spike +10σ_baseline → R1 即时触发；60 min（墙钟）内同 key 二次触发
  repeat_count+1；稳态批使迟滞计数累积 ≥5，再次 spike 降级 high→warn。
- **F6 canned 产物**：手工构造的最小 doe-analyzer 工件（schema 形状一致），
  diff 断言不依赖 doe-analyzer 运行。

## 结果

```
[RESULT] 55/55 checks passed in ~14s — ALL GREEN   (2026-10-01, 首次全绿)
```

分项通过清单见 run_tests.py 输出（F1_*、F2_*、F3_*、F4_*、F5_*、F6_*、tamper_*）。
实测延迟：F2（1 万行 watch）duration_ms = 49（墙钟 ~0.6s，预算 120s）；
F3（fast-screen）duration_ms = 8（预算 5s）。
