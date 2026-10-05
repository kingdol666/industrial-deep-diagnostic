# fieldtest-20261004 批改成绩单（scorecard.md）

- 批改人：出题人（Examiner）续任 Grader。批改依据：`truth/T1_truth.md … T5_truth.json`、出题人 dry-run 实测记录、测试者产物（`results/`）逐一复核。
- 测试者纪律核查：`truth/` 未读（简报与台账无真值痕迹）；全部走真实 CLI（venv python / node）；仅写 `results/`（T1 的自查脚本也放在 `results/T1/` 内，cases/ 未被改动）；台账逐条含退出码。**纪律全部满足。**
- 复核方式： tester 报告的每个关键数字均与其落盘产物（alert.json / attribution json / conclusion / effect_table / preprocessing_report 等）以及出题人 dry-run 逐项比对。T4 的 incumbent 与 confirm 重复测量值与出题人 dry-run **逐字节一致**（objective seed 42 + 确定性 plant），构成强复现性证据。

## 一、总览

| 用例 | 测试者自判 | 批改判定 | 关键数字复核 |
|---|---|---|---|
| T1 数据接驳箱 | PASS | **PASS** | 全部正确（2 处笔误级偏差，见下） |
| T2 产线常驻监控 | PASS | **PASS** | 全部逐字正确 |
| T3 调参归因与经验检索 | PASS | **PASS** | 全部逐字正确 |
| T4 闭环小试寻优 | PASS | **PASS（附设计层发现）** | 全部逐字正确；收敛点偏离真最优点属契约内行为，另见第三节 |
| T5 DOE 设计分析 | PASS | **PASS** | 全部逐字正确；tester 额外发现的 model_spec 粗糙点经查证属实 |

**总体：5/5 PASS，测试者自判与批改一致，无一处需要改判的关键数字。**

## 二、逐用例批改

### T1 — data-preprocessor 目录模式（PASS）

对照 truth/T1_truth.md §1–§3 逐项核对：

| 批改点 | 测试者报告 | 判定 |
|---|---|---|
| 8 文件格式识别（GBK/分号/TAB/JSON/MD 表/HTML 表/xlsx） | 全部识别正确（`file` 命令 + 逐文件 dump） | ✅ |
| 逐文件行列数 | 301×7 / 200×5 / 180×4 / 90×4 / 120×5 / 25×5 / 150×4 / 40×4 | ✅ 与 report tables[] 一致 |
| 注入缺陷 ①sensor_log 重复行 | 行 152/302 整行重复、10:30:00 重复时间戳对 | ✅（=truth 数据行 idx 150/299） |
| 注入缺陷 ②qa_lab 3 缺失 | 行 39/90/123 | ✅（=idx 37/88/121） |
| 注入缺陷 ③batch_records 空值 | B0058 moisture_pct=null（idx 57） | ✅ |
| 注入缺陷 ④dcs 离群 | 温度 999.9@行53、转速 −3.2@行123 | ✅ |
| 统一视图 | 301×18、时间列 batch_time、outer merge 4 文件、缺失 27.41% 正确定性为结构性稀疏 | ✅ |
| 逐列覆盖率自查 | dcs 181/301、process 201/301、batch 120/301（moisture 119）、sensor 301/301 | ✅ 精确（含 10:30 重复键扩展 +1 行的推导） |
| 999.9/−3.2 与重复行透传未标记 | 明确指出，并 grep 证实脚本无哨兵值/离群逻辑 | ✅（诚实披露，见第四节第 5 条） |

**偏差（不改判，仅记录）**：
1. 台账第 2 行把 stdout 摘要转写为 "selected=sensor_log.csv (301×7, time=timestamp)"——实际 stdout 打印的是 `selected_table`（301×**18**、time=**batch_time**）。其"粗糙点②（stdout 与 tables 列数不一致）"实质成立（stdout=合并视图 18 列 vs tables[]=原始 7 列），但台账转写本身有误；真正的内部不一致是其"粗糙点①"（report 内同文件双义），该点完全正确。
2. 未合并文件的排除机制推断部分失准：heater/downtime "零时间重叠"正确（时间轴确实不相交）；但 `operator_notes.md` 实际卡在 **<100 行合并门槛**（根本未进入重叠检验），其"重叠约 13%<30%"属过度推断。qa_lab"无时间列"正确。report 不写排除原因（其粗糙点③）属实。

### T2 — industrial-sentinel（PASS，满分）

退出码矩阵 **0 / 0 / 1 / 1 / 1 / 2 / 0,0** 与 truth §2 完全一致；告警集合逐条一致（fast_drift 7 条全在 speed_rpm；watch_cp 3 条：ROBUST_Z high n=113 + REGIME_CHANGE_NEW cp=121 + VARIANCE_RATIO 34.7975；watch_drift 9 条含 WINDOW_DRIFT_PROJECTION high，slope=3.605815555555561、**hours_to_edge=3.4438713818479867**、direction=up、current=1262.582）。两处加分项：① 正确解读变点窗中 speed_rpm 投影为 info 级（5228h）"判定合理"而非误报为告警；② exit 2 契约同时引用了 sentinel_fast.py docstring（L15-21 原文）与 SKILL.md Failure Recovery 原文，恢复路径（先 build_baseline）表述准确。DOE 先验操作窗 [1225,1275] 逐字段注册进 baseline 经落盘核实。gate 6/6 ×2 属实。

### T3 — industrial-tuning-memory（PASS，满分）

归因三条与 truth §2 逐字一致（1.9928553333333525 / [1.430640409110767, 2.555070257555938] / 0.154487999999958 / [−0.21925685660480254, 0.5282328566047185] / not_estimable+min_points+effect=null）；**正确区分了"CI 跨 0 → direction_established=false（状态仍是 estimable）"与 direction_uncertain 枚举**（契约语义无误读）；A3 诚实空值 + "honest nulls" 原话；build created×2 + SKIP(准入规则) + store=4；playbook_hit @regime、命中 `exp_fault_control_recipe_PVC-M|ca_2adda6ae0dd13c21`、score=1、degradation_path 逐字；回填 corroboration 1→2、E1→E2、observation→verified，且 jsonl 与 state.json 双证一致（落盘核实）；复检 recommend 后 gate 8/8。全链无瑕疵。

### T4 — industrial-optimizer-loop × 黑箱产线（PASS，附设计层发现）

phase 链、method 序列（lhs_fill 8 → rsm_augment 8 → confirm_replicates 1×3）、EI 数值、incumbent（72.039091 / 0.28382 / 0.408538）、confirm 值 [0.480971, 0.460278, 0.440862]、achieved mean=0.4607 sd=0.0201 单侧 CI [0.4269, 0.4945]、dual_gate 三项 true、D=1=D_max、gate 16/16 —— 与出题人 dry-run **逐字一致**；预算 3/6 轮、17/24 trials 有界。**收敛点偏离真最优（78.5, 0.42）的契约判定见第三节。** 测试者未注意到的一点：`optimization_conclusion.json` 已给出 `stationary_point` coded [0.0483, −0.1910]（解码 ≈ T 78.4 degC / C 0.424）、classification=**min**、inside_box=**true** —— RSM 模型实际已基本复原真最优点，但配方仍落在 incumbent（详见第三节）。guardrails/usage_rules 的 advisory 声明齐全，全程无参数下发。

### T5 — industrial-doe-analyzer designed 模式（PASS）

设计识别（full_factorial + center_points=4、12 runs、center-stripping 注记）、效应/df（df_resid=4、df_pure_error=3、LOF p=0.8265）、三个显著项系数与 BH q（+4.059375/6.44e-5、−3.220625/8.09e-5、+1.741625/6.11e-4）、不显著项（C 0.6579、T² 0.7784、A×C 0.1211、B×C 0.7256）、方向（升 ET / 降 DR / CR 不动）、OW-001 [2, 3.75] 与 OW-002 [185, 195]（含 extrapolation=true 诚实标记）、setpoints raw (195, 2, 25) D=1、gate 21/21 —— 全部与 truth 及落盘产物一致。**tester 的粗糙点发现经查证属实**：`effect_table.json.model_spec` 声明 10 项（含 Draw_Ratio^2、Cooling_Rate^2、三阶交互），实际仅估计 7 项，未估项无 reason_code（pooled_terms=[]）。

## 三、T4 专项判定：达标即收敛 vs 偏离真最优

**事实**：黑箱真最优 (T*=78.5, C*=0.42, impurity_min=0.35)；收敛配方 (72.04, 0.284) 确认批均值 0.4607 ≤ tolerance 0.55，dual gate 全过。配方距真最优还有 Δ≈0.11（占 tolerance 带宽 [0.35, 0.55] 的 55%）。

**契约判定：测试者与工具行为均正确，属"by design"。**
1. 冻结收敛门槛是**达标门**而非**全局最优门**：m≥3 重复全落 target 窗（minimize ⇒ impurity ≤ tolerance）∧ 单侧 95% CI 在限 ∧ D≥0.8·D_max。三项均客观满足；OG4 检查的正是这条冻结门，16/16 无放水。
2. 进入 confirming 的触发（candidate in window ∧ EI<ε 或 stall≥2）是文档化状态机；EI 塌缩（1.63e-6 < ε=0.0032）后确认 incumbent 是既定路径；`convergence_mode` 字段本身标注"reserved for future relaxation"——门槛放松属用户决策，脚本未越权。
3. 双门槛的三个子项都对"配方可信"负责（重复落在窗内、CI 在限、期望合意），不对"是否还有更优点"负责。

**但暴露三个真实的设计弱点（建议立项）**：
- **W1（最重要）**：`converge` 已计算并落盘 `stationary_point`（分类 min、in-box、预测更优），却仍按 incumbent 出配方——缺少"在驻点处加一轮确认"或至少 `verification_status` 注记 `in_tolerance_off_optimum` 的机制。本例 RSM 二次面已复原真最优（误差 <0.15 degC / <0.004），信息是现成的。
- **W2**：D 以**观测值域**归一，incumbent 必然 D=1=D_max——desirability 门在 incumbent 处不具判别力（恒真项）。
- **W3**：EI 的 ε 与 D_span 挂钩，模型局部自信时 ε 塌缩会提前触发 confirming（本例 R2 后即触发）。

## 四、粗糙点清单（tester 报告 + 出题人 dry-run 合并，去重后 9 条）

| # | 粗糙点 | 来源 | 影响 |
|---|---|---|---|
| 1 | **sentinel `_io.hours_axis` 在 pandas 3.0.5 下的时间单位 bug**：ISO 字符串解析为 datetime64[us] → 小时轴缩小 1000×（slope 虚大 1000×、hours_to_edge 虚小）；epoch 秒整数路径 → 1e9× 误差。仅纳秒分数位时间戳（`.fffffffff`）正确。本测试数据已用 ns 分数位规避 | 出题人 dry-run | 高：任何 pandas≥3 部署下 C2 投影数值失真 |
| 2 | **C2 投影隐性依赖 `--doe-run-dir`**：基线无 `operating_windows` 时 watch 静默失去 C2 覆盖，无任何提示 | 出题人 dry-run | 中：漏配 DOE 先验 = 漂移投影失效而用户无感 |
| 3 | **tuning-memory 缺省 `--settle-steps=200` 在密集动作日志下截断除最后一条外所有动作的效果窗**（→ truncated/E0）；需要显式工艺知识（本测试简报钉死 30） | 出题人 dry-run | 中：默认参数下归因结论系统性 degraded |
| 4 | **doe-analyzer model_spec 声明 10 项、仅估 7 项、未估项无 reason_code**（Draw_Ratio^2 / Cooling_Rate^2 / 三阶交互） | tester 发现，批改核实 | 低：产物不自解释（df 预算可推断） |
| 5 | **data-preprocessor 对哨兵值/重复行零标记**：999.9 与 −3.2 原样进入统一视图，重复时间戳行也未去重或提示（"downstream cleaning handles them"契约成立，但连 warning 都没有） | tester + 出题人 | 中：接驳箱场景下坏值会无声流入下游 |
| 6 | T1 report 内部 `n_cols` 双义（selected_table=合并视图 18 vs tables[]=原始 7，同名同文件）；且 `merge.key` 报 primary 的时间列名（timestamp）而实际 join 键是基表（batch_records）的 `batch_time` | tester(①) + 出题人 | 低：展示层不一致 |
| 7 | preprocessor 不输出未合并文件的排除原因（tester 独立推断时把 operator_notes 的 <100 行门槛误推为重叠率不足） | tester | 低：可推断但易推错 |
| 8 | optimizer D 值按观测值域归一 → incumbent 恒 D=D_max，desirability 门不具判别力；confirm 轮恒锚定 incumbent（见第三节 W1/W2/W3） | 出题人复核 | 中高：达标即收敛，可能停留在带内次优点 |
| 9 | venv 缺 lxml/bs4/html5lib：`pd.read_html` 不可用（tester 用 stdlib HTMLParser 自救 exit 0；预处理器自身用内置 regex 抽取器不受影响） | tester | 低：环境完备性问题，已自愈 |

## 五、最佳实践符合性表（设计是否符合该场景最佳实践）

| 功能 | 符合项（有证据） | 偏离/风险项 | 结论 |
|---|---|---|---|
| **industrial-sentinel** | 退出码语义诚实（0/1/2/3 与 docstring 一致，exit 2 拒跑不产 alert）；防告警风暴三件套在产物中可见（suppression/hysteresis/quiet-zone，watch_cp 仅 3 条告警即为静默区+稳态过滤效果）；投影语义方向感知、confirmation_needed 封顶、severity 分档（3.44h→high）正确；DOE 先验逐字段搬运可 diff；gate 6/6 | hours_axis pandas3 单位 bug（粗糙点1）；无 operating_windows 时 C2 静默失效（粗糙点2） | **符合**，附 1 个环境级正确性风险 |
| **industrial-optimizer-loop** | 轮次有界（3/6、17/24）；纯分析（recipe=advisory+usage_rules，无 autonomy/下发字段，全程未代执行试验）；gate 16/16 且 OG4 严格按冻结双门槛；失散保护（dup_ratio、OG2 越域、OG5 安全限）；经验回写仅本地文件 | 达标即收敛 + 驻点信息弃用 + D 不具判别力（粗糙点8/第三节） | **符合**，收敛语义建议增强 |
| **industrial-tuning-memory** | 诚实空值（not_estimable→effect=null，"honest nulls"）；准入规则拒收 not_estimable；chunk 幂等（ts8+sha 派生可复现）；证据晋升只由计数+CI 驱动（E1→E2/verified），无 LLM 参与；kb_summary 仅本地交接 | 缺省 settle-steps 在密集动作日志下系统性截断（粗糙点3）；ack 执行回执链本场景未覆盖（trigger=manual，属场景选择非缺陷） | **符合** |
| **industrial-doe-analyzer** | BH-FDR 多重检验；纯误差/LOF/失拟披露；窗口带 extrapolation 诚实标记；驻点鞍点告警进 watchlist；designed 模式无因果越权（observational 模式的 confirmation_needed 硬门在本模式不适用，属正确分流）；gate 21/21 | model_spec 与实估项数不一致且无 reason_code（粗糙点4） | **符合** |
| **industrial-data-preprocessor** | 8/8 格式覆盖（含 GBK/分号/MD/HTML）；源文件只读（未改动）；**无静默数据丢失**（0 skipped、全部行列保留、非表内容进 context 的机制存在）；合并有防膨胀门；幂等 | 质量问题只透传不告警（哨兵值/重复行，粗糙点5）；展示层双义与排除原因缺失（粗糙点6/7） | **基本符合**；建议补质量告警层 |

## 六、总体结论

**5/5 PASS。** 测试者在完全盲态下：所有关键数字（退出码矩阵、告警类型/级别/参数、投影 slope/hours_to_edge、归因状态/delta/CI、佐证晋升、incumbent/dual gate/gate 16 项、效应/q 值/显著性/操作窗、逐文件格式与全部 4 处注入缺陷）与真值一致，多处逐字级吻合；T4 全链与出题人 dry-run 确定性复现。台账与中文报告达到"可审计"标准。发现的 9 条粗糙点中没有一条属于测试者操作错误；2 处笔误级偏差（T1 stdout 转写、operator_notes 排除机制推断）不影响任何判定。

## 七、Top-5 修复建议（按优先级）

1. **修复 sentinel `hours_axis` 的 datetime 单位处理**（粗糙点1）：先统一 `.astype("datetime64[ns]")` 再取 int64，或直接用 `series.view("int64")` 前断言 unit；补一条 pandas 3.x 回归测试。这是唯一会导致**数值错误**（而非仅体验）的缺陷。
2. **optimizer-loop 收敛语义增强**（第三节 W1–W3）：converge 时若 `stationary_point` 分类为符合 goal 的极值且 in-box、预测响应优于 incumbent 超出噪声（如 >2×confirm sd），要求在驻点补一轮 confirm_replicates 方可 converged，或在 recipe/verification_status 标注 `in_tolerance_off_optimum` + needs_review；同时把 D 门在 incumbent 处的恒真问题（按观测值域归一）改为绝对达标带判据。
3. **sentinel 对 C2 覆盖缺失显式化**（粗糙点2）：基线无 `operating_windows` 时在 watch_report/alert 中发 info 级提示（"未注册操作窗，C2 投影未启用，请补 DOE 先验"），并写入 SKILL.md Failure Recovery。
4. **tuning-memory 归因前置检查**（粗糙点3）：attribute 时若动作密集（下一动作落在缺省 settle 窗内）则在 stdout 摘要与报告中显式提示"建议提供 settle-steps 工艺值，当前按 200 步截断"，避免默认参数下的系统性 truncated/E0。
5. **preprocessor 质量告警层 + 展示层一致性**（粗糙点5/6/7）：preprocessing_report 增加逐源 `quality_flags`（重复时间戳/重复行、|z|>阈值或物理不可能值、缺失计数），并在 merge 信息中写明实际 join 键与每个未合并文件的排除原因；同文件 selected_table 与 tables[] 的 n_cols 语义需命名区分。doe-analyzer 一并处理：model_spec 未估项补 `reason_code`（粗糙点4）。
