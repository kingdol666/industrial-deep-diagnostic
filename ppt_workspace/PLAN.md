# PPT制作规划文件

## 一、基本信息

| 字段 | 值 |
|------|-----|
| PPT标题 | BOPET纵拉段划伤缺陷诊断报告 |
| 副标题 | 工业深度诊断管线全流程分析 |
| 总页数 | 10页（含4页真实诊断图，1张封面AI图，1张概念图） |
| 制作引擎 | huashu-slides + gpt-image-2 |
| 路径 | Path A（可编辑HTML） |
| 风格 | 线条简约风格 + 数据叙事 |
| **比例** | **16:9（960pt×540pt）** |
| 语言 | 中文 |
| 受众 | 领导管理层（需解释专业术语） |

## 二、风格参数速查

### 线条简约专业风
- **页面底色**: #F8F9FA
- **主色**: #1B3A5C（深蓝黑 — 标题、强调）
- **强调色**: #E85D3A（暖橙 — 关键数字、标注）
- **正文色**: #2D3436
- **辅助色**: #636E72（标签、脚注）
- **卡片底色**: #FFFFFF，1px #DFE6E9边框，border-left 3pt #1B3A5C
- **分割线色**: #DFE6E9
- **标题字体**: 微软雅黑 Bold, 22-28pt, #1B3A5C
- **正文字体**: 微软雅黑, 11-13pt, #2D3436
- **数据大字**: 36pt Arial Bold, #E85D3A
- **生图风格关键词**: "clean line-art, flat vector, precise thin lines, #F8F9FA background, navy #1B3A5C + warm orange #E85D3A accents, minimal professional, no text no shadows"

## 三、逐页规划

### 第1页：封面
- **标题**: BOPET纵拉段划伤缺陷诊断报告
- **副标题**: 55批次工业数据分析 × 三温区18辊 × 竞争假说协议
- **密度**: 极简
- **视觉主角**: 18辊纵拉机概念图
- **布局**: 图上文下——占位图(500pt×230pt)，标题28pt居中，暖橙短rule，副标题12pt #636E72，底部日期
- **内容要点**:
  - 要点1：工业深度诊断管线 · 55批次·182参数·8种型号
  - 要点2：诊断日期：2026-06-04
- **图片决策**: 1张hero-cover
- **配图Prompt**: "BOPET film MD stretching machine, 18 rolls in three temperature zones (preheat yellow-warm 75C, stretching orange 82C, quenching blue 35C), film web through rollers speed gradient left to right, clean engineering schematic, thin black lines, #F8F9FA background, navy #1B3A5C accents, flat vector, no text"

### 第2页：目录
- **标题**: 汇报结构
- **密度**: 极简
- **布局**: 标题+短rule，下方5格水平排列（编号+章名）
- **内容要点**:
  - 01 数据来源与工艺背景
  - 02 参数本体解读
  - 03 专业名词解释
  - 04 核心发现——Simpson悖论
  - 05 诊断结论与建议
- **图片决策**: text-only

### 第3页：数据来源与工艺背景
- **标题**: 数据来源与BOPET纵拉工艺
- **密度**: 中等
- **布局**: 左栏40%数据来源3卡片（带序号），右栏60%工艺示意图
- **内容要点**:
  - 要点1：数据来源——aligned_scratch_process.csv(55批×182列), scratch_defects.csv(1729条), merged_process_data(8640行30秒时序), parameter_mapping.json(参数含义) 
  - 要点2：BOPET工艺——挤出→纵拉三温区：预加热75-76C(near Tg) →拉伸82-84C(拉伸3倍) →急冷30-36C(冻结取向)
- **图片**: 使用已有fig7_md_stretcher_layout.png

### 第4页：参数本体解读
- **标题**: 参数本体——每个数据的物理含义
- **密度**: 中等
- **布局**: 2×2网格，每格一种参数类型+图标+含义+典型值
- **内容要点**:
  - 温度MD_TH001-018：18辊温度，三温区。预加热~75C(near Tg)，拉伸~82C，急冷~35C。极稳定stdev<0.1C
  - 扭矩W1C7C-8D：18辊扭矩，反映薄膜-辊面接触力。负值=制动辊(如11#辊~-67%)
  - 速度W1C40/W1C4B：慢辊/快辊线速度。拉伸比=快/慢≈3.0，极稳定CV~1%
  - 挤出参数：螺杆转速+熔体压力，与划伤为间接关系
- **图片决策**: text-only

### 第5页：专业名词解释
- **标题**: 看懂诊断报告的关键概念
- **密度**: 中等
- **布局**: 上部分栏（左6名词+右6名词），下方Simpson悖论概念图解
- **内容要点**:
  - Simpson悖论：全局趋势在按型号分组后消失或反转。如W1C80_std全局r=+0.469→PG31DS内r=-0.364
  - Pearson r：线性相关系数，-1→+1。|r|>0.5强相关
  - COMPETING_SET：竞争假说集——多个假说都无法排除时列出
  - 聚合 vs 分层相关：全体vs按型号分组后分别计算
  - Tg(~75C)：PET玻璃化转变温度，从硬变软的临界点
  - CCF交叉相关：分析时间序列间滞后关系
- **图片决策**: 1张Simpson悖论概念图解图
- **配图Prompt**: "Simpson's Paradox diagram, three data clusters (blue large left, orange medium right, green small far-right), each with downward slope line, but combined aggregate line slopes upward, clear statistical illustration, navy #1B3A5C lines, orange #E85D3A aggregate accent, #F8F9FA background, flat minimal vector, no text"

### 第6页：Simpson悖论——核心发现（关键页）
- **标题**: Simpson悖论确认——全局相关性是型号混杂假象
- **密度**: 深度
- **布局**: 左上标题，左中数据表(全局r vs 型号内r)，右中Simpson图，底部结论
- **内容要点**:
  - 表格：W1C86_std全局r=+0.487→PG31DS内r=+0.044(衰减91%)；W1C80_std全局r=+0.469→PG31DS内r=-0.364(反转！)；W1C81_std全局r=+0.468→PG31DS内r=-0.278(反转)
  - 速度波动：高/零划伤比8.9倍，但型号内平均r仅0.16-0.19(归零)
  - 结论：所有聚合相关是型号间差异假象。型号→速度设定→摩擦功率决定划伤基线
- **图片**: fig_vlm_simpson_torque.png + fig3_speed_scratch_by_model.png

### 第7页：竞争假设分析
- **标题**: 什么驱动了划伤？——竞争假说分析
- **密度**: 中等
- **布局**: 左栏假设表格(绿/黄/红状态)，右栏扭矩profile对比图
- **内容要点**:
  - H1(型号驱动)：存续65——15倍密度差、速度2倍、膜厚2.6倍。但PG31DS内0-36的变异未完全解释
  - H2(扭矩波动残留)：残留35——FP21内5#辊r=0.442但方向不一致，小样本(n≤10)
  - H3(速度波动)：排除95%——型号内平均r<0.20
  - H4(温度)：排除99%——18辊全部std<0.1C
- **图片**: fig6_torque_profile_high_vs_low.png

### 第8页：诊断结论
- **标题**: 诊断结论与置信度评估
- **密度**: 中等
- **布局**: 顶部标题，中左诊断类型卡片+中右置信度数字，底部3条数据限制
- **内容要点**:
  - 诊断类型COMPETING_SET：H1(型号主导)65上限，H2(扭矩残留)35
  - 排除：速度波动(95%)、温度(99%)
  - 限制：批次级丢失秒级信息、型号共线无法拆解、小样本不足
- **图片决策**: text-only

### 第9页：改进建议
- **标题**: 改进建议——下一步行动
- **密度**: 中等
- **布局**: 3项优先级卡片纵向排列(P0/P1/P2)，每项带成本估计
- **内容要点**:
  - P0(低成高)：产品型号规范管理——高频伤型号专项SOP。预计降划伤50%+
  - P1(低成本)：FP21/PG22C增采样至n≥30——确认方向稳定性
  - P2(中成本)：辊级秒级监测——关键辊5/6/11#高频采集
- **图片决策**: text-only

### 第10页：总结
- **标题**: 三条核心结论
- **密度**: 极简
- **布局**: 上区大结论卡片(2/3宽，橙左border)，下区左次结论+下区右次结论
- **内容要点**:
  - 划伤由产品型号差异主导——PG32D划伤率是PG22C的15倍
  - 所有工艺-划伤强相关(r=0.43-0.49)被确认为型号混杂假象，系统本身未出故障
  - 建议从型号规范管理入手，先降高频伤再精细化分析
- **图片决策**: text-only

## 四、配图生成清单

| 序号 | 文件名 | 页码 | 尺寸 | 类型 | 来源 |
|------|--------|-----|------|------|------|
| 1 | p01_cover.png | 1 | 960×432 | hero-cover AI生成 | gpt-image-2 |
| 2 | p05_simpson_explain.png | 5 | 720×280 | 概念图解AI生成 | gpt-image-2 |
| 3 | fig7_md_stretcher_layout.png | 3 | 576×288 | 已有诊断图 | 03_figures/ |
| 4 | fig_vlm_simpson_torque.png | 6 | 480×360 | 已有诊断图 | 03_figures/ |
| 5 | fig3_speed_scratch_by_model.png | 6 | 480×360 | 已有诊断图 | 03_figures/ |
| 6 | fig6_torque_profile_high_vs_low.png | 7 | 640×360 | 已有诊断图 | 03_figures/ |

**配图统计**: 6张图 / 10页总计

## 五、技术规范

- **slide尺寸**: 16:9（960pt×540pt）
- **页眉**: h=6pt, bg #1B3A5C
- **内容区**: padding 12pt 24pt
- **底部栏**: h=20pt, 页码#636E72右下
- **图片路径**: slides/figures/（真实诊断图已复制）
- **编码**: UTF-8

## 六、知识直通

- 诊断详细数据: workspace/diagnostic-runs/202606040345090_lekai_BOPET_scratch/
- 完整报告: report.md + optimizer.md
- 图表资源: 03_figures/（含9张诊断图）
