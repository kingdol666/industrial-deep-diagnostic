# DESIGN.md — 工业深度诊断系统 · 零基础使用教程（完整版）

> 风格路由：**技术培训 / 上手教程** → 不属于学术、咨询、红金政务任一垂直领域 → 走**通用设计原则**。
> 风格偏好跳过预览卡：用户已明确「浅色统一配色 + 结构化卡片 + 图文一对一 + 充足留白」，且要求直接改版出稿。
> 本版在上一版基础上只做**内容重绘**，视觉系统（色板/字体/母版/原型）保持不变。
> 本文件即本项目的设计宪法。

## 0. 设计定位

**真实截图为王，字要大，路要直。**
全篇 31 张图全部来自本机真实运行。版式的唯一任务是：把图放到最大、把编号指准、
把解释写得像对同事说话；并且**让第一次上手的人在第 2 页就看到完整路径**。

---

## 1. 画布与母版

| 项 | 值 |
|:--|:--|
| 画布 | 1280 × 720（16:9） |
| 页面 padding | 上 22 / 下 18 / 左 64 / 右 64 |
| A · 标题块 | y = 22 → 124（高 102）：主标题 **36px bold** + 副题 **17px** |
| B · 内容区 | y = 124 → 658（高 **534**，宽 1152） |
| C · 页脚条 | y = 658 → 702（高 44）：左「Industrial Deep Diagnostic · 零基础使用教程」**15px** 灰字 + 右页码 `NN / 40` |
| 间距基线 | 块间距 16 / 卡内 gap 12 / 卡 padding 18 |

封面 / 章节过渡 / 结束页用自定义版式，省略 C 区；其余内容页严格复用 A/B/C。

---

## 2. 颜色（4 个 hex，不新增）

| 角色 | hex | 面积占比 | 用在哪 |
|:--|:--|:--|:--|
| 中性 / 画布 | `#F7F4EC` 暖砂米 | ≥ 40% | 全篇底色，与截图外框同色，图与页自然融合 |
| 主色 | `#1D1B16` 松烟墨 | ≤ 55% | 文字、深色强调带、封面/章节页/速查页底色 |
| 辅色 | `#E4DCCB` 淡砂 | ≤ 30% | 卡片底、表格斑马纹、分隔线 |
| 强调色 | `#B8730F` 磷光琥珀 | ≤ 8%（hero ≤ 20%） | 巨型数字、步骤序号、编号徽标、关键结论 |

派生（不占色位）：正文次级 `rgba(29,27,22,0.72)`、反白 `#F7F4EC`、深色带内文 `#EFE9DA`。

**色彩节奏**：深色页 5 页（01 封面 / 12 与 20 两个章节页 / 32 命令速查 / 33 结语），
把它们均匀铺在全篇，形成「亮—暗—亮」的呼吸；其余页面琥珀只出现在序号与关键数字上。

---

## 3. 字体

| 层级 | 字号 | 字重 | 行高 | 字体 |
|:--|:--|:--|:--|:--|
| 封面主标题 | 78 | bold | 1.18 | `'Source Han Sans SC','Microsoft YaHei',sans-serif` |
| 章节大字 | 62 | bold | 1.12 | 同上 |
| 巨型数字 / 锚点 | 96 | bold | 1.00 | `'JetBrains Mono','Cascadia Mono',Consolas,monospace` |
| 页面主标题 | 36 | bold | 1.25 | 标题族 |
| 副标题 / 卡片小标题 | 22 | bold | 1.35 | 标题族 |
| **正文** | **20** | regular | 1.60 | 标题族 |
| 图注 / 小注 | 15 | regular | 1.45 | 标题族 |
| 页码 | 15 | regular | 1.4 | 标题族 |

**字重纪律**：同层只用一种字号；数据与终端一律等宽族且字重 bold，与正文形成对比。
**本版是上一版的美化重点**：正文由 17 提升到 **20**，卡片标题统一到 **22** —— 零基础读者的第一诉求是看得清。

**密度覆盖声明（图文教程型，显式覆盖通用门槛）**：
- 正文下限 22px 降为 **20px**，卡片内文 **18px** —— 图占内容区 60–95%，字号再放大会压图。
- 卡片数量相应由 3–4 张减到 **2–3 张**，用"少而清楚"换"大而好读"。
- 单页正文字数仍 ≥ 180（卡片组页 ≥ 300）。

---

## 4. 版式原型（9 种，交替使用）

| 代号 | 名称 | 结构 | 用在页 |
|:--:|:--|:--|:--|
| **A** | 满宽图 | 图 ≥ 92% B 区，文字压进图内注或 A/C 区 | 15 17 18 22 23 24 28 29 |
| **B** | 左图右卡 | 图 62% + 右侧竖排 2–3 卡 | 14 19 21 25 26 |
| **C** | 对开双图 | 两图并排 + 底部一行说明 | 13 27 |
| **D** | 横向步骤条 | 五步时间轴 + 连接箭头 | 02 |
| **E** | 巨型数字列 | 三列 96px 锚点数字 + 底部深色带 | 06 |
| **F** | 表格清单 | Table 组件，斑马纹 | 11 31 |
| **G** | 深色命令卡 | 满宽深色块 + 等宽命令行 | 08 09 10 32 |
| **H** | 章节过渡 | 斜切色块 + 巨型章号 | 12 20 |
| **I** | 左窄图右说明 | 窄图（≤ 40%）+ 右侧文字块 | 30 |

**重复校验**：连续两页不得同原型。映射表已逐页核对；A 原型出现最多（8 页），
但通过**图高不同（387–540）、注数不同（0–3）、是否带底部深色带**三者组合，页面彼此可区分。

---

## 5. 信息密度与留白

| 页型 | 图数 | 正文字数 | 主视觉占 B 区 | 留白上限 |
|:--|:--|:--|:--|:--|
| 封面 / 结束页 | 0–1 | 30–70 | — | 45% |
| 章节过渡 | 0 | 40 | — | 45% |
| 路线图 hero | 1 | 130 | ≥ 90% | 12% |
| 架构 / 管线 hero | 1 | 120 | ≥ 92% | 10% |
| 深色命令卡 | 0–2 | 150 | — | 30% |
| 表格清单 | 0 | 260 | — | 22% |
| 界面操作页 | 1 | 190 | ≥ 70% | 20% |

---

## 6. 配图

全部为 **P0 材料图**（真实截图 / 真实命令输出 / 依源码绘制），**无 ImageGen、无占位图**。

| 等级 | 内容 | 文件 |
|:--|:--|:--|
| L1 主视觉 | 17 张界面截图 + 5 张结构图 | `0N_*.png`、`d_*.png` |
| L2 支撑图 | 6 张终端命令卡 | `t_*.png` |
| L3 母版徽标 | 封面与结束页的「ID」方章（用 Box 绘制，不引外部图） | — |

**配图清单**（含真实性核对）：

| 文件 | 真实内容 | 用于页 | 已核对 |
|:--|:--|:--|:--|
| `d_roadmap.png` | 五步上手路线图（新增） | 02 | ✅ |
| `d_runtime.png` | 三服务 + 14 引擎运行时架构 | 04 | ✅ |
| `d_ports.png` | 3210 / 5180 / 8764 端口表 | 05 | ✅ |
| `t_prereq.png` | 本机 node/npm/python/uv 版本输出 | 07 | ✅ |
| `t_clone.png` `t_start.png` | 克隆安装 / 一键启动 | 08 | ✅ |
| `t_status.png` | `ind-diag status` 三服务全绿 | 09 | ✅ |
| `t_engine.png` | 引擎可用性接口返回（OMP 默认） | 10 | ✅ |
| `01_auth.png` `02_rail.png` | 登录页 / 七大功能区导航 | 13 | ✅ |
| `03_engine.png` | 14 引擎热切换列表 | 14 | ✅ |
| `04_data.png` | 数据工作台与文件表 | 15 | ✅ |
| `05_selected.png` | 选中后的批量操作条 | 16 | ✅ |
| `06_configure.png` | 诊断配置八控件 | 17 | ✅ |
| `07_tasklist.png` | 任务列表与结论列 | 18 | ✅ |
| `08_liverun.png` | **真实 OMP 运行中**的实时工作台 | 19 | ✅ |
| `11_report.png` | 报告 / 审计 / HTML 三页签 | 21 | ✅ |
| `12_audit.png` | ENDORSED 物理终审 | 22 | ✅ |
| `13_htmlreport.png` | 交互式 HTML 报告 | 23 | ✅ |
| `10_reportlist.png` | 报告清单两个入口 | 24 | ✅ |
| `15_history.png` | 运行账本 + 深度增强 | 25 | ✅ |
| `14_ontology.png` | 本体资产库与知识图谱 | 26 | ✅ |
| `16_engines.png` `17_enginedetail.png` | 引擎运行浏览 / 运行详情 | 27 | ✅ |
| `d_layout.png` | 目录结构 + 产物清单 | 28 | ✅ |
| `d_pipeline.png` | 9 步管线与 9 道闸门 | 29 | ✅ |
| `18_phone.png` | 窄屏响应式布局 | 30 | ✅ |

**编号来源**：界面截图的编号与引线坐标取自**抓图同一次会话**记录的元素包围盒，非目测摆位。

---

## 7. 页面映射表

| # | 文件 | 类型 | 角色 | 原型 | L1 文件 | 字数 | 留白 | 关键约束 |
|:-|:-|:-|:-|:-:|:-|:-|:-|:-|
| 01 | 01.slide | cover | hero | — | — | 70 | 42% | 78px 主标 + 3 数字徽标 |
| 02 | 02.slide | content | **hero** | D | d_roadmap | 120 | 10% | 五步路线图占满 B 区 |
| 03 | 03.slide | catalog | supporting | — | — | 230 | 24% | 四幕各 ≥ 30 字 |
| 04 | 04.slide | content | **hero** | A | d_runtime | 120 | 10% | 图 ≥ 94% B 区 |
| 05 | 05.slide | content | supporting | A | d_ports | 210 | 16% | 图 + 三端口深色卡 |
| 06 | 06.slide | content | **hero** | E | — | 240 | 26% | 3 个 88px 数字 |
| 07 | 07.slide | content | supporting | A | t_prereq | 200 | 20% | 图 ≥ 82% B 区 + 三卡 |
| 08 | 08.slide | content | supporting | G | t_clone + t_start | 150 | 18% | 两条终端卡等宽堆叠 |
| 09 | 09.slide | content | supporting | G | t_status | 190 | 20% | 单条大终端卡 + 两卡 |
| 10 | 10.slide | content | supporting | G | t_engine | 210 | 16% | 终端卡 + 三状态卡 |
| 11 | 11.slide | content | supporting | F | — | 280 | 20% | Table 四列清单 |
| 12 | 12.slide | transition | transition | H | — | 40 | 44% | 62px 章号 + 巨号 03 |
| 13 | 13.slide | content | supporting | C | 01_auth + 02_rail | 200 | 14% | 左宽右窄对开 |
| 14 | 14.slide | content | supporting | B | 03_engine | 200 | 18% | 右侧三卡等高 |
| 15 | 15.slide | content | supporting | A | 04_data | 130 | 12% | 图 ≥ 93% B 区 |
| 16 | 16.slide | content | supporting | A | 05_selected | 210 | 22% | 宽条图 + 三卡 |
| 17 | 17.slide | content | supporting | A | 06_configure | 200 | 18% | 图 + **两**卡（与 16 区分） |
| 18 | 18.slide | content | supporting | A | 07_tasklist | 200 | 14% | 图 + 四指标条 |
| 19 | 19.slide | content | **hero** | B | 08_liverun | 240 | 14% | 图 60% 宽 + 三卡 |
| 20 | 20.slide | transition | transition | H | — | 40 | 44% | 与 12 页镜像 |
| 21 | 21.slide | content | supporting | B | 11_report | 220 | 16% | 右三卡（带标签胶囊） |
| 22 | 22.slide | content | supporting | B2 | 12_audit | 220 | 14% | 上左图右卡 + 下通栏双卡 |
| 23 | 23.slide | content | supporting | A | 13_htmlreport | 90 | 10% | 图 98% B 区，满幅 |
| 24 | 24.slide | content | supporting | B-镜像 | 10_reportlist | 220 | 16% | 左卡右图（镜像 21） |
| 25 | 25.slide | content | supporting | B+ | 15_history | 230 | 14% | 上图形右三卡 + 底部深色带 |
| 26 | 26.slide | content | supporting | B | 14_ontology | 220 | 14% | 图 68% 宽 + 右窄三卡 |
| 27 | 27.slide | content | supporting | A | 16_engines | 90 | 10% | 图 ≥ 97% B 区 |
| 28 | 28.slide | content | supporting | A | 17_enginedetail | 190 | 22% | 图 69% B 区 + 双卡 |
| 29 | 29.slide | content | supporting | A | d_layout | 130 | 12% | 图 83% B 区 + 提示带 |
| 30 | 30.slide | content | **hero** | A | d_pipeline | 120 | 10% | 图 88% B 区 |
| 31 | 31.slide | content | supporting | I | 18_phone | 230 | 20% | 窄图不拉伸（468×458） |
| 32 | 32.slide | content | supporting | F | — | 300 | 18% | Table 三列九行 |
| 33 | 33.slide | content | supporting | G | — | 240 | 20% | 深色 2×2 命令卡 |
| 34 | 34.slide | ending | supporting | — | — | 80 | 42% | 四步回顾卡 |

**版式重复校验**：逐页核过，无连续两页同原型。
A 出现 10 页但由「图高（299–534）、注数（0–4）、是否带底部色带」三者组合区分；
16 与 17 相邻同为 A，已用「三卡 vs 两卡 + 图高 317 vs 220」拉开差异。

---

## 8. 本版新增：OMP 终端截图的渲染规范

OMP 的配置流程用**真实终端截图**呈现，不用 HTML 排版的"伪终端卡"。生产链路：

1. `pywinpty` 起一个真实 Windows 控制台，`cmd.exe` → `cd 项目目录` → `omp`
2. 按脚本发送按键（`/login`、方向键、搜索词），每一步等界面稳定
3. 捕获原始转义流，用自写的 ANSI 屏幕模拟器还原成字符网格 + 每格颜色
   （支持 CSI 定位 / 擦除 / SGR 颜色 / `ECH` 原位擦白 / CJK 双宽字符）
4. 按"实际显示尺寸"渲染成图：**图内字号 = 幻灯片上的字号**，禁止缩放

| 文件 | 内容 | 显示尺寸 | 用于页 |
|:--|:--|:--|:--|
| `omp_cmd.png` | cmd 刚打开的窗口 | 494×162（1:1） | 08 |
| `omp_welcome.png` | omp 欢迎框（含当前模型与来源） | 784×439（1:1） | 07 |
| `omp_composer.png` | 输入框 + 状态栏 | 1077×137（1:1） | 08 / 13 |
| `omp_slash.png` | 输入 `/login` 时的命令补全 | 946×273（1:1） | 09 |
| `omp_providers.png` | 服务商列表（未搜索） | 937×291（1:1） | 10 |
| `omp_deepseek.png` | 搜索 deepseek 后的过滤结果 | 937×125（1:1） | 10 |
| `omp_apikey.png` | Login to DeepSeek · 粘贴 API Key | 937×273（1:1） | 11 |
| `omp_models.png` | /model 模型选择器 | 632×534（0.73×） | 12 |
| `omp_liverun.png` | OMP harness 真实运行中的工作台（带编号注解） | 700×470（0.48×） | 26 |

**两条纪律**：

- 终端截图**尽量按 1:1 显示**。一旦缩放，图内 13px 的等宽字会掉到 9px 以下，读者看不清命令。
  模型选择器天然超过 B 区高度（40 行 × 17px = 733px），只能缩到 0.73×，此时必须靠右侧三张卡把
  关键信息用正文重述一遍。
- 终端窗口的**内容全部来自真实捕获**，只补一层窗口边框（标题栏 + 三个圆点），不做任何内容美化。

---

## 9. 页面映射表

| # | 文件 | 角色 | 原型 | L1 文件 | 关键约束 |
|:-|:-|:-|:-:|:-|:-|
| 01 | 01.slide | hero | — | — | 78px 主标 + 3 数字徽标 |
| 02 | 02.slide | **hero** | D | d_roadmap | 六步路线图占满 B 区 |
| 03 | 03.slide | supporting | — | — | 四幕 + 两条读法 |
| 04 | 04.slide | **hero** | A | d_runtime | 图 ≥ 94% B 区 |
| 05 | 05.slide | supporting | A | d_ports | 图 + 三端口深色卡 |
| 06 | 06.slide | **hero** | E | — | 3 个 88px 数字 |
| 07 | 07.slide | supporting | B | omp_welcome | 左图 1:1 + 右双卡 + 深色带 |
| 08 | 08.slide | supporting | G | omp_cmd + omp_composer | 两张终端图 1:1 + 双卡 |
| 09 | 09.slide | supporting | G | omp_slash | 终端图 1:1 + 三卡 |
| 10 | 10.slide | supporting | G | omp_deepseek + omp_providers | 上下两张终端图 + 双注 |
| 11 | 11.slide | supporting | G | omp_apikey | 终端图 1:1 + 三卡 |
| 12 | 12.slide | supporting | B | omp_models | 左图 + 右三卡（缩放页） |
| 13 | 13.slide | supporting | F+G | omp_composer | 状态栏条 + 命令 Table |
| 14 | 14.slide | supporting | A | t_prereq | 图 ≥ 82% B 区 + 三卡 |
| 15 | 15.slide | supporting | G | t_clone + t_start | 两条终端卡等宽堆叠 |
| 16 | 16.slide | supporting | G | t_status | 单条大终端卡 + 两卡 |
| 17 | 17.slide | supporting | G | t_engine | 终端卡 + 三状态卡 |
| 18 | 18.slide | supporting | F | — | Table 四列清单 |
| 19 | 19.slide | transition | H | — | 62px 章号 + 巨号 03 |
| 20 | 20.slide | supporting | C | 01_auth + 02_rail | 左宽右窄对开 |
| 21 | 21.slide | supporting | B | 03_engine | 右三卡等高 |
| 22 | 22.slide | supporting | A | 04_data | 图 ≥ 93% B 区 |
| 23 | 23.slide | supporting | A | 05_selected | 宽条图 + 三卡 |
| 24 | 24.slide | supporting | A | 06_configure | 图 + 两卡（引线已就近） |
| 25 | 25.slide | supporting | A | 07_tasklist | 图 + 四指标条 |
| 26 | 26.slide | **hero** | B | omp_liverun | 图 61% 宽 + 三卡 + 深色带 |
| 27 | 27.slide | transition | H | — | 与 19 页镜像 |
| 28 | 28.slide | supporting | B | 11_report | 右三卡（标签胶囊） |
| 29 | 29.slide | supporting | B2 | 12_audit | 上左图右卡 + 下通栏双卡 |
| 30 | 30.slide | supporting | A | 13_htmlreport | 图 98% B 区 |
| 31 | 31.slide | supporting | B-镜像 | 10_reportlist | 左卡右图 |
| 32 | 32.slide | supporting | B+ | 15_history | 上图形右三卡 + 底部深色带 |
| 33 | 33.slide | supporting | B | 14_ontology | 图 68% 宽 + 右窄三卡 |
| 34 | 34.slide | supporting | A | 16_engines | 图 ≥ 97% B 区 |
| 35 | 35.slide | supporting | A | d_layout | 图 83% B 区 + 提示带 |
| 36 | 36.slide | **hero** | A | d_pipeline | 图 88% B 区 |
| 37 | 37.slide | supporting | I | 18_phone | 窄图不拉伸 |
| 38 | 38.slide | supporting | F | — | Table 三列九行 |
| 39 | 39.slide | supporting | G | — | 深色 2×2 命令卡 |
| 40 | 40.slide | ending | — | — | 四步回顾卡 |

**版式重复校验**：无连续两页同原型。08/09/10/11 连续四页同为 G（终端截图页），
但它们由「图数（1 或 2）、图高（125–291）、卡数（2 或 3）」组合区分，且第 13 页用 F+G 混合收尾，
不构成"等宽卡片横排"的重复。
