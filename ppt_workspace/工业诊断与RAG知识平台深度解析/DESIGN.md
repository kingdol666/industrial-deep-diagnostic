# DESIGN.md — 工业诊断与RAG知识平台深度解析（7 页）

## 1. 画布与母版（1280×720）
| 母版区 | 垂直位置 | 高度 | 规则 |
| :--- | :--- | :--- | :--- |
| 页面 padding | 上下 20px / 左右 56px | — | 安全区 x:56–1224（1168px），y:20–700 |
| **A · 标题块** | 20–108px | 88px | 主标题 30–32px bold + 副标题 14px；右上元信息 mono 12px |
| **B · 内容区** | 120–640px | 520px | 全部正文/图/结构 |
| **C · 页脚条** | 666–700px | 34px | 左：项目名 / 右：`NN / 07`，12.5px |

高度核算：20 + 88 + 12 + B + 12 + 34 + 20 = 720 → **B ≤ 520px**（每页按此上界分配）。

## 2. 颜色系统（双系统语义色 + 中性）
| 角色 | Hex | 用途 |
| :--- | :--- | :--- |
| 文本主色 ink | `#0F172A` | 标题与正文主体 |
| **IDD 色 blue** | `#2563EB` | IDD 相关层/列/锚点（浅底 `#EFF6FF`，边框 `#BFDBFE`） |
| **RAG 色 violet** | `#7C3AED` | RAG 相关层/列/锚点（浅底 `#F5F3FF`，边框 `#DDD6FE`） |
| 证据色 teal | `#0D9488` | 实证数字、正向结果、通过标记（浅底 `#F0FDFA`） |
| 表面色 surface | `#F1F5F9` | 底板、说明条、图片衬底 |
| 中性 | `#FFFFFF` 页底 / `#E2E8F0` 边框 / `#F8FAFC` 卡底 / `#64748B` `#94A3B8` 次级文字 / `#0B1220` 深底 | — |

- 语义绑定全篇不可互换：**blue = 工业数据诊断 IDD**，**violet = RAG 知识平台**，**teal = 实证/通过**。
- 闸门页（03）使用 blue 色阶递进 `#EFF6FF → #DBEAFE → #BFDBFE` 表达"越往后越严"。
- 渐变仅在封面底部管线带使用一次（`135deg, #EFF6FF → #F5F3FF`）；其余纯色。

## 3. 字体系统（2 套家族，本机已核验）
| 层级 | 字号 | 字重 | 行高 | 字体 |
| :--- | :--- | :--- | :--- | :--- |
| 封面主标题 | 52px | bold | 1.2 | Noto Sans SC |
| 页面主标题 | 30px | bold | 1.25 | Noto Sans SC |
| 巨型数字锚点 | 44–48px | bold | 1.0 | Cascadia Mono |
| 卡片/闸门标题 | 15–17px | bold | 1.3 | Noto Sans SC |
| 正文 | 12–13.5px | normal | 1.6 | Noto Sans SC |
| 标签 / 元信息 | 10.5–11.5px | normal | 1.5 | Cascadia Mono |
| 页脚 | 12.5px | normal | 1.4 | Noto Sans SC |

## 4. 信息密度与"不落俗套"约束
- 每页正文 ≥ 220 字；留白 ≤ 30%；每页 ≥ 1 个视觉锚点（≥44px 数字 / ≥40% B 区面积的图）。
- **禁止连续两页使用同一种版式结构**：时间轴（02）→ 纵向闸门（03）→ 大图+巨数（04）→ 左图右栏（05）→ 通栏大图（06）→ 左流向右矩阵（07）。
- 禁止把 200×70 小图塞进标题块；L3 角标不设（本 deck 不用角标图）。
- 每页图片 ≤ 3 张，图片总面积 ≤ B 区 65%。

## 5. 页面映射表
| # | 文件 | 类型 | 角色 | 版式 | 主视觉 | 图片尺寸 | 关键约束 |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | 01.slide | cover | hero | 左标题 + 右双系统身份卡 + 底部通栏管线 | idd_pipeline.png | 1168×150（5.39:1 通栏） | 主标题 52px；两张身份卡等高 200 |
| 02 | 02.slide | content | supporting | 横向时间轴（10 节点）+ 下方左文右图 | idd_ui_diagnose.png | 476×298 | 10 节点等距；轴线上方步号、下方 Agent |
| 03 | 03.slide | content | hero | 纵向三闸门（色阶递进）+ 底部封顶条 | — | — | 三列等宽 372；每列 ≥ 130 字 |
| 04 | 04.slide | data | hero | 左窄数字栏（42%）+ 右宽图（58%）+ 底部实证条 | idd_benchmark.png / idd_mechanism.png | 640×340 / 380×150 | 巨型数字 5/6、1/1、0 误报 |
| 05 | 05.slide | content | supporting | 左大图（55%）+ 右竖排要点（45%） | rag_architecture.png / rag_graph.png | 620×372 / 300×168 | 与 02/04 结构不同 |
| 06 | 06.slide | data | hero | 通栏大图（71%）+ 右窄要点栏 | rag_qdcvr_pipeline.png | 818×468 | 图区 ≥ B 区 65% |
| 07 | 07.slide | content | hero | 左纵向闭环 4 步 + 右 2×2 能力矩阵 | rag_search.png（可选小图） | 300×168 | 收束金句 |

## 6. 素材清单（全部真实，无生成图）
| 文件 | 来源 | 内容 |
| :--- | :--- | :--- |
| `idd_pipeline.png` | IDD `paper/figures/fig_pipeline.png` | 管线全流程图 |
| `idd_benchmark.png` | IDD `paper/figures/fig_benchmark.png` | 基准结果：9 场景 fault outcomes + rubric/judge 评分分布 |
| `idd_mechanism.png` | IDD 真实分析产物 | 机理判别：8# 拉伸扭矩 vs 熔融缺陷族 / 划伤 |
| `idd_ui_diagnose.png` / `idd_ui_ontology.png` | Playwright 现场截图（IDD `:5180`） | 诊断工作台 / 本体模型管理 |
| `rag_architecture.png` | rag-knowledge 仓库 `docs/images/` | 五层架构图 |
| `rag_qdcvr_pipeline.png` | 同上 | QDCVR 六阶段检索管线 + 可信度模型 |
| `rag_graph.png` / `rag_search.png` / `rag_soul.png` | 同上 `docs/screenshots/` | 知识图谱 / 检索界面 / SOUL 人格工作室 |
