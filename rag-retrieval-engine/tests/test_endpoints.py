#!/usr/bin/env python3
"""Quick smoke test for the RAG engine endpoints."""

import json, sys, urllib.request

BASE = "http://localhost:8765"

def req(method, path, data=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    r = urllib.request.Request(url, data=body, method=method,
        headers={"Content-Type": "application/json"} if data else {})
    with urllib.request.urlopen(r) as resp:
        return json.loads(resp.read())

def test(label, fn):
    try:
        fn()
        print(f"  ✅ {label}")
    except Exception as e:
        print(f"  ❌ {label}: {e}")

print("RAG Engine Smoke Test")
print("====================")

# 1. Health
test("GET /health", lambda: req("GET", "/health"))

# 2. Index (don't crash)
test("POST /index", lambda: req("POST", "/index", {"rebuild": False}))

# 3. Retrieve
result = None
def do_retrieve():
    global result
    result = req("POST", "/retrieve", {
        "scenario": "CNC machining",
        "target_columns": ["surface_roughness_Ra_um"],
        "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C"],
        "group_columns": ["material"],
        "mode": "local_only",
        "top_k": 3,
    })
test("POST /retrieve", do_retrieve)

# 4. Score
if result and result.get("retrieval_run_id"):
    run_id = result["retrieval_run_id"]
    def do_score():
        req("POST", "/score", {
            "retrieval_run_id": run_id,
            "scenario": "CNC machining",
            "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C"],
            "target_columns": ["surface_roughness_Ra_um"],
        })
    test("POST /score", do_score)

    # 5. Inject
    def do_inject():
        req("POST", "/inject", {
            "retrieval_run_id": run_id,
            "column_details": [
                {"name": "spindle_vibration_mm_s", "type": "number"},
                {"name": "spindle_temp_C", "type": "number"},
                {"name": "surface_roughness_Ra_um", "type": "number"},
                {"name": "material", "type": "string"},
            ],
            "mode": "auto",
        })
    test("POST /inject", do_inject)

# 6. Runs
test("GET /runs", lambda: req("GET", "/runs"))

# 7. Stats
test("GET /stats", lambda: req("GET", "/stats"))

print("\nAll smoke tests completed.")
