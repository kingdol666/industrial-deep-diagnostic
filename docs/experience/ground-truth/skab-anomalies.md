# SKAB 根因真值表

> 来源：SKAB 官方仓库 `waico/skab` `data/README.md`（每个文件一种人工注入异常）。每文件明细（行数/异常点数/首个异常时间戳）见 `data/benchmark/prepared/skab/ground_truth.json`。

## 试验台

Skoltech 水循环试验台：水箱 + 离心泵 + 阀门闭环回路。8 传感器 @1Hz：

| 列 | 含义 | 单位 |
|---|---|---|
| datetime | 时间戳 | YYYY-MM-DD hh:mm:ss |
| Accelerometer1RMS / Accelerometer2RMS | 振动加速度 RMS（泵/电机侧） | g |
| Current | 电机电流 | A |
| Pressure | 泵后回路压力 | Bar |
| Temperature | 电机本体温度 | ℃ |
| Thermocouple | 回路流体温度 | ℃ |
| Voltage | 电机电压 | V |
| Volume Flow RateRMS | 回路流量 | L/min |
| anomaly / changepoint | 标签列（prepared 版已剥离） | 0.0/1.0 |

## 文件夹级根因真值（评测以此为准）

| 文件 | 根因（人工注入） | 物理机制要点 | 诊断信号预期 |
|---|---|---|---|
| `valve1_0…15.csv`（16 文件） | **泵入口流量阀关闭**（closing the valve at the flow inlet to pump） | 入口节流→泵入口压降/气蚀倾向→流量降、振动升、可能电流波动 | Pressure↓ / Flow↓ 联动 + Accelerometer 抖动 |
| `valve2_0…3.csv`（4 文件） | **泵出口阀关闭**（closing the valve at the outlet of the flow from the pump） | 出口节流→泵后压力升高、流量受抑 | Pressure↑ / Flow↓，电流变化 |
| `other_1…4.csv` | **流体泄漏/添加模拟**（fluid leaks and additions） | 回路质量平衡被破坏 | 流量/压力缓变，振动与电流相对平稳 |
| `other_5.csv` | 转子不平衡·**尖锐**行为 | 转子动力学失衡 | Accelerometer1/2 主信号，1×转速频率 |
| `other_6.csv` | 转子不平衡·**线性**增长 | 同上（渐变） | 振动趋势缓升 |
| `other_7.csv` | 转子不平衡·**阶跃** | 同上 | 振动台阶跳变 |
| `other_8.csv` | 转子不平衡·**Dirac 冲激** | 同上 | 振动单点尖峰 |
| `other_9.csv` | 转子不平衡·**指数** | 同上 | 振动指数演化 |
| `other_10.csv` | **回路水量缓慢增加** | 容积/惯性变化→流量-压力慢漂移 | 缓变趋势 + 电压/电流轻响应 |
| `other_11.csv` | **回路水量突然增加** | 同上（突变） | 快速趋势转折（变点） |
| `other_12.csv` | **排水至气蚀**（draining until cavitation） | 液位下降→泵入口汽化→压力脉动、振动噪声 | Pressure 剧烈波动 + 振动宽带 |
| `other_13.csv` | **泵入口两相流→气蚀**（two-phase flow supply） | 汽蚀空泡溃灭 | 同上（与 12 区分：来源不同） |
| `other_14.csv` | **高温供水**（water of increased temperature） | 流体温度升→热平衡/汽化压力变化 | Thermocouple↑ 主导 |
| `anomaly-free.csv` | **正常工况**（baseline） | — | 误报率评测用（negative control） |

## 标签覆盖说明（重要）

- **标签列值是浮点格式** `1.0`/`0.0`（不是 `1`/`0`），解析评测时注意；
- 实测 34/35 文件有异常标注，共 **13,067 个异常点**；个别文件无标注时段但文件夹级故障类型不变 —— **根因评测以本表文件夹级真值为准，点级标签只用于 ADD（检测延迟）评分**；
- `anomaly` 标记异常点，`changepoint` 标记集体异常起点。

## 诊断请求建议 process_description

> 水循环试验台：水箱+离心泵+阀门回路。列含义：Accelerometer1RMS/Accelerometer2RMS=振动加速度RMS(g)，Current=电机电流(A)，Pressure=泵后回路压力(Bar)，Temperature=电机本体温度(℃)，Thermocouple=回路流体温度(℃)，Voltage=电机电压(V)，Volume Flow RateRMS=回路流量(L/min)。1Hz 采样，回路封闭循环。

## 评测预期分层（供结果解读）

1. **第一梯队（预期 DETERMINED 高命中）**：valve1/valve2 阀门类 —— 压力/流量/振动三方联动信号直白；
2. **第二梯队**：转子不平衡 5 形态 —— 信号单一（振动），根因类型可判，但 5 种形态间的区分考验时序形态分析（正是变点/趋势分析的主场）；
3. **第三梯队（预期 COMPETING_SET 出现）**：other_12 vs other_13（气蚀两来源在传感器上的表现几乎同构，本质不可分 → COMPETING_SET 是正确输出）；other_1-4 泄漏 vs 水量变化（缓变型之间易混淆）。
