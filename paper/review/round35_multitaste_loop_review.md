# Round 35 — 五品味循环审稿与修订记录（2026-09-23）

流程（$loop 动态循环，迭代在会话内同步执行，终止条件=五席全部通过）：
五席不同品味审稿（A 故事线主编 / B 统计方法学 / C 过程工业领域 / D 智能体系统 / E AEI 合规）
→ 裁决修订（22+3 项）→ 返稿复审 → 终态 **5/5 publishable=yes**（A/D/E Accept〔E 与 D 附已闭合校对条件〕、B Accept、C Accept〔附已闭合校对修正〕）。

## AEI 规则核查（席E，对照官方 Guide for Authors）

- **页数：官方无研究论文页数/字数上限**（sciencedirect.com 官方 Guide）；58 页 preprint（10pt 单栏）不违规，双栏定版约 45–50 页，席E 终审接受"内容完整优先"立场，撤回压缩清单。
- 硬性项全 PASS：摘要 ≤250 词（实测 245）、关键词 6 个（限 1–7）、Highlights 5 条（74–84 字符 ≤85）、声明五件套（CRediT/Competing/Funding/Data/AI 声明）、图 547–638dpi（组合图 ≥500dpi 达标）、表格无竖线无底纹、elsarticle-num 顺序编码、结构顺序合规。

## 五席首轮意见（全部 Minor，无 Major/Reject）与本轮落地

### 席A 故事线
- M2 §8 高潮错位 → §8 章首过渡段（"progressively harsher external checks"）；完整节序重排以折中方案替代（席A 复审认可）
- M3 案例研究错置 → **移至 §7.5**（与 §7.1 前向引用形成同节衔接）
- M4 §3 外围先行 → 框定句折中（复审认可）；M5 §9 无总起 → 四组边界总纲句；M1 摘要 → 压至 ~242 词
- m2 §5 承接句；m4 §6.1 按数据集分段；m5/m6 部分重复收敛

### 席B 统计
- M1 CI 二阶量 → Table 6 caption 声明 + top-k 行 "(design-aided)"
- M2 bare 臂审计链缺口 → **新增 released 产物 `results/benchmark/baselines_input_audit.json`**（12 个 baseline brief 的 SHA-256）+ A2 caption 引用；席B 复审独立复算哈希全部吻合
- M3 排名粒度 → family/branch 与 form-specific（1/5）并排；m2 45-run 构成 → 正文臂级分解 + suite manifest（复审可复算 12+12+7+7+7）；m3 LOTO first-order；m4 precision 3/4

### 席C 领域
- M1 IDV11/IDV14 判据一致性 → cap 政策统一论证段（复审认可）
- M2 historian 压缩破坏方差类签名 → §9 部署段新增警告（swinging-door/deadband + 导出要求 + 压缩参数指纹化 + unmapped-tag 首查）
- M3 现场配套实例化 → IDV4 具体 envelope（pre-onset band + XMV_10 上限 + 温度残差升级触发）
- m1 batch-93 案例定义欠完整从句；m3 空化排序措辞收敛；m4 IDV3 行分支标注

### 席D 智能体
- **M1 fig_pipeline 行 2 顺序画反（关键缺陷，此前四轮审稿未发现）→ 已镜像重排**（5a/5b ↓ Step 6 → 7 → 8/8.5 → 9，与架构图一致），席D 复审亲自读图确认
- M3 LLM-as-judge 偏差披露（zheng2023judging、panickssery2024selfpref 入引）+ 反事实改写为 selective-prediction 双操作点；m1 blackboard 认祖 + MAST（cemri2025mast）逐类映射
- M4 编排器上下文通道披露 + 重跑 mandates per-scenario orchestrating session；M5 双封顶结构性 remedy（machine-readable cap table）；m2 mutation-based gate 审计预注册

### 席E 合规
- 摘要 254→~242；Highlights 第 2 条缩短；其余 PASS 维持

## 复审轮新发现与校对期修正（已全部落地并验证）

1. 搬移案例研究时残留字面 `@n@n`（三席共同抓出）→ 已删，PDF 抽取验证 =0
2. IDV11 句 "≥95%" 与机器下限 0.90 未调和（席C）→ 改为 "machine floor: ≥0.90 … and the eliminations this corpus records are all at ≥95%"
3. §5 硬编码 "Section 4" → \ref{sec:method}（席A）

## 终态

58 页、0 错误、0 未定义引用、0 Overfull；摘要 ~242 词（≤250 合规）；highlights 全部 ≤85 字符。
五席终审：A Accept、B Accept、C Accept、D Accept、E Accept（均 publishable=yes，条件全部闭合）。
