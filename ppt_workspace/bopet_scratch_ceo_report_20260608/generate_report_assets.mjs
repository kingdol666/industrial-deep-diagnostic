import fs from 'fs';
import path from 'path';

const root = path.resolve(process.cwd(), 'ppt_workspace/bopet_scratch_ceo_report_20260608');
const refsDir = path.join(root, 'references');
const slidesDir = path.join(root, 'slides');
const imgDir = path.join(root, 'garden-gpt-image-2', 'image');

const write = (file, content) => {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, content, 'utf8');
};

const plan = `# PPT制作规划文件

## 一、基本信息

| 字段 | 值 |
|------|-----|
| PPT标题 | BOPET划伤问题已定位到MD拉伸段过程失稳，但原发机理仍需在线验证 |
| 副标题 | 面向经营层的结论汇报：结论、推导过程、证据链与下一步行动 |
| 总页数 | 12页（其中6页配图，6页text-only） |
| 制作引擎 | huashu-slides + html2pptx |
| 路径 | Path A（可编辑HTML） |
| 风格 | Study Style #20 — 学术研究双模系统（暖学术 + 锐学术） |
| **比例** | **16:9（960pt×540pt）** |
| 语言 | 中文 |
| 受众 | 商业（企业老板 + 制造管理层） |

## 二、风格参数速查

### 暖学术模式（Warm Academic）
- 页面底色: #FAF9F6
- 主色: #16324F
- 强调色: #C7772B
- 正文色: #1F1F1F
- 辅助色: #6C6A66
- 卡片底色: #F2EEE7
- 分割线色: #DDD3C7
- 标题字体: Microsoft YaHei Bold, 24-28pt
- 正文字体: Microsoft YaHei Regular, 10-13pt

### 锐学术模式（Crisp Academic）
- 页面底色: #FFFFFF
- 主色: #0E2A47
- 强调色: #B42318
- 卡片底色: #EEF4FA
- 重点卡片色: #FFF4F2
- 标题字体: Microsoft YaHei Bold, 24-26pt
- 正文字体: Microsoft YaHei Regular, 10-12pt

## 三、逐页规划

### 第1页：封面
- 标题: BOPET划伤问题已定位到MD拉伸段过程失稳
- 布局: 中央断言标题 + 下方四条管理层摘要 + 右侧结论卡
- 图片决策: text-only

### 第2页：经营层要先记住什么
- 标题: 先讲结论：不是温度设定值偏移，而是拉伸段过程稳定性失控
- 布局: 左侧三条核心结论，右侧风险边界与管理动作
- 图片决策: text-only

### 第3页：问题定义
- 标题: 我们分析的不是“某个坏批次”，而是55批次持续出现的划伤波动
- 布局: 左侧背景与样本说明，右侧大数字矩阵
- 图片决策: text-only

### 第4页：第一层证据
- 标题: 方差分解先回答了一个关键问题：问题主要发生在产品内，而不是产品之间
- 布局: 左图右文，图为方差分解
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_variance_decomposition.png
  - 占位符id: img-variance

### 第5页：第二层证据
- 标题: 分产品时间线说明设备具备低缺陷能力，但部分型号对过程失稳更敏感
- 布局: 左图右文，图为分产品时间线
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_product_timelines.png
  - 占位符id: img-products

### 第6页：第三层证据
- 标题: 参数排序把关注点收敛到MD拉伸段扭矩STD与速度STD
- 布局: 左文右图，图为相关排序
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_torque_correlation.png
  - 占位符id: img-corr

### 第7页：第四层证据
- 标题: 时序叠加图把“划伤峰值”和“扭矩/速度波动峰值”串到了一起
- 布局: 上图下文，图为主时序叠加
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_master_time_aligned_overlay.png
  - 占位符id: img-overlay

### 第8页：第五层证据
- 标题: 温度断面几乎重合，因此温度不是主根因
- 布局: 左图右侧反证链
- 图片决策: 1张
- 配图:
  - 文件: garden-gpt-image-2/image/fig_zone_profile.png
  - 占位符id: img-zone

### 第9页：证据链收束
- 标题: 由“排除法 + 关联证据 + 物理机理”收束到两个竞争假设
- 布局: 双列竞争假设卡片 + 底部证据链
- 图片决策: text-only

### 第10页：为什么现在不能直接定单根因
- 标题: 当前最大风险不是没找到方向，而是把批次级相关误当成确定因果
- 布局: 左侧统计稳健性问题，右侧对结论的影响
- 图片决策: text-only

### 第11页：企业下一步怎么做
- 标题: 下一步不是继续争论，而是设计能区分H1/H2的验证动作
- 布局: 三阶段行动路线图
- 图片决策: text-only

### 第12页：汇报收口
- 标题: 管理层决策建议：先稳住过程，再用在线数据定责
- 布局: 左侧一句话收口，右侧三条决策请求
- 图片决策: text-only

## 四、配图生成清单

| 序号 | 文件名 | 对应页码 | 来源 |
|------|--------|---------|------|
| 1 | fig_variance_decomposition.png | 4 | 诊断run原始图 |
| 2 | fig_product_timelines.png | 5 | 诊断run原始图 |
| 3 | fig_torque_correlation.png | 6 | 诊断run原始图 |
| 4 | fig_master_time_aligned_overlay.png | 7 | 诊断run原始图 |
| 5 | fig_zone_profile.png | 8 | 诊断run原始图 |

## 五、技术规范

- slide尺寸: 960pt×540pt
- 顶部签名线: 6pt 深蓝
- 底部信息栏: 22pt，页码右下
- 图片: placeholder div + compile.cjs addImage
- 编码: UTF-8
`;

const notes = `# BOPET划伤老板汇报研究摘要

## 汇报目标

这套PPT用于向企业老板说明四件事：
1. 本次分析最终结论是什么。
2. 这个结论是怎样一步步得出来的。
3. 哪些证据最稳，哪些地方仍然有统计边界。
4. 企业下一步应该投入什么动作来把结论变成改善结果。

## 最终主结论

- 当前最稳的经营层结论不是“已经锁定某一个参数”，而是：
  BOPET划伤问题已经明确收敛到MD拉伸段过程稳定性问题，而非温度设定值或产品切换本身。
- 现阶段不能把H1或H2当作唯一根因对外宣布。
- 最合理的表达是：过程失稳已定位，原发机理仍处于竞争假设集，需要在线验证闭环。

## 结论链路

### 1. 先确认问题是不是产品结构造成的假象
- 78.6%的划伤方差来自产品内波动，只有21.4%来自产品间差异。
- 这意味着“同一产品内部的运行波动”比“不同产品型号差异”更重要。
- 对老板的翻译：不是简单换产品就能解决，核心还是设备/控制过程稳定性。

### 2. 再确认设备是否具备做好能力
- PG22C均值0.8、最大2，证明设备具备低缺陷生产能力。
- 对老板的翻译：不是设备天然做不好，而是设备在某些运行条件下失稳。

### 3. 再看哪些参数和划伤最靠近
- Pearson排序最高的是W1C86/W1C80/W1C81扭矩STD，其次是W1C4B/W1C40速度STD。
- 这些参数都在MD拉伸段。
- 对老板的翻译：问题方向已经从242个参数收敛到了拉伸段扭矩与速度波动。

### 4. 再看图像证据是否和统计方向一致
- 主时序叠加图中，划伤高峰与扭矩/速度波动峰值有同步性。
- 分产品时序图表明FP21、PG32D更敏感，PG22C最稳定。
- 温度断面图中高划伤和低划伤批次几乎重合。

### 5. 用排除法清理掉错误方向
- 温度偏移：排除。
- SG滤网：基本排除。
- 急冷段波动：排除。
- 挤出机参数：排除。
- 产品混杂：基本排除。
- 拉伸比均值：排除。

## 两个竞争假设

### H1
- 扭矩波动 -> 张力不均 -> 薄膜局部微滑移 -> 划伤

### H2
- 速度波动 -> 瞬时拉伸比波动 -> 分子取向不均 -> 应力集中 -> 划伤

### 为什么现在不能二选一
- 扭矩和速度在机械系统里耦合。
- 当前数据是批次级，不是秒级过程数据。
- Spearman不显著，说明批次级Pearson相关不能被过度解读。

## 统计边界必须诚实披露

- 批次级Pearson相关显著，但Spearman不显著。
- 去掉极端批次后，相关会明显衰减。
- 因此“过程失稳方向”是可信的，但“原发是扭矩还是速度”目前不能拍板。

## 给企业的行动建议

### P0 立即做
- 上线秒级扭矩、速度、张力同步采集。
- 对MD拉伸段速度控制回路PI参数做专项排查。
- 把PG22C低缺陷条件整理成基准窗口。

### P1 一周内推进
- 重点检查辊11与辊5-6的扭矩波动来源。
- 做一次针对FP21、PG32D的过程复盘。
- 补做Spearman和离群敏感性复核，作为正式对外版本的统计附页。

### P2 两到四周内形成闭环
- 建立“在线异常波动 -> 质量风险预警”规则。
- 设计H1/H2区分实验：谁先波动、谁驱动谁。
- 把过程稳定性指标纳入班组与设备管理看板。

## 图像解释原则

- 方差分解图：回答“问题在产品间还是产品内”。
- 分产品时间线：回答“设备有没有做好能力、谁更敏感”。
- 相关排序图：回答“该盯哪些参数”。
- 主时序叠加图：回答“质量峰值和过程波动是否同步”。
- 温度断面图：回答“哪些方向可以不再继续投入”。
`;

const index = `# 参考索引

| 文件 | 用途 |
|------|------|
| research_notes.md | 老板汇报主逻辑、证据链与行动建议 |
`;

const userMaterials = `# 用户要求

- 使用 run: 202606080227085_BOPET_scratch_analysis
- 基于 report.md 与整个分析诊断过程制作老板汇报版PPT
- 讲清楚结论、怎么得出结论、证据链是什么
- 要求 figure 有解释说明，能把证据串起来
- 明确告诉企业下一步需要做什么
`;

const slides = [
  {
    file: 'slide-01.html',
    bodyClass: 'warm',
    html: `
${shellHead('#FAF9F6')}
<div class="topline"></div>
<h1 class="title-center" style="top:76pt;font-size:28pt;">BOPET划伤问题已定位到MD拉伸段过程失稳</h1>
<div class="rule" style="top:132pt;left:418pt;width:124pt;"></div>
<p class="subtitle-center" style="top:150pt;">面向企业老板的结论汇报：结论、证据链、统计边界与下一步动作</p>

<div class="card" style="left:58pt;top:208pt;width:534pt;height:198pt;background:#F2EEE7;">
  <h2 class="card-title">这次汇报只回答四个管理层问题</h2>
  <p class="bullet">1. 划伤问题到底是不是产品本身造成的？</p>
  <p class="bullet" style="top:84pt;">2. 哪些过程参数真正值得管理层盯住？</p>
  <p class="bullet" style="top:120pt;">3. 为什么现在不能直接宣布唯一根因？</p>
  <p class="bullet" style="top:156pt;">4. 企业接下来该投入哪些动作来尽快止损？</p>
</div>

<div class="focus-box" style="left:628pt;top:208pt;width:274pt;height:198pt;">
  <p class="focus-label">一句话结论</p>
  <p class="focus-copy">不是温度设定值问题。</p>
  <p class="focus-copy" style="top:76pt;">核心矛盾已收敛到</p>
  <p class="focus-copy strong" style="top:110pt;">MD拉伸段过程稳定性</p>
  <p class="focus-note">但原发机理仍需在线数据区分 H1 / H2</p>
</div>

<p class="footer-left">Run ID: 202606080227085_BOPET_scratch_analysis</p>
${footer(1,12)}
`
  },
  {
    file: 'slide-02.html',
    bodyClass: 'crisp',
    html: `
${shellHead('#FFFFFF')}
<div class="topline crisp"></div>
<h1 class="title-left">先讲结论：不是温度设定值偏移，而是拉伸段过程稳定性失控</h1>

<div class="grid2" style="left:46pt;top:94pt;width:868pt;height:338pt;">
  <div class="pill-card warn">
    <h2 class="mini-title">结论1：问题性质</h2>
    <p>78.6%的划伤方差来自产品内波动，说明问题主要在运行过程，而不是产品结构差异。</p>
  </div>
  <div class="pill-card">
    <h2 class="mini-title">结论2：关注区域</h2>
    <p>最强关联参数集中在MD拉伸段：扭矩STD最高到r=0.49，速度STD次之到r=0.44。</p>
  </div>
  <div class="pill-card">
    <h2 class="mini-title">结论3：反证方向</h2>
    <p>温度断面高低划伤批次几乎重合，温度控制优异，不是当前主根因。</p>
  </div>
  <div class="pill-card warn">
    <h2 class="mini-title">结论4：管理边界</h2>
    <p>当前应宣布“已定位到过程失稳”，不能宣布“已唯一锁定扭矩或速度”。
    统计上仍属于竞争假设集。</p>
  </div>
</div>

<div class="bar-note" style="left:46pt;top:452pt;width:868pt;">
  <p>对老板最重要的翻译：方向已经找对，但还需要一轮在线验证，把“过程失稳”变成“可执行的设备与控制整改”。</p>
</div>
${footer(2,12)}
`
  },
  {
    file: 'slide-03.html',
    bodyClass: 'warm',
    html: `
${shellHead('#FAF9F6')}
<div class="topline"></div>
<h1 class="title-left">我们分析的不是“某个坏批次”，而是55批次持续出现的划伤波动</h1>

<div class="left-stack" style="left:46pt;top:108pt;width:418pt;height:310pt;">
  <div class="stack-card">
    <h2 class="mini-title">分析对象</h2>
    <p>BOPET薄膜双拉加工挤出到纵拉段，目标缺陷是 <b>scratch_count</b>。</p>
  </div>
  <div class="stack-card" style="top:104pt;">
    <h2 class="mini-title">数据覆盖</h2>
    <p>55批次、242个工艺参数、8个产品型号，覆盖预热段、拉伸段、急冷段以及挤出与过滤参数。</p>
  </div>
  <div class="stack-card" style="top:208pt;">
    <h2 class="mini-title">异常形态</h2>
    <p>划伤均值9.5、最大76、偏态2.38，说明少数高缺陷批次会强烈拉高总体风险。</p>
  </div>
</div>

<div class="metric-panel" style="left:506pt;top:108pt;width:408pt;height:310pt;">
  <div class="metric-box">
    <p class="metric-num">55</p>
    <p class="metric-label">分析批次</p>
  </div>
  <div class="metric-box" style="left:208pt;">
    <p class="metric-num">8</p>
    <p class="metric-label">产品型号</p>
  </div>
  <div class="metric-box" style="top:154pt;">
    <p class="metric-num">242</p>
    <p class="metric-label">工艺参数</p>
  </div>
  <div class="metric-box warn" style="left:208pt;top:154pt;">
    <p class="metric-num">76</p>
    <p class="metric-label">单批最高划伤</p>
  </div>
</div>

<p class="callout">这意味着：管理层不能只看平均值，必须盯住“高缺陷尖峰是如何被过程波动放大的”。</p>
${footer(3,12)}
`
  },
  {
    file: 'slide-04.html',
    bodyClass: 'crisp',
    html: `
${shellHead('#FFFFFF')}
<div class="topline crisp"></div>
<h1 class="title-left">第一层证据：问题主要发生在产品内，而不是产品之间</h1>
<div class="placeholder" id="img-variance" style="position:absolute;left:38pt;top:106pt;width:438pt;height:350pt;"></div>

<div class="right-logic" style="left:508pt;top:106pt;width:406pt;height:350pt;">
  <div class="logic-card">
    <h2 class="mini-title">图怎么看</h2>
    <p>78.6% 的划伤方差来自同一产品内部运行波动；产品之间差异只占 21.4%。</p>
  </div>
  <div class="logic-card" style="top:118pt;">
    <h2 class="mini-title">它说明什么</h2>
    <p>如果问题主要来自产品型号，那么不同产品之间的差异应该占大头；现在恰恰相反。</p>
  </div>
  <div class="logic-card accent" style="top:236pt;">
    <h2 class="mini-title">管理含义</h2>
    <p>“换产品就好”不是核心解法，真正要管的是设备与控制过程稳定性。</p>
  </div>
</div>
${footer(4,12)}
`
  },
  {
    file: 'slide-05.html',
    bodyClass: 'warm',
    html: `
${shellHead('#FAF9F6')}
<div class="topline"></div>
<h1 class="title-left">第二层证据：设备具备低缺陷能力，但不同型号对失稳的敏感度不同</h1>
<div class="placeholder" id="img-products" style="position:absolute;left:32pt;top:104pt;width:524pt;height:358pt;"></div>

<div class="annotation-column" style="left:590pt;top:106pt;width:324pt;height:352pt;">
  <div class="note-card">
    <h2 class="mini-title">PG22C 是内部标杆</h2>
    <p>6批均值0.8、最大2，证明设备不是“先天做不好”，而是在某些运行状态下失稳。</p>
  </div>
  <div class="note-card" style="top:120pt;">
    <h2 class="mini-title">FP21 / PG32D 更敏感</h2>
    <p>FP21均值15.5，PG32D出现76的最差批次，说明这两类产品对过程波动更脆弱。</p>
  </div>
  <div class="note-card accent" style="top:240pt;">
    <h2 class="mini-title">图的作用</h2>
    <p>这张图回答老板最关心的一点：我们既看到风险产品，也确认了可复制的低缺陷运行窗口。</p>
  </div>
</div>
${footer(5,12)}
`
  },
  {
    file: 'slide-06.html',
    bodyClass: 'crisp',
    html: `
${shellHead('#FFFFFF')}
<div class="topline crisp"></div>
<h1 class="title-left">第三层证据：参数排序把关注点收敛到MD拉伸段扭矩STD与速度STD</h1>

<div class="explain-left" style="left:42pt;top:108pt;width:332pt;height:344pt;">
  <div class="stack-card accent">
    <h2 class="mini-title">先看排序，不急着谈因果</h2>
    <p>242个参数里，最高相关全部落在MD拉伸段，而且都是“波动量”而不是“设定均值”。</p>
  </div>
  <div class="stack-card" style="top:128pt;">
    <h2 class="mini-title">前五个重点参数</h2>
    <p>W1C86_std 0.487<br/>W1C80_std 0.469<br/>W1C81_std 0.468<br/>W1C4B_std 0.440<br/>W1C40_std 0.428</p>
  </div>
  <div class="stack-card warn" style="top:252pt;">
    <h2 class="mini-title">管理翻译</h2>
    <p>盯住“稳定性波动”比盯“设定目标值”更重要。</p>
  </div>
</div>

<div class="placeholder" id="img-corr" style="position:absolute;left:400pt;top:116pt;width:514pt;height:330pt;"></div>
${footer(6,12)}
`
  },
  {
    file: 'slide-07.html',
    bodyClass: 'warm',
    html: `
${shellHead('#FAF9F6')}
<div class="topline"></div>
<h1 class="title-left">第四层证据：时序叠加把划伤尖峰和拉伸段波动尖峰串到了一起</h1>
<div class="placeholder" id="img-overlay" style="position:absolute;left:34pt;top:92pt;width:892pt;height:282pt;"></div>

  <div class="bottom-triple" style="left:42pt;top:398pt;width:874pt;height:76pt;">
  <div class="mini-panel" style="width:282pt;">
    <h2 class="mini-title">图怎么看</h2>
    <p>高划伤阴影区附近，扭矩STD和速度STD出现更明显峰值，温度均值线则相对平坦。</p>
  </div>
  <div class="mini-panel" style="left:296pt;width:282pt;">
    <h2 class="mini-title">图说明什么</h2>
    <p>质量异常与过程波动同步，而不是与温度均值偏移同步。</p>
  </div>
  <div class="mini-panel accent" style="left:592pt;width:282pt;">
    <h2 class="mini-title">图的边界</h2>
    <p>这是批次级同步，不是秒级先后，因此能定位方向，但不能直接判定原发机理。</p>
  </div>
</div>
${footer(7,12)}
`
  },
  {
    file: 'slide-08.html',
    bodyClass: 'crisp',
    html: `
${shellHead('#FFFFFF')}
<div class="topline crisp"></div>
<h1 class="title-left">第五层证据：温度断面几乎重合，因此温度不是当前主根因</h1>
<div class="placeholder" id="img-zone" style="position:absolute;left:38pt;top:104pt;width:484pt;height:352pt;"></div>

<div class="right-logic" style="left:554pt;top:104pt;width:360pt;height:352pt;">
  <div class="logic-card">
    <h2 class="mini-title">图怎么看</h2>
    <p>高划伤批次与低划伤批次在18辊温度断面上几乎重合，预热、拉伸、急冷三区都没有明显分叉。</p>
  </div>
  <div class="logic-card" style="top:128pt;">
    <h2 class="mini-title">为什么重要</h2>
    <p>这张图给了管理层一个明确减法：当前不需要把主要改善资源继续投在温度设定值微调上。</p>
  </div>
  <div class="logic-card accent" style="top:256pt;">
    <h2 class="mini-title">反证结论</h2>
    <p>温度是“已排除方向”，过程波动才是“应继续深挖方向”。</p>
  </div>
</div>
${footer(8,12)}
`
  },
  {
    file: 'slide-09.html',
    bodyClass: 'warm',
    html: `
${shellHead('#FAF9F6')}
<div class="topline"></div>
<h1 class="title-left">由“排除法 + 关联证据 + 物理机理”收束到两个竞争假设</h1>

<div class="hypothesis-card" style="left:46pt;top:118pt;width:410pt;height:244pt;">
  <p class="hyp-tag">H1</p>
  <h2 class="hyp-title">扭矩波动导致张力不均，进而产生微滑移划伤</h2>
  <p class="hyp-body">逻辑链：扭矩STD升高 -> 张力分布不均 -> 薄膜局部微滑移 -> 表面划伤。</p>
  <p class="hyp-evidence">支撑：W1C86 / W1C80 / W1C81 相关性最高；图像同步组最强。</p>
</div>

<div class="hypothesis-card alt" style="left:502pt;top:118pt;width:410pt;height:244pt;">
  <p class="hyp-tag">H2</p>
  <h2 class="hyp-title">速度控制失稳导致拉伸比波动，进而产生取向不均划伤</h2>
  <p class="hyp-body">逻辑链：速度STD升高 -> 瞬时拉伸比波动 -> 取向与应力不均 -> 表面划伤。</p>
  <p class="hyp-evidence">支撑：W1C4B / W1C40 同样进入前五相关，且与划伤峰值同步。</p>
</div>

<div class="bottom-chain" style="left:46pt;top:388pt;width:866pt;height:72pt;">
  <p><b>为什么现在只到竞争假设集：</b> 扭矩与速度在机械系统里天然耦合，当前又只有批次级数据，所以能确定“拉伸段过程失稳”，但不能诚实地宣布“原发一定是扭矩或速度其中之一”。</p>
</div>
${footer(9,12)}
`
  },
  {
    file: 'slide-10.html',
    bodyClass: 'crisp',
    html: `
${shellHead('#FFFFFF')}
<div class="topline crisp"></div>
<h1 class="title-left">当前最大风险不是没找到方向，而是把批次级相关误当成确定因果</h1>

<div class="grid2" style="left:42pt;top:110pt;width:874pt;height:320pt;">
  <div class="pill-card warn">
    <h2 class="mini-title">统计边界1：Spearman不显著</h2>
    <p>虽然Pearson排序把方向收敛到拉伸段，但Spearman不显著，说明结果可能被极端批次放大。</p>
  </div>
  <div class="pill-card">
    <h2 class="mini-title">统计边界2：去掉极端批次会衰减</h2>
    <p>去除少量极端批次后，相关会明显变弱，因此不能把当前相关值直接当作根因强度。</p>
  </div>
  <div class="pill-card">
    <h2 class="mini-title">稳的部分仍然存在</h2>
    <p>方差分解、NO_RESET、PG22C低缺陷能力、温度排除，这四块证据仍然稳固支撑“过程失稳方向”。</p>
  </div>
  <div class="pill-card accent">
    <h2 class="mini-title">管理层应怎么理解</h2>
    <p>不是推翻结论，而是把结论从“根因已定”修正为“方向已定、原发待证”。这会让整改更可靠。</p>
  </div>
</div>

<p class="callout">真正成熟的汇报，不是把不确定性藏起来，而是告诉管理层下一步怎样把不确定性消掉。</p>
${footer(10,12)}
`
  },
  {
    file: 'slide-11.html',
    bodyClass: 'warm',
    html: `
${shellHead('#FAF9F6')}
<div class="topline"></div>
<h1 class="title-left">下一步不是继续争论，而是设计能区分H1/H2的验证动作</h1>

<div class="roadmap">
  <div class="road-step" style="left:46pt;">
    <p class="step-no">P0</p>
    <h2 class="mini-title">立即动作</h2>
    <p>上线秒级扭矩、速度、张力同步采集；专项排查速度控制回路PI参数；固化PG22C低缺陷基准窗口。</p>
  </div>
  <div class="road-step" style="left:334pt;">
    <p class="step-no">P1</p>
    <h2 class="mini-title">一周内动作</h2>
    <p>重点检查辊11与辊5-6扭矩波动来源；复盘FP21与PG32D；补做Spearman与离群敏感性附页。</p>
  </div>
  <div class="road-step" style="left:622pt;">
    <p class="step-no">P2</p>
    <h2 class="mini-title">两到四周闭环</h2>
    <p>建立在线异常波动预警规则；设计H1/H2区分实验；把过程稳定性指标纳入设备与班组管理看板。</p>
  </div>
</div>

<div class="bottom-chain" style="left:46pt;top:418pt;width:866pt;height:58pt;">
  <p><b>老板要拍的板：</b> 先投数据采集和控制回路排查，再谈根因归责；先稳住过程，再追求机理定论。</p>
</div>
${footer(11,12)}
`
  },
  {
    file: 'slide-12.html',
    bodyClass: 'crisp',
    html: `
${shellHead('#FFFFFF')}
<div class="topline crisp"></div>
<h1 class="title-center" style="top:78pt;font-size:28pt;">管理层决策建议：先稳住过程，再用在线数据定责</h1>
<div class="rule crisp" style="top:136pt;left:430pt;width:100pt;"></div>

<div class="center-card" style="left:144pt;top:176pt;width:672pt;height:92pt;">
  <p class="summary-line">当前最成熟的对外口径应是：<b>划伤问题已定位到MD拉伸段过程稳定性，原发机理处于竞争假设集，需用在线验证闭环。</b></p>
</div>

<div class="decision-grid">
  <div class="decision-card">
    <h2 class="mini-title">请批准</h2>
    <p>秒级在线数据采集与过程看板建设。</p>
  </div>
  <div class="decision-card" style="left:308pt;">
    <h2 class="mini-title">请要求</h2>
    <p>设备、工艺、质量三方联合排查MD拉伸段控制稳定性。</p>
  </div>
  <div class="decision-card" style="left:616pt;">
    <h2 class="mini-title">请明确</h2>
    <p>正式对外结论必须区分“已证实方向”和“待验证机理”。</p>
  </div>
</div>

<p class="footer-left">结论稳住方向，验证决定定责。</p>
${footer(12,12)}
`
  }
];

function shellHead(bg) {
  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{width:960pt;height:540pt;position:relative;overflow:hidden;background:${bg};font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif;color:#1F1F1F}
.topline{position:absolute;top:0;left:0;width:960pt;height:6pt;background:#16324F}
.topline.crisp{background:#0E2A47}
.title-left{position:absolute;left:42pt;top:42pt;width:874pt;font-size:24pt;line-height:1.35;font-weight:700;color:#16324F}
.title-center{position:absolute;left:60pt;width:840pt;text-align:center;line-height:1.35;font-weight:700;color:#16324F}
.subtitle-center{position:absolute;left:90pt;width:780pt;text-align:center;font-size:12pt;color:#6C6A66}
.rule{position:absolute;height:4pt;background:#C7772B;border-radius:3pt}
.rule.crisp{background:#B42318}
.card,.focus-box,.stack-card,.metric-box,.logic-card,.note-card,.hypothesis-card,.road-step,.decision-card,.center-card,.mini-panel,.pill-card,.bar-note,.bottom-chain{position:absolute;border-radius:14pt}
.card-title,.mini-title,.hyp-title{position:absolute;left:18pt;top:16pt;width:calc(100% - 36pt);font-size:16pt;line-height:1.3;font-weight:700;color:#16324F}
.bullet{position:absolute;left:22pt;width:488pt;font-size:13pt;line-height:1.55;color:#1F1F1F}
.focus-box{background:#16324F;color:#FFFFFF;padding:18pt}
.focus-label{position:absolute;left:18pt;top:18pt;font-size:11pt;letter-spacing:1pt;color:#D9E5F2}
.focus-copy{position:absolute;left:18pt;width:238pt;font-size:18pt;line-height:1.45;font-weight:700}
.focus-copy.strong{font-size:22pt;color:#FFD39A}
.focus-note{position:absolute;left:18pt;bottom:18pt;width:238pt;font-size:10.5pt;line-height:1.5;color:#D7DFE8}
.footer-left{position:absolute;left:22pt;bottom:24pt;font-size:9.5pt;color:#6C6A66}
.footer-bar{position:absolute;left:0;bottom:0;width:960pt;height:20pt;border-top:1px solid #DDD3C7}
.footer-bar p{position:absolute;right:22pt;bottom:2pt;font-size:9pt;color:#6C6A66}
.grid2{position:absolute}
.pill-card{position:absolute;width:422pt;height:148pt;background:#EEF4FA;border-left:6pt solid #0E2A47}
.pill-card.warn{background:#FFF4F2;border-left-color:#B42318}
.pill-card p{position:absolute;left:18pt;top:48pt;width:378pt;font-size:12pt;line-height:1.6;color:#222}
.pill-card:nth-child(1){left:0;top:0}
.pill-card:nth-child(2){left:452pt;top:0}
.pill-card:nth-child(3){left:0;top:172pt}
.pill-card:nth-child(4){left:452pt;top:172pt}
.bar-note{height:48pt;background:#16324F;border-radius:12pt}
.bar-note p{position:absolute;left:20pt;top:12pt;width:828pt;font-size:12pt;line-height:1.55;color:#FFF}
.left-stack,.metric-panel,.right-logic,.annotation-column,.explain-left,.bottom-triple,.roadmap,.decision-grid{position:absolute}
.stack-card,.logic-card,.note-card,.mini-panel{left:0;width:100%;height:94pt;background:#F2EEE7}
.stack-card p,.logic-card p,.note-card p,.mini-panel p{position:absolute;left:18pt;top:46pt;width:calc(100% - 36pt);font-size:12pt;line-height:1.6}
.stack-card.accent,.logic-card.accent,.note-card.accent,.pill-card.accent{background:#FFF6EA}
.stack-card.warn{background:#FFF4F2}
.metric-box{width:180pt;height:128pt;background:#F2EEE7;padding:16pt}
.metric-box.warn{background:#FFF4F2}
.metric-num{position:absolute;left:18pt;top:20pt;width:144pt;font-size:38pt;font-weight:700;color:#16324F;text-align:center}
.metric-label{position:absolute;left:18pt;top:78pt;width:144pt;font-size:11pt;text-align:center;line-height:1.5;color:#444}
.callout{position:absolute;left:58pt;top:452pt;width:844pt;font-size:12pt;line-height:1.6;color:#16324F;font-weight:700}
.placeholder{background:#E8ECF0;border:1.5pt dashed #A7B7C7;border-radius:8pt;display:flex;align-items:center;justify-content:center;color:#5B6B7C;font-size:10pt}
.hypothesis-card{background:#F2EEE7;padding:18pt}
.hypothesis-card.alt{background:#EEF4FA}
.hyp-tag{position:absolute;left:18pt;top:14pt;font-size:11pt;font-weight:700;color:#B42318}
.hyp-title{top:38pt;font-size:16pt}
.hyp-body,.hyp-evidence{position:absolute;left:18pt;width:374pt;font-size:12pt;line-height:1.6}
.hyp-body{top:118pt}
.hyp-evidence{top:180pt;color:#444}
.bottom-chain{background:#16324F}
.bottom-chain p{position:absolute;left:20pt;top:14pt;width:826pt;font-size:12pt;line-height:1.55;color:#FFF}
.road-step{top:132pt;width:252pt;height:248pt;background:#F2EEE7;padding:18pt}
.step-no{position:absolute;left:20pt;top:16pt;font-size:28pt;font-weight:700;color:#C7772B}
.road-step p:not(.step-no){position:absolute;left:18pt;top:82pt;width:216pt;font-size:12pt;line-height:1.65}
.decision-card{top:300pt;width:272pt;height:120pt;background:#EEF4FA;border-top:6pt solid #0E2A47}
.decision-card p{position:absolute;left:18pt;top:50pt;width:236pt;font-size:12pt;line-height:1.6}
.center-card{background:#FFF6EA;border:1pt solid #F1D7B0}
.summary-line{position:absolute;left:24pt;top:22pt;width:624pt;font-size:15pt;line-height:1.65;color:#16324F;text-align:center}
</style>
</head>
<body>`;
}

function footer(n, total) {
  return `<div class="footer-bar"><p>${n} / ${total}</p></div></body></html>`;
}

write(path.join(root, 'PLAN.md'), plan);
write(path.join(refsDir, 'research_notes.md'), notes);
write(path.join(refsDir, '_index.md'), index);
write(path.join(refsDir, '_user_materials.md'), userMaterials);

for (const slide of slides) {
  write(path.join(slidesDir, slide.file), slide.html);
}

const compile = `const pptxgen = require('pptxgenjs');
const html2pptx = require(process.env.HOME + '/.claude/skills/huashu-slides/scripts/html2pptx.js');
const path = require('path');
const fs = require('fs');

const ROOT = __dirname;
const SLIDES_DIR = path.join(ROOT, 'slides');
const RUN_DIR = path.resolve(ROOT, '../../workspace/diagnostic-runs/202606080227085_BOPET_scratch_analysis/03_figures');

const IMAGE_MAP = {
  'img-variance': path.join(RUN_DIR, 'fig_variance_decomposition.png'),
  'img-products': path.join(RUN_DIR, 'fig_product_timelines.png'),
  'img-corr': path.join(RUN_DIR, 'fig_torque_correlation.png'),
  'img-overlay': path.join(RUN_DIR, 'fig_master_time_aligned_overlay.png'),
  'img-zone': path.join(RUN_DIR, 'fig_zone_profile.png')
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.author = 'Codex';
  pptx.company = 'OpenAI';
  pptx.subject = 'BOPET scratch CEO report';
  pptx.title = 'BOPET划伤老板汇报';
  pptx.lang = 'zh-CN';

  const slideFiles = fs.readdirSync(SLIDES_DIR)
    .filter((f) => /^slide-\\d+\\.html$/.test(f))
    .sort((a, b) => Number(a.match(/\\d+/)[0]) - Number(b.match(/\\d+/)[0]));

  for (const htmlFile of slideFiles) {
    const htmlPath = path.join(SLIDES_DIR, htmlFile);
    const { slide, placeholders } = await html2pptx(htmlPath, pptx);
    for (const ph of placeholders) {
      const imgPath = IMAGE_MAP[ph.id];
      if (imgPath && fs.existsSync(imgPath)) {
        slide.addImage({ path: imgPath, x: ph.x, y: ph.y, w: ph.w, h: ph.h });
      }
    }
  }

  const outPath = path.join(ROOT, 'BOPET_划伤问题老板汇报_20260608.pptx');
  await pptx.writeFile({ fileName: outPath });
  const stat = fs.statSync(outPath);
  console.log(JSON.stringify({ outPath, pages: slideFiles.length, size: stat.size }, null, 2));
})().catch((err) => {
  console.error(err);
  process.exit(1);
});
`;

write(path.join(root, 'compile.cjs'), compile);

console.log(`Generated assets in ${root}`);
