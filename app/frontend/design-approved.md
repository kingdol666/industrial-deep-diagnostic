# direction-approved.md — Web Console UI 美化方向（2026-09-19）

## 豁免声明（huashu-design 三方向硬门）

本次任务为**既有产品 UI 的迭代美化**（huashu-design「唯一豁免」第 2 类：同一项目内改稿——
方向即产品现有设计系统「warm-iron graphite + phosphor amber · Fraunces + IBM Plex ·
precision instrument」），且为自主会话（用户要求直接执行到底，见会话上下文）。
不重新过三方向门，方向依据产品既有 design system（global.css 头部注释即规范原文）。

## Form 五问

1. **叙事角色**：工作仪表台（working instrument console）——主角是数据与诊断内容，chrome 必须后退。
2. **观众距离**：50-70cm 桌面工位，高密度数据合法，靠层级补偿字号。
3. **视觉温度**：冷静权威（calm authority）。暖石墨底，单一琥珀信号色，磷光绿只给 live/OK。
4. **容量**：百行级表格 × 7 导航 × 14 引擎——密度管理是核心矛盾（重复噪音、accent 通胀）。
5. **视觉母题**：精密仪表/控制室面板（发丝线、等宽微标注、tabular 数字、状态指示灯）。
   美化 = 把这个母题执行到位，不引入新母题。

## 诊断出的具体问题（基线截图 paper/workbench/ui-baseline/）

- P1 accent 通胀：状态徽章/行内按钮琥珀色铺满全屏（PENDING×20、Analyze/Read Report 每行 amber）
- P2 emoji slop：💬 ✨ 📁 📊 ⚡（ChatView 空态、DiagnosisView 目标/阶段、ReportViewer、i18n 文案）
- P3 重复：OMP 页内 hero 与顶栏双标题；ChatView 每卡片重复「DIAGNOSE SESSIONS」章
- P4 语言切换按钮在侧栏底部孤居中；stat 带拉伸过宽无仪器读数感
- P5 本体图节点薄荷糖配色与全局琥珀系冲突（低风险处理）

## 执行方案（不破坏功能为前提）

CSS 语义化徽章（PENDING→中性灰、RUNNING→琥珀、绿=完成、红=停/败）；emoji 全部替换为
字体字形/纯 CSS 仪表标记；去重双标题；语言切换并入 footer 行；stat 带改单面板发丝线
分隔的 readout；按钮 hover/press 微交互与 focus-visible 统一；本体图节点色收敛进 token 族。

用户选择记录：自主会话，按上述豁免直接执行；结果以 20 轮真实交互测试验证功能不回退。
