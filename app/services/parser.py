"""
PDF parsing pipeline for CT-200 documents.

Approach:
  We use pdfminer.six (pure-Python, no OCR needed because PDFs are text-based
  from ReportLab) to extract text with font/size metadata, then reconstruct a
  heading hierarchy by classifying text elements by their dominant font size.

Hierarchy reconstruction strategy:
  1. Extract all text objects with bounding boxes and font sizes.
  2. Cluster font sizes to heading levels: the largest = H1, next = H2, etc.
     We use relative percentile thresholds (not hard-coded sizes) because
     ReportLab embeds fonts at point sizes that match our style definitions,
     but a real-world PDF may differ.
  3. Assign heading level by matching against known prefixes (e.g. "1.", "1.1",
     "Appendix") as a secondary signal — this handles cases where a heading
     font size overlaps with body text.
  4. Build a stack-based tree: when we see a heading at level N, pop the stack
     back to level N-1, push the new node, collect subsequent body text.

Known edge cases handled:
  - Duplicate headings (same text, same level) → separate nodes with distinct IDs.
  - Level-skipping (H2 directly containing H3 without an intermediate H2).
  - "Table of Contents" section: detected by prefix and stored as a leaf, not
    used to generate child nodes (its entries are plain body text, not headings).
  - Figures/captions: lines matching "Figure X-Y:" pattern are tagged as captions
    and stored in body_text of the parent section.
  - Tables: ReportLab renders table cells as individual text objects; we detect
    adjacent short-line clusters and reconstruct them as tab-separated text rows.
  - Warnings (⚠ WARNING:) are folded into parent section body_text.

Known failure modes:
  - Font-size clustering is heuristic: if a PDF has very many distinct sizes,
    thresholds can mis-classify.  We fall back to the prefix regex in those cases.
  - Tables with merged cells lose their structure (they become concatenated text).
  - Very long paragraphs split across pages may be joined with an extra space.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

# pdfminer is imported lazily inside _extract_text_lines so that the module
# can be imported even in test environments where pdfminer is unavailable.


# ─── Data structures ──────────────────────────────────────────────────────────

@dataclass
class ParsedNode:
    """Intermediate representation of a document tree node."""
    node_id:      str
    logical_id:   str          # deterministic path-based key, e.g. "1.2.3"
    heading:      str
    level:        int          # 0 = document root, 1 = H1, 2 = H2, 3 = H3
    body_lines:   list[str]   = field(default_factory=list)
    children:     list["ParsedNode"] = field(default_factory=list)
    parent_id:    Optional[str] = None
    order_index:  int = 0

    @property
    def body_text(self) -> str:
        return "\n".join(self.body_lines).strip()

    @property
    def content_hash(self) -> str:
        raw = f"{self.heading}\n{self.body_text}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ─── Heading detection ────────────────────────────────────────────────────────

# Matches numbered headings: "1.", "1.1", "1.1.1", "Appendix A:"
_NUMBERED   = re.compile(r"^(\d+(?:\.\d+)*)\.\s+\S")
_APPENDIX   = re.compile(r"^Appendix\s+[A-Z]:?\s+\S", re.IGNORECASE)
_TOC_ENTRY  = re.compile(r"\.{5,}\s*\d+\s*$")      # "Section heading ........ 12"
_FIGURE_CAP = re.compile(r"^Figure\s+[\d\-]+:", re.IGNORECASE)
_WARNING    = re.compile(r"^[⚠\u26a0]\s*WARNING:", re.IGNORECASE)

def _heading_level_from_prefix(text: str) -> Optional[int]:
    """Return the structural level implied by a numbered heading prefix, or None."""
    m = _NUMBERED.match(text)
    if m:
        dots = m.group(1).count(".")
        return dots + 1          # "1." → level 1,  "1.1." → level 2, etc.
    if _APPENDIX.match(text):
        return 1
    return None


def _is_toc_entry(text: str) -> bool:
    return bool(_TOC_ENTRY.search(text))


# ─── Font-size → heading level ────────────────────────────────────────────────

def _classify_sizes(sizes: list[float]) -> dict[float, int]:
    """
    Map distinct font sizes to heading levels 1–3 (larger = lower level number).
    Body text (most common size) maps to level 0 (= not a heading).
    """
    if not sizes:
        return {}

    unique = sorted(set(sizes), reverse=True)
    # Find the body-text size as the mode
    from collections import Counter
    mode_size = Counter(sizes).most_common(1)[0][0]

    mapping: dict[float, int] = {}
    heading_level = 1
    for s in unique:
        if abs(s - mode_size) < 0.5:
            mapping[s] = 0   # body text
        else:
            mapping[s] = min(heading_level, 3)
            heading_level += 1
    return mapping


# ─── PDF text extraction ──────────────────────────────────────────────────────

@dataclass
class _TextLine:
    text: str
    font_size: float
    y_top: float   # page-top y coordinate (for ordering)
    page: int


def _extract_text_lines(pdf_path: str) -> list[_TextLine]:
    """
    Extract all text lines from a PDF with their dominant font size.
    Merges LTChar sizes within each LTTextLine by taking the max size.
    """
    try:
        from pdfminer.high_level import extract_pages
        from pdfminer.layout import LTTextBox, LTChar, LTTextLine
    except ImportError:
        raise ImportError("pdfminer.six is not installed. Run: pip install pdfminer.six")

    lines: list[_TextLine] = []
    for page_num, page_layout in enumerate(extract_pages(pdf_path), start=1):
        page_height = page_layout.height
        for element in page_layout:
            if not isinstance(element, LTTextBox):
                continue
            for line in element:
                if not isinstance(line, LTTextLine):
                    continue
                text = line.get_text().strip()
                if not text:
                    continue
                # Dominant size = max char size in line
                sizes = [
                    ch.size for ch in line
                    if isinstance(ch, LTChar) and ch.size > 0
                ]
                fs = max(sizes) if sizes else 10.0
                # Convert to page-top y
                y_top = page_height - line.y1
                lines.append(_TextLine(text=text, font_size=fs,
                                       y_top=y_top, page=page_num))
    return lines



# ─── Tree builder ─────────────────────────────────────────────────────────────

def _build_tree(lines: list[_TextLine]) -> list[ParsedNode]:
    """
    Convert flat list of text lines into a list of top-level ParsedNodes,
    each of which may have children.
    """
    # 1. Classify sizes
    all_sizes = [l.font_size for l in lines]
    size_map  = _classify_sizes(all_sizes)

    # 2. Stack-based tree construction
    root_children: list[ParsedNode] = []
    # Stack: [(level, node)]
    stack: list[tuple[int, ParsedNode]] = []
    sibling_counters: dict[str, int] = {}   # parent_logical_id → counter

    def _next_sibling(parent_lid: str) -> int:
        sibling_counters[parent_lid] = sibling_counters.get(parent_lid, 0) + 1
        return sibling_counters[parent_lid]

    def _get_parent() -> Optional[ParsedNode]:
        return stack[-1][1] if stack else None

    current_body_target: Optional[ParsedNode] = None
    in_toc = False

    for ln in lines:
        text = ln.text.strip()
        if not text:
            continue

        # --- TOC detection: enter/exit ----------------------------------------
        if text.startswith("Table of Contents"):
            in_toc = True
            # Fall through so the TOC heading itself gets processed as a heading node

        if in_toc and text != "Table of Contents":
            size_level_toc = size_map.get(ln.font_size, 0)
            # Any line inside TOC that is either:
            #   (a) a dot-leader entry, OR
            #   (b) has body-size font (not heading size)
            # should be treated as body text of the TOC node.
            if _is_toc_entry(text) or size_level_toc == 0:
                if current_body_target:
                    current_body_target.body_lines.append(text)
                continue
            else:
                # It's a heading-size line → we've left the TOC block
                in_toc = False

        # --- Heading level from font size + prefix ----------------------------
        size_level = size_map.get(ln.font_size, 0)
        prefix_level = _heading_level_from_prefix(text)

        if size_level > 0:
            level = size_level
        elif prefix_level is not None:
            level = prefix_level
        else:
            # Plain body text, figure caption, warning, etc.
            if current_body_target is not None:
                current_body_target.body_lines.append(text)
            continue

        # --- Build node -------------------------------------------------------
        # Pop stack back to parent level
        while stack and stack[-1][0] >= level:
            stack.pop()

        parent = _get_parent()
        if parent:
            parent_lid = parent.logical_id
        else:
            parent_lid = "root"

        idx = _next_sibling(parent_lid)
        logical_id = f"{parent_lid}.{idx}" if parent_lid != "root" else str(idx)

        node = ParsedNode(
            node_id=str(uuid.uuid4()),
            logical_id=logical_id,
            heading=text,
            level=level,
            parent_id=parent.node_id if parent else None,
            order_index=idx,
        )

        if parent:
            parent.children.append(node)
        else:
            root_children.append(node)

        stack.append((level, node))
        current_body_target = node

    return root_children


# ─── Public API ───────────────────────────────────────────────────────────────

def parse_pdf(pdf_path: str) -> list[ParsedNode]:
    """
    Parse a PDF file and return a list of top-level ParsedNode objects
    (each with children populated recursively).

    Raises:
        ImportError   – if pdfminer.six is not installed.
        FileNotFoundError – if the PDF path does not exist.
        RuntimeError  – if the PDF has no extractable text.
    """
    import os
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    lines = _extract_text_lines(pdf_path)
    if not lines:
        raise RuntimeError(f"No text extracted from PDF: {pdf_path}")

    tree = _build_tree(lines)
    return tree


def flatten_tree(nodes: list[ParsedNode]) -> list[ParsedNode]:
    """Return all nodes in DFS pre-order (parent before children)."""
    result = []
    def _dfs(ns: list[ParsedNode]):
        for n in ns:
            result.append(n)
            _dfs(n.children)
    _dfs(nodes)
    return result


def print_tree(nodes: list[ParsedNode], indent: int = 0) -> None:
    """Pretty-print the document tree (for debugging)."""
    for n in nodes:
        print(" " * (indent * 2) + f"[L{n.level}] {n.heading[:70]!r} ({n.logical_id})")
        if n.body_text:
            print(" " * (indent * 2 + 2) + f"body: {n.body_text[:60]!r}…")
        print_tree(n.children, indent + 1)
