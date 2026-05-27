# PPT制作规划文件

## 一、基本信息

| 字段 | 值 |
|------|-----|
| PPT标题 | BOPET薄膜CCD表面缺陷根因诊断——177个工艺参数无一通过统计验证 |
| 副标题 | 挤出段热降解假说与产品等级混杂效应：基于151批次生产数据的系统性分析 |
| 总页数 | 10页（其中4页配图，6页text-only） |
| 制作引擎 | huashu-slides + gpt-image-2 |
| 路径 | Path A（可编辑HTML） |
| 风格 | Bauhaus #13 — 包豪斯风格（红蓝黄三原色 + 几何构成） |
| **比例** | **16:9（960pt×540pt）** |
| 语言 | 中文 |
| 受众 | 外部客户（兼顾专业性与可读性） |
| 研究笔记 | ppt_workspace/references/（知识库目录） |

## 二、风格参数速查

### Bauhaus #13 包豪斯风格

> 包豪斯核心设计哲学：形式追随功能，几何即逻辑，三原色的心理学力量。本风格通过红(#E53935)蓝(#1E88E5)黄(#FDD835)三原色与几何基本形（圆/三角/方）构建信息层级，适合工程技术汇报的清晰论证。

- **页面底色**: #FAFAFA（纸白）
- **主色**: #E53935（包豪斯红 — 标题、重点数据、关键标注）
- **副色**: #1E88E5（包豪斯蓝 — 卡片边框、章节标签、次要信息）
- **强调色**: #FDD835（包豪斯黄 — 高亮、关键数值底衬、装饰几何形）
- **文字色**: #212121（包豪斯黑 — 正文）
- **辅助色**: #757575（中灰 — 脚注、标签、辅助说明）
- **卡片底色**: #FFFFFF（白底）+ 左侧4pt #1E88E5蓝边框
- **重点卡片色**: #FFFFFF + 左侧6pt #E53935红边框 + 顶部#FDD835三角装饰
- **分割线**: 1pt solid #E0E0E0 或 2pt solid #1E88E5
- **签名元素**: 底部2pt #E53935红横线 + 右下角 #212121 页码 + 左上角几何装饰（蓝圆或黄三角）
- **标题字体**: 思源黑体/微软雅黑 Bold, 24-28pt, #E53935
- **副标题字体**: 微软雅黑 Bold, 14-16pt, #212121
- **正文字体**: 微软雅黑 Regular, 11-13pt, #212121
- **英文字体**: Helvetica Neue / Arial（数字、单位）
- **几何装饰原则**: 圆代表"完整/系统"，三角代表"警示/关键"，方代表"稳定/数据"

### 生图风格关键词（Bauhaus注入）

> bauhaus geometric style, primary colors red #E53935 blue #1E88E5 yellow #FDD835 on paper white #FAFAFA background, clean vector illustration, flat geometric shapes (circles, triangles, rectangles), form follows function composition, no text, no shadows, no photographic textures, precise lines, industrial design aesthetic, suitable for engineering presentation

## 三、逐页规划

### 第1页：封面
- **模式**: 包豪斯红+黑基调
- **标题**: BOPET薄膜CCD表面缺陷根因诊断
- **密度**: 极简（标题20字）
- **论证逻辑**: 建立诊断报告的第一印象——工业严谨性、数据驱动、问题导向
- **视觉主角**: 一张BOPET工艺概念图（hero-cover），占页面55%面积
- **布局**: 上下分区——上方全宽概念图（520pt×240pt），中部标题24pt Helvetica Neue Bold #E53935居中 + 红短rule 48pt居中，副标题14pt #212121，底部几何装饰色块条（蓝8pt + 黄8pt + 红8pt 等宽排列）
- **内容要点**:
  - 要点1：副标题——177个工艺参数与6类CCD表面缺陷的系统性匹配分析
  - 要点2：日期 2026-05 | 151批次 | 基于工业诊断方法论
- **图片决策**: Q1✓ Q2✓（封面需要视觉锚点建立第一印象）→ 1张 hero-cover
- **配图类型**: hero-cover
- **内容锚点**: BOPET薄膜挤出→MD纵拉→CCD在线检测的生产流程概念图，展现PET原料经挤出机、18辊拉伸机到CCD检测的完整链路
- **配图 Prompt**: "BOPET film production line conceptual diagram: extrusion system on left feeding molten PET through die, 18-roll MD stretcher in center with three zones (pre-heat, stretch, quench), CCD surface inspection at right end detecting defects on film surface, bauhaus geometric style, paper white background, red #E53935 blue #1E88E5 yellow #FDD835 accents, flat vector, clean industrial aesthetic, 16:9 composition with bottom 30% empty for title, no text"

### 第2页：目录
- **模式**: 包豪斯（红蓝黄三原色章节标记）
- **标题**: 报告结构
- **密度**: 极简（每章5-8字）
- **论证逻辑**: 快速导航——让观众了解报告包含背景→数据→发现→根因→建议的完整逻辑链
- **视觉主角**: 编号网格——左侧大号装饰数字（30pt Helvetica Neue Bold）配红/蓝/黄三色圆点标记
- **布局**: 3列×2行非等大网格——顶部标题栏（2pt #E53935红线），每格：左侧彩色圆点（直径18pt）+ 数字（24pt Helvetica #212121 opacity 30%）+ 章节标题（12pt Bold）+ 一行概述（9pt #757575），底排几何装饰条
- **内容要点**:
  - 要点1：项目背景——BOPET工艺与CCD检测
  - 要点2：数据概况——151批次 × 189变量
  - 要点3：核心发现——缺陷共现与等级混杂
  - 要点4：根因假设——挤出段热降解
  - 要点5：统计验证——Simpson悖论与6重过滤
  - 要点6：结论与行动——置信度评估与P0建议
- **图片决策**: text-only（目录结构本身是视觉设计，用三色圆点+网格呈现）

### 第3页：项目背景
- **模式**: 包豪斯（蓝调为主，突出工艺系统性）
- **标题**: BOPET双拉薄膜：挤出→MD纵拉→CCD检测
- **密度**: 中等（每段30-50字）
- **论证逻辑**: 让外部客户快速理解BOPET生产工艺、CCD检测的6类缺陷、以及本次分析的聚焦范围（挤出+MD段）
- **视觉主角**: 上方全宽工艺流程图 + 下方六类缺陷标签网格
- **布局**: 上下分区——上方工艺流程图（全宽530pt×110pt，展示挤出机→过滤器→模头→MD纵拉机→CCD检测），下方左半部分6类缺陷标签（2行×3列，每格红底白字缺陷名+一行描述），右半部分分析目标卡片（蓝边框+目标文字），底部几何装饰
- **内容要点**:
  - 要点1：工艺流程——PET原料→主挤出机MG(280°C)→过滤器→模头流延→MD纵拉(18辊)→CCD检测，分三阶段（预热75°C/拉伸82°C/急冷35°C）
  - 要点2：6类CCD缺陷——膜点(film_points)、低聚物(oligomer)、尘埃(dust)、气泡(bubbles)、熔斑(melt_spots)、划伤(scratch_count)
  - 要点3：分析范围——挤出段(主/辅挤出机参数) + MD纵拉段(18辊温度/扭矩/速度)共177个工艺参数
  - 要点4：核心约束——无挤出段熔体温度数据、无原材料质量数据、无维护记录
- **图片决策**: Q1✓ Q2✓ Q3✓ Q4✓ → 1张（BOPET工艺流程图对外部客户理解分析边界至关重要）
- **配图类型**: process-flow
- **内容锚点**: BOPET薄膜双拉工艺完整流程：主挤出机→主过滤器→辅挤出机→辅过滤器→模头流延→MD纵拉三段(预热/拉伸/急冷)→CCD表面检测。用几何箭头连接各工段，标注关键温度点
- **配图 Prompt**: "BOPET film production process flow from left to right: main extruder (labeled 280°C) → main filter → co-extrusion die → MD stretcher with 18 rolls in three zones (pre-heating 75°C, stretching 82°C, quenching 35°C) → CCD surface inspection, sequential geometric arrow connections between stages, bauhaus style flat vector, paper white background, blue #1E88E5 primary flow arrows, red #E53935 temperature markers, yellow #FDD835 accent dots at stage transitions, 16:9 wide composition height approximately 120pt, no text"

### 第4页：数据概况——令人震惊的初步结论
- **模式**: 包豪斯（红+黑冲击力）
- **标题**: 151批次数据分析：所有177个工艺参数与缺陷的相关性均未通过验证
- **密度**: 中等（关键数字突出，文字精简）
- **论证逻辑**: 用大数字制造认知冲击——虽然做了全面分析，但发现了一个"负结果"：没有工艺参数可以单独解释缺陷变化
- **视觉主角**: 超大数字"177" + "32" + "0" 形成三列对比
- **布局**: 三列不对称布局——左列大数字"177"（48pt #E53935 Bold）+ 标注"工艺参数无显著相关" + 中列大数字"32"（48pt #1E88E5）+ 标注"Simpson悖论发现" + 右列大数字"0"（48pt #212121）+ 标注"通过全验证的参数"，底部文字栏解释核心结论，右侧红三角装饰
- **内容要点**:
  - 要点1：177个工艺参数——全部与6类缺陷的Pearson |r| < 0.55（最强仅r=0.5543且完全无效）
  - 要点2：32个Simpson悖论发现——聚合相关在主导等级PG31DS内全部坍塌或反转
  - 要点3：87个Spearman-Pearson分歧——缺陷数据严重偏态（skewness 2.28-12.12），Pearson不可靠
  - 要点4：核心结论：产品等级(model)是主导混杂因子，聚合层面相关皆为等级间差异
- **图片决策**: text-only（数据冲击靠超大数字+对比布局，文字更直接）

### 第5页：最强统计信号——缺陷共现
- **模式**: 包豪斯（红+黄强调）
- **标题**: film_points↔oligomer r=0.9133——缺陷共现强度远超任何工艺参数
- **密度**: 中等（核心数字大，辅以解释）
- **论证逻辑**: 证明缺陷之间存在远比工艺参数更强的相关性，暗示它们共享同一来源（挤出段）
- **视觉主角**: 两个缺陷聚簇的可视化——聚簇1（膜点+低聚物）大号红圈，聚簇2（尘埃+熔斑）蓝圈
- **布局**: 左右分区——左侧60%: 两圆相交文氏图(聚簇1红|聚簇2蓝)，每个缺陷名+相关r值标注 + 圆重叠区"共享来源"，右侧40%: 关键数据卡片（film_points↔oligomer r=0.9133 大字 + PG31DS内r=0.8378 + 置信度65/100），底部辅助说明
- **内容要点**:
  - 要点1：聚簇1——film_points(膜点)↔oligomer(低聚物) Pearson r=0.9133, PG31DS内r=0.8378 — 全数据集最强信号
  - 要点2：聚簇2——dust(尘埃)↔melt_spots(熔斑) Pearson r=0.6455, PG31DS内r=0.531 — 中度相关
  - 要点3：物理含义——根据PET化学，膜点和低聚物均为挤出段280°C热降解产物（环状三聚体+交联凝胶粒子）
  - 要点4：诊断意义——缺陷-缺陷相关 > 任何工艺-缺陷相关 → 共源而非独立调控
- **图片决策**: Q1✓ Q2✓（两聚簇的视觉关系用文氏图比文字更直观）→ 1张
- **配图类型**: relationship-diagram
- **内容锚点**: 两个相交的圆表示缺陷聚簇——大圆聚簇1(红)包含film_points和oligomer相连，外标注r=0.9133 + 圆聚簇2(蓝)包含dust和melt_spots相连，外标注r=0.6455，两圆之间用标注"共享挤出段来源"，底部用几何箭头指向挤出机图标
- **配图 Prompt**: "Two overlapping circles representing defect clusters: large red #E53935 circle contains film_points and oligomer nodes connected by line labeled r=0.9133, smaller blue #1E88E5 circle contains dust and melt_spots nodes connected by line labeled r=0.6455, overlapping region labeled shared source, geometric arrow pointing from cluster to extruder icon at bottom, bauhaus flat vector, paper white #FAFAFA background, yellow #FDD835 accent dots on data nodes, clean minimalist, relationship diagram, no text"

### 第6页：Simpson悖论——等级混杂效应
- **模式**: 包豪斯（蓝+黄，方法论重音）
- **标题**: 32个Simpson悖论——聚合相关在等级内全部失效
- **密度**: 深度（需要解释统计概念和具体案例）
- **论证逻辑**: 揭示本次诊断中最关键的统计发现——如果不控制产品等级，所有结论都是错误的
- **视觉主角**: 对比图——左"聚合层面"高正相关 vs 右"PG31DS内"低/负相关
- **布局**: 左右对比分区——左半: 聚合数据散点图(r=0.55)配大红标注× + 右半: PG31DS内散点图(r=0.22)配绿标注✓，顶部: Simpson悖论概念卡片（蓝边框+定义），底部: 三个关键反转案例表格（参数|聚合r|PG31DS内r|方向）
- **内容要点**:
  - 要点1：典型案例——W1C80@PV1_std↔film_points: 聚合r=0.5543 → PG31DS内r=0.2167（衰减62%），且符号反转风险（离群值驱动）
  - 要点2：方向反转——W1C4B@PV1_std↔film_points: 聚合r=0.367 → PG31DS内r=-0.197（完全反转！）
  - 要点3：唯一幸存信号——film_points↔oligomer: 聚合r=0.913 → PG31DS内r=0.838（衰减但保持方向）
  - 要点4：方法论意义——任何未控制产品等级的工艺-缺陷相关分析均不可信，等级间工艺设定值差异是虚假相关的根源
- **图片决策**: Q1✓ Q2✓ Q3✓（Simpson悖论是抽象统计概念，对比图是外部客户理解的关键）→ 1张
- **配图类型**: comparison-diagram
- **内容锚点**: 左右对比：左侧聚合层面散点图(多个颜色混合)向上倾斜趋势标注r=0.55 + 大红色×，右侧单一等级(PG31DS)散点图接近水平标注r=0.22 + 绿色✓，两个散点用不同颜色圆圈表示不同产品等级，几何黄三角警示标注Simpson's Paradox
- **配图 Prompt**: "Left-right comparison diagram: left panel shows aggregate scatter plot with mixed colored points trending upward with red line labeled r=0.55 and large red X mark, right panel shows PG31DS-grade-only scatter plot flat near zero with green line labeled r=0.22 and green checkmark, different colored circles represent different product grades, yellow #FDD835 warning triangle between panels labeled Simpson's Paradox, bauhaus geometric style, paper white #FAFAFA background, red #E53935 negative signal, blue #1E88E5 axes, clean data visualization aesthetics, no text"

### 第7页：根因H1——挤出段热降解
- **模式**: 包豪斯（红主色+黄强调，根因重音）
- **标题**: 首要根因：挤出段PET热降解——置信度55/100
- **密度**: 中等（机制描述+定量验证）
- **论证逻辑**: 综合所有证据，唯一幸存且物理可行的假说——膜点和低聚物在挤出段280°C下由PET热降解产生
- **视觉主角**: PET热降解机理示意——280°C降解到80°C对比
- **布局**: 上下分区——上方: PET热降解机理图（全宽540pt×120pt，从PET链→降解产物(环状三聚体+凝胶粒子)→CCD检测的因果链），中间: 核心论证卡片（红边框大号"55/100"置信度+三段评分），下方: Arrhenius检验卡片（蓝边框——280°C半衰期分钟级 vs 80°C半衰期千年级，排除MD段可能性）
- **内容要点**:
  - 要点1：数据证据(12/25分)——film_points↔oligomer在PG31DS内保持中度正相关(r=0.838)，唯一部分通过分层检验的信号
  - 要点2：物理机制(15/20分)——PET在≥200°C热降解产生环状三聚体(oligomer)和交联凝胶粒子(film_points)，Arrhenius检验定量确认MD段75-83°C无法引起化学降解（反应速率差异约10^9倍）
  - 要点3：逻辑链(8/30分)——因果链约50%为[INFERRED]，缺少挤出段熔体温度数据是最关键缺口
  - 要点4：结论——挤出段热降解是最可能的根因，但需直接测量数据确认
- **图片决策**: Q1✓ Q2✓ Q3✓（化学降解机理图对外部客户理解"为什么是挤出段而非MD段"至关重要）→ 1张
- **配图类型**: mechanism-diagram
- **内容锚点**: PET分子链在280°C下断裂产生两种产物——环状三聚体(oligomer)和交联凝胶粒子(film_points)，用热力学箭头从高温挤出机指向两种缺陷，下方用×+温度计表示80°C的MD纵拉段无法引起降解，温度计红柱从280°C(高)到80°C(几乎空)对比，包豪斯红蓝黄几何风格
- **配图 Prompt**: "Chemical mechanism diagram: PET polymer chain at top, under 280°C heat (red thermometer icon) breaking into two degradation products - cyclic trimer labeled oligomer and cross-linked gel particle labeled film_points, downward arrows from extruder icon to both defect types, below section shows MD line at 80°C with large X mark and nearly empty thermometer indicating no degradation possible, bauhaus geometric flat vector, paper white #FAFAFA background, red #E53935 for high temperature pathway, blue #1E88E5 for ruled-out pathway, yellow #FDD835 arrow highlights, clean industrial schematic, no text"

### 第8页：已排除假设与其他因素
- **模式**: 包豪斯（蓝灰调，次位信息）
- **标题**: 已排除的假设与次要因素——四个假说被推翻
- **密度**: 中等（四组排除链清晰呈现）
- **论证逻辑**: 展示诊断过程的严谨性——不是忽略数据而是通过多重检验排除了大多数假说
- **视觉主角**: 四组排除链条垂直排列，每组用红×标记
- **布局**: 垂直4段排列——每段: 左侧红底白字"排除"标签(40pt×20pt pill) + 右侧假设名称(14pt Bold #212121) + 排除原因(11pt #757575)，段间用1pt #E0E0E0分隔，右栏装饰性几何点缀
- **内容要点**:
  - 要点1：MD辊温异常→化学降解 ✗ — Arrhenius检验：75-83°C半衰期月级/年级，9天窗口不可能
  - 要点2：扭矩波动→膜点 ✗ — W1C80@PV1_std Pearson r=0.55但Spearman=-0.11（离群值驱动符号反转），PG31DS内r=0.22
  - 要点3：快辊速度→划伤 ✗ — 聚合r=0.37但PG31DS内r=-0.197（Simpson方向反转）
  - 要点4：次要因素——熔斑(melt_spots)时间趋势（r=0.382, ρ=0.696）可能来自过程缓慢退化（过滤器堵塞/污染物累积），但去趋势后所有扭矩相关衰减60-93%，不可作为直接证据
- **图片决策**: text-only（排除链是清单式内容，垂直排列最清晰）

### 第9页：结论与置信度评估
- **模式**: 包豪斯（红+黑，果断收束）
- **标题**: 诊断结论：挤出段热降解为首要根因，置信度55/100
- **密度**: 极简（每条结论10-15字，数字突出）
- **论证逻辑**: 收束全部论证，形成三条可以带走的核心信息——根因是什么、为什么排除工艺参数、需要什么数据
- **视觉主角**: 三个结论卡片，尺寸渐变——最重要的结论（挤出段热降解）占最大卡片
- **布局**: 1大+2小不规则拼贴——左大卡片(60%宽度)：根因声明"挤出段热降解 55/100"红底白字 + 右上方中卡片：策略含义"等级混杂是主导效应 90/100"蓝边框 + 右下方小卡片：数据缺口"需挤出段熔体温度 无维护记录"黄三角标记，底部一句话总结
- **内容要点**:
  - 要点1：首要根因——挤出段PET热降解（置信度55/100），支撑：膜点-低聚物等级内相关+Arrhenius物理检验
  - 要点2：方法论发现——产品等级是主导混杂因子（置信度90/100），所有工艺参数相关为等级间差异
  - 要点3：关键缺口——缺少挤出段熔体温度数据、原材料质量数据、维护记录，导致因果链50%为推断
  - 要点4：什么会改变结论——若有熔体温度数据与膜点无相关→H1被推翻；若维护记录显示过滤网更换后熔斑下降→过程退化被确认
- **图片决策**: text-only（结论靠文字和数据力量，不需配图）

### 第10页：推荐行动与展望
- **模式**: 包豪斯（蓝+黄，行动导向）
- **标题**: 优先行动：P0-采集挤出段数据，P1-增加过滤器监测
- **密度**: 中等（每项建议30-50字）
- **论证逻辑**: 将结论转化为可操作的行动——让客户知道下一步应该做什么、为什么做、预期效果
- **视觉主角**: 三列行动优先级卡片（P0/P1/P2），用颜色区分优先级
- **布局**: 三列等宽卡片——P0列(#E53935红底白字): "采集熔体温度"+"按产品等级分析" + P1列(#1E88E5蓝边框): "过滤器压差监测"+"记录维护事件" + P2列(#757575灰边框): "原料质量检测"+"TD横拉段数据"，底部展望语句 + 几何装饰条
- **内容要点**:
  - 要点1：P0-采集挤出段熔体温度数据——直接验证/排除H1，按产品等级分开分析消除混杂
  - 要点2：P1-增加过滤器压差连续监测——量化过滤网堵塞与熔斑的趋势关系，记录维护时间点验证重置效应
  - 要点3：P1-提高采样频率至辊级别——实现真正的时序分析（批次级分辨率不足）
  - 要点4：P2-增加原料IV值/水分检测、增加TD横拉段参数——补全对薄膜质量的完整分析
- **图片决策**: text-only（行动建议用三列卡片对比最清晰）

## 四、配图生成清单

> 10页中仅4页需要配图（配图率40%），其余6页为text-only纯文字排版。

| 序号 | 文件名 | 页码 | 尺寸 | 图片类型 | 内容锚点 | Prompt风格注入 |
|------|--------|-----|------|---------|---------|---------------|
| 1 | p01_cover.png | 1 | 1536×864 | hero-cover | BOPET生产线概念图（挤出→MD纵拉→CCD检测），底部1/3留白 | bauhaus geometric, red/blue/yellow, paper white, flat vector |
| 2 | p03_process.png | 3 | 1536×864 | process-flow | 挤出→MD纵拉三段→CCD全流程，几何箭头连接各工段 | bauhaus style, blue flow arrows, red temp markers |
| 3 | p05_defect_clusters.png | 5 | 1536×864 | relationship-diagram | 两个缺陷聚簇文氏图（film_points+oligomer / dust+melt_spots） | bauhaus flat vector, two overlapping circles, red+blue |
| 4 | p06_simpson.png | 6 | 1536×864 | comparison-diagram | 聚合r=0.55 vs PG31DS内r=0.22散点图对比 | bauhaus geometric, data viz, clean aesthetic |
| 5 | p07_mechanism.png | 7 | 1536×864 | mechanism-diagram | PET分子链280°C降解→oligomer+film_points vs 80°C被排除 | bauhaus schematic, red high-temp pathway, blue ruled-out |

**配图统计**: 4页配图 / 10页总计 = 40%配图率（text-only优先原则）

## 五、技术规范

- slide尺寸: 960pt×540pt（16:9宽屏比例，pptxgenjs LAYOUT_WIDE）
- 内容区: padding 6pt 20pt
- 底部栏: h=24pt, bg #212121, color #FAFAFA, 右下页码 #E53935
- 几何装饰: 左上角装饰元素（蓝圆直径12pt + 黄三角10pt 重叠），每页位置稳定
- 图片: placeholder div + build.js addImage（Windows兼容，正斜杠路径）
- 编码: UTF-8 + meta charset
- text-only页排版: 大标题+卡片分区+大数字+充足留白（每页留白≥20%）
- 配图Prompt已注入风格关键词：bauhaus geometric, red #E53935 blue #1E88E5 yellow #FDD835, paper white #FAFAFA, flat vector, clean lines

## 六、知识直通

- **知识传递链**: knowledge-agent → references/ref-*.md + _index.md → PLAN.md（浓缩） + references/（原文） → huashu-slides → 幻灯片
- 下游技能（huashu-slides）构建时，可从以下维度文件获取补充素材：
  - `ref-bopet-process.md` — BOPET双拉薄膜生产工艺详情
  - `ref-pet-degradation.md` — PET热降解化学机理
  - `ref-ccd-inspection.md` — CCD在线检测技术
  - `ref-simpson-paradox.md` — Simpson悖论在工业分析中的应用
  - 以及 `_user_materials.md` 中完整的诊断报告（report.md）+ 优化器评审（optimizer.md）
- 各页内容要点中的核心数字（r值、置信度、批次量）可直接使用，背景解释和引用细节可从 `ref-*.md` 中提取。
