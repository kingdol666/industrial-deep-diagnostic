import fs from 'fs';
import path from 'path';

const ROOT = path.resolve(
  '/Volumes/laxer/codes/skills/industrial-deep-diagnostic/ppt_workspace/bopet_model_diff_ceo_report_20260609_run0427156'
);
const RUN_DIR = path.resolve(
  '/Volumes/laxer/codes/skills/industrial-deep-diagnostic/workspace/diagnostic-runs/202606090427156_BOPET薄膜双拉加工'
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
  background:#FBFAF7;color:#1F2430;
  font-family:'Microsoft YaHei','PingFang SC',Arial,sans-serif
}
.topline{position:absolute;left:0;top:0;width:960pt;height:5pt;background:#1C3144}
.topline.crisp{background:#B44A2E}
.bottomline{position:absolute;left:34pt;bottom:28pt;width:892pt;height:1.2pt;background:#D7D2CA}
.page{position:absolute;right:38pt;bottom:10pt;font-size:9pt;color:#6E6A64}
.eyebrow{position:absolute;left:42pt;top:26pt;font-size:9.5pt;letter-spacing:1.4pt;color:#8A5A3B}
.title{position:absolute;left:42pt;top:48pt;width:876pt;font-size:25pt;line-height:1.32;font-weight:700;color:#1C3144}
.title.small{font-size:23pt}
.subtitle{position:absolute;left:42pt;top:112pt;width:876pt;font-size:12pt;line-height:1.65;color:#6A6762}
.rule{position:absolute;left:42pt;top:102pt;width:110pt;height:3pt;background:#B44A2E;border-radius:2pt}
.card{position:absolute;border:1.1pt solid #D9D4CC;border-radius:14pt;background:#FFFFFF}
.card.soft{background:#F4F1EA}
.card.accent{background:#FFF5EE;border-color:#E7C8B9}
.card.blue{background:#F1F6FA;border-color:#C8D7E3}
.card.dark{background:#1C3144;border-color:#1C3144}
.card.warn{background:#FFF7F2;border-color:#E9B8A8}
.card h2{
  position:absolute;left:18pt;top:14pt;width:calc(100% - 36pt);
  font-size:15pt;line-height:1.35;font-weight:700;color:#1C3144
}
.card.dark h2,.card.dark p,.card.dark li{color:#FFFFFF}
.card p{
  position:absolute;left:18pt;width:calc(100% - 36pt);
  font-size:11.2pt;line-height:1.62;color:#20242B
}
.card ul{
  position:absolute;left:28pt;top:50pt;width:calc(100% - 52pt);
  font-size:11.2pt;line-height:1.62;color:#20242B;padding-left:16pt
}
.card.dark ul{color:#FFFFFF}
.node{position:absolute;border:1.2pt solid #1C3144;border-radius:12pt;background:#FFFFFF}
.node h3{
  position:absolute;left:12pt;top:12pt;width:calc(100% - 24pt);
  font-size:13pt;line-height:1.35;font-weight:700;color:#1C3144;text-align:center
}
.node p{
  position:absolute;left:12pt;width:calc(100% - 24pt);
  font-size:10.4pt;line-height:1.55;color:#27303B;text-align:center
}
.term{position:absolute;border:1.1pt solid #D9D4CC;border-radius:12pt;background:#FFFFFF}
.term h3{
  position:absolute;left:16pt;top:14pt;width:calc(100% - 32pt);
  font-size:14pt;line-height:1.35;font-weight:700;color:#1C3144
}
.term p{
  position:absolute;left:16pt;width:calc(100% - 32pt);
  font-size:11pt;line-height:1.62;color:#232831
}
.placeholder{
  position:absolute;border:1.2pt dashed #B7C3CE;border-radius:12pt;background:#F7F9FB
}
.kpi{position:absolute;border:1.1pt solid #D9D4CC;border-radius:14pt;background:#FFFFFF}
.kpi-num{
  position:absolute;left:14pt;top:16pt;width:calc(100% - 28pt);
  font-size:28pt;line-height:1.2;font-weight:700;text-align:center;color:#1C3144
}
.kpi-label{
  position:absolute;left:14pt;top:60pt;width:calc(100% - 28pt);
  font-size:10pt;line-height:1.55;text-align:center;color:#5E5A54
}
.arrow{position:absolute;font-size:20pt;line-height:1;color:#1C3144}
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
| PPT标题 | BOPET划伤诊断：MD工艺参数基本排除，调查重点转向产品型号固有差异 |
| 副标题 | 面向企业老板的汇报版本：讲清结论、推理过程、证据链、统计边界和下一步动作 |
| 总页数 | 12页（其中5页使用诊断原始figure，7页为线条简约解释页） |
| 制作引擎 | huashu-slides 风格约束 + html2pptx 组装 |
| 路径 | Path A（可编辑HTML） |
| 风格 | 线条简约商务风（Warm Academic 基底，局部 Crisp 强调） |
| **比例** | **16:9（960pt×540pt）** |
| 语言 | 中文 |
| 受众 | 企业老板 + 制造/工艺/质量管理层 |
| 研究笔记 | ppt_workspace/bopet_model_diff_ceo_report_20260609_run0427156/references/ |

## 二、风格参数速查

### 线条简约商务风
- 页面底色: #FBFAF7
- 主线条色: #1C3144
- 强调色: #B44A2E
- 正文色: #1F2430
- 辅助色: #6A6762
- 卡片底色: #FFFFFF / #F4F1EA / #F1F6FA / #FFF5EE
- 标题字体: Microsoft YaHei Bold, 23-25pt
- 正文字体: Microsoft YaHei Regular, 10.5-12pt
- 设计原则: 留白优先、细线条、少色块、每页一个主结论、每张图都配“图怎么看 / 图说明什么 / 图的边界”

## 三、逐页规划

### 第1页：封面
- **标题**: BOPET划伤诊断：MD工艺参数基本排除，调查重点转向产品型号固有差异
- **密度**: 中等
- **论证逻辑**: 封面先把老板最需要记住的判断说清楚
- **视觉主角**: 右侧深色结论卡
- **布局**: 左侧汇报问题卡 + 右侧一句话结论卡 + 底部 run 信息
- **图片决策**: text-only

### 第2页：老板先记住什么
- **标题**: 这次最重要的不是“继续调MD参数”，而是“不要把错误方向当改善方向”
- **密度**: 中等
- **论证逻辑**: 拆成能确认、不能确认、已纠偏、应行动四块
- **视觉主角**: 四象限结论卡
- **布局**: 2×2卡片网格
- **图片决策**: text-only

### 第3页：产线和术语先讲明白
- **标题**: 这次报告分析的是MD纵拉加工段，但最终结论指向“问题未必发生在这一段”
- **密度**: 中等
- **论证逻辑**: 让老板理解 BOPET 产线、Tg、MD/TD 的含义
- **视觉主角**: 右侧三段式产线卡片
- **布局**: 左术语卡 + 右流程卡 + 底部数据覆盖说明
- **图片决策**: text-only

### 第4页：证据链是怎么得出来的
- **标题**: 我们不是凭一张图下结论，而是按“先找强信号、再纠偏、再排除、最后收束”的顺序推进
- **密度**: 中等
- **论证逻辑**: 先解释分析方法，再看证据页
- **视觉主角**: 五步推理链
- **布局**: 横向节点 + 下方一句话说明
- **图片决策**: text-only

### 第5页：Figure 1
- **标题**: 型号差异是当前最强信号，但要注意“均值很大”不等于“所有正常批次都一样大”
- **密度**: 深度
- **论证逻辑**: 讲清型号差异、极端值驱动和管理层正确理解方式
- **视觉主角**: scratch by model 原始图
- **布局**: 左图右侧三层解释卡
- **图片决策**: 使用原始figure

### 第6页：Figure 2
- **标题**: 产品切换时划伤会跳变，而切换前后大部分MD工艺参数并没有同步跳变
- **密度**: 中等
- **论证逻辑**: 说明“分组变量”比工艺参数更强
- **视觉主角**: event response 原始图
- **布局**: 上图下方三张说明卡
- **图片决策**: 使用原始figure

### 第7页：Figure 3
- **标题**: 视在相关经稳健性检查后明显变弱，说明很多表面相关都只是离群批次放大的假象
- **密度**: 深度
- **论证逻辑**: 给老板解释为什么不能只看 Pearson
- **视觉主角**: correlation robustness 原始图
- **布局**: 左图右文，上下两层解释
- **图片决策**: 使用原始figure

### 第8页：Figure 4
- **标题**: 同色聚类比斜率更重要：产品型号在工艺参数空间和划伤空间里都形成独立簇
- **密度**: 中等
- **论证逻辑**: 讲清 BETWEEN_PRODUCT_ONLY 和 Simpson 悖论风险
- **视觉主角**: filter + quench scatter 原始图
- **布局**: 左图右侧术语卡 + 解释卡
- **图片决策**: 使用原始figure

### 第9页：Figure 5
- **标题**: 高划伤和低划伤批次的温度剖面几乎重叠，所以“继续调MD温度”不是当前最优先动作
- **密度**: 中等
- **论证逻辑**: 用空间剖面图完成对 H2/H3 的直观排除
- **视觉主角**: zone spatial profile 原始图
- **布局**: 左图右文，右侧分三层解释
- **图片决策**: 使用原始figure

### 第10页：术语和统计边界翻译
- **标题**: 听懂这四个词，就能明白为什么这次结论要讲得“坚定，但克制”
- **密度**: 中等
- **论证逻辑**: 解释 Pearson / Spearman / Kruskal-Wallis / COMPETING_SET
- **视觉主角**: 2×2术语卡
- **布局**: 术语卡 + 底部一句话总结
- **图片决策**: text-only

### 第11页：下一步企业该做什么
- **标题**: 下一步不是继续围着MD参数调，而是补齐能区分材料、厚度和下游工艺的数据
- **密度**: 中等
- **论证逻辑**: 按 P0 / P1 / P2 分阶段行动
- **视觉主角**: 三阶段行动路线图
- **布局**: 三列行动卡 + 底部责任分工提醒
- **图片决策**: text-only

### 第12页：汇报收口
- **标题**: 管理层现在要拍板的，是“验证资源”和“跨段数据打通”，不是替技术团队提前指定根因
- **密度**: 中等
- **论证逻辑**: 明确老板要决定的三件事
- **视觉主角**: 右侧三张决策请求卡
- **布局**: 左侧收束句 + 右侧决策卡
- **图片决策**: text-only

## 四、配图生成清单

| 序号 | 文件名 | 对应页码 | 来源 |
|------|--------|---------|------|
| 1 | fig_scratch_by_model.png | 5 | 诊断run原始figure |
| 2 | fig_vlm_event_response.png | 6 | 诊断run原始figure |
| 3 | fig_correlation_robustness.png | 7 | 诊断run原始figure |
| 4 | fig_filter_quench_scatter.png | 8 | 诊断run原始figure |
| 5 | fig_zone_spatial_profile.png | 9 | 诊断run原始figure |

## 五、技术规范

- slide尺寸: 960pt×540pt
- 顶部签名线: 5pt 深蓝
- 页码: 右下角 9pt
- 图片插入: placeholder div + compile.cjs addImage
- 编码: UTF-8
- 说明要求: 每张图必须附“图怎么看 / 图说明什么 / 图的边界”
`;

const researchNotes = `# BOPET薄膜双拉加工老板汇报研究底稿

## 1. 本次汇报的最重要口径

- 当前最稳的结论是：
  **MD纵拉段工艺参数（温度、扭矩、速度）基本被排除，不是当前划伤缺陷的主导根因。**
- 当前最强信号转向：
  **产品型号固有差异**，但它的内部子机制还没有被直接测到。
- 因此，最合适的老板表述不是“我们已经找到唯一根因”，而是：
  **方向已经收敛，但根因仍处于竞争假设集合，需要企业补数据把它分开。**

## 2. 核心数字

- 149批次
- 184列数据
- 18根纵拉辊
- Judge 96/100 PASS
- 诊断类型：COMPETING_SET
- H1最终置信度：64/100

## 3. 老板需要记住的四句话

1. **不要再把主要资源投在继续调MD温度或扭矩均值上。**
2. **温度相关看起来存在，但稳健性检查后明显变弱，本质上是产品型号混杂和离群批次驱动。**
3. **产品型号差异是当前最强分组信号，但它更多解释的是“极端划伤概率差异”，不一定意味着正常批次基线差异同样巨大。**
4. **下一步最该补的是原材料配方、厚度规格、TD横拉/收卷段数据，而不是继续只盯MD段。**

## 4. 证据链主线

### 4.1 先看最强分组因子

- 产品型号之间的 scratch_count 均值差异很大。
- 代表性对比：
  - FP21 mean = 375.5
  - PG32B mean = 4.2
  - PG22C mean = 0.8
- 但注意：
  - 审计明确提醒，均值差异里含有极端批次驱动成分
  - FP21 与 PG32B 的中位数差异没有均值差异那么夸张
- 对老板的翻译：
  **型号差异不是“每一批都差很多”，更准确地说，是某些型号更容易出现极端高划伤事件。**

### 4.2 再看产品切换事件

- PG32B -> PG32D 切换时，scratch 从 4.2 跳到 171.9。
- 同期大部分 MD 工艺参数没有同步出现同量级跳变。
- 对老板的翻译：
  **比起“这一时刻机器参数变了”，更像是“换了型号以后，质量风险基线换了”。**

### 4.3 再做稳健性纠偏

- 温度相关的 Pearson r 大多在 0.23-0.28。
- 但 Spearman rho 只有 0.02-0.13。
- Pearson 和 Spearman 的差值达到 0.15-0.28。
- 对老板的翻译：
  **看起来有关系，不代表它在大多数批次里都成立；有时只是被少数极端点硬拉出来。**

### 4.4 再看分层散点

- 不同型号在散点图里形成独立簇。
- 这说明全局相关很可能只是“型号不同，设定值也不同，划伤也不同”造成的表面关系。
- 报告把这种模式定义为 BETWEEN_PRODUCT_ONLY。

### 4.5 再看空间剖面

- 高划伤与低划伤批次在温度剖面上几乎重叠。
- 预热 / 拉伸段的差异通常小于 0.15C。
- 这种量级不够解释从 4 到 6925 的划伤跨度。
- 对老板的翻译：
  **如果真是温度主导，我们应该看到一条明显分开的两条线；现在并没有。**

## 5. 存活假设 H1 该怎么讲

H1 不是一个已经被完全证明的单一根因，而是一个“上位假设”：

- H1-A：原材料配方差异
- H1-B：厚度规格差异
- H1-C：下游 TD 横拉 / 收卷工艺差异

目前这三个子机制的共同点是：
- 都能解释为什么“型号差异比MD参数差异更强”
- 但当前数据里没有直接观测量能把它们彼此分开

## 6. 关键术语的老板翻译

- **Tg**：
  材料从“偏硬”转向“可以被拉伸”的温度门槛。PET 大约在 75C 左右。
- **Pearson相关**：
  看两个量是不是沿着“直线关系”一起变。
- **Spearman相关**：
  不看绝对大小，只看大小规律是不是一致，更适合有极端值的数据。
- **Kruskal-Wallis**：
  用来比较多组分布是不是不一样，比“拿分类变量去做相关”更合适。
- **COMPETING_SET**：
  不是没方向，而是还有几个合理解释同时活着，企业要做的是支持验证，而不是提前选答案。

## 7. 企业下一步动作

### P0 立即做

- 获取各批次 PET 切片的原材料配方数据，尤其是 SiO2 含量和关键添加剂信息。
- 收集各产品型号对应的厚度规格。
- 明确 model 列清洗规则，解决尾随空格导致的分组失真。

### P1 两周内做

- 部署 TD 横拉段和收卷段的工艺参数采集。
- 做 FP21 与 PG32B “同型号不同材料批次”的回顾分析。
- 针对极端批次做单独复盘，而不是把它们只混在总体均值里。

### P2 一个月内做

- 打通从原材料 -> MD -> TD -> 收卷 -> 缺陷检测的全链路数据。
- 建立“型号切换 -> 质量风险基线变化”的预警规则。
- 如仍需验证温度影响，再做定向小范围实验，而不是把它当成主战场。

## 8. 汇报时要反复提醒老板的风险边界

- 不要把“型号均值差异大”误讲成“所有正常批次的基线差异都同样大”
- 不要把“温度有弱相关”误讲成“温度就是根因”
- 不要把“MD段被排除”误讲成“问题已经完全找到”
- 正确表达应该是：
  **本轮分析最大的价值，是排除了错误方向，并把调查重点从MD工艺参数转向产品固有差异及下游未观测环节。**
`;

const userMaterials = `# 用户要求整理

- 使用 workspace/diagnostic-runs/202606090427156_BOPET薄膜双拉加工/report.md
- 要把结论、怎么得出结论、证据链、下一步企业动作讲清楚
- 给企业老板汇报，要求逻辑完整，不跳脱
- 所有关键 figure 都要解释，能把证据串起来
- 使用线条风格的简约风 PPT，并且布局要好看
- 专业名词要翻译成老板听得懂的话
- 结论必须有真正证据作为支撑
`;

const indexMd = `# 参考索引

| 文件 | 用途 |
|------|------|
| research_notes.md | 老板汇报的核心逻辑、证据链、风险边界和行动建议 |
| _user_materials.md | 用户目标和使用的诊断run说明 |
`;

const compileCjs = `const fs = require('fs');
const path = require('path');
const pptxgen = require('/Users/haozhengzhang/.cc-switch/skills/ppt-auto-builder/node_modules/pptxgenjs');
const html2pptx = require('/Users/haozhengzhang/.cc-switch/skills/huashu-slides/scripts/html2pptx.js');

const ROOT = __dirname;
const SLIDES_DIR = path.join(ROOT, 'slides');
const FIG_DIR = path.resolve(ROOT, '../../workspace/diagnostic-runs/202606090427156_BOPET薄膜双拉加工/03_figures');

const IMAGE_MAP = {
  'img-model': path.join(FIG_DIR, 'fig_scratch_by_model.png'),
  'img-switch': path.join(FIG_DIR, 'fig_vlm_event_response.png'),
  'img-robust': path.join(FIG_DIR, 'fig_correlation_robustness.png'),
  'img-cluster': path.join(FIG_DIR, 'fig_filter_quench_scatter.png'),
  'img-zone': path.join(FIG_DIR, 'fig_zone_spatial_profile.png')
};

(async () => {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_WIDE';
  pptx.author = 'Codex';
  pptx.company = 'OpenAI';
  pptx.subject = 'BOPET model-difference diagnosis CEO report';
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

  const outPath = path.join(ROOT, 'BOPET_双拉加工划伤诊断老板汇报_20260609.pptx');
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
<p class="eyebrow">BOPET MODEL DIFFERENCE DIAGNOSIS</p>
<h1 class="title">BOPET划伤诊断：MD工艺参数基本排除，调查重点转向产品型号固有差异</h1>
<div class="rule"></div>
<p class="subtitle">这是一份给企业老板的汇报版本。重点不是展示“分析做了多少”，而是帮助管理层判断：哪些方向已经可以停掉、哪些方向必须继续追、下一步资源该投到哪里。</p>

<div class="card soft" style="left:42pt;top:168pt;width:468pt;height:250pt;">
  <h2>这次汇报只回答四个问题</h2>
  <ul>
    <li>当前最稳的结论到底是什么？</li>
    <li>为什么说 MD 工艺参数不是当前主战场？</li>
    <li>哪些证据支持“产品型号差异更强”？</li>
    <li>企业下一步具体要补什么数据、做什么动作？</li>
  </ul>
</div>

<div class="card dark" style="left:540pt;top:168pt;width:378pt;height:250pt;">
  <h2>一句话结论</h2>
  <p style="top:66pt;font-size:19pt;line-height:1.55;font-weight:700;">先停掉错误方向。</p>
  <p style="top:108pt;font-size:21pt;line-height:1.48;font-weight:700;color:#FFD9C8;">当前最有证据支持的判断，不是“继续调 MD 参数”，而是“调查产品型号固有差异及其未观测子机制”。</p>
  <p style="top:196pt;font-size:11pt;line-height:1.58;color:#D8E4EC;">这轮分析最大的价值，是排除了误诊风险，把调查范围缩小到了材料、规格和下游工艺三个方向。</p>
</div>

<div class="card blue" style="left:42pt;top:438pt;width:876pt;height:56pt;">
  <p style="top:16pt;font-size:10.5pt;line-height:1.5;">Run ID: 202606090427156_BOPET薄膜双拉加工 ｜ 149批次 ｜ Judge 96/100 PASS ｜ 诊断类型：COMPETING_SET ｜ 存活假说 H1 = 64/100</p>
</div>
`
  ),
  html(
    2,
    `
<div class="topline crisp"></div>
<p class="eyebrow">EXECUTIVE TAKEAWAYS</p>
<h1 class="title small">这次最重要的不是“继续调MD参数”，而是“不要把错误方向当改善方向”</h1>
<div class="rule"></div>

<div class="card" style="left:42pt;top:142pt;width:418pt;height:150pt;">
  <h2>现在能确认</h2>
  <p style="top:56pt;">MD纵拉段温度、扭矩、速度与划伤之间没有稳定的因果证据。温度相关在稳健性检查和分层分析后明显变弱，不能作为主根因方向。</p>
</div>

<div class="card accent" style="left:500pt;top:142pt;width:418pt;height:150pt;">
  <h2>现在不能确认</h2>
  <p style="top:56pt;">还不能直接宣布“就是原材料”或“就是厚度”或“就是TD段”。当前只能确认它们比 MD 参数更值得调查，但三者仍处于竞争假设集合。</p>
</div>

<div class="card blue" style="left:42pt;top:312pt;width:418pt;height:150pt;">
  <h2>已经被纠偏</h2>
  <p style="top:56pt;">原本看起来存在的温度相关，在 Spearman、去趋势和按型号分层后被证明不稳。原始“分类变量直接做相关”的做法也被修正为更合适的 Kruskal-Wallis 检验。</p>
</div>

<div class="card soft" style="left:500pt;top:312pt;width:418pt;height:150pt;">
  <h2>企业要立刻做什么</h2>
  <p style="top:56pt;">补原材料配方、厚度规格、TD横拉与收卷段数据；同时清洗型号字段、回放极端批次。下一轮要做的不是再调MD参数，而是让 H1-A / H1-B / H1-C 真正可区分。</p>
</div>
`
  ),
  html(
    3,
    `
<div class="topline"></div>
<p class="eyebrow">PROCESS AND TERMS</p>
<h1 class="title small">这次报告分析的是 MD 纵拉加工段，但最终结论指向“问题未必发生在这一段”</h1>
<div class="rule"></div>

<div class="card soft" style="left:42pt;top:140pt;width:252pt;height:322pt;">
  <h2>先把几个术语翻成老板能听懂的话</h2>
  <p style="top:56pt;"><b>MD</b>：薄膜在纵向被拉开的工段，是本次已有数据最完整的段。</p>
  <p style="top:120pt;"><b>TD</b>：后续横向拉伸工段。虽然这次没采到数据，但划伤也可能在那一段发生。</p>
  <p style="top:198pt;"><b>Tg</b>：材料从“偏硬”转向“可以被拉伸”的温度门槛，PET 大约在 75C 左右。</p>
  <p style="top:274pt;"><b>双拉</b>：先纵向拉，再横向拉，所以“MD出口检测到划伤”不等于“划伤一定发生在MD”。</p>
</div>

<div class="card" style="left:312pt;top:140pt;width:606pt;height:154pt;">
  <h2>可以把产线理解成四段</h2>
  <div class="card blue" style="left:18pt;top:56pt;width:128pt;height:76pt;">
    <h2 style="font-size:13pt;">挤出 / 过滤</h2>
    <p style="top:36pt;font-size:10.3pt;">原料熔融、过滤杂质。</p>
  </div>
  <div class="card soft" style="left:164pt;top:56pt;width:128pt;height:76pt;">
    <h2 style="font-size:13pt;">MD预热 / 纵拉</h2>
    <p style="top:36pt;font-size:10.3pt;">这次已有最完整参数。</p>
  </div>
  <div class="card accent" style="left:310pt;top:56pt;width:128pt;height:76pt;">
    <h2 style="font-size:13pt;">TD横拉</h2>
    <p style="top:36pt;font-size:10.3pt;">当前数据缺失，但可能产伤。</p>
  </div>
  <div class="card warn" style="left:456pt;top:56pt;width:132pt;height:76pt;">
    <h2 style="font-size:13pt;">收卷 / 后处理</h2>
    <p style="top:36pt;font-size:10.3pt;">也可能放大划伤表现。</p>
  </div>
</div>

<div class="card accent" style="left:312pt;top:312pt;width:606pt;height:62pt;">
  <p style="top:18pt;font-size:10.8pt;line-height:1.5;">老板翻译：这次能确认的是“MD参数不是主要矛盾”，但不能因此误解成“问题一定发生在MD”。相反，真正该追的很可能在材料、规格或下游环节。</p>
</div>

<div class="card blue" style="left:312pt;top:392pt;width:606pt;height:70pt;">
  <h2>这次数据覆盖了什么</h2>
  <p style="top:40pt;">149批次、184列数据、18根纵拉辊参数、产品型号信息和划伤计数。数据对 MD 段很丰富，但对原材料、厚度和 TD 段仍然缺口明显。</p>
</div>
`
  ),
  html(
    4,
    `
<div class="topline"></div>
<p class="eyebrow">REASONING CHAIN</p>
<h1 class="title small">我们不是凭一张图下结论，而是按“先找强信号、再纠偏、再排除、最后收束”的顺序推进</h1>
<div class="rule"></div>

<div class="node" style="left:42pt;top:180pt;width:152pt;height:108pt;">
  <h3>第一步</h3>
  <p style="top:42pt;">先看分布和分组差异</p>
  <p style="top:70pt;">找最强信号是谁</p>
</div>
<p class="arrow" style="left:202pt;top:218pt;">→</p>
<div class="node" style="left:230pt;top:180pt;width:152pt;height:108pt;">
  <h3>第二步</h3>
  <p style="top:42pt;">看相关图</p>
  <p style="top:70pt;">圈出可疑参数</p>
</div>
<p class="arrow" style="left:390pt;top:218pt;">→</p>
<div class="node" style="left:418pt;top:180pt;width:152pt;height:108pt;">
  <h3>第三步</h3>
  <p style="top:42pt;">做去趋势 / Spearman</p>
  <p style="top:70pt;">识别伪相关</p>
</div>
<p class="arrow" style="left:578pt;top:218pt;">→</p>
<div class="node" style="left:606pt;top:180pt;width:152pt;height:108pt;">
  <h3>第四步</h3>
  <p style="top:42pt;">按型号分层</p>
  <p style="top:70pt;">检查混杂</p>
</div>
<p class="arrow" style="left:766pt;top:218pt;">→</p>
<div class="node" style="left:794pt;top:180pt;width:124pt;height:108pt;">
  <h3>第五步</h3>
  <p style="top:42pt;">排除 H2-H5</p>
  <p style="top:70pt;">保留 H1</p>
</div>

<div class="card dark" style="left:42pt;top:334pt;width:876pt;height:86pt;">
  <h2>这条链路的意义</h2>
  <p style="top:42pt;">它保证我们的结论不是“谁看图更像谁就算谁”，而是每一步都在缩小误诊空间：先找最强分组，再用稳健性和分层把表面相关洗掉，最后才决定企业该把资源投到哪里。</p>
</div>

<div class="card accent" style="left:42pt;top:438pt;width:876pt;height:58pt;">
  <p style="top:18pt;font-size:10.8pt;line-height:1.5;">老板翻译：这次不是“没找到答案”，而是“已经知道哪些答案不成立，剩下哪几个值得继续验证”。</p>
</div>
`
  ),
  html(
    5,
    `
<div class="topline"></div>
<p class="eyebrow">FIGURE 1</p>
<h1 class="title.small title">型号差异是当前最强信号，但要注意“均值很大”不等于“所有正常批次都一样大”</h1>
<div class="rule"></div>

<div class="placeholder" id="img-model" style="left:42pt;top:146pt;width:560pt;height:314pt;"></div>

<div class="card soft" style="left:628pt;top:146pt;width:290pt;height:92pt;">
  <h2>图怎么看</h2>
  <p style="top:48pt;">柱高代表各型号平均划伤水平，柱顶 n 表示样本数。它先告诉我们“最强差异来自分组，而不是单个参数”。</p>
</div>

<div class="card blue" style="left:628pt;top:254pt;width:290pt;height:108pt;">
  <h2>图说明什么</h2>
  <p style="top:48pt;">FP21、FG22、FP41、PG32D 的平均划伤明显高于 PG32B、PG22C。当前最强信号不是温度或扭矩，而是“产品型号不同，划伤风险层级不同”。</p>
</div>

<div class="card accent" style="left:628pt;top:378pt;width:290pt;height:82pt;">
  <h2>图的边界</h2>
  <p style="top:44pt;">均值里含极端批次驱动成分。正确理解应是“某些型号更容易出现极端高划伤事件”，而不是“所有正常批次都差那么大”。</p>
</div>
`
  ),
  html(
    6,
    `
<div class="topline"></div>
<p class="eyebrow">FIGURE 2</p>
<h1 class="title small">产品切换时划伤会跳变，而切换前后大部分MD工艺参数并没有同步跳变</h1>
<div class="rule"></div>

<div class="placeholder" id="img-switch" style="left:42pt;top:146pt;width:876pt;height:236pt;"></div>

<div class="card soft" style="left:42pt;top:402pt;width:276pt;height:94pt;">
  <h2>图怎么看</h2>
  <p style="top:48pt;">红色竖线代表型号切换事件，看切换前后质量水平有没有明显变台阶。</p>
</div>

<div class="card blue" style="left:340pt;top:402pt;width:276pt;height:94pt;">
  <h2>图说明什么</h2>
  <p style="top:48pt;">像 PG32B -> PG32D 这样的切换，划伤会明显跳升，而同期 MD 参数没有出现同量级跳变。</p>
</div>

<div class="card accent" style="left:638pt;top:402pt;width:280pt;height:94pt;">
  <h2>图的边界</h2>
  <p style="top:48pt;">切换不是“唯一原因”，但它说明分组因素比单个MD工艺变量更强。</p>
</div>
`
  ),
  html(
    7,
    `
<div class="topline crisp"></div>
<p class="eyebrow">FIGURE 3</p>
<h1 class="title small">视在相关经稳健性检查后明显变弱，说明很多表面相关都只是离群批次放大的假象</h1>
<div class="rule"></div>

<div class="placeholder" id="img-robust" style="left:42pt;top:146pt;width:520pt;height:314pt;"></div>

<div class="card soft" style="left:588pt;top:146pt;width:330pt;height:94pt;">
  <h2>图怎么看</h2>
  <p style="top:48pt;">蓝柱是原始 Pearson，橙柱是去趋势后，绿柱是 Spearman。看三者差距有多大。</p>
</div>

<div class="card accent" style="left:588pt;top:256pt;width:330pt;height:112pt;">
  <h2>关键纠偏</h2>
  <p style="top:48pt;">如果 Pearson 明显高于 Spearman，说明这条“相关”更像是被少数极端批次拉出来的，而不是多数批次都遵守的规律。</p>
</div>

<div class="card blue" style="left:588pt;top:384pt;width:330pt;height:76pt;">
  <h2>结论</h2>
  <p style="top:42pt;">温度相关不稳，不能把它当根因证据。继续围绕 MD 温度调参，性价比很低。</p>
</div>
`
  ),
  html(
    8,
    `
<div class="topline"></div>
<p class="eyebrow">FIGURE 4</p>
<h1 class="title small">同色聚类比斜率更重要：产品型号在工艺参数空间和划伤空间里都形成独立簇</h1>
<div class="rule"></div>

<div class="placeholder" id="img-cluster" style="left:42pt;top:146pt;width:540pt;height:314pt;"></div>

<div class="term" style="left:606pt;top:146pt;width:312pt;height:98pt;">
  <h3>BETWEEN_PRODUCT_ONLY 是什么意思</h3>
  <p style="top:48pt;">全局看起来有相关，但拆到每个型号内部后，关系就近零、反转或互相矛盾。这种相关不能拿来做因果判断。</p>
</div>

<div class="term" style="left:606pt;top:260pt;width:312pt;height:102pt;">
  <h3>这页最关键的观察</h3>
  <p style="top:48pt;">同色点自己抱团，说明“型号是谁”同时影响工艺设定值和划伤水平。全局斜率只是这些簇错位以后产生的表面效果。</p>
</div>

<div class="term" style="left:606pt;top:378pt;width:312pt;height:82pt;">
  <h3>老板翻译</h3>
  <p style="top:44pt;">不是“温度越高划伤越大”，而是“某些型号本来就既更高温、又更容易划伤”。</p>
</div>
`
  ),
  html(
    9,
    `
<div class="topline"></div>
<p class="eyebrow">FIGURE 5</p>
<h1 class="title small">高划伤和低划伤批次的温度剖面几乎重叠，所以“继续调MD温度”不是当前最优先动作</h1>
<div class="rule"></div>

<div class="placeholder" id="img-zone" style="left:42pt;top:146pt;width:540pt;height:314pt;"></div>

<div class="card soft" style="left:606pt;top:146pt;width:312pt;height:94pt;">
  <h2>图怎么看</h2>
  <p style="top:48pt;">蓝线和红线分别代表低划伤与高划伤批次的温度剖面。看它们是不是大幅分开。</p>
</div>

<div class="card blue" style="left:606pt;top:256pt;width:312pt;height:112pt;">
  <h2>图说明什么</h2>
  <p style="top:48pt;">预热 / 拉伸段基本重叠，差异通常小于 0.15C。这个量级太小，解释不了从 4 到 6925 的划伤跨度。</p>
</div>

<div class="card accent" style="left:606pt;top:384pt;width:312pt;height:76pt;">
  <h2>图的边界</h2>
  <p style="top:42pt;">急冷段个别型号有系统性偏低，但方向与高划伤并不匹配，所以不能当作主因。</p>
</div>
`
  ),
  html(
    10,
    `
<div class="topline"></div>
<p class="eyebrow">GLOSSARY AND LIMITS</p>
<h1 class="title small">听懂这四个词，就能明白为什么这次结论要讲得“坚定，但克制”</h1>
<div class="rule"></div>

<div class="term" style="left:42pt;top:148pt;width:418pt;height:128pt;">
  <h3>Pearson相关</h3>
  <p style="top:48pt;">看两个量是不是沿着“直线关系”一起变。优点是直观，缺点是很容易被极端大值拉歪。</p>
</div>

<div class="term" style="left:500pt;top:148pt;width:418pt;height:128pt;">
  <h3>Spearman相关</h3>
  <p style="top:48pt;">不看绝对大小，只看大小规律是不是一致。对极端值多、分布偏的数据更稳。</p>
</div>

<div class="term" style="left:42pt;top:294pt;width:418pt;height:128pt;">
  <h3>Kruskal-Wallis</h3>
  <p style="top:48pt;">适合比较多组分布差异。比“把产品型号这样的分类变量直接拿去做相关”更合适。</p>
</div>

<div class="term" style="left:500pt;top:294pt;width:418pt;height:128pt;">
  <h3>COMPETING_SET</h3>
  <p style="top:48pt;">不是没方向，而是还有多个合理解释同时活着。管理层现在最有价值的动作是支持验证，而不是提前指定答案。</p>
</div>

<div class="card dark" style="left:42pt;top:440pt;width:876pt;height:56pt;">
  <h2>一句话总结</h2>
  <p style="top:22pt;">这次最确定的不是“根因是谁”，而是“哪些方向已经不值得继续重投资源”。</p>
</div>
`
  ),
  html(
    11,
    `
<div class="topline"></div>
<p class="eyebrow">ACTION PLAN</p>
<h1 class="title small">下一步不是继续围着MD参数调，而是补齐能区分材料、厚度和下游工艺的数据</h1>
<div class="rule"></div>

<div class="node" style="left:42pt;top:156pt;width:270pt;height:258pt;">
  <h3>阶段一：本周内先补关键数据</h3>
  <p style="top:54pt;">1. 获取各批次 PET 切片配方，尤其是 SiO2 和关键添加剂信息。</p>
  <p style="top:114pt;">2. 收集各型号厚度规格，并与缺陷数据做一一对应。</p>
  <p style="top:172pt;">3. 清洗 model 字段，消除尾随空格导致的分组失真。</p>
</div>

<div class="node" style="left:345pt;top:156pt;width:270pt;height:258pt;">
  <h3>阶段二：两周内补下游视角</h3>
  <p style="top:54pt;">1. 部署 TD 横拉段和收卷段参数采集。</p>
  <p style="top:114pt;">2. 做 FP21 与 PG32B 的同型号不同材料批次回顾分析。</p>
  <p style="top:172pt;">3. 把极端批次单独拎出来复盘，不只混在总体均值里。</p>
</div>

<div class="node" style="left:648pt;top:156pt;width:270pt;height:258pt;">
  <h3>阶段三：一个月内形成闭环</h3>
  <p style="top:54pt;">1. 打通原材料 -> MD -> TD -> 收卷 -> 缺陷检测的全链路数据。</p>
  <p style="top:114pt;">2. 建立“型号切换 -> 风险基线变化”预警规则。</p>
  <p style="top:172pt;">3. 若仍需验证温度影响，再做小范围定向实验，而不是全面调参。</p>
</div>

<div class="card accent" style="left:42pt;top:432pt;width:876pt;height:64pt;">
  <h2>责任分工提醒</h2>
  <p style="top:38pt;">工艺负责验证设计，质量负责极端批次回放，设备 / 信息化负责跨段数据打通，生产负责为对照分析留出稳定窗口。没有协同，这个问题会在不同型号上反复出现。</p>
</div>
`
  ),
  html(
    12,
    `
<div class="topline"></div>
<p class="eyebrow">DECISION REQUEST</p>
<h1 class="title small">管理层现在要拍板的，是“验证资源”和“跨段数据打通”，不是替技术团队提前指定根因</h1>
<div class="rule"></div>

<div class="card dark" style="left:42pt;top:156pt;width:356pt;height:262pt;">
  <h2>汇报收口</h2>
  <p style="top:62pt;font-size:17pt;line-height:1.68;font-weight:700;">当前最稳的结论，是“MD纵拉段工艺参数不是主导根因，真正该追的是产品型号固有差异及其未观测子机制”。</p>
  <p style="top:164pt;font-size:17pt;line-height:1.68;font-weight:700;color:#FFD9C8;">最不应该做的，是在证据还不够时，继续把主要资源砸在MD温度或扭矩均值上。</p>
</div>

<div class="card soft" style="left:430pt;top:156pt;width:488pt;height:76pt;">
  <h2>需要拍板 1</h2>
  <p style="top:40pt;">批准补采原材料配方、厚度规格和 TD / 收卷段数据，不再只看 MD 段。</p>
</div>

<div class="card blue" style="left:430pt;top:248pt;width:488pt;height:76pt;">
  <h2>需要拍板 2</h2>
  <p style="top:40pt;">要求极端批次单独复盘，并建立型号切换后的风险监测机制。</p>
</div>

<div class="card accent" style="left:430pt;top:340pt;width:488pt;height:76pt;">
  <h2>需要拍板 3</h2>
  <p style="top:40pt;">把后续验证目标写清楚：要区分的是材料差异、厚度差异，还是下游工艺差异。</p>
</div>

<div class="card" style="left:430pt;top:432pt;width:488pt;height:64pt;">
  <p style="top:18pt;font-size:11pt;line-height:1.6;">如果这三件事落下去，下一轮汇报就有机会从“方向已收敛”升级成“子机制已分开”。</p>
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
