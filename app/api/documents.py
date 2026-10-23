"""
Document ingestion and browse API.

Endpoints:
  POST /api/ingest         – ingest a new document version
  GET  /api/versions       – list all ingested versions
  GET  /api/nodes          – list top-level nodes for a version
  GET  /api/nodes/{id}     – get a specific node with children and body text
  GET  /api/nodes/{id}/diff – compare a node across two versions
  GET  /api/search         – full-text search across nodes
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import DocumentNode, DocumentVersion, NodeVersion
from app.models.schemas import (
    IngestResponse, NodeDetail, NodeDiff, NodeSummary, VersionSummary,
)
from app.services.ingestion import ingest_document

router = APIRouter(prefix="/api", tags=["documents"])
logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _resolve_version(db: Session, document_id: str, version_tag: Optional[str]) -> DocumentVersion:
    q = db.query(DocumentVersion).filter_by(document_id=document_id)
    if version_tag:
        ver = q.filter_by(version_tag=version_tag).first()
    else:
        ver = q.order_by(DocumentVersion.ingested_at.desc()).first()
    if not ver:
        raise HTTPException(404, f"No version found for document '{document_id}'" +
                            (f" with tag '{version_tag}'" if version_tag else "."))
    return ver


def _node_to_summary(node: DocumentNode) -> NodeSummary:
    return NodeSummary(
        id=node.id,
        logical_id=node.logical_id,
        heading=node.heading,
        level=node.level,
        content_hash=node.content_hash,
        order_index=node.order_index,
        parent_id=node.parent_id,
        child_count=len(node.children),
    )


def _node_to_detail(node: DocumentNode) -> NodeDetail:
    return NodeDetail(
        id=node.id,
        logical_id=node.logical_id,
        heading=node.heading,
        level=node.level,
        content_hash=node.content_hash,
        order_index=node.order_index,
        parent_id=node.parent_id,
        body_text=node.body_text or "",
        children=[_node_to_summary(c) for c in
                  sorted(node.children, key=lambda c: c.order_index)],
    )


def _get_nodes_for_version(db: Session, doc_version_id: str) -> list[DocumentNode]:
    """Return all nodes that appear in a specific document version."""
    nv_rows = db.query(NodeVersion).filter_by(doc_version_id=doc_version_id).all()
    node_ids = [nv.node_id for nv in nv_rows]
    return db.query(DocumentNode).filter(DocumentNode.id.in_(node_ids)).all()


# ─── Ingestion ────────────────────────────────────────────────────────────────

@router.post("/ingest", response_model=IngestResponse, summary="Ingest a PDF document version")
async def ingest_pdf(
    file:        UploadFile = File(..., description="PDF file to ingest"),
    document_id: str        = Form(..., description="Stable document identifier, e.g. CT200-MAN-001"),
    version_tag: str        = Form(..., description="Version label, e.g. '1.0' or '2.0'"),
    db:          Session    = Depends(get_db),
):
    """
    Upload and ingest a PDF.  Re-ingestion of an existing version is rejected.
    To re-ingest, bump the version_tag.
    """
    # Save the uploaded file to disk
    os.makedirs("data", exist_ok=True)
    pdf_path = f"data/{file.filename}"
    with open(pdf_path, "wb") as f:
        f.write(await file.read())

    try:
        doc_ver = ingest_document(
            db=db,
            pdf_path=pdf_path,
            document_id=document_id,
            version_tag=version_tag,
        )
    except ValueError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        logger.exception("Ingestion failed")
        raise HTTPException(500, f"Ingestion failed: {e}")

    return IngestResponse(
        message=f"Successfully ingested version '{version_tag}' of '{document_id}'.",
        version=VersionSummary.model_validate(doc_ver),
    )


# ─── Document Versions ────────────────────────────────────────────────────────

@router.get("/versions", response_model=list[VersionSummary], summary="List all document versions")
def list_versions(
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    db: Session = Depends(get_db),
):
    q = db.query(DocumentVersion)
    if document_id:
        q = q.filter_by(document_id=document_id)
    return [VersionSummary.model_validate(v) for v in
            q.order_by(DocumentVersion.ingested_at.desc()).all()]


# ─── Browse Nodes ─────────────────────────────────────────────────────────────

@router.get("/nodes", response_model=list[NodeSummary], summary="List top-level nodes for a version")
def list_top_nodes(
    document_id: str            = Query(...),
    version_tag: Optional[str]  = Query(None, description="Defaults to latest"),
    db: Session = Depends(get_db),
):
    ver = _resolve_version(db, document_id, version_tag)
    all_nodes = _get_nodes_for_version(db, ver.id)
    # Top-level = no parent, OR parent not in this version
    version_node_ids = {n.id for n in all_nodes}
    tops = [n for n in all_nodes
            if n.parent_id is None or n.parent_id not in version_node_ids]
    tops.sort(key=lambda n: n.order_index)
    return [_node_to_summary(n) for n in tops]


@router.get("/nodes/{node_id}", response_model=NodeDetail, summary="Get a node with full text and children")
def get_node(
    node_id: str,
    db: Session = Depends(get_db),
):
    node = db.get(DocumentNode, node_id)
    if not node:
        raise HTTPException(404, f"Node '{node_id}' not found.")
    return _node_to_detail(node)


# ─── Diff ────────────────────────────────────────────────────────────────────

@router.get("/nodes/{node_id}/diff", response_model=NodeDiff,
            summary="Compare a node across two document versions")
def node_diff(
    node_id:     str,
    document_id: str           = Query(...),
    version_a:   str           = Query(..., description="Earlier version tag"),
    version_b:   str           = Query(..., description="Later version tag"),
    db: Session = Depends(get_db),
):
    node = db.get(DocumentNode, node_id)
    if not node:
        raise HTTPException(404, f"Node '{node_id}' not found.")

    ver_a = _resolve_version(db, document_id, version_a)
    ver_b = _resolve_version(db, document_id, version_b)

    nv_a = db.query(NodeVersion).filter_by(
        node_id=node_id, doc_version_id=ver_a.id).first()
    nv_b = db.query(NodeVersion).filter_by(
        node_id=node_id, doc_version_id=ver_b.id).first()

    if not nv_a or not nv_b:
        raise HTTPException(
            404,
            f"Node '{node_id}' not found in one or both versions "
            f"('{version_a}': {'yes' if nv_a else 'NO'}, "
            f"'{version_b}': {'yes' if nv_b else 'NO'})."
        )

    changed = nv_a.content_hash != nv_b.content_hash
    return NodeDiff(
        node_id=node_id,
        logical_id=node.logical_id,
        heading=node.heading,
        version_a_tag=version_a,
        version_b_tag=version_b,
        changed=changed,
        diff_summary=nv_b.diff_summary if changed else None,
    )


# ─── Search ──────────────────────────────────────────────────────────────────

@router.get("/search", response_model=list[NodeSummary], summary="Search nodes by heading or text")
def search_nodes(
    q:           str            = Query(..., min_length=2, description="Search query"),
    document_id: Optional[str]  = Query(None),
    version_tag: Optional[str]  = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(DocumentNode)

    # If version is specified, filter to nodes in that version
    if document_id:
        ver = _resolve_version(db, document_id, version_tag)
        nv_rows = db.query(NodeVersion).filter_by(doc_version_id=ver.id).all()
        version_node_ids = [nv.node_id for nv in nv_rows]
        query = query.filter(DocumentNode.id.in_(version_node_ids))

    q_lower = f"%{q.lower()}%"
    results = query.filter(
        (DocumentNode.heading.ilike(q_lower)) |
        (DocumentNode.body_text.ilike(q_lower))
    ).limit(50).all()

    return [_node_to_summary(n) for n in results]


# ─── Bulk diff: all changed nodes between two versions ────────────────────────

@router.get(
    "/diff",
    response_model=list[NodeDiff],
    summary="List all nodes that changed between two document versions",
)
def bulk_diff(
    document_id: str = Query(...),
    version_a:   str = Query(..., description="Earlier version tag"),
    version_b:   str = Query(..., description="Later version tag"),
    db: Session = Depends(get_db),
):
    """
    Compare every node that exists in version_a against version_b using
    logical_id as the stable key.

    Strategy:
      1. Load all NodeVersion rows for ver_a  → map {logical_id: NodeVersion}
      2. Load all NodeVersion rows for ver_b  → map {logical_id: NodeVersion}
      3. For each logical_id present in BOTH versions, compare content_hash.
      4. Return only the nodes where changed=True.

    This completely avoids the UUID lookup problem in the per-node endpoint.
    """
    ver_a = _resolve_version(db, document_id, version_a)
    ver_b = _resolve_version(db, document_id, version_b)

    # Build logical_id → (NodeVersion, DocumentNode) maps for each version
    def _build_map(doc_version_id: str) -> dict[str, tuple[NodeVersion, DocumentNode]]:
        rows = db.query(NodeVersion).filter_by(doc_version_id=doc_version_id).all()
        result: dict[str, tuple[NodeVersion, DocumentNode]] = {}
        for nv in rows:
            node = db.get(DocumentNode, nv.node_id)
            if node:
                result[node.logical_id] = (nv, node)
        return result

    map_a = _build_map(ver_a.id)
    map_b = _build_map(ver_b.id)

    diffs: list[NodeDiff] = []
    common_ids = set(map_a.keys()) & set(map_b.keys())

    for lid in sorted(common_ids):
        nv_a, node_a = map_a[lid]
        nv_b, node_b = map_b[lid]

        if nv_a.content_hash != nv_b.content_hash:
            # Use the diff_summary stored in nv_b (computed at v2 ingestion time)
            diff_summary = nv_b.diff_summary

            # Fallback: compute diff on the fly if not stored
            if not diff_summary:
                import difflib
                old_lines = (f"{node_a.heading}\n{node_a.body_text or ''}").splitlines(keepends=True)
                # node_b already has v2 content (mutated in place during ingestion)
                new_lines = (f"{node_b.heading}\n{node_b.body_text or ''}").splitlines(keepends=True)
                raw = list(difflib.unified_diff(old_lines, new_lines,
                                                fromfile="old", tofile="new", lineterm=""))
                diff_summary = "".join(raw[:8]).strip()

            diffs.append(NodeDiff(
                node_id=node_b.id,
                logical_id=lid,
                heading=node_b.heading,
                version_a_tag=version_a,
                version_b_tag=version_b,
                changed=True,
                diff_summary=diff_summary or "Content changed",
            ))

    return diffs

