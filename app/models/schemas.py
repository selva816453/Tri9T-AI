"""
Pydantic response schemas for the API.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# ─── Document / Node ──────────────────────────────────────────────────────────

class NodeBase(BaseModel):
    id:           str
    logical_id:   str
    heading:      str
    level:        int
    content_hash: str
    order_index:  int

    class Config:
        from_attributes = True


class NodeSummary(NodeBase):
    """Lightweight node used in listings."""
    child_count: int = 0
    parent_id:   Optional[str] = None


class NodeDetail(NodeBase):
    """Full node with body text and children."""
    body_text:   str
    parent_id:   Optional[str] = None
    children:    list[NodeSummary] = []


class VersionSummary(BaseModel):
    id:          str
    version_tag: str
    file_name:   Optional[str]
    ingested_at: datetime
    node_count:  int

    class Config:
        from_attributes = True


class IngestResponse(BaseModel):
    message:     str
    version:     VersionSummary


# ─── Diff / Change detection ──────────────────────────────────────────────────

class NodeDiff(BaseModel):
    node_id:         str
    logical_id:      str
    heading:         str
    version_a_tag:   str
    version_b_tag:   str
    changed:         bool
    diff_summary:    Optional[str] = None


# ─── Selections ───────────────────────────────────────────────────────────────

class SelectionItemSchema(BaseModel):
    node_id:        str
    doc_version_id: str


class SelectionCreate(BaseModel):
    name:           str
    doc_version_id: str
    node_ids:       list[str]


class SelectionResponse(BaseModel):
    id:             str
    name:           str
    doc_version_id: str
    created_at:     datetime
    items:          list[SelectionItemSchema]

    class Config:
        from_attributes = True


# ─── Generations / Test Cases ─────────────────────────────────────────────────

class TestCaseSchema(BaseModel):
    id:               str
    title:            str
    preconditions:    str
    steps:            list[str]
    expected_result:  str
    requirement_ref:  str


class StalenessInfo(BaseModel):
    """Per-node staleness detail."""
    node_id:      str
    logical_id:   str
    heading:      str
    is_stale:     bool
    current_hash: str
    pinned_hash:  str
    diff_summary: Optional[str] = None


class GenerationResponse(BaseModel):
    generation_id:  str
    selection_id:   str
    status:         str            # "ok" | "partial_error" | "mock"
    test_cases:     list[TestCaseSchema]
    error_detail:   Optional[str] = None
    created_at:     datetime
    # Staleness
    is_stale:       bool
    stale_nodes:    list[StalenessInfo] = []


class GenerationListItem(BaseModel):
    generation_id:  str
    selection_id:   str
    status:         str
    test_case_count: int
    created_at:     datetime
    is_stale:       bool
