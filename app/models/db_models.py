"""
CT-200 QA System – SQLAlchemy + SQLite data models.

Design decisions:
- DocumentVersion  : immutable record per ingestion run (version_tag + semver)
- DocumentNode     : every heading/section. Soft-deleted never removed so old
                     selections still resolve.  content_hash (SHA-256 of heading+body)
                     is the staleness anchor.
- NodeVersion      : bridge – which node appears in which doc version and whether
                     it changed.  logical_id groups the same "logical" section across
                     versions (matched by path-based strategy).
- Selection        : a named, version-pinned basket of node+version pairs.
- SelectionItem    : each pinned node in a selection.
- Generation       : LLM output linked to a selection + the exact content hashes
                     at generation time (needed for staleness checks).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, DateTime, ForeignKey, Integer, String, Text, Boolean, Float,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


# ─── Document versioning ──────────────────────────────────────────────────────

class DocumentVersion(Base):
    """One ingestion run = one version of the document."""
    __tablename__ = "document_versions"

    id          = Column(String(36), primary_key=True, default=_uuid)
    document_id = Column(String(80), nullable=False, index=True)   # e.g. "CT200-MAN-001"
    version_tag = Column(String(50), nullable=False)               # e.g. "1.0", "2.0"
    file_name   = Column(String(200))
    ingested_at = Column(DateTime, default=_now, nullable=False)
    node_count  = Column(Integer, default=0)

    __table_args__ = (
        UniqueConstraint("document_id", "version_tag", name="uq_doc_version"),
    )

    # relationships
    node_versions = relationship("NodeVersion", back_populates="doc_version",
                                 cascade="all, delete-orphan")


# ─── Tree nodes ───────────────────────────────────────────────────────────────

class DocumentNode(Base):
    """
    One heading/section in the document.  A node is NEVER deleted so that
    version-pinned selections always resolve.

    logical_id  – groups the same conceptual section across versions.
                  Set during ingestion by the path-matching strategy.
    content_hash – SHA-256(heading + body).  Staleness is detected when this
                   differs between the version a generation was created against
                   and the current version.
    """
    __tablename__ = "document_nodes"

    id           = Column(String(36), primary_key=True, default=_uuid)
    logical_id   = Column(String(80), nullable=False, index=True)
    heading      = Column(String(500), nullable=False)
    level        = Column(Integer, nullable=False)     # 1=H1, 2=H2, 3=H3 …
    body_text    = Column(Text, default="")
    content_hash = Column(String(64), nullable=False)  # hex SHA-256

    # Tree structure (self-referential)
    parent_id    = Column(String(36), ForeignKey("document_nodes.id"), nullable=True)
    order_index  = Column(Integer, default=0)          # sibling order within parent

    # Which doc version this node was first seen in
    first_version_id = Column(String(36), ForeignKey("document_versions.id"),
                               nullable=False)

    parent   = relationship("DocumentNode", remote_side="DocumentNode.id",
                            back_populates="children")
    children = relationship("DocumentNode", back_populates="parent",
                            order_by="DocumentNode.order_index")

    first_version = relationship("DocumentVersion", foreign_keys=[first_version_id])
    node_versions = relationship("NodeVersion", back_populates="node",
                                 cascade="all, delete-orphan")
    selection_items = relationship("SelectionItem", back_populates="node")


class NodeVersion(Base):
    """
    Tracks which nodes are present in each document version and whether they
    changed from the previous version.

    changed       – True when content_hash differs from the previous version's node.
    diff_summary  – lightweight text diff stored at ingestion time.
    """
    __tablename__ = "node_versions"

    id             = Column(String(36), primary_key=True, default=_uuid)
    node_id        = Column(String(36), ForeignKey("document_nodes.id"),
                             nullable=False, index=True)
    doc_version_id = Column(String(36), ForeignKey("document_versions.id"),
                             nullable=False, index=True)
    content_hash   = Column(String(64), nullable=False)
    changed        = Column(Boolean, default=False)
    diff_summary   = Column(Text, default="")          # "" if unchanged

    __table_args__ = (
        UniqueConstraint("node_id", "doc_version_id", name="uq_node_docversion"),
    )

    node        = relationship("DocumentNode", back_populates="node_versions")
    doc_version = relationship("DocumentVersion", back_populates="node_versions")


# ─── Selections ───────────────────────────────────────────────────────────────

class Selection(Base):
    """
    A named, version-pinned basket of document nodes.

    version-pinned means each SelectionItem records BOTH the node_id AND the
    doc_version_id it was chosen from, so re-ingestion doesn't corrupt old
    selections.
    """
    __tablename__ = "selections"

    id             = Column(String(36), primary_key=True, default=_uuid)
    name           = Column(String(200), nullable=False)
    doc_version_id = Column(String(36), ForeignKey("document_versions.id"),
                             nullable=False, index=True)
    created_at     = Column(DateTime, default=_now, nullable=False)

    doc_version = relationship("DocumentVersion")
    items       = relationship("SelectionItem", back_populates="selection",
                               cascade="all, delete-orphan")
    generations = relationship("Generation", back_populates="selection")


class SelectionItem(Base):
    """One node pinned inside a selection."""
    __tablename__ = "selection_items"

    id             = Column(String(36), primary_key=True, default=_uuid)
    selection_id   = Column(String(36), ForeignKey("selections.id"),
                             nullable=False, index=True)
    node_id        = Column(String(36), ForeignKey("document_nodes.id"),
                             nullable=False)
    doc_version_id = Column(String(36), ForeignKey("document_versions.id"),
                             nullable=False)
    # Snapshot of hash at pin time – the staleness anchor.
    pinned_hash    = Column(String(64), nullable=False)

    selection = relationship("Selection", back_populates="items")
    node      = relationship("DocumentNode", back_populates="selection_items")
    doc_version = relationship("DocumentVersion")


# ─── LLM Generations (metadata in SQL; full output in MongoDB) ────────────────

class Generation(Base):
    """
    SQL metadata for an LLM generation run.  Full JSON output lives in MongoDB.
    The mongo_id column is the ObjectId string referencing the MongoDB document.

    content_snapshot_hashes – pipe-separated list of content_hash values of all
    pinned nodes at generation time.  Used later to detect staleness: if any of
    those hashes no longer matches the current version of the node, the generation
    is flagged as potentially stale.

    Policy on duplicate submissions: if the same selection_id is submitted again,
    we create a NEW generation (idempotent: caller always gets fresh output).
    The old generation is preserved with its original staleness state.  The API
    returns both in the retrieval endpoint with generation timestamps so callers
    can distinguish them.
    """
    __tablename__ = "generations"

    id                       = Column(String(36), primary_key=True, default=_uuid)
    selection_id             = Column(String(36), ForeignKey("selections.id"),
                                      nullable=False, index=True)
    mongo_id                 = Column(String(36), nullable=True)   # set after Mongo write
    content_snapshot_hashes  = Column(Text, nullable=False)        # "|"-separated hashes
    created_at               = Column(DateTime, default=_now, nullable=False)

    # Staleness is recomputed at query time; cached here for quick listing.
    is_stale                 = Column(Boolean, default=False)
    stale_nodes              = Column(Text, default="")            # "|"-sep node_ids

    selection = relationship("Selection", back_populates="generations")
