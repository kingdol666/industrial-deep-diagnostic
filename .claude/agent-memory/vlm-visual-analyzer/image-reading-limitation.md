---
name: image-reading-limitation
description: Haiku 4.5 cannot directly read PNG images; must use metadata_backed_inference mode
metadata:
  type: feedback
---

When running as vlm-visual-analyzer on the Haiku 4.5 model, the model returns "[Unsupported Image]" for all PNG Read attempts. This means direct_image_reading is not possible.

**Why:** The Haiku 4.5 model does not support multimodal image understanding through the Read tool. All figures return unsupported, making visual inspection impossible.

**How to apply:** Always set `observation_mode` to `"metadata_backed_inference"` rather than `"direct_image_reading"`. Build observations from:
- plot_manifest.json figure descriptions and titles
- Statistical context files (feature_summary.json, validate_report.json, anomaly_report.json)
- ontology.json physical meanings and expected behaviors
- Figure filenames, which encode the parameters and chart types

Document each figure's `read_status` as `READ_FAILED` with `read_failure_reason` explaining the model limitation. Set `figure_inputs_read_successfully` to `[]` (empty array). The output remains valid and useful — the schema explicitly supports this mode.
