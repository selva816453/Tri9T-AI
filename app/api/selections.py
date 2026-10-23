"""
Selection API.

A selection is a named, version-pinned basket of document nodes.
Every SelectionItem records the node_id AND the doc_version_id it was
chosen from, so re-ingestion of a new version does not invalidate old
selections — they still resolve to the exact text they were created against.

Endpoints:
  POST /api/selections           – create a named selection
  GET  /api/selections           – list all selections
  GET  /api/selections/{id}      – get a selection with its items
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.db_models import (
    DocumentNode, DocumentVersion, Selection, SelectionItem,
)
from app.models.schemas import SelectionCreate, SelectionItemSchema, SelectionResponse

router = APIRouter(prefix="/api/selections", tags=["selections"])
logger = logging.getLogger(__name__)


@router.post("", response_model=SelectionResponse, status_code=201,
             summary="Create a version-pinned selection of nodes")
def create_selection(
    payload: SelectionCreate,
    db: Session = Depends(get_db),
):
    """
    Create a named selection.  The selection is pinned to a specific document
    version (doc_version_id).  Each node_id supplied must exist and must have
    appeared in that version.
    """
    # Validate version exists
    doc_ver = db.get(DocumentVersion, payload.doc_version_id)
    if not doc_ver:
        raise HTTPException(404, f"Document version '{payload.doc_version_id}' not found.")

    if not payload.node_ids:
        raise HTTPException(400, "node_ids must not be empty.")

    # Validate each node exists and appeared in this version
    from app.models.db_models import NodeVersion as NV
    pinned_hashes: dict[str, str] = {}
    for nid in payload.node_ids:
        node = db.get(DocumentNode, nid)
        if not node:
            raise HTTPException(404, f"Node '{nid}' not found.")
        nv = db.query(NV).filter_by(node_id=nid,
                                     doc_version_id=payload.doc_version_id).first()
        if not nv:
            raise HTTPException(
                422,
                f"Node '{nid}' did not appear in version '{payload.doc_version_id}'."
            )
        pinned_hashes[nid] = nv.content_hash

    # Create selection
    sel = Selection(
        name=payload.name,
        doc_version_id=payload.doc_version_id,
    )
    db.add(sel)
    db.flush()

    for nid in payload.node_ids:
        item = SelectionItem(
            selection_id=sel.id,
            node_id=nid,
            doc_version_id=payload.doc_version_id,
            pinned_hash=pinned_hashes[nid],
        )
        db.add(item)

    db.commit()
    db.refresh(sel)

    return SelectionResponse(
        id=sel.id,
        name=sel.name,
        doc_version_id=sel.doc_version_id,
        created_at=sel.created_at,
        items=[SelectionItemSchema(node_id=i.node_id,
                                   doc_version_id=i.doc_version_id)
               for i in sel.items],
    )


@router.get("", response_model=list[SelectionResponse], summary="List all selections")
def list_selections(
    doc_version_id: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(Selection)
    if doc_version_id:
        q = q.filter_by(doc_version_id=doc_version_id)
    sels = q.order_by(Selection.created_at.desc()).all()
    return [
        SelectionResponse(
            id=s.id,
            name=s.name,
            doc_version_id=s.doc_version_id,
            created_at=s.created_at,
            items=[SelectionItemSchema(node_id=i.node_id,
                                       doc_version_id=i.doc_version_id)
                   for i in s.items],
        )
        for s in sels
    ]


@router.get("/{selection_id}", response_model=SelectionResponse,
            summary="Get a selection by ID")
def get_selection(
    selection_id: str,
    db: Session = Depends(get_db),
):
    sel = db.get(Selection, selection_id)
    if not sel:
        raise HTTPException(404, f"Selection '{selection_id}' not found.")
    return SelectionResponse(
        id=sel.id,
        name=sel.name,
        doc_version_id=sel.doc_version_id,
        created_at=sel.created_at,
        items=[SelectionItemSchema(node_id=i.node_id,
                                   doc_version_id=i.doc_version_id)
               for i in sel.items],
    )
