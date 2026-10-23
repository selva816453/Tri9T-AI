"""
Generate a professional, publication-quality Approach Document PDF for the Tri9T AI Internship Assignment.
Uses ReportLab to render typography, tables, callout blocks, and embedded dashboard screenshots.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, KeepTogether, Image
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY, TA_RIGHT
from reportlab.pdfgen import canvas

PAGE_W, PAGE_H = A4  # 595.27 x 841.89 points
MARGIN = 46
CONTENT_W = PAGE_W - 2 * MARGIN  # 503.27 points

class NumberedCanvas(canvas.Canvas):
    """Two-pass canvas to dynamically compute and stamp total page count and headers."""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#555555"))

        # Header (Pages 2+) - use standard ASCII hyphen to avoid Helvetica encoding issues
        if self._pageNumber > 1:
            self.drawString(MARGIN, PAGE_H - 34, "CT-200 QA Document System - Architectural Approach Document")
            self.drawRightString(PAGE_W - MARGIN, PAGE_H - 34, "Tri9T AI Internship Assignment")
            self.setStrokeColor(colors.HexColor("#cccccc"))
            self.setLineWidth(0.5)
            self.line(MARGIN, PAGE_H - 38, PAGE_W - MARGIN, PAGE_H - 38)

        # Footer (All pages)
        self.setStrokeColor(colors.HexColor("#cccccc"))
        self.setLineWidth(0.5)
        self.line(MARGIN, 40, PAGE_W - MARGIN, 40)
        self.drawString(MARGIN, 28, "Tri9T AI - AI Engineering Assignment | Author: Selvam M (selva816453)")
        self.drawRightString(PAGE_W - MARGIN, 28, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()


def build_styles():
    base = getSampleStyleSheet()

    def add(name, parent="Normal", **kw):
        base.add(ParagraphStyle(name=name, parent=base[parent], **kw))

    # Curated Professional Palette
    C_PRIMARY   = colors.HexColor("#0f3460")
    C_SECONDARY = colors.HexColor("#16213e")
    C_ACCENT    = colors.HexColor("#e94560")
    C_PURPLE    = colors.HexColor("#533483")
    C_TEXT      = colors.HexColor("#222222")
    C_MUTED     = colors.HexColor("#555555")

    add("DocTitle", parent="Title", fontSize=20, leading=24, alignment=TA_CENTER, textColor=C_PRIMARY, fontName="Helvetica-Bold")
    add("DocSubtitle", fontSize=10.5, leading=14, alignment=TA_CENTER, textColor=C_PURPLE, fontName="Helvetica-Bold")
    add("MetaBadge", fontSize=8, leading=12, alignment=TA_CENTER, textColor=C_MUTED)

    add("SecH1", parent="Heading1", fontSize=12, leading=15, spaceBefore=10, spaceAfter=4, textColor=C_PRIMARY, fontName="Helvetica-Bold", keepWithNext=True)
    add("SecH2", parent="Heading2", fontSize=9.5, leading=13, spaceBefore=6, spaceAfter=2, textColor=C_PURPLE, fontName="Helvetica-Bold", keepWithNext=True)

    add("BodyJ", parent="Normal", fontSize=8, leading=11.5, spaceAfter=4, alignment=TA_JUSTIFY, textColor=C_TEXT)
    add("BodyL", parent="Normal", fontSize=8, leading=11.5, spaceAfter=4, alignment=TA_LEFT, textColor=C_TEXT)
    add("BulletText", parent="Normal", fontSize=8, leading=11.2, spaceAfter=2.5, textColor=C_TEXT)
    
    add("CalloutBox", parent="Normal", fontSize=8, leading=11.5, textColor=colors.HexColor("#1b4332"),
        backColor=colors.HexColor("#edf7f2"), borderColor=colors.HexColor("#2d6a4f"),
        borderWidth=0.8, borderPadding=5, spaceAfter=5)

    add("ImgCaption", parent="Normal", fontSize=7.5, leading=9.5, alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"), fontName="Helvetica-Oblique", spaceAfter=5)

    add("TblHeader", parent="Normal", fontSize=7.5, leading=9.5, fontName="Helvetica-Bold",
        textColor=colors.white, alignment=TA_CENTER)
    add("TblCell", parent="Normal", fontSize=7.2, leading=9.5, textColor=C_TEXT)
    add("TblCellBold", parent="Normal", fontSize=7.2, leading=9.5, fontName="Helvetica-Bold", textColor=C_PRIMARY)

    return base


def create_approach_pdf(output_path="Approach_Document.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=46,
        bottomMargin=48,
    )

    S = build_styles()
    story = []

    # ─── HEADER / BANNER BLOCK ────────────────────────────────────────────────
    story.append(Paragraph("CT-200 QA DOCUMENT SYSTEM", S["DocTitle"]))
    story.append(Paragraph("Engineering Approach, System Architecture & Technical Decision Log", S["DocSubtitle"]))
    story.append(Spacer(1, 2))
    
    meta_text = (
        "<b>AI Engineering Internship Assignment - Tri9T AI</b> &nbsp;|&nbsp; "
        "<b>Author:</b> Selvam M &nbsp;|&nbsp; "
        "<b>Date:</b> October 2026<br/>"
        "<b>GitHub Repository:</b> <font color='#0f3460'><u>https://github.com/selva816453/Tri9T-AI</u></font>"
    )
    story.append(Paragraph(meta_text, S["MetaBadge"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#0f3460"), spaceAfter=6))

    # ─── 1. EXECUTIVE SUMMARY ────────────────────────────────────────────────
    story.append(Paragraph("1. Executive Summary & Problem Scope", S["SecH1"]))
    story.append(Paragraph(
        "Medical device documentation (e.g. the CardioTrack CT-200 Blood Pressure Monitor) undergoes continuous regulatory "
        "and technical revisions. In traditional QA workflows, manual tracking of document changes against test suites is error-prone, "
        "slow, and non-compliant with standards such as ISO 13485 and IEC 62304. The <b>CT-200 QA Document System</b> provides "
        "an automated, end-to-end platform that parses multi-page medical PDFs into structured hierarchical trees, reconciles changes "
        "across revisions, supports version-pinned requirement selection, and generates LLM-powered test suites with "
        "<b>automatic retrieval-time staleness detection</b>.",
        S["BodyJ"]
    ))

    callout_html = (
        "<b>Core Implementation Highlights:</b><br/>"
        "• <b>Deterministic Parser:</b> Pure-Python extraction using <code>pdfminer.six</code>; font clustering + prefix heuristics reconstruct trees.<br/>"
        "• <b>Path-Based Versioning:</b> Relates nodes across v1.0 and v2.0 using <code>logical_id</code> (e.g., '2.2') and generates unified diffs.<br/>"
        "• <b>Staleness Detection Engine:</b> Captures snapshot hashes and flags test cases as STALE immediately when manual parameters change.<br/>"
        "• <b>Structured LLM Pipeline:</b> Groq (Llama-3.3-70b) integration with Pydantic schema validation, regex fallback, and offline mock support."
    )
    story.append(Paragraph(callout_html, S["CalloutBox"]))

    # ─── 2. SYSTEM ARCHITECTURE ──────────────────────────────────────────────
    story.append(Paragraph("2. System Architecture & Layered Design", S["SecH1"]))
    story.append(Paragraph(
        "The system is organized into decoupled layers ensuring high modularity, testability, and resilience:",
        S["BodyJ"]
    ))

    arch_data = [
        [Paragraph("Layer", S["TblHeader"]), Paragraph("Technology Stack", S["TblHeader"]), Paragraph("Core Functionality & Guarantees", S["TblHeader"])],
        [
            Paragraph("API & Web UI", S["TblCellBold"]),
            Paragraph("FastAPI, Uvicorn, Vanilla HTML5/CSS/JS", S["TblCell"]),
            Paragraph("Interactive Swagger docs and dark-mode management dashboard for tree browsing, diffs, and test case monitoring.", S["TblCell"])
        ],
        [
            Paragraph("PDF Parsing", S["TblCellBold"]),
            Paragraph("pdfminer.six, regex, ReportLab", S["TblCell"]),
            Paragraph("Extracts text/font metadata; clusters font sizes (H1-H3); parses TOC, tables, captions, and safety warnings.", S["TblCell"])
        ],
        [
            Paragraph("Versioning Engine", S["TblCellBold"]),
            Paragraph("Path-based matcher, difflib, SHA-256", S["TblCell"]),
            Paragraph("Ingests immutable version snapshots; correlates nodes by logical_id; calculates line-level unified diffs.", S["TblCell"])
        ],
        [
            Paragraph("LLM & Staleness", S["TblCellBold"]),
            Paragraph("Groq (llama-3.3-70b), Pydantic v2", S["TblCell"]),
            Paragraph("Generates structured QA test cases; captures SHA-256 snapshots; invalidates test cases dynamically upon retrieval.", S["TblCell"])
        ],
        [
            Paragraph("Hybrid Persistence", S["TblCellBold"]),
            Paragraph("SQLite (SQLAlchemy) + MongoDB / JSON", S["TblCell"]),
            Paragraph("Relational schema for document nodes, versions, and selections; document store with JSON fallback for test case payloads.", S["TblCell"])
        ],
    ]
    t_arch = Table(arch_data, colWidths=[75, 140, CONTENT_W - 215])
    t_arch.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ('TOPPADDING', (0, 0), (-1, -1), 2.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2.5),
    ]))
    story.append(t_arch)
    story.append(Spacer(1, 4))

    # ─── 3. PDF PARSING & TREE RECONSTRUCTION ────────────────────────────────
    story.append(Paragraph("3. PDF Parsing & Document Tree Reconstruction", S["SecH1"]))
    story.append(Paragraph(
        "PDF is a display format lacking native semantic structure (no <code>&lt;h1&gt;</code> tags). Our parser in "
        "<code>app/services/parser.py</code> uses a dual-signal classification strategy:",
        S["BodyJ"]
    ))
    story.append(Paragraph("• <b>Font-Size Clustering:</b> Extracts text runs with bounding boxes and font sizes. Percentile clustering dynamically identifies H1 (e.g. 16pt), H2 (13pt), and H3 (11pt) without brittle hardcoded sizes.", S["BulletText"]))
    story.append(Paragraph("• <b>Numbered Prefix Regex:</b> Matches patterns such as <code>^(\\d+(?:\\.\\d+)*)\\.\\s+\\S</code> and <code>Appendix</code>. The dot count deterministically defines hierarchy depth.", S["BulletText"]))
    story.append(Paragraph("• <b>Stack-Based Hierarchy Builder:</b> Sequential traversal pushes and pops nodes on an active stack to assemble accurate parent-child relationships.", S["BulletText"]))
    story.append(Paragraph("• <b>Edge Cases Handled:</b> Duplicate section titles receive distinct UUIDs and logical IDs; level-skipping (H1 to H3) is bridged without node loss; TOC leader dots (<code>...... 12</code>) are isolated; and <code>⚠ WARNING:</code> blocks are attached to their parent section.", S["BulletText"]))

    story.append(Spacer(1, 4))

    # ─── 4. VERSIONING & CROSS-VERSION NODE MATCHING ──────────────────────────
    story.append(Paragraph("4. Versioning & Cross-Version Node Matching", S["SecH1"]))
    story.append(Paragraph(
        "When an updated manual (e.g. v2.0) is ingested alongside v1.0, sections must be matched to detect modifications:",
        S["BodyJ"]
    ))
    story.append(Paragraph(
        "• <b>Path-Based Matching (<code>logical_id</code>):</b> Nodes are linked across versions using their hierarchical path (e.g. <code>2.2</code>). "
        "Medical device manuals follow disciplined section numbering. Content hash matching fails whenever text changes (precisely when diffing is required), "
        "while fuzzy string matching erroneously conflates distinct sections like 'Error Codes' and 'Error Codes During Startup'.",
        S["BodyJ"]
    ))
    story.append(Paragraph(
        "• <b>Content Hashing & Unified Diffs:</b> Each node's content is hashed via SHA-256 over <code>heading + '\\n' + body_text</code>. "
        "When hashes differ between versions, <code>difflib.unified_diff</code> generates a concise diff summary stored in "
        "<code>node_versions.diff_summary</code> (e.g., highlighting cuff limit revision: 300 mmHg → 320 mmHg).",
        S["BodyJ"]
    ))

    # ─── 5. SELECTION PINNING & STALENESS DETECTION ───────────────────────────
    story.append(Paragraph("5. Selection Pinning & Staleness Detection Engine", S["SecH1"]))
    story.append(Paragraph(
        "• <b>Immutable Version Pinning:</b> Selections permanently bind to a specific <code>doc_version_id</code>. Ingesting future versions "
        "never mutates or silently shifts an existing selection, ensuring reproducible audit baselines.<br/>"
        "• <b>Content Snapshot Hashing:</b> Generating test cases captures an immutable snapshot array of the SHA-256 hashes of all selected nodes.<br/>"
        "• <b>Retrieval-Time Invalidation:</b> Upon <code>GET /api/generations/{id}</code>, current node hashes are compared against snapshot hashes. "
        "If any hash differs, <b><code>is_stale: true</code></b> is returned with detailed <code>StalenessInfo</code> and exact diff text.<br/>"
        "• <b>Append-Only Submission:</b> Re-submitting the same selection creates a new generation record rather than overwriting, preserving audit history.",
        S["BodyL"]
    ))

    # ─── 6. LLM TEST CASE GENERATION ─────────────────────────────────────────
    story.append(Paragraph("6. LLM Test Case Generation & Reliability", S["SecH1"]))
    story.append(Paragraph(
        "• <b>Inference Engine:</b> Groq API with <code>llama-3.3-70b-versatile</code> for high-throughput, structured output.<br/>"
        "• <b>ISO 13485 / IEC 62304 Persona:</b> Prompts instruct the model to produce concrete, executable test steps with explicit acceptance criteria.<br/>"
        "• <b>Traceability Anchor:</b> Every test case features a mandatory <code>requirement_ref</code> linking directly to the manual section heading.<br/>"
        "• <b>Fault Tolerance:</b> Pydantic schema validation is backed by regex JSON extraction. Schema mismatches degrade gracefully to "
        "<code>partial_error</code> with raw text preserved. If <code>GROQ_API_KEY</code> is absent, deterministic mock generation enables offline development.",
        S["BodyL"]
    ))

    # ─── 7. DATABASE ARCHITECTURE ────────────────────────────────────────────
    story.append(Paragraph("7. Database Architecture & Hybrid Persistence", S["SecH1"]))
    story.append(Paragraph(
        "The storage architecture uses SQLite for structured relational integrity and MongoDB (with JSON fallback) for test payloads:",
        S["BodyJ"]
    ))

    db_data = [
        [Paragraph("Table / Entity", S["TblHeader"]), Paragraph("Database", S["TblHeader"]), Paragraph("Schema Fields & Purpose", S["TblHeader"])],
        [
            Paragraph("DocumentVersion", S["TblCellBold"]),
            Paragraph("SQLite", S["TblCell"]),
            Paragraph("id, document_id, version_tag, file_name, node_count, ingested_at. Tracks immutable version records.", S["TblCell"])
        ],
        [
            Paragraph("DocumentNode", S["TblCellBold"]),
            Paragraph("SQLite", S["TblCell"]),
            Paragraph("node_id, logical_id, heading, level, body_text, parent_id, order_index, content_hash.", S["TblCell"])
        ],
        [
            Paragraph("NodeVersion", S["TblCellBold"]),
            Paragraph("SQLite", S["TblCell"]),
            Paragraph("Bridge table (node_id, doc_version_id), is_changed boolean, diff_summary unified diff text.", S["TblCell"])
        ],
        [
            Paragraph("Selection & Items", S["TblCellBold"]),
            Paragraph("SQLite", S["TblCell"]),
            Paragraph("selection_id, doc_version_id (pinned), name, created_at. Binds user selections to exact versions.", S["TblCell"])
        ],
        [
            Paragraph("Generation", S["TblCellBold"]),
            Paragraph("SQLite + NoSQL", S["TblCell"]),
            Paragraph("generation_id, selection_id, status, content_snapshot_hashes. Full JSON test cases stored in MongoDB / JSON fallback.", S["TblCell"])
        ],
    ]
    t_db = Table(db_data, colWidths=[85, 70, CONTENT_W - 155])
    t_db.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t_db)

    # ─── 8. VERIFICATION & SCREENSHOTS ───────────────────────────────────────
    story.append(Spacer(1, 4))
    story.append(Paragraph("8. Verification & System Demonstration", S["SecH1"]))
    story.append(Paragraph(
        "• <b>Unit Test Suite:</b> All 7 tests in <code>tests/test_parser.py</code> pass (duplicate headings, level-skipping, TOC filtering, table rows, captions, hash stability).<br/>"
        "• <b>End-to-End Workflow:</b> <code>scripts/e2e_demo.py</code> successfully demonstrates v1.0 ingestion (145 nodes), v2.0 ingestion (149 nodes), selection pinning, and live staleness invalidation when cuff safety thresholds change from 300 to 320 mmHg.",
        S["BodyL"]
    ))

    # Screenshots scaled cleanly
    img_dir = "Output"
    s1_path = os.path.join(img_dir, "Screenshot 2026-10-23 191820.png")
    s2_path = os.path.join(img_dir, "Screenshot 2026-10-23 191846.png")
    
    img_w = 440
    img_h = 440 / 1.78  # ~247 pt

    if os.path.exists(s1_path):
        story.append(KeepTogether([
            Image(s1_path, width=img_w, height=img_h),
            Paragraph("Figure 1: CT-200 QA System Overview Dashboard - Live Health, Document Versions, and Node Metrics", S["ImgCaption"])
        ]))

    if os.path.exists(s2_path):
        story.append(KeepTogether([
            Image(s2_path, width=img_w, height=img_h),
            Paragraph("Figure 2: Staleness Invalidation in Action - Flagging STALE Test Cases with Exact Line-Level Parameter Diffs", S["ImgCaption"])
        ]))

    # ─── 9. DECISION LOG & TRADE-OFF MATRIX ──────────────────────────────────
    story.append(Paragraph("9. Architectural Decision Log & Trade-Off Matrix", S["SecH1"]))
    story.append(Paragraph(
        "The following matrix summarizes key technical trade-offs evaluated during system design:",
        S["BodyJ"]
    ))

    dec_data = [
        [Paragraph("Decision Point", S["TblHeader"]), Paragraph("Alternatives Considered", S["TblHeader"]), Paragraph("Selected Approach", S["TblHeader"]), Paragraph("Trade-Off Rationale", S["TblHeader"])],
        [
            Paragraph("Node Matching Strategy", S["TblCellBold"]),
            Paragraph("Content Hash / Fuzzy Title Match", S["TblCell"]),
            Paragraph("<b>Path-based (logical_id)</b>", S["TblCell"]),
            Paragraph("Content hashing fails upon any text edit; fuzzy matching conflates distinct sections. Path IDs reflect numbering discipline in manuals.", S["TblCell"])
        ],
        [
            Paragraph("Staleness Semantics", S["TblCellBold"]),
            Paragraph("Semantic LLM diff / Embeddings", S["TblCell"]),
            Paragraph("<b>SHA-256 Hash + Unified Diff</b>", S["TblCell"]),
            Paragraph("Medical compliance requires absolute determinism. Embeddings can miss critical numeric shifts (300 to 320 mmHg).", S["TblCell"])
        ],
        [
            Paragraph("Selection Versioning", S["TblCellBold"]),
            Paragraph("Floating pointer (always latest)", S["TblCell"]),
            Paragraph("<b>Immutable Version Pinning</b>", S["TblCell"]),
            Paragraph("Test specifications must be reproducible against an exact baseline. Dynamic pointers invalidate historical compliance.", S["TblCell"])
        ],
        [
            Paragraph("Duplicate Submissions", S["TblCellBold"]),
            Paragraph("Deduplication / Overwrite", S["TblCell"]),
            Paragraph("<b>Append-Only History Preservation</b>", S["TblCell"]),
            Paragraph("Re-submissions reflect post-change re-evaluations. Silently deduplicating destroys audit lineage of prior tests.", S["TblCell"])
        ],
        [
            Paragraph("LLM Failure Strategy", S["TblCellBold"]),
            Paragraph("Infinite retry / Silent drop", S["TblCell"]),
            Paragraph("<b>Regex Extract + Partial Error</b>", S["TblCell"]),
            Paragraph("Schema mismatches signal prompt/model issues where retries fail. Returning partial_error preserves raw output without crashing.", S["TblCell"])
        ],
        [
            Paragraph("Persistence Architecture", S["TblCellBold"]),
            Paragraph("Pure Relational / Pure NoSQL", S["TblCell"]),
            Paragraph("<b>SQLite + MongoDB (JSON fallback)</b>", S["TblCell"]),
            Paragraph("Relational DB enforces tree hierarchy integrity; Document store manages variable test payloads. JSON fallback ensures zero setup friction.", S["TblCell"])
        ],
    ]
    t_dec = Table(dec_data, colWidths=[80, 95, 95, CONTENT_W - 270])
    t_dec.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f3460")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#dcdfe6")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(t_dec)

    # ─── 10. CONCLUSION & FUTURE ROADMAP ─────────────────────────────────────
    story.append(Spacer(1, 4))
    story.append(Paragraph("10. Conclusion & Future Roadmap", S["SecH1"]))
    story.append(Paragraph(
        "The CT-200 QA Document System provides a robust, production-ready foundation for automated medical device QA engineering. "
        "By integrating hierarchical PDF parsing, path-based version reconciliation, version-pinned test generation, and "
        "deterministic staleness tracking, the platform guarantees full traceability and auditability for technical manuals.",
        S["BodyJ"]
    ))
    story.append(Paragraph(
        "<b>Future Enhancements:</b><br/>"
        "• <i>Multi-Modal OCR Pipeline:</i> Integrating vision models for diagrams, waveforms, and schematic flowcharts.<br/>"
        "• <i>Semantic Embedding Search:</i> Adding vector embeddings (e.g. BAAI/bge-small) for conceptual section retrieval.<br/>"
        "• <i>Automated Test Suite Re-Generation:</i> One-click batch re-generation of stale test suites with automated notifications.",
        S["BodyL"]
    ))

    # Build PDF
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Approach document successfully generated at: {output_path}")

if __name__ == "__main__":
    create_approach_pdf("Approach_Document.pdf")
    create_approach_pdf("APPROACH.pdf")
