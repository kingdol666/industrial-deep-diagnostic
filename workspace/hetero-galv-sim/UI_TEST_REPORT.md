# 前后端联调 UI 实测报告 — 产线报告（镀锌线场景）

- 时间：2026-10-17；方式：**真实浏览器操作**（ZCode IAB）+ 当前代码前后端（backend 3210 `npm start` / frontend 5180 vite）
- 场景数据：`workspace/hetero-galv-sim/`（热镀锌线 3 天，43 文件：DCS 432 行 + 剖面 144×(10 位) + 温度场 36×(5×4) + 图像流 36 帧 + 备注 7 条 + 实验室 36 行；真值=右气刀结渣→右缘镀层偏厚→清理恢复，`ground_truth.md` 单独存放）
- 运行：`workspace/diagnostic-runs/202610170143079_galv-sim`（web 端发起，engine=claude-opus-4-7，intent=stability-report）

## 验收标准与结果

| # | 验收项 | 结果 |
|---|---|---|
| AC1 | 前后端集成：服务启动、health/ready、cookie 认证、WS/SSE | ✅ health/ready 200；cookie 登录+`/me`；WS "Realtime Connected"；SSE 实时事件流正常；**CSRF 守卫实测拦截无 Origin 的 cookie POST** |
| AC2 | UI 实操链：登录→数据页→选意图→启动→实时观察 | ✅ 全链路真 UI 操作（上传经应用上传 API 43/43 入 `data/galv-sim`，UI 数据页可见）；启动后工作台流式显示工具调用（引擎初始化 claude-opus-4-7 / 29 tools） |
| AC3 | 产线报告正确性 | ✅ `line_report/stability_report.json` status=ok + HTML 81KB 级；**LSR 门禁 11/11 PASS**（schema/评分域/zero_llm/input sha256/html≥8KB/selfcheck/severity/no-autonomy）；**评分 61.6/C**；风险链命中真值「右气刀→横向均匀性→镀层克重」；SPC 42+50 剧集（Nelson R1/R2/R5/R6）；数字抽查（独立复算）逐项吻合 |
| AC4 | 多源异构链路 | ✅ 代理自主执行 E-1（1920 选主表评分 6.532）+ **E-1H 4 源全 featured**（profile 18 / map 11 / img 7 / txt 3 特征），门禁 exit 0；40 入评参数中 **33 个 HX 通道**；6 个时间不变量通道诚实剔除并披露 |
| AC5 | UI 查看报告 | ✅ Reports 页列出 `202610170143079 galv-sim · COMPLETED` → **Read Report 渲染完整中文报告**（结论先行/评分口径/异构明细表/下载与图表入口） |

## 数字抽查（独立复算 vs 注入真值）

| 通道 | 基线(h0-36) | 故障窗(h36-60) | 恢复后(h66+) | 报告 |
|---|---|---|---|---|
| GAL-COATING-GSM | 120.02 | **124.73** | 119.97 | 评分 61 + SPC 判定严重 |
| GAL-AIRKNIFE-R-PRES | 0.419 | **0.602** | 0.422 | **评分 35（全场最低带）** |
| GAL-YIELD | 98.51 | **97.02** | 98.47 | 评分 76 + 50 剧集 |
| GAL-AIRKNIFE-L-PRES（对照） | 0.419 | 0.419 | 0.417 | 评分 93（高稳定） |

## 观察记录（工程备注）

1. UI 上传文件选择器在当前 IAB 自动化下不可用 → 文件经应用上传 API 入仓（43/43，6 请求；CSRF 需带同源 Origin 头），其余全部真 UI 操作。
2. 重流式页面下 Playwright 角色定位器多次超 3s 预算 → 按技能文档的逃生口改用页面内受控点击；完成后 UI 曾停留过期帧，**刷新后正确显示 COMPLETED**（PAST TASKS 1）。
3. 专家分析类任务（stability report 等）在任务列表 VERDICT/SCORE 列为「—」（judge 体系仅对 deep-diagnosis 运行）；报告详情含完整渲染。
4. 运行时长约 12 分钟（含 E-1/E-1H 链与 LSR 全协议）；`run_manifest` 仅 `hetero_preprocess` 步完成（LSR 意图按指令不跑 9 段管线，属设计）。
