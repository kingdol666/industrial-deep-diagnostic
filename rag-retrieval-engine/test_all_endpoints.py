#!/usr/bin/env python3
"""Full API test suite for RAG Retrieval Engine."""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import httpx

BASE = "http://localhost:8764"
# Bypass system proxy for localhost testing
client = httpx.Client(base_url=BASE, timeout=30, proxy=None)
results = []

def test(name, method, path, **kwargs):
    try:
        r = getattr(client, method)(path, **kwargs)
        ok = r.status_code == 200
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else r.text[:500]
        results.append({"test": name, "status": "PASS" if ok else "FAIL", "code": r.status_code, "detail": str(body)[:300]})
        print(f"  {'✅' if ok else '❌'} {name} → {r.status_code}")
        return body if ok else None
    except Exception as e:
        results.append({"test": name, "status": "ERROR", "detail": str(e)})
        print(f"  ❌ {name} → ERROR: {e}")
        return None

print("=" * 60)
print("RAG Retrieval Engine — Full API Test Suite")
print("=" * 60)

# 1. Health
print("\n--- GET Endpoints ---")
test("GET /health", "get", "/health")
test("GET /stats", "get", "/stats")
test("GET /runs", "get", "/runs")
test("GET /index/files", "get", "/index/files")

# 2. Retrieve (core)
print("\n--- POST /retrieve ---")
retrieve_data = test("POST /retrieve", "post", "/retrieve", json={
    "scenario": "CNC machining",
    "target_columns": ["surface_roughness_Ra_um"],
    "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C"],
    "group_columns": ["material"],
    "mode": "local_only",
    "top_k": 3
})
run_id = None
if retrieve_data and isinstance(retrieve_data, dict):
    run_id = retrieve_data.get("retrieval_run_id")
    print(f"    run_id = {run_id}")

# 3. Score
if run_id:
    print("\n--- POST /score ---")
    test("POST /score", "post", "/score", json={
        "retrieval_run_id": run_id,
        "scenario": "CNC machining",
        "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C"],
        "target_columns": ["surface_roughness_Ra_um"],
    })

# 4. Inject
if run_id:
    print("\n--- POST /inject ---")
    test("POST /inject", "post", "/inject", json={
        "retrieval_run_id": run_id,
        "column_details": [
            {"name": "surface_roughness_Ra_um", "type": "number"},
            {"name": "spindle_vibration_mm_s", "type": "number"},
            {"name": "spindle_temp_C", "type": "number"},
            {"name": "material", "type": "string"},
        ],
    })

# 5. Full pipeline
print("\n--- POST /pipeline/full ---")
pipeline_data = test("POST /pipeline/full", "post", "/pipeline/full", json={
    "scenario": "CNC machining",
    "target_columns": ["surface_roughness_Ra_um"],
    "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C"],
    "group_columns": ["material"],
    "mode": "local_only",
    "top_k": 3
})
pipeline_run_id = None
if pipeline_data and isinstance(pipeline_data, dict):
    pipeline_run_id = pipeline_data.get("run_id")
    print(f"    pipeline_run_id = {pipeline_run_id}")

# 6. Query enhance
print("\n--- POST /query/enhance ---")
test("POST /query/enhance", "post", "/query/enhance", json={
    "scenario": "CNC machining",
    "parameter_columns": ["spindle_vibration_mm_s", "spindle_temp_C"],
    "target_columns": ["surface_roughness_Ra_um"],
    "group_columns": ["material"],
})

# 7. Run management
print("\n--- GET /runs/{id} ---")
if run_id:
    test(f"GET /runs/{run_id}", "get", f"/runs/{run_id}")
    test(f"GET /runs/{run_id}/result/retrieval_result", "get", f"/runs/{run_id}/result/retrieval_result")

if pipeline_run_id:
    test(f"GET /runs/{pipeline_run_id}", "get", f"/runs/{pipeline_run_id}")
    test(f"GET /runs/{pipeline_run_id}/result/ontology_draft", "get", f"/runs/{pipeline_run_id}/result/ontology_draft")

# 8. Web inject
print("\n--- POST /web/inject ---")
test("POST /web/inject", "post", "/web/inject", json={
    "chunks": [
        {
            "chunk_id": "web_test_001",
            "content": "CNC spindle vibration is a key predictor of surface roughness degradation. Studies show vibration > 0.5 mm/s correlates with Ra > 1.6 μm.",
            "source": {"type": "web_general", "url": "https://example.com"},
            "scenario_tags": ["CNC machining"],
            "parameter_tags": ["spindle_vibration_mm_s", "surface_roughness_Ra_um"],
            "mechanism_type": "causal_chain",
        }
    ]
})

# 9. Admin endpoints (no API key configured, should work)
print("\n--- POST /index (admin, no key) ---")
test("POST /index", "post", "/index", json={"rebuild": False})

# Summary
print("\n" + "=" * 60)
print("TEST SUMMARY")
print("=" * 60)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
errors = sum(1 for r in results if r["status"] == "ERROR")
total = len(results)
print(f"Total: {total} | ✅ Pass: {passed} | ❌ Fail: {failed} | 💥 Error: {errors}")
print()
for r in results:
    icon = "✅" if r["status"] == "PASS" else ("❌" if r["status"] == "FAIL" else "💥")
    print(f"  {icon} {r['test']} → {r['status']}")

client.close()
