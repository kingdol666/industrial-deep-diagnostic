# Example Invocations

## Example 1: Standalone build

```text
/diagnostic-html-visualizer build run_dir="/abs/path/to/workspace/diagnostic-runs/202606151602359_bopet_scratch_lekai"
```

## Example 2: Specify audience and output

```text
/diagnostic-html-visualizer build run_dir="/abs/path/to/workspace/diagnostic-runs/202606151602359_bopet_scratch_lekai" output_html="/abs/path/to/workspace/diagnostic-runs/202606151602359_bopet_scratch_lekai/executive-report.html" audience="manager" visual_mode="executive"
```

## Example 3: Called after diagnosis pipeline

```text
Skill({
  skill: "diagnostic-html-visualizer",
  args: "build run_dir='/abs/path/to/workspace/diagnostic-runs/202606151602359_bopet_scratch_lekai' output_html='/abs/path/to/workspace/diagnostic-runs/202606151602359_bopet_scratch_lekai/diagnostic-report.html'"
})
```

