# PPT制作规划文件

## 一、基本信息

| 字段 | 值 |
|------|-----|
| PPT标题 | 多智能体+RAG驱动的工业深度诊断系统——从传感器数据到根因结论的8阶段自动化管线 |
| 副标题 | Industrial Deep Diagnostic: 一个端到端的工业根因分析系统架构 |
| 总页数 | 12页（其中5页配图，7页text-only） |
| 制作引擎 | huashu-slides + gpt-image-2 |
| 路径 | Path A（可编辑HTML） |
| 风格 | xkcd白板手绘 #05 (Whiteboard Sketch) |
| **比例** | **16:9（960pt×540pt）** |
| 语言 | 中文 |
| 受众 | 混合（工程师+技术管理者+跨部门） |
| 研究笔记 | ppt_workspace/references/ |

## 二、风格参数速查

### xkcd白板手绘 (Whiteboard Sketch #05)

- **页面底色**: #FFFFFF（纯白 — 白板基底）
- **主色**: #000000（墨黑 — 所有绘制线条和文字）
- **强调色**: #4488FF（天蓝 — 关键概念标注）+ #FF4444（红 — 重点标记、错误标注）
- **辅助色**: #333333（深灰 — 次要文字）
- **卡片底色**: #F5F5F5（极浅灰 — 内容区块，像便利贴）
- **重点卡片**: #FFF8E1（浅黄 — 像荧光笔标记的便利贴）
- **签名元素**: 手绘风格边框(wobbly borders) + 手绘箭头 + 便利贴式卡片 + 涂鸦装饰
- **标题字体**: 手写风格 (Comic Sans MS / Segoe Print), 24-30pt, #000000
- **正文字体**: 手写风格 Regular, 12-14pt, #333333
- **数字强调**: 60-80pt 手写数字作为视觉锚点
- **英文字体**: 手写风格 (Comic Sans MS / Segoe Print)

### 生图风格关键词

```
hand-drawn whiteboard sketch style, black ink lines on pure white background,
stick figures with expressive poses, hand-drawn arrows connecting concepts,
wobbly uneven lines, annotation circles and underlines,
single accent color blue #4488FF for highlights,
no gradients no shadows no photographic elements,
like a professor just drew this on a whiteboard, 16:9, no text
```

### 布局核心特征

- 自由白板布局，非刚性网格
- 手绘箭头连接概念
- 便利贴式卡片承载信息
- 火柴人表达角色和交互
- 注释式标注（圆圈、下划线、星号）
- 像有人刚刚在白板上画出来的——活、乱、但突然就懂了

## 三、逐页规划

### 第1页：封面
- **标题**: 多智能体+RAG驱动的工业深度诊断系统
- **密度**: 极简（15-25字）
- **论证逻辑**: 建立第一印象——这是一个将传感器数据自动转化为根因结论的AI系统
- **视觉主角**: 白板概念图——一个工程师站在白板前，白板上画着从数据到诊断到报告的流程
- **布局**: 图上文下——上方占位图（680pt×290pt居中），中下方手写标题26pt居中，蓝色下划线80pt居中，底部汇报人信息10pt #333333
- **内容要点**:
  - 要点1：副标题——从传感器数据到根因结论的8阶段自动化管线
  - 要点2：Industrial Deep Diagnostic | 2024
- **图片决策**: Q1通过（封面需要视觉锚点）→ 1张 hero-cover
- **配图类型**: hero-cover
- **内容锚点**: 一个火柴人工程师站在白板前，白板上画着传感器→AI智能体→诊断报告的简化流程图，连接箭头和气泡注释
- **配图Prompt**: A stick figure engineer standing before a large whiteboard, the whiteboard shows a simplified flow diagram with boxes connected by hand-drawn arrows going from sensor icon through multiple agent nodes to a report document, some boxes circled in blue highlighter, small doodles and coffee cup in margin, black ink on white board, single blue accent #4488FF, hand-drawn whiteboard sketch style, professor lecture feel, 16:9 wide format with bottom 25% empty for title overlay, no text
- **风格注入**: 已融入风格关键词

### 第2页：目录
- **标题**: 这次分享你会看到什么？
- **密度**: 极简（每个章节5-8字）
- **论证逻辑**: 快速导航——告诉观众接下来的旅程
- **视觉主角**: 手写编号 + 便利贴式卡片
- **布局**: 左侧3个大便利贴（第1到第3 主章节），右侧2个小便利贴（第4到第5 收束章节），用蓝色手绘箭头连接。每张便利贴：大号手写数字(36pt) + 章节标题(12pt Bold) + 一行概述(10pt #333333)
- **内容要点**:
  - 要点1：诊断管线架构 — 8步6智能体的根因分析流水线
  - 要点2：RAG知识引擎 — FastAPI+ChromaDB的领域知识检索
  - 要点3：整体集成架构 — 三大模块如何协同工作
  - 要点4：关键技术决策 — 工程亮点与设计哲学
  - 要点5：总结 — 系统核心价值
- **图片决策**: text-only（目录用便利贴式卡片本身就是白板风格的视觉设计）
- **密度节奏**: 极简（过渡页）

### 第3页：项目全景
- **标题**: 给它传感器数据，它还你根因结论 — 全自动
- **密度**: 中等（60-80字）
- **论证逻辑**: 一句话定义系统价值，三个核心能力，一个关键数字
- **视觉主角**: 三个大数字作为视觉锚点
- **布局**: 上部手写标题+蓝色下划线，中部三列非等宽(3:4:3)——每列顶部超大手写数字(60pt蓝色) + 数字含义标签(10pt) + 一行注释，下部一个浅黄便利贴写核心定位
- **内容要点**:
  - 要点1：8阶段 — 从数据输入到最终报告的完整自动化管线，无人工干预
  - 要点2：6智能体 — 每个智能体各司其职（本体构建→统计→诊断→评审→报告→审计）
  - 要点3：3输出 — DETERMINED / COMPETING_SET / NEEDS_DATA 三种结论类型
  - 要点4：核心定位=场景自适应 — 不绑定特定工业场景，数据自描述+RAG+物理第一性原理
- **图片决策**: Q2通过（数字冲击页）→ text-only
- **密度节奏**: 中等

### 第4页：诊断Skill架构 — 8步管线全景
- **标题**: 8步管线 x 6智能体：从原始数据到可信诊断
- **密度**: 深度（100-130字）
- **论证逻辑**: 展示完整的诊断管线架构，每一步做什么、哪个智能体负责、产出什么
- **视觉主角**: 一张完整的管线架构流程图
- **布局**: 上部标题+蓝色下划线，主体为一张全宽架构流程图（880pt×380pt），展示8步从左到右的流程，每个步骤用便利贴式卡片，智能体名字用火柴人图标标注
- **内容要点**:
  - 要点1：Step 0 Setup 到 Step 7 Reviewer，8步管线完整流程
  - 要点2：每个Step的核心产出文件（ontology.json → validate_report.json → diagnosis.json → judge_feedback.json → report.md → optimizer.md）
  - 要点3：修复循环机制——Judge评分小于90重跑Diagnostician（最多3次），Reviewer未通过则D→J→R→R重跑（最多5次全局上限）
- **图片决策**: Q1通过 Q2不通过（流程图纯文字无法3秒传达）Q3=流程示意 Q4通过 → 1张 pipeline-architecture
- **配图类型**: pipeline-architecture
- **内容锚点**: 8步诊断管线的完整流程图，从数据输入(左)到报告输出(右)，6个智能体分别标注在不同阶段，修复循环用红色回退箭头标注
- **配图Prompt**: Hand-drawn whiteboard pipeline diagram showing 8 steps from left to right, each step as a wobbly sticky note box connected by arrows, 6 stick figure agents labeled at their steps, a red loop arrow from Judge back to Diagnose with tally marks max 3, another red loop from Review back to Diagnose with tally marks max 5, small output document icons below key steps, black ink lines on white, blue #4488FF accent on agent labels, professor whiteboard sketch style, 16:9 wide, no text
- **风格注入**: 已融入风格关键词

### 第5页：诊断方法论核心 — 竞争性假设协议
- **标题**: 诊断不是确认，是排除 — 竞争性假设协议
- **密度**: 中等（70-90字）
- **论证逻辑**: 解释诊断的核心方法论——为什么用排除法而非确认法
- **视觉主角**: 四条反推测条件 + 三种结论类型
- **布局**: 左右分栏（左55%右45%），左栏标题+4个手写checklist项（每项前有手绘checkbox），右栏3个不同大小的便利贴（DETERMINED大号绿色勾、COMPETING_SET中号黄色叹号、NEEDS_DATA小号红色问号），底部一行注释
- **内容要点**:
  - 要点1：四条反推测条件——时间先后+统计显著+物理机制+无矛盾，全部满足才能确立因果
  - 要点2：DETERMINED=已确定根因，COMPETING_SET=多个假设不可区分（置信度上限65%），NEEDS_DATA=数据不足需补充
  - 要点3：证据等级体系——1级直接测量(最高)到7级无支持假设(最低)
  - 要点4：双驱动分析=纯工艺波动诊断+工艺-检测双驱动诊断
- **图片决策**: Q2通过（checklist+分类用文字卡片即可清晰表达）→ text-only
- **密度节奏**: 中等

### 第6页：诊断修复循环 — 质量保障机制
- **标题**: 不通过？重跑！三层审查闭环保证诊断质量
- **密度**: 中等（70-90字）
- **论证逻辑**: 展示质量保障的修复循环机制，说明为什么结果可信
- **视觉主角**: 循环流程示意图
- **布局**: 上部标题，中部一张流程图（Diagnose→Judge→Reporter→Reviewer的循环，回退箭头标注修复条件），下部浅黄便利贴写关键数字
- **内容要点**:
  - 要点1：Judge评审10项标准（含物理源审计），评分小于90则重跑Diagnostician（最多3次）
  - 要点2：Reviewer独立物理真相审计，未通过则完整重跑D→J→R→R（全局上限5次）
  - 要点3：计数器持久化在.pipeline_events.jsonl中，断电不丢失
  - 要点4：四套独立编号体系——Pipeline Step / Agent Phase / Reasoning Segment / Method Stage
- **图片决策**: Q1通过 Q2不通过（循环流程图需要可视化）Q3=循环示意 Q4通过 → 1张 repair-loop
- **配图类型**: repair-loop
- **内容锚点**: 诊断→评审→报告→审计的四步循环，两个回退环（Judge回退到Diagnose，Reviewer回退到Diagnose）
- **配图Prompt**: Hand-drawn circular flow diagram on whiteboard, Diagnose box at top, Judge box right, Report box bottom, Review box left, clockwise arrows connecting them, a red curved arrow from Judge back to Diagnose with tally marks showing max 3, a bigger red curved arrow from Review back to Diagnose with tally marks showing max 5, a stick figure with magnifying glass at the Judge step, another stick figure with red pen at Review step, crossed-out wrong answer doodles, black ink on white, blue #4488FF on forward arrows, red #FF4444 on loop-back arrows, whiteboard sketch style, 16:9, no text
- **风格注入**: 已融入风格关键词

### 第7页：RAG知识引擎架构
- **标题**: 给诊断装上知识大脑 — RAG检索引擎
- **密度**: 深度（100-130字）
- **论证逻辑**: 展示RAG引擎的完整架构，如何为诊断提供领域知识
- **视觉主角**: RAG引擎架构图
- **布局**: 上部标题，主体一张全宽架构图（880pt×360pt），展示知识源→ChromaDB索引→三阶段管线(Retrieve→Score→Inject)→诊断Skill消费
- **内容要点**:
  - 要点1：技术栈——FastAPI(port 8765) + ChromaDB向量数据库 + sentence-transformers嵌入
  - 要点2：多源知识——本地Markdown(按##分段)、JSON参数库、用户上传文档(PDF/TXT/MD/CSV)、目录批量索引、Web搜索结果
  - 要点3：三阶段管线——/retrieve(语义检索+Web搜索) → /score(5维评分+Tier分级) → /inject(本体草稿生成)
  - 要点4：便捷端点 /pipeline/retrieve-score 一步到位
- **图片决策**: Q1通过 Q2不通过（架构图必须可视化）Q3=架构示意 Q4通过 → 1张 rag-architecture
- **配图类型**: rag-architecture
- **内容锚点**: RAG引擎完整架构——左侧多源知识输入(MD/PDF/JSON/Web)→中间ChromaDB向量库+三阶段管线(Retrieve→Score→Inject)→右侧诊断Skill消费本体知识
- **配图Prompt**: Hand-drawn system architecture diagram on whiteboard, left side shows 5 knowledge source icons feeding into a central ChromaDB cylinder, from ChromaDB three arrows go to three process boxes in sequence, final arrow going right to a diagnostic engine box with gear icon, stick figure librarian managing the knowledge sources, small arrows and annotations everywhere, black ink on white, blue #4488FF accent on the three pipeline stages, red #FF4444 circle around Inject stage, whiteboard sketch style, 16:9 wide, no text
- **风格注入**: 已融入风格关键词

### 第8页：RAG评分引擎 — 5维知识质量门控
- **标题**: 不是所有知识都值得信赖 — 5维评分+Tier分级
- **密度**: 中等（60-80字）
- **论证逻辑**: 解释RAG如何确保知识质量，不是简单的向量检索
- **视觉主角**: 5维评分slider bar展示
- **布局**: 左右分栏（左50%右50%），左栏5个评分维度（每个维度一行，手绘slider bar标注分数），右栏Tier分级金字塔（Tier1最精选→Tier4最宽松）+ 浅黄便利贴写运行持久化到SQLite
- **内容要点**:
  - 要点1：5维评分——领域相关性、技术深度、时效性、来源权威性、与诊断场景匹配度
  - 要点2：Tier分级——Tier1(精选高质量)→Tier2(良好)→Tier3(可用)→Tier4(宽松)
  - 要点3：运行持久化——每次检索运行记录到SQLite，可审计可追溯
  - 要点4：12+个API端点覆盖索引、检索、评分、注入、积累、查询增强全流程
- **图片决策**: Q2通过（5维评分用slider bar卡片呈现比图片更清晰）→ text-only
- **密度节奏**: 中等

### 第9页：Web应用架构 — 可视化诊断界面
- **标题**: 不是黑盒 — 实时可视化让诊断过程透明可控
- **密度**: 中等（70-90字）
- **论证逻辑**: 展示Web应用的完整架构，如何让用户实时观察和干预诊断过程
- **视觉主角**: 三层架构图
- **布局**: 上中下三层架构——上层Frontend(Vue 3 SPA, 5-tab布局)、中层Backend(Express.js + WebSocket事件总线)、下层Data(SQLite WAL + 诊断运行目录)，层间用手绘双向箭头标注通信协议
- **内容要点**:
  - 要点1：Frontend——Vue 3 + Vite + ECharts，5个标签页(Data/Diagnose/Reports/History/Chat)，SSE实时流+WebSocket推送
  - 要点2：Backend——Express.js(port 3210) + SQLite WAL模式 + WebSocket，事件总线架构
  - 要点3：5个路由 + 5个服务层 + Winston日志
  - 要点4：CLI工具ind-diag统一管理
- **图片决策**: Q2通过（三层架构用分层卡片即可清晰表达）→ text-only
- **密度节奏**: 中等

### 第10页：整体集成架构 — 三大模块如何协同
- **标题**: 三位一体：Skill管线 + RAG知识 + Web可视化
- **密度**: 深度（100-130字）
- **论证逻辑**: 这是整份PPT的核心页——展示三大模块如何协同工作，数据如何在模块间流转
- **视觉主角**: 完整的系统集成架构图
- **布局**: 上部标题，主体一张全宽架构图（880pt×380pt），三大模块用不同颜色的手绘边界框区分，模块间用粗手绘箭头标注数据流和接口协议
- **内容要点**:
  - 要点1：三大模块——Claude Code Skill + RAG引擎 + Web应用
  - 要点2：数据流——用户Web上传→Backend触发Skill→Step2 Context-Builder调用RAG→RAG返回知识→构建本体→诊断→WebSocket推送到Frontend
  - 要点3：关键接口——rag_client.py(Skill与RAG)、WebSocket(Backend与Frontend)、SSE(CLI到Frontend)
  - 要点4：部署方案——Docker + nginx + Cloudflare Tunnel
- **图片决策**: Q1通过 Q2不通过（三模块集成必须用架构图展示）Q3=集成架构 Q4通过 → 1张 integrated-architecture
- **配图类型**: integrated-architecture
- **内容锚点**: 三大模块的完整集成图——左侧Web应用通过WebSocket连接用户，中间诊断Skill管线执行核心诊断，右上RAG引擎提供知识支持，箭头标注数据流方向和接口协议
- **配图Prompt**: Hand-drawn system integration diagram on whiteboard, three large dashed boundary areas, left area shows a browser window icon with Vue and Express labels, center area shows the diagnostic pipeline as 8 connected sticky note boxes with stick figure agents, right area shows a database cylinder labeled ChromaDB, thick hand-drawn arrows connecting the three areas with small labels on arrows, a stick figure user at far left uploading data through browser, output report document coming out at bottom center, black ink on white, blue #4488FF accent on center pipeline, red #FF4444 on RAG knowledge flow arrows, whiteboard sketch style, 16:9 wide, no text
- **风格注入**: 已融入风格关键词

### 第11页：关键工程决策
- **标题**: 5个让这个系统能用而不只是能跑的工程决策
- **密度**: 中等（70-90字）
- **论证逻辑**: 展示核心工程亮点，说明这不是一个demo而是一个生产级系统
- **视觉主角**: 5个手写编号要点
- **布局**: 纵向5段，每段左侧大号手写数字(48pt蓝色) + 右侧标题(14pt Bold) + 一行解释(11pt #333333)，段间用手绘分割线。第3条用浅黄便利贴高亮
- **内容要点**:
  - 要点1：事件总线解耦 — EventEmitter将Claude CLI进程与WS/SSE传输分离
  - 要点2：Agent文件解耦 — 子智能体仅通过workspace文件通信，不共享主agent context
  - 要点3：Schema-First写入 — 14个JSON Schema覆盖所有结构化产出（浅黄高亮）
  - 要点4：三重执行证明 — .pipeline_events.jsonl + 产物文件 + artifact-check.mjs校验
  - 要点5：Agent Memory跨会话 — 4个子智能体有独立记忆目录，经验积累
- **图片决策**: Q2通过（工程清单用编号+卡片最清晰）→ text-only
- **密度节奏**: 中等

### 第12页：总结
- **标题**: 一个信念：工业诊断应该是数据驱动的、可解释的、可积累的
- **密度**: 极简（每条10-15字）
- **论证逻辑**: 收束——留下3条核心结论
- **视觉主角**: 3个不同大小的便利贴
- **布局**: 居中不规则排列——1个大便利贴(核心信念，浅黄底)居中偏上，2个小便利贴(技术亮点)左右分布，底部一行谢谢手写体
- **内容要点**:
  - 要点1（大便利贴）：数据驱动不等于黑盒——竞争性假设+物理第一性原理=可解释的AI诊断
  - 要点2（左小便利贴）：6智能体协同——每个智能体专注一件事，修复循环保证质量
  - 要点3（右小便利贴）：RAG+Memory——领域知识持续积累，诊断越做越好
- **图片决策**: text-only（结论靠文字力量，便利贴本身就是白板风格的视觉元素）
- **密度节奏**: 极简（收束页）

## 四、配图生成清单

> 12页中5页需要配图（配图率42%），其余7页为text-only纯文字排版。架构类主题配图率允许偏高。

| 序号 | 文件名 | 对应页码 | 尺寸 | 图片类型 | 内容锚点 | Prompt摘要 |
|------|--------|---------|------|---------|---------|-----------|
| 1 | p01_cover.png | 1 | 1536x864 | hero-cover | 工程师站在白板前，白板画着传感器→智能体→报告的简化流程 | 白板前火柴人工程师+白板流程图+咖啡杯涂鸦 |
| 2 | p04_pipeline.png | 4 | 1536x864 | pipeline-architecture | 8步诊断管线从Setup到Review，6智能体标注，修复循环回退箭头 | 8个便利贴式步骤+火柴人智能体+红色回退箭头 |
| 3 | p06_repair_loop.png | 6 | 1536x864 | repair-loop | 诊断→评审→报告→审计循环，两个回退环 | 四步循环+Judge回退(max3)+Reviewer回退(max5) |
| 4 | p07_rag_arch.png | 7 | 1536x864 | rag-architecture | 5知识源→ChromaDB→三阶段管线(Retrieve/Score/Inject)→诊断消费 | 5知识源图标→ChromaDB圆柱→三阶段管线→诊断引擎 |
| 5 | p10_integrated.png | 10 | 1536x864 | integrated-architecture | 三大模块(Web/RAG/Skill)集成，数据流与接口标注 | 三大虚线边界区域+粗箭头连接+火柴人用户 |

**配图统计**: 5页配图 / 12页总计 = 42%配图率

## 五、技术规范

- slide尺寸: 960pt×540pt（16:9宽屏，pptxgenjs LAYOUT_WIDE）
- 页眉: h=0pt（白板风格无传统页眉，用顶部手绘装饰线替代）
- 内容区: padding 8pt 20pt
- 底部栏: h=0pt（白板风格无底部栏，用右下角手写页码替代，10pt Comic Sans MS #4488FF）
- 图片: placeholder div + build.js addImage（Windows兼容，正斜杠路径）
- 编码: UTF-8 + meta charset
- text-only页排版: 大手写标题+便利贴卡片分区+超大数字锚点+手绘分割线+充足留白
- 配图Prompt已注入风格关键词：hand-drawn whiteboard + black ink + blue #4488FF + red #FF4444 + stick figures

## 六、知识直通

- 核心参考文件：
  - ref-skill-design.md — 诊断Skill设计评估（7个子智能体、竞争假设协议、修复循环）
  - ref-rag-design.md — RAG引擎设计（三阶段管线、5维评分、端点一览）
  - ref-project-overview.md — 项目全景（技术栈、文件结构、架构决策）
  - ref-backend-arch.md — 后端架构（事件总线、WebSocket、路由/服务层）
  - ref-frontend-design.md — 前端设计（Vue 3 SPA、5-tab布局、实时流）
