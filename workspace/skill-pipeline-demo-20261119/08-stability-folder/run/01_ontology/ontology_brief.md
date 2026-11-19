# 本体简报 · packaging_folder_profile（stability）

- 契约版本：1.0（profile=stability）　数据阶段：`collected`
- 上下文指纹 context_fp：`sha256:5938a212cd72d69a4a6cd3d95501bd0c773a4943bda1032d1fcc266a272dffef`
- 本体版本：1　本体哈希：`sha256:1c97d8c542f8cfedfd71e508a5135de0cfa6130982c8f51428c1f90db19c1c63`

## 1. 场景理解

- 场景：offline-data_diag（工艺类型：挤出/注塑式热工艺产线（PROTO3-B3 文档驱动接入线）时序数据稳定性评估）
- 生产目标：评估 2026-11-01 11:03 ~ 12:03 窗口内该产线 7 个标量节点的运行稳定性，给出评分与分级、证据链与中文落地报告　分析目的：['评估 2026-11-01 11:03 ~ 12:03 窗口内该产线 7 个标量节点的运行稳定性，给出评分与分级、证据链与中文落地报告']

## 2. 列角色与单位

| 列 | 角色语义 | 本体角色 | 单位 | 单位来源 | knowledge_source | 置信 |
|---|---|---|---|---|---|---|

## 3. 规格与参考区间

### 3.1 用户/上下文声明规格（可作判定边界）

- （无用户声明规格——Cpk 将不计算，不做规格罚分）

### 3.2 词典参考区间（非规格）

- （无词典参考带）

## 4. 混杂与局限

- 声明先验本体：全部字段来自 report_context 声明、数据表头探测或物理词典唯一命中，不含任何实测行为（observed_data_behavior=NOT_APPLICABLE / behavior_match=UNVERIFIED）
- 词典纪律：parameter_to_physics.json 的 typical_ranges 是参考区间（非规格），只展示在本体 watch.reference_bands 与简报中，永不写入 normal_range/spec/Cpk
- 关系边留空：无方向声明不造因果边（relationships=[]），相关性发现的机理校验将按 unknown 处理并打 [MECHANISM_UNKNOWN]
- 数据表头不可探测（缺失或非 CSV/TSV）：先验仅来自上下文声明

## 5. 列映射覆盖（0 静默）

- matched: 0　inferred: 0　unmatched: 0
- coverage.ratio = 1.0（1.0 ⟺ 无静默列：每列都带状态与原因出现；unmatched 是已披露的缺失，不是静默）
- matched_ratio = 1.0（matched+inferred 占比；unmatched 越多，语义覆盖越弱）

## 6. 未解决项

- （无）

## 7. 来源（provenance）

- build_mode=prior_knowledge　engine=industrial-ontology-builder　store=v1（profile=stability）
- rag_used=False　web_used=False　physics_prior_used=True（确定性路径，未调用 RAG/网络）
- source_note：reused store asset offline-data_diag/stability/v1/ontology.json　lookup=exact　build_seconds=0.224

> 本简报由确定性脚本生成（零 RAG、零网络）。分析器在 mode≠off 时要求本文件存在（门禁 `ONTOLOGY_BRIEF_REQUIRED`）；agent 阅读本文件后再进入统计解读。
