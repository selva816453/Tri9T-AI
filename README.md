# CT-200 QA Document System

**AI Engineering Internship Assignment — Tri9T AI**

A backend API that ingests the CardioTrack CT-200 medical device manual, builds a versioned hierarchical document tree, and generates LLM-powered QA test cases with staleness tracking.

---

## Quick Start (3 commands)

```bash
# 1 — Install dependencies
pip install -r requirements.txt

# 2 — Generate the mock PDFs (v1 and v2)
python scripts/generate_mock_pdfs.py

# 3 — Start the API server
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000/docs** for the interactive Swagger UI.

---

## Full Setup Guide

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.10+ |
| pip | any |
| MongoDB | optional (JSON fallback provided) |
| Groq API key | optional (mock output used without it) |

### Step 1 — Clone / open the project

```
cd "c:\Users\selva\OneDrive\Desktop\Tri9T AI"
```

### Step 2 — Install Python dependencies

```bash
pip install -r requirements.txt
```

### Step 3 — Configure environment variables

```bash
# Copy the template
copy .env.example .env
```

Edit `.env` and fill in your keys (both are optional for local testing):

```
GROQ_API_KEY=gsk_your_key_here          # https://console.groq.com/
MONGO_URI=mongodb://localhost:27017      # leave blank to use JSON fallback
```

### Step 4 — Generate the mock PDFs

```bash
python scripts/generate_mock_pdfs.py
```

This creates:
- `data/ct200_manual_v1.pdf` — original manual (145 nodes)
- `data/ct200_manual_v2.pdf` — revised manual (149 nodes, 5 sections changed)

### Step 5 — Run the server

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

The SQLite database (`data/ct200_qa.db`) and all tables are created automatically on first startup.

---

## Running the Tests

```bash
# Unit tests (no server required)
python tests/test_parser.py
```

Expected output: **7/7 passed** — covers duplicate headings, level-skipping, TOC handling, and more.

---

## Triggering the v1 → v2 Re-ingestion Flow

This is the key flow. With the server running, run:

```bash
python scripts/e2e_demo.py
```

This script:
1. **Ingests v1** → 145 nodes stored in SQLite
2. **Ingests v2** → 149 nodes; changed nodes flagged with diff summaries
3. **Lists nodes** for latest version
4. **Diffs node** `2.2 Cuff Pressure Safety` between v1 and v2 (300→320 mmHg, 2s→1s)
5. **Searches** across node text
6. **Creates a v1-pinned selection** containing the two sections that change in v2
7. **Generates QA test cases** (mock or real LLM depending on `GROQ_API_KEY`)
8. **Retrieves the generation** — `is_stale: true` fires because v2 changed the pinned nodes
9. **Re-submits** the same selection → proves a NEW generation ID is created (not deduplicated)
10. **Lists all generations** for the selection

---

## API Reference

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/docs` | Swagger UI |

### Documents & Versioning
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/ingest` | Ingest a PDF as a new version |
| GET | `/api/versions` | List all document versions |
| GET | `/api/nodes?document_id=&version_tag=` | List top-level nodes (defaults to latest) |
| GET | `/api/nodes/{id}` | Get node with full body text and children |
| GET | `/api/nodes/{id}/diff?document_id=&version_a=&version_b=` | Diff a node across versions |
| GET | `/api/search?q=&document_id=` | Full-text search across nodes |

### Selections
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/selections` | Create a version-pinned selection |
| GET | `/api/selections` | List all selections |
| GET | `/api/selections/{id}` | Get a selection |

### Generations (LLM + Staleness)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/generations?selection_id=` | Generate QA test cases |
| GET | `/api/generations?selection_id=` | List generations with staleness flag |
| GET | `/api/generations/{id}` | Get generation + full staleness detail |

---

## curl Examples

```bash
# Health
curl http://localhost:8000/health

# Ingest v1
curl -X POST http://localhost:8000/api/ingest \
  -F "file=@data/ct200_manual_v1.pdf" \
  -F "document_id=CT200-MAN-001" \
  -F "version_tag=1.0"

# List top-level nodes (latest version)
curl "http://localhost:8000/api/nodes?document_id=CT200-MAN-001"

# Search
curl "http://localhost:8000/api/search?q=pressurisation&document_id=CT200-MAN-001"

# Diff a node across versions
curl "http://localhost:8000/api/nodes/{NODE_ID}/diff?document_id=CT200-MAN-001&version_a=1.0&version_b=2.0"

# Create a selection (version-pinned)
curl -X POST http://localhost:8000/api/selections \
  -H "Content-Type: application/json" \
  -d '{"name":"My Selection","doc_version_id":"VERSION_ID","node_ids":["NODE_ID"]}'

# Generate test cases
curl -X POST "http://localhost:8000/api/generations?selection_id=SELECTION_ID"

# Retrieve generation (with staleness check)
curl "http://localhost:8000/api/generations/GENERATION_ID"
```

---

## Project Structure

```
Tri9T AI/
├── app/
│   ├── main.py                  # FastAPI app entry point
│   ├── api/
│   │   ├── documents.py         # Ingest, browse, diff, search
│   │   ├── selections.py        # Version-pinned selections
│   │   └── generations.py       # LLM generation + staleness
│   ├── core/
│   │   └── database.py          # SQLAlchemy engine + session
│   ├── models/
│   │   ├── db_models.py         # SQLAlchemy ORM models
│   │   └── schemas.py           # Pydantic response schemas
│   └── services/
│       ├── parser.py            # PDF parsing pipeline
│       ├── ingestion.py         # Document ingestion service
│       ├── llm_service.py       # Groq LLM + structured output
│       └── mongo_store.py       # MongoDB / JSON fallback store
├── data/
│   ├── ct200_manual_v1.pdf      # Generated mock PDF v1
│   ├── ct200_manual_v2.pdf      # Generated mock PDF v2
│   ├── ct200_qa.db              # SQLite database (auto-created)
│   └── mongo_fallback/          # JSON fallback for LLM output
├── scripts/
│   ├── generate_mock_pdfs.py    # Generates both mock PDFs
│   └── e2e_demo.py              # End-to-end demo / integration test
├── tests/
│   └── test_parser.py           # 7 unit tests for parser edge cases
├── .env.example                 # Environment variable template
├── requirements.txt
└── README.md
```

---

## Known Limitations & Design Decisions

See `APPROACH.md` for the full decision log. Key points:

- **Path-based version matching** (not hash-based): stable when content changes, breaks on section renumbering
- **Staleness = hash inequality**: a one-word change and a full rewrite look identical — the diff summary provides context
- **Duplicate submission policy**: always creates a new generation — history is preserved
- **LLM failure handling**: schema validation failure → `partial_error` (no retry); transient HTTP errors → up to 2 retries with backoff
- **MongoDB is optional**: JSON file fallback in `data/mongo_fallback/` keeps the system testable without a running MongoDB instance
