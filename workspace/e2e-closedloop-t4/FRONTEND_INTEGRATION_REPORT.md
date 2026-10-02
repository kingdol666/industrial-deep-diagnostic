# 前端闭环控制台集成测试报告（2026-10-02）

> 分支 `v4-AgentWorkShopIntegrate` · 前端 5180（Vite dev）× 后端 3210（Express）× 真实浏览器驱动（ZCode IAB）× visual-judge 视觉验收。

## 交付内容

**新增「ClosedLoop 闭环控制台」tab**（`∿`，Diagnose/Reports 之后的常驻 tab）：

| 文件 | 内容 |
|------|------|
| `components/closedloop/ClosedLoopView.vue` | 容器：三子面板切换 + 全局刷新 + 共享 `cl-*` 设计系统样式（沿用暗色石墨+磷光琥珀规范） |
| `components/closedloop/SentinelPanel.vue` | 基线登记表 / 构建基线（异步任务轮询）/ 批筛 watch（异步）/ 增量快筛（同步）；告警表（规则×参数×级别药丸×观测值）；数据路径 datalist（服务端真实文件清单） |
| `components/closedloop/ExperiencePanel.vue` | 库状态 / 动作摄取（异步归因 job 轮询）/ 故障签名检索（命中卡片：匹配分、证据级、autonomy null 标注、归因 Δ+CI95）/ 执行反馈（一键带出 experience_id） |
| `components/closedloop/OptimizerPanel.vue` | Campaign 列表（阶段药丸）/ 发起 campaign（O-G1）/ 会话状态（阶段·轮次·预算·next_action）/ design 布点表 / **一键生成回执模板** / ingest / 暂停恢复 |
| `api/index.js` | +16 个闭环 API 方法 |
| `i18n/zh.js` `en.js` | `tabs.closedloop` + `closedloop.*` 全量中英文案 |
| 后端 `closedloop.util.mjs` + `sentinel/experience.service.mjs` | **`resolveServerPath` 仓库相对路径解析器**（修复后端以 app/backend 为 cwd 导致 UI 相对路径 404 的兼容缺陷） |

## 前后端交互测试结果（全部真实执行）

| # | 交互链 | 结果 |
|---|--------|------|
| 1 | 登录（UI 表单 → `/api/auth/login`） | ✅ 进入主工作台 |
| 2 | 哨兵·构建基线（仓库相对路径 history.csv + doe_run） | ✅ 任务 completed，`L1-UI` 入登记表 |
| 3 | 哨兵·批筛 watch（10000 行漂移窗） | ✅ exit 1 · alert · **11 告警**（含 C2 WINDOW_OUT_OF_RANGE critical 88.45）· 告警表渲染 |
| 4 | 哨兵·增量快筛（300 行漂移切片） | ✅ exit 1 · alert · 5 告警 · 基线模式 prior |
| 5 | 经验·摄取动作日志（异步归因 job） | ✅ job `attr-…` running→completed，库条目 2 |
| 6 | 经验·故障签名检索 | ✅ **playbook 命中**：匹配分 1 · regime · E0 · autonomy null (AWS) · Δ+CI95 展示 |
| 7 | 经验·执行反馈 | ✅ 成功 effective（experience_id 一键带出） |
| 8 | 寻优·发起 campaign `OPT-20261002-101` | ✅ O-G1 通过 · initialized |
| 9 | 寻优·design→模板→回投 ×7 轮（R001 LHS 8 布点 → poly_refine → confirm_replicates） | ✅ 状态机 exploring→confirming→exploiting 全程推进（7/10 轮，14/30 trials） |
| 10 | 寻优·收敛纪律 | ✅ R007 确认轮被**双门槛诚实拒绝**（1 复测出界 → fake-summit 回退 + LHS 注入） |

## 视觉验收（visual-judge）

三张截图（`workspace/e2e-closedloop-t4/shots/01–03*.png`）**3/3 PASS**——无截断、无重叠、药丸/表格/JSON 视图样式统一、暗底对比度达标。

## 测试中发现并修复的缺陷

| 级别 | 缺陷 | 修复 |
|------|------|------|
| **P1（skill 脚本）** | `optimizer.py` poly_refine 分支 `dict(zip(names, best["coded"]))`：doe-analyzer `refine_optimum` 返回的 `coded` 是 dict，zip 迭代**键**生成 `{"x0":"x0"}` → `float()` 崩溃。GP 退化的关键恢复路径在真实 2 因子 campaign 下必现 | 改为 `dict(best["coded"])`；optimizer 测试 55/55 保持全绿 |
| P1（后端） | 闭环路由 `requireExistingFile`/`registerDataset` 用进程 cwd（app/backend）解析相对路径，UI 的 `data/…`、`workspace/…` 路径全部 404 | `closedloop.util.resolveServerPath`（PROJECT_ROOT 兜底），后端回归 160/160 全绿 |
| P2（前端） | API `request()` 已解包 `data.data`，面板重复解构；任务视图是拍平形态（`exit_code/alerts` 在顶层）；基线登记表 `{lines:{…}}` 对象形态；库条目字段名 `store_entries` | 全部按实际契约修正 |
| P2（i18n） | `examples`/`effective` 等 6 个键漏配（下拉显示原始 key） | zh/en 补齐 |

## 运行环境

后端（3210）与前端 dev（5180）均在本会话后台运行；浏览器控制台页面已标记 deliverable 供继续操作。截图存于 `workspace/e2e-closedloop-t4/shots/`。
