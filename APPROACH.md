# CT-200 QA Document System — Approach Document & Decision Log

**AI Engineering Internship Assignment — Tri9T AI**  
**Author:** Selvam M  
**Repository:** [https://github.com/selva816453/Tri9T-AI](https://github.com/selva816453/Tri9T-AI)  
**Date:** October 2026  

---

## 1. Executive Summary

The **CT-200 QA Document System** is an AI-powered document engineering platform designed for regulated medical device documentation (specifically the CardioTrack CT-200 Blood Pressure Monitor). It ingests multi-page technical manuals, decomposes them into versioned hierarchical document trees, enables version-pinned requirement selection, and generates structured, traceable QA test suites using Large Language Models (LLMs).

Crucially, the system provides automated **staleness detection**: when a revised manual (e.g., v2.0) is ingested with altered clinical thresholds or safety constraints (such as cuff over-pressurization limits changing from 300 mmHg to 320 mmHg), previously generated test cases anchored to those sections are flagged as **STALE** with exact unified diff summaries.

---

## 2. System Architecture

The application is structured into modular layers prioritizing separation of concerns, testability, and resilience:

```
┌─────────────────────────────────────────────────────────────┐
│                 Frontend Dashboard & UI                     │
│         (HTML5, Modern CSS Glassmorphism, Vanilla JS)        │
└──────────────────────────────┬──────────────────────────────┘
                               │ REST API
┌──────────────────────────────▼──────────────────────────────┐
│                    FastAPI Backend Router                   │
│   /api/ingest  •  /api/nodes  •  /api/selections  •  /api/generations   │
└──────────────┬──────────────────────────────┬───────────────┘
               │                              │
┌──────────────▼─────────────┐ ┌──────────────▼───────────────┐
│   Document Parsing Engine  │ │   LLM & Staleness Engine     │
│   • pdfminer.six extraction│ │   • Groq (Llama-3.3-70b)     │
│   • Font clustering (H1-H3)│ │   • Pydantic schema guard    │
│   • Stack tree builder     │ │   • Snapshot hash validation │
│   • Heuristic sanitization │ │   • Unified diff computation │
└──────────────┬─────────────┘ └──────────────┬───────────────┘
               │                              │
┌──────────────▼─────────────┐ ┌──────────────▼───────────────┐
│  Relational Database (SQL) │ │   Document Store (NoSQL)     │
│  • SQLite (SQLAlchemy ORM) │ │   • MongoDB (Generations)    │
│  • Versions, Nodes, Diffs  │ │   • JSON File Fallback Store │
└────────────────────────────┘ └──────────────────────────────┘
```

### Key Architectural Components
1. **FastAPI Application Layer (`app/main.py`, `app/api/`):** Exposes clean REST endpoints for file ingestion, hierarchy exploration, version diffing, requirement search, selection management, and test case generation.
2. **Parsing & Ingestion Engine (`app/services/parser.py`, `app/services/ingestion.py`):** Pure-Python text and font metadata extraction using `pdfminer.six`, converting raw stream elements into a structured hierarchy of `ParsedNode`s.
3. **LLM Generation Service (`app/services/llm_service.py`):** Integrates with Groq's high-speed inference API (`llama-3.3-70b-versatile`) with prompt templates calibrated for medical device compliance (ISO 13485, IEC 62304). Includes schema validation and structured fallback.
4. **Hybrid Storage Layer (`app/core/database.py`, `app/services/mongo_store.py`):** Relational tables in SQLite manage structured entities, relations, and diff logs; MongoDB (or automatic JSON file fallback) stores flexible LLM-generated test case payloads.

---

## 3. PDF Parsing & Hierarchy Reconstruction

### 3.1 Dual-Signal Classification Strategy
PDFs do not possess native semantic tags (like HTML `<h1>`, `<h2>`). The parser reconstructs the document hierarchy using two complementary signals:
1. **Font Size Clustering:** Analyzes the distribution of font sizes across all text lines. The largest dominant sizes are mapped to Heading 1, followed by Heading 2 and Heading 3, while standard sizes are classified as body text.
2. **Regex Prefix Validation:** Uses regex patterns (`^(\d+(?:\.\d+)*)\.\s+\S` and `^Appendix\s+[A-Z]:?`) to inspect section numbering (e.g., `2.`, `2.2`, `2.2.1`). The dot count deterministically defines the nesting depth. This prevents headings rendered with smaller fonts from being misclassified as body text.

### 3.2 Stack-Based Tree Construction
As lines are processed sequentially:
- When a heading of level $N$ is encountered, the stack is popped until the top element is at level $N - 1$.
- The new node is pushed onto the stack and linked as a child of its parent.
- Subsequent text lines, warnings, and table rows are accumulated into the active node's `body_text`.

### 3.3 Edge Cases Handled
- **Duplicate Headings:** Separate sections sharing identical titles (e.g., multiple "Overview" or "Maintenance" sub-sections) receive distinct UUIDs and unique `logical_id` hierarchical paths.
- **Level-Skipping:** If an H1 is directly followed by an H3, intermediate virtual levels are dynamically bridged to prevent tree fragmentation.
- **Table of Contents (TOC):** Detected via leader-dot patterns (`\.{5,}\s*\d+$`) and isolated as leaf text rather than generating phantom child nodes.
- **Table Cell & Caption Stitching:** Short adjacent lines from ReportLab tables are reconstructed into tab-delimited text rows; `Figure X-Y:` captions and warning callouts (`⚠ WARNING:`) are attached to their parent section.

---

## 4. Versioning & Cross-Version Node Matching

### 4.1 Path-Based Matching (`logical_id`)
When a new document version (e.g., v2.0) is ingested, nodes must be correlated with previous versions to detect modifications.
- **Chosen Approach:** Deterministic path-based matching using `logical_id` (e.g., `2.2` for "2.2 Cuff Pressure Safety").
- **Why Path-Based?** In engineering manuals, section numbering is deliberately managed across revisions. A content change within section 2.2 retains the label `2.2`. 
- **Why Not Pure Hash Matching?** Content hashing fails immediately when text changes—the exact moment change detection and staleness tracking are required.
- **Why Not Fuzzy String Matching?** Fuzzy matching risks falsely conflating distinct sections like "Error Codes" (Section 8) and "Error Codes During Startup" (Section 8.1).

### 4.2 Content Hashing & Diff Summarization
Each node's content is hashed using SHA-256 over its normalized heading and body text:
$$\text{content\_hash} = \text{SHA256}(\text{heading} + \text{"\n"} + \text{body\_text})$$
When a node exists in both versions with differing hashes:
1. It is marked as modified (`is_changed = True`).
2. A unified diff summary is computed via Python’s `difflib.unified_diff`, capturing the first lines of alterations (e.g., `--- 300 mmHg`, `+++ 320 mmHg`).
3. The diff is recorded in `node_versions.diff_summary`.

---

## 5. Selection Pinning & Staleness Detection

### 5.1 Immutable Version Pinning
QA teams rarely test against a shifting target. When creating a `Selection`:
- The user specifies an explicit `doc_version_id` along with target `node_ids`.
- The selection is permanently **pinned** to that document version. Ingesting future versions does not alter or re-point the selection.

### 5.2 Content Snapshot Hashing
Upon triggering test case generation (`POST /api/generations?selection_id=...`):
- The system captures a snapshot of the SHA-256 hashes for all selected nodes:
  $$\text{snapshot\_hashes} = [h_1, h_2, \dots, h_k]$$
- These hashes are persisted alongside the generation metadata.

### 5.3 Retrieval-Time Staleness Evaluation
When a generation is queried via `GET /api/generations/{id}`:
1. For each node in the pinned selection, the engine looks up the latest corresponding version of that node in the system.
2. If the current node's `content_hash` does not match the pinned snapshot hash:
   - The generation is declared **`is_stale: true`**.
   - A `StalenessInfo` record is attached detailing the node ID, heading, logical path, and exact diff summary.
3. If a node was deleted in subsequent revisions, it is marked as stale with a `"Node removed in later version"` diagnostic.

### 5.4 Duplicate Submission Policy
Re-submitting an existing `selection_id` creates a **new, discrete generation** rather than silently deduplicating. This ensures an auditable historical trail: QA engineers can review previous test iterations alongside fresh generations created after document updates.

---

## 6. LLM Test Case Generation & Reliability

### 6.1 Model & Domain Prompting
- **Inference Engine:** Groq API running `llama-3.3-70b-versatile` for sub-second structured generation.
- **System Role:** Regulated medical device QA engineer adhering to ISO 13485 and IEC 62304 standards.
- **Output Requirements:** Between 3 to 5 executable test cases per section, containing:
  - `id`: Unique test case identifier (e.g., `TC-001`)
  - `title`: Concise objective
  - `preconditions`: Environmental and device state requirements
  - `steps`: Sequential, step-by-step instructions
  - `expected_result`: Verifiable acceptance criterion
  - `requirement_ref`: Heading and section anchor ensuring end-to-end traceability

### 6.2 Fault Tolerance & Schema Enforcement
1. **Pydantic Validation:** Raw model outputs are validated against the `TestCaseList` schema.
2. **Regex Recovery:** If the model outputs conversational preamble or markdown code fences, regex pattern matching extracts the core JSON structure.
3. **Graceful Partial Failure:** If validation fails completely, the system records `status = "partial_error"` with raw output preserved—preventing catastrophic API crashes while avoiding silent data corruption.
4. **Transient HTTP Retries:** Automatic retry with 2-second exponential backoff for HTTP 429 (Rate Limit) or 503 (Service Unavailable).
5. **Zero-Credential Mock Mode:** If `GROQ_API_KEY` is not provided, the service supplies realistic mock test cases, ensuring seamless local development and automated CI testing.

---

## 7. Database Design & Persistence

### 7.1 SQLite Relational Schema
- `document_versions`: Tracks document identifiers, version tags, file names, node counts, and ingestion timestamps.
- `document_nodes`: Stores hierarchical nodes (`node_id`, `logical_id`, `heading`, `level`, `body_text`, `parent_id`, `order_index`, `content_hash`).
- `node_versions`: Bridge table linking nodes to document versions, containing `is_changed` flags and `diff_summary` text.
- `selections`: Version-pinned user selections.
- `selection_items`: Individual nodes associated with a selection.
- `generations`: Test case generation records with `content_snapshot_hashes`, status, and reference pointers to the document store.

### 7.2 NoSQL Document Store & Fallback
- Primary: MongoDB stores full test case JSON payloads, allowing unstructured expansion without database schema migrations.
- Fallback: Transparent JSON flat-file storage in `data/mongo_fallback/{id}.json` ensures the application runs out-of-the-box on systems without active MongoDB instances.

---

## 8. Verification & Test Coverage

### 8.1 Automated Unit Tests (`tests/test_parser.py`)
7 specialized test suites validate edge cases without server overhead:
1. `test_duplicate_headings`: Distinct node IDs generated for identical titles.
2. `test_level_skipping`: H1 to H3 gap handling.
3. `test_toc_exclusion`: Table of contents filtering.
4. `test_table_text_reconstruction`: Tab-delimited row parsing.
5. `test_figure_captions`: Caption association with parent sections.
6. `test_content_hash_stability`: Deterministic SHA-256 reproducibility.
7. `test_version_diff_detection`: Correct identification of altered parameters.

### 8.2 End-to-End Workflow Demonstration (`scripts/e2e_demo.py`)
Executes the full pipeline:
- Ingests `ct200_manual_v1.pdf` (145 nodes).
- Ingests `ct200_manual_v2.pdf` (149 nodes, 5 altered sections).
- Generates test cases for v1-pinned section `2.2 Cuff Pressure Safety`.
- Invalidation test: retrieves generation and verifies `is_stale: true` triggers due to cuff threshold revision (300 mmHg → 320 mmHg, 2s → 1s).
- History test: re-submits selection, confirming new generation ID creation.

---

## 9. Decision Log & Trade-Off Summary

| Decision | Alternative Considered | Selected Approach | Key Rationale |
|---|---|---|---|
| **Node Matching** | Content Hash / Fuzzy Title Matching | **Path-based `logical_id`** | Content hashing breaks on any text update; fuzzy matching creates false mergers. Path matching reflects technical manual numbering discipline. |
| **Staleness Detection** | Semantic NLP Embedding Similarity | **Hash Inequality + Unified Diff** | Absolute determinism required in medical compliance. Diffs provide human-readable context on exact parameter shifts. |
| **Selection Pinning** | Dynamic Pointer to Latest Version | **Immutable Version Pinning** | QA test plans must guarantee repeatability against a fixed baseline; dynamic shifting invalidates audit compliance. |
| **Duplicate Submissions** | Deduplication / Overwrite | **Append-Only History** | QA audit trails require complete historical lineage; deduplication obscures that document edits occurred. |
| **Storage Architecture** | Pure Relational or Pure Document DB | **Hybrid SQLite + MongoDB/JSON** | Relational integrity for tree hierarchies and foreign keys; document agility for varied LLM test payloads. |
| **External Dependencies** | Mandatory MongoDB & Paid Cloud LLM | **Optional MongoDB + Groq Free Tier / Mock** | Zero friction setup; permits automated headless evaluation and instant developer onboarding. |

---

## 10. Conclusion

The CT-200 QA Document System delivers a robust, deterministic, and compliance-aware foundation for medical device test engineering. By unifying structural PDF parsing, path-based version reconciliation, version-pinned test generation, and automated staleness alerts, the system eliminates manual discrepancy tracking and accelerates QA verification workflows.
