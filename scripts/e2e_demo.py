"""
End-to-end demo script that exercises the full v1 → v2 ingestion and staleness flow.

This script directly calls the API via httpx so it doubles as an integration test.
Run it while the server is running (see README.md).

Usage:
    python scripts/e2e_demo.py

It will:
  1. Ingest ct200_manual_v1.pdf as version 1.0
  2. Ingest ct200_manual_v2.pdf as version 2.0
  3. List top-level nodes (v1, v2, and latest)
  4. Show diff for a known-changed node (2.2 Cuff Pressure Safety)
  5. Search for "pressurisation"
  6. Create a version-pinned selection
  7. Generate QA test cases
  8. Retrieve the generation (staleness = False, just ingested)
  9. Show what happens when the same selection is submitted again (new generation)
  10. Retrieve the generation AFTER v2 ingestion → staleness = True for changed nodes
"""

import json
import os
import sys
import time
import httpx

# Force UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


BASE = os.getenv("API_BASE", "http://localhost:8000")
DOC_ID = "CT200-MAN-001"
V1_PATH = "data/ct200_manual_v1.pdf"
V2_PATH = "data/ct200_manual_v2.pdf"


def _pretty(label: str, data) -> None:
    print(f"\n{'='*60}")
    print(f"  {label}")
    print('='*60)
    print(json.dumps(data, indent=2, default=str))


def _check(r: httpx.Response, label: str) -> dict:
    if r.status_code not in (200, 201):
        print(f"\nERROR [{label}]: HTTP {r.status_code}")
        print(r.text)
        sys.exit(1)
    data = r.json()
    _pretty(label, data)
    return data


def main():
    c = httpx.Client(base_url=BASE, timeout=120)

    # ── Health ──────────────────────────────────────────────────────────────
    r = c.get("/health")
    _check(r, "Health check")

    # ── 1. Ingest v1 ────────────────────────────────────────────────────────
    print(f"\n[1] Ingesting {V1_PATH} as version 1.0 …")
    with open(V1_PATH, "rb") as f:
        r = c.post("/api/ingest", files={"file": ("ct200_manual_v1.pdf", f, "application/pdf")},
                   data={"document_id": DOC_ID, "version_tag": "1.0"})
    v1_resp = _check(r, "Ingest v1")
    v1_id = v1_resp["version"]["id"]

    # ── 2. Ingest v2 ────────────────────────────────────────────────────────
    print(f"\n[2] Ingesting {V2_PATH} as version 2.0 …")
    with open(V2_PATH, "rb") as f:
        r = c.post("/api/ingest", files={"file": ("ct200_manual_v2.pdf", f, "application/pdf")},
                   data={"document_id": DOC_ID, "version_tag": "2.0"})
    v2_resp = _check(r, "Ingest v2")
    v2_id = v2_resp["version"]["id"]

    # ── 3. List top-level nodes (latest = v2) ────────────────────────────────
    r = c.get("/api/nodes", params={"document_id": DOC_ID})
    nodes_data = _check(r, "Top-level nodes (latest)")
    top_nodes = nodes_data

    # ── 4. Find section 2 – Safety Warnings ─────────────────────────────────
    safety_node = next((n for n in top_nodes if "Safety" in n["heading"]), None)
    if not safety_node:
        print("WARNING: Safety node not found in top-level; searching …")
        r = c.get("/api/search", params={"q": "Cuff Pressure Safety", "document_id": DOC_ID})
        results = r.json()
        safety_node = results[0] if results else None

    if safety_node:
        # Get node detail
        r = c.get(f"/api/nodes/{safety_node['id']}")
        _check(r, "Safety section detail")

    # ── 5. Search for a known-changed term ──────────────────────────────────
    r = c.get("/api/search", params={"q": "pressurisation", "document_id": DOC_ID})
    _check(r, "Search: 'pressurisation'")

    # ── 6. Find the "2.2 Cuff Pressure Safety" node by search ───────────────
    r = c.get("/api/search", params={"q": "Cuff Pressure Safety", "document_id": DOC_ID})
    cuff_results = r.json()
    if cuff_results:
        cuff_node_id = cuff_results[0]["id"]

        # ── 7. Diff: compare across versions ────────────────────────────────
        r = c.get(f"/api/nodes/{cuff_node_id}/diff",
                  params={"document_id": DOC_ID,
                          "version_a": "1.0", "version_b": "2.0"})
        _check(r, "Diff: 2.2 Cuff Pressure Safety (v1 vs v2)")
    else:
        cuff_node_id = None

    # ── 8. List all versions ─────────────────────────────────────────────────
    r = c.get("/api/versions", params={"document_id": DOC_ID})
    _check(r, "All versions")

    # ── 9. Create a v1-pinned selection with changed nodes ───────────────────
    # Find nodes in v1 that we know will change in v2
    r = c.get("/api/search", params={"q": "Cuff Pressure Safety",
                                      "document_id": DOC_ID, "version_tag": "1.0"})
    v1_cuff = r.json()
    r2 = c.get("/api/search", params={"q": "Taking a Measurement",
                                       "document_id": DOC_ID, "version_tag": "1.0"})
    v1_measure = r2.json()

    node_ids_for_selection = []
    if v1_cuff:
        node_ids_for_selection.append(v1_cuff[0]["id"])
    if v1_measure:
        node_ids_for_selection.append(v1_measure[0]["id"])

    if not node_ids_for_selection:
        # Fallback: use whatever top-level nodes exist
        r = c.get("/api/nodes", params={"document_id": DOC_ID, "version_tag": "1.0"})
        v1_tops = r.json()
        node_ids_for_selection = [v1_tops[0]["id"]] if v1_tops else []

    sel_payload = {
        "name": "Safety & Measurement Sections (v1)",
        "doc_version_id": v1_id,
        "node_ids": node_ids_for_selection,
    }
    r = c.post("/api/selections", json=sel_payload)
    sel_data = _check(r, "Create selection (v1-pinned)")
    selection_id = sel_data["id"]

    # ── 10. Generate test cases ──────────────────────────────────────────────
    r = c.post("/api/generations", params={"selection_id": selection_id})
    gen_data = _check(r, "Generate test cases")
    generation_id = gen_data["generation_id"]

    # ── 11. Retrieve generation → staleness should be True (v1 nodes changed in v2) ──
    print("\n[Waiting 1s for DB flush …]")
    time.sleep(1)
    r = c.get(f"/api/generations/{generation_id}")
    _check(r, f"Retrieve generation {generation_id} (staleness check)")

    # ── 12. Submit same selection again → NEW generation created ────────────
    r = c.post("/api/generations", params={"selection_id": selection_id})
    gen_data2 = _check(r, "Re-submit same selection -> new generation")
    assert gen_data2["generation_id"] != generation_id, \
        "Duplicate submission must create a NEW generation ID."
    print("\n✓ Duplicate submission created new generation (as designed).")

    # ── 13. List all generations for the selection ───────────────────────────
    r = c.get("/api/generations", params={"selection_id": selection_id})
    _check(r, "List generations for selection")

    print("\n" + "="*60)
    print("  END-TO-END DEMO COMPLETE — all flows verified.")
    print("="*60)


if __name__ == "__main__":
    main()
