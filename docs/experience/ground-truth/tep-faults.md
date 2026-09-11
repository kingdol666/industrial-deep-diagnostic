# TEP 根因真值表与变量语义表

> 来源：Downs & Vogel 1993（TEP 原始论文）；Chiang, Russell & Braatz 2001《Fault Detection and Diagnosis in Industrial Systems》故障根因记载；变量表摘自 Braatz 组发行 README（UIUC, 1998-2002）。用途：① 外供本体层变量映射；② 根因评测真值（机理关键词 + LLM-judge 双评）。

## 1. 连续过程测量 XMEAS(1)–(22)

| # | 描述 | 单位 | # | 描述 | 单位 |
|---|---|---|---|---|---|
| 1 | A Feed (stream 1) | kscmh | 12 | Product Sep Level | % |
| 2 | D Feed (stream 2) | kg/hr | 13 | Product Sep Pressure | kPa gauge |
| 3 | E Feed (stream 3) | kg/hr | 14 | Product Sep Underflow (stream 10) | m³/hr |
| 4 | A and C Feed (stream 4) | kscmh | 15 | Stripper Level | % |
| 5 | Recycle Flow (stream 8) | kscmh | 16 | Stripper Pressure | kPa gauge |
| 6 | Reactor Feed Rate (stream 6) | kscmh | 17 | Stripper Underflow (stream 11) | m³/hr |
| 7 | Reactor Pressure | kPa gauge | 18 | Stripper Temperature | °C |
| 8 | Reactor Level | % | 19 | Stripper Steam Flow | kg/hr |
| 9 | Reactor Temperature | °C | 20 | Compressor Work | kW |
| 10 | Purge Rate (stream 9) | kscmh | 21 | Reactor Cooling Water Outlet Temp | °C |
| 11 | Product Sep Temp | °C | 22 | Separator Cooling Water Outlet Temp | °C |

## 2. 采样成分测量 XMEAS(23)–(41)（0.1h 采样，摩尔 %）

| # | 描述 | # | 描述 |
|---|---|---|---|
| 23 | Component A — Purge (stream 9) | 33 | Component D — Stream 6 |
| 24 | Component B — Purge (stream 9) | 34 | Component E — Stream 6 |
| 25 | Component C — Purge (stream 9) | 35 | Component F — Stream 6 |
| 26 | Component D — Purge (stream 9) | 36 | Component A — Stripper Underflow (stream 11) |
| 27 | Component E — Purge (stream 9) | 37 | Component B — Stream 11 |
| 28 | Component F — Purge (stream 9) | 38 | Component C — Stream 11 |
| 29 | Component G — Purge (stream 9) | 39 | Component D — Stream 11 |
| 30 | Component H — Purge (stream 9) | 40 | Component E — Stream 11 |
| 31 | Component A — Stream 6 | 41 | Component F — Stream 11 |
| 32 | Component B — Stream 6 | | |

## 3. 操纵变量 XMV(1)–(11)（数据文件 52 列布局含此 11 列）

| # | 描述 | # | 描述 |
|---|---|---|---|
| 1 | D Feed Flow (stream 2) | 7 | Separator Pot Liquid Flow (stream 10) |
| 2 | E Feed Flow (stream 3) | 8 | Stripper Liquid Product Flow (stream 11) |
| 3 | A Feed Flow (stream 1) | 9 | Stripper Steam Valve |
| 4 | A and C Feed Flow (stream 4) | 10 | Reactor Cooling Water Flow |
| 5 | Compressor Recycle Valve | 11 | Condenser Cooling Water Flow |
| 6 | Purge Valve (stream 9) | | （原表 XMV(12) Agitator Speed 不在 52 列数据内） |

## 4. 故障根因真值 IDV(1)–(21)

| IDV | 过程变量/根因 | 类型 | 可检测性 |
|---|---|---|---|
| 1 | A/C 进料比阶跃，B 成分不变（Stream 4） | Step | 可检 |
| 2 | B 成分阶跃，A/C 比不变（Stream 4） | Step | 可检 |
| 3 | D 进料温度阶跃（Stream 2） | Step | **极难检**（PCA 不可检） |
| 4 | 反应器冷却水入口温度阶跃 | Step | 可检 |
| 5 | 冷凝器冷却水入口温度阶跃 | Step | 可检 |
| 6 | A 进料损失（Stream 1） | Step | 可检 |
| 7 | C 集管压力损失、可用性下降（Stream 4） | Step | 可检 |
| 8 | A、B、C 进料成分随机波动（Stream 4） | Random | 可检 |
| 9 | D 进料温度随机波动（Stream 2） | Random | **极难检** |
| 10 | C 进料温度随机波动（Stream 4） | Random | 可检 |
| 11 | 反应器冷却水入口温度随机波动 | Random | 可检 |
| 12 | 冷凝器冷却水入口温度随机波动 | Random | 可检 |
| 13 | D 进料压力慢漂移（Stream 2） | Slow drift | 可检（难定位） |
| 14 | 反应器冷却水阀粘滞（sticking） | Valve sticking | 可检 |
| 15 | 冷凝器冷却水阀粘滞（sticking） | Valve sticking | **极难检** |
| 16–20 | **官方标注 Unknown（无根因真值）** | Unknown | 16 可检；其余难 |
| 21 | Stream 4 阀门固定在稳态位置 | Constant position | 可检 |

**评测约定**：
- 根因评测集 = IDV 1–15 + 21（16 类）；IDV 16–20 只参与检测评测，不参与根因评分；
- IDV 3/9/15 单列"难检集"：输出 COMPETING_SET/NEEDS_DATA 记为校准正确，只有"DETERMINED + 错误根因"记失败；
- 有文献记载完整根因的 15 类 = IDV 1–15（与 FaultExplainer 论文口径一致）。

## 5. 根因匹配关键词建议（双评之"机理关键词"一侧）

| IDV | 匹配关键词（英/中） |
|---|---|
| 1 | A/C feed ratio, stream 4 composition, A/C 进料比 |
| 2 | B composition, stream 4, B 成分 |
| 3 | D feed temperature, D 进料温度 |
| 4 | reactor cooling water, inlet temperature, 反应器冷却水 |
| 5 | condenser cooling water, 冷凝器冷却水 |
| 6 | A feed loss, stream 1, A 进料损失 |
| 7 | C header pressure, C 集管压力 |
| 8 | feed composition random, A/B/C 成分波动 |
| 9–12 | 对应温度随机波动（random variation） |
| 13 | D feed pressure, D 进料压力漂移 |
| 14 | reactor cooling water valve sticking, 阀粘滞 |
| 15 | condenser cooling water valve sticking, 阀粘滞 |
| 21 | stream 4 valve fixed, 阀位恒定 |

> LLM-judge 侧：把本表 §4 的根因行作为参考答案，让 judge 模型对 `diagnosis.json` 的结论打"同根因/相关/错误"三档；与关键词侧不一致的样本人工仲裁。
