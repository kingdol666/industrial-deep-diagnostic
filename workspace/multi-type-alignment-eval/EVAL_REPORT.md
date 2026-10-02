# 多数据类型 × 多工况 时间对齐匹配分析实测报告（EVAL_REPORT）

- 日期：2026-10-01 · 主 seed：`20261001`（全部数据由 `gen_data.py` 固定种子生成，可复现）
- 工作目录：`workspace/multi-type-alignment-eval/`
- 纪律：全部使用已交付 skill 的**真实 CLI**（venv：`.claude/shared/scripts/.venv/Scripts/python.exe`）；**零源码修改**（唯一被定位的 P0 为功能性缺陷、非崩溃级，按评测纪律仅记录并用等价目标对照验证）；所有结论数字均摘自 skill 产出的 artifact JSON。
- 覆盖 skill：`industrial-doe-analyzer`（观测模式全反伪链）、`industrial-sentinel`（watch + baseline）、`industrial-tuning-memory`（action_log→归因→经验库→recommend 全链）、`industrial-optimizer-loop`（init→design→ingest→converge 闭环）。

---

## 1. 场景 × Skill 结果矩阵

| 场景 | 数据形态 / 真值 | 滞后恢复 | 成因命中 | 防伪降级正确性 | sentinel 对齐 | 闭环/收敛 |
|---|---|---|---|---|---|---|
| **S1** 单点×稳态 | 3 标量 1min×1200 行；`y=50+0.6·x1(t-4)+N(0,0.3)`，x2 无关 | ✅ `best_lag=-4`（参数超前 4 步），`best_lag_r=0.8909`，lag_window_consistent=true | ✅ x1 操作窗（OW-001，confirm_needed=true），x2 q=0.955 无信号 | ✅ x1 PASS（无趋势/离群/Simpson），x2 PASS | ⚠️ AR(1) 通道误报 29 条（见 F3）；SPC-off 对照 **0 告警 exit 0** ✅ | — |
| **S2** 单点×双工况 | 1200 行，row 600 切产品 P1→P2（水平阶跃 x1 10→16，y 50→44，层内同为 +0.6 耦合） | ⚠️ 混池 `best_lag=3` ✗（层间阶跃主导，近似平局由噪声决定）；**分层后两产品均 `best_lag=-4`，r=0.889** ✅ | ✅ PELT 变点恰在 row 600；层内真值配对存活 | ✅ 混池 (y,x1) full_r=**-0.814**（聚合错觉）→ Simpson DIRECTION_REVERSAL → **FAIL**；❌ x2（r=-0.003）遭伪 CAUTION（见 F4） | 未要求 | — |
| **S3** 向量×TD 剖面 | 21 位置 2min/扫描 ×400，过程 1min×810；pos_07 条纹 = 0.8·T3(t-10min)（=5 扫描步） | ✅ 未对齐帧 `best_lag=-5`（r 0→0.9861）；反推对齐 10min 后 `best_lag=0`，r=0.986 | ✅ zone 派生有效：dev_pos07↔T3 r=0.986、zone_L↔T3 r=0.940（稀释 7 倍仍检出）；melt/pull 全零信号 | ✅ 全 PASS，操作窗落在 T3 上 | ✅ REGIME_CHANGE_NEW 恰在真值行（watch-row 50 = 扫描 300） | — |
| **S4** 向量×光谱 | 64 bin × 600 帧（5min/帧）；bin10-20 整体偏移 = 0.35·(炉温(t-3帧)-1180)，炉温 350 帧 +6 阶跃 | ✅ `best_lag=-3`，`best_lag_r=0.9939` | ✅ band_mean↔furnace 唯一显著（q=0.0）；**stability 变点 = 353 帧，与真值逐帧一致** | ❌ stir_speed（r=0.059）伪 CAUTION（同 F4） | ✅ REGIME watch-row 57（真值 53，+4 行）+ ROBUST_Z 命中 band/furnace | — |
| **S5** 单点×漂移 | x1 真值滞后配对 + drift_a/drift_b 共趋势（y 含 0.002t 漂移） | ✅ x1 `best_lag=-4`，`best_lag_r=0.6498`（理论 0.63），PASS，q=0.0006 | ✅ 唯一操作窗给 x1；drift_a/b 进 watchlist | ✅ 共趋势判 **CAUTION**（非 FAIL 非 PASS）：raw r≈0.73 → 去趋势 r≈0.01，`TREND_CONFOUNDED_NO_WINDOW` 拒绝产窗 | 未要求 | — |
| **S1T** 调参动作（S1 滞后配对 + row700 设定 +1） | 动作 x1 50→51，效果 row704 起 +0.6 | ✅ 段放置正确：dead-time=4，基线 [666,696]（无效果泄漏），效果窗 [705,900] | ⚠️ estimable/E1，delta=+0.205，CI[-0.202,0.612] 跨 0 → direction_established=false（+1 步长下 SNR 不足，诚实降级；对照 S1T2 +2 步长：delta=**1.345**，CI[0.683,2.006] 盖住真值 1.2，方向 ✅） | ✅ 状态机未夸大 | — | gate 8/8 ✅；playbook_hit @regime，score=1.0 |
| **S6** 向量→闭环寻优 | 目标 dev_pos07（S3 pos_07 条纹），1 因子 die_bolt_T3_pct∈[0,10]，真值 `0.25·(T3-2)²+N(0,0.03)`（minimize→0） | — | — | — | — | ❌ 原始 minimize+tolerance：**exhausted**（R005，P0 bug，见 F1）；✅ 等价 target 对照（S6b）：**converged R008**，最终 T3=1.541，dev=0.0763∈[0,0.15]，D=0.982，O-G gate 16/16 |

---

## 2. 各场景实测命令与关键数字

### S1 单点×稳态（doe-analyzer + sentinel）
```bash
PY .claude/skills/industrial-doe-analyzer/scripts/analyze.py all --run-dir S1/run
PY .claude/skills/industrial-sentinel/scripts/build_baseline.py \
  --history-csv S1/s1_history.csv --time-col t --out S1/watch_baseline.json
PY .claude/skills/industrial-sentinel/scripts/sentinel.py watch \
  --data S1/s1_watch.csv --baseline S1/watch_baseline.json --time-col t --out-dir S1/sentinel_out
# 对照（关 SPC）: 同上 + --config S1/watch_config_nospc.json -> sentinel_out_nospc
```
- 相关对 (y,x1)：`r=0.0723`（零滞后）、`best_lag=-4`、`best_lag_r=0.8909`、verdict PASS、q=0.0244。(y,x2)：`r=-0.0016`、q=0.955。
- 符号约定验证：负值 = 参数超前（x1 提前 4 步驱动 y）✅。
- 操作窗 OW-001 x1∈[-1.358,1.223]，confidence=low，`confirmation_needed=true`（观测级契约，未越级）✅。
- sentinel：exit 1，29 条告警（x1 14 / y 11 / x2 4；规则 R1×5、R2×8、R3×10、R5×3、R6×3）。基线 σ：x1 `sigma_within_mr/sigma_overall=0.644`（lag1 自相关 0.552），R1 实际阈值 1.907（数据单位）→ 600 行中 37 点越限。SPC-off 对照：`status=ok alerts=0`。
- doe quality_gate：21/21 PASS；sentinel gate：6/6 PASS。

### S2 单点×双工况
```bash
PY analyze.py all --run-dir S2/run                    # 混池, ctx.group_col=product
PY analyze.py all --run-dir S2/run_p1                 # P1 切片
PY analyze.py all --run-dir S2/run_p2                 # P2 切片（需 mode_override, 见 F2）
```
- 混池 (y,x1)：`full_r=-0.8143`，Simpson paradox 判定（strata 均正、混池负）→ verdict **FAIL**，notes="Simpson paradox / direction reversal across strata"；stability PELT 变点 `[600]` ✅。
- 分层真值存活：P1 `best_lag=-4, r=0.8888`；P2（observational override 后）`best_lag=-4, r=0.8893`，均 PASS ✅。
- 混池 best_lag=3 ✗ —— 聚合阶跃使各滞后 |r| 几乎并列（≈-0.81），`find_best_lag` 在近似平局上由噪声决定（见 F6）。
- ❌ 副作用：x2（r=-0.0034，detrended_r=0.0275）被判 CAUTION "shared time trend"——纯噪声对的相对衰减率假阳性（F4）。
- 过程坑：P2 切片自动模式检测误判 `rsm_ccd`（F2），改 ctx `mode_override="observational"` 后正常；run_p2 首跑残留 designed 工件已被 override 重跑覆盖。

### S3 向量×TD 剖面（film-demo 反推对齐法）
```bash
PY s3_align.py --back-min 10 --out S3/run/00_input/data.csv    # 反推对齐（5 扫描步×2min）
PY s3_align.py --back-min 0  --out S3/run_unaligned/00_input/data.csv
PY analyze.py all --run-dir S3/run &  PY analyze.py all --run-dir S3/run_unaligned
```
- `s3_align`：400/400 精确邻匹配（merge_asof nearest，过程 1min 网格）。
- 未对齐帧 (dev_pos07,T3)：零滞后 r 仅 0.4639，`best_lag=-5, best_lag_r=0.9861`，lag_window_consistent=true ✅（滞后被 CCF 完整恢复）。
- 反推对齐帧：`best_lag=0, r=0.986` ✅（对齐吃掉整 5 步滞后）；zone_L↔T3 r=0.9396（21 位置条纹稀释到 7 位置均值后仍强检出）✅；decoy melt/pull q≥0.08 无信号 ✅。
- sentinel（基线=对齐帧前 250 行，watch=后 150 行）：`REGIME_CHANGE_NEW` 观测行恰为 watch-row **50**（=扫描 300=真值阶跃行）✅；另有 dev_pos07/zone_L/td_std R1/R5/R6 响应告警；但 melt/pull 两条 AR 通道产生 16 条阶跃前误报（同 F3）。

### S4 向量×光谱
```bash
PY analyze.py all --run-dir S4/run        # 派生帧: band_mean=mean(bin10..20), band_ref_mean=mean(bin45..55)
PY build_baseline.py --history-csv S4/s4_history.csv --time-col timestamp --out S4/watch_baseline.json
PY sentinel.py watch --data S4/s4_watch.csv --baseline S4/watch_baseline.json --time-col timestamp --out-dir S4/sentinel_out
```
- bin 派生有效：band_mean↔furnace `best_lag=-3`（真值 3 帧），`best_lag_r=0.9939`，q=0.0 ✅。
- stability 变点 `positions=[353]`——真值 band_mean 阶跃恰好发生在帧 353（炉温 350 + 滞后 3），**逐帧一致** ✅。
- ❌ stir_speed（r=0.0588）伪 CAUTION（F4）。
- sentinel：REGIME watch-row 57（真值 53，晚 4 行，quiet-zone/显著性过滤的代价）+ ROBUST_Z_OUTLIER 命中 band_mean/furnace_temp_C ✅；阶跃前 11 条 AR 误报（F3）。

### S5 单点×漂移混杂
```bash
PY analyze.py all --run-dir S5/run
```
- 真值存活：x1 `best_lag=-4, best_lag_r=0.6498`（理论 ≈0.63），PASS，q=0.0006，唯一操作窗给 x1（confirm_needed=true）✅。
- 共趋势正确降级：drift_a raw r=0.7335 → detrended r=0.011 → `trend_confounded=true` → **CAUTION**；drift_b raw r=0.7278 → detrended r=-0.0453 → CAUTION；两者均进 watchlist `TREND_CONFOUNDED_NO_WINDOW`（拒绝产出操作窗）✅ —— 陷阱相关性（raw r≈0.73）被去趋势链完整拆除。

### S1T / S1T2 调参经验全链（tuning-memory）
```bash
PY tune_stats.py attribute --run-dir S1T/run --metric y --time-col t --dead-time 4
node experience_build.mjs build --run-dir S1T/run
node match_playbook.mjs recommend --run-dir S1T/run     # 需 00_input/fault_signature.json
node quality_gate.mjs S1T/run --skill-path <skill> --shared-path <shared>
```
- 滞后场景段放置：`dead_time_used=4.0`，基线 [666,696]（在 row 704 效果起点之前，无泄漏），效果窗 [705,900]，truncated_by=null ✅。
- S1T（+1 步长，真效果 +0.6）：`estimable/E1`，delta=+0.2046，CI95 [-0.2024, 0.6116] 跨 0 → `direction_established=false`。评价：AR(1) 基线 n_eff=13 使单动作 ±0.6 效果的方向不可判——状态机**诚实降级**而非编造 ✅（但意味着该 SNR 下经验条目只有 observed 强度）。
- S1T2（+2 步长对照，真效果 +1.2）：delta=**1.3447**，CI [0.6833, 2.0060] 盖住真值，`direction_established=true`，方向为正 ✅。
- 经验库：`created exp_tuning_action_effect_P1|M1|R1_74c09763...`；recommend：`playbook_hit @regime`，score=1.0，grade E1，expected_effect 透传 delta/CI/方向标志，`autonomy_level=null`（v1.4 契约）✅。
- quality_gate：S1T 8/8、S1T2 8/8 PASS ✅。
- 过程坑（P2 级，见 F8/F9）：fault_signature 方向为**同向**语义；`ingest_meta.source` 必须取枚举 `api|csv_import|retro_mined`。

### S6 闭环寻优（optimizer-loop）
```bash
PY optimizer.py init --run-dir S6/run     # objective: goal=minimize, tolerance=0.15
PY optimizer.py design / ingest ...       # 试验结果由真值函数 0.25*(T3-2)^2+N(0,0.03) 生成（AWS 替身）
PY optimizer.py converge --run-dir S6b/run  # 对照: goal=target, target_range=[0,0.15]
node optimizer_gate.mjs <run> --skill-path <skill> --shared-path <shared>
```
- S6（题设 minimize→0）：R001 `lhs_fill`（x=2.041 试出 dev=0.0226，已在目标带内）→ 但 `max_EI≈e-31` 崩塌、`best_D=0.0` 恒零 → rsm_augment 围绕错误 incumbent（x=9.312，dev=13.36，**全域最差点**，却 `in_target:true`）→ R004 dup_ratio=0.33 → R005 dup_ratio=1.0 → **exhausted**。30 次试验、5 轮，正确区域从未被利用。
- 根因（P0，F1）：`optcore/objective.py metric_specs` 在 `goal=minimize ∧ tolerance` 时设置了 `usl`，于是 `_grid_hi`（归一化锚点）永不写入；`doestats/rsm.py d_individual` minimize 分支 `lo = grid_hi if grid_hi is not None else y` → `span = y - usl ≤ 0` → **所有点 D≡0**；`optimizer.py` incumbent 以 `d > best_d` 取最大，全零并列 → 取第一个试验点（最差区域），EI 以此为基准 → 永不改进 → stall→重复→exhausted。同区域 `in_target` 对非 target 目标无条件置 true（次要错误，同一处）。
- S6b（等价 target 对照，非侵入适配）：`goal=target, target_range=[0,0.15]` → exploring→exploiting→confirming（R004 首次 confirm 未过门→resume_exploit→R005/R007 补点→R008）**converged**；incumbent T3=1.541%，dev mean=0.0763（n=3, sd=0.019，in_target=true），D=0.982，`verification=verified`；converge 产出 recipe/conclusion/report/经验回写 4 类工件；gate 16/16 PASS ✅。GP/RSM/confirm 状态机本身工作正常。
- 两次 S6 gate 均 13/13 PASS —— O-G 门是**结构契约门**，对"incumbent 统计上荒谬"无感知（F7）。

---

## 3. Bug / 局限清单（P0/P1/P2）

### P0（功能性缺陷：目标无法收敛）
- **F1 optimizer-loop `goal=minimize`+`tolerance` 的期望度函数恒零**：`metric_specs`（`optcore/objective.py` L281-291）在 usl 已设时不写入 `_grid_hi`；`d_individual`（doe-analyzer `doestats/rsm.py` L75-84）minimize 分支失去归一化锚点后对所有 y≤usl 返回 0。后果链：D≡0 → incumbent=argmax 平局取首个试验（S6 中是全域最差点 x=9.31）→ `in_target` 无条件 true → EI≈0 → stall→duplication=1.0 → exhausted。**任何 minimize+tolerance 活动均无法收敛**（对照 S6b target 路径 8 轮收敛）。修复方向（一行级，未动源码）：`if spec["usl"] is None or goal == "minimize": spec["_grid_hi"] = ghi`。**本次未修复**（非崩溃级，按评测纪律记录）；已用 goal=target 等价目标完成收敛能力验证。

### P1（误判/误报，影响结论可信度）
- **F2 doe-analyzer 模式自动检测把纯连续观测噪声误判为 `rsm_ccd`（designed，grade A−）**：`_center_axial_counts` 用编码容差 0.05/0.12 数"中心点/轴点"，600 行高斯 AR(1) 噪声随机满足 `n_center≥2 ∧ n_axial≥4` 即判 CCD。S2 的 P2 切片中招（产出 designed 模型 + A− 结论），P1 切片未中招——同一生成器、不同抽样，检测**随抽样不稳定**。时间序列被套进"试验设计"证据框架属严重误置；需人工 `mode_override="observational"` 拉回。建议：time_col 存在且因子行间强自相关时跳过 RSM 分支。
- **F3 sentinel C1 Nelson 族在 1-min 自相关传感器上系统性误报**：σ 取 `MRbar/1.128`（短工序 σ），AR(1) φ≈0.55-0.6 时 ≈0.64×边际 σ → R1 有效阈值 ≈1.9σ_marginal。S1 静态窗 600 行 29 条告警（x1 14 条；真值完全平稳）；S3/S4 watch 各有 11-16 条阶跃前误报（集中在 AR 的 melt/pull/stir 通道）。iid 通道（x2）仅 4 条（ chance 水平）。SPC-off 对照 0 告警 → 误报全部来自 C1。产线 1 分钟级采样普遍自相关，建议 pre-whitening、或以 `sigma_overall` 为 R1 的备选 σ、或在 config 暴露 σ 选择。
- **F4 反伪链对近零 |r| 对产生随机伪判决（CAUTION）**：衰减率 `(raw-det)/|raw|` 以 |r| 为分母，|r|→0 时噪声主导。S2 x2（r=-0.0034，纯噪声）被判 CAUTION "shared time trend"；S4 stir（r=0.0588）同样中招；S1 x2（r=-0.0016）同分布却 PASS——判决随抽样翻转。建议 |r|<0.1 时反伪判决直接记 N/A。

### P2（可用性/语义/门盲区）
- **F5 滞后补偿对的证据分级按零滞后 raw r 评**：S1 (y,x1) `best_lag_r=0.891` 但 `evidence_level=L4`（门槛用 raw r=0.072<0.3）——滞后修正是观测模式的核心增值，却拿不到对应证据级别。
- **F6 聚合（混层）数据的 best_lag 不可靠且无降级标注**：S2 混池 `best_lag=3`（真值 4 步），近似平局由噪声决定；该帧同时被 Simpson FAIL 正确拦截，但 report 未对 best_lag 本身加"层间混杂，不可信"标注。
- **F7 optimizer O-G 门对 incumbent 统计荒谬无感知**：S6 全程 D=0、incumbent=最差点，gate 13/13 PASS。O-G1~O-G8 全为结构契约检查；建议补一条"incumbent-in_target 与 tolerance 的一致性"哨兵（同区域 `in_target` 对 minimize/maximize 无条件 true 是同一盲区）。
- **F8 tuning-memory fault_signature 方向为"同向"语义**：anomalous direction 必须与历史动作 from→to 方向**相同**才得分（`rec.direction === p.direction`）——语义是"当时参数也这样偏"；与"对策取反方向"的直觉相反（本评测首跑即因此 `fallback_generic`）。建议在 schema/文档标注。
- **F9 action_log 校验报错不披露合法枚举**：`bad ingest_meta.source eval_S1T` 不说合法值（`api|csv_import|retro_mined`）。
- **F10 sentinel REGIME_CHANGE_NEW 告警无 parameter 字段**（S3/S4 中 `parameter=None`），下游需自行关联是哪个通道的变点。

### 过程性观察（非缺陷）
- doe stability 的 PELT 变点两次精确命中（S2 row 600、S4 frame 353），sentinel C3 一次精确（S3）、一次 +4 行（S4）——变点类检查是四条链中对齐质量最高的。
- 经验条目 action_log_id 由内容哈希派生：修改 action_log 后必须重跑 tune_stats，否则 build 时 `SKIP ... no attribution report`（幂等设计正常工作，但链路顺序敏感）。

---

## 4. 修复声明

本次评测**未修改任何 skill 源码**（含 P0/F1：功能性缺陷、非崩溃级，按"发现 bug 记录不修"纪律处理，已用 goal=target 等价路径完成 S6 收敛能力对照）。评测自建文件：`gen_data.py`、`s3_align.py`、`s6_run_loop.py`、`s6b_run_target.py` 及各场景 run 目录。

## 5. 遗留问题

1. S6 题设 `minimize→0` 的收敛在 F1 修复前不可达——需要 skill 侧一行修复后重跑确认。
2. tuning-memory E2/E3（跨工况佐证晋升）与 ack 回执链未测（单动作场景只能到 E1）。
3. sentinel fast-screen（增量 1-500 行）模式未纳入本评测。
4. doe-analyzer `report.html` 渲染内容未做人工审读（仅 G7 gate 通过）。
5. S3 只验证了单区单条纹；多区条纹混叠下的 zone 派生分辨力未测。
