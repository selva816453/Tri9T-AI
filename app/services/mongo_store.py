"""
MongoDB store for LLM-generated output.

We use MongoDB (local or Atlas) for storing the full LLM generation output.
Rationale: LLM output is semi-structured JSON that can vary in shape (e.g.,
partial_error responses have no test_cases); a document store avoids schema
migration pain as the output format evolves.

SQL (SQLite) stores the metadata and staleness state; MongoDB stores the
full payload.  The Generation.mongo_id SQL column links the two.

If MONGO_URI is not set, we fall back to a simple JSON-file-based store
to keep the system functional without MongoDB.  This is explicitly a
development convenience, not a production design.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── MongoDB client (lazy, singleton) ─────────────────────────────────────────

_mongo_client = None
_mongo_db     = None

def _get_mongo_collection():
    global _mongo_client, _mongo_db
    mongo_uri = os.getenv("MONGO_URI", "")
    if not mongo_uri:
        return None
    if _mongo_client is None:
        from pymongo import MongoClient
        _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        _mongo_db = _mongo_client[os.getenv("MONGO_DB_NAME", "ct200_qa")]
    return _mongo_db["generations"]


# ─── JSON file fallback ───────────────────────────────────────────────────────

_FALLBACK_DIR = Path("data/mongo_fallback")

def _fallback_insert(doc: dict) -> str:
    _FALLBACK_DIR.mkdir(parents=True, exist_ok=True)
    oid = str(uuid.uuid4())
    doc["_id"] = oid
    (_FALLBACK_DIR / f"{oid}.json").write_text(
        json.dumps(doc, indent=2, default=str), encoding="utf-8"
    )
    return oid


def _fallback_find(oid: str) -> Optional[dict]:
    path = _FALLBACK_DIR / f"{oid}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


# ─── Public API ───────────────────────────────────────────────────────────────

def store_generation(
    generation_id: str,
    selection_id:  str,
    status:        str,
    test_cases:    list[dict],
    raw_llm_output: Optional[str],
    error_detail:  Optional[str],
    node_hashes:   list[str],
) -> str:
    """
    Store a generation result.  Returns the MongoDB ObjectId (or fallback UUID).
    """
    doc = {
        "generation_id":   generation_id,
        "selection_id":    selection_id,
        "status":          status,
        "test_cases":      test_cases,
        "raw_llm_output":  raw_llm_output,
        "error_detail":    error_detail,
        "node_hashes":     node_hashes,   # snapshot hashes at generation time
        "created_at":      datetime.now(timezone.utc).isoformat(),
    }

    col = _get_mongo_collection()
    if col is not None:
        try:
            result = col.insert_one(doc)
            oid = str(result.inserted_id)
            logger.info("Stored generation in MongoDB: %s", oid)
            return oid
        except Exception as e:
            logger.warning("MongoDB write failed (%s); using fallback.", e)

    oid = _fallback_insert(doc)
    logger.info("Stored generation in JSON fallback: %s", oid)
    return oid


def fetch_generation(mongo_id: str) -> Optional[dict]:
    """
    Retrieve a generation document by its Mongo ObjectId (or fallback UUID).
    """
    col = _get_mongo_collection()
    if col is not None:
        try:
            from bson import ObjectId
            doc = col.find_one({"_id": ObjectId(mongo_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
                return doc
        except Exception as e:
            logger.warning("MongoDB read failed (%s); trying fallback.", e)

    return _fallback_find(mongo_id)


def fetch_generations_by_selection(selection_id: str) -> list[dict]:
    """
    Retrieve all generation documents for a given selection_id.
    """
    col = _get_mongo_collection()
    if col is not None:
        try:
            docs = list(col.find({"selection_id": selection_id}))
            for d in docs:
                d["_id"] = str(d["_id"])
            return docs
        except Exception as e:
            logger.warning("MongoDB query failed (%s); using fallback.", e)

    # Fallback: scan all JSON files
    results = []
    if _FALLBACK_DIR.exists():
        for path in _FALLBACK_DIR.glob("*.json"):
            try:
                d = json.loads(path.read_text(encoding="utf-8"))
                if d.get("selection_id") == selection_id:
                    results.append(d)
            except Exception:
                pass
    return results
