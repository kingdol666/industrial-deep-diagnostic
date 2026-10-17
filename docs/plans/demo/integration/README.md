# IDD ⇄ AgentWorkShop integration probe

This directory holds the evidence for the API/plugin end-to-end test described in
`docs/plans/agentworkshop-integration-audit-2026-10-17.md`.

## Files

| File | What it is |
|---|---|
| `plugin_probe.mjs` | Loads the **builtin** diag-bridge plugin and the project idd-closedloop-bridge plugin with a minimal OMP-like `ctx`, then calls `diag_run`/`diag_status` against a live IDD backend and calls `sentinel_screen`. |
| `plugin_probe.json` | The probe result: builtin plugin loaded, real `diag_run` task, stored question/intent, closedloop 404. |
| `evidence/api_contract.json` | Auth/error-code/task-lifecycle checks (401/400/404/200, mock task completed). |
| `evidence/api_mock_result.json` | External API result for the mock DOE task (score/verdict/report path/artifact shape). |
| `evidence/omp_agent_heat_treat_report.html` | Report from the real OMP agent run (analysis artifacts; deterministic report/gate finalize on the same run dir). |
| `evidence/omp_recommendations.json` | The agent-produced recommendations (joint setpoint, windows, units). |
| `evidence/omp_doe_conclusion.json` | The agent-produced evidence grade and key findings. |

## Reproduce

```bash
# 1. start one IDD backend (single backend per DB!)
cd app/backend && PORT=3211 AUTH_ENABLED=1 node src/index.mjs

# 2. register/login and mint an idd_ token (see the audit report §1)
#    save it to workspace/aws-capture-e2e/token.txt

# 3. run the plugin probe (uses workspace/doe-generality/heat_treat_ccd input)
node docs/plans/demo/integration/plugin_probe.mjs \
  --base http://127.0.0.1:3211 \
  --token-file workspace/aws-capture-e2e/token.txt

# 4. the real OMP run was launched through the external API:
#    POST /api/external/v1/analyze
#    {folderPath:"workspace/e2e-api/heat_treat_flat", analysisIntent:"doe-analysis",
#     harness:"omp", ontologyMode:"auto", ontologyScene:"heat-treat-furnace3-4140"}
```

## Findings visible in the files

- `plugin_probe.json.checks.stored_intent = "doe-analysis"` but
  `stored_question = "offline-data 产线该时窗数据深度根因诊断"` → the bridge's
  default-question override (P0).
- `sentinel_screen_text = "sentinel_screen 失败: 404"` → the closedloop bridge's
  `/api/sentinel/*` family is retired (P0).
- The project `diag-bridge` copy cannot be imported: `host/plugin.mjs` imports
  `./exports.mjs`, which exists only in the builtin copy (P0).
- The OMP run produced a complete analysis (grade A, joint 859.384/44.787/0.5008) but the
  parent agent stalled waiting on its `DoeAnalysis` subagent; the report/gate in
  `evidence/` were produced deterministically on the same run dir (25/25 gate).
