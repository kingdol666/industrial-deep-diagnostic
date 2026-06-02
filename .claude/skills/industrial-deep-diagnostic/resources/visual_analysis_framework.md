---
name: visual-analysis-framework
description: VLM视觉图像分析框架——定义Data Processor生成VLM可读图表后，如何对图表进行结构化视觉解析
metadata:
  type: reference
---

# VLM 视觉图像分析框架

## 核心理念

图像不是被动的"证据展示"，而是诊断推理的**主动输入源**。VLM Agent 通过阅读图像获取以下三类无法从纯数字中获得的洞察：

1. **时序对齐洞察**：多个参数在同一时间轴上的波动同步性——谁先变？谁后变？谁同步？
2. **空间模式洞察**：散点图中肉眼可见的非线性、分簇、异常区域
3. **事件关联洞察**：事件标记处前后的视觉变化——质量是否跳变？幅度多大？

## 设计原则

### 图表必须为 VLM 设计

| 设计要素 | 为什么重要 | 实现方式 |
|---------|-----------|---------|
| **共享时间轴** | VLM 通过对齐的时间刻度判断参数间的时序关系 | 所有时间序列使用同一个 x 轴 |
| **参数归一化** | 不同量纲的参数无法在同一尺度上比较 | z-score 归一化或 min-max 到 [0,1] |
| **事件标记线** | VLM 可以看到"事件发生时参数是否有明显变化" | 红色虚线 + 文字标注 |
| **颜色编码分组** | VLM 可以看到不同分组的数据是否形成独立簇 | 按分组使用不同颜色 |
| **异常区间着色** | VLM 可以看到异常是否集中在特定时段 | 红色半透明阴影 |
| **大字体 + 高对比度** | VLM 需要清晰可读的标签 | 字体 ≥ 12pt，黑白背景 |

### 关键图表类型：时间对齐叠加图

这是 VLM 最能提取诊断信息的图表类型。将所有参数归一化后叠加在同一个时间轴上：

```
纵轴: 归一化值 (z-score)
横轴: 时间 (共享)

         conversion_pct (蓝实线)
         reactor_temp_C  (红虚线, 反转)
         cooling_duty_kW (绿实线)
         byproduct_ppm   (橙虚线, 反转)
    1.5 ┤ ╭─╮
        │/   ╲
    1.0 ┤      ╲  ← 早期稳定区
        │        ╲
    0.5 ┤         ╲ ╭──→ 转化率下降
        │          ╲╱
    0.0 ┤           ╲
        │  ╲         ╲
   -0.5 ┤   ╲         ╲
        │    ╲         ╲  ← 趋势同步区(所有参数同步变化)
   -1.0 ┤     ╲         ╲
        │      ╲         │╲ ← regen事件(红色虚线)
   -1.5 ┤       ╲       │  ╲ ← 部分恢复
        │        ╲      │   ╲
   -2.0 ┤         ╲_____│____╲
        └────────────────┴────── 时间 →
```

VLM 可以从这个图中直接读出：
- "蓝色和绿色线同步下降——同一机制"
- "红色线(温度)是上升的——反向关系"
- "红色虚线处有明显跳变——事件关联"
- "事件后恢复但不回到初始水平——部分恢复"

---

## Phase 5.5: 视觉图像解析协议

在生成所有图表之后、写入 image_captions 之前，执行以下协议：

### Step 1: 逐图阅读（VLM 直接看 PNG）

对 `03_figures/` 中的每一张 PNG 图片，使用 Read 工具直接读取图像文件。

**VLM 阅读每张图时必须回答以下问题**：

| 问题 | 适用于什么图 | 期望的洞察 |
|------|------------|-----------|
| **时序同步性**：哪些参数的波动在时间上同步？谁先谁后？ | 时间序列图、对齐叠加图 | 因果时序线索 |
| **事件响应**：在事件标记处，哪些参数有明显跳变？方向是什么？幅度多大？ | 含事件标记的图 | 根因确认/排除 |
| **分簇/分层**：不同颜色的数据点是否形成独立簇？簇内斜率是否一致？ | 散点图(按分组着色) | Simpson Paradox 检测 |
| **非线性**：散点图中是否有可见的拐点、阈值效应？ | 散点图 | 物理阈值识别 |
| **趋势形态**：下降是线性的还是加速的？有无拐点？ | 趋势图、退化曲线 | 退化模式分类 |
| **异常聚集**：异常点是否聚集在特定时段？ | 标注异常的时间序列图 | 异常成因线索 |
| **方向一致性**：多个质量指标的退化方向是否一致？ | 多指标时间序列 | 机制一致性验证 |

### Step 2: 提取结构化视觉洞察

将 VLM 的观察结构化为 `visual_analysis.json`，每个图表条目包含：

```json
{
  "figure": "fig_01_temporal_alignment.png",
  "visual_observations": [
    {
      "type": "temporal_synchronization",
      "description": "conversion_pct(蓝)和cooling_duty_kW(绿)几乎完美同步下降，时序上无可见滞后",
      "parameters_involved": ["conversion_pct", "cooling_duty_kW"],
      "estimated_lag": "0 (同步)",
      "confidence": "high",
      "diagnostic_weight": "STRONG — 同一物理机制(催化剂活性下降)的互补表现"
    },
    {
      "type": "event_response",
      "description": "在t=1200红色虚线处，conversion_pct出现约5%的向上跳变，byproduct出现约15%的向下跳变",
      "event": "catalyst_regeneration",
      "parameters_responded": ["conversion_pct", "byproduct_ppm", "selectivity_pct"],
      "parameters_did_not_respond": ["feed_sulfur_ppm", "cooling_water_temp_C"],
      "recovery_completeness": "partial — 未回到初始水平(~72% vs 初始95%)",
      "diagnostic_weight": "CRITICAL — 催化剂再生导致部分恢复，确证催化剂为根因"
    },
    {
      "type": "trend_morphology",
      "description": "退化曲线在t≈300处斜率明显增加(加速退化)，与product_lot切换时间点吻合",
      "trend_type": "piecewise_linear_with_acceleration",
      "inflection_points": ["t≈300", "t≈600"],
      "diagnostic_weight": "MODERATE — 加速退化与原料批次质量变化有关"
    }
  ],
  "cross_parameter_temporal_alignment": {
    "synchronous_groups": [
      {
        "parameters": ["conversion_pct", "quality_index", "cooling_duty_kW"],
        "description": "三个参数几乎完美同步下降——同一物理机制(催化剂失活)的三个互补表现",
        "estimated_group_lag": "0"
      },
      {
        "parameters": ["reactor_temp_C"],
        "description": "温度上升趋势与质量下降同步，但方向相反——操作工补偿行为",
        "estimated_group_lag": "0 (同步，非因果滞后)"
      }
    ],
    "precedence_signals": [
      {
        "earlier": "conversion_pct下降",
        "later": "reactor_temp_C上升",
        "description": "质量下降在先，温度补偿在后——但视觉上几乎同步，无法确定先后",
        "visual_confidence": "LOW — 需要CCF数值确认"
      }
    ],
    "independent_parameters": [
      {
        "parameters": ["feed_sulfur_ppm"],
        "description": "总硫值在图中呈现随机噪声模式，与任何趋势都不同步",
        "diagnostic_weight": "MODERATE — 总硫不是退化驱动因素"
      }
    ]
  },
  "synthesis": "图像揭示了一个清晰的累积退化模式：从t≈0开始，所有质量指标单调下降，冷却负荷同步下降(热力学耦合)。温度反向上升(操作工补偿)。退化在t≈300加速(原料批次变化)。催化剂再生(t=1200)导致部分恢复但不完全(不可逆烧结)。总硫和冷却水温与质量退化无视觉上的同步关系。"
}
```

### Step 3: 生成 image_captions.json（兼容层）

从 `visual_analysis.json` 提取关键信息，生成兼容格式的 `image_captions.json`，供不使用 VLM 的下游 Agent 使用。

### Step 4: 传递给 Diagnostician

`visual_analysis.json` 成为 Diagnostician Phase 0 的**必读文件**。它提供的视觉洞察比纯数字更丰富：

| 纯数字能告诉 Diagnostician | 视觉分析额外告诉 Diagnostician |
|:---|:---|
| conversion 与 cooling_duty r=0.880 | "两个参数在图上几乎完美同步下降，无可见滞后——同一机制" |
| Simpson Paradox 在 CAT-A-regen 中 r=-0.545 | "橙色点(再生后)的散点斜率方向与蓝色点(再生前)完全相反——肉眼可见的方向反转" |
| 再生前 conversion 均值 78.2%，再生后 73.8% | "再生事件处有约5%的向上跳变，但远低于初始95%——部分恢复的视觉印象很清晰" |
| 趋势衰减 44.8% | "去趋势后散点明显更分散，相关性减弱——视觉确认了衰减不是微小的" |

---

## 图表设计规范

### 时间对齐叠加图（最重要的 VLM 输入）

```python
# 设计要点：
# 1. 所有参数归一化到同一尺度 (z-score)
# 2. 共享 x 轴（时间）
# 3. 反转与质量负相关的参数（如温度）使所有参数在同一方向上变化
# 4. 事件标记为红色虚线 + 文字标注
# 5. 异常区间为红色阴影
# 6. 图例清晰，字体 ≥ 12pt
# 7. 纵轴标签: "归一化值 (z-score, 负相关参数已反转)"

def generate_vlm_temporal_overlay(df, targets, key_params, events, fig_dir):
    """
    生成 VLM 可读的时间对齐叠加图。
    
    关键设计：
    - 反转负相关参数使所有线"同向变化"
    - 事件标记清晰可见
    - 异常区间着色
    """
    fig, ax = plt.subplots(figsize=(18, 8))
    
    for col in targets + key_params:
        values = (df[col] - df[col].mean()) / df[col].std()
        # 如果与主要质量目标负相关，反转方向
        if correlation_sign(col, primary_target) < 0:
            values = -values
            label = f"{col} (reversed)"
        else:
            label = col
        ax.plot(df['timestamp'], values, linewidth=1.0, label=label, alpha=0.8)
    
    # 事件标记
    for event_time, event_name in events:
        ax.axvline(event_time, color='red', linestyle='--', linewidth=2, alpha=0.8)
        ax.text(event_time, ax.get_ylim()[1]*0.95, event_name,
                rotation=90, va='top', ha='right', fontsize=11, color='red', fontweight='bold')
    
    ax.set_xlabel('Time', fontsize=13)
    ax.set_ylabel('Normalized Value (z-score, negative correlations reversed)', fontsize=12)
    ax.legend(fontsize=10, loc='upper right')
    ax.set_title('Temporal Alignment — All Parameters Normalized & Direction-Aligned', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    fig.savefig(fig_dir + '/fig_vlm_temporal_overlay.png', dpi=150, bbox_inches='tight')
```

### Simpson Paradox 可视化（VLM 特化）

```python
# 设计要点：
# 1. 两个子图并排(CAT-A vs CAT-A-regen)
# 2. 每个子图内用颜色区分分组
# 3. 回归线用粗线，方向一目了然
# 4. 标注 r 值和 p 值
# 5. 标题用大字写 "SIMPSON PARADOX" 或 "方向一致"
```

---

## 与 Diagnostician 的集成

Diagnostician Phase 0 新增读取 `visual_analysis.json`：

```
Phase 0 新增:
  03_figures/visual_analysis.json  ← VLM 视觉分析结果
  ├── visual_observations[]        ← 每张图的视觉洞察
  ├── cross_parameter_temporal_alignment ← 时序对齐分析
  │   ├── synchronous_groups[]     ← 同步参数组
  │   ├── precedence_signals[]     ← 谁先变的信号
  │   └── independent_parameters[] ← 独立参数
  └── synthesis                    ← 整体视觉结论
```

Diagnostician 在 Phase 3 候选筛选中额外使用视觉洞察：

```
筛选规则新增:
  IF visual_analysis.cross_parameter_temporal_alignment.synchronous_groups 包含参数组
  AND 组内参数与质量目标的相关性经 validate_report 验证
  THEN 标记为 "视觉确认的同一机制参数组"
  
  IF visual_analysis 中某参数的 event_response.recovery_completeness == "partial"
  THEN 标记为 "视觉确认的部分恢复——催化剂相关"
  
  IF visual_analysis 中某参数的 event_response.parameters_did_not_respond 包含该参数
  THEN 该参数与事件无关，降低为根因候选
```
