import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(
  '/Volumes/laxer/codes/skills/industrial-deep-diagnostic/ppt_workspace/bopet_scratch_ceo_report_20260608_run1100505'
);
const RUN_DIR = path.resolve(
  '/Volumes/laxer/codes/skills/industrial-deep-diagnostic/workspace/diagnostic-runs/202606081100505_BOPET_scratch_diagnosis'
);
const SLIDES_DIR = path.join(ROOT, 'slides');
const REFS_DIR = path.join(ROOT, 'references');

const ensureDir = (dir) => fs.mkdirSync(dir, { recursive: true });
const write = (file, content) => {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, content, 'utf8');
};

const styleBlock = `
*{margin:0;padding:0;box-sizing:border-box}
body{
  width:960pt;height:540pt;position:relative;overflow:hidden;
  background:#FBFAF7;color:#1E2430;
  font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif
}
.topline{position:absolute;left:0;top:0;width:960pt;height:5pt;background:#1C3144}
.topline.crisp{background:#B3472E}
.bottomline{position:absolute;left:34pt;bottom:28pt;width:892pt;height:1.2pt;background:#D7D2CA}
.page{position:absolute;right:38pt;bottom:10pt;font-size:9pt;color:#6E6A64}
.eyebrow{position:absolute;left:42pt;top:26pt;font-size:9.5pt;letter-spacing:1.4pt;color:#8A5A3B}
.title{position:absolute;left:42pt;top:48pt;width:876pt;font-size:25pt;line-height:1.32;font-weight:700;color:#1C3144}
.title.small{font-size:23pt}
.subtitle{position:absolute;left:42pt;top:112pt;width:876pt;font-size:12pt;line-height:1.65;color:#6A6762}
.rule{position:absolute;left:42pt;top:102pt;width:110pt;height:3pt;background:#B3472E;border-radius:2pt}
.card{
  position:absolute;border:1.1pt solid #D9D4CC;border-radius:14pt;background:#FFFFFF
}
.card.soft{background:#F4F1EA}
.card.accent{background:#FFF5EE;border-color:#E7C8B9}
.card.blue{background:#F1F6FA;border-color:#C8D7E3}
.card.dark{background:#1C3144;border-color:#1C3144}
.card h2{
  position:absolute;left:18pt;top:14pt;width:calc(100% - 36pt);
  font-size:15pt;line-height:1.35;font-weight:700;color:#1C3144
}
.card.dark h2,.card.dark p,.card.dark li{color:#FFFFFF}
.card p{
  position:absolute;left:18pt;width:calc(100% - 36pt);
  font-size:11.5pt;line-height:1.62;color:#20242B
}
.card ul{
  position:absolute;left:28pt;top:50pt;width:calc(100% - 52pt);
  font-size:11.5pt;line-height:1.62;color:#20242B;padding-left:16pt
}
.card.dark ul{color:#FFFFFF}
.kpi{
  position:absolute;border:1.1pt solid #D9D4CC;border-radius:14pt;background:#FFFFFF
}
.kpi-num{
  position:absolute;left:14pt;top:16pt;width:calc(100% - 28pt);
  font-size:28pt;line-height:1.2;font-weight:700;text-align:center;color:#1C3144
}
.kpi-label{
  position:absolute;left:14pt;top:60pt;width:calc(100% - 28pt);
  font-size:10pt;line-height:1.55;text-align:center;color:#5E5A54
}
.pill{
  position:absolute;height:24pt;padding:0 12pt;border:1pt solid #C8D7E3;border-radius:999pt;background:#F5F9FC
}
.pill p{
  position:absolute;left:0;top:4pt;width:100%;font-size:10pt;line-height:1.3;font-weight:700;text-align:center;color:#1C3144
}
.term{
  position:absolute;border:1.1pt solid #D9D4CC;border-radius:12pt;background:#FFFFFF
}
.term h3{
  position:absolute;left:16pt;top:14pt;width:calc(100% - 32pt);
  font-size:14pt;line-height:1.35;font-weight:700;color:#1C3144
}
.term p{
  position:absolute;left:16pt;width:calc(100% - 32pt);font-size:11pt;line-height:1.62;color:#232831
}
.line{
  position:absolute;height:1.2pt;background:#1C3144
}
.line.accent{background:#B3472E}
.vline{
  position:absolute;width:1.2pt;background:#1C3144
}
.dot{
  position:absolute;width:10pt;height:10pt;border-radius:999pt;background:#B3472E
}
.node{
  position:absolute;border:1.2pt solid #1C3144;border-radius:12pt;background:#FFFFFF
}
.node h3{
  position:absolute;left:12pt;top:12pt;width:calc(100% - 24pt);
  font-size:13pt;line-height:1.35;font-weight:700;color:#1C3144;text-align:center
}
.node p{
  position:absolute;left:12pt;width:calc(100% - 24pt);font-size:10.5pt;line-height:1.55;color:#27303B;text-align:center
}
.arrow{
  position:absolute;font-size:20pt;line-height:1;color:#1C3144
}
.placeholder{
  position:absolute;border:1.2pt dashed #B7C3CE;border-radius:12pt;background:#F7F9FB
}
.note{
  position:absolute;border-left:3pt solid #B3472E;padding-left:12pt
}
.note p{
  position:absolute;left:12pt;width:calc(100% - 12pt);font-size:11pt;line-height:1.6;color:#1C3144
}
`;

const html = (pageNo, bodyContent) => `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>${styleBlock}</style>
</head>
<body>
${bodyContent}
<div class="bottomline"></div>
<p class="page">${pageNo} / 12</p>
</body>
</html>
`;

const plan = `# PPT制作规划文件

## 一、基本信息

| 字段 | 值 |
|------|-----|
| PPT标题 | BOPET划伤诊断：已确认主矛盾，但不能过早宣布单一根因 |
| 副标题 | 面向企业老板的汇报版本：讲清结论、推理过程、证据链和下一步动作 |
| 总页数 | 12页（其中5页使用诊断原始figure，7页为线条风格解释页） |
| 制作引擎 | huashu-slides 风格约束 + html2pptx 组装 |
| 路径 | Path A（可编辑HTML） |
| 风格 | 线条简约商务风（Warm Academic 基底，局部 Crisp 强调） |
| **比例** | **16:9（960pt×540pt）** |
| 语言 | 中文 |
| 受众 | 企业老板 + 制造管理层 |
| 研究笔记 | ppt_workspace/bopet_scratch_ceo_report_20260608_run1100505/references/ |

## 二、风格参数速查

### 线条简约商务风
- 页面底色: #FBFAF7
- 主线条色: #1C3144
- 强调色: #B3472E
- 正文色: #1E2430
- 辅助色: #6A6762
- 卡片底色: #FFFFFF / #F4F1EA / #F1F6FA
- 标题字体: Microsoft YaHei Bold, 23-25pt
- 正文字体: Microsoft YaHei Regular, 10.5-12pt
- 设计原则: 留白优先、细线框、少色块、每页一个主结论、每张图都配“老板翻译”

## 三、逐页规划

### 第1页：封面
- **标题**: BOPET划伤诊断：已确认主矛盾，但不能过早宣布单一根因
- **密度**: 中等
- **论证逻辑**: 先把老板最关心的两个判断放在封面上：方向已收敛，单根因未锁定
- **视觉主角**: 右侧深色结论卡
- **布局**: 左侧汇报目标卡 + 右侧一句话结论卡，底部一行run信息
- **图片决策**: text-only

### 第2页：老板先记住什么
- **标题**: 这次汇报最重要的，不是“找到了唯一参数”，而是“知道该怎么继续缩小范围”
- **密度**: 中等
- **论证逻辑**: 将“能确认 / 不能确认 / 已纠偏 / 要行动”拆开
- **视觉主角**: 四象限结论卡
- **布局**: 2×2非对称卡片网格
- **图片决策**: text-only

### 第3页：先把产线和数据讲明白
- **标题**: 分析对象是MD纵拉段18根辊的稳定性，不是单个设备点位的孤立异常
- **密度**: 中等
- **论证逻辑**: 解释预热、拉伸、急冷、Tg等术语，让老板知道我们在看哪一段
- **视觉主角**: 中央线条式产线流程图
- **布局**: 左侧术语和数据范围，右侧产线流程框图
- **图片决策**: text-only

### 第4页：证据链是怎么收束的
- **标题**: 我们不是凭感觉下结论，而是按“分层、纠偏、排除、保留”的顺序逐步收束
- **密度**: 中等
- **论证逻辑**: 交代诊断过程，避免老板觉得只是看了几张图
- **视觉主角**: 五节点证据链流程
- **布局**: 中部横向步骤图 + 下方证据说明带
- **图片决策**: text-only

### 第5页：Figure 1
- **标题**: 型号差异是当前最稳的统计信号：不同型号的划伤基线相差30倍以上
- **密度**: 中等
- **论证逻辑**: 先证明“型号基线”是目前最强信号
- **视觉主角**: scratch by model 原始图
- **布局**: 左图右侧三层解释卡
- **图片决策**: 使用原始figure

### 第6页：Figure 2
- **标题**: 5号辊扭矩波动看起来像最强关联，但严格纠偏后不能再当作单一根因
- **密度**: 深度
- **论证逻辑**: 讲清 Pearson、Spearman、离群点，解释什么叫“伪相关”
- **视觉主角**: W1C80散点图
- **布局**: 左图右文，右侧上中下三层解释
- **图片决策**: 使用原始figure

### 第7页：Figure 3
- **标题**: 型号内趋势并不一致，这说明除了型号差异，还存在尚未被直接测到的过程退化因素
- **密度**: 中等
- **论证逻辑**: 说明为什么 H3 虽然最强，但还不是最终物理根因
- **视觉主角**: per-model trends 原始图
- **布局**: 上图下文，底部三卡总结
- **图片决策**: 使用原始figure

### 第8页：Figure 4
- **标题**: 温度不是现在最应该继续押注的方向：主数据里方向不稳、量级也不够解释全部划伤
- **密度**: 中等
- **论证逻辑**: 用温度图解释“不是所有看起来有差别的参数都能当根因”
- **视觉主角**: temperature zone profile 原始图
- **布局**: 左图右侧术语卡 + 结论卡
- **图片决策**: 使用原始figure

### 第9页：Figure 5
- **标题**: 主时序图把质量尖峰和过程波动串起来了，但批次级数据还不足以判定谁先谁后
- **密度**: 深度
- **论证逻辑**: 向老板解释“为什么方向可信，但因果链还差一步”
- **视觉主角**: master time aligned overlay 原始图
- **布局**: 上图下方三栏解释
- **图片决策**: 使用原始figure

### 第10页：统计边界和术语翻译
- **标题**: 听懂这四个词，就能明白为什么这次结论必须讲得既坚定又克制
- **密度**: 中等
- **论证逻辑**: 给老板翻译专业词，提升汇报可理解性
- **视觉主角**: 四张术语卡
- **布局**: 2×2术语卡 + 底部一句话总结
- **图片决策**: text-only

### 第11页：下一步企业该做什么
- **标题**: 下一步不是继续争论，而是用在线数据和对照实验把 H1、H2、H3 真正分开
- **密度**: 中等
- **论证逻辑**: 给出分阶段行动清单和责任分工
- **视觉主角**: 三阶段行动路线图
- **布局**: 三列路线卡 + 底部责任提醒
- **图片决策**: text-only

### 第12页：汇报收口
- **标题**: 管理层现在要拍板的，是“验证资源”和“协同机制”，不是替技术团队提前选答案
- **密度**: 中等
- **论证逻辑**: 把决策请求说清楚
- **视觉主角**: 右侧三条决策请求卡
- **布局**: 左侧收束句，右侧三张决策卡
- **图片决策**: text-only

## 四、配图生成清单

| 序号 | 文件名 | 对应页码 | 来源 |
|------|--------|---------|------|
| 1 | fig1_scratch_by_model.png | 5 | 诊断run原始figure |
| 2 | fig3_w1c80_std_vs_scratch.png | 6 | 诊断run原始figure |
| 3 | fig4_per_model_scratch_trends.png | 7 | 诊断run原始figure |
| 4 | fig2_temperature_zone_profile.png | 8 | 诊断run原始figure |
| 5 | fig_master_time_aligned_overlay.png | 9 | 诊断run原始figure |

## 五、技术规范

- slide尺寸: 960pt×540pt
- 顶部签名线: 5pt 深蓝
- 页码: 右下角 9pt
- 图片插入: placeholder div + compile.cjs addImage
- 编码: UTF-8
- 说明要求: 每张图必须附“图怎么看 / 图说明什么 / 图的边界”
`;

const researchNotes = `# BOPET划伤老板汇报研究底稿

## 1. 汇报核心口径

- 这次最稳的结论不是“已经锁定唯一工艺根因”，而是：
  当前最强、最可重复的信号是**产品型号基线差异**；现有工艺参数证据还不足以宣布某一个参数是唯一根因。
- 诊断类型是 **COMPETING_SET**，整体置信度 **45/100**。
- 对经营层最合适的表达是：
  **方向已收敛，单根因未锁定；先用验证动作缩小不确定性，再做过程整改定责。**

## 2. 这次分析到底看了什么

- 生产场景：BOPET 薄膜 MD 纵拉段划伤缺陷诊断
- 主数据集：55批次
- 辅助数据集：149批次
- 参数规模：266个工艺参数
- 工艺结构：18根纵拉辊，分为预热段、拉伸段、急冷定型段

## 3. 老板先要记住的四句话

1. **最稳的信号是型号差异，不是某个单一温度点位。**
2. **此前看起来很强的扭矩相关，已经被纠正为“可能受极端离群批次放大”的伪相关。**
3. **我们能定位到方向，但还不能直接宣布“5号辊扭矩”或“温度”就是唯一根因。**
4. **下一步最重要的是补在线秒级数据、记录型号设定值，并做对照实验。**

## 4. 证据链主线

### 4.1 型号差异先站出来

- 55行主数据集中，8种型号的划伤均值差异达到30倍以上。
- 代表性对比：PG22C 均值约 0.83，PG32D 均值约 25.7。
- 这说明“不同型号自带不同划伤基线”是当前最稳的统计事实。

### 4.2 扭矩相关需要纠偏，不能直接拿来下结论

- 历史上看起来最强的信号是 FP21 型号内 5#辊扭矩标准差与划伤的 Pearson 相关。
- 但在149行全数据集里，这个高相关被一个极端离群批次显著拉高。
- 报告给出的关键纠偏结果：
  - Pearson r = 0.935
  - Spearman rho = 0.2504
  - delta = 0.6846
- 对老板的翻译：
  **图上看起来像一条直线，不代表大多数批次都遵循这个规律；有时只是被极少数异常点“拽”出来的。**

### 4.3 温度不是当前最值得继续押注的方向

- 55行主数据里，预热段温度与划伤是负相关。
- 149行全数据里，同一关系却变成正相关。
- 方向反转意味着这个变量受混杂或极端批次影响大，不能作为稳定结论。
- 同时，温度波动本身很小，量级不足以独自解释全部划伤差异。

### 4.4 型号内趋势又提醒我们：型号不是全部答案

- PG31DS 和 PG32B 在各自型号内部出现上升趋势。
- 这说明除了“型号自带基线”之外，还可能存在未被直接测量到的过程退化因素，例如辊面状态、张力波动、轴承/机械状态等。

### 4.5 主时序图说明方向可信，但批次级数据还不足以定单根因

- 质量尖峰与部分过程波动尖峰在批次级时间线上能对齐。
- 但 time_sorted=null，而且当前不是秒级过程数据。
- 所以我们可以说“方向上高度怀疑是过程稳定性问题”，但不能说“已经证明谁先谁后、谁驱动谁”。

## 5. 关键专业词的老板翻译

- **Tg（玻璃化转变温度）**：
  材料从“比较硬、比较脆的状态”转向“开始变软、可以被拉伸的状态”的温度门槛。PET 的 Tg 大约在 75°C。
- **Pearson相关**：
  看两个量是否沿着一条直线一起变大或变小。
- **Spearman相关**：
  不看绝对大小，只看大小规律是否一致，更适合偏态或异常点很多的数据。
- **离群点**：
  极少数特别异常的大值，会把一条“看起来很强”的相关关系硬拉出来。
- **COMPETING_SET**：
  不是没方向，而是还有多个假设同时成立，现有证据还不足以宣布唯一答案。

## 6. 给企业的下一步动作

### P0 立即做（本周内）

- 在 FP21、PG32D 等敏感型号上补采秒级扭矩、速度、张力同步数据。
- 统一记录每个型号的完整工艺设定值、厚度和配方信息。
- 固化 PG22C 等低缺陷型号的“好窗口”作为对照基准。

### P1 两周内做

- 安排同型号对照实验，分辨 H1（扭矩链）与 H2（速度/拉伸比链）。
- 记录辊面维护、滤网更换、设备状态事件时间戳。
- 复盘149批全数据中极端批次，单独分析其共同特征。

### P2 一个月内做

- 建立“过程波动异常 -> 质量风险预警”规则。
- 视条件加装 5#辊张力或更直接的在线测量手段。
- 将型号切换管理纳入质量治理，而不是仅当作生产排程问题。

## 7. 汇报页与图的对应关系

- 第5页 figure：回答“当前最稳的差异来自哪里”
- 第6页 figure：回答“为什么不能被表面强相关误导”
- 第7页 figure：回答“为什么 H3 最强但还不够最终”
- 第8页 figure：回答“为什么温度不是首要整改方向”
- 第9页 figure：回答“为什么方向可信但单根因仍需验证”
`;

const userMaterials = `# 用户要求整理

- 使用 workspace/diagnostic-runs/202606081100505_BOPET_scratch_diagnosis/report.md
- 要把结论、怎么得出结论、证据链、下一步企业动作讲清楚
- 给企业老板汇报，要求逻辑完整，不跳脱
- 所有关键 figure 都要解释，能把证据串起来
- 要使用线条风格的简约风 PPT
- 专业名词需要翻译成老板听得懂的话
`;

const indexMd = `# 参考索引

| 文件 | 用途 |
|------|------|
| research_notes.md | 老板汇报的逻辑主线、证据链、术语翻译与行动建议 |
| _user_materials.md | 用户目标和使用的诊断run说明 |
`;

const compileCjs = `const fs = require('fs');
const path = require('path');
const pptxgen = require('/Users/haozhengzhang/.cc-switch/skills/ppt-auto-builder/node_modules/pptxgenjs');
const html2pptx = require('/Users/haozhengzhang/.cc-switch/skills/huashu-slides/scripts/html2pptx.js');

const ROOT = __dirname;
const SLIDES_DIR = path.join(ROOT, 'slides');
const RUN_DIR = path.resolve(ROOT, '../../workspace/diagnostic-runs/202606081100505_BOPET_scratch_diagnosis/03_figures');

const IMAGE_MAP = {
  'img-model': path.join(RUN_DIR, 'fig1_scratch_by_model.png'),
  'img-scatter': path.join(RUN_DIR, 'fig3_w1c80_std_vs_scratch.png'),
  'img-trends': path.join(RUN_DIR, 'fig4_per_model_scratch_trends.png'),
  'img-temp': path.join(RUN_DIR, 'fig2_temperature_zone_profile.png'),
  'img-overlay': path.join(RUN_DIR, 'fig_master_time_aligned_overlay.png')
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.author = 'Codex';
  pptx.company = 'OpenAI';
  pptx.subject = 'BOPET scratch diagnosis CEO report';
  pptx.title = 'BOPET划伤诊断老板汇报';
  pptx.lang = 'zh-CN';

  const slideFiles = fs.readdirSync(SLIDES_DIR)
    .filter((file) => /^slide-\\d+\\.html$/.test(file))
    .sort((a, b) => Number(a.match(/\\d+/)[0]) - Number(b.match(/\\d+/)[0]));

  for (const slideFile of slideFiles) {
    const htmlPath = path.join(SLIDES_DIR, slideFile);
    const { slide, placeholders } = await html2pptx(htmlPath, pptx);
    for (const ph of placeholders) {
      const imgPath = IMAGE_MAP[ph.id];
      if (imgPath && fs.existsSync(imgPath)) {
        slide.addImage({ path: imgPath, x: ph.x, y: ph.y, w: ph.w, h: ph.h });
      }
    }
  }

  const outPath = path.join(ROOT, 'BOPET_划伤诊断老板汇报_20260608.pptx');
  await pptx.writeFile({ fileName: outPath });
  const stat = fs.statSync(outPath);
  console.log(JSON.stringify({ outPath, pages: slideFiles.length, size: stat.size }, null, 2));
})().catch((error) => {
  console.error(error);
  process.exit(1);
});
`;

const slides = [
  html(
    1,
    `
<div class="topline"></div>
<p class="eyebrow">BOPET SCRATCH DIAGNOSIS</p>
<h1 class="title">BOPET划伤诊断：已确认主矛盾，但不能过早宣布单一根因</h1>
<div class="rule"></div>
<p class="subtitle">这是一份给企业老板的汇报版本。目标不是展示“分析做了多少”，而是讲清楚四件事：现在最稳的结论是什么、它是怎么得出来的、哪些地方还不能过度下结论、下一步企业要做什么。</p>

<div class="card soft" style="left:42pt;top:164pt;width:468pt;height:258pt;">
  <h2>这次汇报只回答四个管理层问题</h2>
  <ul>
    <li>当前最稳的结论到底是什么？</li>
    <li>证据链是如何一层一层收束出来的？</li>
    <li>为什么现在还不能替团队提前宣布唯一根因？</li>
    <li>企业下一步要投入哪些验证和治理动作？</li>
  </ul>
</div>

<div class="card dark" style="left:540pt;top:164pt;width:378pt;height:258pt;">
  <h2>一句话结论</h2>
  <p style="top:66pt;font-size:19pt;line-height:1.55;font-weight:700;">方向已经收敛。</p>
  <p style="top:108pt;font-size:22pt;line-height:1.45;font-weight:700;color:#FFD9C8;">当前主矛盾是“划伤表现受型号基线强影响，且过程稳定性证据不足以锁定唯一工艺根因”。</p>
  <p style="top:196pt;font-size:11pt;line-height:1.6;color:#D8E4EC;">经营层需要支持的是验证资源和跨部门协同，而不是现在就替技术团队拍板“就是某个参数”。</p>
</div>

<div class="card blue" style="left:42pt;top:440pt;width:876pt;height:54pt;">
  <p style="top:15pt;font-size:10.5pt;line-height:1.5;">Run ID: 202606081100505_BOPET_scratch_diagnosis ｜ 主数据 55批次，辅助数据 149批次 ｜ 诊断类型：COMPETING_SET ｜ 报告判定：Judge 91/100 PASS</p>
</div>
`
  ),
  html(
    2,
    `
<div class="topline crisp"></div>
<p class="eyebrow">EXECUTIVE TAKEAWAYS</p>
<h1 class="title small">这次汇报最重要的，不是“找到了唯一参数”，而是“知道该怎样继续缩小范围”</h1>
<div class="rule"></div>

<div class="card" style="left:42pt;top:138pt;width:418pt;height:150pt;">
  <h2>现在能确认</h2>
  <p style="top:56pt;">型号基线差异是当前最稳、最可重复的统计信号。不同型号的划伤均值在主数据中相差30倍以上，说明“产品条件差异”必须先被控制住。</p>
</div>

<div class="card accent" style="left:500pt;top:138pt;width:418pt;height:150pt;">
  <h2>现在不能确认</h2>
  <p style="top:56pt;">不能把 5#辊扭矩、温度偏移或某一个单独参数，直接对外宣布为唯一根因。现有数据只能支持“若干竞争假设并存”。</p>
</div>

<div class="card blue" style="left:42pt;top:308pt;width:418pt;height:150pt;">
  <h2>已经被纠偏</h2>
  <p style="top:56pt;">此前看起来很强的相关关系，经过 Spearman 和离群值检查后，被纠正为“可能由极端批次放大”的伪相关。这个纠偏非常关键，避免企业押错方向。</p>
</div>

<div class="card soft" style="left:500pt;top:308pt;width:418pt;height:150pt;">
  <h2>企业要立刻做什么</h2>
  <p style="top:56pt;">补秒级在线数据、记录每个型号的完整设定值、安排同型号对照实验。下一步最重要的是让 H1 / H2 / H3 真正可区分，而不是继续靠批次级相关猜答案。</p>
</div>
`
  ),
  html(
    3,
    `
<div class="topline"></div>
<p class="eyebrow">PROCESS AND DATA</p>
<h1 class="title small">分析对象是 MD 纵拉段 18 根辊的稳定性，不是单个设备点位的孤立异常</h1>
<div class="rule"></div>

<div class="card soft" style="left:42pt;top:140pt;width:248pt;height:322pt;">
  <h2>先把术语翻成老板能听懂的话</h2>
  <p style="top:56pt;"><b>Tg</b>：材料开始从“偏硬”转向“可以被拉伸”的温度门槛，PET 大约在 75°C。</p>
  <p style="top:124pt;"><b>预热段</b>：先把薄膜加到接近可拉伸状态。</p>
  <p style="top:174pt;"><b>拉伸段</b>：真正把薄膜拉开的关键区，也是表面最容易出问题的敏感区。</p>
  <p style="top:242pt;"><b>急冷段</b>：把状态快速固定下来，防止后续继续变化。</p>
</div>

<div class="card" style="left:308pt;top:140pt;width:610pt;height:150pt;">
  <h2>产线可以简化理解成三段</h2>
  <div class="card blue" style="left:18pt;top:56pt;width:176pt;height:72pt;">
    <h2 style="font-size:13pt;">预热段</h2>
    <p style="top:36pt;font-size:10.5pt;">1-5#辊，约75-76°C，让薄膜接近可拉伸状态。</p>
  </div>
  <div class="card accent" style="left:214pt;top:56pt;width:176pt;height:72pt;">
    <h2 style="font-size:13pt;">拉伸段</h2>
    <p style="top:36pt;font-size:10.5pt;">6-11#辊，约82-83°C，真正把薄膜拉开，是本次关注核心。</p>
  </div>
  <div class="card soft" style="left:410pt;top:56pt;width:182pt;height:72pt;">
    <h2 style="font-size:13pt;">急冷段</h2>
    <p style="top:36pt;font-size:10.5pt;">12-18#辊，约31-36°C，把状态固定下来。</p>
  </div>
</div>

<div class="card accent" style="left:308pt;top:308pt;width:610pt;height:54pt;">
  <p style="top:16pt;font-size:10.8pt;line-height:1.5;">老板翻译：薄膜最容易积累划伤风险的，是“开始变软后被真正拉开”的这段，也就是本次重点看的 MD 拉伸段。</p>
</div>

<div class="card blue" style="left:308pt;top:378pt;width:610pt;height:84pt;">
  <h2>这次数据覆盖了什么</h2>
  <p style="top:46pt;">主数据 55 批次，辅助数据 149 批次；共分析 266 个参数，包括 18 根辊的温度、速度、扭矩与相关工艺变量。也就是说，我们不是只盯一个点位，而是对整段稳定性做了扫描。</p>
</div>
`
  ),
  html(
    4,
    `
<div class="topline"></div>
<p class="eyebrow">REASONING CHAIN</p>
<h1 class="title small">我们不是凭感觉下结论，而是按“分层、纠偏、排除、保留”的顺序逐步收束</h1>
<div class="rule"></div>

<div class="node" style="left:42pt;top:172pt;width:146pt;height:112pt;">
  <h3>第一步</h3>
  <p style="top:44pt;">先看数据分布和型号差异</p>
  <p style="top:74pt;">判断问题是在产品间还是产品内</p>
</div>
<p class="arrow" style="left:198pt;top:214pt;">→</p>
<div class="node" style="left:226pt;top:172pt;width:146pt;height:112pt;">
  <h3>第二步</h3>
  <p style="top:44pt;">看相关图</p>
  <p style="top:74pt;">把可疑参数先找出来</p>
</div>
<p class="arrow" style="left:382pt;top:214pt;">→</p>
<div class="node" style="left:410pt;top:172pt;width:146pt;height:112pt;">
  <h3>第三步</h3>
  <p style="top:44pt;">做 Spearman / 离群值检查</p>
  <p style="top:74pt;">把表面强相关纠偏</p>
</div>
<p class="arrow" style="left:566pt;top:214pt;">→</p>
<div class="node" style="left:594pt;top:172pt;width:146pt;height:112pt;">
  <h3>第四步</h3>
  <p style="top:44pt;">排除温度、过滤器等弱方向</p>
  <p style="top:74pt;">识别仍然存活的假设</p>
</div>
<p class="arrow" style="left:750pt;top:214pt;">→</p>
<div class="node" style="left:778pt;top:172pt;width:140pt;height:112pt;">
  <h3>第五步</h3>
  <p style="top:44pt;">输出 COMPETING_SET</p>
  <p style="top:74pt;">并给出下一步验证动作</p>
</div>

<div class="card dark" style="left:42pt;top:330pt;width:876pt;height:114pt;">
  <h2>这条证据链的意义</h2>
  <p style="top:58pt;">它保证我们的结论不是“谁看图更像谁就算谁”，而是每往前走一步，都在缩小不确定性：先找大信号，再纠偏，再排除，最后把剩下的假设交给验证动作去区分。</p>
</div>

<div class="card accent" style="left:42pt;top:458pt;width:876pt;height:38pt;">
  <p style="top:10pt;font-size:10.5pt;line-height:1.45;">老板翻译：这次不是“没找到答案”，而是“已经把问题范围缩小到值得投入验证资源的程度”。</p>
</div>
`
  ),
  html(
    5,
    `
<div class="topline"></div>
<p class="eyebrow">FIGURE 1</p>
<h1 class="title small">型号差异是当前最稳的统计信号：不同型号的划伤基线相差 30 倍以上</h1>
<div class="rule"></div>

<div class="placeholder" id="img-model" style="left:42pt;top:146pt;width:560pt;height:314pt;"></div>

<div class="card soft" style="left:628pt;top:146pt;width:290pt;height:94pt;">
  <h2>图怎么看</h2>
  <p style="top:50pt;">这是箱线图。中间的线看“典型水平”，盒子的高度看“波动范围”，离散点看“异常高值”。</p>
</div>

<div class="card blue" style="left:628pt;top:256pt;width:290pt;height:100pt;">
  <h2>图说明什么</h2>
  <p style="top:50pt;">PG22C 长期低划伤，而 PG32D、FP21 等型号基线明显更高。当前最稳的信号先来自“型号差异”，不是单个工艺参数。</p>
</div>

<div class="card accent" style="left:628pt;top:372pt;width:290pt;height:88pt;">
  <h2>图的边界</h2>
  <p style="top:50pt;">型号差异说明“条件不同”，但它本身不是最终物理根因。它告诉我们：后续分析必须先分型号再谈参数。</p>
</div>
`
  ),
  html(
    6,
    `
<div class="topline crisp"></div>
<p class="eyebrow">FIGURE 2</p>
<h1 class="title small">5号辊扭矩波动看起来像最强关联，但严格纠偏后不能再当作单一根因</h1>
<div class="rule"></div>

<div class="placeholder" id="img-scatter" style="left:42pt;top:146pt;width:500pt;height:314pt;"></div>

<div class="card soft" style="left:568pt;top:146pt;width:350pt;height:100pt;">
  <h2>图怎么看</h2>
  <p style="top:50pt;">散点图是看“一个参数变大时，缺陷是不是也跟着变大”。不同颜色代表不同型号，所以能看到“是不是只有某个型号在拉高相关”。</p>
</div>

<div class="card accent" style="left:568pt;top:262pt;width:350pt;height:116pt;">
  <h2>关键纠偏</h2>
  <p style="top:50pt;">149批全数据里，FP21 的 Pearson r = 0.935，但 Spearman rho 只有 0.2504，而且主要受一个极端批次拉动。对老板的翻译：表面很直，不代表大多数批次都遵守这条关系。</p>
</div>

<div class="card blue" style="left:568pt;top:394pt;width:350pt;height:66pt;">
  <h2>结论</h2>
  <p style="top:40pt;">扭矩波动仍是值得盯住的方向，但现在不能对外说“它就是唯一根因”。</p>
</div>
`
  ),
  html(
    7,
    `
<div class="topline"></div>
<p class="eyebrow">FIGURE 3</p>
<h1 class="title small">型号内趋势并不一致，这说明除了型号差异，还存在尚未被直接测到的过程退化因素</h1>
<div class="rule"></div>

<div class="placeholder" id="img-trends" style="left:42pt;top:144pt;width:876pt;height:260pt;"></div>

<div class="card soft" style="left:42pt;top:420pt;width:280pt;height:76pt;">
  <h2>图怎么看</h2>
  <p style="top:42pt;">不要只看全局均值，要看同一个型号内部是稳定、上升还是混乱。</p>
</div>

<div class="card blue" style="left:340pt;top:420pt;width:280pt;height:76pt;">
  <h2>图说明什么</h2>
  <p style="top:42pt;">PG31DS、PG32B 在型号内有上升趋势，说明“型号基线”不是全部答案，可能还有过程退化因素。</p>
</div>

<div class="card accent" style="left:638pt;top:420pt;width:280pt;height:76pt;">
  <h2>图的边界</h2>
  <p style="top:42pt;">趋势存在，不代表已经知道退化源头。可能是辊面、张力、机械状态等未测因素。</p>
</div>
`
  ),
  html(
    8,
    `
<div class="topline"></div>
<p class="eyebrow">FIGURE 4</p>
<h1 class="title small">温度不是现在最应该继续押注的方向：主数据里方向不稳、量级也不够解释全部划伤</h1>
<div class="rule"></div>

<div class="placeholder" id="img-temp" style="left:42pt;top:146pt;width:538pt;height:314pt;"></div>

<div class="term" style="left:606pt;top:146pt;width:312pt;height:92pt;">
  <h3>Tg 是什么</h3>
  <p style="top:48pt;">PET 在约 75°C 附近开始从偏硬状态转向可拉伸状态，所以预热和拉伸段温度理论上重要，但不能只凭“理论上重要”就下根因结论。</p>
</div>

<div class="term" style="left:606pt;top:254pt;width:312pt;height:112pt;">
  <h3>为什么温度现在不能坐上主桌</h3>
  <p style="top:48pt;">55批主数据里，预热温度和划伤是负相关；149批全数据里又变成正相关。方向反转说明它受混杂或极端批次影响大，不够稳定。</p>
</div>

<div class="term" style="left:606pt;top:382pt;width:312pt;height:78pt;">
  <h3>结论</h3>
  <p style="top:44pt;">温度可以继续关注，但不应成为当前整改资源的第一优先级。</p>
</div>
`
  ),
  html(
    9,
    `
<div class="topline crisp"></div>
<p class="eyebrow">FIGURE 5</p>
<h1 class="title small">主时序图把质量尖峰和过程波动串起来了，但批次级数据还不足以判定谁先谁后</h1>
<div class="rule"></div>

<div class="placeholder" id="img-overlay" style="left:42pt;top:146pt;width:876pt;height:248pt;"></div>

<div class="card soft" style="left:42pt;top:412pt;width:280pt;height:84pt;">
  <h2>图怎么看</h2>
  <p style="top:44pt;">看红区附近，哪些过程变量的波动也同时抬头。</p>
</div>

<div class="card blue" style="left:340pt;top:412pt;width:280pt;height:84pt;">
  <h2>图说明什么</h2>
  <p style="top:44pt;">质量尖峰与过程波动存在批次级同步性，所以“过程稳定性问题”这个方向是可信的。</p>
</div>

<div class="card accent" style="left:638pt;top:412pt;width:280pt;height:84pt;">
  <h2>图的边界</h2>
  <p style="top:44pt;">当前不是秒级数据，而且 time_sorted 未确认，所以还不能直接说谁先发生、谁驱动谁。</p>
</div>
`
  ),
  html(
    10,
    `
<div class="topline"></div>
<p class="eyebrow">GLOSSARY AND LIMITS</p>
<h1 class="title small">听懂这四个词，就能明白为什么这次结论必须讲得既坚定又克制</h1>
<div class="rule"></div>

<div class="term" style="left:42pt;top:148pt;width:418pt;height:128pt;">
  <h3>Pearson相关</h3>
  <p style="top:48pt;">看两个量是不是沿着“直线关系”一起变大或变小。优点是直观，风险是很容易被极端大值拉歪。</p>
</div>

<div class="term" style="left:500pt;top:148pt;width:418pt;height:128pt;">
  <h3>Spearman相关</h3>
  <p style="top:48pt;">不看绝对大小，只看大小规律是不是一致。对于偏态分布和极端批次很多的场景，更稳。</p>
</div>

<div class="term" style="left:42pt;top:294pt;width:418pt;height:128pt;">
  <h3>离群点</h3>
  <p style="top:48pt;">极少数特别异常的大值。它会让“少数批次的极端现象”看起来像“所有批次都遵循的规律”。</p>
</div>

<div class="term" style="left:500pt;top:294pt;width:418pt;height:128pt;">
  <h3>COMPETING_SET</h3>
  <p style="top:48pt;">不是没方向，而是还有多个假设同时活着。对管理层而言，这意味着现在最有价值的是支持验证，而不是提前选边。</p>
</div>

<div class="card dark" style="left:42pt;top:440pt;width:876pt;height:56pt;">
  <h2>一句话总结</h2>
  <p style="top:22pt;">我们已经知道“往哪里查”，但还没有到可以替技术团队宣布“就它一个”的阶段。</p>
</div>
`
  ),
  html(
    11,
    `
<div class="topline"></div>
<p class="eyebrow">ACTION PLAN</p>
<h1 class="title small">下一步不是继续争论，而是用在线数据和对照实验把 H1、H2、H3 真正分开</h1>
<div class="rule"></div>

<div class="node" style="left:42pt;top:156pt;width:270pt;height:258pt;">
  <h3>阶段一：本周内先稳现场</h3>
  <p style="top:54pt;">1. 在 FP21、PG32D 等敏感型号补采秒级扭矩、速度、张力同步数据。</p>
  <p style="top:110pt;">2. 统一记录每个型号的完整设定值、厚度和配方。</p>
  <p style="top:162pt;">3. 固化 PG22C 等低缺陷窗口作为对照基准。</p>
</div>

<div class="node" style="left:345pt;top:156pt;width:270pt;height:258pt;">
  <h3>阶段二：两周内做验证</h3>
  <p style="top:54pt;">1. 做同型号对照实验，分辨扭矩链和速度 / 拉伸比链。</p>
  <p style="top:110pt;">2. 记录辊面维护、滤网更换、设备状态事件时间戳。</p>
  <p style="top:162pt;">3. 单独复盘149批全数据里的极端批次。</p>
</div>

<div class="node" style="left:648pt;top:156pt;width:270pt;height:258pt;">
  <h3>阶段三：一个月内固化机制</h3>
  <p style="top:54pt;">1. 建立“过程波动异常 -> 质量风险预警”规则。</p>
  <p style="top:110pt;">2. 视条件补更直接的在线张力或接触测量。</p>
  <p style="top:162pt;">3. 把型号切换管理纳入质量治理看板。</p>
</div>

<div class="card accent" style="left:42pt;top:432pt;width:876pt;height:64pt;">
  <h2>责任分工提醒</h2>
  <p style="top:38pt;">工艺负责实验设计，设备负责在线测量与事件日志，质量负责极端批次回溯，生产负责为同型号试验留出窗口。没有协同，这个问题只会反复在不同型号上出现。</p>
</div>
`
  ),
  html(
    12,
    `
<div class="topline"></div>
<p class="eyebrow">DECISION REQUEST</p>
<h1 class="title small">管理层现在要拍板的，是“验证资源”和“协同机制”，不是替技术团队提前选答案</h1>
<div class="rule"></div>

<div class="card dark" style="left:42pt;top:156pt;width:356pt;height:262pt;">
  <h2>汇报收口</h2>
  <p style="top:62pt;font-size:17pt;line-height:1.7;font-weight:700;">当前最稳的结论，是“型号基线差异必须先控制，过程稳定性问题必须继续验证”；</p>
  <p style="top:150pt;font-size:17pt;line-height:1.7;font-weight:700;color:#FFD9C8;">最不应该做的，是在证据还不够时，过早宣布某个单一参数就是最终根因。</p>
</div>

<div class="card soft" style="left:430pt;top:156pt;width:488pt;height:76pt;">
  <h2>需要拍板 1</h2>
  <p style="top:40pt;">批准同型号验证试车窗口，优先覆盖 FP21、PG32D 等敏感型号。</p>
</div>

<div class="card blue" style="left:430pt;top:248pt;width:488pt;height:76pt;">
  <h2>需要拍板 2</h2>
  <p style="top:40pt;">批准秒级在线数据采集和设备事件日志完善，不再只依赖批次级汇总。</p>
</div>

<div class="card accent" style="left:430pt;top:340pt;width:488pt;height:76pt;">
  <h2>需要拍板 3</h2>
  <p style="top:40pt;">要求工艺、设备、质量共用一个“型号设定与质量基线”基准表，防止型号切换被当成黑箱。</p>
</div>

<div class="card" style="left:430pt;top:432pt;width:488pt;height:64pt;">
  <p style="top:18pt;font-size:11pt;line-height:1.6;">如果这三件事能落下去，下一轮汇报就有机会从“方向已收敛”走到“单根因已锁定”。</p>
</div>
`
  )
];

ensureDir(ROOT);
ensureDir(SLIDES_DIR);
ensureDir(REFS_DIR);

write(path.join(ROOT, 'PLAN.md'), plan);
write(path.join(ROOT, 'compile.cjs'), compileCjs);
write(path.join(REFS_DIR, 'research_notes.md'), researchNotes);
write(path.join(REFS_DIR, '_user_materials.md'), userMaterials);
write(path.join(REFS_DIR, '_index.md'), indexMd);

slides.forEach((content, index) => {
  const file = `slide-${String(index + 1).padStart(2, '0')}.html`;
  write(path.join(SLIDES_DIR, file), content);
});

console.log(
  JSON.stringify(
    {
      root: ROOT,
      slides: slides.length,
      runDir: RUN_DIR
    },
    null,
    2
  )
);
