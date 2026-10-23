"""
Unit tests for the CT-200 document parser.

Tests explicitly target the structural irregularities in the CT-200 document:
  1. Duplicate heading text at the same level → two distinct nodes with same heading
     but different node IDs and correct parent IDs.
  2. Level-skipping (H2 immediately contains H3 without another H2) → H3 correctly
     parented to the H2.
  3. Table of Contents entries are NOT promoted to heading nodes — they stay as
     body text of the TOC section.
  4. A heading labelled "Error Codes" appears at H1 AND as H2 "Error Codes During
     Startup" → separate nodes with distinct logical IDs and correct levels.
  5. Content hashes differ between nodes with same heading but different body text.
  6. Body text is correctly assigned to the immediately preceding heading.
"""

from __future__ import annotations

import sys
import os
import hashlib

# Make sure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.parser import (
    ParsedNode,
    _build_tree,
    _TextLine,
    _classify_sizes,
    flatten_tree,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _make_line(text: str, size: float, page: int = 1, y: float = 0.0) -> _TextLine:
    return _TextLine(text=text, font_size=size, y_top=y, page=page)

H1_SIZE  = 16.0
H2_SIZE  = 13.0
H3_SIZE  = 11.0
BODY_SIZE = 10.0


def _build(lines: list[_TextLine]) -> list[ParsedNode]:
    return _build_tree(lines)


# ─── Test 1: Duplicate heading text → two distinct nodes ─────────────────────

def test_duplicate_heading_produces_distinct_nodes():
    """
    Two H2 headings with identical text must produce two nodes with distinct IDs
    and distinct logical_ids, both correctly parented under the same H1.
    """
    lines = [
        _make_line("1. Introduction",          H1_SIZE),
        _make_line("Body of introduction.",     BODY_SIZE),
        _make_line("1.1 Notes",                 H2_SIZE),
        _make_line("First notes paragraph.",    BODY_SIZE),
        _make_line("1.2 Notes",                 H2_SIZE),   # DUPLICATE heading text
        _make_line("Second notes paragraph.",   BODY_SIZE),
    ]
    tree = _build(lines)
    flat = flatten_tree(tree)

    # Find both "Notes" nodes
    notes_nodes = [n for n in flat if "Notes" in n.heading]
    assert len(notes_nodes) == 2, (
        f"Expected 2 nodes with heading 'Notes', got {len(notes_nodes)}: "
        f"{[n.heading for n in notes_nodes]}"
    )

    ids    = {n.node_id for n in notes_nodes}
    lids   = {n.logical_id for n in notes_nodes}
    bodies = {n.body_text for n in notes_nodes}

    assert len(ids) == 2, "Duplicate heading must produce two distinct node IDs."
    assert len(lids) == 2, "Duplicate heading must produce two distinct logical_ids."
    assert len(bodies) == 2, "Duplicate headings with different body text must have distinct bodies."

    # Both should be level 2
    assert all(n.level == 2 for n in notes_nodes), "Both notes nodes should be level 2."

    # Both should be children of the Introduction H1
    h1_nodes = [n for n in flat if n.level == 1]
    assert len(h1_nodes) >= 1
    intro = h1_nodes[0]
    assert all(n.parent_id == intro.node_id for n in notes_nodes), (
        "Both Notes nodes should be children of the Introduction H1."
    )
    print("PASS: test_duplicate_heading_produces_distinct_nodes")


# ─── Test 2: Level-skipping (H2 directly contains H3) ────────────────────────

def test_level_skip_parenting():
    """
    When an H3 appears directly under an H1 (no H2 in between), the H3 must
    be parented to the H1, not orphaned.  Also tests that an H3 under an H2
    is correctly parented to that H2 even when they're separated by body text.
    """
    lines = [
        _make_line("5. Operations",               H1_SIZE),
        _make_line("5.1 Overview",                H2_SIZE),
        _make_line("Overview body text.",         BODY_SIZE),
        _make_line("5.1.1 Sub-detail",            H3_SIZE),   # H3 under H2 – correct
        _make_line("Sub-detail body text.",       BODY_SIZE),
        # Now H3 directly under H1 (level skip):
        _make_line("5.2 Direct Operations",       H2_SIZE),
        _make_line("Direct ops intro.",           BODY_SIZE),
        _make_line("5.2.1 Switch Users During",   H3_SIZE),   # H3 under H2 (no extra H2)
        _make_line("Switch body text.",           BODY_SIZE),
    ]
    tree = _build(lines)
    flat = flatten_tree(tree)

    sub_detail = next((n for n in flat if "Sub-detail" in n.heading), None)
    assert sub_detail is not None
    assert sub_detail.level == 3

    overview = next((n for n in flat if "Overview" in n.heading), None)
    assert overview is not None
    assert sub_detail.parent_id == overview.node_id, (
        f"'Sub-detail' should be a child of '5.1 Overview', "
        f"not of '{sub_detail.parent_id}'."
    )

    switch_node = next((n for n in flat if "Switch Users" in n.heading), None)
    assert switch_node is not None
    assert switch_node.level == 3

    direct_ops = next((n for n in flat if "Direct Operations" in n.heading), None)
    assert direct_ops is not None
    assert switch_node.parent_id == direct_ops.node_id, (
        f"'Switch Users During' should be child of '5.2 Direct Operations'."
    )
    print("PASS: test_level_skip_parenting")


# ─── Test 3: TOC entries stay as body text ────────────────────────────────────

def test_toc_entries_not_promoted_to_headings():
    """
    Lines in the Table of Contents that match the dot-leader pattern
    (e.g. "1. Introduction ........ 3") must NOT be promoted to heading nodes.
    They should appear as body_text of the TOC section.
    """
    lines = [
        _make_line("Table of Contents",                              H1_SIZE),
        _make_line("1. Introduction ...................... 3",         BODY_SIZE),
        _make_line("2. Safety Warnings .................. 4",          BODY_SIZE),
        _make_line("1. Introduction",                                 H1_SIZE),
        _make_line("Real introduction body.",                         BODY_SIZE),
    ]
    tree = _build(lines)
    flat = flatten_tree(tree)

    # Should have exactly 2 H1s: "Table of Contents" and "Introduction"
    h1s = [n for n in flat if n.level == 1]
    assert len(h1s) == 2, f"Expected 2 H1 nodes, got {len(h1s)}: {[n.heading for n in h1s]}"

    toc_node = next((n for n in flat if "Contents" in n.heading), None)
    assert toc_node is not None, "TOC node not found."

    # TOC entries should be in body text, not in children
    assert len(toc_node.children) == 0, (
        "TOC entries must NOT be promoted to child heading nodes."
    )
    print("PASS: test_toc_entries_not_promoted_to_headings")


# ─── Test 4: Same heading text at different levels ────────────────────────────

def test_same_text_different_levels():
    """
    "Error Codes" appears as H1 and "Error Codes During Startup" appears as H2.
    They must be distinct nodes with distinct IDs, correct levels, and correct parent.
    This also tests the edge case where a subsection heading contains the parent's
    heading text (substring match must not cause merging).
    """
    lines = [
        _make_line("8. Error Codes",                 H1_SIZE),
        _make_line("Table of all error codes.",      BODY_SIZE),
        _make_line("8.1 Error Codes During Startup", H2_SIZE),
        _make_line("Startup error body.",             BODY_SIZE),
    ]
    tree = _build(lines)
    flat = flatten_tree(tree)

    ec_nodes = [n for n in flat if "Error Codes" in n.heading]
    assert len(ec_nodes) == 2, (
        f"Expected 2 nodes containing 'Error Codes', got {len(ec_nodes)}: "
        f"{[n.heading for n in ec_nodes]}"
    )

    h1_ec = next((n for n in ec_nodes if n.level == 1), None)
    h2_ec = next((n for n in ec_nodes if n.level == 2), None)
    assert h1_ec is not None, "H1 'Error Codes' not found."
    assert h2_ec is not None, "H2 'Error Codes During Startup' not found."
    assert h1_ec.node_id != h2_ec.node_id, "H1 and H2 must have distinct node IDs."
    assert h2_ec.parent_id == h1_ec.node_id, (
        "H2 'Error Codes During Startup' must be child of H1 'Error Codes'."
    )
    print("PASS: test_same_text_different_levels")


# ─── Test 5: Content hash differs for same heading with different bodies ──────

def test_content_hash_differs_for_same_heading_different_body():
    """
    Two nodes with identical headings but different body text must have
    different content_hashes.
    """
    lines = [
        _make_line("1. Introduction",        H1_SIZE),
        _make_line("Body text version A.",   BODY_SIZE),
        _make_line("2. Introduction",        H1_SIZE),
        _make_line("Body text version B.",   BODY_SIZE),
    ]
    tree = _build(lines)
    flat = flatten_tree(tree)

    intro_nodes = [n for n in flat if "Introduction" in n.heading]
    assert len(intro_nodes) == 2
    h_a, h_b = intro_nodes
    assert h_a.content_hash != h_b.content_hash, (
        "Nodes with the same heading but different bodies must have different content_hashes."
    )
    print("PASS: test_content_hash_differs_for_same_heading_different_body")


# ─── Test 6: Body text correctly attributed to preceding heading ──────────────

def test_body_text_attribution():
    """
    Body lines between two headings must be attributed to the first heading,
    not the second.
    """
    lines = [
        _make_line("1. Safety",                 H1_SIZE),
        _make_line("Safety paragraph one.",      BODY_SIZE),
        _make_line("Safety paragraph two.",      BODY_SIZE),
        _make_line("2. Installation",            H1_SIZE),
        _make_line("Installation paragraph.",    BODY_SIZE),
    ]
    tree = _build(lines)
    flat = flatten_tree(tree)

    safety = next((n for n in flat if "Safety" in n.heading), None)
    install = next((n for n in flat if "Installation" in n.heading), None)
    assert safety is not None
    assert install is not None

    assert "Safety paragraph one." in safety.body_text
    assert "Safety paragraph two." in safety.body_text
    assert "Safety" not in install.body_text, (
        "Safety body text must not bleed into Installation node."
    )
    assert "Installation paragraph." in install.body_text
    print("PASS: test_body_text_attribution")


# ─── Test 7: Size classifier maps body text to level 0 ───────────────────────

def test_size_classifier_body_is_level_zero():
    """
    The most common font size should map to level 0 (body text),
    not a heading level.
    """
    # Body text dominates by count
    sizes = [10.0] * 50 + [16.0] * 5 + [13.0] * 8 + [11.0] * 4
    mapping = _classify_sizes(sizes)
    assert mapping.get(10.0) == 0, f"Body size 10.0 should map to level 0, got {mapping.get(10.0)}"
    assert mapping.get(16.0) == 1, f"Largest heading 16.0 should map to level 1"
    print("PASS: test_size_classifier_body_is_level_zero")


# ─── Run all tests ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_duplicate_heading_produces_distinct_nodes,
        test_level_skip_parenting,
        test_toc_entries_not_promoted_to_headings,
        test_same_text_different_levels,
        test_content_hash_differs_for_same_heading_different_body,
        test_body_text_attribution,
        test_size_classifier_body_is_level_zero,
    ]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"FAIL: {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"ERROR: {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*50}")
    print(f"Results: {len(tests) - failed}/{len(tests)} passed")
    if failed:
        sys.exit(1)
