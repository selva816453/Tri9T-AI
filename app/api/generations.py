"""
Generations API: LLM test case generation + staleness + retrieval.

Endpoints:
  POST /api/generations                         – generate test cases for a selection
  GET  /api/generations                         – list generations (by selection or node)
  GET  /api/generations/{generation_id}         – get a generation with staleness check

Staleness detection:
  At generation time we store a pipe-separated list of content_hash values
  of all pinned nodes (Generation.content_snapshot_hashes).

  At retrieval time, for each pinned node we look up the current DocumentNode.content_hash.
  If the current hash differs from the pinned hash, that node is "stale" and we return
  a StalenessInfo entry explaining what changed.

  Limits:
  - We use hash equality, not semantic diff — a one-word change ("300 mmHg" → "320 mmHg")
    looks the same as a structural rewrite.  We surface the diff_summary from NodeVersion
    to give the user some signal, but a QA engineer must decide if the change is material.
  - Nodes that were deleted entirely (not present in any later version) are flagged as
    stale with a "node removed" note.
  - The Table of Contents changes whenever any section is added; its staleness flag will
    almost always fire and should be interpreted cautiously.

Duplicate submission policy:
  If the same selection_id is submitted again we create a NEW generation and return it.
  The old generation is preserved with its original state.  The list endpoint returns
  all generations for a selection in reverse-chronological order, so callers can always
  retrieve the history.  Rationale: the user may intentionally re-generate after a
  document change, and silently deduplicating would hide that the content changed.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import (
    DocumentNode, DocumentVersion, Generation,
    NodeVersion, Selection, SelectionItem,
)
from app.models.schemas import (
    GenerationListItem, GenerationResponse, StalenessInfo, TestCaseSchema,
)
from app.services.llm_service import generate_test_cases
from app.services.mongo_store import fetch_generation, fetch_generations_by_selection, store_generation

router = APIRouter(prefix="/api/generations", tags=["generations"])
logger = logging.getLogger(__name__)


# ─── Staleness computation ────────────────────────────────────────────────────

def _compute_staleness(
    db: Session,
    items: list[SelectionItem],
    snapshot_hashes: list[str],
) -> tuple[bool, list[StalenessInfo]]:
    """
    Compare pinned hashes against current node hashes.

    Returns (is_stale, list[StalenessInfo]).
    """
    stale_infos: list[StalenessInfo] = []
    snapshot_set = set(snapshot_hashes)

    for item in items:
        node = db.get(DocumentNode, item.node_id)
        if node is None:
            stale_infos.append(StalenessInfo(
                node_id=item.node_id,
                logical_id="unknown",
                heading="[NODE REMOVED]",
                is_stale=True,
                current_hash="",
                pinned_hash=item.pinned_hash,
                diff_summary="Node no longer exists in the database.",
            ))
            continue

        current_hash = node.content_hash
        is_stale = current_hash != item.pinned_hash

        diff_summary: Optional[str] = None
        if is_stale:
            # Try to find the latest NodeVersion diff_summary
            latest_nv = (
                db.query(NodeVersion)
                .filter_by(node_id=item.node_id, changed=True)
                .order_by(NodeVersion.id.desc())
                .first()
            )
            diff_summary = latest_nv.diff_summary if latest_nv else None

        if is_stale:
            stale_infos.append(StalenessInfo(
                node_id=node.id,
                logical_id=node.logical_id,
                heading=node.heading,
                is_stale=True,
                current_hash=current_hash,
                pinned_hash=item.pinned_hash,
                diff_summary=diff_summary,
            ))

    return bool(stale_infos), stale_infos


# ─── Generate ─────────────────────────────────────────────────────────────────

@router.post("", response_model=GenerationResponse, status_code=201,
             summary="Generate QA test cases for a selection")
def generate(
    selection_id: str   = Query(..., description="Selection ID to generate from"),
    db: Session = Depends(get_db),
):
    """
    Reconstruct section text from all pinned nodes, send to the LLM, and
    store the result in MongoDB.  Always creates a new generation (see module
    docstring for duplicate-submission policy).
    """
    sel = db.get(Selection, selection_id)
    if not sel:
        raise HTTPException(404, f"Selection '{selection_id}' not found.")

    # Reconstruct section texts
    section_texts: list[tuple[str, str]] = []
    snapshot_hashes: list[str] = []
    for item in sel.items:
        node = db.get(DocumentNode, item.node_id)
        if not node:
            continue
        section_texts.append((node.heading, node.body_text or ""))
        snapshot_hashes.append(item.pinned_hash)

    if not section_texts:
        raise HTTPException(422, "Selection has no resolvable nodes.")

    # LLM call
    result = generate_test_cases(section_texts)

    # Persist SQL metadata
    gen = Generation(
        selection_id=selection_id,
        content_snapshot_hashes="|".join(snapshot_hashes),
        is_stale=False,
        stale_nodes="",
    )
    db.add(gen)
    db.flush()

    # Persist full output in Mongo/fallback
    mongo_id = store_generation(
        generation_id=gen.id,
        selection_id=selection_id,
        status=result.status,
        test_cases=[tc.model_dump() for tc in result.test_cases],
        raw_llm_output=result.raw_llm_output,
        error_detail=result.error_detail,
        node_hashes=snapshot_hashes,
    )
    gen.mongo_id = mongo_id
    db.commit()

    # Staleness (fresh generation is never stale)
    return GenerationResponse(
        generation_id=gen.id,
        selection_id=selection_id,
        status=result.status,
        test_cases=[TestCaseSchema(**tc.model_dump()) for tc in result.test_cases],
        error_detail=result.error_detail,
        created_at=gen.created_at,
        is_stale=False,
        stale_nodes=[],
    )


# ─── List Generations ─────────────────────────────────────────────────────────

@router.get("", response_model=list[GenerationListItem],
            summary="List generations by selection or node ID")
def list_generations(
    selection_id: Optional[str] = Query(None),
    node_id:      Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Generation)
    if selection_id:
        q = q.filter_by(selection_id=selection_id)
    if node_id:
        # find selections containing this node
        sel_ids = [
            si.selection_id
            for si in db.query(SelectionItem).filter_by(node_id=node_id).all()
        ]
        q = q.filter(Generation.selection_id.in_(sel_ids))

    gens = q.order_by(Generation.created_at.desc()).all()

    items = []
    for g in gens:
        # Recompute staleness at query time
        sel = db.get(Selection, g.selection_id)
        if sel:
            snap_hashes = g.content_snapshot_hashes.split("|") if g.content_snapshot_hashes else []
            is_stale, _ = _compute_staleness(db, sel.items, snap_hashes)
            # Update cached flag
            if g.is_stale != is_stale:
                g.is_stale = is_stale
                db.commit()

        # Get test case count from Mongo
        mongo_doc = fetch_generation(g.mongo_id) if g.mongo_id else None
        tc_count = len(mongo_doc.get("test_cases", [])) if mongo_doc else 0

        items.append(GenerationListItem(
            generation_id=g.id,
            selection_id=g.selection_id,
            status=mongo_doc.get("status", "unknown") if mongo_doc else "unknown",
            test_case_count=tc_count,
            created_at=g.created_at,
            is_stale=g.is_stale,
        ))

    return items


# ─── Get Single Generation ────────────────────────────────────────────────────

@router.get("/{generation_id}", response_model=GenerationResponse,
            summary="Get a generation with current staleness check")
def get_generation(
    generation_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieve a generation by ID.  Staleness is computed at query time by
    comparing the pinned content hashes against the current node hashes.
    """
    gen = db.get(Generation, generation_id)
    if not gen:
        raise HTTPException(404, f"Generation '{generation_id}' not found.")

    # Fetch from Mongo
    mongo_doc = fetch_generation(gen.mongo_id) if gen.mongo_id else None
    if not mongo_doc:
        raise HTTPException(500, "Generation output not found in document store.")

    # Reconstruct test cases
    raw_tcs = mongo_doc.get("test_cases", [])
    test_cases = []
    for tc in raw_tcs:
        try:
            test_cases.append(TestCaseSchema(**tc))
        except Exception:
            pass   # skip malformed entries from historical partial_error responses

    # Staleness check
    sel = db.get(Selection, gen.selection_id)
    if not sel:
        raise HTTPException(500, f"Selection '{gen.selection_id}' missing.")

    snap_hashes = gen.content_snapshot_hashes.split("|") if gen.content_snapshot_hashes else []
    is_stale, stale_infos = _compute_staleness(db, sel.items, snap_hashes)

    # Update cached flag
    if gen.is_stale != is_stale:
        gen.is_stale = is_stale
        gen.stale_nodes = "|".join([si.node_id for si in stale_infos])
        db.commit()

    return GenerationResponse(
        generation_id=gen.id,
        selection_id=gen.selection_id,
        status=mongo_doc.get("status", "unknown"),
        test_cases=test_cases,
        error_detail=mongo_doc.get("error_detail"),
        created_at=gen.created_at,
        is_stale=is_stale,
        stale_nodes=stale_infos,
    )
