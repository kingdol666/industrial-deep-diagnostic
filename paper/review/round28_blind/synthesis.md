# 盲审 Round 1（2026-09-20）— 三席全新 subagent

## R1-methodology — publishable: NO — Major Revision — confidence 5
总评：评估纪律显著高于同类文献；多重读数分层、循环性自声明、Wilson 区间逐项核算正确、bare-LLM 9/9 不利反证如实。抽查 4/9、9/9、45/45、seed 1003818694、153 指纹、12/12 执行证明、forced-commitment 期望 ≈6.1/9 均与产物一致。唯一实质缺口：标识符召回混淆补救仅承诺未执行。

- [MAJOR] 摘要/表4/§7/结论：4 个 resolved 判定全部处于自设 recall-possible tier（联合下界 0/9），neutralised 重跑未执行；表4 Top-1 行无 recall 警示。→ 最低限度：表4+摘要并列标注 tier。
- [MINOR] R3 控制场景误触发后逐例重分类为 check mis-specification——评分器内一次事后人工判定；建议预注册跳过规则。
- [MINOR] film-line 部署产物匿名且未发布，不可核验；建议标注未审计示例。
- [MINOR] 摘要 ~450 词单段，多层读数堆叠；建议分层。

```json
{"reviewer":"R1-methodology","publishable":"no","recommendation":"Major Revision","blocking":[{"id":"B1","issue":"标识符召回混淆未实际消除；须执行重跑或至少表4/摘要并列标注 tier"}],"confidence":5}
```

## R2-domain — publishable: YES — Minor Revision — confidence 4
总评：场景构造与检测限论述准确；FE Table 1 转录逐行核对相符（含 8/11 自相矛盾的忠实披露）；Register B 严格隔离；IDV4 能量平衡、IDV7 算术、IDV14 黏滞签名均成立。主要不足：IndPenSim 真值溯源与少量经典文献缺位。

- [MAJOR] IndPenSim "its documented process-deviation batch is 93" 措辞 + 描述溯源至自建 case definition 而非一手文档；官方口径为 91–100 批次含偏差。→ 引官方 per-batch 偏差表并修正排他性措辞。
- [MINOR] SKAB 溯源措辞：机制命名出自官方实验说明而非 anomaly 标签列；建议改述+补引仓库。
- [MINOR] 建议补根因-传播经典（Yoon & MacGregor 2001；Alcalá & Qin 2009）；黏滞可补 Hágglund 1995。
- [MINOR] 图6/表A1 "T²-only screen" 宜注明 FE 检测统计量出处。

```json
{"reviewer":"R2-domain","publishable":"yes","recommendation":"Minor Revision","blocking":[{"id":"B1","issue":"IndPenSim batch-93 ground truth 须溯源一手文档并修正唯一偏差批次表述"}],"confidence":4}
```

## R3-rigor — publishable: YES — Minor Revision — confidence 4
最强反驳：摘要称五个 capped 案例"数据不可分"，但同一 blind digest 喂裸模型严格命中 9/9——分离失败是协议消除阈值的政策产物而非数据极限；且 cap 内排名在 §6.3"无真值含义"、§6.5 却用作抗召回证据，语义随论点切换。

- [MAJOR-1] 摘要+§6.2 "the data cannot separate" 与消融矛盾 → 全文统一为"未达协议量化消除阈值"口径。
- [MAJOR-2] 排名语义机会主义切换 → 明确定义（证据权重、非校准置信、无真值含义）并重写抗召回论证。
- [MINOR-3] 贡献2 "none of the determined verdicts is wrong" 缺 family-level 限定（identity-strict 下 batch-93 即错）。
- [MINOR-4] "does not fabricate faults under an honest brief" 由 n=1 概括略强；降低强度并明示 n=1。
- 观察（不计缺陷）：top-k 自称 instrument reading；标识召回通道与重跑承诺；rubric 循环性；trustworthy 限定定义与信任边界表；retest n=1 自认；45/45 仅确定性臂；双 cap set gap 自认；script-only 替代解释已标注为假设。

```json
{"reviewer":"R3-rigor","publishable":"yes","recommendation":"Minor Revision","blocking":[{"id":"B1","issue":"'数据不可分'措辞与消融矛盾，统一为协议阈值口径"},{"id":"B2","issue":"cap 内排名语义需统一定义并重写依赖论证"}],"confidence":4}
```

## 编辑合成
共识未达（R1 no）。4 个 blocking 全部为文本级可修：已按各席"最低限度"路径执行（见 blind_loop_state.json revisions_applied）。R1 的"执行 neutralised 重跑"完整路径需 ≈16h agent time，保留为已承诺的 post-revision 执行项；本轮采用其明示的最低替代（tier 并列标注）。
