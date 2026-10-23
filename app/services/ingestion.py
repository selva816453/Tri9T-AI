"""
Document ingestion service.

Responsibilities:
  1. Parse a PDF into a ParsedNode tree (via parser.py).
  2. Persist document versions, nodes, and node-version bridge rows to SQLite.
  3. Implement version-matching strategy: path-based logical_id matching.

Version-matching strategy (path-based):
  Nodes are matched across versions using their logical_id (e.g., "1.2.3"),
  which is computed from the heading prefix present in the document
  (e.g., "2.2 Cuff Pressure Safety" → logical_id "2.2").

  Why path-based?  The CT-200 manual has consistent section numbering in
  headings, making logical_id stable across minor edits.  Pure hash-based
  matching would fail when content changes (which is exactly when we *want*
  to match and flag a change).  Fuzzy title matching would falsely merge
  "Error Codes" (Section 8 H1) with "Error Codes During Startup" (Section 8.1 H2).

  Known failure modes of path-based matching:
  - Section renumbering between versions (e.g., inserting a new section 3 shifts
    everything after it): all nodes after the insertion would be treated as
    "new" even if their content is unchanged.
  - A heading whose prefix is not a number (e.g., "Appendix A") might collide
    if a new appendix is inserted before it.
  - The Table of Contents section has the same logical_id in every version; its
    content changes whenever any section is added — this may generate spurious
    "changed" flags for TOC nodes.

Diff summary:
  We store a lightweight diff summary (first 3 changed lines) produced by
  difflib.unified_diff.  This is stored in NodeVersion.diff_summary.
"""

from __future__ import annotations

import difflib
import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.db_models import (
    DocumentNode, DocumentVersion, NodeVersion,
)
from app.services.parser import ParsedNode, flatten_tree, parse_pdf

logger = logging.getLogger(__name__)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _short_diff(old_text: str, new_text: str, max_lines: int = 5) -> str:
    """Return a short unified diff string (at most max_lines changed lines)."""
    old_lines = old_text.splitlines(keepends=True)
    new_lines = new_text.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines,
                                     fromfile="old", tofile="new",
                                     lineterm=""))
    # Keep header + first max_lines change lines
    return "".join(diff[:max_lines + 3]).strip()


# ─── Core ingestion function ──────────────────────────────────────────────────

def ingest_document(
    db: Session,
    pdf_path: str,
    document_id: str,
    version_tag: str,
) -> DocumentVersion:
    """
    Parse a PDF and persist it as a new document version.

    Raises:
        ValueError – if (document_id, version_tag) already exists.
    """
    # Guard: no duplicate versions
    existing = db.query(DocumentVersion).filter_by(
        document_id=document_id, version_tag=version_tag
    ).first()
    if existing:
        raise ValueError(
            f"Version '{version_tag}' of document '{document_id}' already exists."
        )

    # 1. Parse PDF
    logger.info("Parsing PDF: %s", pdf_path)
    tree = parse_pdf(pdf_path)
    flat = flatten_tree(tree)
    logger.info("Extracted %d nodes", len(flat))

    # 2. Create DocumentVersion record
    doc_ver = DocumentVersion(
        document_id=document_id,
        version_tag=version_tag,
        file_name=pdf_path.split("/")[-1].split("\\")[-1],
        node_count=len(flat),
    )
    db.add(doc_ver)
    db.flush()   # get doc_ver.id before we use it

    # 3. Load previous version nodes (for matching + diff)
    prev_nodes: dict[str, DocumentNode] = _load_previous_nodes(db, document_id, version_tag)

    # 4. Persist nodes + node-version bridge rows
    id_map: dict[str, str] = {}   # ParsedNode.node_id → DocumentNode.id
    _persist_tree(db, flat, tree, doc_ver, prev_nodes, id_map)

    db.commit()
    logger.info("Ingestion complete: version %s (%d nodes)", version_tag, len(flat))
    return doc_ver


def _load_previous_nodes(
    db: Session,
    document_id: str,
    current_version_tag: str,
) -> dict[str, DocumentNode]:
    """
    Load the most recent previous version's nodes keyed by logical_id.
    Returns empty dict if this is the first version.
    """
    prev_ver = (
        db.query(DocumentVersion)
        .filter(DocumentVersion.document_id == document_id)
        .filter(DocumentVersion.version_tag != current_version_tag)
        .order_by(DocumentVersion.ingested_at.desc())
        .first()
    )
    if not prev_ver:
        return {}

    # Get all nodes that appeared in prev_ver
    nv_rows = (
        db.query(NodeVersion)
        .filter_by(doc_version_id=prev_ver.id)
        .all()
    )
    result: dict[str, DocumentNode] = {}
    for nv in nv_rows:
        node = db.get(DocumentNode, nv.node_id)
        if node:
            result[node.logical_id] = node
    return result


def _persist_tree(
    db: Session,
    flat: list[ParsedNode],
    tree: list[ParsedNode],          # top-level nodes (for parent resolution)
    doc_ver: DocumentVersion,
    prev_nodes: dict[str, DocumentNode],
    id_map: dict[str, str],
) -> None:
    """
    Persist every node from `flat` into the DB.
    Nodes matched by logical_id to a previous version reuse the existing
    DocumentNode row; new nodes get a fresh row.
    """
    # Build a local map: parsed_node_id → db_node for parent resolution
    parsed_to_db: dict[str, DocumentNode] = {}

    for pn in flat:
        # Resolve DB parent_id
        db_parent_id: Optional[str] = None
        if pn.parent_id:
            parent_db = parsed_to_db.get(pn.parent_id)
            db_parent_id = parent_db.id if parent_db else None

        matched = prev_nodes.get(pn.logical_id)

        if matched:
            # Reuse the existing DocumentNode row; update body/heading if changed
            changed = matched.content_hash != pn.content_hash
            if changed:
                old_text = f"{matched.heading}\n{matched.body_text}"
                new_text = f"{pn.heading}\n{pn.body_text}"
                diff_summary = _short_diff(old_text, new_text)
                matched.heading      = pn.heading
                matched.body_text    = pn.body_text
                matched.content_hash = pn.content_hash
            else:
                diff_summary = ""

            # Update tree position (parent/order might shift across versions)
            matched.parent_id   = db_parent_id
            matched.order_index = pn.order_index
            db_node = matched
        else:
            # Brand-new node
            changed = False
            diff_summary = ""
            db_node = DocumentNode(
                logical_id=pn.logical_id,
                heading=pn.heading,
                level=pn.level,
                body_text=pn.body_text,
                content_hash=pn.content_hash,
                parent_id=db_parent_id,
                order_index=pn.order_index,
                first_version_id=doc_ver.id,
            )
            db.add(db_node)
            db.flush()

        # Node-version bridge
        nv = NodeVersion(
            node_id=db_node.id,
            doc_version_id=doc_ver.id,
            content_hash=pn.content_hash,
            changed=changed,
            diff_summary=diff_summary,
        )
        db.add(nv)

        parsed_to_db[pn.node_id] = db_node
        id_map[pn.node_id] = db_node.id
