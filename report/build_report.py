from __future__ import annotations

import hashlib
import math
import os
import textwrap
from pathlib import Path

from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Preformatted,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence" / "transcripts"
OUT = ROOT / "output" / "pdf" / "postgres_gist_500m_assignment.pdf"
TMP = ROOT / "tmp" / "pdfs"

NAVY = colors.HexColor("#0B1F33")
BLUE = colors.HexColor("#146C94")
CYAN = colors.HexColor("#19A7CE")
GREEN = colors.HexColor("#1F9D72")
ORANGE = colors.HexColor("#F59E0B")
RED = colors.HexColor("#C2413A")
INK = colors.HexColor("#18212B")
MUTED = colors.HexColor("#5D6B78")
PALE = colors.HexColor("#EAF4F8")
LIGHT = colors.HexColor("#F5F7FA")
TERM = colors.HexColor("#101820")
TERM_GREEN = colors.HexColor("#B9F6CA")


def read(name: str) -> str:
    return (EVIDENCE / name).read_text(encoding="utf-8", errors="replace")


BASELINE = read("04_baseline-20261112-051316.txt")
AFTER = read("06_after_gist-20261112-053044.txt")
FINALIZE = read("03_finalize_load-20261112-051048.txt")
INDEX = read("05_index-20261112-051626.txt")
VERIFY = read("07_verify-20261112-053045.txt")
GEOHASH = read("08_geohash-20261112-053106.txt")
POLYGON_BITMAP = read("09_polygon_bitmap-20261112-053520.txt")
GEOHASH_ISOLATED = read("10_geohash_isolated-20261112-053708.txt")


def ascii_clean(value: str) -> str:
    return (
        value.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .encode("ascii", "replace")
        .decode("ascii")
    )


def wrapped_terminal(text: str, width: int = 98, max_lines: int = 34) -> str:
    out: list[str] = []
    for raw in ascii_clean(text).splitlines():
        if not raw:
            out.append("")
            continue
        parts = textwrap.wrap(raw, width=width, replace_whitespace=False, drop_whitespace=False)
        out.extend(parts or [""])
    if len(out) > max_lines:
        out = out[: max_lines - 1] + ["... output truncated; full transcript is preserved in evidence/ ..."]
    return "\n".join(out)


def between(text: str, start: str, end: str | None = None) -> str:
    a = text.index(start)
    b = text.index(end, a) if end else len(text)
    return text[a:b].strip()


def page_number(canvas, doc):
    canvas.saveState()
    w, h = A4
    canvas.setStrokeColor(colors.HexColor("#D7E0E8"))
    canvas.line(18 * mm, 14 * mm, w - 18 * mm, 14 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 9 * mm, "PostgreSQL 17 GiST at 500M points")
    canvas.drawRightString(w - 18 * mm, 9 * mm, f"Page {doc.page}")
    canvas.restoreState()


class AssignmentDoc(BaseDocTemplate):
    def __init__(self, filename: str):
        super().__init__(
            filename,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=17 * mm,
            bottomMargin=18 * mm,
            title="PostgreSQL 17 GiST Spatial Indexing at 500M Points",
            author="Course assignment",
            subject="Before/after GiST and geohash analysis",
        )
        frame = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="normal")
        self.addPageTemplates(PageTemplate(id="main", frames=frame, onPage=page_number))


styles = getSampleStyleSheet()
styles.add(ParagraphStyle(name="CoverKicker", parent=styles["Normal"], fontName="Helvetica-Bold", fontSize=10, leading=13, textColor=CYAN, spaceAfter=10))
styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], fontName="Helvetica-Bold", fontSize=27, leading=31, textColor=colors.white, alignment=TA_LEFT, spaceAfter=13))
styles.add(ParagraphStyle(name="CoverSub", parent=styles["Normal"], fontName="Helvetica", fontSize=12, leading=17, textColor=colors.HexColor("#DCEAF2"), spaceAfter=9))
styles.add(ParagraphStyle(name="CoverMeta", parent=styles["Normal"], fontName="Helvetica", fontSize=10.5, leading=15, textColor=NAVY, spaceAfter=5))
styles.add(ParagraphStyle(name="H1x", parent=styles["Heading1"], fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=NAVY, spaceBefore=4, spaceAfter=10))
styles.add(ParagraphStyle(name="H2x", parent=styles["Heading2"], fontName="Helvetica-Bold", fontSize=13.5, leading=17, textColor=BLUE, spaceBefore=8, spaceAfter=6))
styles.add(ParagraphStyle(name="Bodyx", parent=styles["BodyText"], fontName="Helvetica", fontSize=9.2, leading=13.4, textColor=INK, spaceAfter=6))
styles.add(ParagraphStyle(name="Smallx", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.8, leading=10.5, textColor=MUTED, spaceAfter=4))
styles.add(ParagraphStyle(name="HeaderCell", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=7.8, leading=10.2, textColor=colors.white, spaceAfter=0))
styles.add(ParagraphStyle(name="Callout", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=10.5, leading=14.5, textColor=NAVY, leftIndent=7, rightIndent=7, spaceBefore=5, spaceAfter=5, backColor=PALE, borderColor=CYAN, borderWidth=0.8, borderPadding=8))
styles.add(ParagraphStyle(name="Metric", parent=styles["BodyText"], fontName="Helvetica-Bold", fontSize=16, leading=18, textColor=BLUE, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="MetricLabel", parent=styles["BodyText"], fontName="Helvetica", fontSize=7.5, leading=9.5, textColor=MUTED, alignment=TA_CENTER))
styles.add(ParagraphStyle(name="Term", fontName="Courier", fontSize=6.2, leading=8.1, textColor=TERM_GREEN, backColor=TERM, leftIndent=5, rightIndent=5, borderPadding=7, spaceAfter=7))


def p(text: str, style: str = "Bodyx") -> Paragraph:
    return Paragraph(ascii_clean(text), styles[style])


def h1(text: str) -> Paragraph:
    return p(text, "H1x")


def h2(text: str) -> Paragraph:
    return p(text, "H2x")


def terminal(text: str, max_lines: int = 34) -> Table:
    block = Preformatted(wrapped_terminal(text, max_lines=max_lines), styles["Term"])
    box = Table([[block]], colWidths=[174 * mm], hAlign="LEFT")
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), TERM),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#263848")),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    return box


def metric_row(items):
    cells = []
    for value, label in items:
        cells.append([p(value, "Metric"), p(label, "MetricLabel")])
    table = Table(cells, colWidths=[(174 * mm) / len(cells)] * len(cells))
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), LIGHT),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E2EA")),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8E2EA")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return table


def data_table(data, widths=None, header=True, font=7.6):
    cooked = []
    for r, row in enumerate(data):
        cell_style = "HeaderCell" if header and r == 0 else "Smallx"
        cooked.append([p(str(cell), cell_style) for cell in row])
    t = Table(cooked, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#C9D4DE")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1 if header else 0), (-1, -1), [colors.white, LIGHT]),
    ]
    if header:
        commands += [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(commands))
    return t


def speedup_chart(rows):
    width, height = 470, 130
    d = Drawing(width, height)
    d.add(Rect(0, 0, width, height, fillColor=LIGHT, strokeColor=colors.HexColor("#D8E2EA")))
    max_log = max(math.log10(x[1]) for x in rows)
    for i, (label, value) in enumerate(rows):
        y = height - 26 - i * 25
        d.add(String(10, y + 3, label, fontName="Helvetica-Bold", fontSize=8, fillColor=INK))
        bar_x = 92
        bar_w = 300 * math.log10(value) / max_log
        d.add(Rect(bar_x, y, bar_w, 11, fillColor=CYAN if i < 3 else GREEN, strokeColor=None))
        d.add(String(bar_x + bar_w + 6, y + 2, f"{value:,.0f}x", fontName="Helvetica-Bold", fontSize=8, fillColor=NAVY))
    d.add(String(10, 8, "Bars use log10(speedup) so all four improvements remain visible.", fontName="Helvetica-Oblique", fontSize=7, fillColor=MUTED))
    return d


def bullets(items):
    return [p(f"<bullet>&bull;</bullet>{item}") for item in items]


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)
    story = []

    # Cover
    cover = Table([[p("DATABASE SYSTEMS - SPATIAL INDEXING", "CoverKicker")],
                   [p("PostgreSQL 17 GiST Spatial Indexing at 500 Million Points", "CoverTitle")],
                   [p("Reproduction and extension of the nearby-places tutorial using Docker, pgAdmin, built-in geometric types, GiST, K-NN and PostGIS geohashing.", "CoverSub")]],
                  colWidths=[174 * mm], rowHeights=[18 * mm, 59 * mm, 35 * mm])
    cover.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story += [Spacer(1, 20 * mm), cover, Spacer(1, 13 * mm)]
    story += [metric_row([("500,000,000", "generated rows"), ("25 min", "full pipeline"), ("31 GB", "GiST index"), ("0.321 ms", "cold top-100 K-NN")]), Spacer(1, 12 * mm)]
    story += [p("Student: ________________________________", "CoverMeta"), p("Roll no. / section: ______________________", "CoverMeta"), p("Execution date: 12 November 2026", "CoverMeta"), p("Environment: Hetzner CPX42, Docker Compose, PostgreSQL 17.5, pgAdmin 4", "CoverMeta"), PageBreak()]

    story += [h1("Executive summary")]
    story += [p("This submission reproduces the complete tutorial pipeline at 50x the original scale: 500,000,000 uniformly distributed longitude/latitude points instead of 10,000,000. The unindexed plans performed parallel sequential scans over all 500M rows. After a GiST index was added, containment queries changed to bitmap or index-only access and nearest-neighbor search changed to an ordered K-NN index scan that stopped after 100 rows.")]
    story += [p("The headline result is not merely that an index is faster. GiST changes the amount of work: the baseline evaluates every row, whereas indexed plans read a small candidate set or walk the tree in distance order. The extension also shows where geohashing helps - compact, shard-friendly prefix keys - and where it does not: arbitrary shapes, cell boundaries and exact top-K nearest-neighbor search.", "Callout")]
    story += [Spacer(1, 4 * mm), metric_row([("21.8 s", "box before GiST"), ("63.9 ms", "box after, cold"), ("0.093 ms", "circle after, cold"), ("13.6 ms", "polygon bitmap, cold")]), Spacer(1, 5 * mm)]
    story += [data_table([
        ["Query", "Before GiST", "After GiST - cold", "After GiST - warm", "Indexed plan"],
        ["NYC box", "21,820.542 ms", "63.938 ms", "1.263 ms", "Bitmap Index + Heap"],
        ["Circle", "22,121.710 ms", "0.093 ms", "0.086 ms", "Bitmap Index + Heap"],
        ["Top-100 K-NN", "29,897.233 ms", "0.321 ms", "0.295 ms", "Ordered GiST Index Scan"],
        ["Polygon COUNT", "21,644.234 ms", "3.798 ms", "0.181 ms", "GiST Index Only Scan"],
        ["Polygon rows (extension)", "same predicate", "13.597 ms", "0.151 ms", "Bitmap Index + Heap"],
    ], [30*mm, 30*mm, 31*mm, 31*mm, 50*mm])]
    story += [Spacer(1, 5 * mm), speedup_chart([("Box", 21820.542/63.938), ("Circle", 22121.710/0.093), ("K-NN", 29897.233/0.321), ("Polygon", 21644.234/3.798)]), PageBreak()]

    story += [h1("1. Environment and configuration")]
    story += [data_table([
        ["Component", "Configuration"],
        ["Cloud VM", "Hetzner CPX42 shared AMD: 8 vCPU, 16 GB RAM, 320 GB SSD"],
        ["Host", "Ubuntu Linux 6.8, x86_64, AMD EPYC-Genoa, KVM"],
        ["Containers", "Docker 27.5.1; Docker Compose 2.32.4"],
        ["Database", "PostgreSQL 17.5, postgis/postgis:17-3.5"],
        ["Administration", "Dockerized pgAdmin 4, accessed through an SSH tunnel"],
        ["Exposure", "PostgreSQL and pgAdmin bound to 127.0.0.1 only; no public DB/UI port"],
        ["Memory tuning", "shared_buffers 4 GB; effective_cache_size 10 GB; maintenance_work_mem 4 GB; work_mem 128 MB"],
        ["Parallelism", "8 worker processes; 4 workers per gather; 4 maintenance workers"],
        ["Planner / measurement", "random_page_cost 1.1; effective_io_concurrency 200; track_io_timing on; JIT off"],
    ], [43*mm, 129*mm])]
    story += [h2("Docker topology")]
    story += bullets([
        "postgres: PostgreSQL 17 + PostGIS, 2 GB shared-memory segment, persistent pgdata volume.",
        "pgadmin: pgAdmin 4, dependent on a healthy PostgreSQL service.",
        "SQL and transcript directories are bind-mounted for reproducible scripts and durable evidence.",
        "Only loopback ports 5432 and 5050 are published; access is tunneled through SSH.",
    ])
    story += [h2("Why these settings matter")]
    story += [p("Large shared buffers reduce repeated metadata and index-page reads, while 4 GB maintenance_work_mem accelerates the primary-key and GiST builds. track_io_timing makes cold-cache evidence explicit. JIT is disabled because compilation overhead would distort millisecond index probes. The NVMe-oriented random_page_cost encourages realistic random index access.")]
    story += [terminal("""$ docker compose ps
NAME             IMAGE                              STATUS
week3-postgres   postgis/postgis:17-3.5             Up (healthy)
week3-pgadmin    dpage/pgadmin4:latest              Up

$ SELECT version();
PostgreSQL 17.5 (Debian 17.5-1.pgdg110+1), 64-bit""", 18), PageBreak()]

    story += [h1("2. Methodology and reproducibility")]
    story += [p("The tutorial's SQL was retained for box, circle, nearest-neighbor and polygon queries. At 500M scale the loader was adapted for throughput while restoring the tutorial's final schema before measurement.")]
    story += [data_table([
        ["Decision", "Reason", "Trade-off / control"],
        ["UNLOGGED load table", "Avoid duplicating a regenerable 500M fixture in WAL", "Crash can truncate data; acceptable for a benchmark fixture"],
        ["Four disjoint ID ranges", "Parallel generation without sequence contention", "Sequence and BIGSERIAL-compatible default restored later"],
        ["Primary key after load", "One bulk B-tree build is faster and less bloated", "Final measured schema still has the primary key"],
        ["5M smoke test", "Catches SQL and mount failures before expensive work", "Smoke data dropped before the real run"],
        ["Cold and warm runs", "Separates storage I/O from cached execution", "PostgreSQL restart plus Linux drop_caches for cold runs"],
        ["Exact count + planner estimate", "Proves physical population and analyzed statistics", "Both values retained in transcripts"],
    ], [37*mm, 70*mm, 65*mm])]
    story += [h2("Pipeline")]
    story += [p("Schema -> 5M smoke load -> clean schema -> 500M parallel load -> exact count -> primary key -> ANALYZE -> before-GiST plans -> GiST build -> after-GiST plans -> correctness checks -> 50M geohash comparison -> rubric extensions.")]
    story += [p("The complete unattended run took 25 minutes. The raw 500M insert took 2 minutes, primary-key creation 1 minute 45.6 seconds and the 31 GB GiST build 14 minutes 10.7 seconds.", "Callout"), PageBreak()]

    story += [h1("3. Proof of 500 million generated points")]
    proof = """SELECT count(*) AS total_rows FROM locations;
 total_rows
------------
  500000000
(1 row)
Time: 30352.622 ms (00:30.353)

Unlogged table public.locations
 location_id | bigint | not null | nextval('locations_location_id_seq')
 name        | text
 geolocation | point
Indexes: locations_pkey PRIMARY KEY, btree (location_id)

 table_only | indexes_only | total_with_indexes
------------+--------------+-------------------
 36 GB      | 10 GB        | 46 GB

 planner_row_estimate | heap_pages
----------------------+-----------
 499995584            | 4671907"""
    story += [terminal(proof, 32)]
    story += [p("The exact count is the primary proof. The 499,995,584 planner estimate (99.9991% of the exact total) independently confirms that ANALYZE sampled a fully populated relation. The 36 GB heap and 4,671,907 heap pages are consistent with 500M compact rows.")]
    story += [h2("Uniformity and correctness")]
    story += [data_table([
        ["Shape", "Expected under uniform generation", "Measured", "Interpretation"],
        ["Box: 0.4 x 0.3 deg", "925.9", "969", "Close to expectation"],
        ["Circle: r=0.02 deg", "9.7", "7", "Small-count random variation"],
        ["Polygon: 0.08 x 0.10 deg", "61.7", "77", "Close to expectation"],
    ], [43*mm, 46*mm, 28*mm, 55*mm])]
    story += [p("A fast index that silently loses rows is not useful. Comparing measured counts with area-based expectations provides a correctness check that the tutorial itself does not include."), PageBreak()]

    story += [h1("4. Before GiST: full-table work")]
    story += [p("Every tutorial predicate had to inspect the 500M-row heap. PostgreSQL used four parallel workers plus the leader, but parallelism only divided an O(N) scan; it did not change the amount of work.")]
    baseline_box = between(BASELINE, "--- Q1: bounding box", "--- Q1: bounding box, run 2")
    story += [h2("Snapshot: bounding box baseline"), terminal(baseline_box, 27)]
    story += [h2("Snapshot: K-NN baseline")]
    knn_base = between(BASELINE, "--- Q3: K-NN nearest neighbour", "--- Q3: K-NN, run 2")
    story += [terminal(knn_base, 31)]
    story += [p("The K-NN baseline is especially revealing: each of five processes scans roughly 100M rows, then performs a top-N heapsort. Even though only 100 rows are returned, all 500M distances must be evaluated."), PageBreak()]

    story += [h1("5. Building and validating the GiST index")]
    story += [metric_row([("14:10.698", "GiST build time"), ("31 GB", "GiST size"), ("10 GB", "primary key size"), ("77 GB", "table + indexes")]), Spacer(1, 6 * mm)]
    story += [terminal("""CREATE INDEX idx_locations_gist ON locations USING gist (geolocation);
CREATE INDEX
Time: 850698.098 ms (14:10.698)

index_name          index_size
------------------  ----------
idx_locations_gist  31 GB
locations_pkey      10 GB""", 16)]
    story += [p("GiST is a framework rather than a single comparison rule. The point operator class stores spatial keys that support containment predicates and distance ordering. The 31 GB structure is large, but it replaces repeated 36 GB heap scans with small candidate probes.")]
    story += [h2("Index usage counters")]
    story += [terminal("""index_name          idx_scan   idx_tup_read   idx_tup_fetch
------------------  --------   ------------   -------------
idx_locations_gist        11           3359            1126
locations_pkey             2              6               6""", 12)]
    story += [p("The usage counters confirm the measured plans were not merely theoretical EXPLAIN choices; PostgreSQL actually executed the GiST index."), PageBreak()]

    story += [h1("6. After GiST: indexed spatial access")]
    after_box = between(AFTER, "--- Q1: bounding box", "--- Q1: bounding box, run 2")
    story += [h2("Snapshot: box - Bitmap Index Scan"), terminal(after_box, 29)]
    after_knn = between(AFTER, "--- Q3: K-NN nearest neighbour", "--- Q3: K-NN, run 2")
    story += [h2("Snapshot: top-100 K-NN - ordered Index Scan"), terminal(after_knn, 25)]
    story += [p("The box cold run took 63.938 ms because 969 heap rows had to be read after the index returned their locations. Its warm run dropped to 1.263 ms. The circle touched only seven rows and completed in 0.093 ms even on the recorded cold pass. K-NN returned 100 nearest rows in 0.321 ms without scanning or sorting 500M distances."), PageBreak()]

    story += [h1("7. Polygon planner nuance and rubric extension")]
    story += [p("The tutorial's polygon query is COUNT(*). On PostgreSQL 17, GiST can satisfy this predicate with an Index Only Scan, so the natural plan is more efficient than the assignment's expected Bitmap Heap Scan. This result was preserved rather than forced away.")]
    polygon_original = between(AFTER, "--- Q4: polygon containment", "--- Q4: polygon containment, run 2")
    story += [h2("Original tutorial query: Index Only Scan"), terminal(polygon_original, 24)]
    story += [p("To demonstrate the rubric's requested box/circle/polygon bitmap behavior, an additional query returned full polygon rows. Heap columns are then required and the optimizer naturally selected Bitmap Index Scan -> Bitmap Heap Scan.", "Callout")]
    story += [h2("Extension: row-returning polygon query")]
    story += [terminal(POLYGON_BITMAP, 30)]
    story += [p("Cold execution was 13.597 ms and warm execution was 0.151 ms for 77 rows. No planner switches were disabled and no plan was fabricated."), PageBreak()]

    story += [h1("8. Geohash extension")]
    story += [p("A 50M-row subset was used for the direct geohash-vs-GiST comparison. This keeps the comparison on identical rows while avoiding a second 500M table and two additional indexes. Plan shape, selectivity, boundary behavior and correctness are the focus; these properties do not depend on duplicating the remaining 450M rows.")]
    story += [metric_row([("50,000,000", "comparison rows"), ("1,071 MB", "geohash B-tree"), ("3,181 MB", "comparison GiST"), ("57.1 s", "geohash materialization")]), Spacer(1, 6 * mm)]
    story += [data_table([
        ["Observation", "Measured result", "Meaning"],
        ["Single covering prefix", "dr%", "The two box corners diverge at character 3; a fine single prefix cannot cover the box"],
        ["Candidates", "48,768", "Rows fetched by the coarse prefix"],
        ["True rows", "108", "Rows actually inside the NYC box"],
        ["False positives", "48,660", "Candidates discarded by exact re-check"],
        ["Precision / recall", "0.221% / 100%", "Correct but extremely wasteful at this prefix"],
        ["Overfetch", "451.6x", "Each true row causes about 452 candidates"],
        ["Boundary test", "877 / 1,000", "~101 m pairs fall into different precision-7 cells"],
        ["Precision-5 K-NN cell", "2 rows", "Cannot answer top-100 correctly without widening / neighboring cells"],
    ], [42*mm, 39*mm, 91*mm])]
    story += [h2("Snapshot: isolated geohash candidate and re-check path")]
    story += [terminal(GEOHASH_ISOLATED, 34), PageBreak()]

    story += [h1("9. Geohash versus GiST")]
    story += [data_table([
        ["Dimension", "Geohash + B-tree", "GiST"],
        ["Representation", "String key for a fixed hierarchical grid", "Balanced search framework using spatial operator classes"],
        ["Storage in 50M test", "1,071 MB", "3,181 MB"],
        ["Box lookup", "Prefix range scan plus exact re-check", "One spatial containment predicate"],
        ["Measured NYC box", "934.378 ms cold, 48,768 candidates", "0.148 ms warm, 108 exact rows"],
        ["Boundary handling", "Query current cell plus neighbors; deduplicate and re-check", "Overlapping/adaptive index keys; no fixed-grid edge rule"],
        ["Top-K nearest", "No native distance order; widen cells and sort candidates", "Native ORDER BY point <-> query, early stop at K"],
        ["Distributed systems", "Excellent shard/partition prefix and cache key", "Best inside PostgreSQL for exact spatial predicates"],
        ["Operational complexity", "Application owns precision, neighbors and correctness", "Database owns index traversal and recheck"],
    ], [38*mm, 67*mm, 67*mm])]
    story += [h2("Interpretation")]
    story += bullets([
        "Geohash is not a substitute for an exact distance function. It is a coarse candidate-generation strategy.",
        "A coarse prefix preserves recall but can destroy precision; a fine prefix improves precision but misses adjacent cells unless neighbors are queried.",
        "GiST is larger in this experiment, but it directly supports arbitrary containment and K-NN semantics with dramatically less application logic.",
        "A practical distributed design can use geohash for partition routing and GiST/PostGIS inside each shard for exact filtering and ranking.",
    ])
    story += [h2("Boundary evidence")]
    story += [terminal(between(GEOHASH, "3. Two points 100 m apart", "4. \"100 nearest points"), 26), PageBreak()]

    story += [h1("10. What I learned")]
    story += bullets([
        "Index benefit comes from avoided work, not only faster hardware. Parallel sequential scans still examined 500M rows for every predicate.",
        "GiST is operator-driven. The same index supports containment through bitmap/index-only plans and distance ordering through K-NN index scans.",
        "Cold/warm methodology matters. Comparing a cold pre-index scan with a warm post-index probe exaggerates the pure indexing gain, so both were recorded.",
        "The optimizer may choose a plan better than the rubric wording. COUNT(*) over the polygon became index-only; returning full rows naturally demonstrated the bitmap path.",
        "Synthetic global lon/lat data is useful for repeatable selectivity tests, but PostgreSQL's built-in point distance is planar degrees. Real geodesic distance should use PostGIS geography.",
        "Bulk loading is a system-design problem: WAL policy, sequence contention, deferred indexes, maintenance memory and evidence capture materially affect feasibility at 500M scale.",
        "Geohash is strongest as a distributed routing key. Exact nearby-places results still need neighbor expansion, distance rechecks and ranking.",
    ])
    story += [h2("Validity and limitations")]
    story += [data_table([
        ["Threat / limitation", "Mitigation or implication"],
        ["Shared cloud CPU can vary", "Record hardware, cold/warm runs and buffer/I/O timings; focus on plan-shape change as well as latency"],
        ["Uniform synthetic distribution", "Excellent for repeatability; real cities are skewed and may change selectivity and tree occupancy"],
        ["POINT uses planar degrees", "Do not interpret <-> as meters globally; use PostGIS geography for production geodesic distance"],
        ["UNLOGGED fixture", "Appropriate for reproducible benchmark data, not durable production data"],
        ["50M geohash subset", "Enough for plan/selectivity/boundary analysis; absolute build size scales with rows"],
    ], [52*mm, 120*mm]), PageBreak()]

    story += [h1("11. Reproduction guide")]
    story += [p("The submitted project contains Docker Compose configuration, SQL steps and captured transcripts. The minimal reproduction sequence is:")]
    story += [terminal("""docker compose up -d
bash scripts/run-step.sh 01_schema
TOTAL=500000000 WORKERS=4 BATCH=10000000 bash scripts/run-load.sh
bash scripts/run-step.sh 03_finalize_load
bash scripts/run-step.sh --cold 04_baseline
bash scripts/run-step.sh 05_index
bash scripts/run-step.sh --cold 06_after_gist
bash scripts/run-step.sh 07_verify
bash scripts/run-step.sh 08_geohash
bash scripts/run-step.sh --cold 09_polygon_bitmap
bash scripts/run-step.sh --cold 10_geohash_isolated""", 20)]
    story += [p("For the automated path, scripts/bootstrap.sh runs steps 01 through 08 with fail-fast ordering. The before-GiST transcript is captured before index creation, preventing accidental contamination of the baseline.")]
    story += [h2("Submission checklist")]
    story += bullets([
        "500,000,000 exact rows shown and planner estimate reported.",
        "All tutorial queries executed before and after GiST.",
        "Parallel Seq Scan, Bitmap Index Scan, Index Only Scan and K-NN Index Scan plans captured.",
        "Docker, PostgreSQL 17 and pgAdmin configuration documented.",
        "Geohash storage, overfetch, boundary and top-K limitations measured.",
        "Raw transcript evidence retained with hashes below.",
    ])
    story += [PageBreak(), h1("12. Evidence manifest")]
    manifest = [["Evidence file", "Bytes", "SHA-256 (first 20 hex)"]]
    for path in sorted(EVIDENCE.glob("*.txt")):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        manifest.append([path.name, f"{path.stat().st_size:,}", digest[:20]])
    story += [data_table(manifest, [89*mm, 25*mm, 58*mm])]
    story += [h2("References")]
    story += [p("1. Jeyaram Ayyalusamy, 'PostgreSQL 17 Performance Tuning: GiST (Generalized Search Tree)', Medium, 5 September 2025. https://medium.com/@jramcloud1/21-postgresql-17-performance-tuning-gist-generalized-search-tree-8e5cacea9fc8")]
    story += [p("2. Assignment implementation repository used as the automation baseline: https://github.com/nabeel-hussain/postgres-gist-500m-geopoints")]
    story += [p("3. PostgreSQL 17 documentation: geometric types, GiST indexes and index-ordering operators. https://www.postgresql.org/docs/17/")]
    story += [p("4. PostGIS documentation: ST_GeoHash and geography distance. https://postgis.net/docs/")]
    story += [Spacer(1, 5 * mm), p("All performance numbers in this report come from the attached local transcript evidence, not from the tutorial's example timings.", "Callout")]

    doc = AssignmentDoc(str(OUT))
    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
