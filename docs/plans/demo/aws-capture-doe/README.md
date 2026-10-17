# AgentWorkShop capture → anomaly / fluctuation / DOE

A reproducible field trial over one simulated BOPET 12 µm line. The data is organized exactly
like AgentWorkShop DAQ exports (`manifest.json` + `nodes/<id>.csv` per window), so the test
exercises the real platform → IDD ingest path, not a hand-written CSV.

## Run

```bash
# full run: regenerate the capture, rebuild everything, copy evidence
python docs/plans/demo/aws-capture-doe/run_demo.py --fresh

# keep the capture/store, rerun the analyses
python docs/plans/demo/aws-capture-doe/run_demo.py

# skip the external E-1H skill (the capture's prepared features are used)
python docs/plans/demo/aws-capture-doe/run_demo.py --skip-hetero
```

Exit 0 = every assertion passed. The last run: **100/100**.

## What it proves

| Stage | What runs | Key result |
|---|---|---|
| E-1H | 63-point TD profiles + 22 operator notes → scalar features | edge feature r=0.976, profile mean r=0.999997 vs planted truth |
| DOE | `aws_capture` → `doe_context_adapter` → `doe_ontology_prepare` (build → reuse) → `analysis_plan` → `analyze.py all` → G1-G11 | effects within 5% of truth; joint setpoint 200 °C / 317.5 m/min / 3.075; grade A; gate 25/25 |
| quick-screen | sentinel baseline (with DOE windows) → watch → gate | Z4 drift 0.896 vs 0.9 °C/h, current 204.7 > window 203 → critical; 6/6 gate |
| stability | stability analyzer (ontology + sentinel baseline + DOE windows) → HTML → gate | 53.9 / C, 20 findings, 3 DOE windows loaded; 11/11 gate |
| retrieval | `results_index.json` + 7 keyword queries | 12 entries; 7/7 hit; backend manifest 15 artifacts |
| routing | `routing_check.mjs` (IDD directives × AgentWorkShop catalog) | 20/20 IDD; AWS skills 5/5; P0 platform gap disclosed |

Search the committed results without rerunning anything:

```bash
python docs/plans/demo/aws-capture-doe/query_results.py 厚度
python docs/plans/demo/aws-capture-doe/query_results.py 漂移 --json
python docs/plans/demo/aws-capture-doe/query_results.py 联合设定点
```

## Layout

```
generate_capture.py     seeded generator (history/line/campaign/hetero + truth)
run_demo.py             driver + assertions + evidence copy
routing_check.mjs       scenario → skill routing check
capture/
  history/              stable 6 h export (sentinel baseline)
  line/                 6 h export with the planted anomaly
  campaign/
    mapping.json        platform semantics (factors/responses/constraints/platform_ref)
    trial_design.csv    22 executions (face-centred CCD, 3 blocks)
    qc_measurements.csv lab responses
    hetero_features.csv E-1H features joined by run_id (prepared)
    runs/<run_id>/      one DAQ export per execution
  hetero/               profiles.csv, notes.csv, anchor.csv (E-1H inputs)
scenario_truth.json     planted surface, stationary point, anomaly times (acceptance only)
evidence/               compact outputs: DOE/stability HTML, JSON contracts, index, routing
```

The full run directory is regenerated under `workspace/aws-capture-e2e/` (not committed):
`doe/`, `sentinel/`, `stability/`, `hetero/`, `_store/`.

## Notes

- `current_setpoint` is the pre-trial recipe (196 °C / 330 m/min / 3.1), a corner that runs
  44.79 µm — intentionally off-spec so the recommendation has a measurable effect.
- The DOE joint point is a multi-response compromise, not the thickness-only stationary point
  (201.56 °C / 315.28 m/min / 2.947). The report shows both; execution uses the joint point.
- `next_design` is `none` here because the design has no lack of fit, aliasing or randomization
  gap. The rules emit runs when one of those fires; `recommendations.confirmations` is the other
  carrier.
- E-1H is optional in this demo: the generator writes a fallback `hetero_features.csv`; the driver
  uses the real E-1H skill when it is available and compares its features with the planted signal.
- Do **not** give `scenario_truth.json` to a diagnosing agent — it is acceptance ground truth.
