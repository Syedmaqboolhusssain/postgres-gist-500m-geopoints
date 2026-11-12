from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import PageBreak, Spacer, Table, TableStyle

from build_report import (
    AssignmentDoc,
    BLUE,
    CYAN,
    GREEN,
    LIGHT,
    NAVY,
    OUT as ORIGINAL_OUT,
    PALE,
    RED,
    data_table,
    h1,
    h2,
    metric_row,
    p,
    styles,
    terminal,
)


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "pdf" / "postgres_gist_500m_assignment_concise.pdf"


def cover_block():
    block = Table(
        [
            [p("DATABASE SYSTEMS ASSIGNMENT", "CoverKicker")],
            [p("PostgreSQL 17 GiST Spatial Indexing at 500 Million Points", "CoverTitle")],
            [p("Docker setup, spatial queries, GiST performance, and Geo-hash analysis", "CoverSub")],
        ],
        colWidths=[174 * mm],
        rowHeights=[16 * mm, 54 * mm, 30 * mm],
    )
    block.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), NAVY),
                ("LEFTPADDING", (0, 0), (-1, -1), 14),
                ("RIGHTPADDING", (0, 0), (-1, -1), 14),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return block


def build():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    story = []

    # Page 1: cover
    story += [cover_block(), Spacer(1, 18 * mm)]
    story += [metric_row([
        ("500,000,000", "generated points"),
        ("31 GB", "GiST index"),
        ("0.321 ms", "cold top-100 K-NN"),
    ])]
    story += [Spacer(1, 16 * mm)]
    story += [
        p("Student: Syed Maqbool Hussain", "CoverMeta"),
        p("Execution date: 12 November 2026", "CoverMeta"),
        p("Environment: Hetzner CPX42, Docker Compose, PostgreSQL 17.5, PostGIS 3.5, pgAdmin 4", "CoverMeta"),
        PageBreak(),
    ]

    # Page 2: setup and 500M proof
    story += [h1("1. Setup and data generation")]
    story += [p(
        "The test used a Hetzner CPX42 virtual machine with 8 vCPUs, 16 GB RAM, and a 320 GB SSD. "
        "PostgreSQL 17.5 with PostGIS 3.5 and pgAdmin 4 ran in Docker containers. PostgreSQL and pgAdmin "
        "were bound to localhost and accessed through an SSH tunnel."
    )]
    story += [data_table([
        ["Component", "Configuration"],
        ["Database", "PostgreSQL 17.5 with PostGIS 3.5"],
        ["Administration", "pgAdmin 4 in Docker"],
        ["Container runtime", "Docker 27.5.1 and Compose 2.32.4"],
        ["Server", "8 vCPU, 16 GB RAM, 320 GB SSD"],
        ["Security", "Database and pgAdmin ports bound to 127.0.0.1"],
    ], [43 * mm, 131 * mm])]
    story += [h2("Docker layout")]
    story += [p(
        "The Compose file starts two services. The postgres service stores the database in a persistent volume. "
        "The pgAdmin service starts after PostgreSQL passes its health check."
    )]
    story += [h2("Proof of 500 million points")]
    story += [terminal("""SELECT count(*) AS total_rows FROM locations;
 total_rows
------------
  500000000
(1 row)

Table: public.locations
 location_id | bigint | not null
 name        | text
 geolocation | point

 table_only | indexes_only | total_with_indexes
------------+--------------+-------------------
 36 GB      | 10 GB        | 46 GB

 planner_row_estimate | heap_pages
----------------------+-----------
 499995584            | 4671907""", 24)]
    story += [p(
        "The exact count confirms that the locations table contains 500,000,000 rows. The 36 GB heap size and "
        "planner estimate provide additional evidence that the full data set was loaded and analyzed."
    ), PageBreak()]

    # Page 3: before GiST
    story += [h1("2. Queries before the GiST index")]
    story += [p(
        "Each tutorial query was first executed without a spatial index using EXPLAIN (ANALYZE, BUFFERS). "
        "PostgreSQL scanned the full table in parallel."
    )]
    story += [terminal("""Q1: Bounding box
Parallel Seq Scan on locations
Filter: geolocation <@ box '((-74.1,40.6),(-73.7,40.9))'
Rows returned: 969
Execution Time: 21820.542 ms

Q2: Circle
Parallel Seq Scan on locations
Filter: geolocation <@ circle '<(-73.9857,40.7484),0.02>'
Rows returned: 7
Execution Time: 22121.710 ms""", 22)]
    story += [Spacer(1, 3 * mm)]
    story += [terminal("""Q3: Top-100 nearest neighbours
Parallel Seq Scan on locations
Sort Key: geolocation <-> '(-73.9857,40.7484)'::point
Limit: 100
Execution Time: 29897.233 ms

Q4: Polygon containment
Parallel Seq Scan on locations
Filter: geolocation <@ polygon
Rows returned: 77
Execution Time: 21644.234 ms""", 22)]
    story += [data_table([
        ["Query", "Time", "Plan"],
        ["Bounding box", "21.821 s", "Parallel Seq Scan"],
        ["Circle", "22.122 s", "Parallel Seq Scan"],
        ["Top-100 K-NN", "29.897 s", "Parallel Seq Scan + sort"],
        ["Polygon", "21.644 s", "Parallel Seq Scan"],
    ], [60 * mm, 34 * mm, 80 * mm])]
    story += [p(
        "Parallel workers reduced elapsed time, but every query still read the 500 million row table. "
        "The nearest-neighbour query also sorted distances before returning 100 rows."
    ), PageBreak()]

    # Page 4: index and after GiST
    story += [h1("3. GiST index and indexed query results")]
    story += [terminal("""CREATE INDEX idx_locations_gist
ON locations USING gist (geolocation);

CREATE INDEX
Time: 850698.098 ms (14:10.698)

index_name          | index_size
--------------------+-----------
idx_locations_gist  | 31 GB
locations_pkey      | 10 GB""", 18)]
    story += [terminal("""Q1: Bounding box
Bitmap Heap Scan on locations
  -> Bitmap Index Scan on idx_locations_gist
Rows returned: 969
Execution Time: 63.938 ms

Q2: Circle
Bitmap Heap Scan on locations
  -> Bitmap Index Scan on idx_locations_gist
Rows returned: 7
Execution Time: 0.093 ms""", 22)]
    story += [terminal("""Q3: Top-100 nearest neighbours
Index Scan using idx_locations_gist on locations
Order By: geolocation <-> '(-73.9857,40.7484)'::point
Rows returned: 100
Execution Time: 0.321 ms

Q4: Polygon count
Index Only Scan using idx_locations_gist on locations
Rows returned by index: 77
Execution Time: 3.798 ms

Polygon row retrieval
Bitmap Heap Scan + Bitmap Index Scan
Execution Time: 13.597 ms""", 25)]
    story += [p(
        "The tutorial polygon query uses COUNT(*), so PostgreSQL 17 selected an Index Only Scan. A second polygon "
        "query returned the rows and produced the expected Bitmap Index Scan and Bitmap Heap Scan."
    ), PageBreak()]

    # Page 5: comparison
    story += [h1("4. Before and after GiST")]
    story += [data_table([
        ["Query", "Before GiST", "After GiST cold", "After GiST warm", "Indexed plan"],
        ["Bounding box", "21,820.542 ms", "63.938 ms", "1.263 ms", "Bitmap index + heap"],
        ["Circle", "22,121.710 ms", "0.093 ms", "0.086 ms", "Bitmap index + heap"],
        ["Top-100 K-NN", "29,897.233 ms", "0.321 ms", "0.295 ms", "Ordered GiST scan"],
        ["Polygon count", "21,644.234 ms", "3.798 ms", "0.181 ms", "Index Only Scan"],
        ["Polygon rows", "Same predicate", "13.597 ms", "0.151 ms", "Bitmap index + heap"],
    ], [36 * mm, 31 * mm, 32 * mm, 31 * mm, 44 * mm])]
    story += [Spacer(1, 5 * mm)]
    story += [metric_row([
        ("341x", "box cold speedup"),
        ("237,868x", "circle cold speedup"),
        ("93,137x", "K-NN cold speedup"),
        ("5,699x", "polygon cold speedup"),
    ])]
    story += [h2("Why the index helped")]
    story += [p(
        "Without GiST, PostgreSQL checked the spatial condition against every row. With GiST, the index located "
        "small candidate sets. Bitmap scans were suitable for box, circle, and row-returning polygon searches. "
        "The K-NN query used the distance ordering provided by GiST and stopped as soon as 100 rows were found."
    )]
    story += [p(
        "The warm results are lower because relevant index and table pages were already in memory. The cold values "
        "are a fairer measure of the first execution, while the warm values show repeated-query performance."
    )]
    story += [h2("Storage cost")]
    story += [data_table([
        ["Item", "Size"],
        ["Table heap", "36 GB"],
        ["Primary key", "10 GB"],
        ["GiST index", "31 GB"],
        ["Table and all indexes", "77 GB"],
    ], [110 * mm, 64 * mm])]
    story += [p(
        "The GiST index uses significant disk space, but it avoids repeated scans of the 36 GB table."
    ), PageBreak()]

    # Page 6: geohash
    story += [h1("5. Geo-hash and spatial indexing")]
    story += [p(
        "Geo-hash converts a location into a text prefix. Nearby points often share a prefix, so a B-tree can use "
        "the prefix to produce candidates. The final result still needs an exact spatial check."
    )]
    story += [terminal("""Test data: first 50,000,000 locations

Geo-hash B-tree size: 1,071 MB
Comparison GiST size: 3,181 MB

Prefix: dr%
Candidates:       48,768
True rows:           108
False positives:  48,660
Precision:          0.221%
Recall:           100.000%
Overfetch:          451.6x

Geo-hash only, including exact recheck: 934.378 ms
GiST exact box query:                    0.148 ms""", 24)]
    story += [data_table([
        ["Point", "Geo-hash + B-tree", "GiST"],
        ["Box search", "Prefix scan followed by exact check", "Direct spatial predicate"],
        ["Nearest neighbours", "Search cells, merge, sort, and recheck", "Ordered K-NN index scan"],
        ["Boundary handling", "Neighbouring cells must be included", "Handled by index traversal"],
        ["Useful for", "Routing, partitioning, and cache keys", "Database spatial search"],
    ], [35 * mm, 70 * mm, 69 * mm])]
    story += [h2("Boundary test")]
    story += [p(
        "In the boundary test, 877 of 1,000 point pairs about 101 metres apart had different precision-7 Geo-hashes. "
        "Searching one cell can therefore miss a nearby point. An application must also search neighbouring cells "
        "and calculate the real distance."
    )]
    story += [p(
        "Geo-hash is useful when data must be divided across machines. GiST is the better choice for exact box, "
        "circle, polygon, and nearest-neighbour queries inside PostgreSQL. A large system can use both."
    ), PageBreak()]

    # Page 7: learning and conclusion
    story += [h1("6. What I learned")]
    story += [p(
        "This experiment showed that parallel execution does not solve every large-table problem. The unindexed "
        "queries used several workers, but they still inspected all 500 million rows and took between 21 and 30 seconds."
    )]
    story += [p(
        "A GiST index stores spatial keys that help PostgreSQL reject most rows before reading the table. This changed "
        "the containment queries to bitmap or index-only plans. It also allowed the nearest-neighbour query to read "
        "points in distance order and stop after the first 100 results."
    )]
    story += [p(
        "The results also showed that an index has a cost. The GiST index used 31 GB and took about 14 minutes to build. "
        "That cost is reasonable when the same large data set must answer many nearby-place queries."
    )]
    story += [p(
        "Geo-hash is not an exact distance calculation. A coarse prefix returns too many candidates, while a fine "
        "prefix can miss points across a cell boundary. It works well as a routing or partitioning key, but exact "
        "nearby-place results still need neighbouring cells and a distance check."
    )]
    story += [h2("Conclusion")]
    story += [p(
        "The assignment was completed with 500,000,000 points. All four tutorial queries were measured before and "
        "after GiST. Before indexing, PostgreSQL used parallel sequential scans and took seconds. After indexing, "
        "the same work used spatial index plans and completed in milliseconds. For this PostgreSQL workload, GiST "
        "was the most direct solution for nearby-place filtering and K-NN search."
    )]
    story += [h2("References")]
    story += [p(
        "1. Jeyaram Ayyalusamy, 'PostgreSQL 17 Performance Tuning: GiST (Generalized Search Tree)', 5 September 2025. "
        "https://medium.com/@jramcloud1/21-postgresql-17-performance-tuning-gist-generalized-search-tree-8e5cacea9fc8"
    )]
    story += [p("2. PostgreSQL 17 documentation: https://www.postgresql.org/docs/17/")]
    story += [p("3. PostGIS documentation: https://postgis.net/docs/")]
    story += [Spacer(1, 4 * mm)]
    story += [p(
        "The timings and plans in this report were taken from the saved PostgreSQL transcripts produced during the run.",
        "Callout",
    )]

    doc = AssignmentDoc(str(OUT))
    doc.title = "PostgreSQL 17 GiST Spatial Indexing at 500 Million Points"
    doc.author = "Syed Maqbool Hussain"
    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
