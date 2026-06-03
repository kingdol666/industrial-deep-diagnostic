---
name: data-processor-string-type-gotcha
description: cleaned_data.json from dp_toolkit.py preprocess outputs string-typed numeric values, causing downstream Python scripts to fail
metadata:
  type: feedback
---

dp_toolkit.py preprocess writes cleaned_data.csv, and when converted to cleaned_data.json via convert.mjs, all numeric values remain as strings. This causes physics_check.py to crash with `TypeError: unsupported operand type(s) for -: 'str' and 'str'`.

**Why:** The CSV→JSON conversion does not automatically parse numeric strings. The JSON output preserves the CSV cell types as-is.

**How to apply:** After generating cleaned_data.json, always run a type-fix step that converts known numeric columns to float/int. Or load cleaned_data.csv directly with csv.DictReader and convert inline (as the expert_analysis.py script does). The type-fix approach: load JSON, iterate rows, try `float(v)` on known numeric columns, write back.
