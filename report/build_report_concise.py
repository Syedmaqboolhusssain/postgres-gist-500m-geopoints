"""Build the five-page assignment PDF from the saved PostgreSQL run."""

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
import re
from textwrap import wrap
from xml.sax.saxutils import escape

import pypdfium2
from reportlab.lib.colors import HexColor, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    Image, KeepTogether, PageBreak, Paragraph, Preformatted, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/pdf/postgres_gist_500m_assignment_concise.pdf"
LOGS = ROOT / "evidence/transcripts"
BEFORE = "04_baseline-20261112-051316.txt"
AFTER = "06_after_gist-20261112-053044.txt"
POLYGON = "09_polygon_bitmap-20261112-053520.txt"
LOAD = "03_finalize_load-20261112-051048.txt"
BUILD = "05_index-20261112-051626.txt"
VERIFY = "07_verify-20261112-053045.txt"
HASH_BOX = "10_geohash_isolated-20261112-053708.txt"
HASH_BOUNDARY = "08_geohash-20261112-053106.txt"
TUTORIAL = (
    "https://medium.com/@jramcloud1/"
    "21-postgresql-17-performance-tuning-gist-generalized-search-tree-8e5cacea9fc8"
)
DOCKER_REF = "https://github.com/pszponder/docker_postgres-pgadmin/blob/main/docker-compose.yaml"

PLUM = HexColor("#4C2548")
GOLD = HexColor("#A36C22")
INK = HexColor("#29232C")
MUTED = HexColor("#59515C")
PANEL = HexColor("#F4F2F5")
RULE = HexColor("#DAD3DB")
MARGIN = 37
WIDTH = A4[0] - 2 * MARGIN - 12  # Default frame padding, 6 pt per side.

BODY = ParagraphStyle("Body", fontName="Helvetica", fontSize=10, leading=14,
                      textColor=INK, spaceAfter=7)
SMALL = ParagraphStyle("Small", parent=BODY, fontSize=8.4, leading=11,
                       textColor=MUTED, spaceAfter=5)
TITLE = ParagraphStyle("Title", parent=BODY, fontName="Helvetica-Bold",
                       fontSize=31, leading=34, textColor=PLUM, spaceAfter=9)
SECTION = ParagraphStyle("Section", parent=TITLE, fontSize=23, leading=27, spaceAfter=10)
SUBHEAD = ParagraphStyle("Subhead", parent=BODY, fontName="Helvetica-Bold",
                         fontSize=12, leading=15, textColor=PLUM, spaceBefore=7, spaceAfter=4)
KICKER = ParagraphStyle("Kicker", parent=SMALL, fontName="Helvetica-Bold",
                        textColor=GOLD, fontSize=9, spaceAfter=7)
CODE = ParagraphStyle("SQL", parent=BODY, fontName="Courier", fontSize=8.6,
                      leading=10.8, leftIndent=6, spaceAfter=4)
TH = ParagraphStyle("TH", parent=SMALL, fontName="Helvetica-Bold", textColor=white, spaceAfter=0)
TD = ParagraphStyle("TD", parent=SMALL, fontSize=9, textColor=INK, spaceAfter=0)


@dataclass(frozen=True)
class Plan:
    sql: str
    output: tuple[str, ...]
    ms: float


def read(name):
    return (LOGS / name).read_text(encoding="utf-8-sig")


def query_runs(name):
    # Each -e transcript section starts with the exact statement sent to psql.
    parts = re.findall(
        r"(?ms)^EXPLAIN \(ANALYZE, BUFFERS\)\n(.*?;)\n"
        r"^[ \t]*QUERY PLAN[ \t]*\n-+\n(.*?^ Execution Time: ([\d.]+) ms)",
        read(name),
    )
    return [Plan(sql, tuple(lines.splitlines()), float(ms)) for sql, lines, ms in parts]


def excerpt(name, start, stop):
    transcript = read(name)
    first = transcript.index(start)
    last = transcript.index(stop, first + len(start))
    return transcript[first:last].strip("\n").splitlines()


def output_lines(plan, *needles):
    selected = [
        line for line in plan.output
        if not re.match(r"\s*Worker \d+:", line)
        and any(needle in line for needle in needles)
    ]
    if any(not any(needle in line for line in selected) for needle in needles):
        raise ValueError(f"Expected plan lines missing from {plan.sql}")
    return selected + [plan.output[-1]]


def snapshot(label, filename, lines):
    # Render only recorded lines. Visual wraps preserve all characters on the line.
    max_columns = int((WIDTH - 20) / stringWidth("M", "Courier", 8.2))
    lines = [part for line in lines for part in wrap(
        line.rstrip(), width=max_columns, subsequent_indent="    ", replace_whitespace=False,
        drop_whitespace=True, break_long_words=False, break_on_hyphens=False,
    ) or [""]]
    if any(not line.isascii() for line in lines):
        raise ValueError(f"Non-ASCII evidence in {filename}")
    height = 27 + len(lines) * 10.4
    if any(stringWidth(line, "Courier", 8.2) > WIDTH - 20 for line in lines):
        raise ValueError(f"Evidence line exceeds the panel width in {filename}")
    source = BytesIO()
    drawing = canvas.Canvas(source, pagesize=(WIDTH, height))
    drawing.setFillColor(PANEL)
    drawing.rect(0, 0, WIDTH, height, fill=1, stroke=0)
    drawing.setFillColor(GOLD)
    drawing.rect(0, 0, 2.5, height, fill=1, stroke=0)
    drawing.setFont("Helvetica-Bold", 8.2)
    drawing.setFillColor(PLUM)
    drawing.drawString(10, height - 12, label)
    drawing.setFont("Helvetica", 7.4)
    drawing.setFillColor(MUTED)
    drawing.drawRightString(WIDTH - 9, height - 12, f"Recorded psql output | {filename}"
                            if filename != "bootstrap.log" else "Recorded Docker output | bootstrap.log")
    drawing.setFont("Courier", 8.2)
    drawing.setFillColor(INK)
    for index, line in enumerate(lines):
        drawing.drawString(10, height - 25 - index * 10.4, line)
    drawing.save()
    document = pypdfium2.PdfDocument(source.getvalue())
    page = document[0]
    bitmap = page.render(scale=3)
    png = BytesIO()
    bitmap.to_pil().save(png, format="PNG")
    bitmap.close()
    page.close()
    document.close()
    png.seek(0)
    return Image(png, width=WIDTH, height=height)


def text(value, style=BODY):
    return Paragraph(value, style)


def sql(plan):
    return Preformatted("EXPLAIN (ANALYZE, BUFFERS)\n" + plan.sql, CODE)


def heading(label, title):
    return [text(label, KICKER), text(title, SECTION)]


def evidence(label, filename, plan, *needles):
    return snapshot(label, filename, output_lines(plan, *needles))


def table(headers, rows, widths):
    data = [[text(escape(cell), TH) for cell in headers]]
    data += [[text(escape(cell), TD) for cell in row] for row in rows]
    result = Table(data, colWidths=widths, hAlign="LEFT")
    result.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), PLUM),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [PANEL, white]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, -1), (-1, -1), 0.5, RULE),
    ]))
    return result


def footer(page, doc):
    page.setStrokeColor(RULE)
    page.line(MARGIN + 6, 31, A4[0] - MARGIN - 6, 31)
    page.setFont("Helvetica", 8)
    page.setFillColor(MUTED)
    page.drawString(MARGIN + 6, 19, "POSTGRESQL 17  /  SPATIAL INDEXING")
    page.drawRightString(A4[0] - MARGIN - 6, 19, str(doc.page))


def build():
    before, after, polygon = (query_runs(name) for name in (BEFORE, AFTER, POLYGON))
    if (len(before), len(after), len(polygon)) != (8, 8, 2):
        raise ValueError("Expected two recorded passes of each spatial query.")
    if [plan.sql for plan in before] != [plan.sql for plan in after]:
        raise ValueError("Before and after SQL differs in the source transcripts.")

    story = [
        text("DATABASE SYSTEMS ASSIGNMENT", KICKER),
        text("Spatial indexing on<br/>500 million points", TITLE),
        text("<b>Syed Maqbool Hussain</b> | 12 November 2026", BODY),
        text("PostgreSQL 17.5 with PostGIS 3.5 and pgAdmin 4<br/>"
             "Hetzner CPX42 | 8 vCPU, 16 GB RAM, 320 GB SSD", SMALL),
        text("Start PostgreSQL and pgAdmin", SUBHEAD),
        text("Copy <b>.env.example</b> to <b>.env</b>, set the passwords, and keep the port bindings "
             "on 127.0.0.1. Run these commands from the repository root."),
        Preformatted("docker compose up -d\ndocker compose ps", CODE),
        text("Open pgAdmin at <b>http://localhost:5050</b>. From a remote workstation, first run "
             "<font name='Courier'>ssh -L 5050:127.0.0.1:5050 user@server</font>. "
             "Sign in with the pgAdmin credentials from <b>.env</b>. Register the server with "
             "host <b>postgres</b>, port <b>5432</b>, database <b>geo</b>, "
             "user <b>postgres</b> and the password from <b>.env</b>."),
        snapshot("Container startup", "bootstrap.log",
                 excerpt("bootstrap.log", " Container week3-postgres  Running",
                         "[2026-11-12T05:08:20]")),
        text("Generate and count the points", SUBHEAD),
        Preformatted("bash scripts/run-step.sh 01_schema\n"
                     "TOTAL=500000000 WORKERS=4 BATCH=10000000 bash scripts/run-load.sh\n"
                     "bash scripts/run-step.sh 03_finalize_load", CODE),
        text("Four workers inserted random longitude and latitude values into an unlogged table. "
             "After loading, the finalization step counted the rows, added the primary key, "
             "set the ID sequence and ran <font name='Courier'>ANALYZE locations</font>."),
        snapshot("Exact count in locations", LOAD,
                 excerpt(LOAD, "SELECT count(*) AS total_rows", "\n\nTime:")),
        PageBreak(),
        *heading("QUERY RESULTS", "Box and circle"),
        text("Each query ran before and after GiST. The panels show selected lines from the first "
             "pass of each phase. The full execution plans are in the repository."),
    ]

    for idx, label, matches in [(0, "Bounding box", "969"), (2, "Circle", "7")]:
        if f"rows={matches} loops=1" not in "\n".join(after[idx].output):
            raise ValueError(f"Unexpected result count for {label}.")
        story += [KeepTogether([
            text(f"{label} <font color='#59515C'>| {matches} matches</font>", SUBHEAD),
            sql(before[idx]),
            evidence("Before GiST", BEFORE, before[idx], "Workers Launched", "Parallel Seq Scan"),
            Spacer(1, 5),
            evidence("After GiST", AFTER, after[idx], "Bitmap Heap Scan", "Bitmap Index Scan"),
        ])]
    story += [
        text("The circle radius is 0.02 degrees. PostgreSQL's built-in POINT uses planar "
             "coordinates, so this is an approximate nearby search.", SMALL),
        PageBreak(),
        *heading("QUERY RESULTS", "Nearest neighbours and polygon"),
        text("Top-100 nearest neighbours", SUBHEAD),
        sql(before[4]),
        evidence("Before GiST", BEFORE, before[4], "Limit  (cost", "Sort Method: top-N", "Parallel Seq Scan"),
        Spacer(1, 5),
        evidence("After GiST", AFTER, after[4], "Index Scan using", "Order By:"),
        text("Polygon containment", SUBHEAD),
        sql(before[6]),
        evidence("Before GiST", BEFORE, before[6], "Workers Launched", "Parallel Seq Scan"),
        Spacer(1, 5),
        evidence("After GiST | count", AFTER, after[6], "Index Only Scan", "Heap Fetches"),
        Spacer(1, 5),
        evidence("After GiST | select full rows", POLYGON, polygon[0], "Bitmap Heap Scan", "Bitmap Index Scan"),
        text("Both polygon queries matched 77 points. The count used an Index Only Scan. "
             "Selecting the full rows used a Bitmap Heap Scan.", SMALL),
        PageBreak(),
        *heading("BENCHMARK", "Performance and index checks"),
    ]

    names = ["Bounding box", "Circle", "Top-100 K-NN", "Polygon count"]
    rows = [
        [name, f"{before[i].ms / 1000:.3f} s", f"{before[i+1].ms / 1000:.3f} s",
         f"{after[i].ms:.3f} ms", f"{after[i+1].ms:.3f} ms"]
        for name, i in zip(names, range(0, 8, 2))
    ]
    rows.append(["Polygon rows", "n/a", "n/a", f"{polygon[0].ms:.3f} ms", f"{polygon[1].ms:.3f} ms"])
    story += [
        table(["Query", "Before first", "Before repeat", "After first", "After repeat"],
              rows, [WIDTH - 344, 86, 86, 86, 86]),
        Spacer(1, 9),
        text("PostgreSQL restarted and the OS page cache was cleared at the start of each "
             "benchmark phase. Queries within a phase ran in sequence and could reuse cached pages."),
        text("Build and analyze the index", SUBHEAD),
        snapshot("GiST creation", BUILD, excerpt(BUILD, "CREATE INDEX idx_locations_gist", "\n\n---")),
        text("Verify index usage and storage", SUBHEAD),
        snapshot("pg_stat_user_indexes", VERIFY, excerpt(VERIFY, "     index_name     | idx_scan", "\n\nTime:")),
        Spacer(1, 5),
        snapshot("Table and all indexes", VERIFY, excerpt(VERIFY, " table_only | indexes_only", "\n\nTime:")),
        Spacer(1, 5),
        snapshot("Individual index sizes", VERIFY, excerpt(VERIFY, "     index_name     | index_size", "\n\nTime:")),
        text("The build took about 14 minutes and added a 31 GB index. For a live service, "
             "<font name='Courier'>CREATE INDEX CONCURRENTLY</font> is an alternative.", SMALL),
        PageBreak(),
        *heading("ANALYSIS", "Geo-hash vs. GiST"),
        text("On the first 50 million points, a B-tree prefix search for <b>dr%</b> yielded "
             "48,768 candidates for the same NYC box. Only 108 passed the exact spatial filter."),
        snapshot("Prefix candidates and exact matches", HASH_BOX,
                 excerpt(HASH_BOX, " candidates | true_rows |", "\n\nTime:")),
        Spacer(1, 7),
        text("In a separate test, 877 of 1,000 point pairs with a mean separation of about 101 m "
             "fell in different precision-7 Geo-hash cells."),
        snapshot("Nearby pairs across cell boundaries", HASH_BOUNDARY,
                 excerpt(HASH_BOUNDARY, " pairs_tested |", "\n\nTime:")),
        Spacer(1, 7),
        table(["What changes", "Geo-hash + B-tree", "GiST"],
              [["Index size on the subset", "1,071 MB", "3,181 MB"],
               ["Range searches", "Prefix candidates need an exact filter", "Uses the spatial predicate"],
               ["Nearest neighbours", "Search adjacent cells and rank candidates", "Reads in distance order"]],
              [WIDTH * 0.28, WIDTH * 0.38, WIDTH * 0.34]),
        text("What I learned", SUBHEAD),
        text("1. Four parallel workers still had to scan the whole table. GiST cut the box query "
             "from about 22 s to 64 ms on the first pass."),
        text("2. GiST returned the nearest 100 points in 0.321 ms without sorting the full table. "
             "That speed came with extra disk space and build time."),
        text("3. Geo-hash prefixes can help route requests to a shard. An exact nearby search "
             "also needs adjacent cells and a distance check."),
        text("References", SUBHEAD),
        text(f'<link href="{TUTORIAL}" color="#4C2548">Jeyaram Ayyalusamy, PostgreSQL 17 GiST tutorial</link><br/>'
             f'<link href="{DOCKER_REF}" color="#4C2548">Docker Compose reference for PostgreSQL and pgAdmin</link><br/>'
             '<link href="https://www.postgresql.org/docs/17/" color="#4C2548">PostgreSQL 17 documentation</link><br/>'
             '<link href="https://github.com/Syedmaqboolhusssain/postgres-gist-500m-geopoints" color="#4C2548">'
             'Assignment repository and full transcripts</link>',
             SMALL),
    ]

    doc = SimpleDocTemplate(
        str(OUT), pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=37, bottomMargin=42, title="Spatial indexing on 500 million points",
        author="Syed Maqbool Hussain",
    )
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == "__main__":
    build()
