#!/usr/bin/env bash
set -euo pipefail

BASE="http://localhost:8765"
PASS=0
FAIL=0
ERROR=0
TOTAL=0

run_test() {
    local name="$1"
    local method="$2"
    local path="$3"
    local data="${4:-}"
    TOTAL=$((TOTAL + 1))

    if [ -n "$data" ]; then
        resp=$(curl -s -w "\n%{http_code}" -X "$method" "$BASE$path" \
            -H "Content-Type: application/json" \
            -d "$data" 2>&1) || { echo "  💥 $name → CONNECTION ERROR"; ERROR=$((ERROR + 1)); return; }
    else
        resp=$(curl -s -w "\n%{http_code}" "$BASE$path" 2>&1) || { echo "  💥 $name → CONNECTION ERROR"; ERROR=$((ERROR + 1)); return; }
    fi

    code=$(echo "$resp" | tail -1)
    body=$(echo "$resp" | sed '$d' | head -c 500)

    if [ "$code" = "200" ]; then
        echo "  ✅ $name → $code"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $name → $code"
        FAIL=$((FAIL + 1))
    fi
    echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print('    ', json.dumps({k: d[k] for k in list(d.keys())[:5]}, indent=2, default=str)[:300])" 2>/dev/null || true
    echo ""
}

echo "============================================================"
echo "RAG Retrieval Engine — Full API Test Suite"
echo "============================================================"

# ── GET Endpoints ──
echo ""
echo "--- GET Endpoints ---"
run_test "GET /health" "GET" "/health"
run_test "GET /stats" "GET" "/stats"
run_test "GET /runs" "GET" "/runs"
run_test "GET /index/files" "GET" "/index/files"

# ── POST /retrieve ──
echo "--- POST /retrieve ---"
RETRIEVE_RESP=$(curl -s -X POST "$BASE/retrieve" \
    -H "Content-Type: application/json" \
    -d '{"scenario":"CNC machining","target_columns":["surface_roughness_Ra_um"],"parameter_columns":["spindle_vibration_mm_s","spindle_temp_C"],"group_columns":["material"],"mode":"local_only","top_k":3}' 2>&1)
RETRIEVE_CODE=$(echo "$RETRIEVE_RESP" | python3 -c "import sys; print('200')" 2>/dev/null || echo "0")
RUN_ID=$(echo "$RETRIEVE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('retrieval_run_id',''))" 2>/dev/null || echo "")
TOTAL=$((TOTAL + 1))
if [ -n "$RUN_ID" ]; then
    echo "  ✅ POST /retrieve → 200 (run_id=$RUN_ID)"
    PASS=$((PASS + 1))
else
    echo "  ❌ POST /retrieve → FAILED (no run_id)"
    FAIL=$((FAIL + 1))
fi
echo ""

# ── POST /score ──
echo "--- POST /score ---"
if [ -n "$RUN_ID" ]; then
    SCORE_RESP=$(curl -s -X POST "$BASE/score" \
        -H "Content-Type: application/json" \
        -d "{\"retrieval_run_id\":\"$RUN_ID\",\"scenario\":\"CNC machining\",\"parameter_columns\":[\"spindle_vibration_mm_s\",\"spindle_temp_C\"],\"target_columns\":[\"surface_roughness_Ra_um\"]}" 2>&1)
    SCORE_CODE=$(echo "$SCORE_RESP" | python3 -c "import sys; print('200')" 2>/dev/null || echo "0")
    TOTAL=$((TOTAL + 1))
    if [ "$SCORE_CODE" = "200" ]; then
        echo "  ✅ POST /score → 200"
        PASS=$((PASS + 1))
    else
        echo "  ❌ POST /score → $SCORE_CODE"
        FAIL=$((FAIL + 1))
    fi
    echo ""
fi

# ── POST /inject ──
echo "--- POST /inject ---"
if [ -n "$RUN_ID" ]; then
    INJECT_RESP=$(curl -s -X POST "$BASE/inject" \
        -H "Content-Type: application/json" \
        -d "{\"retrieval_run_id\":\"$RUN_ID\",\"column_details\":[{\"name\":\"surface_roughness_Ra_um\",\"type\":\"number\"},{\"name\":\"spindle_vibration_mm_s\",\"type\":\"number\"},{\"name\":\"spindle_temp_C\",\"type\":\"number\"},{\"name\":\"material\",\"type\":\"string\"}]}" 2>&1)
    INJECT_CODE=$(echo "$INJECT_RESP" | python3 -c "import sys; print('200')" 2>/dev/null || echo "0")
    TOTAL=$((TOTAL + 1))
    if [ "$INJECT_CODE" = "200" ]; then
        echo "  ✅ POST /inject → 200"
        PASS=$((PASS + 1))
    else
        echo "  ❌ POST /inject → $INJECT_CODE"
        FAIL=$((FAIL + 1))
    fi
    echo ""
fi

# ── POST /pipeline/full ──
echo "--- POST /pipeline/full ---"
PIPELINE_RESP=$(curl -s -X POST "$BASE/pipeline/full" \
    -H "Content-Type: application/json" \
    -d '{"scenario":"CNC machining","target_columns":["surface_roughness_Ra_um"],"parameter_columns":["spindle_vibration_mm_s","spindle_temp_C"],"group_columns":["material"],"mode":"local_only","top_k":3}' 2>&1)
PIPELINE_RUN_ID=$(echo "$PIPELINE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin).get('run_id',''))" 2>/dev/null || echo "")
TOTAL=$((TOTAL + 1))
if [ -n "$PIPELINE_RUN_ID" ]; then
    echo "  ✅ POST /pipeline/full → 200 (run_id=$PIPELINE_RUN_ID)"
    PASS=$((PASS + 1))
else
    echo "  ❌ POST /pipeline/full → FAILED"
    FAIL=$((FAIL + 1))
fi
echo ""

# ── POST /query/enhance ──
echo "--- POST /query/enhance ---"
run_test "POST /query/enhance" "POST" "/query/enhance" \
    '{"scenario":"CNC machining","parameter_columns":["spindle_vibration_mm_s","spindle_temp_C"],"target_columns":["surface_roughness_Ra_um"],"group_columns":["material"]}'

# ── Run Management ──
echo "--- Run Management ---"
if [ -n "$RUN_ID" ]; then
    run_test "GET /runs/{id}" "GET" "/runs/$RUN_ID"
    run_test "GET /runs/{id}/result/retrieval_result" "GET" "/runs/$RUN_ID/result/retrieval_result"
fi
if [ -n "$PIPELINE_RUN_ID" ]; then
    run_test "GET /runs/{pipeline_id}" "GET" "/runs/$PIPELINE_RUN_ID"
    run_test "GET /runs/{pipeline_id}/result/ontology_draft" "GET" "/runs/$PIPELINE_RUN_ID/result/ontology_draft"
fi

# ── POST /web/inject ──
echo "--- POST /web/inject ---"
run_test "POST /web/inject" "POST" "/web/inject" \
    '{"chunks":[{"chunk_id":"web_test_001","content":"CNC spindle vibration is a key predictor of surface roughness degradation.","source":{"type":"web_general","url":"https://example.com"},"scenario_tags":["CNC machining"],"parameter_tags":["spindle_vibration_mm_s"],"mechanism_type":"causal_chain"}]}'

# ── POST /index (admin) ──
echo "--- POST /index (admin, no key required) ---"
run_test "POST /index" "POST" "/index" '{"rebuild": false}'

# ── Summary ──
echo ""
echo "============================================================"
echo "TEST SUMMARY"
echo "============================================================"
echo "Total: $TOTAL | ✅ Pass: $PASS | ❌ Fail: $FAIL | 💥 Error: $ERROR"
echo ""
if [ "$FAIL" -eq 0 ] && [ "$ERROR" -eq 0 ]; then
    echo "🎉 ALL TESTS PASSED!"
else
    echo "⚠️  Some tests failed or had errors."
fi
