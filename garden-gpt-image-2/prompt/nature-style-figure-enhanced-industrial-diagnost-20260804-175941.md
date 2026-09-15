# Nature-Style Figure — Enhanced Industrial Diagnostic Analysis Pipeline (E0–E8)

## Final Prompt

```json
{
  "type": "工程类技术路线图 / engineering research roadmap figure, Nature journal style",
  "goal": "Generate a publication-quality figure for a Nature-style engineering paper Methods section, depicting the ENHANCED industrial diagnostic analysis pipeline (E0–E8) built on top of a baseline root-cause diagnosis. Minimal, white background, geometrically precise, grayscale-printable.",
  "canvas": {
    "aspect_ratio": "2.2:1 (wide, fits double-column journal width)",
    "background": "pure white #FFFFFF",
    "padding": "60px around all content",
    "render": "vector-clean, anti-aliased, sharp text, no gradients, no drop shadows, no 3D"
  },
  "layout": {
    "mode": "left / center / right three-panel roadmap",
    "width_ratio": "2 : 5 : 2",
    "panel_separators": "thin vertical divider lines between panels, light gray #E2E8F0"
  },
  "left_panel": {
    "header": "BASELINE DIAGNOSTICS (qualitative, uppercase 9pt letter-spaced)",
    "content": [
      "Process ontology construction",
      "Statistical validation & steady-state filtering",
      "Competing-hypothesis root-cause diagnosis",
      "Evidence & confidence scoring",
      "Quality-gate review (Judge)"
    ],
    "style": "stacked thin-outline rounded rectangles, no fill or very light #F1F5F9 fill, dark slate text #1B2A4A, each with a small 1-line descriptor"
  },
  "center_panel": {
    "header": "ENHANCED ANALYSIS PIPELINE",
    "rows": [
      {
        "group": "GATE",
        "blocks": ["E0 Readiness & Data-Integrity Check", "SHA-256 fingerprint verification"]
      },
      {
        "group": "FEATURE LAYER",
        "blocks": ["E1 Analysis-Coverage Matrix", "E2 Physical Derived Features"]
      },
      {
        "group": "RELATION LAYER",
        "blocks": ["E3 Conditional / Regime Analysis", "E3.5 Causal Association Graph"]
      },
      {
        "group": "PHYSICS LAYER",
        "blocks": ["E5 Physics Bridge — mechanism verification"]
      },
      {
        "group": "FUSION & DELIVERY",
        "blocks": ["E6 Knowledge Fusion", "E7a–E7c Report · HTML · Review", "E8 Finalization & Status"]
      }
    ],
    "style": "five horizontal rows, each row is one pipeline stage group; blocks are identical-size rounded rectangles (corner ~4px), 1.4px border #334155, fill alternates between #F1F5F9 and #E8EEF7 only; thin dark arrows #334155 connect blocks left→right within each row; a vertical feeder arrow on the left merges all rows into E6–E8; group labels on the far left in italic gray 8pt"
  },
  "right_panel": {
    "header": "ENHANCED KNOWLEDGE OUTPUTS",
    "content": [
      "Mechanism chains with verification status",
      "Evidence-gap ledger",
      "Conditional trade-off matrix",
      "Operability & leverage assessment",
      "Enhanced HTML / Markdown artifacts"
    ],
    "style": "same block style as left panel; last block slightly emphasized with a single low-saturation amber #C8963E outline (accent only, no fill)"
  },
  "typography": {
    "font": "Helvetica / Arial / Inter sans-serif ONLY, no serif, no handwriting",
    "headers": "8–9pt bold, letter-spaced uppercase, dark slate #1B2A4A",
    "block_labels": "9–10pt regular, #334155",
    "descriptors": "7.5–8pt italic, gray #64748B",
    "title_caption": "bottom-center, italic 8pt: 'Figure S1. Enhanced diagnostic analysis pipeline (E0–E8). The baseline diagnostic outputs feed an integrity-gated enhancement pipeline that produces physics-verified knowledge artifacts.'"
  },
  "constraints": {
    "must_keep": [
      "pure white background, no gradient, no shadow, no 3D",
      "maximum 4 colors total: white, slate blue #1B2A4A/#334155, light gray #F1F5F9/#E2E8F0, one amber accent #C8963E (right panel only)",
      "all blocks in the center panel identical size and strictly aligned",
      "readable in grayscale print",
      "no quantitative data, no equations, no fabricated numbers — qualitative stage labels only",
      "no emoji, no cartoon icons, no photo textures",
      "all labels in English"
    ],
    "avoid": [
      "gradients, gloss, glassmorphism, drop shadows",
      "neon or saturated colors",
      "commercial flowchart look (office diagrams), no clip-art arrows",
      "mixing serif with sans-serif"
    ]
  }
}
```

## 画面内容说明（供参考，不进入 prompt）

- 左侧 = 基线诊断产物（本体构建 → 统计验证 → 竞争假设诊断 → 证据/置信评分 → Judge 质量门）
- 中间 = 增强管线 E0–E8 五层分组（门控 → 特征层 → 关系层 → 物理层 → 融合交付）
- 右侧 = 增强知识输出（机理链 / 证据缺口 / 权衡矩阵 / 可操作性 / 交付产物）
