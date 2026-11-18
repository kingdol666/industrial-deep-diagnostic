# 产线哨兵巡检报告（watch 模式）

- **生成时间**：2026-10-14T03:35:46.382452+00:00
- **总体状态**：**alert** · 告警数 **25**
- **数据**：`D:\codes\myskills\industrial-deep-diagnostic\workspace\bopet-skill-eval\S3_sentinel_tdo_watch\00_input\tdo_watch_5d.csv`（120 行；时间列 时间；分组列 -）
- **基线**：模式：prior（v1.0.0），路径：D:\codes\myskills\industrial-deep-diagnostic\workspace\bopet-skill-eval\S3_sentinel_tdo_watch\baselines\watch_baseline.json
- **耗时**：13 ms（零 LLM / 零网络，全部统计由确定性脚本计算）


## 一、告警清单

| # | 级别 | 规则 | 参数/指标 | 分组 | 位置 | 观测值 | 建议 |
|---|------|------|-----------|------|------|--------|------|
| 1 | high | ROBUST_Z_OUTLIER | TDO定型区温度CX6 | __ALL__ | 64 | 196.2 | TDO定型区温度CX6 稳健 z 分数 \|4.21\| 超过 3.5，疑似离群点，请核对该行原始记录 |
| 2 | high | NELSON_R1 | TDO定型区温度CX6 | __ALL__ | 22 | 194 | TDO定型区温度CX6 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 3 | high | NELSON_R1 | TDO定型区温度CX6 | __ALL__ | 119 | 197.8 | TDO定型区温度CX6 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 4 | high | NELSON_R1 | TDO拉伸区温度CX4 | __ALL__ | 11 | 237.9 | TDO拉伸区温度CX4 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 5 | high | NELSON_R1 | 熔体压力 | __ALL__ | 54 | 114.3 | 熔体压力 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 6 | high | NELSON_R1 | 纵拉预热辊温 | __ALL__ | 105 | 76.66 | 纵拉预热辊温 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 7 | high | NELSON_R1 | 铸片辊温度 | __ALL__ | 48 | 25.73 | 铸片辊温度 出现超过 3σ 的单点突变，请核对传感器量程与该时刻的工况记录 |
| 8 | high | NELSON_R5 | TDO定型区温度CX6 | __ALL__ | 27 | 192.2 | TDO定型区温度CX6 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 9 | high | NELSON_R5 | TDO定型区温度CX6 | __ALL__ | 119 | 197.8 | TDO定型区温度CX6 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 10 | high | NELSON_R5 | TDO拉伸区温度CX4 | __ALL__ | 19 | 240.8 | TDO拉伸区温度CX4 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 11 | high | NELSON_R5 | TDO拉伸区温度CX4 | __ALL__ | 108 | 241.7 | TDO拉伸区温度CX4 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 12 | high | NELSON_R5 | 牵引入口张力 | __ALL__ | 39 | 2209 | 牵引入口张力 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 13 | high | NELSON_R5 | 纵拉预热辊温 | __ALL__ | 106 | 77.66 | 纵拉预热辊温 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 14 | high | NELSON_R5 | 铸片辊温度 | __ALL__ | 30 | 26.17 | 铸片辊温度 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 15 | high | NELSON_R5 | 铸片辊温度 | __ALL__ | 119 | 27.44 | 铸片辊温度 短窗口内多点超出 2σ，波动加剧，建议检查控制回路与扰动源 |
| 16 | high | NELSON_R6 | TDO定型区温度CX6 | __ALL__ | 7 | 191.8 | TDO定型区温度CX6 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 17 | high | NELSON_R6 | TDO定型区温度CX6 | __ALL__ | 119 | 197.8 | TDO定型区温度CX6 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 18 | high | NELSON_R6 | 熔体压力 | __ALL__ | 114 | 108.3 | 熔体压力 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 19 | high | NELSON_R6 | 牵引入口张力 | __ALL__ | 11 | 2253 | 牵引入口张力 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 20 | high | NELSON_R6 | 纵拉预热辊温 | __ALL__ | 68 | 78.49 | 纵拉预热辊温 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 21 | high | NELSON_R6 | 铸片辊温度 | __ALL__ | 51 | 26.22 | 铸片辊温度 窗口内多点超出 1σ 同侧，离散度升高，建议关注 |
| 22 | warn | VARIANCE_RATIO_HIGH | TDO定型区温度CX6 | __ALL__ | - | 2.25 | TDO定型区温度CX6 稳态段标准差为基线的 2.8 倍，离散度显著升高，建议检查波动来源 |
| 23 | warn | NELSON_R2 | TDO定型区温度CX6 | __ALL__ | 21 | 192.8 | TDO定型区温度CX6 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 24 | warn | NELSON_R2 | 牵引入口张力 | __ALL__ | 64 | 2286 | 牵引入口张力 连续多点偏离中心线同一侧，存在均值漂移趋势，建议检查上下游工况 |
| 25 | warn | NELSON_R3 | 熔体压力 | __ALL__ | 66 | 108.8 | 熔体压力 连续单调上升/下降，存在趋势性漂移，建议排查慢变量（结垢、磨损、环境温度） |


> 级别语义：`info` 记录级 / `warn` 趋势与待确认趋势 / `high` 统计异常 / `critical` 越规格。
> 本系统为纯分析系统：所有告警仅为建议核查项，不下发任何参数，动作决策由产线（AWS 侧）做出。

## 二、稳态映射（C3）

- **__ALL__**：steady=120

## 三、操作窗口投影（C2）

- **C2 漂移投影未启用**：基线中无 operating_windows —— 构建基线时传入 --doe-run-dir 注册 DOE 先验操作窗即可启用（C2 drift projection disabled: no operating_windows in baseline (build with --doe-run-dir to enable)）

## 四、防风暴抑制

合并触发 15 组同 key 重复；静默期 30 行；同类抑制窗口 60 分钟；迟滞 5 点

## 五、告警事件摘要（incidents）

| 事件 | 参数 | 类别 | 峰值级别 | 跨度(行) | 告警数 | 规则 |
|------|------|------|----------|----------|--------|------|
| EVT-20261014033546-002 | TDO定型区温度CX6 | spc | high | 112 | 7 | NELSON_R6、NELSON_R2、NELSON_R1… |
| EVT-20261014033546-005 | 铸片辊温度 | spc | high | 89 | 4 | NELSON_R5、NELSON_R1、NELSON_R6 |
| EVT-20261014033546-003 | TDO拉伸区温度CX4 | spc | high | 97 | 3 | NELSON_R1、NELSON_R5 |
| EVT-20261014033546-004 | 牵引入口张力 | spc | high | 53 | 3 | NELSON_R6、NELSON_R5、NELSON_R2 |
| EVT-20261014033546-006 | 熔体压力 | spc | high | 60 | 3 | NELSON_R1、NELSON_R3、NELSON_R6 |
| EVT-20261014033546-008 | 纵拉预热辊温 | spc | high | 38 | 3 | NELSON_R6、NELSON_R1、NELSON_R5 |
| EVT-20261014033546-007 | TDO定型区温度CX6 | multivariate | high | 0 | 1 | ROBUST_Z_OUTLIER |
| EVT-20261014033546-001 | TDO定型区温度CX6 | regime | warn | 0 | 1 | VARIANCE_RATIO_HIGH |

## 六、建议后续动作

- 有 `high`/`critical` 告警：按告警中的 `suggested_check` 现场核查；需要根因分析时转 `industrial-diagnostician`，需要参数窗口/工况数据分析时转 `industrial-doe-analyzer`。
- 事件摘要按峰值级别与告警数排序；完整逐段告警在 alert.json 的 `alerts` 数组（契约不变），事件视图在 `events` 数组。
- 本报告由脚本生成（`authored_by: script`）；代理只允许追加中文 `interpretation` 注记，禁止改动任何数值字段。
