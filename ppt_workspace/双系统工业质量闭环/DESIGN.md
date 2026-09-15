# DESIGN.md — 双系统工业质量闭环（单页）

## 0. 设计路线
通用设计原则（universal-only）。场景为技术项目介绍，不命中学术 / 咨询 / 政务预设风格。
风格基调：**浅色白底 + 双色分区 + 卡片化**，克制、清晰、工程师审美。

## 1. 画布与母版（1280×720）
| 母版区 | 垂直位置 | 高度 | 内容 |
| :--- | :--- | :--- | :--- |
| 页面 padding | 上下 20px / 左右 64px | — | 安全区 x:64–1216, y:20–700 |
| **A · 标题块** | 20–116px | 96px | 主标题 34px bold + 副标题 15px；右上角元信息 13px 灰字 |
| **B · 内容区** | 132–600px | 468px | 双卡（336px）+ 间距 20px + 闭环条（112px） |
| **C · 页脚条** | 660–700px | 40px | 左：项目名 / 右：页码 `01 / 01`，13px 灰字 |

高度核算：20(上pad) + 96(A) + 16(gap) + 336(卡片) + 20(gap) + 112(闭环条) + 60(至页脚) + 40(C) + 20(下pad) = 720 ✅

## 2. 颜色系统（色彩池 4 色 + 中性）
| 角色 | Hex | 用途 | 面积占比 |
| :--- | :--- | :--- | :--- |
| 文本主色 ink | `#0F172A` | 标题、正文主体 | 中性 |
| 项目色 teal（BOPET） | `#0D9488` | BOPET 层/列标识与要点前缀 | ≤ 15% |
| 项目色 blue（IDD） | `#2563EB` | IDD 层/列标识、闭环流程、结果锚点 | ≤ 25% |
| 项目色 violet（RAG） | `#7C3AED` | RAG 层/列标识与要点前缀 | ≤ 12% |
| 表面色 surface | `#F1F5F9` | 卡片底、结果带底、图片衬底 | ≤ 40% |
| 中性（不计入池） | `#FFFFFF` 页面底 / `#E2E8F0` 1px 边框 / `#64748B` 次级文字 / `#94A3B8` 页脚 / `#F8FAFC` 卡片底 / `#0B1220` 终端底 | — | 剩余 |

- 语义绑定（全篇不可互换）：**teal = BOPET 数据平台**、**blue = IDD 诊断引擎**、**violet = RAG 知识平台**；每层/每列的浅底为其 50 色阶（`#F0FDFA` / `#EFF6FF` / `#F5F3FF`），边框为对应 200 色阶。

- 语义绑定：**teal = BOPET（数据侧）**，**blue = IDD（诊断侧）**，全篇不得互换。
- 渐变策略：本页不使用渐变（纯色卡片 + 1px 边框），保持工程感。
- 半透明策略：仅卡片顶部 3px 色条与图片衬底使用纯色，无叠加透明度。
- 强调色（提高饱和的 blue）仅出现在：右卡边框高亮、闭环流程箭头、案例数字 `0.18`。占比 ≤ 10%。

## 3. 字体系统（2 套家族，均经本机字体核验）
| 层级 | 字号 | 字重 | 行高 | 字体 |
| :--- | :--- | :--- | :--- | :--- |
| 页面主标题 | 34px | bold | 1.25 | Noto Sans SC（思源黑体同源，本机已安装） |
| 页面副标题 | 15px | normal | 1.5 | Noto Sans SC |
| 卡片标题 | 21px | bold | 1.3 | Noto Sans SC |
| 卡片副题 / 引导句 | 13px | normal | 1.5 | Noto Sans SC |
| 卡片要点 | 13.5px | normal | 1.62 | Noto Sans SC |
| 技术标签 chips | 11.5px | normal | 1.4 | Cascadia Mono |
| 案例巨量数字 | 48px | bold | 1.0 | Cascadia Mono |
| 页脚 | 13px | normal | 1.4 | Noto Sans SC |

> 字体核验：初版曾用「思源黑体 / JetBrains Mono」，校验时报字体回退（本机未安装）；已替换为本机实际安装的 Noto Sans SC（`NotoSansSC-VF.ttf`）与 Cascadia Mono（`CascadiaMono.ttf`），二次校验零回退警告。

## 4. 信息密度声明
- 类型：内容页 · 卡片组（双卡）+ 数据图表
- 正文合计 ≥ 300 字；图片 2 张（均为真实项目图表）；留白 ≤ 25%
- 卡片填充率 ≥ 85%：卡片高 336px → 每卡正文 ≥ 100 字 ✅
- 横向兄弟卡对齐：两卡标题块高 46px、正文块、尾部 chips 三段 y 轴对齐（chips 用 `marginTop:'auto'` 钉底）

## 5. 配图清单
| 文件 | 来源 | 类型 | 真实内容 | 使用位置 | 尺寸 | 是否核对 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `assets/bopet_md_temporal.png` | 项目真实产物（P0 材料图）：`experience/reports/bopet_md_scratch/03_figures/fig_temporal_overview.png` | L2 支撑图 | BOPET MD 段关键参数时序总览（6 联图，05-04~05-13） | 左卡（BOPET）图片位 | 176×176（方形，contain） | ✅ 已 Read 核对 |
| `assets/idd_mechanism_discrimination.png` | 项目真实产物（P0 材料图）：`experience/reports/bopet_md_scratch/03_figures/fig4_mechanism_discrimination.png` | L2 支撑图 | 机理判别：8# 拉伸扭矩 vs 熔融缺陷族 / 划伤 的 |ρ| 对比 | 右卡（IDD）底部通栏图 | 516×142（宽幅 2.24:1，contain） | ✅ 已 Read 核对 |

说明：两图均为用户项目的**真实分析产物（材料图 P0）**，非生成图；风格同属"科学图表"，全篇统一。闭环条与流程箭头用 SVG 结构化绘制（P2 允许）。

## 6. 页面映射表（2 页 · 三系统版）
| # | 文件 | 类型 | 角色 | 版式 | 主视觉 | 字数估算 | 留白% | 色彩分配 | 关键约束 |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 01 | 01.slide | 架构+运行 | hero | 左"三层系统"纵列（每层一色）+ 底部数据流条；右"运行启动"证据列（终端图 / 登录卡 / 三服务端口表） | term_startup.png + login_card.png | 约 380 | 16% | surface42% + blue22% + teal13% + violet10% + 强调 | 三层等高 128px；层内左侧 4px 色条绑定项目色 |
| 02 | 02.slide | 功能+结果 | hero | 上：三等分列（每列=项目名+真实截图+3 条要点）；下：结果带（96 锚点 + 机理图 + 三条验证结论） | bopet_dashboard.png / ui_diagnose.png / rag_search.png + idd_mechanism_discrimination.png | 约 400 | 15% | surface38% + 三项目色各约 12% + 强调12% | 三列等宽 372px、截图统一 372×200；锚点数字 96（48px） |

> 说明：原「双系统工业质量闭环」总览页（`slides/01_overview.slide`）保留为备份文件，不再写入演示文稿。

## 7. 素材来源说明（全部为真实界面 / 真实产物，无生成图）
| 文件 | 来源 | 内容 |
| :--- | :--- | :--- |
| `term_startup.png` | 真实执行 `node commands/cli.mjs status` 输出经渲染（已剥离 ANSI） | 三服务 running / healthy |
| `login_card.png` | Playwright 现场截图（IDD，元素级裁切） | IDD 统一鉴权入口 |
| `bopet_dashboard.png` | Playwright 现场截图（BOPET EDA `:3100`，admin 登录后） | 数据概览看板：总量/新增/待处理/已结案、月度趋势、模板分布 |
| `ui_diagnose.png` | Playwright 现场截图（IDD `:5180`，注入会话 token） | 实时诊断工作台：状态/结论/评分 |
| `ui_data.png` / `ui_ontology.png` | 同上 | 数据接入与选择 / 本体模型管理（备用素材） |
| `rag_search.png` | rag-knowledge 仓库自带官方截图（`docs/screenshots/`） | QDCVR 知识检索界面 |
| `rag_architecture.png` / `rag_graph.png` / `rag_soul.png` | 同上 | 五层架构图 / 知识图谱 / SOUL 人格工作室（备用素材） |
| `bopet_md_temporal.png` / `idd_mechanism_discrimination.png` | 项目真实分析产物 | BOPET MD 段时序总览 / 机理判别结果 |



## 7. 自检清单（提交前逐项确认）
1. A/B/C 三区齐全，页码 `01 / 01` 在右下
2. 标题块右侧无装饰小图（仅 13px 元信息文字）
3. 视觉锚点：案例数字 48px + 右卡通栏图（≥40% 卡宽）
4. 仅用本文件 4 色 + 中性；仅 2 套字体家族
5. 留白约 22% ≤ 35%
6. 两卡尾部 chips 等高对齐（`marginTop:'auto'`）
7. 所有图片位于 `assets/`，无在线 URL
