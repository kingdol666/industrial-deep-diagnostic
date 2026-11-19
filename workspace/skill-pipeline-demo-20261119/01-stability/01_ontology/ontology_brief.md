# 本体简报 · packaging_line_oven（stability）

- 契约版本：1.0（profile=stability）　数据阶段：`collected`
- 上下文指纹 context_fp：`sha256:51b8cd3a70dd455d564ae26d0f0589d0da193c5006064288c11e06eece54ee37`
- 本体版本：2　本体哈希：`sha256:ee81bd8f7aa5d30a0bc3f5c165d6fa966cf57ec95731e11db1ff154d1244e47b`

## 1. 场景理解

- 场景：packaging_line_oven（工艺类型：包装产线烘箱段 8 小时 DCS 导出运行稳定性评估）
- 生产目标：评估包装线烘箱段本班次 8 小时运行稳定性并识别主要波动来源　分析目的：['评估包装线烘箱段本班次 8 小时运行稳定性并识别主要波动来源']

## 2. 列角色与单位

| 列 | 角色语义 | 本体角色 | 单位 | 单位来源 | knowledge_source | 置信 |
|---|---|---|---|---|---|---|
| `scrap_rate_pct` | inspection | target | % | declared | user_provided | KNOWN |

## 3. 规格与参考区间

### 3.1 用户/上下文声明规格（可作判定边界）

- （无用户声明规格——Cpk 将不计算，不做规格罚分）

### 3.2 词典参考区间（非规格）

- （无词典参考带）

## 4. 混杂与局限

- 声明先验本体：全部字段来自 report_context 声明、数据表头探测或物理词典唯一命中，不含任何实测行为（observed_data_behavior=NOT_APPLICABLE / behavior_match=UNVERIFIED）
- 词典纪律：parameter_to_physics.json 的 typical_ranges 是参考区间（非规格），只展示在本体 watch.reference_bands 与简报中，永不写入 normal_range/spec/Cpk
- 关系边留空：无方向声明不造因果边（relationships=[]），相关性发现的机理校验将按 unknown 处理并打 [MECHANISM_UNKNOWN]
- 1 列单位未声明（unit undeclared）：timestamp
- 4 列未获得语义映射（unmatched，原因见 column_mapping）——这些列仍按数值参数参与启发式评估，但报告必须如实标注其单位/语义缺失
- 数据表头不可探测（缺失或非 CSV/TSV）：先验仅来自上下文声明

## 5. 列映射覆盖（0 静默）

- matched: 1　inferred: 0　unmatched: 0
- coverage.ratio = 1.0（1.0 ⟺ 无静默列：每列都带状态与原因出现；unmatched 是已披露的缺失，不是静默）
- matched_ratio = 1.0（matched+inferred 占比；unmatched 越多，语义覆盖越弱）

## 6. 未解决项

- （无）

## 7. 来源（provenance）

- build_mode=extend　engine=industrial-ontology-builder　store=v2（profile=stability）
- rag_used=False　web_used=False　physics_prior_used=True（确定性路径，未调用 RAG/网络）
- source_note：extended store asset packaging_line_oven/stability/v1/ontology.json　lookup=scene_only　build_seconds=0.199

> 本简报由确定性脚本生成（零 RAG、零网络）。分析器在 mode≠off 时要求本文件存在（门禁 `ONTOLOGY_BRIEF_REQUIRED`）；agent 阅读本文件后再进入统计解读。
